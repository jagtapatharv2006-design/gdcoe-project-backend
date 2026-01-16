"""
Git repository management for HPPS system.
Handles cloning, updating, and extracting Git activity metrics.
"""

import os
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from collections import defaultdict
from config import Config
from logger import logger
from utils import normalize_github_url, generate_repo_local_path, get_directory_size


def run_git_command(cmd: List[str], cwd: Path, timeout: int = 60) -> tuple:
    """
    Run git command safely.
    
    Args:
        cmd: Git command as list
        cwd: Working directory
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (stdout, stderr, return_code)
    """
    try:
        result = subprocess.run(
            ["git"] + cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        logger.warning(f"Git command timeout: {' '.join(cmd)}")
        return "", "Command timeout", -1
    except FileNotFoundError:
        logger.error("Git not found. Please install Git.")
        return "", "Git not found", -1
    except Exception as e:
        logger.error(f"Git command error: {str(e)}")
        return "", str(e), -1


def clone_repository(repo_url: str, local_path: Optional[Path] = None) -> Optional[Path]:
    """
    Clone repository from GitHub URL.
    
    Args:
        repo_url: GitHub repository URL
        local_path: Optional local path (auto-generated if None)
        
    Returns:
        Local path to cloned repository or None if failed
    """
    normalized_url = normalize_github_url(repo_url)
    if not normalized_url:
        logger.error(f"Invalid GitHub URL: {repo_url}")
        return None
    
    if local_path is None:
        local_path = generate_repo_local_path(repo_url, Config.REPO_STORAGE_PATH)
    
    # Remove existing directory if it exists
    if local_path.exists():
        try:
            shutil.rmtree(local_path)
        except Exception as e:
            logger.warning(f"Could not remove existing directory: {str(e)}")
    
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Cloning repository: {normalized_url} to {local_path}")
    
    stdout, stderr, returncode = run_git_command(
        ["clone", normalized_url, str(local_path)],
        cwd=local_path.parent,
        timeout=300
    )
    
    if returncode != 0:
        logger.error(f"Failed to clone repository: {stderr}")
        return None
    
    logger.info(f"Successfully cloned repository to {local_path}")
    return local_path


def update_repository(local_path: Path) -> bool:
    """
    Update existing repository (git pull).
    
    Args:
        local_path: Local path to repository
        
    Returns:
        True if successful, False otherwise
    """
    if not local_path.exists():
        logger.error(f"Repository path does not exist: {local_path}")
        return False
    
    if not (local_path / ".git").exists():
        logger.error(f"Not a Git repository: {local_path}")
        return False
    
    logger.info(f"Updating repository: {local_path}")
    
    stdout, stderr, returncode = run_git_command(
        ["pull"],
        cwd=local_path,
        timeout=120
    )
    
    if returncode != 0:
        logger.warning(f"Failed to update repository: {stderr}")
        return False
    
    logger.info(f"Successfully updated repository: {local_path}")
    return True


def clone_or_update_repository(repo_url: str, local_path: Optional[Path] = None) -> Optional[Path]:
    """
    Clone repository if it doesn't exist, or update if it does.
    
    Args:
        repo_url: GitHub repository URL
        local_path: Optional local path (auto-generated if None)
        
    Returns:
        Local path to repository or None if failed
    """
    if local_path is None:
        local_path = generate_repo_local_path(repo_url, Config.REPO_STORAGE_PATH)
    
    if local_path.exists() and (local_path / ".git").exists():
        # Repository exists, try to update
        if update_repository(local_path):
            return local_path
        else:
            # Update failed, try cloning fresh
            logger.info("Update failed, cloning fresh copy")
            return clone_repository(repo_url, local_path)
    else:
        # Repository doesn't exist, clone it
        return clone_repository(repo_url, local_path)


def get_git_activity_metrics(repo_path: Path) -> Dict[str, any]:
    """
    Extract Git activity metrics from repository.
    
    Returns:
        Dictionary with:
        - active_months: int
        - activity_frequency: float (commits per month)
        - longest_streak: int (days)
        - rating_stability: float (0-1, based on commit consistency)
    """
    if not repo_path.exists() or not (repo_path / ".git").exists():
        logger.warning(f"Invalid Git repository: {repo_path}")
        return {
            "active_months": 0,
            "activity_frequency": 0.0,
            "longest_streak": 0,
            "rating_stability": 0.0
        }
    
    try:
        # Get all commit dates
        stdout, stderr, returncode = run_git_command(
            ["log", "--pretty=format:%ai", "--all"],
            cwd=repo_path,
            timeout=120
        )
        
        if returncode != 0 or not stdout:
            logger.warning(f"Could not get commit history: {stderr}")
            return {
                "active_months": 0,
                "activity_frequency": 0.0,
                "longest_streak": 0,
                "rating_stability": 0.0
            }
        
        commit_dates = []
        for line in stdout.split("\n"):
            if line.strip():
                try:
                    # Parse date (format: "2024-01-15 10:30:00 +0000")
                    date_str = line.strip()[:19]  # Get "2024-01-15 10:30:00"
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    commit_dates.append(dt.date())
                except Exception:
                    continue
        
        if not commit_dates:
            return {
                "active_months": 0,
                "activity_frequency": 0.0,
                "longest_streak": 0,
                "rating_stability": 0.0
            }
        
        commit_dates.sort()
        
        # Calculate active_months
        if len(commit_dates) > 1:
            first_date = commit_dates[0]
            last_date = commit_dates[-1]
            delta = last_date - first_date
            active_months = max(1, (delta.days // 30) + 1)
        else:
            active_months = 1
        
        # Calculate activity_frequency (commits per month)
        total_commits = len(commit_dates)
        if active_months > 0:
            activity_frequency = total_commits / active_months
        else:
            activity_frequency = float(total_commits)
        
        # Calculate longest_streak (consecutive days with commits)
        longest_streak = 1
        current_streak = 1
        
        for i in range(1, len(commit_dates)):
            diff = (commit_dates[i] - commit_dates[i-1]).days
            if diff <= 1:  # Same day or next day
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
        
        # Calculate rating_stability (consistency of commits)
        # Group commits by month
        monthly_commits = defaultdict(int)
        for date in commit_dates:
            month_key = date.strftime("%Y-%m")
            monthly_commits[month_key] += 1
        
        if len(monthly_commits) > 0:
            # Calculate coefficient of variation
            commit_counts = list(monthly_commits.values())
            mean_commits = sum(commit_counts) / len(commit_counts)
            
            if mean_commits > 0:
                variance = sum((c - mean_commits) ** 2 for c in commit_counts) / len(commit_counts)
                std_dev = variance ** 0.5
                cv = std_dev / mean_commits if mean_commits > 0 else 1.0
                # Lower CV = more stable, convert to 0-1 scale (inverse)
                rating_stability = max(0.0, min(1.0, 1.0 / (1.0 + cv)))
            else:
                rating_stability = 0.0
        else:
            rating_stability = 0.0
        
        return {
            "active_months": active_months,
            "activity_frequency": activity_frequency,
            "longest_streak": longest_streak,
            "rating_stability": rating_stability
        }
        
    except Exception as e:
        logger.error(f"Error calculating Git metrics: {str(e)}")
        return {
            "active_months": 0,
            "activity_frequency": 0.0,
            "longest_streak": 0,
            "rating_stability": 0.0
        }


def cleanup_old_repositories(days: int = None) -> int:
    """
    Clean up old repositories that haven't been accessed recently.
    
    Args:
        days: Number of days (uses config default if None)
        
    Returns:
        Number of repositories removed
    """
    if days is None:
        days = Config.CLEANUP_OLD_REPOS_DAYS
    
    from utils import clean_old_directories
    return clean_old_directories(Config.REPO_STORAGE_PATH, days)

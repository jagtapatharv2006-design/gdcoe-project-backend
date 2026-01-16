"""
Utility functions for HPPS system.
"""

import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import json


def normalize_github_url(url: str) -> Optional[str]:
    """
    Normalize GitHub URL to standard format.
    
    Args:
        url: GitHub URL (various formats accepted)
        
    Returns:
        Normalized URL or None if invalid
    """
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip()
    
    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]
    
    # Handle various GitHub URL formats
    patterns = [
        r"https?://github\.com/([^/]+/[^/]+)",
        r"github\.com/([^/]+/[^/]+)",
        r"git@github\.com:([^/]+/[^/]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            repo_path = match.group(1)
            return f"https://github.com/{repo_path}"
    
    return None


def extract_repo_name_from_url(url: str) -> Optional[str]:
    """
    Extract repository name from GitHub URL.
    
    Args:
        url: GitHub URL
        
    Returns:
        Repository name (owner/repo) or None
    """
    normalized = normalize_github_url(url)
    if not normalized:
        return None
    
    match = re.search(r"github\.com/([^/]+/[^/]+)", normalized)
    if match:
        return match.group(1)
    
    return None


def generate_repo_local_path(repo_url: str, base_path: Path) -> Path:
    """
    Generate local path for repository based on URL.
    
    Args:
        repo_url: GitHub repository URL
        base_path: Base storage path
        
    Returns:
        Path object for local repository
    """
    repo_name = extract_repo_name_from_url(repo_url)
    if not repo_name:
        # Fallback: use hash of URL
        repo_name = hashlib.md5(repo_url.encode()).hexdigest()[:12]
    
    # Replace / with _ for filesystem compatibility
    repo_name = repo_name.replace("/", "_")
    return base_path / repo_name


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email string
        
    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL string
        
    Returns:
        True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    pattern = r"^https?://.+"
    return bool(re.match(pattern, url))


def safe_json_loads(data: str, default: Any = None) -> Any:
    """
    Safely parse JSON string.
    
    Args:
        data: JSON string
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    Safely convert object to JSON string.
    
    Args:
        data: Object to serialize
        default: Default JSON string if serialization fails
        
    Returns:
        JSON string or default
    """
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return default


def format_timedelta(td: timedelta) -> str:
    """
    Format timedelta as human-readable string.
    
    Args:
        td: Timedelta object
        
    Returns:
        Formatted string
    """
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def format_size(size_bytes: int) -> str:
    """
    Format bytes as human-readable size.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def get_directory_size(path: Path) -> int:
    """
    Get total size of directory in bytes.
    
    Args:
        path: Directory path
        
    Returns:
        Size in bytes
    """
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except (OSError, PermissionError):
        pass
    return total


def clean_old_directories(base_path: Path, days: int = 30) -> int:
    """
    Remove directories older than specified days.
    
    Args:
        base_path: Base directory path
        days: Number of days
        
    Returns:
        Number of directories removed
    """
    if not base_path.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    
    try:
        for item in base_path.iterdir():
            if not item.is_dir():
                continue
            
            # Check last modification time
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime < cutoff:
                try:
                    import shutil
                    shutil.rmtree(item)
                    removed += 1
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    
    return removed


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for filesystem compatibility.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename or "unnamed"


def dict_to_json_safe(data: Dict[str, Any]) -> str:
    """
    Convert dictionary to JSON string with error handling.
    
    Args:
        data: Dictionary to convert
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return "{}"


def json_to_dict_safe(data: str) -> Dict[str, Any]:
    """
    Convert JSON string to dictionary with error handling.
    
    Args:
        data: JSON string
        
    Returns:
        Dictionary or empty dict on error
    """
    if not data:
        return {}
    
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {}

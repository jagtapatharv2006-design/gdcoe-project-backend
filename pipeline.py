"""
Data processing pipeline for HPPS system.
Orchestrates the complete analysis flow from student data to HPPS score.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from database import (
    get_db_session, StudentDAO, RepositoryDAO, HPPSScoreDAO, AnalysisLogDAO
)
from git_manager import clone_or_update_repository, get_git_activity_metrics
from layer0_code_analyzer import analyze_repo
from layer_skill_detector import detect_skill_tags
from function import calculate_HPPS
from scrapers import fetch_ratings
from logger import logger
from config import Config


def analyze_student_complete(student_id: int) -> Dict:
    """
    Complete analysis pipeline for a student.
    
    1. Get student from DB
    2. Fetch ratings (Codeforces/LeetCode)
    3. Clone/update repo
    4. Run code analysis
    5. Run skill detection
    6. Extract git metrics
    7. Calculate HPPS
    8. Save results to DB
    
    Args:
        student_id: Student ID
        
    Returns:
        Dictionary with analysis results and status
    """
    start_time = time.time()
    analysis_log = None
    
    try:
        with get_db_session() as session:
            # 1. Get student from DB
            student = StudentDAO.get_by_id(session, student_id)
            if not student:
                return {
                    "success": False,
                    "error": f"Student not found: {student_id}",
                    "student_id": student_id
                }
            
            logger.info(f"Starting analysis for student {student_id}: {student.name}")
            
            # Create analysis log
            from models import AnalysisLog
            analysis_log = AnalysisLog(
                student_id=student_id,
                analysis_type="FULL",
                status="IN_PROGRESS"
            )
            session.add(analysis_log)
            session.flush()
            
            # 2. Fetch ratings if usernames are provided
            cf_rating = None
            lc_rating = None
            
            if student.cf_username or student.lc_username:
                logger.info(f"Fetching ratings for student {student_id}")
                ratings = fetch_ratings(
                    cf_username=student.cf_username,
                    lc_username=student.lc_username
                )
                cf_rating = ratings.get("cf_rating")
                lc_rating = ratings.get("lc_rating")
                
                # Update student with ratings
                if cf_rating is not None:
                    student.cf_rating = cf_rating
                if lc_rating is not None:
                    student.lc_rating = lc_rating
            
            # Use existing ratings if fetch failed
            if cf_rating is None:
                cf_rating = student.cf_rating
            if lc_rating is None:
                lc_rating = student.lc_rating
            
            # 3. Clone/update repository
            repo_path = None
            repository = None
            
            if student.github_url:
                logger.info(f"Cloning/updating repository for student {student_id}")
                repo_path = clone_or_update_repository(student.github_url)
                
                if repo_path:
                    # Get or create repository record
                    repos = RepositoryDAO.get_by_student_id(session, student_id)
                    if repos:
                        repository = repos[0]
                    else:
                        repository = RepositoryDAO.create(
                            session,
                            student_id=student_id,
                            repo_url=student.github_url,
                            local_path=str(repo_path),
                            analysis_status="IN_PROGRESS"
                        )
                    
                    repository.local_path = str(repo_path)
                    session.commit()
                else:
                    logger.warning(f"Failed to clone repository for student {student_id}")
            else:
                logger.warning(f"No GitHub URL for student {student_id}")
            
            # 4. Run code analysis
            code_analysis_result = {}
            if repo_path and repo_path.exists():
                logger.info(f"Running code analysis for student {student_id}")
                code_analysis_result = analyze_repo(str(repo_path))
            else:
                logger.warning(f"No repository path for code analysis: student {student_id}")
                code_analysis_result = {
                    "warnings": ["No repository available for analysis"],
                    "errors": []
                }
            
            # 5. Run skill detection
            skill_tags_result = {}
            if repo_path and repo_path.exists():
                logger.info(f"Running skill detection for student {student_id}")
                skill_tags_result = detect_skill_tags(str(repo_path))
            else:
                logger.warning(f"No repository path for skill detection: student {student_id}")
                skill_tags_result = {
                    "warnings": ["No repository available for skill detection"],
                    "backend": False,
                    "frontend": False,
                    "machine_learning": False,
                    "competitive_programming": False,
                    "devops": False,
                    "data_engineering": False
                }
            
            # 6. Extract git metrics
            git_metrics = {}
            if repo_path and repo_path.exists():
                logger.info(f"Extracting Git metrics for student {student_id}")
                git_metrics = get_git_activity_metrics(repo_path)
            else:
                git_metrics = {
                    "active_months": 0,
                    "activity_frequency": 0.0,
                    "longest_streak": 0,
                    "rating_stability": 0.0
                }
            
            # 7. Calculate HPPS
            logger.info(f"Calculating HPPS for student {student_id}")
            
            hpps_result = calculate_HPPS(
                CF_rating=cf_rating,
                LC_rating=lc_rating,
                CF_hard_problem_ratio=code_analysis_result.get("CF_hard_problem_ratio", 0.0),
                LC_medium_hard_ratio=code_analysis_result.get("LC_medium_hard_ratio", 0.0),
                real_projects_count=code_analysis_result.get("real_projects_count", 1),
                active_months=git_metrics.get("active_months", 0),
                activity_frequency=git_metrics.get("activity_frequency", 0.0),
                rating_stability=git_metrics.get("rating_stability", 0.0),
                longest_streak=git_metrics.get("longest_streak", 0),
                project_complexity_score=code_analysis_result.get("project_complexity_score", 50.0),
                code_quality_indicators=code_analysis_result.get("code_quality_indicators", 50.0),
                stack_diversity=code_analysis_result.get("stack_diversity", 50.0),
                reusable_components=code_analysis_result.get("reusable_components", 50.0),
                cross_domain_work=code_analysis_result.get("cross_domain_work", 50.0),
                oss_engagement=code_analysis_result.get("oss_engagement", 50.0),
                new_tech_usage=code_analysis_result.get("new_tech_usage", 50.0)
            )
            
            # 8. Save results to DB
            if repository:
                repository.analysis_status = "COMPLETED"
                repository.last_analyzed = datetime.now()
            
            # Save HPPS score
            hpps_score = HPPSScoreDAO.create(
                session,
                student_id=student_id,
                hpps=hpps_result["HPPS"],
                hpps_percentage=hpps_result["HPPS_percentage"],
                AD=hpps_result["AD"],
                EAP=hpps_result["EAP"],
                CCL=hpps_result["CCL"],
                LA=hpps_result["LA"]
            )
            
            # Update student general_score
            student.general_score = hpps_result["HPPS"]
            
            # Update analysis log
            execution_time = time.time() - start_time
            if analysis_log:
                analysis_log.status = "SUCCESS"
                analysis_log.execution_time_seconds = execution_time
                analysis_log.repository_id = repository.id if repository else None
            
            session.commit()
            
            logger.info(f"Analysis completed for student {student_id} in {execution_time:.2f}s")
            
            return {
                "success": True,
                "student_id": student_id,
                "hpps": hpps_result["HPPS"],
                "hpps_percentage": hpps_result["HPPS_percentage"],
                "sub_scores": {
                    "AD": hpps_result["AD"],
                    "EAP": hpps_result["EAP"],
                    "CCL": hpps_result["CCL"],
                    "LA": hpps_result["LA"]
                },
                "code_analysis": code_analysis_result,
                "skill_tags": skill_tags_result,
                "git_metrics": git_metrics,
                "execution_time_seconds": execution_time,
                "warnings": hpps_result.get("warnings", []),
                "errors": hpps_result.get("errors", [])
            }
            
    except Exception as e:
        logger.error(f"Error in analyze_student_complete for student {student_id}: {str(e)}", exc_info=True)
        
        # Update analysis log on error
        try:
            with get_db_session() as session:
                if analysis_log:
                    from models import AnalysisLog
                    log_record = session.query(AnalysisLog).filter_by(id=analysis_log.id).first()
                    if log_record:
                        log_record.status = "FAILED"
                        log_record.error_message = str(e)
                        log_record.execution_time_seconds = time.time() - start_time
                session.commit()
        except Exception:
            pass
        
        return {
            "success": False,
            "error": str(e),
            "student_id": student_id
        }


def analyze_batch(student_ids: List[int]) -> Dict:
    """
    Analyze multiple students in batch.
    
    Args:
        student_ids: List of student IDs
        
    Returns:
        Dictionary with batch results
    """
    results = []
    successful = 0
    failed = 0
    
    for student_id in student_ids:
        result = analyze_student_complete(student_id)
        results.append(result)
        
        if result.get("success"):
            successful += 1
        else:
            failed += 1
    
    return {
        "total": len(student_ids),
        "successful": successful,
        "failed": failed,
        "results": results
    }

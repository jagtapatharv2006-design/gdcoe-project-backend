"""
Celery tasks for HPPS system.
Handles async task execution for analysis and job matching.
"""

import os
from celery import Celery
from typing import List, Dict, Optional
from pipeline import analyze_student_complete, analyze_batch
from job_matching_layer import process_job_profile
from database import get_db_session, StudentDAO, JobDAO, JobRequestDAO
from logger import logger

# Create Celery app
app = Celery("hpps_tasks")
app.config_from_object("celery_config")

# Fallback to synchronous execution if Celery broker not available
CELERY_ENABLED = True
try:
    app.control.inspect().ping()
except Exception:
    CELERY_ENABLED = False
    logger.warning("Celery broker not available, tasks will run synchronously")


@app.task(name="tasks.analyze_student_task", bind=True, max_retries=3)
def analyze_student_task(self, student_id: int) -> Dict:
    """
    Async task to analyze a student.
    
    Args:
        student_id: Student ID to analyze
        
    Returns:
        Analysis results dictionary
    """
    try:
        logger.info(f"Starting async analysis for student {student_id}")
        result = analyze_student_complete(student_id)
        return result
    except Exception as exc:
        logger.error(f"Error in analyze_student_task: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@app.task(name="tasks.analyze_batch_task", bind=True)
def analyze_batch_task(self, student_ids: List[int]) -> Dict:
    """
    Async task to analyze multiple students.
    
    Args:
        student_ids: List of student IDs
        
    Returns:
        Batch analysis results
    """
    try:
        logger.info(f"Starting async batch analysis for {len(student_ids)} students")
        result = analyze_batch(student_ids)
        return result
    except Exception as exc:
        logger.error(f"Error in analyze_batch_task: {str(exc)}")
        raise


@app.task(name="tasks.match_job_task", bind=True)
def match_job_task(self, job_id: int, gemini_api_key: Optional[str] = None) -> Dict:
    """
    Async task to process job matching.
    
    Args:
        job_id: Job ID to match
        gemini_api_key: Optional Gemini API key
        
    Returns:
        Job matching results
    """
    try:
        logger.info(f"Starting async job matching for job {job_id}")
        
        with get_db_session() as session:
            job = JobDAO.get_by_id(session, job_id)
            if not job:
                return {
                    "success": False,
                    "error": f"Job not found: {job_id}"
                }
            
            # Get all students with HPPS scores
            from models import Student, HPPSScore
            students_query = session.query(Student).join(HPPSScore).all()
            
            students_data = []
            for student in students_query:
                # Get latest HPPS score
                latest_score = max(
                    student.hpps_scores,
                    key=lambda s: s.calculated_at,
                    default=None
                )
                
                # Get skill tags from repository analysis
                skills = []
                tags = []
                for repo in student.repositories:
                    # In a real implementation, you'd fetch skill tags from analysis results
                    # For now, we'll use basic structure
                    pass
                
                students_data.append({
                    "student_id": student.id,
                    "name": student.name,
                    "github_url": student.github_url,
                    "general_score": latest_score.hpps if latest_score else 0.0,
                    "skills": skills,
                    "tags": tags,
                    "languages": []  # Would be populated from repository analysis
                })
            
            # Process job profile
            result = process_job_profile(
                job_description=job.description,
                students=students_data,
                gemini_api_key=gemini_api_key or os.getenv("GEMINI_API_KEY")
            )
            
            # Create job requests
            for request_data in result.get("job_requests", []):
                JobRequestDAO.create(session, **request_data)
            
            session.commit()
            
            return {
                "success": True,
                "job_id": job_id,
                "job_role": result.get("job_role"),
                "matched_students": len(result.get("job_requests", [])),
                "rankings": {
                    "general": result.get("general_ranking", []),
                    "job_specific": result.get("job_specific_ranking", [])
                }
            }
            
    except Exception as exc:
        logger.error(f"Error in match_job_task: {str(exc)}")
        return {
            "success": False,
            "error": str(exc)
        }


# Synchronous wrappers for when Celery is not available
def analyze_student_sync(student_id: int) -> Dict:
    """Synchronous wrapper for analyze_student_task."""
    if CELERY_ENABLED:
        return analyze_student_task.delay(student_id).get()
    else:
        return analyze_student_complete(student_id)


def analyze_batch_sync(student_ids: List[int]) -> Dict:
    """Synchronous wrapper for analyze_batch_task."""
    if CELERY_ENABLED:
        return analyze_batch_task.delay(student_ids).get()
    else:
        return analyze_batch(student_ids)


def match_job_sync(job_id: int, gemini_api_key: Optional[str] = None) -> Dict:
    """Synchronous wrapper for match_job_task."""
    if CELERY_ENABLED:
        return match_job_task.delay(job_id, gemini_api_key).get()
    else:
        # Run synchronously
        return match_job_task(job_id, gemini_api_key)

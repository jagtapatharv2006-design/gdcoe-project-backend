"""
FastAPI application for HPPS system.
REST API endpoints for student management, analysis, and job matching.
"""

import os
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, init_db, StudentDAO, JobDAO, JobRequestDAO, HPPSScoreDAO
from schemas import (
    StudentCreate, StudentUpdate, StudentResponse,
    JobCreate, JobResponse, JobRankingResponse,
    AnalysisRequest, AnalysisResponse,
    HPPSScoreResponse, HealthResponse
)
from pipeline import analyze_student_complete
from tasks import analyze_student_task, match_job_task, analyze_student_sync
from job_matching_layer import process_job_profile
from config import Config
from logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("Starting HPPS API...")
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
    yield
    # Shutdown
    logger.info("Shutting down HPPS API...")


# Create FastAPI app
app = FastAPI(
    title=Config.PROJECT_NAME,
    version=Config.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    try:
        # Check database
        from database import engine
        with engine.connect() as conn:
            db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # Check Celery
    try:
        from tasks import CELERY_ENABLED
        celery_status = "enabled" if CELERY_ENABLED else "disabled"
    except Exception:
        celery_status = "unknown"
    
    return HealthResponse(
        status="healthy",
        version=Config.VERSION,
        database=db_status,
        celery=celery_status
    )


# Student endpoints
@app.post("/students", response_model=StudentResponse, status_code=201)
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    """Create a new student."""
    try:
        db_student = StudentDAO.create(
            db,
            **student.dict(exclude_none=True)
        )
        db.commit()
        db.refresh(db_student)
        return db_student
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating student: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/students/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    """Get student by ID."""
    student = StudentDAO.get_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.get("/students", response_model=List[StudentResponse])
def list_students(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """List all students."""
    students = StudentDAO.get_all(db, limit=limit, offset=offset)
    return students


@app.put("/students/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    student_update: StudentUpdate,
    db: Session = Depends(get_db)
):
    """Update student."""
    student = StudentDAO.update(
        db,
        student_id,
        **student_update.dict(exclude_none=True)
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.commit()
    db.refresh(student)
    return student


@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    """Delete student."""
    student = StudentDAO.delete(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.commit()


# HPPS Score endpoints
@app.get("/students/{student_id}/score", response_model=HPPSScoreResponse)
def get_student_score(student_id: int, db: Session = Depends(get_db)):
    """Get latest HPPS score for student."""
    score = HPPSScoreDAO.get_latest_by_student_id(db, student_id)
    if not score:
        raise HTTPException(status_code=404, detail="HPPS score not found")
    return score


@app.post("/students/{student_id}/analyze", response_model=AnalysisResponse)
def analyze_student(
    student_id: int,
    background_tasks: BackgroundTasks,
    async_mode: bool = True
):
    """Trigger analysis for a student."""
    try:
        if async_mode:
            # Run in background
            task = analyze_student_task.delay(student_id)
            return AnalysisResponse(
                success=True,
                student_id=student_id
            )
        else:
            # Run synchronously
            result = analyze_student_complete(student_id)
            return AnalysisResponse(
                success=result.get("success", False),
                student_id=student_id,
                hpps=result.get("hpps"),
                hpps_percentage=result.get("hpps_percentage"),
                sub_scores=result.get("sub_scores"),
                execution_time_seconds=result.get("execution_time_seconds"),
                error=result.get("error"),
                warnings=result.get("warnings")
            )
    except Exception as e:
        logger.error(f"Error triggering analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Job endpoints
@app.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    """Create a new job posting."""
    try:
        db_job = JobDAO.create(db, **job.dict(exclude_none=True))
        db.commit()
        db.refresh(db_job)
        return db_job
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job by ID."""
    job = JobDAO.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs/{job_id}/matches", response_model=JobRankingResponse)
def get_job_matches(job_id: int, db: Session = Depends(get_db)):
    """Get matched students for a job."""
    job = JobDAO.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        # Get all students with their data
        from models import Student, HPPSScore
        students_query = db.query(Student).join(HPPSScore).all()
        
        students_data = []
        for student in students_query:
            latest_score = max(
                student.hpps_scores,
                key=lambda s: s.calculated_at,
                default=None
            )
            
            students_data.append({
                "student_id": student.id,
                "name": student.name,
                "github_url": student.github_url,
                "general_score": latest_score.hpps if latest_score else 0.0,
                "skills": [],
                "tags": [],
                "languages": []
            })
        
        # Process job matching
        result = process_job_profile(
            job_description=job.description,
            students=students_data,
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Convert to response format
        general_ranking = []
        for item in result.get("general_ranking", []):
            general_ranking.append({
                "student_id": item["student_id"],
                "keyword_match_pct": item["keyword_match_pct"],
                "general_score": item["general_score"],
                "matched_keywords": item.get("matched_keywords", []),
                "unmatched_keywords": item.get("unmatched_keywords", [])
            })
        
        job_specific_ranking = []
        for item in result.get("job_specific_ranking", []):
            job_specific_ranking.append({
                "student_id": item["student_id"],
                "keyword_match_pct": item["keyword_match_pct"],
                "general_score": item["general_score"],
                "matched_keywords": item.get("matched_keywords", []),
                "unmatched_keywords": item.get("unmatched_keywords", [])
            })
        
        return JobRankingResponse(
            general_ranking=general_ranking,
            job_specific_ranking=job_specific_ranking
        )
        
    except Exception as e:
        logger.error(f"Error getting job matches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/{job_id}/match")
def trigger_job_matching(job_id: int, background_tasks: BackgroundTasks):
    """Trigger job matching (async)."""
    try:
        task = match_job_task.delay(job_id)
        return {"task_id": task.id, "status": "pending"}
    except Exception as e:
        logger.error(f"Error triggering job matching: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Task status endpoint
@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """Get task status."""
    try:
        from tasks import app as celery_app
        task = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": task.state,
            "result": task.result if task.ready() else None,
            "error": str(task.info) if task.failed() else None
        }
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=Config.API_RELOAD
    )

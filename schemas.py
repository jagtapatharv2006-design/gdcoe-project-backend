"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, HttpUrl, Field


class StudentCreate(BaseModel):
    """Schema for creating a student."""
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    github_url: Optional[str] = None
    cf_username: Optional[str] = None
    lc_username: Optional[str] = None


class StudentUpdate(BaseModel):
    """Schema for updating a student."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    github_url: Optional[str] = None
    cf_username: Optional[str] = None
    lc_username: Optional[str] = None
    cf_rating: Optional[float] = None
    lc_rating: Optional[float] = None


class StudentResponse(BaseModel):
    """Schema for student response."""
    id: int
    name: str
    email: Optional[str]
    github_url: Optional[str]
    cf_username: Optional[str]
    lc_username: Optional[str]
    cf_rating: Optional[float]
    lc_rating: Optional[float]
    general_score: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class HPPSScoreResponse(BaseModel):
    """Schema for HPPS score response."""
    id: int
    student_id: int
    hpps: float
    hpps_percentage: float
    AD: float
    EAP: float
    CCL: float
    LA: float
    calculated_at: datetime
    
    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    """Schema for creating a job."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    keywords: Optional[List[str]] = None
    job_role: Optional[str] = None


class JobResponse(BaseModel):
    """Schema for job response."""
    id: int
    title: str
    description: str
    keywords: Optional[List[str]]
    job_role: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class JobMatchResponse(BaseModel):
    """Schema for job match response."""
    student_id: int
    keyword_match_pct: float
    general_score: float
    matched_keywords: List[str]
    unmatched_keywords: List[str]


class JobRankingResponse(BaseModel):
    """Schema for job ranking response."""
    general_ranking: List[JobMatchResponse]
    job_specific_ranking: List[JobMatchResponse]


class AnalysisRequest(BaseModel):
    """Schema for analysis request."""
    student_id: int


class AnalysisResponse(BaseModel):
    """Schema for analysis response."""
    success: bool
    student_id: int
    hpps: Optional[float] = None
    hpps_percentage: Optional[float] = None
    sub_scores: Optional[Dict[str, float]] = None
    execution_time_seconds: Optional[float] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None


class TaskStatusResponse(BaseModel):
    """Schema for task status response."""
    task_id: str
    status: str  # PENDING, SUCCESS, FAILURE, RETRY
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    database: str
    celery: str

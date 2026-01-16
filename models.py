"""
SQLAlchemy ORM models for HPPS system.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Student(Base):
    """Student model."""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    github_url = Column(String(512), nullable=True, index=True)
    cf_username = Column(String(100), nullable=True)
    lc_username = Column(String(100), nullable=True)
    cf_rating = Column(Float, nullable=True)
    lc_rating = Column(Float, nullable=True)
    general_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    repositories = relationship("Repository", back_populates="student", cascade="all, delete-orphan")
    hpps_scores = relationship("HPPSScore", back_populates="student", cascade="all, delete-orphan")
    job_requests = relationship("JobRequest", back_populates="student", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_student_github", "github_url"),
        Index("idx_student_email", "email"),
    )


class Repository(Base):
    """Repository model."""
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    repo_url = Column(String(512), nullable=False)
    local_path = Column(String(1024), nullable=True)
    last_analyzed = Column(DateTime, nullable=True)
    analysis_status = Column(String(50), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    student = relationship("Student", back_populates="repositories")
    
    __table_args__ = (
        Index("idx_repo_student", "student_id"),
        Index("idx_repo_url", "repo_url"),
        Index("idx_repo_status", "analysis_status"),
    )


class Job(Base):
    """Job posting model."""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    keywords = Column(JSON, nullable=True)  # List of keywords
    job_role = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    job_requests = relationship("JobRequest", back_populates="job", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_job_title", "title"),
        Index("idx_job_role", "job_role"),
    )


class JobRequest(Base):
    """Job request/application model."""
    __tablename__ = "job_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="PENDING")  # PENDING, ACCEPTED, REJECTED
    keyword_match_pct = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    student = relationship("Student", back_populates="job_requests")
    job = relationship("Job", back_populates="job_requests")
    
    __table_args__ = (
        Index("idx_job_request_student_job", "student_id", "job_id"),
        Index("idx_job_request_status", "status"),
        Index("idx_job_request_match_pct", "keyword_match_pct"),
    )


class HPPSScore(Base):
    """HPPS score model."""
    __tablename__ = "hpps_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    hpps = Column(Float, nullable=False)  # 0-1 scale
    hpps_percentage = Column(Float, nullable=False)  # 0-100 scale
    AD = Column(Float, nullable=False)  # Algorithmic Depth
    EAP = Column(Float, nullable=False)  # Execution & Application Power
    CCL = Column(Float, nullable=False)  # Consistency & Career Longevity
    LA = Column(Float, nullable=False)  # Leverage & Adaptability
    calculated_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    student = relationship("Student", back_populates="hpps_scores")
    
    __table_args__ = (
        Index("idx_hpps_student", "student_id"),
        Index("idx_hpps_score", "hpps"),
        Index("idx_hpps_calculated_at", "calculated_at"),
    )


class AnalysisLog(Base):
    """Analysis log model for tracking analysis operations."""
    __tablename__ = "analysis_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True)
    analysis_type = Column(String(50), nullable=False)  # FULL, PARTIAL, UPDATE
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED, PARTIAL
    error_message = Column(Text, nullable=True)
    execution_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_analysis_log_student", "student_id"),
        Index("idx_analysis_log_repo", "repository_id"),
        Index("idx_analysis_log_status", "status"),
        Index("idx_analysis_log_created", "created_at"),
    )

"""
Database connection and session management for HPPS system.
"""

from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config import Config
from logger import logger
from models import (
    Base, Student, Repository, Job, JobRequest, HPPSScore, AnalysisLog
)

# Create engine based on database URL
def create_db_engine():
    """Create SQLAlchemy engine with appropriate configuration."""
    database_url = Config.get_database_url()
    
    # Special handling for SQLite
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=Config.DB_ECHO
        )
        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # PostgreSQL or other databases
        engine = create_engine(
            database_url,
            pool_size=Config.DB_POOL_SIZE,
            max_overflow=Config.DB_MAX_OVERFLOW,
            echo=Config.DB_ECHO
        )
    
    return engine


# Create engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database by creating all tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise


def get_db() -> Session:
    """
    Get database session (dependency for FastAPI).
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Session:
    """
    Context manager for database session.
    
    Usage:
        with get_db_session() as session:
            # Use session
            pass
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# CRUD Operations

class StudentDAO:
    """Data Access Object for Student operations."""
    
    @staticmethod
    def create(session: Session, **kwargs):
        """Create a new student."""
        student = Student(**kwargs)
        session.add(student)
        session.flush()
        return student
    
    @staticmethod
    def get_by_id(session: Session, student_id: int):
        """Get student by ID."""
        return session.query(Student).filter(Student.id == student_id).first()
    
    @staticmethod
    def get_by_email(session: Session, email: str):
        """Get student by email."""
        return session.query(Student).filter(Student.email == email).first()
    
    @staticmethod
    def get_by_github_url(session: Session, github_url: str):
        """Get student by GitHub URL."""
        return session.query(Student).filter(Student.github_url == github_url).first()
    
    @staticmethod
    def get_all(session: Session, limit: int = None, offset: int = 0):
        """Get all students with pagination."""
        query = session.query(Student)
        if limit:
            query = query.limit(limit).offset(offset)
        return query.all()
    
    @staticmethod
    def update(session: Session, student_id: int, **kwargs):
        """Update student."""
        student = StudentDAO.get_by_id(session, student_id)
        if student:
            for key, value in kwargs.items():
                if hasattr(student, key):
                    setattr(student, key, value)
            session.flush()
        return student
    
    @staticmethod
    def delete(session: Session, student_id: int):
        """Delete student."""
        student = StudentDAO.get_by_id(session, student_id)
        if student:
            session.delete(student)
            session.flush()
        return student


class RepositoryDAO:
    """Data Access Object for Repository operations."""
    
    @staticmethod
    def create(session: Session, **kwargs):
        """Create a new repository."""
        repo = Repository(**kwargs)
        session.add(repo)
        session.flush()
        return repo
    
    @staticmethod
    def get_by_id(session: Session, repo_id: int):
        """Get repository by ID."""
        return session.query(Repository).filter(Repository.id == repo_id).first()
    
    @staticmethod
    def get_by_student_id(session: Session, student_id: int):
        """Get repositories by student ID."""
        return session.query(Repository).filter(
            Repository.student_id == student_id
        ).all()
    
    @staticmethod
    def update(session: Session, repo_id: int, **kwargs):
        """Update repository."""
        repo = RepositoryDAO.get_by_id(session, repo_id)
        if repo:
            for key, value in kwargs.items():
                if hasattr(repo, key):
                    setattr(repo, key, value)
            session.flush()
        return repo


class JobDAO:
    """Data Access Object for Job operations."""
    
    @staticmethod
    def create(session: Session, **kwargs):
        """Create a new job."""
        job = Job(**kwargs)
        session.add(job)
        session.flush()
        return job
    
    @staticmethod
    def get_by_id(session: Session, job_id: int):
        """Get job by ID."""
        return session.query(Job).filter(Job.id == job_id).first()
    
    @staticmethod
    def get_all(session: Session, limit: int = None, offset: int = 0):
        """Get all jobs with pagination."""
        query = session.query(Job)
        if limit:
            query = query.limit(limit).offset(offset)
        return query.all()
    
    @staticmethod
    def update(session: Session, job_id: int, **kwargs):
        """Update job."""
        job = JobDAO.get_by_id(session, job_id)
        if job:
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            session.flush()
        return job


class HPPSScoreDAO:
    """Data Access Object for HPPS Score operations."""
    
    @staticmethod
    def create(session: Session, **kwargs):
        """Create a new HPPS score."""
        score = HPPSScore(**kwargs)
        session.add(score)
        session.flush()
        return score
    
    @staticmethod
    def get_latest_by_student_id(session: Session, student_id: int):
        """Get latest HPPS score for student."""
        return session.query(HPPSScore).filter(
            HPPSScore.student_id == student_id
        ).order_by(HPPSScore.calculated_at.desc()).first()
    
    @staticmethod
    def get_all_by_student_id(session: Session, student_id: int):
        """Get all HPPS scores for student."""
        return session.query(HPPSScore).filter(
            HPPSScore.student_id == student_id
        ).order_by(HPPSScore.calculated_at.desc()).all()


class JobRequestDAO:
    """Data Access Object for JobRequest operations."""
    
    @staticmethod
    def create(session: Session, **kwargs):
        """Create a new job request."""
        request = JobRequest(**kwargs)
        session.add(request)
        session.flush()
        return request
    
    @staticmethod
    def get_by_job_id(session: Session, job_id: int):
        """Get all job requests for a job."""
        return session.query(JobRequest).filter(
            JobRequest.job_id == job_id
        ).all()
    
    @staticmethod
    def get_by_student_id(session: Session, student_id: int):
        """Get all job requests for a student."""
        return session.query(JobRequest).filter(
            JobRequest.student_id == student_id
        ).all()


class AnalysisLogDAO:
    """Data Access Object for AnalysisLog operations."""
    
    @staticmethod
    def create(session: Session, **kwargs):
        """Create a new analysis log."""
        log = AnalysisLog(**kwargs)
        session.add(log)
        session.flush()
        return log

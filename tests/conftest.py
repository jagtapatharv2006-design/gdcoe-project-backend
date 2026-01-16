"""
Pytest configuration and fixtures for HPPS system tests.
"""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["GEMINI_API_KEY"] = "test_key"
os.environ["DEBUG"] = "True"

from models import Base
from database import SessionLocal, init_db


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def temp_repo_path():
    """Create a temporary directory for testing repository operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_student_data():
    """Sample student data for testing."""
    return {
        "name": "Test Student",
        "email": "test@example.com",
        "github_url": "https://github.com/testuser/testrepo",
        "cf_username": "testuser",
        "lc_username": "testuser"
    }


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "title": "Backend Developer",
        "description": "Looking for a Python backend developer with FastAPI experience.",
        "keywords": ["python", "fastapi", "backend"],
        "job_role": "Backend Developer"
    }

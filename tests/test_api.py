"""
API endpoint tests for HPPS system.
"""

import pytest
from fastapi.testclient import TestClient
from app import app
from database import StudentDAO, get_db
from tests.conftest import db_session, sample_student_data


@pytest.fixture
def client(db_session):
    """Create test client."""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_student(client, sample_student_data):
    """Test student creation endpoint."""
    response = client.post("/students", json=sample_student_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_student_data["name"]
    assert "id" in data


def test_get_student(client, db_session, sample_student_data):
    """Test getting a student."""
    # Create student first
    student = StudentDAO.create(db_session, **sample_student_data)
    db_session.commit()
    
    # Get student
    response = client.get(f"/students/{student.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student.id
    assert data["name"] == sample_student_data["name"]


def test_list_students(client, db_session, sample_student_data):
    """Test listing students."""
    # Create a student
    student = StudentDAO.create(db_session, **sample_student_data)
    db_session.commit()
    
    # List students
    response = client.get("/students")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

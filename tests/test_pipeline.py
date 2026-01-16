"""
Integration tests for pipeline module.
"""

import pytest
from database import StudentDAO, get_db_session
from pipeline import analyze_student_complete
from tests.conftest import db_session, sample_student_data


def test_analyze_student_complete_no_repo(db_session, sample_student_data):
    """Test analysis with no repository."""
    # Create student
    student = StudentDAO.create(db_session, **sample_student_data)
    db_session.commit()
    
    # Run analysis
    result = analyze_student_complete(student.id)
    
    # Check results
    assert result["success"] is False or result.get("hpps") is not None
    assert result["student_id"] == student.id


def test_student_creation(db_session, sample_student_data):
    """Test student creation."""
    student = StudentDAO.create(db_session, **sample_student_data)
    db_session.commit()
    
    assert student.id is not None
    assert student.name == sample_student_data["name"]
    assert student.email == sample_student_data["email"]

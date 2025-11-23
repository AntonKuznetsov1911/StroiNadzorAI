"""
Tests for database models
"""

import pytest
from datetime import datetime

from src.database.models import User, Request, Project, RequestType, UserRole, DefectSeverity


class TestUserModel:
    """Tests for User model"""

    def test_create_user(self, db_session):
        """Test user creation"""
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            role=UserRole.USER
        )

        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.total_requests == 0

    def test_user_defaults(self, db_session):
        """Test user default values"""
        user = User(telegram_id=123456789)

        db_session.add(user)
        db_session.commit()

        assert user.role == UserRole.USER
        assert user.language == "ru"
        assert user.total_requests == 0
        assert user.total_photos == 0
        assert user.total_voice == 0


class TestRequestModel:
    """Tests for Request model"""

    def test_create_request(self, db_session):
        """Test request creation"""
        # Create user first
        user = User(telegram_id=123456789)
        db_session.add(user)
        db_session.commit()

        # Create request
        request = Request(
            user_id=user.id,
            request_type=RequestType.TEXT,
            message_text="Test question",
            response_text="Test answer"
        )

        db_session.add(request)
        db_session.commit()

        assert request.id is not None
        assert request.user_id == user.id
        assert request.request_type == RequestType.TEXT

    def test_request_with_defect(self, db_session):
        """Test request with defect information"""
        user = User(telegram_id=123456789)
        db_session.add(user)
        db_session.commit()

        request = Request(
            user_id=user.id,
            request_type=RequestType.PHOTO,
            defect_type="трещина",
            defect_severity=DefectSeverity.CRITICAL,
            mentioned_regulations=["СП 63.13330.2018"]
        )

        db_session.add(request)
        db_session.commit()

        assert request.defect_type == "трещина"
        assert request.defect_severity == DefectSeverity.CRITICAL
        assert "СП 63.13330.2018" in request.mentioned_regulations


class TestProjectModel:
    """Tests for Project model"""

    def test_create_project(self, db_session):
        """Test project creation"""
        user = User(telegram_id=123456789)
        db_session.add(user)
        db_session.commit()

        project = Project(
            owner_id=user.id,
            name="Test Project",
            description="Test project description",
            address="Moscow, Russia"
        )

        db_session.add(project)
        db_session.commit()

        assert project.id is not None
        assert project.owner_id == user.id
        assert project.name == "Test Project"
        assert project.is_active is True

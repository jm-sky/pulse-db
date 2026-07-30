"""Pytest configuration and fixtures."""

import os

# CRITICAL: Set environment variables BEFORE any app imports
# This overrides .env file values for testing
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-min-32-characters-long-for-testing"
os.environ["ALLOWED_HOSTS"] = '["localhost","127.0.0.1"]'
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
# SQLite doesn't support pool_size/max_overflow, so disable them for tests
os.environ["DATABASE_POOL_SIZE"] = "1"
os.environ["DATABASE_MAX_OVERFLOW"] = "0"

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from main import app


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with a test database."""

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

"""Tests for the PulseDB detailed health endpoint (GET /api/health/details).

This endpoint has no database/ORM dependency (it uses a raw ``SELECT 1`` via
``AsyncSessionLocal``, not the ``get_db`` dependency), so tests use a plain
``TestClient`` instead of the shared ``client``/``db_session`` fixtures from
``conftest.py``.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from main import app

TEST_TOKEN = "test-health-details-token"


@pytest.fixture(name="client")
def client_fixture() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _health_details_test_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a known token and avoid real outbound calls to the frontend origin."""
    monkeypatch.setattr(settings.health, "details_token", TEST_TOKEN)
    monkeypatch.setattr(settings, "frontend_url", "http://127.0.0.1:9")


def test_health_details_requires_token(client: TestClient) -> None:
    """No Authorization header must be rejected."""
    response = client.get("/api/health/details")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_health_details_rejects_wrong_token(client: TestClient) -> None:
    """A malformed/incorrect bearer token must be rejected."""
    response = client.get(
        "/api/health/details",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_health_details_rejects_when_token_unconfigured(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unconfigured (empty) token must disable the endpoint, not open it."""
    monkeypatch.setattr(settings.health, "details_token", "")
    response = client.get(
        "/api/health/details",
        headers={"Authorization": "Bearer anything"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_health_details_returns_schema_with_valid_token(client: TestClient) -> None:
    """A valid token returns a response matching the pulse-db contract."""
    response = client.get(
        "/api/health/details",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["schema_version"] == 1
    assert data["status"] in ("ok", "degraded", "failed")
    assert "version" in data
    assert "environment" in data

    components = data["components"]
    for name in ("database", "cache", "storage", "frontend"):
        assert name in components
        assert components[name]["status"] in ("ok", "degraded", "failed")

    assert components["frontend"]["status"] == "failed"
    assert components["database"]["status"] == "ok"

"""Unit tests for CSRFMiddleware (double-submit cookie)."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.core.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, CSRFMiddleware


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/ping")
    async def ping() -> JSONResponse:
        return JSONResponse(content={"ok": True})

    @app.post("/api/mutate")
    async def mutate() -> JSONResponse:
        return JSONResponse(content={"ok": True})

    @app.post("/api/billing/webhook")
    async def stripe_webhook() -> JSONResponse:
        return JSONResponse(content={"received": True})

    app.add_middleware(CSRFMiddleware)
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)


def _csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/ping")
    assert response.status_code == status.HTTP_200_OK
    token = response.cookies.get(CSRF_COOKIE_NAME)
    assert token
    return {CSRF_HEADER_NAME: token}


class TestCSRFMiddleware:
    def test_get_issues_csrf_cookie(self, client: TestClient) -> None:
        response = client.get("/api/ping")
        assert response.status_code == status.HTTP_200_OK
        assert response.cookies.get(CSRF_COOKIE_NAME)

    def test_cross_origin_get_uses_cookie_attributes_accepted_by_browsers(self, client: TestClient) -> None:
        response = client.get(
            "/api/ping",
            headers={"Origin": "https://app.example.com"},
        )

        assert response.status_code == status.HTTP_200_OK
        set_cookie = response.headers.get("set-cookie", "")
        assert "SameSite=none" in set_cookie
        assert "Secure" in set_cookie

    def test_post_without_csrf_is_rejected(self, client: TestClient) -> None:
        response = client.post("/api/mutate", json={})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "CSRF token missing or invalid"

    def test_post_with_mismatched_csrf_is_rejected(self, client: TestClient) -> None:
        client.get("/api/ping")
        response = client.post(
            "/api/mutate",
            json={},
            headers={CSRF_HEADER_NAME: "not-the-cookie-value"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_with_valid_csrf_succeeds(self, client: TestClient) -> None:
        headers = _csrf_headers(client)
        response = client.post("/api/mutate", json={}, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True}

    def test_stripe_webhook_is_exempt(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # pulse-db has no billing module; WEBHOOK_PATHS defaults to [].
        monkeypatch.setattr(
            "app.core.csrf.WEBHOOK_PATHS",
            ["/api/billing/webhook"],
        )
        response = client.post("/api/billing/webhook", json={"type": "test"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"received": True}

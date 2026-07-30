"""Detailed health check for PulseDB.

Implements the response contract documented in pulse-db's
``docs/health-schema.md``: ``GET /api/health/details`` reports per-component
status (database, cache, storage, frontend) plus a top-level status that is
the worst of all components. Protected by a static bearer token
(``HEALTH_DETAILS_TOKEN``) so it can be exposed to PulseDB without being
fully public.
"""

import asyncio
import secrets
from typing import Literal

import httpx
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.core.storage.factory import get_storage_adapter

ComponentStatus = Literal["ok", "degraded", "failed"]

_CHECK_TIMEOUT_SECONDS = 3.0
_STATUS_SEVERITY: dict[ComponentStatus, int] = {"ok": 0, "degraded": 1, "failed": 2}

_health_details_security = HTTPBearer(auto_error=False)


async def verify_health_details_token(
    credentials: HTTPAuthorizationCredentials | None = Security(_health_details_security),
) -> None:
    """Require a valid ``Authorization: Bearer <token>`` header.

    Fails closed: an unconfigured (empty) token disables the endpoint rather
    than allowing an empty bearer token to match it.
    """
    expected = settings.health.details_token
    if not expected or not credentials or not secrets.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing health details token",
        )


async def _check_database() -> dict:
    try:
        async with AsyncSessionLocal() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=_CHECK_TIMEOUT_SECONDS)
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}


async def _check_cache() -> dict:
    try:
        client = await get_redis_client()
        await asyncio.wait_for(client.ping(), timeout=_CHECK_TIMEOUT_SECONDS)
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}


async def _check_storage() -> dict:
    storage_type = settings.storage.type
    try:
        if storage_type == "local":
            adapter = get_storage_adapter()
            await asyncio.wait_for(adapter.get_available_space(), timeout=_CHECK_TIMEOUT_SECONDS)
            return {"status": "ok"}

        if storage_type == "s3":
            import aioboto3

            session = aioboto3.Session()
            async with session.client(
                "s3",
                region_name=settings.storage.s3_region,
                aws_access_key_id=settings.storage.s3_access_key,
                aws_secret_access_key=settings.storage.s3_secret_key,
                endpoint_url=settings.storage.s3_endpoint_url,
            ) as s3:
                await asyncio.wait_for(
                    s3.head_bucket(Bucket=settings.storage.s3_bucket),
                    timeout=_CHECK_TIMEOUT_SECONDS,
                )
            return {"status": "ok"}

        return {"status": "failed", "reason": f"Unknown storage type: {storage_type}"}
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}


async def _check_frontend() -> dict:
    url = settings.frontend_url
    if not url:
        return {"status": "ok"}

    try:
        async with httpx.AsyncClient(timeout=_CHECK_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
        if response.status_code == 200:
            return {"status": "ok"}
        return {
            "status": "failed",
            "reason": f"HTTP {response.status_code} from frontend origin",
        }
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}


def _worst_status(statuses: list[ComponentStatus]) -> ComponentStatus:
    return max(statuses, key=lambda s: _STATUS_SEVERITY[s], default="ok")


async def build_health_details() -> dict:
    """Run all component checks concurrently and assemble the response."""
    database, cache, storage, frontend = await asyncio.gather(_check_database(), _check_cache(), _check_storage(), _check_frontend())

    components = {
        "database": database,
        "cache": cache,
        "storage": storage,
        "frontend": frontend,
    }

    overall = _worst_status([c["status"] for c in components.values()])

    return {
        "schema_version": 1,
        "status": overall,
        "version": settings.app.version,
        "environment": settings.app.environment.value,
        "components": components,
    }

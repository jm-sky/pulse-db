"""Main API router aggregating all module routers."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.core.health_details import build_health_details, verify_health_details_token
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.settings.router import router as settings_router
from app.modules.users.router import router as users_router

logger = logging.getLogger(__name__)

# Main API router
api_router = APIRouter()


# Health check endpoint
@api_router.get("/health", tags=["Health"])
async def health_check() -> dict:
    db_status = "ok"
    db_reason: str | None = None

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check database probe failed")
        db_status = "failed"
        # Do not leak exception details to clients
        db_reason = "unavailable"

    overall = db_status

    components: dict = {"database": {"status": db_status}}
    if db_reason:
        components["database"]["reason"] = db_reason

    return {"schema_version": 1, "status": overall, "components": components}


@api_router.get(
    "/health/details",
    tags=["Health"],
    dependencies=[Depends(verify_health_details_token)],
)
async def health_check_details() -> dict:
    """Detailed health check for peer monitoring / ops integrations."""
    return await build_health_details()


# Register module routers
api_router.include_router(admin_router)
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(settings_router, prefix="/me/settings", tags=["Settings"])

# Register Two-Factor module (optional, added during development)
try:
    from app.modules.two_factor.router import router as two_factor_router

    api_router.include_router(
        two_factor_router,
        prefix="/two-factor",
        tags=["Two-Factor Authentication", "Security", "WebAuthn", "TOTP"],
    )
except ImportError:
    # Module may be absent in some builds; ignore if not present
    pass

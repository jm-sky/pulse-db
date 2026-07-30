"""Application factory for creating FastAPI app instances."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.limiter import setup_limiter
from app.core.middleware import setup_middleware

logger = logging.getLogger(__name__)


def is_expected_auth_error(exc: BaseException) -> bool:
    """Return True for auth errors that are normal business outcomes, not bugs.

    Expired/invalid tokens and bad credentials are expected during normal use;
    they should not page anyone or clutter Sentry.
    """
    from app.modules.auth.exceptions import (
        ExpiredTokenError,
        InvalidCredentialsError,
        InvalidTokenError,
    )

    return isinstance(exc, (ExpiredTokenError, InvalidTokenError, InvalidCredentialsError))


def is_expected_image_error(exc: BaseException) -> bool:
    """Return True for image errors caused by bad user uploads, not bugs.

    Covers our own ``CorruptedImageError`` plus the ``OSError`` PIL raises for
    truncated / unidentifiable image files.
    """
    from app.core.storage.exceptions import CorruptedImageError

    if isinstance(exc, CorruptedImageError):
        return True
    if isinstance(exc, OSError):
        error_msg = str(exc).lower()
        return "truncated" in error_msg or "cannot identify" in error_msg
    return False


def is_expected_error(exc: BaseException) -> bool:
    """Return True for any error that is an expected business outcome, not a bug.

    Single source of truth shared by the Sentry ``before_send`` filter and the
    global exception handler so the "don't alert on this" policy can't drift
    between the two.
    """
    return is_expected_auth_error(exc) or is_expected_image_error(exc)


def init_sentry() -> None:
    """Initialize Sentry error monitoring if enabled."""
    if not settings.sentry.enabled or not settings.sentry.dsn:
        return

    try:
        from typing import Any

        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        def before_send(event: Any, hint: dict[str, Any]) -> Any:
            """Filter out expected errors that shouldn't be reported to Sentry."""
            # Get the exception from hint
            exc_info = hint.get("exc_info")
            if exc_info:
                _, exc_value, _ = exc_info

                # Don't send expected business-logic errors (expired/invalid tokens,
                # bad credentials, corrupted uploads) to Sentry. Shared policy with
                # the global exception handler via is_expected_error().
                if exc_value is not None and is_expected_error(exc_value):
                    return None

            # Check exception type from event data (fallback for cases where exc_info might not be available)
            if event.get("exception"):
                values = event["exception"].get("values", [])
                for value in values:
                    exc_type_name = value.get("type", "")
                    # Filter out JWT expiration and invalid token errors
                    if exc_type_name in (
                        "ExpiredTokenError",
                        "InvalidTokenError",
                        "InvalidCredentialsError",
                    ):
                        return None
                    # Filter out corrupted image errors
                    if exc_type_name == "CorruptedImageError":
                        return None
                    # Filter out OSError for truncated images
                    if exc_type_name == "OSError":
                        exc_value_str = str(value.get("value", "")).lower()
                        if "truncated" in exc_value_str or "cannot identify" in exc_value_str:
                            return None

            return event

        sentry_sdk.init(
            dsn=settings.sentry.dsn,
            environment=settings.sentry.environment or settings.app.environment.value,
            release=settings.sentry.release or settings.app.version,
            traces_sample_rate=settings.sentry.traces_sample_rate,
            profiles_sample_rate=settings.sentry.profiles_sample_rate,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoggingIntegration(level=None, event_level=logging.ERROR),
            ],
            # Set user context in middleware or route handlers
            send_default_pii=False,  # Don't send PII by default
            before_send=before_send,  # Filter out expected errors
        )
    except ImportError:
        logger.warning("Sentry SDK not installed. Install with: pip install sentry-sdk[fastapi]")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting application", extra={"environment": settings.app.environment})

    # Fail fast on insecure production configuration (no-op outside production).
    settings.validate_production()

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Close database connections
    try:
        from app.core.database import close_db

        await close_db()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Failed to close database connections: {e}")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application instance.

    Returns:
        Configured FastAPI application
    """
    # Initialize Sentry before creating app (to catch all errors)
    init_sentry()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        debug=settings.app.debug,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.is_development() else None,
        redoc_url="/api/redoc" if settings.is_development() else None,
        openapi_url="/api/openapi.json" if settings.is_development() else None,
    )

    # Setup rate limiting (must run before middleware/routers rely on app.state.limiter)
    setup_limiter(app)

    # Setup middleware
    setup_middleware(app)

    # Setup static file serving
    from app.core.static import setup_static_routes

    setup_static_routes(app)

    # Register exception handlers
    register_exception_handlers(app)

    # Register routers
    register_routers(app)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected errors."""
        # These are expected business logic errors, not bugs. Same policy the
        # Sentry before_send filter uses (see is_expected_error).
        expected_auth_error = is_expected_auth_error(exc)
        expected_image_error = is_expected_image_error(exc)

        if not expected_auth_error and not expected_image_error:
            logger.exception("Unhandled exception occurred")
        elif expected_auth_error:
            # Log expected auth errors at debug level (not error)
            logger.debug(f"Expected authentication error: {type(exc).__name__}: {exc}")
        elif expected_image_error:
            # Log expected image errors at warning level (user uploaded bad file)
            logger.warning(f"Corrupted image file: {type(exc).__name__}: {exc}")

        # Sentry will automatically capture exceptions, but we can add context
        # Skip Sentry for expected errors (they're filtered in before_send, but avoid unnecessary processing)
        if settings.sentry.enabled and not expected_auth_error and not expected_image_error:
            try:
                import sentry_sdk

                with sentry_sdk.push_scope() as scope:
                    scope.set_context(
                        "request",
                        {
                            "url": str(request.url),
                            "method": request.method,
                            "path": request.url.path,
                        },
                    )
                    scope.set_user({"id": getattr(request.state, "user_id", None)})
                    sentry_sdk.capture_exception(exc)
            except Exception:
                # Don't fail if Sentry fails
                pass

        if settings.is_development():
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": str(exc),
                    "type": type(exc).__name__,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            },
        )


def register_routers(app: FastAPI) -> None:
    """
    Register API routers.

    Args:
        app: FastAPI application instance
    """
    # Import and register module routers here
    try:
        from app.api.router import api_router

        app.include_router(api_router, prefix="/api", tags=["API"])
    except ImportError as e:
        logger.error(f"Failed to import API router: {e}", exc_info=True)
        raise

    @app.get("/", tags=["System"])
    async def root() -> dict:
        """Root endpoint."""
        return {
            "message": f"Welcome to {settings.app.name}",
            "version": settings.app.version,
            "docs": "/api/docs" if settings.is_development() else None,
        }

    @app.get("/health", tags=["System"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy"}

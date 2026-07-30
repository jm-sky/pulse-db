"""FastAPI application entry point."""

from app.core.app_factory import create_app
from app.core.config import settings
from app.core.logging_config import configure_logging

# Configure logging first
configure_logging()

# Create FastAPI application using factory pattern
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
    )

"""Static file serving configuration for SPA."""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

router = APIRouter()


def setup_static_routes(app: FastAPI) -> None:
    """
    Setup static file serving for Single Page Application.

    Mounts static asset directories if they exist.

    Args:
        app: FastAPI application instance
    """
    # Mount uploads directory for user-uploaded files (if using local storage)
    from app.core.config import settings

    if settings.storage.type == "local":
        uploads_path = Path(settings.storage.local_path)
        if uploads_path.exists():
            app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

    # Check if dist directory exists (for production builds)
    dist_path = Path("dist")

    if dist_path.exists():
        # Mount static files for assets and webfonts
        assets_path = dist_path / "assets"
        if assets_path.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

        webfonts_path = dist_path / "webfonts"
        if webfonts_path.exists():
            app.mount("/webfonts", StaticFiles(directory=str(webfonts_path)), name="webfonts")


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    """
    Serve favicon.

    Returns:
        Favicon file response
    """
    favicon_path = Path("dist/favicon.ico")
    if favicon_path.exists():
        return FileResponse(str(favicon_path))

    # Return 404 if favicon doesn't exist
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Favicon not found")


@router.get("/{path:path}", include_in_schema=False, response_model=None)
async def spa_handler(path: str) -> FileResponse | dict[str, str]:
    """
    Catch-all route for SPA.

    Serves index.html for any non-API routes to enable client-side routing.

    Args:
        path: Request path

    Returns:
        index.html file response or error message
    """
    index_path = Path("dist/index.html")
    if index_path.exists():
        return FileResponse(str(index_path))

    return {"message": "Frontend not built. Run 'npm run build' in frontend directory."}

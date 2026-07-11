from fastapi import APIRouter, Request

from app.config import GITHUB_REPOSITORY, settings

router = APIRouter()


@router.get("/api/info")
async def info(request: Request) -> dict:
    """Public application metadata consumed by the About page."""
    return {
        "version": request.app.version,
        "github": f"https://github.com/{GITHUB_REPOSITORY}",
        "github_repository": GITHUB_REPOSITORY,
        "issues_url": f"https://github.com/{GITHUB_REPOSITORY}/issues/new",
        "swagger_enabled": settings.swagger_enabled,
        "docs_url": "/api/docs" if settings.swagger_enabled else None,
        "health_url": "/api/health",
        "api_keys_enabled": settings.api_keys_enabled,
    }

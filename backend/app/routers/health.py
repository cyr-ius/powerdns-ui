from fastapi import APIRouter, Request

from app.config import GITHUB_REPOSITORY

router = APIRouter()


@router.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/api/info")
async def info(request: Request) -> dict:
    return {
        "version": request.app.version,
        "github": f"https://github.com/{GITHUB_REPOSITORY}",
        "github_repository": GITHUB_REPOSITORY,
        "docs_url": "/api/docs",
    }

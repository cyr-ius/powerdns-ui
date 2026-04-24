from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/api/info")
async def info(request: Request) -> dict:
    return {
        "version": request.app.version,
        "github": "https://github.com/cyr-ius/powerdns-ui",
        "docs_url": "/api/docs",
    }

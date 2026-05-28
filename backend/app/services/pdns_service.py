from typing import Any

import httpx

from app.config import settings


def _pdns_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=f"{settings.pdns_auth_api_url}/api/v1",
        headers={"X-API-Key": settings.pdns_auth_api_key},
        timeout=30.0,
    )


async def pdns_request(method: str, path: str, **kwargs: Any) -> Any:
    async with _pdns_client() as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        if not resp.content or resp.status_code == 204:
            return {}
        return resp.json()


async def pdns_request_text(method: str, path: str, **kwargs: Any) -> str:
    async with _pdns_client() as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.text


async def pdns_request_root(path: str) -> Any:
    """Requête vers pdns sans le préfixe /v1 (ex: /api)."""
    async with httpx.AsyncClient(
        base_url=settings.pdns_auth_api_url,
        headers={"X-API-Key": settings.pdns_auth_api_key},
        timeout=30.0,
    ) as client:
        resp = await client.get(path)
        resp.raise_for_status()
        return resp.json()

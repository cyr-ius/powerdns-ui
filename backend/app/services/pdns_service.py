from typing import Any

import httpx

from app.config import settings

_API_PREFIX = "/api/v1"

# One client per process, opened by the application lifespan, so the
# connections to the PowerDNS API are pooled and reused between requests.
_client: httpx.AsyncClient | None = None


async def open_client() -> None:
    """Create the shared PowerDNS API client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.pdns_auth_api_url,
            headers={"X-API-Key": settings.pdns_auth_api_key},
            timeout=30.0,
        )


async def close_client() -> None:
    """Close the shared PowerDNS API client and its connections."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _get_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("PowerDNS API client is not open")
    return _client


async def pdns_request(method: str, path: str, **kwargs: Any) -> Any:
    resp = await _get_client().request(method, f"{_API_PREFIX}{path}", **kwargs)
    resp.raise_for_status()
    if not resp.content or resp.status_code == 204:
        return {}
    return resp.json()


async def pdns_request_text(method: str, path: str, **kwargs: Any) -> str:
    resp = await _get_client().request(method, f"{_API_PREFIX}{path}", **kwargs)
    resp.raise_for_status()
    return resp.text


async def pdns_request_root(path: str) -> Any:
    """Request to pdns without the /v1 prefix (e.g. /api)."""
    resp = await _get_client().get(path)
    resp.raise_for_status()
    return resp.json()

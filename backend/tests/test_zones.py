import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.routers.zones import operations
from app.routers.zones.access import check_zone_id
from app.services import pdns_service


@pytest.mark.parametrize(
    ("zone_id", "valid"),
    [
        ("example.org.", True),
        ("0=2F26.2.0.192.in-addr.arpa.", True),  # RFC 2317 zone, "/" escaped
        ("example.org..internal", True),  # zone variant of a view
        ("..", False),  # would reach /servers/localhost
        (".", False),
        ("example org.", False),
    ],
)
def test_check_zone_id(zone_id: str, valid: bool) -> None:
    if valid:
        check_zone_id(zone_id)
    else:
        with pytest.raises(HTTPException) as exc:
            check_zone_id(zone_id)
        assert exc.value.status_code == 422


def test_import_rejects_a_too_large_zone_file(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def pdns(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, json={"name": "example.org.", "rrsets": []})

    monkeypatch.setattr(operations, "MAX_ZONE_FILE_SIZE", 16)
    admin = User(id=1, username="root", is_admin=True)
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        with TestClient(app) as client:
            monkeypatch.setattr(
                pdns_service,
                "_client",
                httpx.AsyncClient(
                    base_url="http://pdns.test", transport=httpx.MockTransport(pdns)
                ),
            )
            files = {"file": ("example.org.zone", b"x" * 17, "text/plain")}
            response = client.post("/api/zones/example.org./import", files=files)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413
    # The zone was read for the access check, but nothing was written.
    assert calls == ["GET /api/v1/servers/localhost/zones/example.org."]

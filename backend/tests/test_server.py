import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.services import pdns_service


def _get_status(
    monkeypatch: pytest.MonkeyPatch, user: User | None, pdns_status: int
) -> httpx.Response:
    def pdns(request: httpx.Request) -> httpx.Response:
        return httpx.Response(pdns_status, json={"version": "5.0.1"})

    # Credentials in the URL must never reach the browser.
    monkeypatch.setattr(
        settings, "pdns_auth_api_url", "http://user:secret@pdns.test:8081/"
    )
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            monkeypatch.setattr(
                pdns_service,
                "_client",
                httpx.AsyncClient(
                    base_url="http://pdns.test", transport=httpx.MockTransport(pdns)
                ),
            )
            return client.get("/api/server/status")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("is_admin", "pdns_status", "expected"),
    [
        (
            True,
            200,
            {"connected": True, "version": "5.0.1", "url": "http://pdns.test:8081/"},
        ),
        (False, 200, {"connected": True, "version": "5.0.1", "url": None}),
        (False, 503, {"connected": False, "version": None, "url": None}),
    ],
)
def test_server_status(
    monkeypatch: pytest.MonkeyPatch,
    is_admin: bool,
    pdns_status: int,
    expected: dict[str, object],
) -> None:
    user = User(id=1, username="user", is_admin=is_admin)
    response = _get_status(monkeypatch, user, pdns_status)
    assert response.status_code == 200
    assert response.json() == expected


def test_server_status_requires_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _get_status(monkeypatch, None, 200).status_code == 401

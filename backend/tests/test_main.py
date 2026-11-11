"""Tests of the Angular SPA serving."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main
from app.main import app as fastapi_app


@pytest.mark.parametrize(
    ("path", "cache_control"),
    [
        # Same URL across releases: a stale copy mixes old translations and new code.
        ("i18n/en.json", "no-cache"),
        ("zones/example.com", "no-cache"),
        ("main-B5zA5YFy.js", "public, max-age=31536000, immutable"),
    ],
)
def test_spa_cache_control(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, path: str, cache_control: str
) -> None:
    (tmp_path / "i18n").mkdir()
    (tmp_path / "i18n" / "en.json").write_text("{}")
    (tmp_path / "main-B5zA5YFy.js").write_text("")
    (tmp_path / "index.html").write_text("<html></html>")
    monkeypatch.setattr(app.main, "_FRONTEND_DIST", tmp_path)
    monkeypatch.setattr(app.main, "_FRONTEND_INDEX", tmp_path / "index.html")

    with TestClient(fastapi_app) as client:
        response = client.get(f"/{path}")

    assert response.status_code == 200
    assert response.headers["cache-control"] == cache_control

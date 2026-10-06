"""Phase 27: the UI files are revalidated on every load, so an upgrade never shows a half-old interface."""

from fastapi.testclient import TestClient

from app.main import app


def test_static_files_must_revalidate_and_still_answer_304():
    client = TestClient(app)
    first = client.get("/static/css/style.css")
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-cache"
    etag = first.headers["etag"]
    again = client.get("/static/css/style.css", headers={"if-none-match": etag})
    assert again.status_code == 304 and again.headers["cache-control"] == "no-cache"
    assert client.get("/static/js/api.js").headers["cache-control"] == "no-cache"
    assert client.get("/static/brand/logo-64.png").headers["cache-control"] == "no-cache"


def test_pages_are_revalidated_too():
    client = TestClient(app)
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/music").headers["cache-control"] == "no-cache"

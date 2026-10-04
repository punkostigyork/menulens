import asyncio
import io
from unittest.mock import patch
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.main import app
from app.models.menu import Menu
from app.core.errors import ServiceError
from app.core.upload_limit import UploadLimitMiddleware
from app.services.menu_service import save_menu

# Signature checks are upload validation only; full document decoding is Phase 3.
PDF = b"%PDF-1.4\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\nexample"
JPG = b"\xff\xd8\xffexample"


def count(engine):
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(Menu))


@pytest.mark.parametrize("name,body,mime", [("menu.pdf", PDF, "application/pdf"), ("menu.PNG", PNG, "image/png"), ("menu.jpeg", JPG, "image/jpeg"), ("menu.jpg", JPG, "application/octet-stream")])
def test_upload_and_retrieve(database, name, body, mime):
    engine, settings = database
    with TestClient(app) as client:
        response = client.post("/api/menus", files={"file": (name, body, mime)})
        assert response.status_code == 201, response.text
        menu = response.json()
        assert menu["status"] == "uploaded"
        assert menu["original_filename"] == name
        assert menu["processed_at"] is None
        UUID(menu["id"])
        UUID(menu["stored_filename"].split(".")[0])
        assert (settings.upload_dir / menu["stored_filename"]).read_bytes() == body
        assert client.get(f"/api/menus/{menu['id']}").json()["stored_filename"] == menu["stored_filename"]
        assert count(engine) == 1


@pytest.mark.parametrize("name,body,mime,code", [
    ("menu.txt", b"test", "text/plain", 415),
    ("menu.pdf", b"", "application/pdf", 400),
    ("menu.pdf", PDF, "image/png", 415),
    ("menu.pdf", b"not a pdf", "application/pdf", 415),
    ("menu.png", JPG, "image/png", 415),
    ("menu.pdf", PDF + b"x" * 1024, "application/pdf", 413),
    ("x" * 256 + ".pdf", PDF, "application/pdf", 400),
])
def test_rejected_uploads_leave_no_files_or_records(database, name, body, mime, code):
    engine, settings = database
    with TestClient(app) as client:
        response = client.post("/api/menus", files={"file": (name, body, mime)})
        assert response.status_code == code, response.text
        assert isinstance(response.json()["detail"], str)
        assert count(engine) == 0
        assert not list(settings.upload_dir.glob("*"))


def test_safe_unique_names(database):
    _, settings = database
    with TestClient(app) as client:
        items = [client.post("/api/menus", files={"file": ("../../menu.pdf", PDF, "application/pdf")}).json() for _ in range(2)]
        assert items[0]["stored_filename"] != items[1]["stored_filename"]
        assert all(item["original_filename"] == "menu.pdf" for item in items)
        assert len(list(settings.upload_dir.glob("*.pdf"))) == 2


def test_database_failure_cleans_up(database):
    engine, settings = database
    with TestClient(app) as client, patch("sqlalchemy.orm.Session.commit", side_effect=OperationalError("private", {}, Exception("secret"))):
        response = client.post("/api/menus", files={"file": ("menu.pdf", PDF, "application/pdf")})
        assert response.status_code == 503
        assert "secret" not in response.text
        assert not list(settings.upload_dir.glob("*"))
        assert count(engine) == 0


def test_disk_failure(database):
    engine, settings = database
    settings.upload_dir.write_text("not a directory")
    with TestClient(app) as client:
        response = client.post("/api/menus", files={"file": ("menu.pdf", PDF, "application/pdf")})
        assert response.status_code == 503
        assert count(engine) == 0


def test_metadata_not_found_and_validation(database):
    with TestClient(app) as client:
        assert client.get(f"/api/menus/{uuid4()}").status_code == 404
        assert client.get("/api/menus/not-a-uuid").status_code == 422
        assert client.post("/api/menus").status_code == 422
        assert client.get("/api/menus/upload-config").json() == {"max_upload_bytes": 1024}


def test_exact_size_limit(database):
    _, settings = database
    with TestClient(app) as client:
        body = PDF + b"x" * (settings.max_upload_bytes - len(PDF))
        assert client.post("/api/menus", files={"file": ("menu.pdf", body, "application/pdf")}).status_code == 201


def test_body_limit_handles_chunked_requests():
    async def run():
        called = False
        async def downstream(scope, receive, send):
            nonlocal called
            called = True
        messages = iter([{"type": "http.request", "body": b"1234", "more_body": True}, {"type": "http.request", "body": b"5678", "more_body": False}])
        responses = []
        async def receive(): return next(messages)
        async def send(message): responses.append(message)
        await UploadLimitMiddleware(downstream, max_bytes=5)({"type": "http", "method": "POST", "path": "/api/menus", "headers": []}, receive, send)
        assert not called
        assert responses[0]["status"] == 413
    asyncio.run(run())


def test_declared_body_limit(database):
    with TestClient(app) as client:
        response = client.post("/api/menus", content=b"", headers={"Content-Length": str(200 * 1024 * 1024)})
        assert response.status_code == 413

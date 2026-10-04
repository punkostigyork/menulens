import base64
import io
from pathlib import Path
from uuid import uuid4
import pytest
import pymupdf
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.core.errors import ServiceError
from app.main import app
from app.schemas.document import PreparedDocument
from app.services.document_service import prepare_document


@pytest.fixture
def settings(tmp_path):
    return Settings(upload_dir=tmp_path, max_upload_bytes=10 * 1024 * 1024)


def picture(fmt="PNG", size=(400, 300), orientation=None):
    image = Image.new("RGB", size, "white")
    ImageDraw.Draw(image).text((20, 20), "Gulyasleves 2990 HUF", fill="black")
    output = io.BytesIO()
    exif = Image.Exif()
    if orientation:
        exif[274] = orientation
    image.save(output, format=fmt, exif=exif)
    return output.getvalue()


def pdf_file(path, kinds, encrypted=False):
    with pymupdf.open() as doc:
        for kind in kinds:
            page = doc.new_page(width=400, height=500)
            if kind in ("text", "hybrid"):
                page.insert_text((20, 35), "Hungarian menu\nGulyasleves 2990 HUF\nCsirkepaprikas 4590 HUF")
            if kind in ("scan", "hybrid"):
                page.insert_image(pymupdf.Rect(0, 100, 400, 500), stream=picture())
            if kind == "sparse":
                page.insert_text((20, 35), "Menu")
        if encrypted:
            doc.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="reader")
        else:
            doc.save(path)
    return path


def test_digital_pdf(settings):
    path = pdf_file(settings.upload_dir / "menu.pdf", ["text"])
    original = path.read_bytes()
    result = prepare_document(path, "application/pdf", settings)
    assert result.mode == "text"
    assert "Gulyasleves 2990 HUF" in result.pages[0].text
    assert path.read_bytes() == original
    assert PreparedDocument.model_validate_json(result.model_dump_json()).mode == "text"


@pytest.mark.parametrize("kinds,mode,types", [(["scan"], "images", ["image"]), (["text", "scan"], "mixed", ["text", "image"]), (["hybrid"], "images", ["image"]), (["sparse"], "images", ["image"])])
def test_visual_and_mixed_pdf(settings, kinds, mode, types):
    path = pdf_file(settings.upload_dir / "menu.pdf", kinds)
    result = prepare_document(path, "application/pdf", settings)
    assert result.mode == mode
    assert [p.kind for p in result.pages] == types
    assert [p.page_number for p in result.pages] == list(range(1, len(kinds) + 1))
    for page in result.pages:
        if page.kind == "image":
            image = Image.open(io.BytesIO(base64.b64decode(page.data_base64)))
            assert image.format == "PNG" and image.mode == "RGB"
            assert max(image.size) <= settings.document_image_edge
            if kinds == ["hybrid"]:
                assert "Gulyasleves" in page.extracted_text


def test_blank_pages_are_reported(settings):
    result = prepare_document(pdf_file(settings.upload_dir / "menu.pdf", ["blank", "text"]), "application/pdf", settings)
    assert result.page_count == 2
    assert result.skipped_blank_pages == [1]
    assert result.pages[0].page_number == 2


@pytest.mark.parametrize("fmt,mime,suffix", [("PNG", "image/png", "png"), ("JPEG", "image/jpeg", "jpg")])
def test_images(settings, fmt, mime, suffix):
    path = settings.upload_dir / f"image.{suffix}"
    path.write_bytes(picture(fmt, (2000, 1000)))
    result = prepare_document(path, mime, settings)
    assert result.mode == "images"
    assert result.pages[0].width == 1600
    assert result.pages[0].height == 800


def test_exif_orientation(settings):
    path = settings.upload_dir / "image.jpg"
    path.write_bytes(picture("JPEG", orientation=6))
    page = prepare_document(path, "image/jpeg", settings).pages[0]
    assert (page.width, page.height) == (300, 400)


@pytest.mark.parametrize("body,mime", [(b"%PDF-broken", "application/pdf"), (b"\x89PNG\r\n\x1a\nbroken", "image/png"), (b"\xff\xd8\xffbroken", "image/jpeg")])
def test_corrupt_files(settings, body, mime):
    path = settings.upload_dir / "bad"
    path.write_bytes(body)
    with pytest.raises(ServiceError) as error:
        prepare_document(path, mime, settings)
    assert error.value.status_code == 422


def test_blank_and_locked_pdf(settings):
    for kind in ("blank", "locked"):
        path = pdf_file(settings.upload_dir / f"{kind}.pdf", ["blank" if kind == "blank" else "text"], encrypted=kind == "locked")
        with pytest.raises(ServiceError) as error:
            prepare_document(path, "application/pdf", settings)
        assert error.value.status_code == 422


def test_blank_image(settings):
    path = settings.upload_dir / "blank.png"
    Image.new("RGB", (100, 100), "white").save(path)
    with pytest.raises(ServiceError, match="blank"):
        prepare_document(path, "image/png", settings)


def test_page_text_pixel_and_output_limits(settings):
    path = pdf_file(settings.upload_dir / "menu.pdf", ["text", "scan"])
    for override in ({"document_max_pages": 1}, {"document_max_text_chars": 10}, {"document_max_output_bytes": 10}):
        with pytest.raises(ServiceError) as error:
            prepare_document(path, "application/pdf", settings.model_copy(update=override))
        assert error.value.status_code == 413
    path = settings.upload_dir / "menu.png"
    path.write_bytes(picture())
    with pytest.raises(ServiceError) as error:
        prepare_document(path, "image/png", settings.model_copy(update={"document_max_image_pixels": 10}))
    assert error.value.status_code == 413


def test_missing_source(settings):
    with pytest.raises(ServiceError) as error:
        prepare_document(settings.upload_dir / "missing.pdf", "application/pdf", settings)
    assert error.value.status_code == 503


def test_api_prepares_saved_upload_without_changing_menu_status(database, tmp_path):
    _, settings = database
    settings.max_upload_bytes = 10 * 1024 * 1024
    path = pdf_file(tmp_path / "source.pdf", ["text", "scan"])
    with TestClient(app) as client:
        uploaded = client.post("/api/menus", files={"file": ("source.pdf", path.read_bytes(), "application/pdf")})
        assert uploaded.status_code == 201
        menu_id = uploaded.json()["id"]
        prepared = client.post(f"/api/menus/{menu_id}/prepare")
        assert prepared.status_code == 200, prepared.text
        assert prepared.json()["mode"] == "mixed"
        metadata = client.get(f"/api/menus/{menu_id}").json()
        assert metadata["status"] == "uploaded" and metadata["processed_at"] is None
        assert client.post(f"/api/menus/{uuid4()}/prepare").status_code == 404
        (settings.upload_dir / metadata["stored_filename"]).unlink()
        assert client.post(f"/api/menus/{menu_id}/prepare").status_code == 503


def test_api_clean_error_for_corruption(database):
    with TestClient(app) as client:
        menu = client.post("/api/menus", files={"file": ("bad.pdf", b"%PDF-broken", "application/pdf")}).json()
        response = client.post(f"/api/menus/{menu['id']}/prepare")
        assert response.status_code == 422
        assert "could not be read" in response.json()["detail"]


def test_rejects_mislabeled_and_animated_images(settings):
    path = settings.upload_dir / "menu.png"
    path.write_bytes(picture("JPEG"))
    with pytest.raises(ServiceError, match="format"):
        prepare_document(path, "image/png", settings)
    first = Image.new("RGB", (40, 40), "white")
    second = Image.new("RGB", (40, 40), "black")
    first.save(path, format="PNG", save_all=True, append_images=[second], duration=100)
    with pytest.raises(ServiceError, match="still image"):
        prepare_document(path, "image/png", settings)


def test_image_output_and_source_size_limits(settings):
    path = settings.upload_dir / "menu.png"
    path.write_bytes(picture())
    for override in ({"document_max_output_bytes": 10}, {"max_upload_bytes": 10}):
        with pytest.raises(ServiceError) as error:
            prepare_document(path, "image/png", settings.model_copy(update=override))
        assert error.value.status_code == 413


def test_storage_path_escape_is_rejected(database, tmp_path):
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from app.models.menu import Menu
    engine, _ = database
    outside = tmp_path / "outside.pdf"
    pdf_file(outside, ["text"])
    with TestClient(app) as client:
        menu = client.post("/api/menus", files={"file": ("menu.pdf", b"%PDF-placeholder", "application/pdf")}).json()
        with Session(engine) as session:
            row = session.scalar(select(Menu))
            row.stored_filename = "../outside.pdf"
            session.commit()
        response = client.post(f"/api/menus/{menu['id']}/prepare")
        assert response.status_code == 503

import logging
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.errors import ServiceError
from app.models.menu import Menu
from app.schemas.menu import MenuRead
from app.schemas.document import PreparedDocument

logger = logging.getLogger(__name__)
TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def detected_type(header: bytes) -> str | None:
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None


def save_menu(stream: BinaryIO, filename: str | None, content_type: str | None, session: Session, settings: Settings) -> MenuRead:
    # Original name is display metadata only, never a filesystem path.
    original = (filename or "").replace("\\", "/").split("/")[-1]
    if not original or len(original) > 255 or any(ord(c) < 32 for c in original):
        raise ServiceError(400, "Please use a filename between 1 and 255 characters without control characters.")
    extension = Path(original).suffix.lower()
    expected = TYPES.get(extension)
    if expected is None:
        raise ServiceError(415, "Choose a PDF, JPG, JPEG, or PNG file.")
    if content_type not in (None, "", "application/octet-stream", expected):
        raise ServiceError(415, "The file type does not match its extension.")
    header = stream.read(16)
    if not header:
        raise ServiceError(400, "This file is empty. Please choose another menu.")
    if detected_type(header) != expected:
        raise ServiceError(415, "This file does not appear to be a supported PDF or image.")
    stream.seek(0)
    stored = f"{uuid4().hex}{'.jpg' if extension == '.jpeg' else extension}"
    destination = settings.upload_dir / stored
    created = False
    try:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            created = True
            total = 0
            while chunk := stream.read(64 * 1024):
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise ServiceError(413, "This menu is too large. Choose a file within the upload limit.")
                output.write(chunk)
        menu = Menu(original_filename=original, stored_filename=stored, content_type=expected, status="uploaded")
        session.add(menu)
        session.flush()
        # Serialize before committing to avoid a second query after commit.
        result = MenuRead.model_validate(menu)
        session.commit()
    except Exception as exc:
        session.rollback()
        if created:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                logger.error("menu_upload_cleanup_failed")
        if isinstance(exc, ServiceError):
            raise
        if isinstance(exc, (OSError, SQLAlchemyError)):
            logger.error("menu_upload_failed")
            raise ServiceError(503, "We couldn't save your menu. Please try again.") from None
        raise
    logger.info("menu_uploaded menu_id=%s", result.id)
    return result


def get_menu(menu_id: UUID, session: Session) -> MenuRead:
    try:
        menu = session.get(Menu, menu_id)
        if menu is None:
            raise ServiceError(404, "Menu not found.")
        return MenuRead.model_validate(menu)
    except SQLAlchemyError:
        logger.error("menu_read_failed")
        raise ServiceError(503, "We couldn't load your menu. Please try again.") from None


def prepare_menu(menu_id: UUID, session: Session, settings: Settings) -> "PreparedDocument":
    from app.services.document_service import prepare_document
    menu = get_menu(menu_id, session)
    root = settings.upload_dir.resolve()
    path = (root / menu.stored_filename).resolve()
    if path.parent != root:
        raise ServiceError(503, "The saved menu file is unavailable.")
    logger.info("menu_document_preparation_started menu_id=%s", menu_id)
    try:
        result = prepare_document(path, menu.content_type, settings)
    except ServiceError:
        logger.warning("menu_document_preparation_failed menu_id=%s", menu_id)
        raise
    logger.info("menu_document_preparation_completed menu_id=%s mode=%s", menu_id, result.mode)
    return result

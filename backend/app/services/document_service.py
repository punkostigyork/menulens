import base64
import io
import logging
import threading
from pathlib import Path
import pymupdf
from PIL import Image, ImageOps, UnidentifiedImageError
from app.core.config import Settings
from app.core.errors import ServiceError
from app.schemas.document import ImagePage, PreparedDocument, TextPage

logger = logging.getLogger(__name__)
# PyMuPDF does not support concurrent threads. Serialize its use in this process.
_pdf_lock = threading.Lock()


def clean_text(text: str) -> str:
    return "\n".join(" ".join("".join(c for c in line if c.isprintable() or c == "\t").split()) for line in text.splitlines()).strip()


def useful_text(text: str) -> bool:
    # Conservative heuristic; sparse or garbled text falls back to a visual input.
    return sum(c.isalnum() for c in text) >= 20 and len(text.split()) >= 3 and text.count("\ufffd") / max(len(text), 1) < 0.05


def image_page(image: Image.Image, page_number: int, settings: Settings, text: str = "") -> ImagePage | None:
    image = ImageOps.exif_transpose(image)
    image.thumbnail((settings.document_image_edge, settings.document_image_edge))
    rgba = image.convert("RGBA")
    canvas = Image.new("RGBA", rgba.size, "white")
    canvas.alpha_composite(rgba)
    rgb = canvas.convert("RGB")
    # Only reject completely uniform images, not low-contrast scans.
    if all(low == high for low, high in rgb.getextrema()):
        return None
    output = io.BytesIO()
    rgb.save(output, format="PNG")
    return ImagePage(page_number=page_number, width=rgb.width, height=rgb.height,
                     data_base64=base64.b64encode(output.getvalue()).decode("ascii"), extracted_text=text)


def prepare_image(path: Path, content_type: str, settings: Settings) -> PreparedDocument:
    try:
        with Image.open(path) as image:
            expected = {"image/jpeg": "JPEG", "image/png": "PNG"}[content_type]
            if image.format != expected:
                raise ServiceError(422, "The image format does not match the uploaded file type.")
            if image.width * image.height > settings.document_max_image_pixels:
                raise ServiceError(413, "This image has too many pixels. Please resize it and upload again.")
            if getattr(image, "n_frames", 1) != 1:
                raise ServiceError(422, "Please upload a single still image, not an animated image.")
            image.verify()
        with Image.open(path) as image:
            image.load()
            page = image_page(image, 1, settings)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ServiceError(413, "This image is too large to process. Please resize it.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ServiceError(422, "This image could not be read. Please upload a valid JPG or PNG.") from None
    if page is None:
        raise ServiceError(422, "This image appears blank. Please upload a visible menu.")
    return PreparedDocument(page_count=1, pages=[page])


def prepare_pdf(path: Path, settings: Settings) -> PreparedDocument:
    with _pdf_lock:
        try:
            with pymupdf.open(path) as document:
                if not document.is_pdf:
                    raise ServiceError(422, "This file is not a readable PDF.")
                if document.needs_pass:
                    raise ServiceError(422, "This PDF is password-protected. Please upload an unlocked copy.")
                if not document.page_count:
                    raise ServiceError(422, "This PDF has no pages.")
                if document.page_count > settings.document_max_pages:
                    raise ServiceError(413, f"This PDF has too many pages. The limit is {settings.document_max_pages}.")
                pages = []
                skipped = []
                text_chars = 0
                image_bytes = 0
                for number, page in enumerate(document, 1):
                    text = clean_text(page.get_text("text", sort=True))
                    text_chars += len(text)
                    if text_chars > settings.document_max_text_chars:
                        raise ServiceError(413, "This document contains too much text. Please split it into smaller files.")
                    # A substantial embedded image may contain menu text, even with a text header.
                    area = page.rect.get_area()
                    if area <= 0:
                        raise ServiceError(422, "This PDF contains an invalid page size.")
                    has_large_image = any((pymupdf.Rect(info["bbox"]) & page.rect).get_area() / area >= 0.25 for info in page.get_image_info())
                    if useful_text(text) and not has_large_image:
                        pages.append(TextPage(page_number=number, text=text))
                        continue
                    scale = min(150 / 72, settings.document_image_edge / max(page.rect.width, page.rect.height))
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
                    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                    prepared = image_page(image, number, settings, text)
                    if prepared is None:
                        skipped.append(number)
                    else:
                        image_bytes += len(prepared.data_base64)
                        if image_bytes > settings.document_max_output_bytes:
                            raise ServiceError(413, "This document produces too much image data. Please split it into smaller files.")
                        pages.append(prepared)
                if not pages:
                    raise ServiceError(422, "No visible menu content was found. Please upload another file.")
                return PreparedDocument(page_count=document.page_count, pages=pages, skipped_blank_pages=skipped)
        except ServiceError:
            raise
        except (RuntimeError, ValueError, OSError):
            raise ServiceError(422, "This PDF could not be read. Please upload a valid, undamaged PDF.") from None


def prepare_document(path: Path, content_type: str, settings: Settings) -> PreparedDocument:
    """Decode one stored upload without calling AI, OCR, or mutating its source."""
    try:
        if path.stat().st_size > settings.max_upload_bytes:
            raise ServiceError(413, "This file exceeds the upload limit.")
    except OSError:
        raise ServiceError(503, "The saved menu file is unavailable. Please try again or upload it again.") from None
    if content_type == "application/pdf":
        result = prepare_pdf(path, settings)
    elif content_type in ("image/png", "image/jpeg"):
        result = prepare_image(path, content_type, settings)
    else:
        raise ServiceError(415, "Choose a PDF, JPG, JPEG, or PNG file.")
    if sum(len(p.data_base64) for p in result.pages if isinstance(p, ImagePage)) > settings.document_max_output_bytes:
        raise ServiceError(413, "This document produces too much image data. Please use a smaller file.")
    if any(isinstance(p, TextPage) for p in result.pages):
        logger.info("menu_text_extracted pages=%s", len(result.pages))
    return result

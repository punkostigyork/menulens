import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID
from fastapi import BackgroundTasks
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload
from app.core.config import Settings
from app.core.errors import ServiceError
from app.models import Menu, MenuExtraction, MenuSection, MenuItem
from app.schemas.menu import MenuDetail
from app.services.ai.base import AIProvider, ProviderError
from app.services.ai.factory import get_provider
from app.services.ai.menu_extractor import extract_menu, ExtractionStats, PROMPT_VERSION
from app.services.menu_service import prepare_menu

logger = logging.getLogger(__name__)


def menu_detail(menu_id: UUID, session: Session) -> MenuDetail:
    try:
        menu = session.scalar(select(Menu).where(Menu.id == menu_id).options(selectinload(Menu.sections).selectinload(MenuSection.items).selectinload(MenuItem.explanations), selectinload(Menu.extraction), selectinload(Menu.sections).selectinload(MenuSection.items).selectinload(MenuItem.generated_image)).execution_options(populate_existing=True))
        if menu is None:
            raise ServiceError(404, "Menu not found.")
        detail = MenuDetail.model_validate(menu)
        from app.services.demo_service import DEMO_ID
        detail.is_demo = menu.id == DEMO_ID
        if menu.extraction:
            detail.restaurant_name = menu.extraction.restaurant_name
            detail.processing_error = menu.extraction.error_message
        return detail
    except SQLAlchemyError:
        raise ServiceError(503, "We couldn't load your menu. Please try again.") from None


def start_extraction(menu_id: UUID, session: Session, settings: Settings, tasks: BackgroundTasks) -> MenuDetail:
    detail = menu_detail(menu_id, session)
    if detail.status in ("processing", "processed"):
        return detail
    provider = get_provider(settings)  # Configuration failures do not change the uploaded record.
    try:
        claimed = session.execute(update(Menu).where(Menu.id == menu_id, Menu.status.in_(["uploaded", "failed"])).values(status="processing", processed_at=None))
        if claimed.rowcount != 1:
            session.rollback()
            return menu_detail(menu_id, session)
        record = session.get(MenuExtraction, menu_id)
        if record is None:
            record = MenuExtraction(menu_id=menu_id)
            session.add(record)
        record.provider = provider.name
        record.model = provider.model
        record.prompt_version = PROMPT_VERSION
        record.started_at = datetime.now(timezone.utc)
        record.error_message = None
        record.attempts = record.input_tokens = record.output_tokens = record.latency_ms = 0
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise ServiceError(503, "We couldn't start menu processing. Please try again.") from None
    tasks.add_task(run_extraction, menu_id, session.get_bind(), settings, provider)
    detail.status = "processing"
    detail.processing_error = None
    return detail


def copy_stats(record: MenuExtraction, stats: ExtractionStats) -> None:
    record.attempts = stats.attempts
    record.input_tokens = stats.input_tokens
    record.output_tokens = stats.output_tokens
    record.latency_ms = stats.latency_ms


def run_extraction(menu_id: UUID, engine: Engine, settings: Settings, provider: AIProvider) -> None:
    stats = ExtractionStats()
    logger.info("menu_processing_started menu_id=%s", menu_id)
    try:
        with Session(engine) as session:
            document = prepare_menu(menu_id, session, settings)
        extracted = asyncio.run(extract_menu(provider, document, settings.menu_ai_timeout_seconds, stats))
        with Session(engine) as session:
            menu = session.get(Menu, menu_id)
            if menu is None or menu.status != "processing":
                return
            # ORM cascades delete children if a retry ever replaces prior data.
            menu.sections.clear()
            session.flush()
            for order, section in enumerate(extracted.sections):
                saved_section = MenuSection(name=section.name, display_order=order)
                for item_order, item in enumerate(section.items):
                    saved_section.items.append(MenuItem(
                        display_order=item_order, name=item.name, original_description=item.original_description,
                        price=item.price, currency=item.currency or extracted.currency, language=extracted.language,
                        ingredients=item.ingredients, tags=[], dietary_info=[],
                    ))
                menu.sections.append(saved_section)
            menu.currency = extracted.currency
            menu.language = extracted.language
            menu.status = "processed"
            menu.processed_at = datetime.now(timezone.utc)
            menu.extraction.restaurant_name = extracted.restaurant_name
            menu.extraction.error_message = None
            copy_stats(menu.extraction, stats)
            session.commit()
        logger.info("menu_processing_completed menu_id=%s", menu_id)
    except Exception as exc:
        public_error = exc.message if isinstance(exc, (ServiceError, ProviderError)) else "We couldn't save the processed menu. Please try again."
        # Never log source content, raw responses, validation input, or provider exceptions.
        logger.error("menu_processing_failed menu_id=%s error_type=%s", menu_id, type(exc).__name__)
        try:
            with Session(engine) as session:
                menu = session.get(Menu, menu_id)
                if menu and menu.status == "processing":
                    menu.status = "failed"
                    menu.processed_at = None
                    if menu.extraction:
                        menu.extraction.error_message = public_error
                        copy_stats(menu.extraction, stats)
                    session.commit()
        except SQLAlchemyError:
            logger.error("menu_failure_status_unavailable menu_id=%s", menu_id)


def recover_interrupted(engine: Engine) -> None:
    """The MVP runs one worker; no jobs can survive its process restart."""
    with Session(engine) as session:
        ids = list(session.scalars(select(Menu.id).where(Menu.status == "processing")))
        if ids:
            session.execute(update(Menu).where(Menu.id.in_(ids)).values(status="failed", processed_at=None))
            session.execute(update(MenuExtraction).where(MenuExtraction.menu_id.in_(ids)).values(error_message="Processing was interrupted. Please try again."))
            session.commit()
            logger.warning("menu_processing_interrupted count=%s", len(ids))

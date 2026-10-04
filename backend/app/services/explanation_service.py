import asyncio
import logging
from uuid import UUID
from fastapi import BackgroundTasks
from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.errors import ServiceError
from app.models import Menu, MenuItem, MenuSection
from app.models.item_explanation import ItemExplanation
from app.schemas.explanation import DishSource, ExplanationRead
from app.services.ai.base import AIProvider, ProviderError
from app.services.ai.factory import get_provider
from app.services.ai.dish_explainer import explain_dish, PROMPT_VERSION

logger = logging.getLogger(__name__)


def get_explanation(item_id: UUID, language: str, session: Session) -> ExplanationRead:
    try:
        record = session.get(ItemExplanation, (item_id, language), populate_existing=True)
        if record is None: raise ServiceError(404, "No explanation has been requested for this dish yet.")
        return ExplanationRead.model_validate(record)
    except SQLAlchemyError:
        raise ServiceError(503, "We couldn't load the explanation. Please try again.") from None


def request_explanation(item_id: UUID, language: str, session: Session, settings: Settings, tasks: BackgroundTasks) -> ExplanationRead:
    try:
        item = session.get(MenuItem, item_id)
        if item is None: raise ServiceError(404, "Dish not found.")
        if item.section.menu.status != "processed": raise ServiceError(409, "Please wait until this menu is ready.")
        source = DishSource(name=item.name, original_description=item.original_description, ingredients=list(item.ingredients))
        record = session.get(ItemExplanation, (item_id, language))
        if record and record.status in ("processing", "ready"):
            return ExplanationRead.model_validate(record)
        provider = get_provider(settings)
        values = dict(status="processing", description=None, tags=[], error_message=None, provider=provider.name, model=provider.model, prompt_version=PROMPT_VERSION)
        if record:
            claimed = session.execute(update(ItemExplanation).where(ItemExplanation.item_id == item_id, ItemExplanation.language == language, ItemExplanation.status == "failed").values(**values))
            if claimed.rowcount != 1:
                session.rollback()
                return get_explanation(item_id, language, session)
            session.refresh(record)
        else:
            record = ItemExplanation(item_id=item_id, language=language, **values)
            session.add(record)
        session.flush()
        response = ExplanationRead.model_validate(record)
        session.commit()
    except IntegrityError:
        session.rollback()
        # Composite PK makes simultaneous first requests return the same work.
        return get_explanation(item_id, language, session)
    except SQLAlchemyError:
        session.rollback()
        raise ServiceError(503, "We couldn't start the explanation. Please try again.") from None
    tasks.add_task(run_explanation, item_id, language, source, session.get_bind(), settings, provider)
    return response


def run_explanation(item_id: UUID, language: str, source: DishSource, engine: Engine, settings: Settings, provider: AIProvider) -> None:
    try:
        result = asyncio.run(explain_dish(provider, source, language, settings.menu_ai_timeout_seconds))
        with Session(engine) as session:
            record = session.get(ItemExplanation, (item_id, language))
            if not record or record.status != "processing": return
            record.description = result.description
            record.tags = result.tags
            record.status = "ready"
            record.error_message = None
            session.commit()
        logger.info("dish_explanation_completed item_id=%s language=%s", item_id, language)
    except Exception as exc:
        logger.error("dish_explanation_failed item_id=%s error_type=%s", item_id, type(exc).__name__)
        message = exc.message if isinstance(exc, (ServiceError, ProviderError)) else "We couldn't save the explanation. Please try again."
        try:
            with Session(engine) as session:
                session.execute(update(ItemExplanation).where(ItemExplanation.item_id == item_id, ItemExplanation.language == language, ItemExplanation.status == "processing").values(status="failed", description=None, tags=[], error_message=message))
                session.commit()
        except SQLAlchemyError:
            logger.error("dish_explanation_failure_status_unavailable item_id=%s", item_id)


def recover_explanations(engine: Engine) -> None:
    with Session(engine) as session:
        session.execute(update(ItemExplanation).where(ItemExplanation.status == "processing").values(status="failed", error_message="Explanation was interrupted. Please try again."))
        session.commit()

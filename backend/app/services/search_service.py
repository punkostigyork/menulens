import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload
from app.core.config import Settings
from app.core.errors import ServiceError
from app.models import Menu, MenuItem, MenuSection
from app.schemas.menu_item import MenuItemRead
from app.schemas.search import SearchRequest, SearchResponse, SearchIntent, SearchMatch
from app.services.ai.base import ProviderError
from app.services.ai.factory import get_provider
from app.services.ai.search_interpreter import interpret_search
from app.services.search_matching import match_item

logger = logging.getLogger(__name__)
CLARIFICATIONS = {
    "allergy_safety": "Search cannot verify allergy or dietary safety. Ask the restaurant, or search by a dish name or listed ingredient.",
    "exclusions": "Search cannot reliably exclude ingredients or verify vegetarian/vegan dishes. Try a dish name or an ingredient you want included.",
    "location": "Search currently covers saved menus, without location or restaurant filtering.",
    "nutrition": "Nutrition filtering is not available. Try a dish, ingredient, tag, or price.",
    "alternatives": "Please search for one combination at a time; alternative (either/or) filters aren't supported yet.",
    "other": "Try a dish name, listed ingredient, category, or a price with a currency.",
}


def search(request: SearchRequest, session: Session, settings: Settings) -> SearchResponse:
    logger.info("dish_search_started mode=%s", "query" if request.query else "filters")
    intent = request.filters
    if intent is None:
        try:
            provider = get_provider(settings)
        except ServiceError:
            raise ServiceError(503, "Natural-language search isn't configured yet. You can still browse dishes using the filters.") from None
        try:
            intent = asyncio.run(interpret_search(provider, request.query, settings.menu_ai_timeout_seconds))
        except ProviderError as exc:
            logger.warning("dish_search_failed error_type=%s", type(exc).__name__)
            # Shared adapters have menu-oriented errors; keep the public search context correct.
            message = exc.message if exc.status_code in (422, 504) and "search" in exc.message else "The search service couldn't understand your request. Please try again or use filters."
            raise ServiceError(exc.status_code, message) from None
    return filter_dishes(intent, request, session)


def filter_dishes(intent: SearchIntent, request: SearchRequest, session: Session) -> SearchResponse:
    response = SearchResponse(intent=intent, results=[], total=0, limit=request.limit, offset=request.offset, has_more=False)
    if intent.unsupported:
        response.clarification = " ".join(CLARIFICATIONS[key] for key in intent.unsupported)
        return response
    if (intent.min_price is not None or intent.max_price is not None) and intent.currency is None:
        response.clarification = "Please include a currency with your budget, for example 5000 HUF. Prices in different currencies are not compared."
        return response
    statement = select(MenuItem).join(MenuSection).join(Menu).where(Menu.status == "processed").options(
        selectinload(MenuItem.explanations), selectinload(MenuItem.generated_image),
        joinedload(MenuItem.section).joinedload(MenuSection.menu).joinedload(Menu.extraction),
    ).order_by(Menu.created_at.desc(), Menu.id, MenuSection.display_order, MenuItem.display_order, MenuItem.id)
    if request.menu_id is not None: statement = statement.where(Menu.id == request.menu_id)
    if intent.currency: statement = statement.where(MenuItem.currency == intent.currency)
    if intent.min_price is not None:
        statement = statement.where(MenuItem.price >= intent.min_price if intent.min_price_inclusive else MenuItem.price > intent.min_price)
    if intent.max_price is not None:
        statement = statement.where(MenuItem.price <= intent.max_price if intent.max_price_inclusive else MenuItem.price < intent.max_price)
    try:
        # Stream SQL-filtered candidates; only the requested page is retained. No silent candidate truncation.
        for item in session.scalars(statement.execution_options(yield_per=200)):
            matches, inferred_tags = match_item(item, intent)
            if not matches: continue
            if request.offset <= response.total < request.offset + request.limit:
                menu = item.section.menu
                response.results.append(SearchMatch(item=MenuItemRead.model_validate(item), menu_id=menu.id,
                    menu_title=(menu.extraction.restaurant_name if menu.extraction else None) or menu.original_filename,
                    section_name=item.section.name, matched_inferred_tags=inferred_tags))
            response.total += 1
    except SQLAlchemyError:
        logger.error("dish_search_failed error_type=database")
        raise ServiceError(503, "We couldn't search your saved menus. Please try again.") from None
    response.has_more = request.offset + len(response.results) < response.total
    logger.info("dish_search_completed total=%s returned=%s", response.total, len(response.results))
    return response

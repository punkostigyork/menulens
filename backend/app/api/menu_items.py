from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.database.session import get_session
from app.schemas.explanation import ExplanationLanguage, ExplanationRead, ExplanationRequest
from app.services.explanation_service import get_explanation, request_explanation

router = APIRouter(prefix="/api/menu-items", tags=["menu items"])


@router.post("/{item_id}/explanation", response_model=ExplanationRead, status_code=202)
def explain_item(item_id: UUID, request: ExplanationRequest, tasks: BackgroundTasks, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]):
    return request_explanation(item_id, request.language, session, settings, tasks)


@router.get("/{item_id}/explanation", response_model=ExplanationRead)
def read_explanation(item_id: UUID, session: Annotated[Session, Depends(get_session)], language: ExplanationLanguage = "en"):
    return get_explanation(item_id, language, session)

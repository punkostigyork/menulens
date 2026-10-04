from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.database.session import get_session
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_dishes(request: SearchRequest, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]):
    return search(request, session, settings)

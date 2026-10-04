from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.database.session import get_session
from app.schemas.image import ImageRead
from app.services.image_service import request_image, read_image, read_image_content

router = APIRouter(prefix="/api/menu-items", tags=["images"])


@router.post("/{item_id}/image", response_model=ImageRead, status_code=202)
def generate_image(item_id: UUID, tasks: BackgroundTasks, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]):
    return request_image(item_id, session, settings, tasks)


@router.get("/{item_id}/image", response_model=ImageRead)
def image_status(item_id: UUID, session: Annotated[Session, Depends(get_session)]):
    return read_image(item_id, session)


@router.get("/{item_id}/image/content")
def image_content(item_id: UUID, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]):
    return Response(read_image_content(item_id, session, settings), media_type="image/png", headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})

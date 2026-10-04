from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.database.session import get_session
from app.schemas.menu import MenuRead, MenuDetail
from app.schemas.menu_item import MenuItemRead
from app.services.extraction_service import menu_detail, start_extraction
from app.services.menu_service import get_menu, save_menu, prepare_menu
from app.schemas.document import PreparedDocument

router = APIRouter(prefix="/api/menus", tags=["menus"])


@router.get("/upload-config")
def upload_config(settings: Annotated[Settings, Depends(get_settings)]):
    return {"max_upload_bytes": settings.max_upload_bytes}


@router.post("", response_model=MenuRead, status_code=201)
def upload_menu(file: Annotated[UploadFile, File()], session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]):
    return save_menu(file.file, file.filename, file.content_type, session, settings)


@router.get("/{menu_id}", response_model=MenuDetail)
def read_menu(menu_id: UUID, session: Annotated[Session, Depends(get_session)]):
    return menu_detail(menu_id, session)


@router.post("/{menu_id}/prepare", response_model=PreparedDocument)
def prepare_uploaded_menu(menu_id: UUID, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]):
    return prepare_menu(menu_id, session, settings)


@router.post("/{menu_id}/process", response_model=MenuDetail, status_code=202)
def process_uploaded_menu(menu_id: UUID, tasks: BackgroundTasks, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]):
    return start_extraction(menu_id, session, settings, tasks)


@router.get("/{menu_id}/items", response_model=list[MenuItemRead])
def read_menu_items(menu_id: UUID, session: Annotated[Session, Depends(get_session)]):
    menu = menu_detail(menu_id, session)
    return [item for section in menu.sections for item in section.items]

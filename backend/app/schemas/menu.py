from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class MenuRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    restaurant_id: UUID | None
    original_filename: str
    stored_filename: str
    content_type: str
    status: Literal["uploaded", "processing", "processed", "failed"]
    currency: str | None
    language: str | None
    created_at: datetime
    processed_at: datetime | None


from app.schemas.menu_item import MenuSectionRead


class MenuDetail(MenuRead):
    is_demo: bool = False
    restaurant_name: str | None = None
    processing_error: str | None = None
    sections: list[MenuSectionRead] = []

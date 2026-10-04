from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    menu_item_id: UUID
    status: Literal["processing", "ready", "failed"]
    image_url: str | None
    error_message: str | None
    created_at: datetime

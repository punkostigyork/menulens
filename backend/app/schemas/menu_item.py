from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.explanation import ExplanationRead
from app.schemas.image import ImageRead


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    section_id: UUID
    display_order: int
    name: str
    original_description: str | None
    generated_description: str | None
    price: Decimal | None
    currency: str | None
    language: str | None
    cuisine: str | None
    ingredients: list[str]
    tags: list[str]
    dietary_info: list
    created_at: datetime
    explanations: list[ExplanationRead] = Field(default_factory=list)
    generated_image: ImageRead | None = None


class MenuSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    display_order: int
    items: list[MenuItemRead]

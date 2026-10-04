from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.menu import Base
from app.models.menu_item import json_type


class ItemExplanation(Base):
    __tablename__ = "item_explanations"
    __table_args__ = (CheckConstraint("language IN ('en', 'hu')", name="explanation_language"), CheckConstraint("status IN ('processing', 'ready', 'failed')", name="explanation_status"))
    item_id: Mapped[UUID] = mapped_column(ForeignKey("menu_items.id", ondelete="CASCADE"), primary_key=True)
    language: Mapped[str] = mapped_column(String(2), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="processing")
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(json_type, default=list)
    error_message: Mapped[str | None] = mapped_column(String(300))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    item: Mapped["MenuItem"] = relationship(back_populates="explanations")

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.menu import Base


class MenuExtraction(Base):
    """One current extraction record: provenance and a safe public failure message."""
    __tablename__ = "menu_extractions"
    menu_id: Mapped[UUID] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True)
    restaurant_name: Mapped[str | None] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    attempts: Mapped[int] = mapped_column(default=0)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(String(300))
    menu: Mapped["Menu"] = relationship(back_populates="extraction")

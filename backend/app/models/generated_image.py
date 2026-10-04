from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.menu import Base


class GeneratedImage(Base):
    __tablename__ = "generated_images"
    __table_args__ = (CheckConstraint("status IN ('processing', 'ready', 'failed')", name="image_status"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    menu_item_id: Mapped[UUID] = mapped_column(ForeignKey("menu_items.id", ondelete="CASCADE"), unique=True)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="processing")
    storage_path: Mapped[str | None] = mapped_column(String(40))
    error_message: Mapped[str | None] = mapped_column(String(300))
    latency_ms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    item: Mapped["MenuItem"] = relationship(back_populates="generated_image")

    @property
    def image_url(self) -> str | None:
        return f"/api/menu-items/{self.menu_item_id}/image/content" if self.status == "ready" else None

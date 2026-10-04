from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.menu import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (CheckConstraint("price >= 0", name="nonnegative_price"), UniqueConstraint("section_id", "display_order"))
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    section_id: Mapped[UUID] = mapped_column(ForeignKey("menu_sections.id", ondelete="CASCADE"), index=True)
    display_order: Mapped[int]
    name: Mapped[str] = mapped_column(String(255))
    original_description: Mapped[str | None] = mapped_column(Text)
    generated_description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    language: Mapped[str | None] = mapped_column(String(20))
    cuisine: Mapped[str | None] = mapped_column(String(120))
    ingredients: Mapped[list[str]] = mapped_column(json_type, default=list)
    tags: Mapped[list[str]] = mapped_column(json_type, default=list)
    dietary_info: Mapped[list] = mapped_column(json_type, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    section: Mapped["MenuSection"] = relationship(back_populates="items")
    explanations: Mapped[list["ItemExplanation"]] = relationship(back_populates="item", cascade="all, delete-orphan", order_by="ItemExplanation.language")
    generated_image: Mapped["GeneratedImage | None"] = relationship(back_populates="item", cascade="all, delete-orphan", uselist=False)

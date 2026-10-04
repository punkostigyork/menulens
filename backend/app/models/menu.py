from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Menu(Base):
    __tablename__ = "menus"
    __table_args__ = (CheckConstraint("status IN ('uploaded', 'processing', 'processed', 'failed')", name="menu_status"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # Restaurant model and foreign key arrive with restaurant persistence.
    restaurant_id: Mapped[UUID | None] = mapped_column(nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(40), unique=True)
    content_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sections: Mapped[list["MenuSection"]] = relationship(back_populates="menu", cascade="all, delete-orphan", order_by="MenuSection.display_order")
    extraction: Mapped["MenuExtraction | None"] = relationship(back_populates="menu", cascade="all, delete-orphan", uselist=False)

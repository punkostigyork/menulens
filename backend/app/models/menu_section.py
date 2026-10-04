from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.menu import Base


class MenuSection(Base):
    __tablename__ = "menu_sections"
    __table_args__ = (UniqueConstraint("menu_id", "display_order"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    menu_id: Mapped[UUID] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    display_order: Mapped[int]
    menu: Mapped["Menu"] = relationship(back_populates="sections")
    items: Mapped[list["MenuItem"]] = relationship(back_populates="section", cascade="all, delete-orphan", order_by="MenuItem.display_order")

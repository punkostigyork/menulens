"""Versioned, hand-authored demo. Never creates AI provenance or overwrites user data."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid5
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.models import Menu, MenuItem, MenuSection, MenuExtraction
from app.schemas.extraction import ExtractedMenu

DEMO_ID = UUID("a1d8a5d1-8862-43b8-942b-6e96f746cd89")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEMO_FILENAME = DEMO_ID.hex + ".pdf"
SOURCE_TAGS = {"Gulyasleves": ["Hungarian", "soup", "meat"], "Hortobagyi husos palacsinta": ["Hungarian", "meat"], "Csirkepaprikas": ["Hungarian", "poultry"], "Somloi galuska": ["Hungarian", "dessert", "sweet"]}

def seed_demo(engine: Engine, settings: Settings) -> bool:
    """Single-worker startup/CLI seed, one DB transaction, stable IDs; false if present."""
    with Session(engine) as session:
        if session.get(Menu, DEMO_ID):
            return False
        data = ExtractedMenu.model_validate_json((DATA_DIR / "hungarian-menu.json").read_text())
        source = (DATA_DIR / "hungarian-menu.pdf").read_bytes()
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        destination = settings.upload_dir / DEMO_FILENAME
        created = False
        try:
            try:
                with destination.open("xb") as target:
                    created = True
                    target.write(source)
            except FileExistsError:
                if destination.read_bytes() != source:
                    raise RuntimeError("Demo filename is occupied by a different file; no data was changed.") from None
            menu = Menu(id=DEMO_ID, original_filename="MenuLens Hungarian sample.pdf", stored_filename=DEMO_FILENAME,
                        content_type="application/pdf", status="processed", currency=data.currency,
                        language=data.language, processed_at=datetime.now(timezone.utc))
            session.add(menu)
            session.add(MenuExtraction(menu=menu, restaurant_name=data.restaurant_name, provider="hand-authored", model="demo-v1", prompt_version="not-ai", attempts=0))
            for section_index, section in enumerate(data.sections):
                row = MenuSection(id=uuid5(DEMO_ID, f"section-{section_index}"), menu=menu, name=section.name, display_order=section_index)
                session.add(row)
                for item_index, item in enumerate(section.items):
                    session.add(MenuItem(id=uuid5(DEMO_ID, f"item-{section_index}-{item_index}"), section=row,
                                         display_order=item_index, name=item.name, original_description=item.original_description,
                                         price=item.price, currency=data.currency, language=data.language, cuisine="Hungarian",
                                         ingredients=item.ingredients, tags=SOURCE_TAGS[item.name], dietary_info=[]))
            session.commit()
            return True
        except Exception:
            session.rollback()
            if created:
                destination.unlink(missing_ok=True)
            raise

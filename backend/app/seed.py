"""Run with python -m app.seed. Safe to rerun; does not reset the database."""
from app.core.config import get_settings
from app.database.connection import create_database_engine
from app.models import Base
from app.services.demo_service import seed_demo

if __name__ == "__main__":
    engine = create_database_engine()
    try:
        Base.metadata.create_all(engine)
        created = seed_demo(engine, get_settings())
        print("Demo menu created." if created else "Demo menu already exists; no changes made.")
    finally:
        engine.dispose()

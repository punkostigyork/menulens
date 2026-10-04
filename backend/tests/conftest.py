from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app.main import app
from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def database(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    settings = Settings(upload_dir=tmp_path / "uploads", max_upload_bytes=1024)
    app.dependency_overrides[get_settings] = lambda: settings
    with patch("app.main.create_database_engine", return_value=engine):
        yield engine, settings
    app.dependency_overrides.clear()
    engine.dispose()

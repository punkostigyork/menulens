from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = Field(default="postgresql+psycopg://menulens:menulens_local@localhost:5432/menulens", repr=False)
    seed_demo: bool = False
    upload_dir: Path = Path("uploads")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0, le=100 * 1024 * 1024)
    document_max_pages: int = Field(default=20, ge=1, le=100)
    document_image_edge: int = Field(default=1600, ge=256, le=2400)
    document_max_image_pixels: int = Field(default=40_000_000, ge=1, le=80_000_000)
    document_max_text_chars: int = Field(default=200_000, ge=1)
    document_max_output_bytes: int = Field(default=16 * 1024 * 1024, ge=1)
    openai_api_key: SecretStr = SecretStr("")
    anthropic_api_key: SecretStr = SecretStr("")
    menu_ai_provider: str = ""
    menu_ai_model: str = Field(default="", max_length=200)
    menu_ai_timeout_seconds: float = Field(default=60, gt=0, le=180)
    menu_ai_max_output_tokens: int = Field(default=12000, ge=1024, le=32000)
    image_provider: str = ""
    image_model: str = Field(default="", max_length=200)
    image_timeout_seconds: float = Field(default=180, gt=0, le=300)
    image_max_bytes: int = Field(default=10485760, ge=1024, le=20971520)
    places_api_key: SecretStr = SecretStr("")
    places_timeout_seconds: float = Field(default=15, gt=0, le=60)
    maps_api_key: str = Field(default="", repr=False)
    maps_map_id: str = "DEMO_MAP_ID"
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

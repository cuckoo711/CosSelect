from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/cosselect"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # Security
    secret_key: str = "change-me-in-production-please-set-a-long-random-value"

    # Storage
    data_dir: str = "/data/spaces"

    # Invite code
    invite_code_ttl_hours: int = 24

    # Thumbnail
    thumbnail_max_width: int = 1200
    thumbnail_max_bytes: int = 500 * 1024
    thumbnail_quality: int = 82

    # Uploaded image compression (server-side safety net)
    image_max_pixels: int = 5_000_000  # <= 5 megapixels
    image_quality: int = 85

    # CORS
    cors_origins: str = "*"

    @property
    def broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

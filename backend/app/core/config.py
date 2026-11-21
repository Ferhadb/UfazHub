from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "UFAZ Hub"
    APP_ENV: Literal["development", "test", "production"] = "development"
    API_PREFIX: str = "/api"
    SITE_URL: str = "http://localhost"

    DATABASE_URL: str = "postgresql+asyncpg://ufaz:change_me@localhost:5432/ufazhub"
    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: list[str] = ["http://localhost", "http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def _force_asyncpg(cls, v: str) -> str:
        # Compose and hosting providers hand out plain postgresql:// URLs.
        for prefix in ("postgresql://", "postgres://", "postgresql+psycopg2://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix) :]
        return v

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

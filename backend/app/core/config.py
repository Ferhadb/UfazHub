from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "replace-with-64-random-chars"


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

    # Auth
    JWT_SECRET_KEY: str = DEFAULT_JWT_SECRET
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 30
    COOKIE_SECURE: bool = False
    SIGNUP_ALLOWED_DOMAINS: str = (
        ""  # comma-separated, e.g. "ufaz.az"; empty allows any
    )
    VERIFY_TOKEN_HOURS: int = 48
    RESET_TOKEN_MINUTES: int = 60
    RATE_LIMIT_ENABLED: bool = True
    VOTE_DAILY_CAP: int = 200  # vote changes per user per rolling 24h
    REP_DAILY_CAP: int = 200  # vote reputation a user can earn per rolling 24h

    # Uploads (local disk now; `Storage` in app/core/storage.py is the seam for S3)
    MEDIA_ROOT: str = "media"
    MEDIA_SIGNING_KEY: str = ""  # empty derives one from JWT_SECRET_KEY
    MEDIA_URL_TTL_SECONDS: int = 3600
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # PDFs
    IMAGE_MAX_BYTES: int = 5 * 1024 * 1024

    # Email (sent by the arq worker; logged instead when SMTP_USERNAME is empty)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = "UFAZ Hub <noreply@ufazhub.xyz>"

    @field_validator("DATABASE_URL")
    @classmethod
    def _force_asyncpg(cls, v: str) -> str:
        # Compose and hosting providers hand out plain postgresql:// URLs.
        for prefix in ("postgresql://", "postgres://", "postgresql+psycopg2://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix) :]
        return v

    @model_validator(mode="after")
    def _prod_safety(self):
        if self.APP_ENV == "production":
            if (
                self.JWT_SECRET_KEY == DEFAULT_JWT_SECRET
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError(
                    "JWT_SECRET_KEY must be set to 32+ random chars in production"
                )
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE must be true in production")
        return self

    @property
    def signup_domains(self) -> list[str]:
        return [
            d.strip().lower().lstrip("@")
            for d in self.SIGNUP_ALLOWED_DOMAINS.split(",")
            if d.strip()
        ]

    @property
    def media_key(self) -> bytes:
        return (self.MEDIA_SIGNING_KEY or "media:" + self.JWT_SECRET_KEY).encode()

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

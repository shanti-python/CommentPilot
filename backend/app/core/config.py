import os
from typing import Optional
from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Instagram Comment Automation API"

    # Security
    JWT_SECRET: str = "supersecretjwtkeychangeinproduction"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ENCRYPTION_KEY: Optional[str] = None  # Fernet key. If None, derived from JWT_SECRET.

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin123@localhost:5432/insta_automator"

    # Redis and Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Meta Graph API
    META_APP_ID: str = "dummy_app_id"
    META_APP_SECRET: str = "dummy_app_secret"
    META_VERIFY_TOKEN: str = "dummy_verify_token"
    META_ACCESS_TOKEN: Optional[str] = None  # Default fallback token if any
    META_OAUTH_SCOPES: str = "instagram_basic,instagram_manage_comments,pages_show_list,pages_read_engagement"

    # First Superuser / Admin
    FIRST_SUPERUSER: EmailStr = "admin@insta-automator.com"
    FIRST_SUPERUSER_PASSWORD: str = "adminpassword123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        # Support postgresql:// -> postgresql+asyncpg:// for async compatibility
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def sync_database_url(self) -> str:
        # Returns standard postgresql:// for Alembic or sync connection
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


settings = Settings()
StandardDATABASE_URL = settings.DATABASE_URL

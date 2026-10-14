"""Validated application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment variables override values from the local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Meeting Coordinator", min_length=1)
    environment: Literal["development", "test", "production"] = "development"
    groq_api_key: SecretStr | None = None
    groq_model: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""
    return Settings()


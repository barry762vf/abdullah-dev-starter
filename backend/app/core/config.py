"""Validated runtime settings loaded from the repository's root .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: SecretStr
    database_url: SecretStr
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False

    # These values are defined in the master template and used by later phases.
    initial_admin_email: str = ""
    initial_admin_password: SecretStr = SecretStr("")
    ai_provider: str = "disabled"
    gemini_api_key: SecretStr = SecretStr("")
    telegram_bot_token: SecretStr = SecretStr("")
    supabase_url: str = ""
    supabase_key: SecretStr = SecretStr("")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        parsed = urlsplit(value.get_secret_value())
        if (
            parsed.scheme != "postgresql+asyncpg"
            or not parsed.hostname
            or not parsed.path.strip("/")
        ):
            raise ValueError("DATABASE_URL must be a PostgreSQL asyncpg URL with host and database")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",")]
        if not origins or any(not origin for origin in origins):
            raise ValueError("CORS_ORIGINS must contain explicit origins")
        for origin in origins:
            parsed = urlsplit(origin)
            try:
                _ = parsed.port
            except ValueError as error:
                raise ValueError("CORS_ORIGINS contains an invalid port") from error
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or origin == "*"
            ):
                raise ValueError("CORS_ORIGINS must contain only explicit HTTP(S) origins")
        return ",".join(dict.fromkeys(origins))

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment != "production":
            return self
        key = self.secret_key.get_secret_value()
        if len(key) < 64 or any(char not in "0123456789abcdefABCDEF" for char in key):
            raise ValueError(
                "Production SECRET_KEY must contain at least 64 hexadecimal characters"
            )
        if self.debug:
            raise ValueError("DEBUG must be false in production")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")
        if any(not origin.startswith("https://") for origin in self.allowed_origins):
            raise ValueError("Production CORS_ORIGINS must use HTTPS")
        admin_password = self.initial_admin_password.get_secret_value()
        if len(admin_password) < 12 or admin_password == "Admin123!Secure":
            raise ValueError("Set a strong, non-sample INITIAL_ADMIN_PASSWORD in production")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return self.cors_origins.split(",")


@lru_cache
def get_settings() -> Settings:
    return Settings()

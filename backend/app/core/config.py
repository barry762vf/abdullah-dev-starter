"""Validated runtime settings from the environment and, outside containers, the root .env file."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PARENTS = Path(__file__).resolve().parents
ROOT_DIR = _PARENTS[3] if len(_PARENTS) > 3 else _PARENTS[-1]
# ENV_FILE overrides the file path; an empty ENV_FILE (set in the container image) reads only
# real environment variables, so an accidentally copied .env can never configure production.
_ENV_FILE = os.environ.get("ENV_FILE")
ENV_FILE_PATH = (_ENV_FILE or None) if _ENV_FILE is not None else ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"]
    debug: bool = False
    secret_key: SecretStr
    database_url: SecretStr
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False
    # How the client IP for rate limits and audit is determined (ADR 014). Required outside
    # development: "peer" = socket peer; "edge_header" = X-Edge-Client-IP from an
    # authenticated proxy.
    client_ip_source: Literal["peer", "edge_header"] | None = None
    edge_proxy_secret: SecretStr = SecretStr("")
    # OpenAPI/Swagger: on by default only in development.
    api_docs_enabled: bool | None = None
    # Per-process pool. Size x workers x instances must stay below the database connection limit.
    db_pool_size: int = Field(default=5, ge=1, le=100)
    db_max_overflow: int = Field(default=5, ge=0, le=100)
    db_pool_timeout: float = Field(default=10, gt=0, le=60)
    # true for PgBouncer/Supavisor transaction mode (for example Supabase port 6543).
    database_transaction_pooler: bool = False

    # Read only by the explicit administrator bootstrap command.
    initial_admin_email: str = ""
    initial_admin_password: SecretStr = SecretStr("")
    ai_provider: str = "disabled"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.5-flash"
    messenger_provider: str = "disabled"
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_webhook_secret: SecretStr = SecretStr("")
    storage_provider: str = "disabled"
    supabase_url: str = ""
    supabase_key: SecretStr = SecretStr("")
    supabase_bucket: str = ""
    email_provider: str = "disabled"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_email: str = ""
    smtp_starttls: bool = True

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
    def validate_non_development_security(self) -> "Settings":
        if self.ai_provider not in {"disabled", "gemini"}:
            raise ValueError("AI_PROVIDER must be disabled or gemini")
        if self.ai_provider == "gemini":
            if not self.gemini_api_key.get_secret_value():
                raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")
            if not self.gemini_model or not all(
                char.isascii() and (char.isalnum() or char in "-_.") for char in self.gemini_model
            ):
                raise ValueError("GEMINI_MODEL is invalid")
        if self.messenger_provider not in {"disabled", "telegram"}:
            raise ValueError("MESSENGER_PROVIDER must be disabled or telegram")
        if self.messenger_provider == "telegram":
            if not self.telegram_bot_token.get_secret_value():
                raise ValueError("TELEGRAM_BOT_TOKEN is required")
            secret = self.telegram_webhook_secret.get_secret_value()
            if (
                len(secret) < 32
                or len(secret) > 256
                or not all(char.isascii() and (char.isalnum() or char in "_-") for char in secret)
            ):
                raise ValueError("TELEGRAM_WEBHOOK_SECRET must be 32-256 safe characters")
        if self.storage_provider not in {"disabled", "supabase"}:
            raise ValueError("STORAGE_PROVIDER must be disabled or supabase")
        if self.storage_provider == "supabase":
            url = urlsplit(self.supabase_url)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.port
                or url.username
                or url.password
                or url.path not in {"", "/"}
                or url.query
                or url.fragment
                or not url.hostname.endswith(".supabase.co")
            ):
                raise ValueError("SUPABASE_URL must be an HTTPS supabase.co project origin")
            if not self.supabase_key.get_secret_value() or not self.supabase_bucket:
                raise ValueError("SUPABASE_KEY and SUPABASE_BUCKET are required")
        if self.email_provider not in {"disabled", "smtp"}:
            raise ValueError("EMAIL_PROVIDER must be disabled or smtp")
        if self.email_provider == "smtp":
            if not all(
                (
                    self.smtp_host,
                    self.smtp_username,
                    self.smtp_password.get_secret_value(),
                    self.smtp_from_email,
                )
            ):
                raise ValueError(
                    "SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM_EMAIL are required"
                )
            if self.environment != "development" and not self.smtp_starttls:
                raise ValueError("SMTP_STARTTLS must be true outside development")
        if (
            self.client_ip_source == "edge_header"
            and len(self.edge_proxy_secret.get_secret_value()) < 32
        ):
            raise ValueError(
                "EDGE_PROXY_SECRET must have at least 32 characters in edge_header mode"
            )
        if self.environment == "development":
            return self
        if self.client_ip_source is None:
            raise ValueError("Set CLIENT_IP_SOURCE to peer or edge_header outside development")
        key = self.secret_key.get_secret_value()
        if len(key) < 64 or any(char not in "0123456789abcdefABCDEF" for char in key):
            raise ValueError(
                "Staging/production SECRET_KEY must contain at least 64 hexadecimal characters"
            )
        if self.debug:
            raise ValueError("DEBUG must be false in staging/production")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in staging/production")
        if any(not origin.startswith("https://") for origin in self.allowed_origins):
            raise ValueError("Staging/production CORS_ORIGINS must use HTTPS")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return self.cors_origins.split(",")

    @property
    def effective_client_ip_source(self) -> str:
        return self.client_ip_source or "peer"

    @property
    def docs_enabled(self) -> bool:
        if self.api_docs_enabled is not None:
            return self.api_docs_enabled
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

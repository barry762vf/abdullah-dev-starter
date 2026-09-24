"""Configuration validation tests for the Phase 1 runtime boundary."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

BASE = {
    "secret_key": "test-only-secret",
    "database_url": "postgresql+asyncpg://test:test@localhost:5432/test_db",
    "cors_origins": "http://localhost:5173,http://localhost:3000",
    "client_ip_source": "peer",
}


def test_environment_must_be_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    with pytest.raises(ValidationError, match="environment"):
        Settings(_env_file=None, **BASE)


def test_development_settings_parse_origins_and_hide_secrets() -> None:
    settings = Settings(_env_file=None, **BASE)

    assert settings.allowed_origins == ["http://localhost:5173", "http://localhost:3000"]
    assert "test-only-secret" not in repr(settings)
    assert "test:test" not in repr(settings)


def test_settings_load_from_env_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SECRET_KEY=from-file-only\n"
        "DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/from_file\n"
        "CORS_ORIGINS=https://app.example.com\n",
        encoding="utf-8",
    )
    for key in ("SECRET_KEY", "DATABASE_URL", "CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=env_file)

    assert settings.secret_key.get_secret_value() == "from-file-only"
    assert settings.allowed_origins == ["https://app.example.com"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cors_origins", "*"),
        ("cors_origins", "http://localhost:5173/path"),
        ("cors_origins", "http://localhost:5173,"),
        ("cors_origins", "http://localhost:invalid"),
        ("database_url", "sqlite:///test.db"),
    ],
)
def test_invalid_connections_are_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **(BASE | {field: value}))


def test_production_rejects_sample_secret_and_insecure_flags() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **BASE,
            environment="production",
            debug=True,
            cookie_secure=False,
        )


def test_production_accepts_strong_configuration() -> None:
    settings = Settings(
        _env_file=None,
        **(BASE | {"secret_key": "a" * 64, "cors_origins": "https://example.com"}),
        environment="production",
        debug=False,
        cookie_secure=True,
    )

    assert settings.environment == "production"
    assert settings.allowed_origins == ["https://example.com"]


def test_production_rejects_http_origin() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            **(BASE | {"secret_key": "a" * 64}),
            environment="production",
            cookie_secure=True,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("secret_key", "sample-secret", "SECRET_KEY"),
        ("debug", True, "DEBUG"),
        ("cookie_secure", False, "COOKIE_SECURE"),
        ("cors_origins", "http://example.com", "HTTPS"),
    ],
)
def test_staging_rejects_each_insecure_setting(field: str, value: object, message: str) -> None:
    secure = BASE | {
        "secret_key": "a" * 64,
        "cors_origins": "https://example.com",
        "debug": False,
        "cookie_secure": True,
        "environment": "staging",
    }
    with pytest.raises(ValidationError, match=message):
        Settings(_env_file=None, **(secure | {field: value}))


def test_staging_accepts_strong_configuration() -> None:
    settings = Settings(
        _env_file=None,
        **(BASE | {"secret_key": "a" * 64, "cors_origins": "https://example.com"}),
        environment="staging",
        debug=False,
        cookie_secure=True,
    )
    assert settings.environment == "staging"


STRONG = BASE | {
    "secret_key": "a" * 64,
    "cors_origins": "https://example.com",
    "cookie_secure": True,
}


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_client_ip_source_must_be_explicit_outside_development(environment: str) -> None:
    values = {key: value for key, value in STRONG.items() if key != "client_ip_source"}
    with pytest.raises(ValidationError, match="CLIENT_IP_SOURCE"):
        Settings(_env_file=None, **values, environment=environment)
    assert (
        Settings(_env_file=None, **values, environment="development").effective_client_ip_source
        == "peer"
    )


@pytest.mark.parametrize("secret", ["", "short-secret"])
def test_edge_mode_requires_a_strong_proxy_secret(secret: str) -> None:
    for environment in ("development", "production"):
        with pytest.raises(ValidationError, match="EDGE_PROXY_SECRET"):
            Settings(
                _env_file=None,
                **(STRONG | {"client_ip_source": "edge_header", "edge_proxy_secret": secret}),
                environment=environment,
            )
    edge = Settings(
        _env_file=None,
        **(STRONG | {"client_ip_source": "edge_header", "edge_proxy_secret": "s" * 32}),
        environment="production",
    )
    assert "s" * 32 not in repr(edge)


def test_api_docs_default_to_development_only() -> None:
    assert Settings(_env_file=None, **BASE, environment="development").docs_enabled is True
    assert Settings(_env_file=None, **STRONG, environment="production").docs_enabled is False
    assert Settings(
        _env_file=None, **STRONG, environment="production", api_docs_enabled=True
    ).docs_enabled


def test_env_file_can_be_disabled_for_containers(tmp_path, monkeypatch) -> None:
    """ENV_FILE="" makes the process read only real environment variables."""
    import importlib

    from app.core import config

    monkeypatch.setenv("ENV_FILE", "")
    try:
        reloaded = importlib.reload(config)
        assert reloaded.ENV_FILE_PATH is None
        monkeypatch.setenv("ENV_FILE", str(tmp_path / "custom.env"))
        assert importlib.reload(config).ENV_FILE_PATH == str(tmp_path / "custom.env")
    finally:
        monkeypatch.delenv("ENV_FILE")
        importlib.reload(config)

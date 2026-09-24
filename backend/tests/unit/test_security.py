"""Cryptographic boundary checks."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    new_refresh_token,
    refresh_digest,
    verify_password,
)


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        secret_key="test-only-signing-secret",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
    )


def test_argon2id_hash_and_verify() -> None:
    hashed = hash_password("a secure test password")
    assert hashed.startswith("$argon2id$")
    assert "a secure test password" not in hashed
    assert verify_password("a secure test password", hashed)
    assert not verify_password("wrong password", hashed)
    assert not verify_password("password", "malformed")


def test_access_jwt_claims_and_rejections(settings: Settings) -> None:
    user_id = uuid4()
    token = create_access_token(user_id, settings)
    assert decode_access_token(token, settings) == user_id
    claims = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=["HS256"])
    assert claims["type"] == "access"
    assert set(claims) == {"sub", "type", "iat", "exp"}
    for bad in (
        token + "tamper",
        "malformed",
        jwt.encode(
            {
                "sub": str(user_id),
                "type": "access",
                "iat": datetime.now(UTC) - timedelta(hours=1),
                "exp": datetime.now(UTC) - timedelta(seconds=1),
            },
            settings.secret_key.get_secret_value(),
            algorithm="HS256",
        ),
        jwt.encode(
            {
                "sub": str(user_id),
                "type": "refresh",
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(minutes=1),
            },
            settings.secret_key.get_secret_value(),
            algorithm="HS256",
        ),
    ):
        with pytest.raises(ValueError, match="Invalid access token"):
            decode_access_token(bad, settings)


def test_refresh_token_is_opaque_and_digest_only() -> None:
    first, second = new_refresh_token(), new_refresh_token()
    assert first != second
    assert len(first) >= 40
    assert len(refresh_digest(first)) == 64
    assert first not in refresh_digest(first)

"""Cryptographic boundary checks."""

import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core import security
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


@pytest.mark.asyncio
async def test_password_work_is_offloaded_from_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    loop_thread = threading.get_ident()
    worker_threads: list[int] = []

    def fake_hash(password: str) -> str:
        worker_threads.append(threading.get_ident())
        return f"hash:{password}"

    def fake_verify(password: str, hashed: str) -> bool:
        worker_threads.append(threading.get_ident())
        return hashed == f"hash:{password}"

    monkeypatch.setattr(security, "hash_password", fake_hash)
    monkeypatch.setattr(security, "verify_password", fake_verify)
    hashed = await security.hash_password_async("test-password")
    assert await security.verify_password_async("test-password", hashed)
    assert len(worker_threads) == 2
    assert all(thread != loop_thread for thread in worker_threads)

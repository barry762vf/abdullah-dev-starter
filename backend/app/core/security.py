"""Password and token primitives. Raw credentials must never be logged."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import anyio
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings

ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 14
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
_hasher = PasswordHasher()
# Each Argon2 operation uses substantial memory. Limit this work independently
# of AnyIO's general-purpose worker pool so auth bursts cannot spawn 40 hashes.
_password_limiter = anyio.CapacityLimiter(2)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


async def hash_password_async(password: str) -> str:
    return await anyio.to_thread.run_sync(hash_password, password, limiter=_password_limiter)


async def verify_password_async(password: str, hashed_password: str) -> bool:
    return await anyio.to_thread.run_sync(
        verify_password, password, hashed_password, limiter=_password_limiter
    )


def create_access_token(user_id: UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        },
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "type", "iat", "exp"]},
            leeway=0,
        )
        if payload.get("type") != "access":
            raise ValueError("Wrong token type")
        return UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as error:
        raise ValueError("Invalid access token") from error


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def refresh_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

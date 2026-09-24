"""Password and token primitives. Raw credentials must never be logged."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings

ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 14
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": str(user_id), "type": "access", "iat": now, "exp": now + timedelta(minutes=15)},
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

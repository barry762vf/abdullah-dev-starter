"""Transactional registration, login, refresh rotation, and logout."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.security import (
    REFRESH_TOKEN_DAYS,
    create_access_token,
    hash_password,
    hash_password_async,
    new_refresh_token,
    refresh_digest,
    verify_password_async,
)
from app.models import AuditLog, RefreshToken, Role, User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.user_service import load_user, profile

_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))

# Account-aware throttle shared by every worker and instance through PostgreSQL (ADR 014): failed
# logins since the last success within the window. Complements per-IP limits at the proxy/edge.
LOGIN_FAILURE_LIMIT = 10
LOGIN_FAILURE_WINDOW = timedelta(minutes=15)


def add_audit(
    db: AsyncSession, action: str, user_id: UUID | None, ip: str | None, agent: str | None
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity="user",
            entity_id=str(user_id) if user_id else None,
            ip_address=ip[:45] if ip else None,
            user_agent=agent[:512] if agent else None,
            details={},
        )
    )


async def register(db: AsyncSession, data: RegisterRequest, ip: str | None, agent: str | None):
    role = await db.scalar(select(Role).where(Role.name == "user"))
    if role is None:
        raise AppException(503, "Service Unavailable", "Registration is not configured.")
    hashed_password = await hash_password_async(data.password)
    user = User(email=str(data.email), hashed_password=hashed_password, full_name=data.full_name)
    try:
        db.add(user)
        await db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        add_audit(db, "auth.register", user.id, ip, agent)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise AppException(409, "Conflict", "Email is already registered.") from None
        if getattr(error.orig, "sqlstate", None) == "23503":
            raise AppException(
                503, "Service Unavailable", "Registration is not configured."
            ) from None
        raise
    loaded = await load_user(db, user.id)
    return profile(loaded)


async def recent_login_failures(db: AsyncSession, user_id: UUID) -> int:
    last_success = (
        select(func.max(AuditLog.created_at))
        .where(AuditLog.user_id == user_id, AuditLog.action == "auth.login")
        .scalar_subquery()
    )
    window_start = func.now() - LOGIN_FAILURE_WINDOW
    return await db.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.user_id == user_id,
            AuditLog.action == "auth.login_failed",
            AuditLog.created_at
            > func.greatest(window_start, func.coalesce(last_success, window_start)),
        )
    )


async def login(
    db: AsyncSession, data: LoginRequest, settings: Settings, ip: str | None, agent: str | None
):
    user = await db.scalar(select(User).where(func.lower(User.email) == str(data.email)))
    if user is not None and await recent_login_failures(db, user.id) >= LOGIN_FAILURE_LIMIT:
        # Checked before Argon2 so a targeted attack also cannot consume password-hashing CPU.
        add_audit(db, "auth.login_throttled", user.id, ip, agent)
        await db.commit()
        raise AppException(429, "Too Many Requests", "Too many failed sign-in attempts.")
    password_matches = await verify_password_async(
        data.password, user.hashed_password if user else _DUMMY_PASSWORD_HASH
    )
    if user is None or not password_matches or not user.is_active:
        add_audit(db, "auth.login_failed", user.id if user else None, ip, agent)
        await db.commit()
        raise AppException(401, "Unauthorized", "Invalid credentials.")
    raw = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_digest(raw),
            expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_DAYS),
        )
    )
    add_audit(db, "auth.login", user.id, ip, agent)
    await db.commit()
    loaded = await load_user(db, user.id)
    return profile(loaded), create_access_token(user.id, settings), raw


async def refresh(
    db: AsyncSession, raw: str, settings: Settings, ip: str | None, agent: str | None
):
    digest = refresh_digest(raw)
    consumed = await db.scalar(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == digest,
            RefreshToken.is_revoked.is_(False),
            RefreshToken.expires_at > func.now(),
        )
        .values(is_revoked=True, revoked_at=func.now())
        .returning(RefreshToken.user_id)
    )
    if consumed is None:
        known = (
            await db.execute(
                select(
                    RefreshToken.user_id,
                    RefreshToken.is_revoked,
                    (RefreshToken.expires_at > func.now()).label("unexpired"),
                ).where(RefreshToken.token_hash == digest)
            )
        ).one_or_none()
        if known is not None and known.is_revoked and known.unexpired:
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == known.user_id, RefreshToken.is_revoked.is_(False))
                .values(is_revoked=True, revoked_at=func.now())
            )
            add_audit(db, "auth.refresh_reuse", known.user_id, ip, agent)
            await db.commit()
        raise AppException(401, "Unauthorized", "Invalid refresh token.")
    user = await load_user(db, consumed)
    if user is None or not user.is_active:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == consumed, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True, revoked_at=func.now())
        )
        await db.commit()
        raise AppException(401, "Unauthorized", "Invalid refresh token.")
    successor = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_digest(successor),
            expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_DAYS),
        )
    )
    add_audit(db, "auth.refresh", user.id, ip, agent)
    await db.commit()
    return profile(user), create_access_token(user.id, settings), successor


async def logout(db: AsyncSession, raw: str | None, ip: str | None, agent: str | None) -> None:
    if raw:
        user_id = await db.scalar(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == refresh_digest(raw), RefreshToken.is_revoked.is_(False)
            )
            .values(is_revoked=True, revoked_at=func.now())
            .returning(RefreshToken.user_id)
        )
        if user_id is not None:
            add_audit(db, "auth.logout", user_id, ip, agent)
    await db.commit()

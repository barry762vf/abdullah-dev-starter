"""Live auth lifecycle on rollback-only dedicated test database transactions."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import require_role
from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.security import REFRESH_COOKIE, hash_password, new_refresh_token, refresh_digest
from app.core.seed import bootstrap_superadmin, seed_roles
from app.main import create_app
from app.models import AuditLog, RefreshToken, Role, User, UserRole

CSRF = {"X-Requested-With": "XMLHttpRequest"}
PASSWORD = "Test-password-123!"


@pytest.fixture
async def auth_env(test_database_url: str):
    engine = create_async_engine(test_database_url, hide_parameters=True)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            factory = async_sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            async with factory() as db:
                await seed_roles(db)
                await db.commit()
            settings = Settings(
                _env_file=None,
                secret_key="test-only-signing-secret",
                database_url=test_database_url,
            )
            app = create_app(settings)
            app.state.session_factory = factory
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client, factory, settings
        finally:
            await transaction.rollback()
    await engine.dispose()


async def register(client: AsyncClient, email: str = "person@example.com"):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": " Person "},
    )


async def login(client: AsyncClient, email: str = "person@example.com", password: str = PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


@pytest.mark.asyncio
async def test_register_login_profile_update_and_logout(auth_env, capfd):
    client, factory, _ = auth_env
    created = await register(client, " Person@Example.Com ")
    assert created.status_code == 201, created.text
    assert created.json()["email"] == "person@example.com"
    assert created.json()["roles"] == ["user"]
    assert "password" not in created.text
    assert (await register(client, "PERSON@example.com")).status_code == 409
    privileged = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@example.com",
            "password": PASSWORD,
            "full_name": "X",
            "roles": ["admin"],
        },
    )
    assert privileged.status_code == 422
    async with factory() as db:
        user = await db.scalar(select(User).where(User.email == "person@example.com"))
        assert user.hashed_password.startswith("$argon2id$")
        assert PASSWORD not in user.hashed_password
    assert (await login(client, password="wrong-password")).status_code == 401
    assert (await login(client, email="nobody@example.com")).status_code == 401
    logged = await login(client)
    assert logged.status_code == 200, logged.text
    assert "httponly" in logged.headers["set-cookie"].lower()
    assert "samesite=lax" in logged.headers["set-cookie"].lower()
    access = client.cookies.get("access_token")
    raw = client.cookies.get(REFRESH_COOKIE)
    assert access and raw
    assert (await client.get("/api/v1/users/me")).status_code == 200
    assert (await client.patch("/api/v1/users/me", json={"full_name": "New"})).status_code == 403
    changed = await client.patch("/api/v1/users/me", headers=CSRF, json={"full_name": "New"})
    assert changed.status_code == 200 and changed.json()["full_name"] == "New"
    async with factory() as db:
        stored = await db.scalar(select(RefreshToken).where(RefreshToken.user_id == user.id))
        assert stored.token_hash == refresh_digest(raw)
        assert raw not in stored.token_hash
        actions = set((await db.scalars(select(AuditLog.action))).all())
        assert {"auth.register", "auth.login", "auth.login_failed"} <= actions
    logs = capfd.readouterr().err
    for secret in (
        PASSWORD,
        user.hashed_password,
        raw,
        stored.token_hash,
        "test-only-signing-secret",
    ):
        assert secret not in logs
    assert (await client.post("/api/v1/auth/logout", headers=CSRF)).status_code == 204
    client.cookies.set(REFRESH_COOKIE, raw, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401
    async with factory() as db:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == refresh_digest(raw))
            .values(is_revoked=True, revoked_at=datetime.now(UTC))
        )
        await db.commit()
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401


@pytest.mark.asyncio
async def test_missing_role_and_disabled_account(auth_env):
    client, factory, _ = auth_env
    async with factory() as db:
        await db.execute(delete(Role).where(Role.name == "user"))
        await db.commit()
    assert (await register(client)).status_code == 503
    async with factory() as db:
        await seed_roles(db)
        await db.commit()
    assert (await register(client)).status_code == 201
    assert (await login(client)).status_code == 200
    access = client.cookies.get("access_token")
    async with factory() as db:
        user = await db.scalar(select(User).where(User.email == "person@example.com"))
        user.is_active = False
        await db.commit()
    assert (
        await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
    ).status_code == 401
    assert (await login(client)).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401


@pytest.mark.asyncio
async def test_jwt_and_current_roles_are_database_authoritative(auth_env):
    client, factory, settings = auth_env
    app = client._transport.app
    admin_guard = require_role(["admin"])

    async def admin_route(user: Annotated[User, Depends(admin_guard)]):
        return {"id": str(user.id)}

    app.add_api_route("/test/admin", admin_route)
    await register(client)
    await login(client)
    access = client.cookies.get("access_token")
    bearer = {"Authorization": f"Bearer {access}"}
    assert (await client.get("/test/admin", headers=bearer)).status_code == 403
    async with factory() as db:
        user = await db.scalar(select(User).where(User.email == "person@example.com"))
        admin = await db.scalar(select(Role).where(Role.name == "admin"))
        db.add(UserRole(user_id=user.id, role_id=admin.id))
        await db.commit()
    assert (await client.get("/test/admin", headers=bearer)).status_code == 200
    async with factory() as db:
        await db.execute(
            delete(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == admin.id)
        )
        await db.commit()
    assert (await client.get("/test/admin", headers=bearer)).status_code == 403
    async with factory() as db:
        superadmin = await db.scalar(select(Role).where(Role.name == "superadmin"))
        db.add(UserRole(user_id=user.id, role_id=superadmin.id))
        await db.commit()
    assert (await client.get("/test/admin", headers=bearer)).status_code == 200
    for bad in ("malformed", access + "tamper"):
        assert (
            await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {bad}"})
        ).status_code == 401
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "type": "access",
            "iat": datetime.now(UTC) - timedelta(hours=1),
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )
    assert (
        await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired}"})
    ).status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotation_reuse_and_unknown(auth_env):
    client, factory, _ = auth_env
    await register(client)
    await login(client)
    first = client.cookies.get(REFRESH_COOKIE)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 403
    rotated = await client.post("/api/v1/auth/refresh", headers=CSRF)
    assert rotated.status_code == 200, rotated.text
    second = client.cookies.get(REFRESH_COOKIE)
    assert first != second
    client.cookies.set(REFRESH_COOKIE, "unknown-token", path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401
    async with factory() as db:
        successor = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == refresh_digest(second))
        )
        assert not successor.is_revoked
    client.cookies.set(REFRESH_COOKIE, first, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401
    async with factory() as db:
        successor = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == refresh_digest(second))
        )
        assert successor.is_revoked and successor.revoked_at is not None
        assert await db.scalar(select(AuditLog).where(AuditLog.action == "auth.refresh_reuse"))
    client.cookies.set(REFRESH_COOKIE, second, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401


@pytest.mark.asyncio
async def test_expired_refresh_and_unknown_logout(auth_env):
    client, factory, _ = auth_env
    await register(client)
    await login(client)
    raw = client.cookies.get(REFRESH_COOKIE)
    await login(client)
    still_valid = client.cookies.get(REFRESH_COOKIE)
    async with factory() as db:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == refresh_digest(raw))
            # A wide margin: inside the rollback fixture PostgreSQL now() is frozen at the outer
            # transaction start, so a 1 s margin can still be "in the future" on a slow run.
            .values(expires_at=datetime.now(UTC) - timedelta(days=1))
        )
        await db.commit()
    client.cookies.set(REFRESH_COOKIE, raw, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401
    async with factory() as db:
        valid_row = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == refresh_digest(still_valid))
        )
        assert not valid_row.is_revoked
    client.cookies.set(REFRESH_COOKIE, "unknown-token", path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/logout", headers=CSRF)).status_code == 204
    async with factory() as db:
        valid_row = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == refresh_digest(still_valid))
        )
        assert not valid_row.is_revoked


@pytest.mark.asyncio
async def test_bootstrap_once_without_permanent_secret(auth_env):
    _, factory, settings = auth_env
    with pytest.raises(ValueError, match="INITIAL_ADMIN"):
        async with factory.begin() as db:
            await bootstrap_superadmin(db, settings)
    settings = Settings(
        _env_file=None,
        secret_key="test-only-signing-secret",
        database_url=settings.database_url,
        initial_admin_email="admin@example.com",
        initial_admin_password="Admin123!Secure",
    )
    with pytest.raises(ValueError, match="INITIAL_ADMIN"):
        async with factory.begin() as db:
            await bootstrap_superadmin(db, settings)
    settings.initial_admin_password = type(settings.initial_admin_password)(
        "Unique-bootstrap-pass-123!"
    )
    async with factory.begin() as db:
        assert await bootstrap_superadmin(db, settings)
    settings.initial_admin_password = type(settings.initial_admin_password)("")
    async with factory.begin() as db:
        assert not await bootstrap_superadmin(db, settings)
        admin = await db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin.hashed_password.startswith("$argon2id$")
    assert settings.initial_admin_password.get_secret_value() == ""


@pytest.mark.asyncio
async def test_rate_limits(auth_env):
    client, _, _ = auth_env
    for index in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": PASSWORD},
            headers={"X-Forwarded-For": f"203.0.113.{index}"},
        )
        assert response.status_code == 401
    assert (await login(client, email="nobody@example.com")).status_code == 429
    for index in range(3):
        assert (await register(client, f"limited-{index}@example.com")).status_code == 201
    assert (await register(client, "limited-3@example.com")).status_code == 429


@pytest.mark.asyncio
async def test_public_auth_routes_reject_form_and_plain_text(auth_env):
    client, _, _ = auth_env
    for path in ("/api/v1/auth/register", "/api/v1/auth/login"):
        plain = await client.post(
            path,
            content='{"email":"person@example.com","password":"Test-password-123!"}',
            headers={"Content-Type": "text/plain"},
        )
        form = await client.post(
            path,
            data={"email": "person@example.com", "password": PASSWORD, "full_name": "Person"},
        )
        assert plain.status_code == 422
        assert form.status_code == 422


@pytest.mark.asyncio
async def test_concurrent_refresh_consumes_token_once(test_database_url: str):
    """Use independent connections to exercise PostgreSQL's conditional row update."""
    engine = create_async_engine(test_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None, secret_key="test-only-signing-secret", database_url=test_database_url
    )
    email = f"concurrent-{uuid4()}@example.com"
    raw = new_refresh_token()
    try:
        async with factory.begin() as db:
            user = User(
                email=email, hashed_password=hash_password(PASSWORD), full_name="Concurrent"
            )
            db.add(user)
            await db.flush()
            db.add(
                RefreshToken(
                    user_id=user.id,
                    token_hash=refresh_digest(raw),
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                )
            )
        from app.services.auth_service import refresh

        async def attempt():
            async with factory() as db:
                try:
                    return await refresh(db, raw, settings, "127.0.0.1", "pytest")
                except AppException as error:
                    return error.status_code

        results = await asyncio.gather(attempt(), attempt())
        assert sum(isinstance(item, tuple) for item in results) == 1
        assert results.count(401) == 1
        async with factory() as db:
            rows = (
                await db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id))
            ).all()
            assert len(rows) == 2
            assert all(row.is_revoked for row in rows)  # Replay invalidates the successor.
    finally:
        async with factory.begin() as db:
            await db.execute(delete(AuditLog).where(AuditLog.user_id == user.id))
            await db.execute(delete(User).where(User.id == user.id))
        await engine.dispose()

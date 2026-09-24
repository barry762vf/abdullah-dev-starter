"""Phase 6 security regressions for sessions, cookies, route protection and concurrency.

Rollback-only fixtures for request-level cases; independent committed connections (cleaned up)
only where real PostgreSQL concurrency is the property under test.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_active_user
from app.core import seed
from app.core.config import Settings
from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import REFRESH_COOKIE, hash_password, new_refresh_token, refresh_digest
from app.main import create_app
from app.models import AuditLog, RefreshToken, Role, User, UserRole
from app.services import auth_service

PASSWORD = "Regression-password-123!"
PASSWORD_HASH = hash_password(PASSWORD)
CSRF = {"X-Requested-With": "XMLHttpRequest"}
SECRET = "test-only-signing-secret"
PUBLIC_ROUTES = {
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/ready"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),  # authenticated by the refresh cookie itself
    ("POST", "/api/v1/auth/logout"),
}


def settings_for(url: str, **overrides) -> Settings:
    return Settings(_env_file=None, secret_key=SECRET, database_url=url, **overrides)


@pytest.fixture
async def env(test_database_url: str):
    """Rollback-only app; yields (client, session factory, app)."""
    engine = create_async_engine(test_database_url, hide_parameters=True)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            factory = async_sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            async with factory() as db:
                await seed.seed_roles(db)
                await db.commit()
            app = create_app(settings_for(test_database_url))
            app.state.session_factory = factory
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                yield c, factory, app
        finally:
            await transaction.rollback()
    await engine.dispose()


async def add_user(factory, email: str, role: str = "user") -> User:
    async with factory() as db:
        user = User(email=email, hashed_password=PASSWORD_HASH, full_name="Regression")
        db.add(user)
        await db.flush()
        role_row = await db.scalar(select(Role).where(Role.name == role))
        db.add(UserRole(user_id=user.id, role_id=role_row.id))
        await db.commit()
        return user


async def login(client: AsyncClient, email: str):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response


def _depends_on(dependant, target) -> bool:
    return any(d.call is target or _depends_on(d, target) for d in dependant.dependencies)


@pytest.mark.asyncio
async def test_every_non_public_route_requires_an_active_user(env):
    _, _, app = env
    api_routes = [r for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/api")]
    seen = set()
    for route in api_routes:
        for method in route.methods:
            seen.add((method, route.path))
            if (method, route.path) not in PUBLIC_ROUTES:
                assert _depends_on(route.dependant, get_current_active_user), (method, route.path)
    assert PUBLIC_ROUTES <= seen  # the public list must stay accurate


@pytest.mark.asyncio
async def test_valid_token_for_deleted_user_is_rejected(env):
    client, factory, _ = env
    user = await add_user(factory, "deleted@example.com")
    await login(client, "deleted@example.com")
    token = client.cookies.get("access_token")
    async with factory() as db:
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()
    bearer = {"Authorization": f"Bearer {token}"}
    assert (await client.get("/api/v1/users/me", headers=bearer)).status_code == 401
    assert (await client.get("/api/v1/users/me")).status_code == 401  # cookie transport too
    refreshed = await client.post("/api/v1/auth/refresh", headers=CSRF)
    assert refreshed.status_code == 401  # tokens cascaded away with the user


@pytest.mark.asyncio
@pytest.mark.parametrize("secure", [True, False])
async def test_cookie_attributes_on_login_and_logout(test_database_url: str, env, secure: bool):
    client, factory, app = env
    app.state.settings = settings_for(test_database_url, cookie_secure=secure)
    await add_user(factory, "cookie@example.com")
    cookies = (await login(client, "cookie@example.com")).headers.get_list("set-cookie")
    access = next(c for c in cookies if c.startswith("access_token="))
    refresh = next(c for c in cookies if c.startswith("refresh_token="))
    for cookie, path, max_age in ((access, "/api/v1", 900), (refresh, "/api/v1/auth", 1209600)):
        attributes = [part.strip().lower() for part in cookie.split(";")]
        assert f"path={path}" in attributes and f"max-age={max_age}" in attributes
        assert "httponly" in attributes and "samesite=lax" in attributes
        assert ("secure" in attributes) is secure
        assert not any(part.startswith("domain=") for part in attributes)  # host-only
    cleared = (await client.post("/api/v1/auth/logout", headers=CSRF)).headers.get_list(
        "set-cookie"
    )
    for name, path in (("access_token", "/api/v1"), ("refresh_token", "/api/v1/auth")):
        cookie = next(c for c in cleared if c.startswith(f"{name}="))
        attributes = [part.strip().lower() for part in cookie.split(";")]
        assert f"path={path}" in attributes and "max-age=0" in attributes


@pytest.mark.asyncio
async def test_refresh_for_disabled_user_revokes_every_session(env):
    client, factory, _ = env
    user = await add_user(factory, "disabled@example.com")
    await login(client, "disabled@example.com")
    other_device = client.cookies.get(REFRESH_COOKIE)
    await login(client, "disabled@example.com")
    async with factory() as db:
        await db.execute(User.__table__.update().where(User.id == user.id).values(is_active=False))
        await db.commit()
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401
    async with factory() as db:
        live = await db.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.is_revoked.is_(False))
        )
        total = await db.scalar(
            select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user.id)
        )
    assert live == 0 and total == 2  # both sessions revoked, no successor issued
    client.cookies.set(REFRESH_COOKIE, other_device, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401


@pytest.mark.asyncio
async def test_failure_after_consuming_refresh_token_rolls_back(env, monkeypatch):
    client, factory, _ = env
    await add_user(factory, "rollback@example.com")
    await login(client, "rollback@example.com")
    raw = client.cookies.get(REFRESH_COOKIE)
    original = auth_service.add_audit

    def failing_audit(db, action, *args):
        if action == "auth.refresh":
            raise RuntimeError("simulated failure after the conditional UPDATE")
        return original(db, action, *args)

    monkeypatch.setattr(auth_service, "add_audit", failing_audit)
    failed = await client.post("/api/v1/auth/refresh", headers=CSRF)
    assert failed.status_code == 500
    assert "set-cookie" not in failed.headers  # no cookie before a successful commit
    async with factory() as db:
        row = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == refresh_digest(raw))
        )
        count = await db.scalar(select(func.count()).select_from(RefreshToken))
    assert row.is_revoked is False and row.revoked_at is None and count == 1
    monkeypatch.setattr(auth_service, "add_audit", original)
    client.cookies.set(REFRESH_COOKIE, raw, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 200


@pytest.mark.asyncio
async def test_reuse_and_bootstrap_paths_keep_secrets_out_of_logs(test_database_url, env, capfd):
    client, factory, _ = env
    await add_user(factory, "logs@example.com")
    await login(client, "logs@example.com")
    first = client.cookies.get(REFRESH_COOKIE)
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 200
    second = client.cookies.get(REFRESH_COOKIE)
    client.cookies.set(REFRESH_COOKIE, first, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401  # reuse
    bootstrap_password = "Bootstrap-secret-value-42!"
    async with factory.begin() as db:
        created = await seed.bootstrap_superadmin(
            db,
            settings_for(
                test_database_url,
                initial_admin_email="root@example.com",
                initial_admin_password=bootstrap_password,
            ),
        )
    assert created
    async with factory() as db:
        details = [log.details for log in await db.scalars(select(AuditLog))]
        actions = set(await db.scalars(select(AuditLog.action)))
        root_hash = await db.scalar(
            select(User.hashed_password).where(User.email == "root@example.com")
        )
    assert {"auth.refresh_reuse", "auth.bootstrap"} <= actions
    output = capfd.readouterr()
    logs = output.out + output.err + repr(details)
    for secret in (
        first,
        second,
        refresh_digest(first),
        refresh_digest(second),
        bootstrap_password,
        root_hash,
        PASSWORD,
        SECRET,
    ):
        assert secret not in logs


async def _lock_waiters(engine, event: str | None = None) -> int:
    query = (
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
        "AND wait_event_type = 'Lock'" + (" AND wait_event = :event" if event else "")
    )
    async with engine.connect() as connection:
        return await connection.scalar(text(query), {"event": event} if event else {})


async def _wait_for_waiter(engine, event: str | None = None) -> bool:
    for _ in range(100):
        if await _lock_waiters(engine, event):
            return True
        await asyncio.sleep(0.05)
    return False


@pytest.mark.asyncio
async def test_true_concurrent_refresh_cannot_create_two_sessions(test_database_url, monkeypatch):
    """Hold the first refresh after its UPDATE until the second is blocked on the row lock."""
    engine = create_async_engine(test_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    email = f"race-{uuid4().hex[:8]}@example.com"
    raw = new_refresh_token()
    proven = []
    original_load = auth_service.load_user

    async def load_after_second_blocks(db: AsyncSession, user_id):
        if not proven:
            proven.append(await _wait_for_waiter(engine))
        return await original_load(db, user_id)

    monkeypatch.setattr(auth_service, "load_user", load_after_second_blocks)
    try:
        async with factory.begin() as db:
            user = User(email=email, hashed_password=PASSWORD_HASH, full_name="Race")
            db.add(user)
            await db.flush()
            db.add(
                RefreshToken(
                    user_id=user.id,
                    token_hash=refresh_digest(raw),
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                )
            )
        settings = settings_for(test_database_url)

        async def attempt():
            async with factory() as db:
                try:
                    return await auth_service.refresh(db, raw, settings, None, None)
                except AppException as error:
                    return error.status_code

        results = await asyncio.gather(attempt(), attempt())
        assert proven == [True]  # the second request really was blocked mid-transaction
        assert sum(isinstance(result, tuple) for result in results) == 1
        assert results.count(401) == 1
        async with factory() as db:
            rows = (
                await db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id))
            ).all()
        assert len(rows) == 2 and all(row.is_revoked for row in rows)  # ADR 009 strict reuse
    finally:
        async with factory.begin() as db:
            ids = (await db.scalars(select(User.id).where(User.email == email))).all()
            await db.execute(delete(AuditLog).where(AuditLog.user_id.in_(ids)))
            await db.execute(delete(User).where(User.id.in_(ids)))
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_bootstraps_create_exactly_one_superadmin(test_database_url, monkeypatch):
    engine = create_async_engine(test_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    emails = [f"boot-{uuid4().hex[:8]}@example.com" for _ in range(2)]
    proven = []
    original_hash = seed.hash_password_async

    async def hash_after_second_waits(password: str) -> str:
        if not proven:
            proven.append(await _wait_for_waiter(engine, "advisory"))
        return await original_hash(password)

    monkeypatch.setattr(seed, "hash_password_async", hash_after_second_waits)
    try:
        # Commit roles first: otherwise the second bootstrap blocks on the first one's uncommitted
        # role insert instead of on the advisory lock this test is proving.
        async with factory.begin() as db:
            await seed.seed_roles(db)
        async with factory() as db:
            existing = await db.scalar(
                select(func.count())
                .select_from(UserRole)
                .join(Role)
                .where(Role.name == "superadmin")
            )
        if existing:
            pytest.skip("test database already contains a superadmin")

        async def attempt(email: str) -> bool:
            async with factory.begin() as db:
                await seed.seed_roles(db)
                return await seed.bootstrap_superadmin(
                    db,
                    settings_for(
                        test_database_url,
                        initial_admin_email=email,
                        initial_admin_password="Unique-bootstrap-pass-9!",
                    ),
                )

        results = await asyncio.gather(*(attempt(email) for email in emails))
        assert proven == [True]  # the second bootstrap waited on the advisory lock
        assert sorted(results) == [False, True]
        async with factory() as db:
            count = await db.scalar(
                select(func.count())
                .select_from(UserRole)
                .join(Role)
                .where(Role.name == "superadmin")
            )
        assert count == 1
    finally:
        async with factory.begin() as db:
            ids = (await db.scalars(select(User.id).where(User.email.in_(emails)))).all()
            await db.execute(delete(AuditLog).where(AuditLog.user_id.in_(ids)))
            await db.execute(delete(User).where(User.id.in_(ids)))
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_db_rolls_back_and_releases_connection_when_handler_raises(test_database_url):
    """Uses the app's real session factory against the test database (no outer transaction)."""
    app = create_app(settings_for(test_database_url))
    marker = f"rollback-{uuid4().hex[:8]}"

    @app.post("/boom")
    async def boom(db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        db.add(Role(name=marker, description="must not persist"))
        await db.flush()
        raise RuntimeError("handler failure after a write")

    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/boom")
            assert response.status_code == 500
            assert app.state.engine.pool.checkedout() == 0
            async with app.state.session_factory() as db:
                assert await db.scalar(select(Role).where(Role.name == marker)) is None
    finally:
        engine = create_async_engine(test_database_url)
        async with engine.begin() as connection:
            await connection.execute(delete(Role).where(Role.name == marker))
        await engine.dispose()


@pytest.mark.asyncio
async def test_authorization_header_never_falls_back_to_the_cookie(env):
    client, factory, _ = env
    await add_user(factory, "header@example.com")
    await login(client, "header@example.com")
    assert (await client.get("/api/v1/users/me")).status_code == 200
    for header in ("Basic abc", "Bearer", "Bearer ", "Token abc"):
        response = await client.get("/api/v1/users/me", headers={"Authorization": header})
        assert response.status_code == 401, header
    client.cookies.delete(REFRESH_COOKIE, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh", headers=CSRF)).status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_never_promotes_an_existing_account(test_database_url, env):
    client, factory, _ = env
    squatter = await add_user(factory, "owner@example.com")  # e.g. registered before bootstrap
    settings = settings_for(
        test_database_url,
        initial_admin_email="OWNER@example.com",
        initial_admin_password="Unique-bootstrap-pass-9!",
    )
    with pytest.raises(ValueError, match="already belongs"):
        async with factory.begin() as db:
            await seed.bootstrap_superadmin(db, settings)
    async with factory() as db:
        roles = set(
            await db.scalars(
                select(Role.name).join(UserRole).where(UserRole.user_id == squatter.id)
            )
        )
        await db.execute(delete(Role).where(Role.name == "superadmin"))
        await db.commit()
    assert roles == {"user"}
    fresh = settings_for(
        test_database_url,
        initial_admin_email="new-owner@example.com",
        initial_admin_password="Unique-bootstrap-pass-9!",
    )
    with pytest.raises(ValueError, match="must be seeded"):
        async with factory.begin() as db:
            await seed.bootstrap_superadmin(db, fresh)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["‮evil", "a‭name", "​‌", "line\nbreak", " "])
async def test_spoofing_and_control_characters_in_names_are_rejected(env, name: str):
    client, factory, _ = env
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "name@example.com", "password": PASSWORD, "full_name": name},
    )
    assert registered.status_code == 422
    await add_user(factory, "profile@example.com")
    await login(client, "profile@example.com")
    updated = await client.patch("/api/v1/users/me", json={"full_name": name}, headers=CSRF)
    assert updated.status_code == 422


@pytest.mark.asyncio
async def test_account_login_throttle_is_shared_and_resets(test_database_url: str):
    """Counts come from PostgreSQL, so every worker/instance sees the same limit.

    Uses committed rows (cleaned up): inside one rollback transaction PostgreSQL's now() is
    frozen, which would make every audit row share one timestamp.
    """
    app = create_app(settings_for(test_database_url))
    app.state.auth_rate_limiter.check = lambda *args: None  # isolate from the per-IP limiter
    factory = app.state.session_factory
    emails = [f"{name}-{uuid4().hex[:8]}@example.com" for name in ("target", "bystander")]
    try:
        async with factory() as db:
            await seed.seed_roles(db)
            await db.commit()
        user = await add_user(factory, emails[0])
        await add_user(factory, emails[1])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:

            async def attempt(email: str, password: str) -> int:
                body = {"email": email, "password": password}
                return (await client.post("/api/v1/auth/login", json=body)).status_code

            for _ in range(auth_service.LOGIN_FAILURE_LIMIT - 1):
                assert await attempt(emails[0], "wrong-password-x") == 401
            assert await attempt(emails[0], PASSWORD) == 200  # success resets the count
            for _ in range(auth_service.LOGIN_FAILURE_LIMIT):
                assert await attempt(emails[0], "wrong-password-x") == 401
            # The correct password is refused while throttled, before any password check.
            assert await attempt(emails[0], PASSWORD) == 429
            assert await attempt(emails[1], PASSWORD) == 200  # other accounts unaffected
            async with factory() as db:
                throttled = await db.scalar(
                    select(func.count())
                    .select_from(AuditLog)
                    .where(AuditLog.action == "auth.login_throttled", AuditLog.user_id == user.id)
                )
                await db.execute(
                    AuditLog.__table__.update()
                    .where(AuditLog.user_id == user.id, AuditLog.action == "auth.login_failed")
                    .values(created_at=func.now() - timedelta(minutes=16))
                )
                await db.commit()
            assert throttled == 1
            assert await attempt(emails[0], PASSWORD) == 200  # window expired
    finally:
        async with factory.begin() as db:
            ids = (await db.scalars(select(User.id).where(User.email.in_(emails)))).all()
            await db.execute(delete(AuditLog).where(AuditLog.user_id.in_(ids)))
            await db.execute(delete(User).where(User.id.in_(ids)))
        await app.state.engine.dispose()

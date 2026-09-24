"""Phase 5 administration on rollback-only transactions of the dedicated test database."""

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.admin import admin_only
from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.security import REFRESH_COOKIE, hash_password
from app.core.seed import seed_roles
from app.main import create_app
from app.models import AuditLog, RefreshToken, Role, User, UserRole
from app.schemas.admin import AdminUserUpdate
from app.services import admin_service
from app.services.user_service import load_user

PASSWORD = "Admin-test-password-123!"
PASSWORD_HASH = hash_password(PASSWORD)
CSRF = {"X-Requested-With": "XMLHttpRequest"}
ADMIN_ROUTES = [
    ("GET", "/api/v1/admin/users"),
    ("GET", "/api/v1/admin/stats"),
    ("GET", "/api/v1/admin/audit-logs"),
    ("PATCH", f"/api/v1/admin/users/{uuid4()}"),
]


@pytest.fixture
async def admin_env(test_database_url: str):
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
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                yield c, factory, app
        finally:
            await transaction.rollback()
    await engine.dispose()


async def make_user(factory, email: str, *roles: str, active: bool = True) -> User:
    async with factory() as db:
        user = User(
            email=email,
            hashed_password=PASSWORD_HASH,
            full_name=email.split("@")[0],
            is_active=active,
        )
        db.add(user)
        await db.flush()
        for role in await db.scalars(select(Role).where(Role.name.in_(roles or ("user",)))):
            db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()
        return user


async def bearer(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    token = client.cookies.get("access_token")
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_every_admin_route_requires_admin_role(admin_env):
    client, factory, app = admin_env
    admin_paths = {
        (method, route.path)
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/v1/admin")
        for method in route.methods
    }
    # A new admin route must be added here (and therefore tested) deliberately.
    assert admin_paths == {
        ("GET", "/api/v1/admin/users"),
        ("PATCH", "/api/v1/admin/users/{user_id}"),
        ("GET", "/api/v1/admin/stats"),
        ("GET", "/api/v1/admin/audit-logs"),
    }
    for route in app.routes:
        if getattr(route, "path", "").startswith("/api/v1/admin"):
            assert any(dep.dependency is admin_only for dep in route.dependencies)

    await make_user(factory, "plain@example.com", "user")
    await make_user(factory, "admin@example.com", "admin")
    await make_user(factory, "root@example.com", "superadmin")
    user_headers = await bearer(client, "plain@example.com")
    admin_headers = await bearer(client, "admin@example.com")
    root_headers = await bearer(client, "root@example.com")
    for method, path in ADMIN_ROUTES:
        body = {"is_active": False} if method == "PATCH" else None
        # With the CSRF header the unauthenticated request reaches the token check (401).
        assert (await client.request(method, path, json=body, headers=CSRF)).status_code == 401
        denied = await client.request(method, path, json=body, headers=user_headers)
        assert denied.status_code == 403, (method, path)
    for method, path in ADMIN_ROUTES[:3]:
        assert (await client.request(method, path, headers=admin_headers)).status_code == 200
        assert (await client.request(method, path, headers=root_headers)).status_code == 200


@pytest.mark.asyncio
async def test_user_list_paginates_filters_and_hides_secrets(admin_env):
    client, factory, _ = admin_env
    await make_user(factory, "admin@example.com", "admin")
    for index in range(5):
        await make_user(factory, f"member{index}@example.com", "user")
    await make_user(factory, "Mixed.Case@Example.com", "user")
    await make_user(factory, "percent_100@example.com", "user")
    headers = await bearer(client, "admin@example.com")

    first = await client.get("/api/v1/admin/users?page=1&page_size=3", headers=headers)
    second = await client.get("/api/v1/admin/users?page=2&page_size=3", headers=headers)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["total"] == 8 and first.json()["page_size"] == 3
    first_ids = {item["id"] for item in first.json()["items"]}
    assert len(first_ids) == 3 and first_ids.isdisjoint(i["id"] for i in second.json()["items"])
    for text in (first.text, second.text):
        assert "hashed_password" not in text and "$argon2" not in text and "token" not in text
    assert set(first.json()["items"][0]) == {
        "id",
        "email",
        "full_name",
        "is_active",
        "is_verified",
        "roles",
        "created_at",
    }

    found = await client.get("/api/v1/admin/users?search=MIXED.case", headers=headers)
    # Search is case-insensitive over email and name (the stored value is shown as persisted).
    assert [i["email"] for i in found.json()["items"]] == ["Mixed.Case@example.com"]
    # LIKE wildcards in the search term are literal characters.
    assert (await client.get("/api/v1/admin/users?search=%25", headers=headers)).json()[
        "total"
    ] == 0
    underscore = await client.get("/api/v1/admin/users?search=t_1", headers=headers)
    assert [i["email"] for i in underscore.json()["items"]] == ["percent_100@example.com"]
    admins = await client.get("/api/v1/admin/users?role=admin", headers=headers)
    assert [i["email"] for i in admins.json()["items"]] == ["admin@example.com"]
    assert (
        await client.get("/api/v1/admin/users?page_size=101", headers=headers)
    ).status_code == 422
    assert (await client.get("/api/v1/admin/users?page=0", headers=headers)).status_code == 422


@pytest.mark.asyncio
async def test_admin_status_change_is_immediate_revokes_sessions_and_is_audited(admin_env):
    client, factory, _ = admin_env
    admin = await make_user(factory, "admin@example.com", "admin")
    target = await make_user(factory, "member@example.com", "user")
    admin_headers = await bearer(client, "admin@example.com")
    member_headers = await bearer(client, "member@example.com")
    assert (await client.get("/api/v1/users/me", headers=member_headers)).status_code == 200

    response = await client.patch(
        f"/api/v1/admin/users/{target.id}",
        json={"is_active": False},
        headers=admin_headers | {"User-Agent": "<script>alert(1)</script>"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False
    assert (await client.get("/api/v1/users/me", headers=member_headers)).status_code == 401
    async with factory() as db:
        live = await db.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(RefreshToken.user_id == target.id, RefreshToken.is_revoked.is_(False))
        )
        assert live == 0
        audit = await db.scalar(select(AuditLog).where(AuditLog.action == "admin.user_update"))
        assert audit.user_id == admin.id and audit.entity_id == str(target.id)
        assert audit.details == {"changes": {"is_active": {"from": True, "to": False}}}

    # Repeating the same value changes nothing and writes no second audit row.
    again = await client.patch(
        f"/api/v1/admin/users/{target.id}", json={"is_active": False}, headers=admin_headers
    )
    assert again.status_code == 200
    logs = await client.get(
        "/api/v1/admin/audit-logs?action=admin.user_update", headers=admin_headers
    )
    assert logs.json()["total"] == 1
    entry = logs.json()["items"][0]
    assert entry["actor"]["email"] == "admin@example.com"
    assert entry["user_agent"] == "<script>alert(1)</script>"  # stored and returned as plain data

    enabled = await client.patch(
        f"/api/v1/admin/users/{target.id}", json={"is_active": True}, headers=admin_headers
    )
    assert enabled.json()["is_active"] is True
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": "member@example.com", "password": PASSWORD}
        )
    ).status_code == 200


@pytest.mark.asyncio
async def test_admin_boundaries(admin_env):
    client, factory, _ = admin_env
    admin = await make_user(factory, "admin@example.com", "admin")
    other_admin = await make_user(factory, "other-admin@example.com", "admin")
    root = await make_user(factory, "root@example.com", "superadmin")
    member = await make_user(factory, "member@example.com", "user")
    headers = await bearer(client, "admin@example.com")

    def patch(target_id, body):
        return client.patch(f"/api/v1/admin/users/{target_id}", json=body, headers=headers)

    assert (await patch(member.id, {"roles": ["admin"]})).status_code == 403
    assert (await patch(other_admin.id, {"is_active": False})).status_code == 403
    assert (await patch(root.id, {"is_active": False})).status_code == 403
    assert (await patch(admin.id, {"is_verified": True})).status_code == 403
    assert (await patch(uuid4(), {"is_active": False})).status_code == 404
    assert (await patch("not-a-uuid", {"is_active": False})).status_code == 422
    assert (await patch(member.id, {})).status_code == 422
    assert (await patch(member.id, {"is_active": False, "hashed_password": "x"})).status_code == 422
    assert (await patch(member.id, {"is_verified": True})).json()["is_verified"] is True

    # Cookie-authenticated mutations still need the CSRF header.
    await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": PASSWORD}
    )
    assert (
        await client.patch(f"/api/v1/admin/users/{member.id}", json={"is_verified": False})
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/admin/users/{member.id}", json={"is_verified": False}, headers=CSRF
        )
    ).status_code == 200
    client.cookies.delete(REFRESH_COOKIE)


@pytest.mark.asyncio
async def test_superadmin_role_management_is_immediate_and_guarded(admin_env):
    client, factory, _ = admin_env
    root = await make_user(factory, "root@example.com", "superadmin")
    second_root = await make_user(factory, "root2@example.com", "superadmin")
    member = await make_user(factory, "member@example.com", "user")
    root_headers = await bearer(client, "root@example.com")
    member_headers = await bearer(client, "member@example.com")

    def patch(target_id, body):
        return client.patch(f"/api/v1/admin/users/{target_id}", json=body, headers=root_headers)

    assert (await client.get("/api/v1/admin/stats", headers=member_headers)).status_code == 403
    granted = await patch(member.id, {"roles": ["admin", "admin", " user "]})
    assert granted.status_code == 200 and granted.json()["roles"] == ["admin", "user"]
    assert (await client.get("/api/v1/admin/stats", headers=member_headers)).status_code == 200
    assert (await patch(member.id, {"roles": ["user"]})).json()["roles"] == ["user"]
    assert (await client.get("/api/v1/admin/stats", headers=member_headers)).status_code == 403
    assert (await patch(member.id, {"roles": ["owner"]})).status_code == 422
    assert (await patch(member.id, {"roles": []})).status_code == 422
    assert (await patch(root.id, {"roles": ["user"]})).status_code == 403  # no self-demotion
    # Demoting another superadmin is allowed while the actor remains an active superadmin.
    assert (await patch(second_root.id, {"roles": ["admin"]})).json()["roles"] == ["admin"]
    assert (await patch(second_root.id, {"is_active": False})).json()["is_active"] is False
    async with factory() as db:
        changes = [
            log.details["changes"]
            for log in await db.scalars(
                select(AuditLog)
                .where(AuditLog.action == "admin.user_update")
                .order_by(AuditLog.created_at, AuditLog.id)
            )
        ]
        assert {"roles": {"from": ["user"], "to": ["admin", "user"]}} in changes
        assert {"roles": {"from": ["superadmin"], "to": ["admin"]}} in changes
        assert await db.scalar(select(func.count()).select_from(UserRole)) == 3


@pytest.mark.asyncio
async def test_stats_count_users_roles_and_sessions(admin_env):
    client, factory, _ = admin_env
    await make_user(factory, "root@example.com", "superadmin")
    await make_user(factory, "member@example.com", "user")
    await make_user(factory, "off@example.com", "user", active=False)
    headers = await bearer(client, "root@example.com")
    await bearer(client, "member@example.com")
    body = (await client.get("/api/v1/admin/stats", headers=headers)).json()
    assert (body["users_total"], body["users_active"], body["users_disabled"]) == (3, 2, 1)
    assert body["users_verified"] == 0
    assert {r["name"]: r["users"] for r in body["roles"]} == {
        "admin": 0,
        "superadmin": 1,
        "user": 2,
    }
    assert body["active_sessions"] == 2


@pytest.mark.asyncio
async def test_concurrent_superadmins_cannot_remove_each_other(test_database_url: str):
    """Two superadmins demoting each other at once must leave one active superadmin."""
    engine = create_async_engine(test_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    emails = [f"race-{uuid4().hex[:8]}@example.com" for _ in range(2)]
    try:
        async with factory() as db:
            await seed_roles(db)
            await db.commit()
        users = [await make_user(factory, email, "superadmin") for email in emails]
        async with factory() as db:
            before = await admin_service._active_superadmins(db)

        async def demote(actor: User, target: User):
            async with factory() as db:
                loaded_actor = await load_user(db, actor.id)
                try:
                    return await admin_service.update_user(
                        db, loaded_actor, target.id, AdminUserUpdate(roles=["user"]), None, None
                    )
                except AppException as error:
                    return error.status_code

        results = await asyncio.gather(demote(users[0], users[1]), demote(users[1], users[0]))
        assert sorted(isinstance(result, int) for result in results) == [False, True]
        assert 403 in results
        async with factory() as db:
            assert await admin_service._active_superadmins(db) == before - 1
    finally:
        async with factory.begin() as db:
            ids = (await db.scalars(select(User.id).where(User.email.in_(emails)))).all()
            await db.execute(delete(AuditLog).where(AuditLog.user_id.in_(ids)))
            await db.execute(delete(User).where(User.id.in_(ids)))
        await engine.dispose()

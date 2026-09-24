"""Live PostgreSQL checks on the dedicated *_test database only."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, insert, inspect, select, text
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.core.database import create_engine
from app.core.seed import DEFAULT_ROLES, seed_roles
from app.main import create_app
from app.models import AuditLog, Base, RefreshToken, Role, User, UserRole


def table_names(url: str) -> set[str]:
    async def inspect_tables() -> set[str]:
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                return set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))
        finally:
            await engine.dispose()

    return asyncio.run(inspect_tables())


def test_migration_upgrade_downgrade_reupgrade(
    migration_config: Config, test_database_url: str
) -> None:
    expected = set(Base.metadata.tables)
    command.downgrade(migration_config, "base")
    assert expected.isdisjoint(table_names(test_database_url))
    command.upgrade(migration_config, "head")
    assert expected <= table_names(test_database_url)
    command.downgrade(migration_config, "base")
    assert expected.isdisjoint(table_names(test_database_url))
    command.upgrade(migration_config, "head")
    assert expected <= table_names(test_database_url)
    command.check(migration_config)


@pytest.mark.asyncio
async def test_async_connectivity_and_schema_defaults(test_database_url: str) -> None:
    engine = create_async_engine(test_database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                assert (await connection.scalar(text("SELECT current_database()"))).endswith(
                    "_test"
                )
                async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                    user = User(
                        email="phase2@example.test",
                        hashed_password="not-a-real-hash-test-only",
                        full_name="Phase Two",
                    )
                    role = Role(name="phase2_role", description="Test role")
                    session.add_all([user, role])
                    await session.flush()
                    assert isinstance(user.id, UUID)
                    assert user.created_at.tzinfo is not None
                    assert user.updated_at.tzinfo is not None
                    assert user.is_active is True
                    assert user.is_verified is False
                    assert user.preferences == {}
                    assert role.permissions == []
                    session.add(UserRole(user_id=user.id, role_id=role.id))
                    token = RefreshToken(
                        user_id=user.id,
                        token_hash="a" * 64,
                        expires_at=datetime.now(UTC) + timedelta(days=1),
                    )
                    session.add(token)
                    session.add(AuditLog(user_id=user.id, action="test", entity="user"))
                    await session.flush()
                    assert token.revoked_at is None
                    token.is_revoked = True
                    token.revoked_at = datetime.now(UTC)
                    await session.flush()
                    await session.refresh(token)
                    assert token.revoked_at is not None and token.revoked_at.tzinfo is not None
                    with pytest.raises(IntegrityError):
                        async with session.begin_nested():
                            await session.execute(
                                insert(UserRole).values(user_id=user.id, role_id=role.id)
                            )
                    with pytest.raises(IntegrityError):
                        async with session.begin_nested():
                            session.add(
                                RefreshToken(
                                    user_id=user.id,
                                    token_hash="a" * 64,
                                    expires_at=datetime.now(UTC) + timedelta(days=1),
                                )
                            )
                            await session.flush()
                    with pytest.raises(IntegrityError):
                        async with session.begin_nested():
                            session.add(
                                RefreshToken(
                                    user_id=user.id,
                                    token_hash="too-short",
                                    expires_at=datetime.now(UTC) + timedelta(days=1),
                                )
                            )
                            await session.flush()
                    await session.execute(delete(User).where(User.id == user.id))
                    assert (
                        await session.scalar(select(UserRole).where(UserRole.user_id == user.id))
                        is None
                    )
                    assert (
                        await session.scalar(
                            select(RefreshToken).where(RefreshToken.user_id == user.id)
                        )
                        is None
                    )
                    audit = await session.scalar(select(AuditLog).where(AuditLog.entity == "user"))
                    assert audit is not None
                    await session.refresh(audit)
                    assert audit.user_id is None
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_readiness_pings_test_database(test_database_url: str) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            secret_key="test-only-secret",
            database_url=test_database_url,
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


@pytest.mark.asyncio
async def test_unique_constraints_and_role_seed_are_idempotent(test_database_url: str) -> None:
    engine = create_async_engine(test_database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection) as session:
                    await seed_roles(session)
                    await seed_roles(session)
                    names = [name for name, _ in DEFAULT_ROLES]
                    roles = (await session.scalars(select(Role).where(Role.name.in_(names)))).all()
                    assert {role.name for role in roles} == set(names)
                    assert len(roles) == len(names)
                    user = User(
                        email="unique@example.test", hashed_password="test-only", full_name="Test"
                    )
                    session.add(user)
                    await session.flush()
                    with pytest.raises(IntegrityError):
                        async with session.begin_nested():
                            session.add(
                                User(
                                    email="unique@example.test",
                                    hashed_password="test-only",
                                    full_name="Other",
                                )
                            )
                            await session.flush()
                    with pytest.raises(IntegrityError):
                        async with session.begin_nested():
                            session.add(
                                User(
                                    email="Unique@Example.test",
                                    hashed_password="test-only",
                                    full_name="Case Variant",
                                )
                            )
                            await session.flush()
                    with pytest.raises(IntegrityError):
                        async with session.begin_nested():
                            session.add(Role(name="user", description="Duplicate"))
                            await session.flush()
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_orm_user_delete_with_loaded_children(test_database_url: str) -> None:
    engine = create_async_engine(test_database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                    user = User(
                        email="orm-delete@example.test",
                        hashed_password="test-only",
                        full_name="Delete",
                    )
                    role = Role(name="delete-test-role", description="Test")
                    session.add_all([user, role])
                    await session.flush()
                    user_id, role_id = user.id, role.id
                    session.add(UserRole(user_id=user_id, role_id=role_id))
                    session.add(
                        RefreshToken(
                            user_id=user_id,
                            token_hash="f" * 64,
                            expires_at=datetime.now(UTC) + timedelta(days=1),
                        )
                    )
                    session.add(AuditLog(user_id=user_id, action="test", entity="user"))
                    await session.commit()

                async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                    loaded = await session.scalar(
                        select(User)
                        .options(
                            selectinload(User.role_assignments),
                            selectinload(User.refresh_tokens),
                            selectinload(User.audit_logs),
                        )
                        .where(User.id == user_id)
                    )
                    assert loaded is not None
                    assert len(loaded.role_assignments) == 1
                    assert len(loaded.refresh_tokens) == 1
                    await session.delete(loaded)
                    await session.commit()

                async with AsyncSession(bind=connection) as session:
                    assert await session.get(User, user_id) is None
                    assert (
                        await session.scalar(select(UserRole).where(UserRole.user_id == user_id))
                        is None
                    )
                    assert (
                        await session.scalar(
                            select(RefreshToken).where(RefreshToken.user_id == user_id)
                        )
                        is None
                    )
                    assert await session.get(Role, role_id) is not None
                    audit = await session.scalar(select(AuditLog).where(AuditLog.user_id.is_(None)))
                    assert audit is not None
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_role_delete_is_restricted_with_assignments_loaded(test_database_url: str) -> None:
    engine = create_async_engine(test_database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection) as session:
                    user = User(
                        email="role-restrict@example.test",
                        hashed_password="test-only",
                        full_name="Role",
                    )
                    role = Role(name="restrict-test-role", description="Test")
                    session.add_all([user, role])
                    await session.flush()
                    session.add(UserRole(user_id=user.id, role_id=role.id))
                    await session.flush()
                    loaded_role = await session.scalar(
                        select(Role)
                        .options(selectinload(Role.user_assignments))
                        .where(Role.id == role.id)
                    )
                    assert loaded_role is not None and len(loaded_role.user_assignments) == 1
                    await session.delete(loaded_role)
                    with pytest.raises(IntegrityError):
                        await session.flush()
            finally:
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_unloaded_async_relationship_raises_explicitly(test_database_url: str) -> None:
    engine = create_async_engine(test_database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection) as session:
                    user = User(
                        email="lazy-raise@example.test",
                        hashed_password="test-only",
                        full_name="Lazy",
                    )
                    session.add(user)
                    await session.flush()
                    session.expunge(user)
                    loaded = await session.get(User, user.id)
                    assert loaded is not None
                    with pytest.raises(InvalidRequestError, match="lazy='raise'"):
                        _ = loaded.role_assignments
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_database_engine_hides_password_parameters(test_database_url: str) -> None:
    settings = Settings(
        _env_file=None, secret_key="test-only-secret", database_url=test_database_url
    )
    engine = create_engine(settings)
    assert engine.sync_engine.hide_parameters is True
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection) as session:
                    session.add(
                        User(
                            email="hidden-hash@example.test",
                            hashed_password="synthetic-sensitive-hash-marker",
                            full_name="One",
                        )
                    )
                    await session.flush()
                    with pytest.raises(IntegrityError) as failure:
                        session.add(
                            User(
                                email="hidden-hash@example.test",
                                hashed_password="synthetic-sensitive-hash-marker",
                                full_name="Two",
                            )
                        )
                        await session.flush()
                    assert "synthetic-sensitive-hash-marker" not in str(failure.value)
            finally:
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()

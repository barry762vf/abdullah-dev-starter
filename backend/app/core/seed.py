"""Explicit role seed and one-time administrator bootstrap."""

import argparse
import asyncio

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.security import hash_password_async
from app.models import AuditLog, Role, User, UserRole
from app.services.admin_service import PRIVILEGE_LOCK_KEY

DEFAULT_ROLES = (
    ("superadmin", "Full platform administration"),
    ("admin", "Business administration and user management"),
    ("user", "Standard authenticated user"),
)


async def seed_roles(session: AsyncSession) -> None:
    """Insert missing baseline roles, without changing existing grants or descriptions."""
    for name, description in DEFAULT_ROLES:
        statement = (
            insert(Role)
            .values(name=name, description=description, permissions=[])
            .on_conflict_do_nothing(index_elements=[Role.name])
        )
        await session.execute(statement)


async def bootstrap_superadmin(session: AsyncSession, settings: Settings) -> bool:
    """Create one initial superadmin while holding a transaction-scoped PostgreSQL lock."""
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": PRIVILEGE_LOCK_KEY})
    existing = await session.scalar(
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.name == "superadmin")
        .limit(1)
    )
    if existing is not None:
        return False
    email = settings.initial_admin_email.strip().lower()
    password = settings.initial_admin_password.get_secret_value()
    if not email or len(password) < 12 or len(password) > 128 or password == "Admin123!Secure":
        raise ValueError("Set a valid INITIAL_ADMIN_EMAIL and strong, non-sample password")
    email = str(TypeAdapter(EmailStr).validate_python(email))
    if await session.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise ValueError("Initial administrator email already belongs to an account")
    role = await session.scalar(select(Role).where(Role.name == "superadmin"))
    if role is None:
        raise ValueError("The superadmin role must be seeded before bootstrap")
    try:
        hashed_password = await hash_password_async(password)
        user = User(email=email, hashed_password=hashed_password, full_name="Administrator")
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.add(
            AuditLog(
                user_id=user.id, action="auth.bootstrap", entity="user", entity_id=str(user.id)
            )
        )
        await session.flush()
    except IntegrityError:
        raise ValueError("Initial administrator could not be created") from None
    return True


async def main(bootstrap_admin: bool = False) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        factory = create_session_factory(engine)
        async with factory.begin() as session:
            await seed_roles(session)
            if bootstrap_admin:
                await bootstrap_superadmin(session, settings)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed baseline roles and optionally one administrator"
    )
    parser.add_argument("--bootstrap-admin", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(bootstrap_admin=args.bootstrap_admin))

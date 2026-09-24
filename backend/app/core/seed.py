"""Explicit, repeatable role bootstrap. Account provisioning belongs to Phase 3."""

import asyncio

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.models import Role

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


async def main() -> None:
    engine = create_engine(get_settings())
    try:
        factory = create_session_factory(engine)
        async with factory.begin() as session:
            await seed_roles(session)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

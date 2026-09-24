"""Profile loading and self-service updates."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, UserRole
from app.schemas.user import UserResponse


async def load_user(db: AsyncSession, user_id: UUID) -> User | None:
    return await db.scalar(
        select(User)
        .options(selectinload(User.role_assignments).selectinload(UserRole.role))
        .where(User.id == user_id)
    )


def profile(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        roles=sorted(assignment.role.name for assignment in user.role_assignments),
        created_at=user.created_at,
    )


async def update_profile(db: AsyncSession, user: User, full_name: str) -> UserResponse:
    user.full_name = full_name
    await db.commit()
    return profile(user)

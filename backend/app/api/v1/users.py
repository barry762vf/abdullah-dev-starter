"""Authenticated self-profile endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import profile, update_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: Annotated[User, Depends(get_current_active_user)]) -> UserResponse:
    return profile(user)


@router.patch("/me", response_model=UserResponse)
async def patch_me(
    data: UserUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    return await update_profile(db, user, data.full_name)

"""Current database-backed identity and reusable role guards."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import ACCESS_COOKIE, decode_access_token
from app.models import User
from app.services.user_service import load_user

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def require_cookie_csrf(request: Request) -> None:
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        raise AppException(403, "Forbidden", "Missing request verification header.")


async def get_current_user(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    authorization = request.headers.get("Authorization", "")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AppException(401, "Unauthorized", "Invalid access token.")
    else:
        token = request.cookies.get(ACCESS_COOKIE, "")
        if request.method in UNSAFE_METHODS:
            require_cookie_csrf(request)
    if not token:
        raise AppException(401, "Unauthorized", "Authentication required.")
    try:
        user_id = decode_access_token(token, request.app.state.settings)
    except ValueError:
        raise AppException(401, "Unauthorized", "Invalid access token.") from None
    user = await load_user(db, user_id)
    if user is None:
        raise AppException(401, "Unauthorized", "Invalid access token.")
    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_active:
        raise AppException(401, "Unauthorized", "Account unavailable.")
    return user


def require_role(roles: list[str] | tuple[str, ...]) -> Callable:
    allowed = frozenset(roles)
    if not allowed:
        raise ValueError("At least one role is required")

    async def guard(user: Annotated[User, Depends(get_current_active_user)]) -> User:
        current = {assignment.role.name for assignment in user.role_assignments}
        if "superadmin" not in current and not current.intersection(allowed):
            raise AppException(403, "Forbidden", "Insufficient role.")
        return user

    return guard

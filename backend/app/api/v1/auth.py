"""Authentication endpoints with cookie transport."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_cookie_csrf
from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import (
    ACCESS_COOKIE,
    ACCESS_TOKEN_MINUTES,
    REFRESH_COOKIE,
    REFRESH_TOKEN_DAYS,
)
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


def _client_metadata(request: Request) -> tuple[str | None, str | None]:
    return (
        request.client.host if request.client else None,
        request.headers.get("User-Agent"),
    )


def _set_cookies(response: Response, request: Request, access: str, refresh: str) -> None:
    secure = request.app.state.settings.cookie_secure
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=ACCESS_TOKEN_MINUTES * 60,
        path="/api/v1",
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=REFRESH_TOKEN_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def _clear_cookies(response: Response, request: Request) -> None:
    secure = request.app.state.settings.cookie_secure
    response.delete_cookie(
        ACCESS_COOKIE, path="/api/v1", secure=secure, httponly=True, samesite="lax"
    )
    response.delete_cookie(
        REFRESH_COOKIE, path="/api/v1/auth", secure=secure, httponly=True, samesite="lax"
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    ip, agent = _client_metadata(request)
    request.app.state.auth_rate_limiter.check("register", ip or "unknown")
    return await auth_service.register(db, data, ip, agent)


@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    ip, agent = _client_metadata(request)
    request.app.state.auth_rate_limiter.check("login", ip or "unknown")
    user, access, refresh = await auth_service.login(
        db, data, request.app.state.settings, ip, agent
    )
    _set_cookies(response, request, access, refresh)
    return user


@router.post("/refresh", response_model=UserResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    require_cookie_csrf(request)
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise AppException(401, "Unauthorized", "Invalid refresh token.")
    ip, agent = _client_metadata(request)
    user, access, refresh_token = await auth_service.refresh(
        db, raw, request.app.state.settings, ip, agent
    )
    _set_cookies(response, request, access, refresh_token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    require_cookie_csrf(request)
    ip, agent = _client_metadata(request)
    await auth_service.logout(db, request.cookies.get(REFRESH_COOKIE), ip, agent)
    _clear_cookies(response, request)

"""Administration endpoints. The router-level guard protects every route (ADR 013)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.models import User
from app.schemas.admin import AdminStats, AdminUserPage, AdminUserUpdate, AuditLogPage
from app.schemas.user import UserResponse
from app.services import admin_service

# One guard object: FastAPI resolves it once per request for the router and the handlers.
admin_only = require_role(["admin"])
router = APIRouter(prefix="/admin", tags=["administration"], dependencies=[Depends(admin_only)])

Page = Annotated[int, Query(ge=1, le=100_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("/users", response_model=AdminUserPage)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Page = 1,
    page_size: PageSize = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
    role: Annotated[str | None, Query(max_length=50)] = None,
) -> AdminUserPage:
    return await admin_service.list_users(db, page, page_size, search, role)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: AdminUserUpdate,
    request: Request,
    actor: Annotated[User, Depends(admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    ip = request.client.host if request.client else None
    return await admin_service.update_user(
        db, actor, user_id, data, ip, request.headers.get("User-Agent")
    )


@router.get("/stats", response_model=AdminStats)
async def stats(db: Annotated[AsyncSession, Depends(get_db)]) -> AdminStats:
    return await admin_service.stats(db)


@router.get("/audit-logs", response_model=AuditLogPage)
async def audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Page = 1,
    page_size: PageSize = 20,
    action: Annotated[str | None, Query(max_length=100)] = None,
) -> AuditLogPage:
    return await admin_service.list_audit_logs(db, page, page_size, action)

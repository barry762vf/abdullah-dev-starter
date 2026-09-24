"""Administration queries and account/role mutations (ADR 013)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import distinct, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.models import AuditLog, RefreshToken, Role, User, UserRole
from app.schemas.admin import (
    AdminStats,
    AdminUserPage,
    AdminUserUpdate,
    AuditActor,
    AuditLogEntry,
    AuditLogPage,
    RoleCount,
)
from app.schemas.user import UserResponse
from app.services.user_service import load_user, profile

# Shared with the superadmin bootstrap: every change to privileged membership is serialized.
PRIVILEGE_LOCK_KEY = 389607175213
MANAGEMENT_ROLES = frozenset({"admin", "superadmin"})


def _like_pattern(term: str) -> str:
    escaped = term.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def list_users(
    db: AsyncSession, page: int, page_size: int, search: str | None, role: str | None
) -> AdminUserPage:
    filters = []
    if search and search.strip():
        pattern = _like_pattern(search.strip())
        filters.append(
            or_(
                func.lower(User.email).like(pattern, escape="\\"),
                func.lower(User.full_name).like(pattern, escape="\\"),
            )
        )
    if role:
        filters.append(User.role_assignments.any(UserRole.role.has(Role.name == role)))
    total = await db.scalar(select(func.count()).select_from(User).where(*filters))
    users = await db.scalars(
        select(User)
        .options(selectinload(User.role_assignments).selectinload(UserRole.role))
        .where(*filters)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AdminUserPage(
        items=[profile(user) for user in users], total=total or 0, page=page, page_size=page_size
    )


async def _active_superadmins(db: AsyncSession) -> int:
    return await db.scalar(
        select(func.count(distinct(User.id)))
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.name == "superadmin", User.is_active.is_(True))
    )


async def update_user(
    db: AsyncSession,
    actor: User,
    target_id: UUID,
    data: AdminUserUpdate,
    ip: str | None,
    agent: str | None,
) -> UserResponse:
    if target_id == actor.id:
        raise AppException(403, "Forbidden", "Use another administrator to change your account.")
    await db.execute(select(func.pg_advisory_xact_lock(PRIVILEGE_LOCK_KEY)))
    # Re-read the actor under the lock: a concurrent request may have demoted or disabled them.
    actor_active = await db.scalar(select(User.is_active).where(User.id == actor.id))
    actor_roles = set(
        await db.scalars(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == actor.id)
        )
    )
    if not actor_active or not actor_roles & MANAGEMENT_ROLES:
        raise AppException(403, "Forbidden", "Insufficient role.")
    is_superadmin = "superadmin" in actor_roles

    target = await load_user(db, target_id)
    if target is None:
        raise AppException(404, "Not Found", "User not found.")
    current_roles = {assignment.role.name for assignment in target.role_assignments}
    if not is_superadmin:
        if data.roles is not None:
            raise AppException(403, "Forbidden", "Only a superadmin can change roles.")
        if current_roles & MANAGEMENT_ROLES:
            raise AppException(
                403, "Forbidden", "Only a superadmin can manage administrator accounts."
            )

    changes: dict[str, dict[str, object]] = {}
    if data.is_active is not None and data.is_active != target.is_active:
        changes["is_active"] = {"from": target.is_active, "to": data.is_active}
        target.is_active = data.is_active
    if data.is_verified is not None and data.is_verified != target.is_verified:
        changes["is_verified"] = {"from": target.is_verified, "to": data.is_verified}
        target.is_verified = data.is_verified
    if data.roles is not None and set(data.roles) != current_roles:
        wanted = set(data.roles)
        roles = (await db.scalars(select(Role).where(Role.name.in_(wanted)))).all()
        if len(roles) != len(wanted):
            raise AppException(422, "Unprocessable Entity", "Unknown role.")
        for assignment in list(target.role_assignments):
            if assignment.role.name not in wanted:
                target.role_assignments.remove(assignment)
        for role in roles:
            if role.name not in current_roles:
                target.role_assignments.append(
                    UserRole(user_id=target.id, role_id=role.id, role=role)
                )
        changes["roles"] = {"from": sorted(current_roles), "to": sorted(wanted)}

    if not changes:
        return profile(target)
    await db.flush()
    removes_superadmin = (
        "superadmin" in current_roles
        and (target.is_active is False or "superadmin" not in (data.roles or current_roles))
        and changes.keys() & {"is_active", "roles"}
    )
    # Only a change that takes away an active superadmin can break the invariant; an installation
    # that has not bootstrapped a superadmin yet can still manage ordinary accounts.
    if removes_superadmin and await _active_superadmins(db) == 0:
        await db.rollback()
        raise AppException(409, "Conflict", "At least one active superadmin must remain.")
    if changes.get("is_active", {}).get("to") is False:
        # Access checks read is_active on every request; also end refresh sessions immediately.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == target.id, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True, revoked_at=func.now())
        )
    db.add(
        AuditLog(
            user_id=actor.id,
            action="admin.user_update",
            entity="user",
            entity_id=str(target.id),
            ip_address=ip[:45] if ip else None,
            user_agent=agent[:512] if agent else None,
            details={"changes": changes},
        )
    )
    await db.commit()
    return profile(target)


async def stats(db: AsyncSession) -> AdminStats:
    total, active, verified = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(User.is_active.is_(True)),
                func.count().filter(User.is_verified.is_(True)),
            ).select_from(User)
        )
    ).one()
    role_rows = await db.execute(
        select(Role.name, func.count(UserRole.user_id))
        .outerjoin(UserRole, UserRole.role_id == Role.id)
        .group_by(Role.name)
        .order_by(Role.name)
    )
    sessions = await db.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.is_revoked.is_(False), RefreshToken.expires_at > func.now())
    )
    return AdminStats(
        users_total=total,
        users_active=active,
        users_disabled=total - active,
        users_verified=verified,
        roles=[RoleCount(name=name, users=count) for name, count in role_rows],
        active_sessions=sessions or 0,
        generated_at=datetime.now(UTC),
    )


async def list_audit_logs(
    db: AsyncSession, page: int, page_size: int, action: str | None
) -> AuditLogPage:
    filters = [AuditLog.action == action] if action else []
    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    rows = await db.execute(
        select(AuditLog, User.email)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(*filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        AuditLogEntry(
            id=log.id,
            created_at=log.created_at,
            action=log.action,
            entity=log.entity,
            entity_id=log.entity_id,
            actor=AuditActor(id=log.user_id, email=email) if log.user_id and email else None,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details or {},
        )
        for log, email in rows
    ]
    return AuditLogPage(items=items, total=total or 0, page=page, page_size=page_size)

"""Administration request/response contracts. Only explicit fields leave the API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.user import UserResponse


class AdminUserPage(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class AdminUserUpdate(BaseModel):
    """At least one field; unknown fields are rejected so nothing else can be assigned."""

    model_config = ConfigDict(extra="forbid")

    is_active: bool | None = None
    is_verified: bool | None = None
    # Replaces the user's complete role set. Names must already exist; roles are never created here.
    roles: list[str] | None = Field(default=None, min_length=1, max_length=10)

    @field_validator("roles")
    @classmethod
    def normalize_roles(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        names = sorted({name.strip() for name in value})
        if any(not name or len(name) > 50 for name in names):
            raise ValueError("Invalid role name")
        return names

    @model_validator(mode="after")
    def require_change(self) -> "AdminUserUpdate":
        if self.is_active is None and self.is_verified is None and self.roles is None:
            raise ValueError("Provide at least one field to update")
        return self


class RoleCount(BaseModel):
    name: str
    users: int


class AdminStats(BaseModel):
    users_total: int
    users_active: int
    users_disabled: int
    users_verified: int
    roles: list[RoleCount]
    active_sessions: int
    generated_at: datetime


class AuditActor(BaseModel):
    id: UUID
    email: str


class AuditLogEntry(BaseModel):
    id: UUID
    created_at: datetime
    action: str
    entity: str
    entity_id: str | None
    actor: AuditActor | None
    ip_address: str | None
    user_agent: str | None
    details: dict[str, Any]


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int

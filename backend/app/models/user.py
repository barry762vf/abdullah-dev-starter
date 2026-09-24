"""Identity and role assignment storage; authentication behavior is Phase 3."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAt, UpdatedAt, UUIDPrimaryKey


class User(UUIDPrimaryKey, CreatedAt, UpdatedAt, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    is_verified: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    preferences: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    __table_args__ = (Index("ux_users_email_lower", func.lower(email), unique=True),)

    role_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user", passive_deletes=True, lazy="raise"
    )


class Role(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    permissions: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    user_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="role", passive_deletes="all", lazy="raise"
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="role_assignments", lazy="raise")
    role: Mapped[Role] = relationship(back_populates="user_assignments", lazy="raise")


from app.models.audit import AuditLog  # noqa: E402
from app.models.token import RefreshToken  # noqa: E402

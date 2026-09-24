"""Protect email identity, role assignments, and token revocation history.

Revision ID: 002_pre_auth_hardening
Revises: 001_initial_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_pre_auth_hardening"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicates = op.get_bind().execute(
        sa.text("SELECT 1 FROM users GROUP BY lower(email) HAVING count(*) > 1 LIMIT 1")
    )
    if duplicates.first():
        raise RuntimeError("Resolve case-insensitive duplicate user emails before migration 002")

    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ux_users_email_lower", "users", [sa.text("lower(email)")], unique=True)
    op.add_column("refresh_tokens", sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.drop_constraint("user_roles_role_id_fkey", "user_roles", type_="foreignkey")
    op.create_foreign_key(
        "fk_user_roles_role_id_roles",
        "user_roles",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_user_roles_role_id_roles", "user_roles", type_="foreignkey")
    op.create_foreign_key(
        "user_roles_role_id_fkey",
        "user_roles",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("refresh_tokens", "revoked_at")
    op.drop_index("ux_users_email_lower", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)

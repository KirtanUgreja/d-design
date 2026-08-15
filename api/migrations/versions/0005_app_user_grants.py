"""app_user role gets table grants (phase 18).

Migration 0001 revoked all default privileges from `public` but never granted
`app_user` anything — so as a non-superuser, app_user has zero access to the
app tables, and the RLS tests (and any real app connection) hit "permission
denied for table" before RLS even runs.

RLS controls WHICH rows; table grants control WHETHER a table is reachable.
app_user gets full DML on the app tables; the RLS policies then restrict every
statement to the tenant.

Revision ID: 0005_app_user_grants
Revises: 0004_owner_bootstraps_members
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_app_user_grants"
down_revision: str | None = "0004_owner_bootstraps_members"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APP_TABLES = ("experiences", "briefs", "generations", "teams", "team_members", "brand_kits")


def upgrade() -> None:
    for table in _APP_TABLES:
        op.execute(f"grant select, insert, update, delete on table {table} to app_user;")


def downgrade() -> None:
    for table in _APP_TABLES:
        op.execute(f"revoke all on table {table} from app_user;")

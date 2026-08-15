"""quotas table + RLS + grants (phase 19).

The per-account quota: one row per account, plan, used, limit. The limit is a
config value (the docs deliberately leave the numbers unchosen — decisions.md:
"quota *enforcement* is built; the numbers are not chosen"), so this table
carries it per row for easy adjustment.

The atomic counter (backend.md:160-174) is one UPDATE...RETURNING in the data
module; this migration is just the table + RLS + the grants that 0005 taught
us are mandatory (a role with no table grants gets "permission denied" before
RLS even runs).

Revision ID: 0008_quotas
Revises: 0007_team_members_owner_scoped
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_quotas"
down_revision: str | None = "0007_team_members_owner_scoped"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quotas",
        sa.Column("account_id", sa.Uuid(), primary_key=True),
        sa.Column("plan", sa.String(length=16), server_default="free", nullable=False),
        sa.Column("used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("limit", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # RLS owner-scoped (the 0001 pattern), using AND with check.
    op.execute("alter table quotas enable row level security;")
    op.execute(
        """
        create policy own_quotas on quotas
          for all to app_user
          using      (account_id = current_setting('app.user_id')::uuid)
          with check (account_id = current_setting('app.user_id')::uuid);
        """
    )

    # The 0005 lesson: a new table needs grants or the role is denied before
    # RLS runs.
    op.execute("grant select, insert, update, delete on table quotas to app_user;")


def downgrade() -> None:
    op.execute("revoke all on table quotas from app_user;")
    op.execute("drop policy if exists own_quotas on quotas;")
    op.execute("alter table quotas disable row level security;")
    op.drop_table("quotas")

"""brand kits: teams, team_members, brand_kits

The team model for team-shared brand kits (v3, phase 17). App-owned tables —
Alembic's set; the auth tables (including Better Auth's org tables, which are
not used here) are never touched. RLS is team-scoped: a user sees a kit if
they are a member of its team, via the documented exists() shape
(tenancy-and-data.md), with both using and with check — with check is not
optional.

Revision ID: 0002_brand_kits
Revises: 0001_app_tables
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_brand_kits"
down_revision: str | None = "0001_app_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The team-scoped check, shared by the brand_kits policies. A user sees or
# writes a kit when they are a member of the kit's team.
_TEAM_SCOPE = """
    exists (
      select 1 from team_members tm
      where tm.team_id = {table}.team_id
        and tm.user_id = current_setting('app.user_id')::uuid
    )
"""


def upgrade() -> None:
    # --- teams: owned by a user. The team is the sharing boundary.
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_teams_owner_id", "teams", ["owner_id"])

    # --- team_members: who belongs to a team. The RLS pivot for team scope.
    op.create_table(
        "team_members",
        sa.Column(
            "team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="cascade"), primary_key=True
        ),
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="member"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])

    # --- brand_kits: the kit itself. colors_json holds the extracted facts
    # (never presentational values in a generated tree — these are stored
    # facts, mapped to family roles at generation time). logo_ref is the
    # storage key of the verified, re-encoded logo. font_ids are registry ids
    # only — never a user-uploaded font (platform-and-packages.md: "never
    # parse a user-uploaded font").
    op.create_table(
        "brand_kits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="cascade"), nullable=False
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("colors_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("logo_ref", sa.String(length=200), nullable=True),
        sa.Column("font_ids", sa.JSON(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_brand_kits_team_id", "brand_kits", ["team_id"])

    # --- RLS: teams owner-scoped; team_members and brand_kits team-scoped.
    # Both using AND with check on every write policy.
    op.execute("alter table teams enable row level security;")
    op.execute(
        """
        create policy own_teams on teams
          for all to app_user
          using      (owner_id = current_setting('app.user_id')::uuid)
          with check (owner_id = current_setting('app.user_id')::uuid);
        """
    )

    op.execute("alter table team_members enable row level security;")
    op.execute(
        f"""
        create policy own_team_members on team_members
          for all to app_user
          using      ({_TEAM_SCOPE.format(table="team_members")})
          with check ({_TEAM_SCOPE.format(table="team_members")});
        """
    )

    op.execute("alter table brand_kits enable row level security;")
    op.execute(
        f"""
        create policy own_brand_kits on brand_kits
          for all to app_user
          using      ({_TEAM_SCOPE.format(table="brand_kits")})
          with check ({_TEAM_SCOPE.format(table="brand_kits")});
        """
    )


def downgrade() -> None:
    for table in ("brand_kits", "team_members", "teams"):
        op.execute(f"drop policy if exists own_{table} on {table};")
        op.execute(f"alter table {table} disable row level security;")
    op.drop_table("brand_kits")
    op.drop_table("team_members")
    op.drop_table("teams")

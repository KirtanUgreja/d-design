"""team_members policy: the owner may bootstrap membership (phase 18).

The 0002 team_members policy checked membership on both using AND with check —
but with check demanded the user ALREADY be a member, so the first membership
could never be inserted (the owner cannot add anyone, including themselves).
This is the RLS bootstrap gap, exposed by the live-DB tests (phase 18).

The fix: with check also permits the team OWNER to insert members. using stays
membership-scoped (a member sees the rows of teams they belong to); the owner
who is not yet a member cannot read the roster until they are added — but they
CAN add members, which is the bootstrap.

Revision ID: 0004_owner_bootstraps_members
Revises: 0003_published_key
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_owner_bootstraps_members"
down_revision: str | None = "0003_published_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Owner-scoped through the teams parent — the non-recursive shape. A
    # member never writes team_members (only the owner manages the roster);
    # members read brand_kits, which is scoped through the same teams join
    # without self-reference. using AND with check are both owner-scoped.
    op.execute("drop policy if exists own_team_members on team_members;")
    op.execute(
        """
        create policy own_team_members on team_members
          for all to app_user
          using (
            exists (
              select 1 from teams t
              where t.id = team_members.team_id
                and t.owner_id = current_setting('app.user_id')::uuid
            )
          )
          with check (
            exists (
              select 1 from teams t
              where t.id = team_members.team_id
                and t.owner_id = current_setting('app.user_id')::uuid
            )
          );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists own_team_members on team_members;")
    op.execute(
        """
        create policy own_team_members on team_members
          for all to app_user
          using (
            exists (
              select 1 from teams t
              where t.id = team_members.team_id
                and t.owner_id = current_setting('app.user_id')::uuid
            )
          )
          with check (
            exists (
              select 1 from teams t
              where t.id = team_members.team_id
                and t.owner_id = current_setting('app.user_id')::uuid
            )
          );
        """
    )

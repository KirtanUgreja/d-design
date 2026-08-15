"""team_members policy: owner-scoped, non-recursive (phase 18).

0004's policy was applied to the live DB in its original recursive form before
the fix landed. This migration replaces it with the owner-scoped shape (the
same one 0004 now describes) — `using` AND `with check` reference the teams
parent, never team_members itself, so no recursion. Members read kits via the
is_team_member() SECURITY DEFINER helper (0006); they never write the roster.

Revision ID: 0007_team_members_owner_scoped
Revises: 0006_is_team_member
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007_team_members_owner_scoped"
down_revision: str | None = "0006_is_team_member"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
              select 1 from team_members tm
              where tm.team_id = team_members.team_id
                and tm.user_id = current_setting('app.user_id')::uuid
            )
          )
          with check (
            exists (
              select 1 from team_members tm
              where tm.team_id = team_members.team_id
                and tm.user_id = current_setting('app.user_id')::uuid
            )
          );
        """
    )

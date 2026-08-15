"""brand_kits membership check via a SECURITY DEFINER function (phase 18).

The 0002 brand_kits policy checked membership with `exists (select 1 from
team_members ...)` — but RLS applies to that subquery too, so once team_members
became owner-scoped (0004), a plain MEMBER could never see the roster and thus
could never read a kit. Team-shared reading broke.

The fix: a SECURITY DEFINER function `is_team_member(team_id, user_id)` runs as
the table owner (bypassing RLS on its internal query) and answers the one
question the policy needs: is this user a member of that team? RLS stays on
for everything else; only this narrowly-scoped read of the membership table is
privileged, and it returns a boolean, never rows.

Revision ID: 0006_is_team_member
Revises: 0005_app_user_grants
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_is_team_member"
down_revision: str | None = "0005_app_user_grants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        create or replace function is_team_member(p_team uuid, p_user uuid)
        returns boolean language sql security definer stable as $$
          select exists (
            select 1 from team_members tm
            where tm.team_id = p_team and tm.user_id = p_user
          );
        $$;
        """
    )
    op.execute("grant execute on function is_team_member(uuid, uuid) to app_user;")
    op.execute("drop policy if exists own_brand_kits on brand_kits;")
    op.execute(
        """
        create policy own_brand_kits on brand_kits
          for all to app_user
          using (
            exists (
              select 1 from teams t
              where t.id = brand_kits.team_id
                and t.owner_id = current_setting('app.user_id')::uuid
            )
            or is_team_member(
              brand_kits.team_id,
              current_setting('app.user_id')::uuid
            )
          )
          with check (
            exists (
              select 1 from teams t
              where t.id = brand_kits.team_id
                and t.owner_id = current_setting('app.user_id')::uuid
            )
            or is_team_member(
              brand_kits.team_id,
              current_setting('app.user_id')::uuid
            )
          );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists own_brand_kits on brand_kits;")
    op.execute(
        """
        create policy own_brand_kits on brand_kits
          for all to app_user
          using (
            exists (
              select 1 from team_members tm
              where tm.team_id = brand_kits.team_id
                and tm.user_id = current_setting('app.user_id')::uuid
            )
          )
          with check (
            exists (
              select 1 from team_members tm
              where tm.team_id = brand_kits.team_id
                and tm.user_id = current_setting('app.user_id')::uuid
            )
          );
        """
    )
    op.execute("drop function if exists is_team_member(uuid, uuid);")

"""briefs, with its RLS policy

The approved-claims record (docs/v1/plan/08-intake.md -> "The `briefs`
table"). One `jsonb` payload rather than a column per field: `schema/brief.py`
owns the shape, the row is read and written whole, and nothing queries it by
field.

The policy is created in the same migration as the table, never a follow-up —
a table that exists for even one deploy without its policy is a table that was
readable across tenants for one deploy (the same reasoning as 0001).

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "briefs",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("experience_id", sa.Uuid(), nullable=False),
        sa.Column(
            "payload",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_briefs_owner_id", "briefs", ["owner_id"])
    op.create_index("ix_briefs_experience_id", "briefs", ["experience_id"])

    op.execute("alter table briefs enable row level security")
    # `with check` as well as `using`: `using` alone filters what a tenant can
    # read and leaves them free to INSERT a row owned by someone else.
    op.execute(
        """
        create policy own_briefs on briefs
          for all to app_user
          using      (owner_id = current_setting('app.user_id')::uuid)
          with check (owner_id = current_setting('app.user_id')::uuid)
        """
    )
    op.execute("grant select, insert, update, delete on briefs to app_user")


def downgrade() -> None:
    op.execute("drop policy if exists own_briefs on briefs")
    op.drop_index("ix_briefs_experience_id", table_name="briefs")
    op.drop_index("ix_briefs_owner_id", table_name="briefs")
    op.drop_table("briefs")

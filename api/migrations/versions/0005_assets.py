"""assets, with its RLS policy

The upload record (docs/v1/plan/10-brand-and-uploads.md -> "The `assets`
table"). Columns rather than one `jsonb` payload, unlike `briefs`: this table
*is* queried by field — `list_assets` reads every asset for an owner, and the
editor filters by `kind` and shows `source` — and a row is written once and
read many times.

`source` is not decoration. Generated imagery carries different legal and
brand risk than an uploaded product shot, and a marketer needs to know which
is which before publishing.

`storage_key` is server-generated and unique: a user filename never reaches a
path, and the uniqueness constraint is the second half of that guarantee — a
collision would mean one upload silently serving another's bytes.

The policy is created in the same migration as the table, never a follow-up —
a table that exists for even one deploy without its policy is a table that was
readable across tenants for one deploy (the same reasoning as 0001).

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.String(length=200), nullable=False),
        sa.Column("mime", sa.String(length=128), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("alt", sa.String(length=160), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_assets_storage_key"),
    )
    op.create_index("ix_assets_owner_id", "assets", ["owner_id"])

    op.execute("alter table assets enable row level security")
    # `with check` as well as `using`: `using` alone filters what a tenant can
    # read and leaves them free to INSERT a row owned by someone else.
    op.execute(
        """
        create policy own_assets on assets
          for all to app_user
          using      (owner_id = current_setting('app.user_id')::uuid)
          with check (owner_id = current_setting('app.user_id')::uuid)
        """
    )
    op.execute("grant select, insert, update, delete on assets to app_user")


def downgrade() -> None:
    op.execute("drop policy if exists own_assets on assets")
    op.drop_index("ix_assets_owner_id", table_name="assets")
    op.drop_table("assets")

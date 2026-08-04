"""experiences and brands, with their RLS policies

The policies are part of the same migration as the tables on purpose. A table
that exists for even one deploy without its policy is a table that was readable
by every tenant for one deploy.

Revision ID: 0001
Revises:
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("brands", "experiences")


def upgrade() -> None:
    # gen_random_uuid() is core since Postgres 13 — no pgcrypto, and no
    # extension for `migrator` to lack the privilege to create.
    op.create_table(
        "brands",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("display_font", sa.String(length=120), nullable=False),
        sa.Column("text_font", sa.String(length=120), nullable=False),
        sa.Column("primary", sa.String(length=32), nullable=False),
        sa.Column("secondary", sa.String(length=32), nullable=False),
        sa.Column("neutral", sa.String(length=32), nullable=False),
        sa.Column("logo_asset_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brands_owner_id", "brands", ["owner_id"])

    op.create_table(
        "experiences",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=True),
        sa.Column("art_direction", sa.String(length=64), nullable=False),
        sa.Column("scenes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiences_owner_id", "experiences", ["owner_id"])

    for table in TABLES:
        op.execute(f"alter table {table} enable row level security")
        # `using` filters reads; `with check` filters writes. Only one of them
        # is the obvious half, and a policy with `using` alone lets a tenant
        # insert a row owned by someone else.
        op.execute(
            f"""
            create policy own_{table} on {table}
              for all to app_user
              using      (owner_id = current_setting('app.user_id')::uuid)
              with check (owner_id = current_setting('app.user_id')::uuid)
            """
        )
        # Explicit rather than relying on default privileges, so the grant is
        # visible in the same diff as the table.
        op.execute(f"grant select, insert, update, delete on {table} to app_user")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"drop policy if exists own_{table} on {table}")
    op.drop_index("ix_experiences_owner_id", table_name="experiences")
    op.drop_table("experiences")
    op.drop_index("ix_brands_owner_id", table_name="brands")
    op.drop_table("brands")

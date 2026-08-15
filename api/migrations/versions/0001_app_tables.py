"""app tables + RLS bootstrap

The application tables (the disjoint set api owns, never the auth tables) and
the RLS spine: the app_user role with no bypassrls, RLS enabled on every app
table, and owner-scoped policies with both using and with check.

Revision ID: 0001_app_tables
Revises:
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_app_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- the app role: no bypassrls, owns nothing. The migration role (the
    # connection running this) owns DDL. (tenancy-and-data.md: "no anonymous
    # database role exists"; RLS guards only authenticated users.)
    op.execute(
        "do $$ begin create role app_user nologin;"
        " exception when duplicate_object then null; end $$;"
    )
    op.execute("revoke all on all tables in schema public from public;")
    op.execute("alter default privileges in schema public revoke all on tables from public;")

    # --- experiences: a deck, owned by a user. deck_json is the schema-owned
    # Deck (the renderer's input); the auth user table is web's, referenced
    # read-only here.
    op.create_table(
        "experiences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("deck_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_experiences_owner_id", "experiences", ["owner_id"])

    # --- briefs: the intake a deck was built from (no prompts in generations;
    # the brief is the user's own typed input, retained until account deletion).
    op.create_table(
        "briefs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_briefs_owner_id", "briefs", ["owner_id"])

    # --- generations: METADATA ONLY. No prompts, no outputs, no images —
    # tenancy-and-data.md logging rule. A prompt is a customer's embargoed
    # launch messaging and does not belong in a metrics table.
    op.create_table(
        "generations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("experience_id", sa.Uuid(), nullable=True),
        sa.Column("phase", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("repair", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_generations_owner_id", "generations", ["owner_id"])

    # --- RLS: enable on every app table, owner-scoped, using AND with check.
    # (tenancy-and-data.md: "with check is not optional" — a policy with only
    # using lets an owner insert a row assigning it to someone else.)
    for table in ("experiences", "briefs", "generations"):
        op.execute(f"alter table {table} enable row level security;")
        op.execute(
            f"""
            create policy own_{table} on {table}
              for all to app_user
              using      (owner_id = current_setting('app.user_id')::uuid)
              with check (owner_id = current_setting('app.user_id')::uuid);
            """
        )


def downgrade() -> None:
    for table in ("generations", "briefs", "experiences"):
        op.execute(f"drop policy if exists own_{table} on {table};")
        op.execute(f"alter table {table} disable row level security;")
    op.drop_table("generations")
    op.drop_table("briefs")
    op.drop_table("experiences")

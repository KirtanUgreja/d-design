"""quotas and generations, with their RLS policies

Pulled forward from the persistence table in docs/v1/spec.md (which lists five
tables) because phase 06 needs both immediately: an unattended repair loop
against your own model key is the one way v1 costs real money, and the quota
check has to be transactional to close the A10 race either way.

`quotas` seeds one row for the v1 local user — there is no signup flow yet to
provision one on account creation, and an UPDATE-only atomic increment
(docs/techstack/backend.md) needs a row to already exist.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("quotas", "generations")

# v1 has no signup and no billing — a generous placeholder, not a product
# decision. Real limits arrive with billing (v3).
LOCAL_USER_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_QUOTA_LIMIT = 1000


def upgrade() -> None:
    op.create_table(
        "quotas",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("used", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("limit", sa.Integer(), nullable=False),
        # The kill switch, folded into the same row and the same atomic
        # statement as the quota check rather than a second table: one round
        # trip, one lock, and "halted" fails the same `returning` clause
        # "quota exceeded" does — the caller doesn't need to tell them apart
        # to fail closed correctly (docs/coderules/patterns.md rule 5).
        sa.Column(
            "halted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("owner_id"),
    )

    op.create_table(
        "generations",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("experience_id", sa.Uuid(), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("model_id", sa.String(length=120), nullable=False),
        sa.Column("provider_route", sa.String(length=120), nullable=False),
        sa.Column(
            "tokens_in", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "tokens_out", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "cached_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("calls", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "repaired", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("error_class", sa.String(length=64), nullable=True),
        sa.Column(
            "duration_ms", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generations_owner_id", "generations", ["owner_id"])
    op.create_index("ix_generations_experience_id", "generations", ["experience_id"])

    for table in TABLES:
        op.execute(f"alter table {table} enable row level security")
        op.execute(
            f"""
            create policy own_{table} on {table}
              for all to app_user
              using      (owner_id = current_setting('app.user_id')::uuid)
              with check (owner_id = current_setting('app.user_id')::uuid)
            """
        )
        op.execute(f"grant select, insert, update, delete on {table} to app_user")

    op.execute(
        sa.text(
            'insert into quotas (owner_id, used, "limit") '
            "values (cast(:owner as uuid), 0, :limit)"
        ).bindparams(owner=LOCAL_USER_ID, limit=DEFAULT_QUOTA_LIMIT)
    )


def downgrade() -> None:
    op.execute("drop policy if exists own_generations on generations")
    op.drop_index("ix_generations_experience_id", table_name="generations")
    op.drop_index("ix_generations_owner_id", table_name="generations")
    op.drop_table("generations")

    op.execute("drop policy if exists own_quotas on quotas")
    op.drop_table("quotas")

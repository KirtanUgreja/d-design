"""snapshots, with its RLS policy

v2 phase 00 (docs/v2/plan/00-foundations.md). What phase 06's version history
reads and what phase 07's reskin restores from.

A snapshot is **whole and self-contained**: the scene tree, the resolved art
direction, the motion vocabulary and the mode, all captured together. Storing a
reference and re-resolving at restore time would make "restore" mean "re-render
under whatever the tokens say today", which is not restoring — and phase 07's
exit gate is that reskin-then-restore gives back a tree identical to the
pre-reskin one.

`art_direction` is `jsonb` rather than an id for the same reason: a snapshot
taken under `cinematic-dark` v1 must still restore as v1 after someone
publishes v2 of it.

`owner_id` is carried on the row rather than joined through `experiences`,
which is the shape every tenant-scoped table here already uses — an RLS policy
keys off a column on the row it filters, and a policy that has to join is a
policy that gets slower and easier to get wrong at the same time.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "snapshots",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("experience_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("scenes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "art_direction", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("motion_vocabulary", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        # What a human called it, if anything. Null for the automatic ones.
        sa.Column("label", sa.Text(), nullable=True),
        # What caused it — a reskin, an edit, a publish. Phase 06 shows this in
        # the history panel, and it is the difference between a list of times
        # and a list of reasons.
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["experience_id"], ["experiences.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_snapshots_owner_id", "snapshots", ["owner_id"])
    # The history panel reads one experience's snapshots newest first, which is
    # the only query this table has.
    op.create_index(
        "ix_snapshots_experience_created",
        "snapshots",
        ["experience_id", "created_at"],
    )

    op.execute("alter table snapshots enable row level security")
    op.execute(
        """
        create policy own_snapshots on snapshots
          for all to app_user
          using      (owner_id = current_setting('app.user_id')::uuid)
          with check (owner_id = current_setting('app.user_id')::uuid)
        """
    )
    op.execute("grant select, insert, update, delete on snapshots to app_user")


def downgrade() -> None:
    op.execute("drop policy if exists own_snapshots on snapshots")
    op.drop_index("ix_snapshots_experience_created", table_name="snapshots")
    op.drop_index("ix_snapshots_owner_id", table_name="snapshots")
    op.drop_table("snapshots")

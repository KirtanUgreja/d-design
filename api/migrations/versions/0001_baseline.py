"""The baseline: every table of the `app` database (store/models.py)

Revision ID: 0001
Revises: -
Create Date: 2026-10-08 11:59:36.616777
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blobs",
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("hash"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "avatar",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "decks",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column(
            "data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("aborted", sa.Boolean(), nullable=False),
        sa.Column("history_at", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_decks_updated"), "decks", ["updated"], unique=False)
    op.create_index(op.f("ix_decks_user_id"), "decks", ["user_id"], unique=False)
    op.create_table(
        "deck_files",
        sa.Column("deck_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["hash"],
            ["blobs.hash"],
        ),
        sa.PrimaryKeyConstraint("deck_id", "name"),
    )
    op.create_index(op.f("ix_deck_files_hash"), "deck_files", ["hash"], unique=False)
    op.create_table(
        "events",
        sa.Column("deck_id", sa.String(length=32), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column(
            "data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("deck_id", "seq"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("deck_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=8), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("beat", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_deck_id"), "jobs", ["deck_id"], unique=False)
    op.create_index("ix_jobs_state_created", "jobs", ["state", "created"], unique=False)
    op.create_table(
        "kept",
        sa.Column("deck_id", sa.String(length=32), nullable=False),
        sa.Column("slide_id", sa.String(length=64), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("css", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("deck_id", "slide_id"),
    )
    op.create_table(
        "ledger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("deck_id", sa.String(length=32), nullable=True),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column(
            "data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_at"), "ledger", ["at"], unique=False)
    op.create_index(op.f("ix_ledger_deck_id"), "ledger", ["deck_id"], unique=False)
    op.create_index(op.f("ix_ledger_user_id"), "ledger", ["user_id"], unique=False)
    op.create_table(
        "questions",
        sa.Column("deck_id", sa.String(length=32), nullable=False),
        sa.Column(
            "data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("deck_id"),
    )
    op.create_table(
        "versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("deck_id", sa.String(length=32), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column(
            "deck",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "kept",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_versions_deck_n", "versions", ["deck_id", "n"], unique=False)
    op.create_table(
        "version_files",
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["hash"],
            ["blobs.hash"],
        ),
        sa.ForeignKeyConstraint(["version_id"], ["versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("version_id", "name"),
    )
    op.create_index(op.f("ix_version_files_hash"), "version_files", ["hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_version_files_hash"), table_name="version_files")
    op.drop_table("version_files")
    op.drop_index("ix_versions_deck_n", table_name="versions")
    op.drop_table("versions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_ledger_user_id"), table_name="ledger")
    op.drop_index(op.f("ix_ledger_deck_id"), table_name="ledger")
    op.drop_index(op.f("ix_ledger_at"), table_name="ledger")
    op.drop_table("ledger")
    op.drop_table("kept")
    op.drop_index("ix_jobs_state_created", table_name="jobs")
    op.drop_index(op.f("ix_jobs_deck_id"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("events")
    op.drop_index(op.f("ix_deck_files_hash"), table_name="deck_files")
    op.drop_table("deck_files")
    op.drop_index(op.f("ix_decks_user_id"), table_name="decks")
    op.drop_index(op.f("ix_decks_updated"), table_name="decks")
    op.drop_table("decks")
    op.drop_table("users")
    op.drop_table("blobs")

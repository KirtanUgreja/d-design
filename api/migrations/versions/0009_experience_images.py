"""experiences gets its image sidecar (persistence).

A saved deck needs its images or a reloaded one loses them. `deck_json` holds
the deck alone — the schema has no field for the data URIs, which is why they
ride beside it everywhere else (the build payload, the render service, the
editor store) — so persistence needs the same sidecar.

Known cost, accepted for now: a deck with images is up to a few MB of TEXT.
Postgres TOASTs it out of line, so the row stays small and neither listing nor
the RLS policy touches it. The upgrade path, if it ever bites, is an S3
sidecar with the key in this column instead of the bytes.

Revision ID: 0009_experience_images
Revises: 0008_quotas
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_experience_images"
down_revision: str | None = "0008_quotas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default so existing rows get a valid empty sidecar rather than
    # NULL: every reader can then parse it without a null check.
    op.add_column(
        "experiences",
        sa.Column("images_json", sa.Text(), server_default="{}", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("experiences", "images_json")

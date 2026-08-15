"""experiences gain the hosted-artefact key (phase 18).

The experiences table (0001) stores a deck (deck_json); hosting (phase 18)
gives a deck a hosted URL. The hosted page is the SAME bytes as the
downloadable file — the key of the published HTML object in storage. A deck
that has been published carries that key; a saved-but-unpublished deck has
none (NULL).

No RLS change: experiences stays owner-scoped exactly as 0001 set it.

Revision ID: 0003_published_key
Revises: 0002_brand_kits
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_published_key"
down_revision: str | None = "0002_brand_kits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "experiences",
        sa.Column("published_key", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("experiences", "published_key")

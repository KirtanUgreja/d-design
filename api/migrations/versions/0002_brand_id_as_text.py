"""experiences.brand_id becomes opaque text, not a brand FK yet

Phase 00 modeled `brand_id` as a `brands.id` foreign key before any feature
wrote a brand row — brand kit is phase 10. `schema.experience.Experience`
already requires a non-empty `brand_id` string (every hand-written fixture
uses a placeholder like "brand-1", not a UUID), so the FK/UUID column was
unreachable from day one: the first real write would have failed on both the
type and the constraint. Publish (phase 05) is the first phase that actually
persists an `Experience` row, so this is the first moment the mismatch is
reachable rather than theoretical.

Made a plain nullable string now, with the real FK arriving in phase 10 once
there is a `brands` table row to actually validate against — adding the
missing concept later, not carrying an exception forward.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("experiences_brand_id_fkey", "experiences", type_="foreignkey")
    op.alter_column(
        "experiences",
        "brand_id",
        existing_type=sa.Uuid(),
        type_=sa.String(length=64),
        postgresql_using="brand_id::text",
    )


def downgrade() -> None:
    op.alter_column(
        "experiences",
        "brand_id",
        existing_type=sa.String(length=64),
        type_=sa.Uuid(),
        postgresql_using="brand_id::uuid",
    )
    op.create_foreign_key(
        "experiences_brand_id_fkey", "experiences", "brands", ["brand_id"], ["id"]
    )

"""art_directions gains `fluid`, and the two system rows are seeded

v2 phase 01 (docs/v2/plan/01-ad-format.md -> "Where to resume", step 2).

**A migration, not a script, and that is the security control rather than a
preference.** The write policy 0008 put on this table deliberately has no
`owner_id is null` arm: reading a system art direction is for everybody,
writing one through the tenant wrapper is for nobody, because a tenant that
could insert `owner_id = null` could publish an art direction to every other
account on the platform. A migration runs as the migration role and never
through `as_user()`, so this is the only place a system row can be written at
all.

**`fluid`.** 0008 gave the table a column per token group — `tokens`,
`budgets`, `brand_mapping`, `default_motion` — before the format existed to say
what else there was. Phase 01 found the rest: every clamp triple, the
layout->fit table, texture structure and image treatment, none of which are
expressible as DTCG and all of which live under `$extensions`. That is one more
group, so it is one more column.

`nullable=False` with no default and no backfill, because the table is empty:
nothing in `api` has ever inserted into `art_directions` — 0008 created it for
this phase to fill. If this statement fails on some environment, that
environment has a row nobody wrote through code, and failing loudly is right.

**The values come from `features/art_direction/seed.py`**, validated as
`ArtDirectionRecord` before the insert. A migration that writes jsonb by hand is
a migration that can write a shape the model cannot read back, and the row would
sit there being wrong until a page rendered.

`api/` is a project root rather than a package, so the import below resolves the
same way every other module's does — see the note in AGENTS.md.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from features.art_direction.seed import SYSTEM_ART_DIRECTIONS

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ART_DIRECTIONS = sa.table(
    "art_directions",
    sa.column("id", sa.Text()),
    sa.column("version", sa.Integer()),
    sa.column("name", sa.Text()),
    sa.column("author", sa.Text()),
    sa.column("tokens", postgresql.JSONB()),
    sa.column("budgets", postgresql.JSONB()),
    sa.column("brand_mapping", postgresql.JSONB()),
    sa.column("default_motion", sa.Text()),
    sa.column("fluid", postgresql.JSONB()),
    sa.column("owner_id", sa.Uuid()),
)


def upgrade() -> None:
    op.add_column(
        "art_directions",
        sa.Column("fluid", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )

    op.bulk_insert(
        _ART_DIRECTIONS,
        [
            {
                "id": record.id,
                "version": record.version,
                "name": record.name,
                "author": record.author,
                "tokens": record.tokens.model_dump(
                    mode="json", by_alias=True, exclude_none=True
                ),
                "budgets": record.extensions.budgets.model_dump(
                    mode="json", by_alias=True
                ),
                "brand_mapping": record.extensions.brand_mapping.model_dump(
                    mode="json", by_alias=True
                ),
                "default_motion": record.extensions.default_motion,
                "fluid": record.extensions.fluid.model_dump(
                    mode="json", by_alias=True, exclude_none=True
                ),
                # Null means system. The column that the read policy turns on,
                # and the value the write policy refuses.
                "owner_id": None,
            }
            for record in SYSTEM_ART_DIRECTIONS
        ],
    )


def downgrade() -> None:
    # Only the rows this migration wrote. A blanket delete would take a
    # user-authored art direction with it, and a downgrade that destroys data it
    # did not create is not a downgrade.
    op.execute(
        sa.delete(_ART_DIRECTIONS).where(
            sa.column("owner_id").is_(None),
            sa.tuple_(sa.column("id"), sa.column("version")).in_(
                [(record.id, record.version) for record in SYSTEM_ART_DIRECTIONS]
            ),
        )
    )
    op.drop_column("art_directions", "fluid")

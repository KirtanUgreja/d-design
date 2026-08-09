"""experiences points at a versioned art direction, and picks its motion

v2 phase 00 (docs/v2/plan/00-foundations.md). The one destructive-looking step
in the phase, and the reason the downgrade below is written properly rather
than left as a `pass`: you will use it at least once during phase 01.

**`art_direction` goes from `text` to `jsonb`** because a reference has to
carry a version. `'cinematic-dark'` cannot say *which* `cinematic-dark`, and
from phase 06 a published page is pinned to one — v2 rule 15 is that a
published page never restyles itself, which is unenforceable while the
reference is a bare name. Existing rows become `{"id": …, "version": 1}` in
this same migration, so the column is never briefly a lie.

The conversion is `using` inside the `alter`, not a separate `update`: a type
change and a backfill in two statements is a window where the column exists
with nothing in it, and doing it in one means Postgres either converts every
row or none.

**`motion_vocabulary` is what makes motion an axis rather than a consequence.**
Today `resolveArtDirection` pairs one vocabulary to each art direction in a
code table, so choosing a look chooses the motion with it. A column is the
whole difference between three art directions and twelve combinations, and it
is what phase 02 builds on.

It is `not null` with a server default rather than nullable. Every experience
has *some* motion — the question is only whether it was chosen or inherited —
and a nullable column would push a "no vocabulary set" branch into the renderer,
which is a mode by another name.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every art direction that exists as this migration runs is at version 1, which
# is true by construction: versioning arrives with `art_directions` in 0008 and
# nothing has inserted a second row of anything yet.
_INITIAL_VERSION = 1


def upgrade() -> None:
    op.alter_column(
        "experiences",
        "art_direction",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_type=sa.String(length=64),
        existing_nullable=False,
        postgresql_using=(
            f"jsonb_build_object('id', art_direction, 'version', {_INITIAL_VERSION})"
        ),
    )
    op.add_column(
        "experiences",
        sa.Column(
            "motion_vocabulary",
            sa.Text(),
            nullable=False,
            # `cinematic` is the vocabulary `cinematic-dark` was already paired
            # with in code, so every existing experience keeps exactly the
            # motion it had. A default of "none" would silently strip animation
            # from every page that already existed.
            server_default="cinematic",
        ),
    )


def downgrade() -> None:
    op.drop_column("experiences", "motion_vocabulary")
    # `->>` rather than a cast: `art_direction::text` on a jsonb column yields
    # `"cinematic-dark"` *with* the quotes, which would restore every row to a
    # value that matches no `ArtDirectionId` and fails its schema parse on the
    # next read. The version is dropped, which is the honest inverse — v1's
    # column had nowhere to put one.
    op.alter_column(
        "experiences",
        "art_direction",
        type_=sa.String(length=64),
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=False,
        postgresql_using="art_direction->>'id'",
    )

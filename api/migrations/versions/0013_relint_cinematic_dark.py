"""the system art directions are re-synced after phase 03's linter findings

v2 phase 03 (docs/v2/plan/03-ad-linter.md). The linter judged `cinematic-dark`
against APCA and it failed on three pairs, so the art direction was fixed — and
this is what carries that fix to a database that already ran 0011.

**Why a second migration rather than editing 0011.** 0011 seeds from
`features/art_direction/seed.py`, so a fresh database already gets the corrected
values and needs nothing. An environment that ran 0011 before today does not:
it holds the values as they were that day. A migration that reads current code
writes current values *at the time it runs*, which is right for the environment
that has never seen it and silently wrong for the one that has. This closes that
gap, and the pattern generalises — a change to `seed.py` is a new revision here.

**Why version 1 is updated in place, rather than a version 2 being inserted.**

`(id, version)` is an identity and v2 rule 15 says a published page never
restyles itself, so the reflex is to insert `cinematic-dark` v2 and leave v1
untouched. That reflex is right from the first release onward and is wrong
today, for two reasons worth writing down rather than assuming:

  * **Nothing has been published.** `cinematic-dark` v1 has never been served to
    an audience, so there is no page whose styling this could change out from
    under anyone. Preserving it would be preserving a defect for its own sake.
  * **A published page does not depend on this row anyway.** Phase 01 freezes
    the whole resolved record into the artifact, so `/p/[id]` never reads
    `art_directions` — the pin is belt-and-braces for experiences still being
    edited, and both of those want the corrected colours.

From the first real publish, this stops being true and a token change becomes an
insert. That is phase 06's ground, and the note belongs there as much as here.

Idempotent: it writes the same values every time it runs, and it touches only
the system rows named in `seed.py` — `owner_id is null` is in the predicate, so
a user's own art direction is never caught by a migration that was not about it.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from features.art_direction.seed import SYSTEM_ART_DIRECTIONS

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for record in SYSTEM_ART_DIRECTIONS:
        # Dicts bound through a `JSONB` parameter, **not** JSON text through a
        # cast. The first version of this migration passed `model_dump_json`
        # into a `JSONB` bindparam, which encodes the string *again* and stores
        # a jsonb scalar string rather than an object — a row that inserts
        # cleanly, reports success, and is unreadable. It was caught by looking
        # at the row rather than by the migration failing, which is what that
        # class of bug does.
        op.execute(
            sa.text(
                """
                update art_directions
                   set tokens = :tokens,
                       budgets = :budgets,
                       brand_mapping = :brand_mapping,
                       default_motion = :default_motion,
                       fluid = :fluid,
                       name = :name
                 where id = :id and version = :version and owner_id is null
                """
            ).bindparams(
                sa.bindparam(
                    "tokens",
                    value=record.tokens.model_dump(
                        mode="json", by_alias=True, exclude_none=True
                    ),
                    type_=postgresql.JSONB(),
                ),
                sa.bindparam(
                    "budgets",
                    value=record.extensions.budgets.model_dump(
                        mode="json", by_alias=True
                    ),
                    type_=postgresql.JSONB(),
                ),
                sa.bindparam(
                    "brand_mapping",
                    value=record.extensions.brand_mapping.model_dump(
                        mode="json", by_alias=True
                    ),
                    type_=postgresql.JSONB(),
                ),
                sa.bindparam(
                    "fluid",
                    value=record.extensions.fluid.model_dump(
                        mode="json", by_alias=True, exclude_none=True
                    ),
                    type_=postgresql.JSONB(),
                ),
                id=record.id,
                version=record.version,
                name=record.name,
                default_motion=record.extensions.default_motion,
            )
        )


def downgrade() -> None:
    """A no-op, and deliberately so rather than as an omission.

    The inverse of "make these rows match the code" is "make them match some
    older code", which this revision has no copy of and should not grow one —
    a hardcoded snapshot here would be a third home for the token values,
    disagreeing with both `seed.py` and the database.

    Downgrading past this leaves the corrected art direction in place. That is
    the safe direction to fail in: the values it leaves behind are the ones that
    pass the linter, and the ones it would restore are the ones that do not.
    """

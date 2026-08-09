"""bold-brutalist joins the system art directions, and seeding becomes an upsert

v2 phase 04 (docs/v2/plan/04-three-art-directions.md). Art direction #3, the one
the whole build order is arranged around: the format has to hold a design it was
not extracted from, or it is `cinematic-dark` with extra syntax.

**Why this is an upsert and not an insert, which is the part worth reading.**

0011 seeds by iterating `SYSTEM_ART_DIRECTIONS` in `features/art_direction/
seed.py`. That tuple gained a third entry today, so 0011 *itself* now writes
three rows — a database created after this commit gets `bold-brutalist` from
0011 and would get it a second time from a plain insert here, while a database
migrated last week has two rows and needs it written. One revision cannot be
correct for both if it assumes either.

The general shape is the fix, and 0013 half-found it: a migration that reads
live code writes current values *at the time it runs*, which is right for the
environment that has never seen it and wrong for the one that has. So this
writes every system art direction with `on conflict do update`, which is correct
whatever the database already holds and correct if it is run twice. From here on
**a change to `seed.py` is one more revision of exactly this shape**, and it
subsumes what 0013 did by hand.

It touches only rows with `owner_id is null`. The conflict target is the primary
key `(id, version)`, and the `where` on the update arm is what stops a user's
own art direction being caught by a migration that was not about it — a user
cannot currently create one at all (0008's write policy has no null-owner arm,
and there is no API path), but a predicate that depends on that staying true is
a predicate that fails the day it stops being true.

**Version 1, not 2, for the two that already exist.** `(id, version)` is an
identity and rule 15 says a published page never restyles itself, so the reflex
is to insert new versions. Nothing has been published — see 0013's note, which
argues this in full and is still the live reasoning. From the first real publish
this stops being true and a token change becomes an insert. That is phase 06's
ground.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from features.art_direction.seed import SYSTEM_ART_DIRECTIONS

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The one art direction this revision is *about*, kept separate from the upsert
# above so `downgrade` knows which rows it created rather than guessing. The
# other two predate it and must survive being downgraded past.
_ADDED = ("bold-brutalist", 1)


def upgrade() -> None:
    for record in SYSTEM_ART_DIRECTIONS:
        # Dicts bound through a `JSONB` parameter, **not** JSON text through a
        # cast — 0013 learned this the expensive way. `model_dump_json` into a
        # `JSONB` bindparam encodes the string a second time and stores a jsonb
        # scalar string: a row that inserts cleanly, reports success, and is
        # unreadable. It was caught by looking at a row rather than by anything
        # failing, which is what that class of bug does.
        op.execute(
            sa.text(
                """
                insert into art_directions
                       (id, version, name, author, tokens, budgets,
                        brand_mapping, default_motion, fluid, owner_id)
                values (:id, :version, :name, :author, :tokens, :budgets,
                        :brand_mapping, :default_motion, :fluid, null)
                    on conflict (id, version) do update
                       set name           = excluded.name,
                           author         = excluded.author,
                           tokens         = excluded.tokens,
                           budgets        = excluded.budgets,
                           brand_mapping  = excluded.brand_mapping,
                           default_motion = excluded.default_motion,
                           fluid          = excluded.fluid
                     where art_directions.owner_id is null
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
                author=record.author,
                default_motion=record.extensions.default_motion,
            )
        )


def downgrade() -> None:
    """Removes only the row this revision introduced.

    The two that predate it are left as they are, for the reason 0013's
    downgrade gives: the inverse of "make these rows match the code" is "make
    them match some older code", and a hardcoded snapshot here would be a third
    home for the token values, disagreeing with both `seed.py` and the database.

    Deleting `bold-brutalist` is different — it is a row that did not exist
    before this revision, so removing it is a real inverse rather than a guess.
    An experience referencing it resolves to `not_found` afterwards and renders
    its designed empty state, which is the behaviour phase 01 chose deliberately
    over pretending a compile-time check survived a database read.
    """
    op.execute(
        sa.text(
            "delete from art_directions "
            " where id = :id and version = :version and owner_id is null"
        ).bindparams(id=_ADDED[0], version=_ADDED[1])
    )

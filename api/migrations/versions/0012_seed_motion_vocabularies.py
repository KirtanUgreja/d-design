"""motion_vocabularies is seeded, and the art directions point at the new ids

v2 phase 02 (docs/v2/plan/02-motion-axis.md). The migration that makes motion a
thing you choose rather than a consequence of the look you chose.

**Two vocabularies, both renames of what v1 had in code.** `CINEMATIC_MOTION`
becomes `cinematic-slow` and `EDITORIAL_MOTION` becomes `editorial-restrained`,
with the same numbers — the names are the spec's
(docs/v2/art-direction-system.md) and a rename is all they are.

**`experiences.motion_vocabulary`'s server default moves with them.** Migration
0010 set it to `'cinematic'`, which was the id the code table used and is now
the id of nothing. Every existing row carries that value, so it is rewritten
here: leaving it would leave every experience pointing at a vocabulary the store
cannot resolve, which fails closed — correctly, and on every page at once.

**The art directions' `default_motion` moves for the same reason.** 0011 seeded
them naming `cinematic` and `editorial`. That column is what a *new* experience
inherits, so a stale value there is a page created tomorrow that cannot resolve
its motion.

Both rewrites are scoped to the exact old values rather than applied blanket, so
a row that already named something else — there are none today, and there will
be from phase 11 — is not caught by a migration that was not about it.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from features.motion.seed import SYSTEM_MOTION_VOCABULARIES

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MOTION_VOCABULARIES = sa.table(
    "motion_vocabularies",
    sa.column("id", sa.Text()),
    sa.column("version", sa.Integer()),
    sa.column("tokens", postgresql.JSONB()),
)

# old -> new. The code table's ids on the left, the spec's on the right.
_RENAMES = {
    "cinematic": "cinematic-slow",
    "editorial": "editorial-restrained",
}


def upgrade() -> None:
    op.bulk_insert(
        _MOTION_VOCABULARIES,
        [
            {
                "id": record.id,
                "version": record.version,
                # `id` and `version` are columns, so they do not also belong in
                # the blob — two homes for one value is two places to disagree.
                "tokens": record.model_dump(
                    mode="json", by_alias=True, exclude={"id", "version"}
                ),
            }
            for record in SYSTEM_MOTION_VOCABULARIES
        ],
    )
    _repoint(_RENAMES)

    # The column default too, not only the rows. A default naming a vocabulary
    # that does not exist is a row inserted next week that cannot resolve, and
    # nothing would notice until a page rendered.
    op.alter_column(
        "experiences",
        "motion_vocabulary",
        existing_type=sa.Text(),
        existing_nullable=False,
        server_default=_RENAMES["cinematic"],
    )


def downgrade() -> None:
    op.alter_column(
        "experiences",
        "motion_vocabulary",
        existing_type=sa.Text(),
        existing_nullable=False,
        server_default="cinematic",
    )
    _repoint({new: old for old, new in _RENAMES.items()})
    op.execute(
        sa.delete(_MOTION_VOCABULARIES).where(
            sa.tuple_(sa.column("id"), sa.column("version")).in_(
                [(record.id, record.version) for record in SYSTEM_MOTION_VOCABULARIES]
            )
        )
    )


def _repoint(renames: dict[str, str]) -> None:
    """Rewrite both references, in both directions, from one table.

    One helper rather than two blocks of near-identical SQL: an upgrade whose
    downgrade is spelled out separately is a downgrade that drifts, and this
    migration's whole risk is a reference left naming something that is gone.
    """
    for old, new in renames.items():
        op.execute(
            sa.text(
                "update experiences set motion_vocabulary = :new "
                "where motion_vocabulary = :old"
            ).bindparams(new=new, old=old)
        )
        op.execute(
            sa.text(
                "update art_directions set default_motion = :new "
                "where default_motion = :old"
            ).bindparams(new=new, old=old)
        )

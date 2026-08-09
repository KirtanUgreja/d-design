"""rename the AbstractVisual generator ids

v2 phase 14 (docs/v2/plan/14-texture-without-gradient.md). Three of the five
generators were named for techniques the artifact no longer uses:

    gradient-mesh  ->  halftone-field   four blurred radial gradients
    orb            ->  hatch-drift      a two-stop radial gradient under 40px
    noise-veil     ->  dither-fade      a linear gradient plus turbulence

`particle-field` and `grid-lines` keep their names; `block-collage` is new and
appears in no stored row, so neither needs mapping.

**Why this is a migration and not an edit.** `generator` is a schema `Literal`,
so the moment `scene.py` changed, every stored scene carrying an old id stopped
validating — an experience written last week would fail its Zod parse on read
and the page would 404 rather than render. The ids are a published value.

**The mapping lives here rather than in application code**, which is the point
worth defending: a compatibility shim in the reader is permanent by default —
nobody deletes one, because nobody can prove the old value is gone. A mapping
in a migration runs once, is dated, and is readable afterwards as a record of
what the old names were.

`jsonb_set` per path is not usable here because the generator can sit at any
block index in any scene, and Postgres has no recursive rewrite short of
PL/pgSQL. The text substitution below is safe for two specific reasons, and
neither is "it looked fine":

1. **`jsonb` is stored parsed and re-serialized canonically.** `scenes::text`
   always renders a member as `"key": "value"` — one space after the colon, no
   insignificant whitespace, keys unescaped where they can be. The pattern is
   therefore exact rather than a guess about how the row was written.
2. **The key is matched with the value.** `"generator": "orb"` cannot collide
   with body copy containing the word orb, and `generator` is a closed
   `Literal` with no free-text neighbour that could contain that substring.

Downgrade restores the old ids exactly, because a v1 renderer is still the
thing that reads them if you roll back.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RENAMES: dict[str, str] = {
    "gradient-mesh": "halftone-field",
    "orb": "hatch-drift",
    "noise-veil": "dither-fade",
}


def _rewrite(mapping: dict[str, str]) -> None:
    # Both columns that hold a scene tree. `snapshots` does not exist until v2
    # phase 00, so it is deliberately not touched here — when that table
    # arrives it arrives empty, after this migration.
    for old, new in mapping.items():
        op.execute(
            f"""
            update experiences
               set scenes = replace(
                     scenes::text,
                     '"generator": "{old}"',
                     '"generator": "{new}"'
                   )::jsonb
             where scenes::text like '%"generator": "{old}"%'
            """  # noqa: S608 - keys are module constants, never input
        )


def upgrade() -> None:
    _rewrite(RENAMES)


def downgrade() -> None:
    _rewrite({new: old for old, new in RENAMES.items()})

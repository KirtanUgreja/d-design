"""record what a generation actually cost

v2 phase 15 (docs/v2/plan/15-images.md -> "Cost stays visible").

`generations` has tracked tokens since 0003, and tokens were the right proxy
while every phase was text: docs/v1/ai-pipeline.md is explicit that token cost
is *not* this product's constraint. Imagery is where that stops being true, and
the number is not a projection — measured live against
`google/gemini-3-pro-image` on 2026-08-09, **one image costs $0.137**. At
`MAX_GENERATED_PER_EXPERIENCE = 4` that is about $0.55 of imagery per
experience, against fractions of a cent for all four text phases put together.

Tokens cannot express it. An image response bills per image, and the 1,412
"completion tokens" on that call describe the picture rather than priced text —
a cost column read off the provider's own `usage.cost` is the only honest
number, and OpenRouter returns one on every response, text calls included.

`Numeric(12, 6)`, never a float. Money that accumulates in binary floating
point is a rounding bug with a deadline; micro-dollar precision covers the
cheapest text call and the column still holds five figures of spend.

Nullable, and staying that way. Every row written before this migration has an
unknown cost, and backfilling a zero would make "we have never spent anything"
and "we did not measure" the same value — which is exactly the confusion the
column exists to prevent.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generations",
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generations", "cost_usd")

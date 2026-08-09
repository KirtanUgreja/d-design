"""art_directions and motion_vocabularies, with their policies

v2 phase 00 (docs/v2/plan/00-foundations.md -> "The migrations"). The two token
tables everything else in v2 writes to.

**`(id, version)` is the primary key on both, and a version is not an audit
column here — it is part of the identity.** Phase 06 publishes a page pinned to
one, so updating an art direction *inserts a row* rather than mutating one.
That is what makes v2 rule 15 true ("a published page never restyles itself"):
the old row has to still be there, byte for byte, or a page pinned to it
silently becomes a page pinned to something else.

**`owner_id` is nullable on `art_directions` and the nullability is
load-bearing.** `null` means a system art direction, readable by everyone;
a uuid means a user authored it. That is one column doing what a second table
would otherwise do, and the policy below is where it becomes real:

    owner_id is null or owner_id = current_setting('app.user_id')::uuid

`with check` deliberately does *not* include the `is null` arm. Reading a
system art direction is for everybody; **writing one through the tenant wrapper
is for nobody** — a tenant that could insert `owner_id = null` could publish an
art direction to every other account on the platform. System rows are seeded by
migration, which runs as the migration role and never through `as_user()`.

`motion_vocabularies` has no `owner_id` at all in v2. User-authored motion is
not a v2 feature, and a nullable column with only ever one value in it is a
column that teaches the next reader the wrong thing. It gains one when it needs
one, which is a migration and a policy change together.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "art_directions",
        # `text`, not a uuid: an art direction id is `cinematic-dark`, a name
        # the schema carries as a `Literal` and a published page stores. A
        # surrogate key would add a second identity for the same thing.
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        # One `jsonb` per token group rather than a column per token. The
        # shape's source of truth is Pydantic, and spreading it across columns
        # would be a second definition to keep in step — the same reasoning
        # `briefs` already uses. These are written and read whole.
        sa.Column("tokens", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("budgets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "brand_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("default_motion", sa.Text(), nullable=False),
        # Null means a system art direction. See the module docstring — this is
        # the column the read policy turns on.
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", "version"),
    )
    op.create_index("ix_art_directions_owner_id", "art_directions", ["owner_id"])

    op.execute("alter table art_directions enable row level security")
    op.execute(
        """
        create policy read_art_directions on art_directions
          for select to app_user
          using (owner_id is null
                 or owner_id = current_setting('app.user_id')::uuid)
        """
    )
    # Write is a separate policy from read *because* the two conditions differ.
    # Folding them into one `for all` policy would have made `with check` accept
    # `owner_id is null`, which is a tenant writing a system art direction.
    op.execute(
        """
        create policy write_art_directions on art_directions
          for all to app_user
          using      (owner_id = current_setting('app.user_id')::uuid)
          with check (owner_id = current_setting('app.user_id')::uuid)
        """
    )
    op.execute("grant select, insert, update, delete on art_directions to app_user")

    op.create_table(
        "motion_vocabularies",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tokens", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", "version"),
    )
    # RLS on, and a read-only policy, even though every row is a system row.
    # A table with RLS disabled is a table the isolation test in
    # docs/security/testing.md ("iterate the schema so a new table with no
    # policy fails loudly") is right to complain about — and "there is nothing
    # secret in it" is an argument that ages badly the first time a column is
    # added.
    op.execute("alter table motion_vocabularies enable row level security")
    op.execute(
        """
        create policy read_motion_vocabularies on motion_vocabularies
          for select to app_user
          using (true)
        """
    )
    op.execute("grant select on motion_vocabularies to app_user")


def downgrade() -> None:
    op.execute("drop policy if exists read_motion_vocabularies on motion_vocabularies")
    op.drop_table("motion_vocabularies")
    op.execute("drop policy if exists write_art_directions on art_directions")
    op.execute("drop policy if exists read_art_directions on art_directions")
    op.drop_index("ix_art_directions_owner_id", table_name="art_directions")
    op.drop_table("art_directions")

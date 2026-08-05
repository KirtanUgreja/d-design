"""The application tables, as SQLAlchemy sees them.

`api` owns everything here. It never owns an auth table — those are Drizzle's,
in `web`, and two migration tools against one database survive only because the
table sets are disjoint (docs/techstack/backend.md -> "Two ORMs, one database").

The remaining tables — `assets`, `briefs` — arrive in the phases that need
them, each with its own policy and its own isolation test. A table exists
because something reads it.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID] = mapped_column(index=True)
    display_font: Mapped[str] = mapped_column(String(120))
    text_font: Mapped[str] = mapped_column(String(120))
    primary: Mapped[str] = mapped_column(String(32))
    secondary: Mapped[str] = mapped_column(String(32))
    neutral: Mapped[str] = mapped_column(String(32))
    logo_asset_id: Mapped[UUID | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Experience(Base):
    __tablename__ = "experiences"

    # Without this, an UPDATE leaves `updated_at` (a server-side `onupdate`)
    # marked expired, and the next attribute read tries a lazy refresh —
    # which raises `MissingGreenlet` under asyncio instead of quietly
    # blocking, since there is no sync fallback to fall into. `eager_defaults`
    # fetches server-computed columns via RETURNING on the same statement.
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012 -- SQLAlchemy's own convention; `ClassVar` collides with `DeclarativeBase`'s stub for this name

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(200))
    mode: Mapped[str] = mapped_column(String(16))
    # Opaque text, not a `brands.id` FK yet — brand kit is phase 10, and this
    # column is unreachable as a real FK until a brands row exists to point
    # at. See migrations/versions/0002_brand_id_as_text.py.
    brand_id: Mapped[str | None] = mapped_column(String(64), default=None)
    art_direction: Mapped[str] = mapped_column(String(64))

    # The scene tree is one column and is never normalized. It is always read
    # and written whole, Pydantic validates it rather than SQL, and normalizing
    # would buy queries nobody runs.
    scenes: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Quota(Base):
    """One row per owner, seeded by the migration (v1 has no signup flow to
    provision one on account creation). The atomic increment
    (`features/generation/generation_data.py::consume_quota`) is
    `update ... where used < limit and not halted returning used` — a single
    statement, so there is no window between the check and the consumption
    (docs/techstack/backend.md -> "Rate limits and quotas").

    `halted` is the kill switch, folded into the same row rather than a
    second table or a second query: one round trip, one lock, and a missing
    `RETURNING` row means "refused" either way — the caller doesn't need to
    tell "over quota" from "halted" apart to fail closed correctly
    (docs/coderules/patterns.md rule 5).
    """

    __tablename__ = "quotas"

    owner_id: Mapped[UUID] = mapped_column(primary_key=True)
    used: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    # ponytail: one flat number, no per-phase split, no billing period reset.
    # Real limits and periods arrive with billing (v3) — ../techstack/decisions.md.
    limit: Mapped[int] = mapped_column(Integer)
    halted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Generation(Base):
    """Metadata only — phase, counts, a repair flag, an error class, a
    duration. No prompt, no output, no brief content, ever
    (docs/v1/ai-pipeline.md -> "generations", docs/security/tenancy-and-data.md).
    `owner_id` is denormalized onto the row (not joined through
    `experience_id`) because RLS policies key off a column on the row they
    guard, the same shape as every other tenant-scoped table here.
    """

    __tablename__ = "generations"

    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID] = mapped_column(index=True)
    experience_id: Mapped[UUID] = mapped_column(index=True)
    phase: Mapped[str] = mapped_column(String(16))
    model_id: Mapped[str] = mapped_column(String(120))
    provider_route: Mapped[str] = mapped_column(String(120))
    tokens_in: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    tokens_out: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cached_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    calls: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    repaired: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    error_class: Mapped[str | None] = mapped_column(String(64), default=None)
    duration_ms: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

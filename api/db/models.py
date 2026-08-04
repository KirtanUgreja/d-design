"""The application tables, as SQLAlchemy sees them.

`api` owns everything here. It never owns an auth table — those are Drizzle's,
in `web`, and two migration tools against one database survive only because the
table sets are disjoint (docs/techstack/backend.md -> "Two ORMs, one database").

The other three tables — `assets`, `briefs`, `generations` — arrive in the
phases that need them, each with its own policy and its own isolation test. A
table exists because something reads it.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func, text
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

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(200))
    mode: Mapped[str] = mapped_column(String(16))
    brand_id: Mapped[UUID | None] = mapped_column(ForeignKey("brands.id"), default=None)
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

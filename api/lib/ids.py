"""Identifiers. stdlib, no dependency."""

from uuid import UUID, uuid4


def new_id() -> UUID:
    return uuid4()


def parse_id(raw: str) -> UUID | None:
    """Parse an id that came from outside. `None` rather than a raise, because
    a malformed id in a URL is a client mistake, not a broken invariant."""
    try:
        return UUID(raw)
    except ValueError:
        return None

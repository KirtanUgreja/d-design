"""The no-styling backstop — the runtime half of patterns.md rule 1.

The schema is the first line: a hex code has nowhere to live. This is the
second line: a walk over every generated tree that rejects any string value
matching a presentational pattern, before the tree is stored or rendered.

When this fires it means the schema has a gap a value slipped through — add the
missing concept to the design family, never add an exception to the check.
"""

from __future__ import annotations

import re

# A hex colour, a length/duration in px/rem/em/pt/ms/s, or a CSS function that
# is inherently presentational. There is never a legitimate reason for AI output
# to contain one of these tokens, so the check is allowed to be strict.
PRESENTATIONAL = re.compile(
    r"#[0-9a-f]{3,8}\b"  # #fff, #ffffff, #ff00ff00
    r"|[\d.]+(?:px|rem|em|pt|ms|s)\b"  # 12px, 1.5rem, 300ms
    r"|\b(?:rgb|rgba|hsl|hsla|cubic-bezier)\(",
    re.IGNORECASE,
)

# Values that are legitimately CSS-shaped but are content, not styling. The
# renderer formats the body text; it does not style from the model.
_ALLOWED_KEYS: frozenset[str] = frozenset()


def has_presentational_value(value: object, key: str = "") -> bool:
    """Return True if ``value`` contains a presentational token.

    Recursively walks lists, tuples and dicts. ``key`` is carried for error
    messages only; a key named like a style is not an exception.
    """
    if isinstance(value, str):
        return PRESENTATIONAL.search(value) is not None
    if isinstance(value, dict):
        return any(has_presentational_value(v, str(k)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(has_presentational_value(v, key) for v in value)
    return False


def assert_no_presentational_values(model: object) -> None:
    """Raise ValueError if any presentational value is found in ``model``.

    Call this on every generated tree at the pipeline boundary, before the tree
    is stored or rendered.
    """
    if has_presentational_value(model):
        raise ValueError(
            "AI output carried a presentational value — "
            "add the missing concept to the design family"
        )

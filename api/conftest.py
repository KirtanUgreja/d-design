"""Load `.env` for local runs. CI sets the variables directly, so anything
already in the environment wins — a test run must never be silently reconfigured
by a file on someone's laptop.

At the rootdir, not `tests/`: a conftest.py only auto-applies to test files
under its own directory, and most tests are colocated with the module they
test (docs/coderules/structure.md -> "Colocate") rather than living under
`tests/`. A conftest scoped to `tests/` only loads `.env` when a run happens
to also collect something in there — fine for the full suite, wrong for
`pytest ai/test_complete.py` on its own.
"""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

ENV = Path(__file__).resolve().parent / ".env"

if ENV.exists():
    for line in ENV.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@pytest.fixture(scope="session", autouse=True)
async def close_pool() -> AsyncIterator[None]:
    """Return the pool's connections before the loop goes away."""
    yield
    from db.engine import engine

    await engine().dispose()

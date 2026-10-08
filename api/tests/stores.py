"""Both stores, for tests that must hold on each (phase 29, item A1).

``files`` and ``sql`` (SQLite in a temp file) always run. ``postgres`` runs
only when ``TEST_DATABASE_URL`` names a database called ``app_test``: it is
migrated with Alembic once and emptied before every test.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from store.files import Store
from store.models import Base
from store.sql import SqlStore
from store.tenant import AnyStore

API = Path(__file__).resolve().parent.parent
PG_URL = os.environ.get("TEST_DATABASE_URL", "")
STORES = ["files", "sql", *(["postgres"] if PG_URL else [])]

_migrated: list[bool] = []


def make_store(kind: str, tmp_path: Path) -> AnyStore:
    if kind == "files":
        return Store(tmp_path / "data")
    if kind == "sql":
        store = SqlStore(f"sqlite:///{tmp_path / 'app.db'}", tmp_path / "scratch")
        store.create_tables()
        return store
    if urlsplit(PG_URL).path.rsplit("/", 1)[-1] != "app_test":
        raise RuntimeError("TEST_DATABASE_URL must name the app_test database, never app")
    if not _migrated:
        config = Config(str(API / "alembic.ini"))
        config.attributes["url"] = PG_URL
        command.upgrade(config, "head")
        _migrated.append(True)
    store = SqlStore(PG_URL, tmp_path / "scratch")
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with store.engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    return store

"""Alembic for the `app` database (phase 29). The tables are ``store/models.py``.

The URL, first found wins: ``config.attributes["url"]`` (tests), ``-x url=...``,
then ``APP_DATABASE_URL``. Migrations run on Neon's direct host, never the
pooler (``store.sql.direct_url``).

    cd api && uv run alembic upgrade head
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

import settings
from store.models import Base
from store.sql import direct_url

config = context.config


def _url() -> str:
    given = config.attributes.get("url")
    if isinstance(given, str) and given:
        return direct_url(given)
    url = context.get_x_argument(as_dictionary=True).get("url") or settings.load().database_url
    if not url:
        raise SystemExit("APP_DATABASE_URL is not set")
    return direct_url(url)


def run() -> None:
    url = _url()
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(url, poolclass=NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run()

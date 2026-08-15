"""brand_kits feature — team-shared brand kits (v3, phase 17).

The public surface of the feature. api owns the brand_kits/teams tables
(Alembic set); web reads and writes them through the FastAPI routes, never
through Drizzle. The data module (brand_kits_data.py) is the only place
SQLAlchemy appears here.
"""

from features.brand_kits.brand_kits_data import (
    BrandKitRecord,
    create_kit,
    get_kit,
    list_kits_for_team,
    list_teams,
)

__all__ = [
    "BrandKitRecord",
    "create_kit",
    "get_kit",
    "list_kits_for_team",
    "list_teams",
]

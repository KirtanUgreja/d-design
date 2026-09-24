"""The api HTTP entry — FastAPI (v3, phase 17).

api owns the app tables (experiences, briefs, generations, teams, brand_kits)
and serves them behind the session resolution (auth/session_data.py) plus the
as_user tenant wrapper. The auth tables are web's; api never writes them.

The generation routes put the v1 pipeline on the product surface: the editor
can now drive interview → mapping → build over HTTP instead of only through
cli.py. cli.py remains the eval and batch driver.
"""

from __future__ import annotations

from fastapi import FastAPI

from features.brand_kits.routes import router as brand_kits_router
from features.experiences.routes import router as experiences_router
from features.generation.routes import router as generation_router
from features.quotas.routes import router as quotas_router

app = FastAPI(title="d-design api", version="0.1.0")

app.include_router(brand_kits_router)
app.include_router(experiences_router)
app.include_router(generation_router)
app.include_router(quotas_router)

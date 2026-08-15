"""The api HTTP entry — FastAPI (v3, phase 17).

api owns the app tables (experiences, briefs, generations, teams, brand_kits)
and serves them behind the session resolution (auth/session_data.py) plus the
as_user tenant wrapper. The auth tables are web's; api never writes them.

The model seam and the pipeline stay CLI-driven (cli.py); this app is the
product surface api exposes to web.
"""

from __future__ import annotations

from fastapi import FastAPI

from features.brand_kits.routes import router as brand_kits_router
from features.experiences.routes import router as experiences_router
from features.quotas.routes import router as quotas_router

app = FastAPI(title="d-design api", version="0.1.0")

app.include_router(brand_kits_router)
app.include_router(experiences_router)
app.include_router(quotas_router)

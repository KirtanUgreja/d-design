"""The `api` entry point.

`api` and `jobs` are one codebase with two entry points — same models, same
data modules, same seam. `jobs` arrives in v3 and will sit next to this file.
"""

from fastapi import FastAPI

from routes.experiences import router as experiences_router
from routes.generation import router as generation_router
from routes.health import router as health_router

app = FastAPI(title="d-design api", docs_url=None, redoc_url=None)
app.include_router(health_router)
app.include_router(experiences_router)
app.include_router(generation_router)

"""The `api` entry point.

`api` and `jobs` are one codebase with two entry points — same models, same
data modules, same seam. `jobs` arrives in v3 and will sit next to this file.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.assets import router as assets_router
from routes.brand import router as brand_router
from routes.director import router as director_router
from routes.edit import router as edit_router
from routes.experiences import router as experiences_router
from routes.generation import router as generation_router
from routes.health import router as health_router
from routes.intake import router as intake_router

app = FastAPI(title="d-design api", docs_url=None, redoc_url=None)

# Found live, building the Director harness (docs/v1/plan/07-director.md):
# `web` calls `api` directly from the browser (NEXT_PUBLIC_API_URL, no
# proxy — docs/techstack/decisions.md), and with no CORS middleware at all
# the preflight OPTIONS request 405s, so every one of those calls —
# Director's, and Build's SSE client from phase 06 — silently failed with
# "Failed to fetch" the first time either was exercised against a real
# browser rather than a mocked `fetch`.
#
# A `localhost:*` regex, not an explicit allowlist, and that is a v1-only
# stance, not a template for later: v1 has one local user, no cookies, no
# session (`allow_credentials` stays at its default `False` — nothing here
# is credentialed CORS), and no deployed `web` origin yet to allowlist
# against. The moment a real origin exists, this becomes an explicit list
# and the regex goes — reflecting an arbitrary origin is exactly the
# mistake docs/security/content-and-web.md calls out for the v3 public
# endpoints ("origin reflection is how a CORS policy becomes no CORS
# policy"), and that reasoning applies here just as soon as there is
# something worth stealing behind it.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(experiences_router)
app.include_router(intake_router)
app.include_router(director_router)
app.include_router(generation_router)
app.include_router(edit_router)
app.include_router(assets_router)
app.include_router(brand_router)

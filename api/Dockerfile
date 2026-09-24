# The api service — FastAPI over the app tables (v3, phases 16–19) and the
# generation stages, which put the v1 pipeline on the product surface.
#
# The image carries no model key. OPENROUTER_API_KEY arrives as an environment
# variable and the generation routes refuse with 503 without it — fail closed
# (AGENTS.md rule 10), so a misconfigured deploy is a visible refusal rather
# than an anonymous call.
#
# Built from api's own lockfile (backend.md: uv owns the Python lock).
FROM python:3.13-slim

# uv at the version the lockfile was resolved with. UV_PYTHON_DOWNLOADS=never
# keeps the build offline-ish: use the image's interpreter, do not fetch one.
COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Explicit, not `COPY . .` — the local .venv and __pycache__ trees must not
# enter the image.
COPY ai ./ai
COPY auth ./auth
COPY db ./db
COPY features ./features
COPY lib ./lib
COPY migrations ./migrations
COPY pipeline ./pipeline
COPY schema ./schema
COPY app.py cli.py alembic.ini ./

EXPOSE 8000

CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

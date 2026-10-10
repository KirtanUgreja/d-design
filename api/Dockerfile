# The API service (docs/techstack/infrastructure.md): private on Railway's
# network, no model key, no browser. Migrates the app database, then serves.
FROM public.ecr.aws/docker/library/python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_FROZEN=1 UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=never DATA_DIR=/tmp/data
COPY pyproject.toml uv.lock ./
RUN uv sync --no-install-project
COPY . .
RUN uv sync
# "::" so Railway's private network (IPv6) reaches it.
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && exec uv run --no-sync uvicorn app:serve --factory --host :: --port ${PORT:-8000}"]

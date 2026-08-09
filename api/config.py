"""Environment, read once, in one place.

stdlib `os.environ` rather than pydantic-settings: this is a dozen strings and
a frozen dataclass reads them. Rung 3 of the ladder.
"""

import os
from dataclasses import dataclass
from functools import cache


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


@dataclass(frozen=True, slots=True)
class Config:
    database_url: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str
    # v1 has one user. `as_user` takes this exactly as v3 will take a resolved
    # session's user id — the wrapper does not know the difference, which is
    # the whole reason for building it now.
    local_user_id: str
    # One provider seam, OpenRouter behind it (docs/techstack/backend.md ->
    # "Model access"). No default model for any phase — a wrong default is
    # worse than a loud failure, since "wrong" here means silently spending
    # money on a model nobody chose (docs/techstack/ai-stack.md).
    openrouter_api_key: str
    openrouter_model_intake: str
    openrouter_model_director: str
    openrouter_model_build: str
    openrouter_model_edit: str
    # Image generation. A different response shape entirely — no
    # `response_format`, bytes come back as a data URI — but the same endpoint,
    # the same key, and the same seam (docs/v2/plan/15-images.md).
    openrouter_model_image: str


@cache
def config() -> Config:
    return Config(
        database_url=_require("DATABASE_URL"),
        s3_endpoint=_require("S3_ENDPOINT"),
        s3_bucket=_require("S3_BUCKET"),
        s3_access_key=_require("S3_ACCESS_KEY"),
        s3_secret_key=_require("S3_SECRET_KEY"),
        s3_region=os.environ.get("S3_REGION", "us-east-1"),
        local_user_id=_require("LOCAL_USER_ID"),
        openrouter_api_key=_require("OPENROUTER_API_KEY"),
        openrouter_model_intake=_require("OPENROUTER_MODEL_INTAKE"),
        openrouter_model_director=_require("OPENROUTER_MODEL_DIRECTOR"),
        openrouter_model_build=_require("OPENROUTER_MODEL_BUILD"),
        openrouter_model_edit=_require("OPENROUTER_MODEL_EDIT"),
        openrouter_model_image=_require("OPENROUTER_MODEL_IMAGE"),
    )

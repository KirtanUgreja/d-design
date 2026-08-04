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
    )

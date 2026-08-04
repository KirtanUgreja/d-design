"""Object storage. One implementation, pointed at MinIO locally and S3 in
production — a connection string apart, because MinIO speaks the same protocol.

MinIO from day one is deliberate: this is the only abstraction in the project
with a planned second implementation, and developing against the real S3 API
means it ends up with one implementation after all.

boto3 is synchronous, so every call goes through the threadpool. One blocking
call in an async handler blocks the whole event loop, and the symptom is
latency on unrelated requests — the hardest kind of bug to attribute.
docs/coderules/python.md -> "Async, and the one thing that bites"
"""

from functools import cache

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_s3.client import S3Client
from starlette.concurrency import run_in_threadpool

from config import config
from lib.result import Result, err, ok


@cache
def _client() -> S3Client:
    c = config()
    return boto3.client(
        "s3",
        endpoint_url=c.s3_endpoint,
        aws_access_key_id=c.s3_access_key,
        aws_secret_access_key=c.s3_secret_key,
        region_name=c.s3_region,
    )


def _put(key: str, body: bytes, content_type: str) -> None:
    _client().put_object(
        Bucket=config().s3_bucket, Key=key, Body=body, ContentType=content_type
    )


def _get(key: str) -> bytes:
    return _client().get_object(Bucket=config().s3_bucket, Key=key)["Body"].read()


async def put_object(key: str, body: bytes, content_type: str) -> None:
    """Write. Raises on failure — a storage outage is not something a caller can
    branch on usefully, and there is no permissive default to get wrong."""
    await run_in_threadpool(_put, key, body, content_type)


async def get_object(key: str) -> Result[bytes]:
    """Read. A missing key is an expected outcome, so it is a `Result` and not
    an exception; anything else is an outage and raises."""
    try:
        return ok(await run_in_threadpool(_get, key))
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            return err("not_found", key)
        raise

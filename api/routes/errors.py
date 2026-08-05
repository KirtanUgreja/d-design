"""`AppError` -> `HTTPException`. One mapping, so a route's error branch is a
one-liner and the status code for a given `ErrorCode` never drifts between
routes.
"""

from fastapi import HTTPException

from lib.result import AppError

_STATUS = {
    "unauthorized": 401,
    "not_found": 404,
    "invalid_input": 422,
    "quota_exceeded": 429,
    "upstream_unavailable": 503,
    "repair_exhausted": 502,
}


def as_http_exception(error: AppError) -> HTTPException:
    return HTTPException(status_code=_STATUS[error.code], detail=error.message)

"""Uploads and the asset list.

The route is thin, as every route here is, but the thinness matters more on
this one: the six controls live in `features/assets/upload.py` where they can
be tested without a request, and this file's whole job is to hand it bytes and
turn a `Result` into a status code.
"""

from uuid import UUID

from fastapi import APIRouter, File, Response, UploadFile

from config import config
from db.tenant import as_user
from features.assets import (
    find_by_storage_key,
    get_asset,
    list_assets,
    read_object,
    save_asset,
    store,
    verify_and_reencode,
)
from features.assets.upload import MAX_BYTES, SVG_MIME
from lib.result import AppError, Err
from routes.errors import as_http_exception
from schema.experience import Asset

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("")
async def index() -> list[Asset]:
    async with as_user(config().local_user_id) as session:
        return await list_assets(session)


@router.post("", status_code=201)
async def upload(file: UploadFile = File(...)) -> Asset:  # noqa: B008 -- FastAPI's own dependency idiom
    owner_id = config().local_user_id

    # Read bounded, not whole. `UploadFile` spools to disk, so `.read()` with no
    # argument would happily materialize a multi-gigabyte body before the size
    # cap ever ran — the cap has to be applied to the read itself, not after it.
    # One byte over the limit is enough to know, and is cheaper than measuring.
    raw = await file.read(MAX_BYTES + 1)

    # The filename is never read. Not sanitized, not slugified: a name that
    # never reaches a path cannot traverse one, and `content_type` is skipped
    # for the same reason — both are attacker-supplied, and the bytes decide.
    verified = verify_and_reencode(raw)
    if isinstance(verified, Err):
        raise as_http_exception(verified.error)

    ready = verified.value
    await store(ready)

    async with as_user(owner_id) as session:
        row = await save_asset(
            session,
            owner_id=UUID(owner_id),
            kind="image",
            storage_key=ready.storage_key,
            mime=ready.content_type,
            width=ready.width,
            height=ready.height,
            alt=None,
            source="upload",
        )
        return Asset(
            id=str(row.id),
            kind="image",
            storage_key=row.storage_key,
            mime=row.mime,
            width=row.width,
            height=row.height,
            alt=row.alt,
            source="upload",
        )


__all__ = ["SVG_MIME", "asset_by_id", "router"]


# Controls 5 and 6, at the point they are observable: the browser.
#
#   5. The content type is the server's own — recorded when the bytes were
#      verified, never derived from the request, the extension, or a stored
#      filename (there is no stored filename). `nosniff` stops the browser
#      second-guessing it, and an image reinterpreted as HTML is an XSS.
#   6. Every asset is served from this one prefix, which serves nothing else —
#      no HTML, no JSON, no app route — so a content-type confusion is
#      contained to a path with nothing to confuse it with.
#
# ponytail: one prefix, one origin. docs/security/content-and-web.md wants
# assets on `assets.<domain>`, a separate origin, so that even a total
# content-type failure lands somewhere with no cookies and no same-origin
# reach. That is a DNS and deploy change rather than a code one; the single
# prefix is built now so the move is a host swap and not a re-plumbing.
@router.get("/{storage_key:path}")
async def serve(storage_key: str) -> Response:
    """`storage_key:path` takes the slashes, and the traversal guard is that
    the key is matched against the database rather than joined onto anything.
    `../` in the path resolves to no row, which is a 404 — there is no filesystem
    join here to escape from."""
    async with as_user(config().local_user_id) as session:
        asset = await find_by_storage_key(session, storage_key)
    if asset is None:
        raise as_http_exception(AppError("not_found", "no such asset"))

    return await _serve_bytes(asset)


async def _serve_bytes(asset: Asset) -> Response:
    """The one place asset bytes leave this service, shared by the two routes
    that reach them. Two routes with two copies of these headers is two places
    for `nosniff` to be dropped from."""
    body = await read_object(asset.storage_key)
    if isinstance(body, Err):
        raise as_http_exception(AppError("not_found", "no such asset"))

    return Response(
        content=body.value,
        # From the stored, re-encoded type. Never the request's, never sniffed.
        media_type=asset.mime,
        headers={
            "X-Content-Type-Options": "nosniff",
            # Belt and braces for the SVG case: reached directly rather than
            # through `<img>`, a sandboxed document with no scripting is inert.
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
            # A key is a UUID minted for those exact bytes, so changed content
            # is a different key.
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Disposition": "inline",
        },
    )


# A second router, mounted at `/a`, because this path is composed by the
# *renderer* rather than requested by the app.
#
# docs/v2/plan/15-images.md -> "Resolution: a same-origin path, composed from an
# id". The renderer is pure and cannot fetch (patterns.md rule 6), so the only
# URL it can produce is one derived from something already in the scene tree —
# and an `Image` block carries an `assetId`. Composing `/a/{id}` is string work
# that behaves identically in the browser, the app server and the render
# service. A signed URL cannot: it needs a secret, a clock and a network call,
# and it would put all three inside the renderer.
#
# Short on purpose. It appears in published HTML once per image.
asset_by_id = APIRouter(prefix="/a", tags=["assets"])


@asset_by_id.get("/{asset_id}")
async def serve_by_id(asset_id: UUID) -> Response:
    """Resolution by id, which is the only handle the renderer has.

    `asset_id` is typed as `UUID`, so a path that is not one is a 422 before any
    code here runs — there is no string to traverse with and no key to forge.
    The lookup is tenant-scoped through `as_user()` like every other read, and a
    miss is a 404 rather than a fallback: an `except` that returned the bytes
    would be the vulnerability rule 10 names, not error handling.
    """
    async with as_user(config().local_user_id) as session:
        asset = await get_asset(session, asset_id)
    if asset is None:
        raise as_http_exception(AppError("not_found", "no such asset"))
    return await _serve_bytes(asset)

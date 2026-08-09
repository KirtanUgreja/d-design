"""The upload pipeline (docs/v1/plan/10-brand-and-uploads.md).

    file -> caps -> magic bytes -> re-encode -> uuid key -> stored -> Asset row

**The order is the control.** Every check that costs memory or CPU runs after
every check that does not, so a decompression bomb is refused by arithmetic on
a header rather than by an allocator that has already lost.

ponytail: upload verification and re-encode run in-process. docs/techstack/
backend.md puts this in the fetch worker — the container with no database, no
VPC route and nothing worth stealing — and that container is v3. So this runs
next to the database credentials, which is exactly the placement
docs/coderules/dependencies.md says should feel wrong. Accepted for one
reason: v1 is a single local user uploading their own product shots, with no
other tenant to reach and no network exposure. It stops being acceptable the
moment a second person has an account. Move the whole pipeline to the fetch
worker before the first outside account exists — the interface is a function
call today and an HTTP boundary then.

**Six refusals, six sentences.** A rejected upload is a user holding their own
logo, being told no by a product that has just promised to keep them on brand.
"Invalid file" answers none of the six questions, so each control says which
one failed and what to do instead. None of them names the internal error class,
which is logged and never displayed (docs/security/operations.md).
"""

import io
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError

from features.assets.sanitize_svg import sanitize_svg
from lib.result import Err, Result, err, ok
from lib.storage import get_object, put_object

# Control 1a: a byte cap, applied to the bytes themselves. Cheapest possible
# check and the only one that runs before anything has been read into a parser.
MAX_BYTES = 10 * 1024 * 1024

# Control 1b: a *pixel* cap, applied to the header's declared dimensions and
# never to a decoded buffer. This is the decompression-bomb control: a 200KB
# PNG can declare 30000x30000 and decode to gigabytes, and by the time an
# allocator has been asked for that, the process is already gone. 40 megapixels
# is larger than any product shot and far smaller than a bomb.
MAX_PIXELS = 40_000_000

# Pillow's own guard, set to the same number. It raises `DecompressionBombError`
# rather than allocating — belt and braces, because `Image.open` reads a header
# before this module gets to look at one.
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

# Control 2: magic bytes. Extension and `Content-Type` are attacker-supplied and
# are never consulted — this maps what the *content* says it is to what will be
# stored, and a format absent from this table is refused whatever it claims.
_RASTER = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}

# Everything is re-encoded to one of two formats. Normalizing kills polyglots
# (a file that is a valid GIF *and* a valid HTML document) and strips EXIF,
# which carries GPS coordinates from a phone camera.
_REENCODE_TO = {"image/png": ("PNG", "image/png"), "image/jpeg": ("JPEG", "image/jpeg")}

SVG_MIME = "image/svg+xml"


class Upload:
    """What the pipeline produces: bytes to store and the row to write.

    Deliberately not the `Asset` schema — an `Asset` has an id, and an id
    belongs to the database, not to a function that has only inspected bytes.
    """

    __slots__ = (
        "body",
        "content_type",
        "height",
        "storage_key",
        "thumb",
        "width",
    )

    def __init__(
        self,
        body: bytes,
        content_type: str,
        width: int | None,
        height: int | None,
        thumb: bytes | None = None,
    ) -> None:
        self.body = body
        self.content_type = content_type
        self.width = width
        self.height = height
        # The small rendition, or `None` when there is nothing to gain from one
        # — an SVG has no pixels, and an image already narrower than the
        # breakpoint would be re-encoded into a *larger* file for no reason.
        self.thumb = thumb
        # Control 4: the storage key is a server-generated UUID and the user's
        # filename is never read. Not sanitized, not slugified — never read: a
        # filename that never reaches a path cannot traverse one, and the
        # sanitizing version of this is the one with the bug in it.
        self.storage_key = f"assets/{uuid4()}"


def verify_and_reencode(raw: bytes) -> Result[Upload]:
    """Controls 1-4. Pure: no storage, no database, no owner — which is what
    makes every one of them testable without either."""
    if not raw:
        return err("invalid_input", "that file is empty")

    # Control 1a, before anything parses anything.
    if len(raw) > MAX_BYTES:
        return err(
            "invalid_input",
            f"that file is larger than {MAX_BYTES // (1024 * 1024)}MB; "
            "export it at a smaller size and try again",
        )

    if _looks_like_svg(raw):
        sanitized = sanitize_svg(raw)
        if isinstance(sanitized, Err):
            return sanitized
        # No re-encode and no dimensions: an SVG has no pixels, and the
        # sanitizer's own output is already a re-serialization of a parsed tree
        # rather than the user's bytes with pieces removed.
        return ok(Upload(sanitized.value, SVG_MIME, None, None))

    try:
        with Image.open(io.BytesIO(raw)) as probe:
            declared = probe.format
            width, height = probe.size
    except Image.DecompressionBombError:
        return err("invalid_input", "that image's dimensions are too large to process")
    except (UnidentifiedImageError, OSError, ValueError):
        # Control 2 in its most common form: the bytes are not an image at all,
        # whatever the extension said. A PHP file renamed `.png` lands here.
        return err("invalid_input", "that file is not an image we can read")

    if declared not in _RASTER:
        return err(
            "invalid_input",
            "that image format is not supported; use PNG, JPEG, WEBP, GIF or SVG",
        )

    # Control 1b: the header's numbers, multiplied. Still no pixel buffer.
    if width * height > MAX_PIXELS:
        return err("invalid_input", "that image's dimensions are too large to process")

    source_mime = _RASTER[declared]
    target_format, content_type = _REENCODE_TO.get(source_mime, ("PNG", "image/png"))

    # Control 3: re-encode. Only now is anything decoded, and only after both
    # caps have already passed.
    thumb: bytes | None = None
    try:
        with Image.open(io.BytesIO(raw)) as image:
            flattened = image.convert("RGB" if target_format == "JPEG" else "RGBA")
            buffer = io.BytesIO()
            # `exif` and every other metadata block is dropped by writing a new
            # file from pixels rather than by editing the original's headers.
            flattened.save(buffer, format=target_format)
            thumb = _thumbnail(flattened, target_format, width, len(buffer.getvalue()))
    except (OSError, ValueError):
        return err(
            "invalid_input", "that image could not be processed; try re-saving it"
        )

    return ok(Upload(buffer.getvalue(), content_type, width, height, thumb))


# The small rendition's width. Two sizes, not four: a hero and a grid cell are
# the two real cases and the third is speculative (docs/v2/plan/15-images.md).
# 480 is a grid cell at 2x on a phone.
THUMB_WIDTH = 480

# `-sm` beside the original, so the small key is *derivable* from the large one
# rather than being a second column. Same reasoning as `/a/{id}` itself: a
# value you can compute is a value the renderer can reach without a lookup, and
# a column that can disagree with the object store is a column that eventually
# does.
THUMB_SUFFIX = "-sm"


def thumb_key(storage_key: str) -> str:
    return f"{storage_key}{THUMB_SUFFIX}"


def _thumbnail(
    image: Image.Image, target_format: str, width: int, full_size: int
) -> bytes | None:
    """A second, narrower encode from the *already decoded* image.

    Reuses the decode the re-encode above already paid for — a second
    `Image.open` would double the most expensive step in the pipeline, and it
    would do it on bytes that have already passed both caps, which is the one
    place this file allows itself to relax.

    Returns `None` unless the result is genuinely worth serving, which is two
    conditions and not one:

    **Fewer pixels.** An image already at or below the breakpoint has nothing
    to give up.

    **Fewer bytes.** Not implied by the first, which is the part that surprises:
    downscaling *sharp* artwork — a logo, a diagram, a screenshot, all things
    people upload — resamples hard edges into intermediate colours that PNG
    compresses far worse than the originals. Measured on a 600x400 synthetic
    pattern: 6,045 bytes full size, 11,287 bytes "small". A browser handed that
    `srcset` would dutifully pick the larger file for the smaller slot, so the
    rendition is only kept when it actually pays.
    """
    if width <= THUMB_WIDTH:
        return None
    small = image.copy()
    small.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 4), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    small.save(buffer, format=target_format)
    encoded = buffer.getvalue()
    return encoded if len(encoded) < full_size else None


async def store(upload: Upload) -> None:
    """Controls 5 and 6. The content type is the server's own — derived from
    what the bytes turned out to be, never from what the request claimed — and
    every asset lives under one prefix, which is what keeps a content-type
    confusion contained to an origin that serves nothing else."""
    await put_object(upload.storage_key, upload.body, upload.content_type)
    if upload.thumb is not None:
        await put_object(
            thumb_key(upload.storage_key), upload.thumb, upload.content_type
        )


async def read_object(storage_key: str) -> Result[bytes]:
    """The stored bytes. One storage path, `lib/storage.py`, shared with
    publish — never a second client (docs/v1/plan/10-brand-and-uploads.md).

    A `Result`, because a row can outlive its object: the row is written after
    the upload but nothing guarantees the two stay in step forever, and a
    missing object is a 404 rather than a traceback."""
    return await get_object(storage_key)


def _looks_like_svg(raw: bytes) -> bool:
    """Magic bytes for a text format. An SVG has no signature, so the test is
    the first non-whitespace bytes being an XML or `<svg` opening — checked on a
    bounded prefix so a multi-megabyte line of spaces cannot turn this into a
    scan."""
    head = raw[:1024].lstrip()
    return (
        head.startswith(b"<?xml") or head.startswith(b"<svg") or b"<svg" in head[:512]
    )


def asset_id_of(value: str) -> UUID | None:
    """A caller-supplied asset id, or None. Used where an id arrives from a
    request path and would otherwise reach the database as a raw string."""
    try:
        return UUID(value)
    except ValueError:
        return None

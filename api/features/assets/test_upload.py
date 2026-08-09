"""The six upload controls, one test each, plus the SVG pair.

Every row of docs/security/testing.md -> "Uploads" appears here, and each test
names which control it is exercising — the point of the six is that they are
six, so a test that only proves "bad file rejected" would prove none of them.
"""

import io
import time

import pytest
from PIL import Image

from features.assets.sanitize_svg import sanitize_svg
from features.assets.upload import MAX_BYTES, MAX_PIXELS, SVG_MIME, verify_and_reencode
from lib.result import Err, Ok


def _png(width: int = 8, height: int = 8) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_with_exif() -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (16, 16), (10, 120, 200))
    exif = image.getexif()
    exif[271] = "CanaryCam"  # Make
    exif[34853] = {}  # GPSInfo tag id
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


# --- Control 1: size and dimension caps, before decode ---------------------


def test_a_file_over_the_byte_cap_is_refused() -> None:
    result = verify_and_reencode(b"x" * (MAX_BYTES + 1))
    assert isinstance(result, Err)
    assert "larger than" in result.error.message


def test_a_decompression_bomb_is_refused_without_decoding_it() -> None:
    """A 200KB PNG can decode to gigabytes. The control is arithmetic on the
    header's declared dimensions, so this has to be refused *before* a pixel
    buffer is allocated — which is why the assertion is on elapsed time and not
    only on the rejection. A version that decoded first would still return an
    error, and would still be the bug."""
    buffer = io.BytesIO()
    # ~19000x19000 of one colour: tiny compressed, ~1GB decoded.
    Image.new("L", (19000, 19000), 0).save(buffer, format="PNG")
    bomb = buffer.getvalue()
    assert len(bomb) < 1_000_000, (
        "the bomb should be small on disk, or it proves nothing"
    )
    assert 19000 * 19000 > MAX_PIXELS

    started = time.monotonic()
    result = verify_and_reencode(bomb)
    elapsed = time.monotonic() - started

    assert isinstance(result, Err)
    assert "dimensions" in result.error.message
    # Reading a PNG header is microseconds; decoding 360 megapixels is not.
    assert elapsed < 1.0, f"took {elapsed:.2f}s — that is a decode, not a header read"


# --- Control 2: magic bytes ------------------------------------------------


def test_a_php_file_renamed_png_is_refused_by_its_contents() -> None:
    """Extension and `Content-Type` are attacker-supplied, so neither is
    consulted anywhere in the pipeline — this is the whole test: the bytes are
    what decide, and these bytes are not an image."""
    result = verify_and_reencode(b"<?php system($_GET['c']); ?>" + b"\x00" * 64)
    assert isinstance(result, Err)
    assert "not an image" in result.error.message


def test_an_empty_file_is_refused_with_its_own_sentence() -> None:
    result = verify_and_reencode(b"")
    assert isinstance(result, Err)
    assert "empty" in result.error.message


# --- Control 3: re-encode strips EXIF and kills polyglots ------------------


def test_exif_is_present_before_and_absent_after() -> None:
    """The re-encode is what strips it, and the canary proves the strip rather
    than the absence of a field nobody set: a phone camera's EXIF carries GPS
    coordinates, which is the actual privacy stake."""
    raw = _jpeg_with_exif()
    assert b"CanaryCam" in raw

    result = verify_and_reencode(raw)
    assert isinstance(result, Ok)
    assert b"CanaryCam" not in result.value.body
    with Image.open(io.BytesIO(result.value.body)) as reencoded:
        assert not dict(reencoded.getexif())


def test_a_gif_polyglot_is_normalized_to_a_known_format() -> None:
    """A file that is a valid GIF *and* a valid HTML document stops being one
    the moment it is written out from pixels."""
    buffer = io.BytesIO()
    Image.new("P", (4, 4)).save(buffer, format="GIF")
    polyglot = buffer.getvalue() + b"<script>alert(1)</script>"

    result = verify_and_reencode(polyglot)
    assert isinstance(result, Ok)
    assert b"<script>" not in result.value.body
    assert result.value.content_type == "image/png"


# --- Control 4: server-generated UUID storage keys -------------------------


def test_the_storage_key_is_a_server_uuid_under_one_prefix() -> None:
    """A user filename never reaches a path because it is never read at all.
    The key is generated here, from nothing the request supplied."""
    first = verify_and_reencode(_png())
    second = verify_and_reencode(_png())
    assert isinstance(first, Ok) and isinstance(second, Ok)
    assert first.value.storage_key.startswith("assets/")
    assert first.value.storage_key != second.value.storage_key
    assert ".." not in first.value.storage_key


def test_a_path_traversal_filename_has_nowhere_to_appear() -> None:
    """Structural, not behavioural: `verify_and_reencode` takes bytes and no
    filename, so there is no parameter for `../../etc/passwd` to arrive in."""
    import inspect

    assert list(inspect.signature(verify_and_reencode).parameters) == ["raw"]


# --- Controls 5 and 6: server-set content type, one prefix -----------------


@pytest.mark.parametrize(
    ("source_format", "expected"),
    [
        ("PNG", "image/png"),
        ("JPEG", "image/jpeg"),
        ("WEBP", "image/png"),
        ("GIF", "image/png"),
    ],
)
def test_the_content_type_is_the_servers_own(source_format: str, expected: str) -> None:
    """Never echoed from the request. Everything normalizes to PNG or JPEG, so
    an image cannot be served as anything a browser might sniff as markup."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(buffer, format=source_format)
    result = verify_and_reencode(buffer.getvalue())
    assert isinstance(result, Ok)
    assert result.value.content_type == expected


# --- SVG: sanitized, and served via <img> ----------------------------------


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        (
            "script",
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script><rect/></svg>",
        ),
        (
            "onload",
            b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'><rect onclick='alert(2)'/></svg>",
        ),
        (
            "foreignObject",
            b"<svg xmlns='http://www.w3.org/2000/svg'><foreignObject><div xmlns='http://www.w3.org/1999/xhtml'>x</div></foreignObject><rect/></svg>",
        ),
        (
            "remote use",
            b"<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'><use xlink:href='https://evil.example/x#a'/></svg>",
        ),
        (
            "external url()",
            b"<svg xmlns='http://www.w3.org/2000/svg'><rect fill='url(https://evil.example/x)'/></svg>",
        ),
    ],
)
def test_svg_xss_payloads_do_not_survive(name: str, payload: bytes) -> None:
    result = sanitize_svg(payload)
    assert isinstance(result, Ok), f"{name} should sanitize, not refuse"
    out = result.value.lower()
    for forbidden in (
        b"script",
        b"onload",
        b"onclick",
        b"foreignobject",
        b"evil.example",
    ):
        assert forbidden not in out, f"{name} left {forbidden!r} behind"


def test_an_entity_expansion_bomb_is_refused_in_the_parser() -> None:
    """Billion laughs. A denial-of-service shape, distinct from the XSS case,
    and an allowlist does nothing about it — the expansion happens before any
    element exists to inspect. `defusedxml` refuses the declaration itself."""
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE svg ['
        b'<!ENTITY a "aaaaaaaaaa">'
        b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
        b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
        b'<!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">'
        b']><svg xmlns="http://www.w3.org/2000/svg"><desc>&d;</desc></svg>'
    )
    started = time.monotonic()
    result = sanitize_svg(bomb)
    elapsed = time.monotonic() - started
    assert isinstance(result, Err)
    assert "entities" in result.error.message
    assert elapsed < 1.0, f"took {elapsed:.2f}s — expansion happened"


def test_pathological_nesting_is_refused_without_a_cpu_spike() -> None:
    nested = (
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        + b"<g>" * 500
        + b"</g>" * 500
        + b"</svg>"
    )
    started = time.monotonic()
    result = sanitize_svg(nested)
    elapsed = time.monotonic() - started
    assert isinstance(result, Err)
    assert "nested too deeply" in result.error.message
    assert elapsed < 1.0


def test_a_real_logo_survives_intact() -> None:
    """The controls have to let the common case through. Refusing every SVG
    would pass every test above and be useless — logos are almost always SVG."""
    logo = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        b'<path d="M12 2L2 22h20z" fill="#ff0000"/></svg>'
    )
    result = verify_and_reencode(logo)
    assert isinstance(result, Ok)
    assert result.value.content_type == SVG_MIME
    assert b"M12 2L2 22h20z" in result.value.body
    assert b'fill="#ff0000"' in result.value.body


def test_an_svg_is_not_re_encoded_and_has_no_dimensions() -> None:
    result = verify_and_reencode(
        b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="4" height="4"/></svg>'
    )
    assert isinstance(result, Ok)
    assert result.value.width is None and result.value.height is None


# --- The refusals are six answers, not one -------------------------------


def test_every_refusal_says_something_different() -> None:
    """ "A rejected upload is a user holding their own logo, being told no by a
    product that has just claimed it will keep them on brand" — so "Invalid
    file" is not an answer to any of the six questions."""
    messages = {
        verify_and_reencode(b"").error.message,  # type: ignore[union-attr]
        verify_and_reencode(b"x" * (MAX_BYTES + 1)).error.message,  # type: ignore[union-attr]
        verify_and_reencode(b"<?php ?>" + b"\x00" * 64).error.message,  # type: ignore[union-attr]
        sanitize_svg(
            b"<svg xmlns='http://www.w3.org/2000/svg'>" + b"<g>" * 500
        ).error.message,  # type: ignore[union-attr]
    }
    assert len(messages) == 4
    for message in messages:
        assert "invalid file" not in message.lower()
        # No internal error class ever reaches the user
        # (docs/security/operations.md).
        for leaked in ("Error", "Exception", "Traceback", "PIL", "defusedxml"):
            assert leaked not in message

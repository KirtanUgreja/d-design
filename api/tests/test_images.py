"""Slide imagery, offline: a fake image model's bytes become our own webp in
the slide (tests/test_studio.py); a failure leaves no empty slot; bytes
never reach a prompt."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

from PIL import Image

from engine import Seam
from engine.components import images
from engine.design.sampler import look_for
from engine.design.theme import build
from engine.studio import build as studio
from tests.fakes import Studio, _no_sleep
from tests.test_studio import _story


def test_a_failed_image_leaves_no_empty_slot(tmp_path: Path) -> None:
    theme = build(look_for("img-test", words="a pitch", language="editorial"))
    transport = Studio(no_picture=True)
    built = asyncio.run(
        studio.build(
            Seam(api_key="k", transport=transport, sleep=_no_sleep),
            _story(3),
            theme,
            model="m",
            title="A pitch",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            image_model="img",
        )
    )
    assert transport.calls.count("image") == 1
    assert all("<img" not in s.html for s in built.slides)
    assert all(s.qa.status == "passed" for s in built.slides)


def test_treat_refuses_what_is_not_an_image() -> None:
    assert images.treat(b"not an image", "3:2").__class__.__name__ == "Err"
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, "GIF")
    assert images.treat(gif.getvalue(), "3:2").__class__.__name__ == "Err"


def test_strip_keeps_bytes_out_of_prompts() -> None:
    html = '<dd-image aspect="1:1"></dd-image>'
    filled = images.fill(html, images.data_url(b"abc"))
    assert "<img" in filled
    assert images.strip(filled) == html
    assert images.fill(html, "https://evil.example/x.png") == html

"""Slide imagery, offline (phase 39 -> Verify): a fake image model's bytes
become our own webp in the slide; a failure leaves a quiet field; the export
stays offline; the image's cost is in the ledger."""

from __future__ import annotations

import asyncio
import base64
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest
from PIL import Image

from engine import Seam, Storyline, pipeline
from engine.components import images
from engine.compose import references
from engine.compose.references import Reference
from engine.design.sampler import look_for
from engine.design.theme import build
from tests.test_ladder import _no_sleep
from tests.test_references import _story

THEME = build(look_for("img-test", words="a pitch", language="editorial"))
REF = Reference(
    id="editorial/cover-9",
    language="editorial",
    shape="cover",
    idea="half-bleed picture, title on the ground",
    fields=frozenset({"kicker", "headline", "source"}),
    image="half",
    variants=(),
    html=(
        '<section class="s"><dd-image aspect="2:3" class="pic"></dd-image><div class="t">'
        '<p class="k" data-field="kicker"></p><h1 class="h" data-field="headline"></h1>'
        '<p class="src" data-field="source"></p></div></section>'
    ),
    css=(
        ".s{display:grid;grid-template-columns:1fr 1fr}.pic{height:1080px}"
        ".t{padding:var(--margin);display:grid;align-content:end;gap:var(--s-3)}"
        ".k,.src{font-family:var(--f-label);font-size:var(--t-label)}"
        ".h{font-family:var(--f-display);font-size:var(--t-h2);line-height:1.05}"
    ),
)


def _png(w: int = 900, h: int = 600) -> bytes:
    out = io.BytesIO()
    image = Image.new("RGB", (w, h), (40, 90, 120))
    image.save(out, "PNG", pnginfo=None)
    return out.getvalue()


@dataclass
class Painter:
    """Compose answers are unusable (so the reference is filled by code);
    image calls answer with a PNG, or fail when ``broken``."""

    broken: bool = False
    image_calls: int = 0
    prompts: list[str] = field(default_factory=list)

    async def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        assert isinstance(json, dict)
        usage = {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.002}
        if json.get("modalities") == ["image", "text"]:
            self.image_calls += 1
            self.prompts.append(str(json["messages"][0]["content"]))
            if self.broken:
                return httpx.Response(200, json={"choices": [{"message": {"content": "no"}}]})
            data = base64.b64encode(_png()).decode()
            message = {
                "content": "",
                "images": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}
                ],
            }
            return httpx.Response(200, json={"choices": [{"message": message}], "usage": usage})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "nothing"}}], "usage": usage}
        )


@pytest.fixture
def library(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(references, "load_all", lambda root=None: (REF,))
    monkeypatch.setattr(references, "kept", lambda root=None: frozenset({REF.id}))


def _build(tmp_path: Path, painter: Painter, story: Storyline) -> pipeline.Built:
    return asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=painter, sleep=_no_sleep),
            story,
            THEME,
            model="m",
            title="A pitch",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            image_model="img",
        )
    )


def test_a_generated_image_lands_in_its_slot_as_our_webp(tmp_path: Path, library: None) -> None:
    painter = Painter()
    seam_story = _story(1)
    built = _build(tmp_path, painter, seam_story)
    cover = built.slides[0]
    assert painter.image_calls == 1
    assert cover.qa.status == "passed"
    m = re.search(r'<img src="data:image/webp;base64,([^"]+)"', cover.html)
    assert m is not None
    with Image.open(io.BytesIO(base64.b64decode(m.group(1)))) as got:
        assert got.format == "WEBP"
        assert abs(got.width / got.height - 2 / 3) < 0.02  # cropped to the slot
        assert not got.info.get("exif")
    assert "Absolutely no text anywhere" in painter.prompts[0]
    # embedded in the export: no request needed to show it
    assert "data:image/webp;base64," in built.html
    assert not re.search(r'src="https?:', built.html)


def test_a_failed_image_leaves_a_quiet_field(tmp_path: Path, library: None) -> None:
    built = _build(tmp_path, Painter(broken=True), _story(1))
    cover = built.slides[0]
    assert cover.qa.status == "passed"
    assert "<dd-image" in cover.html and "<img" not in cover.html


def test_images_are_off_without_an_image_model(tmp_path: Path, library: None) -> None:
    painter = Painter()
    built = asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=painter, sleep=_no_sleep),
            _story(1),
            THEME,
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
        )
    )
    assert painter.image_calls == 0
    assert "<dd-image" not in built.slides[0].html  # the slot is taken out, not left empty


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

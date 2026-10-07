"""Measure every vendored face in Chromium and write its meta.json
(docs/v4/design-engine.md -> Registry: x-height, width class and weights).

Run after scripts/vendor_fonts.py. Ratios are per em at the face's weight:
`leading` is cap height plus descender rounded up, the tightest line-height
before a descender meets the capital below.
"""

from __future__ import annotations

import base64
import json
import math
from pathlib import Path

from playwright.async_api import async_playwright

FONTS = Path(__file__).resolve().parent.parent / "library" / "fonts"

_MEASURE = """async ([family, weight]) => {
  const f = `${weight} 200px '${family}'`;
  await document.fonts.load(f);
  if (!document.fonts.check(f)) return null;
  const c = document.createElement('canvas').getContext('2d'); c.font = f;
  const m = (s) => c.measureText(s);
  const text = 'the quick brown fox jumps over the lazy dog';
  return {
    x_height: m('x').actualBoundingBoxAscent / 200,
    cap: m('HTKMB').actualBoundingBoxAscent / 200,
    descender: m('gjpqy').actualBoundingBoxDescent / 200,
    width: m(text).width / 200 / text.length,
  };
}"""


def _sampled(lic: dict[str, object]) -> list[int]:
    """Weights to measure: a variable face every 100 across its range (the
    engine interpolates between them), a static face at each file it has."""
    axes = lic.get("axes")
    if isinstance(axes, dict) and "wght" in axes:
        lo, hi = axes["wght"]
        return list(range(math.ceil(lo / 100) * 100, int(hi) + 1, 100))
    weights = lic.get("weights")
    return [int(w) for w in weights] if isinstance(weights, list) else []


async def measure() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    folders = sorted(p for p in FONTS.iterdir() if (p / "licence.json").exists())
    faces = []
    for folder in folders:
        lic = json.loads((folder / "licence.json").read_text())
        if "axes" in lic:  # one variable file, declared over its weight range
            lo, hi = lic["axes"].get("wght", [400, 400])
            data = base64.b64encode((folder / "variable.woff2").read_bytes()).decode()
            faces.append(
                f"@font-face{{font-family:'{lic['family']}';font-weight:{lo:g} {hi:g};"
                f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
            )
            continue
        for w in lic["weights"]:
            data = base64.b64encode((folder / f"{w}.woff2").read_bytes()).decode()
            faces.append(
                f"@font-face{{font-family:'{lic['family']}';font-weight:{w};"
                f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
            )
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(f"<style>{''.join(faces)}</style>")
        for folder in folders:
            lic = json.loads((folder / "licence.json").read_text())
            metrics: dict[str, object] = {}
            for w in _sampled(lic):
                m = await page.evaluate(_MEASURE, [lic["family"], w])
                if m is None:
                    raise RuntimeError(f"{lic['family']} {w} did not load")
                m = {k: round(v, 3) for k, v in m.items()}
                m["leading"] = math.ceil((m["cap"] + m["descender"]) * 100) / 100
                metrics[str(w)] = m
            meta = {**lic, "metrics": metrics}
            (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
            out[lic["family"]] = meta
        await browser.close()
    return out

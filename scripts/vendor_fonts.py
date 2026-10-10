"""Vendor OFL font families into api/library/fonts/ (docs/v4/design-engine.md -> Registry).

For each family: the Latin-subset woff2 per weight, from the Google Fonts CSS API,
and the family's own OFL.txt from github.com/google/fonts. The licence is checked
from that file — "it is on Google Fonts" is not a licence check — and a Reserved
Font Name is recorded. Measuring the faces (meta.json) is a second step:
`cd api && uv run python -m cli fonts`.

    python3 scripts/vendor_fonts.py            # fetch what is missing
    python3 scripts/vendor_fonts.py --force    # fetch everything again

Stdlib only; run by hand when the registry changes, never at build time.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

FONTS = Path(__file__).resolve().parent.parent / "api" / "library" / "fonts"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"

# family -> (role, weights). Role is a hint for pairing, not a rule.
FAMILIES: dict[str, tuple[str, tuple[int, ...]]] = {
    # already vendored in phase 22
    "Anton": ("condensed", (400,)),
    "Archivo": ("grotesk", (800, 900)),
    "Fraunces": ("serif-display", (400, 700)),
    "Hanken Grotesk": ("sans", (400, 600)),
    "IBM Plex Mono": ("mono", (400, 500)),
    "IBM Plex Sans": ("sans", (400, 600)),
    "Instrument Serif": ("serif-display", (400,)),
    "Schibsted Grotesk": ("sans", (400, 600)),
    # condensed and poster
    "Big Shoulders Display": ("condensed", (800, 900)),
    "Barlow Condensed": ("condensed", (700, 800)),
    "League Gothic": ("condensed", (400,)),
    # didone and serif display
    "Bodoni Moda": ("didone", (500, 800)),
    "DM Serif Display": ("serif-display", (400,)),
    "Young Serif": ("serif-display", (400,)),
    "Gloock": ("serif-display", (400,)),
    # slab
    "Zilla Slab": ("slab", (400, 700)),
    "Alfa Slab One": ("slab", (400,)),
    # grotesk display
    "Bricolage Grotesque": ("grotesk", (500, 800)),
    "Syne": ("grotesk", (700, 800)),
    "Unbounded": ("wide", (500, 800)),
    "Familjen Grotesk": ("grotesk", (500, 700)),
    # text sans
    "Public Sans": ("sans", (400, 600)),
    "Libre Franklin": ("sans", (400, 600)),
    "Work Sans": ("sans", (400, 600)),
    "Karla": ("sans", (400, 600)),
    "Figtree": ("sans", (400, 600)),
    # text serif
    "Newsreader": ("serif", (400, 600)),
    "Source Serif 4": ("serif", (400, 600)),
    "Literata": ("serif", (400, 600)),
    "EB Garamond": ("serif", (400, 600)),
    # mono
    "Space Mono": ("mono", (400, 700)),
    "DM Mono": ("mono", (400, 500)),
    "JetBrains Mono": ("mono", (400, 600)),
}


# Display families vendored as ONE variable file instead of static weights
# (phase 36): each deck draws its own instance. Axis ranges as Google Fonts
# serves them; opsz follows the size automatically (font-optical-sizing).
VARIABLE: dict[str, dict[str, tuple[float, float]]] = {
    "Big Shoulders Display": {"wght": (100, 900)},
    "League Gothic": {"wdth": (75, 100)},
    "Archivo": {"wdth": (62, 125), "wght": (100, 900)},
    "Bricolage Grotesque": {"opsz": (12, 96), "wdth": (75, 100), "wght": (200, 800)},
    "Familjen Grotesk": {"wght": (400, 700)},
    "Syne": {"wght": (400, 800)},
    "Unbounded": {"wght": (200, 900)},
    "Fraunces": {"opsz": (9, 144), "wght": (100, 900), "SOFT": (0, 100), "WONK": (0, 1)},
    "Bodoni Moda": {"opsz": (6, 96), "wght": (400, 900)},
    "Newsreader": {"opsz": (6, 72), "wght": (200, 800)},
    "EB Garamond": {"wght": (400, 800)},
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310 - fixed https hosts
        data: bytes = response.read()
        return data


def folder(family: str) -> str:
    return family.lower().replace(" ", "-")


def latin_woff2(family: str, weight: int) -> str:
    css = get(
        f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}"
        "&display=block"
    ).decode()
    # Each subset is a block preceded by a comment naming it; keep "latin" only.
    for name, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face\s*{[^}]*})", css):
        if name == "latin":
            m = re.search(r"url\((https://[^)]+\.woff2)\)", block)
            if m:
                return m.group(1)
    raise RuntimeError(f"no latin woff2 for {family} {weight}")


def latin_variable(family: str, axes: dict[str, tuple[float, float]]) -> str:
    # Google wants the axis tags lowercase first, then alphabetical.
    tags = sorted(axes, key=lambda t: (t.isupper(), t))
    spec = ",".join(tags) + "@" + ",".join(f"{axes[t][0]:g}..{axes[t][1]:g}" for t in tags)
    css = get(
        f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:{spec}"
        "&display=block"
    ).decode()
    for name, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face\s*{[^}]*})", css):
        if name == "latin":
            m = re.search(r"url\((https://[^)]+\.woff2)\)", block)
            if m:
                return m.group(1)
    raise RuntimeError(f"no latin variable woff2 for {family}")


def licence(family: str) -> tuple[str, str | None]:
    slug = family.lower().replace(" ", "")
    text = get(f"https://raw.githubusercontent.com/google/fonts/main/ofl/{slug}/OFL.txt").decode()
    if "SIL Open Font License" not in text:
        raise RuntimeError(f"{family}: OFL.txt does not carry the SIL Open Font License")
    # Only the copyright lines declare one; line 33 of every OFL defines the term.
    rfn = re.search(r"with Reserved Font Names? [\"'“]([^\"'”]+)[\"'”]", text.split("PREAMBLE")[0])
    return text, rfn.group(1).strip() if rfn else None


def main(force: bool) -> int:
    report: dict[str, object] = {}
    for family, (role, weights) in FAMILIES.items():
        out = FONTS / folder(family)
        axes = VARIABLE.get(family)
        if axes:
            missing = [] if not force and (out / "variable.woff2").exists() else [0]
        else:
            missing = [w for w in weights if force or not (out / f"{w}.woff2").exists()]
        if not missing and (out / "licence.json").exists():
            continue
        out.mkdir(parents=True, exist_ok=True)
        text, rfn = licence(family)
        (out / "OFL.txt").write_text(text)
        if axes:
            (out / "variable.woff2").write_bytes(get(latin_variable(family, axes)))
            for static in out.glob("[0-9]*.woff2"):
                static.unlink()  # one variable file replaces the static weights
        else:
            for weight in missing:
                (out / f"{weight}.woff2").write_bytes(get(latin_woff2(family, weight)))
        record: dict[str, object] = {
            "family": family, "role": role, "weights": list(weights), "licence": "OFL-1.1",
            "reserved_font_name": rfn, "source": "fonts.googleapis.com (latin subset)",
        }
        if axes:
            record["axes"] = {t: list(r) for t, r in axes.items()}
        (out / "licence.json").write_text(json.dumps(record, indent=2) + "\n")
        report[family] = {"weights": weights, "rfn": rfn}
        print(f"{family}: {list(weights)}  RFN={rfn}", flush=True)
    print(f"{len(report)} families fetched; {len(FAMILIES)} in the registry")
    return 0


if __name__ == "__main__":
    sys.exit(main("--force" in sys.argv))

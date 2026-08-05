"""Tier-0 tools: pure reads of the user's own approved data, no state, no
network, no consequence (docs/techstack/pipeline-tools.md). Plain Python
functions the Build orchestration calls directly — not routed through the
model as callable tools, because every one of these is needed on every scene
call rather than conditionally, so there is nothing for the model to decide.
ponytail: wire real tool-calling (see api/ai/complete.py's docstring) if a
future tool is only sometimes relevant rather than always-needed context.
"""

from schema.experience import BrandKit
from schema.scene import LAYOUT_REGIONS

# scene-schema.md's own caps table, restated as prompt text. Prompting is the
# only portable lever on output length (docs/v1/ai-pipeline.md) — structured-
# output enforcement of minLength/maxLength is widely unsupported regardless
# of route, so this has to exist as words, not only as a Pydantic Field. It
# is a copy for the model to read, never a second place validation runs from
# — schema/scene.py's Field(max_length=...) is what actually rejects.
_CHARACTER_CAPS = """Character caps, hard limits:
- Eyebrow: 24
- Headline: 60
- Body: 240
- Quote: 200 (attribution/role: 60 each)
- List item: 80 (detail: 120), 2-5 items
- Stat value: 12, label: 40, prefix/suffix: 8 each
- Image alt: 160
- CTA label: 32"""


def get_brand_kit(brand_id: str | None) -> BrandKit | None:
    """ponytail: brand kit storage is phase 10 (brand + uploads) — there is
    no `brands` row to fetch yet regardless of what `brand_id` names.
    Returns `None`, and the build prompt omits brand-color guidance when it
    does; a null brand is exactly what `resolveBrand` already falls back to
    on the render side (web/src/features/art-direction/resolve-brand.ts),
    so Build and the renderer agree about what "no brand" means."""
    return None


def list_assets() -> list[dict[str, str]]:
    """ponytail: uploads are phase 10 — there is no `assets` table yet, so
    this always returns empty. The build prompt states plainly that no
    assets exist, so the model reaches for `AbstractVisual` instead of
    inventing an `assetId` that `assert_assets_resolve` would reject."""
    return []


def get_constraints() -> str:
    """Character budgets and valid layout regions, as text — stable across
    every scene in a build, so it belongs in the cached system prefix rather
    than being re-fetched per call."""
    regions = "\n".join(
        f"- {layout}: {', '.join(sorted(cells))}"
        for layout, cells in sorted(LAYOUT_REGIONS.items())
    )
    return f"{_CHARACTER_CAPS}\n\nLayouts and their valid regions:\n{regions}"

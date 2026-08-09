"""Tier-0 tools: pure reads of the user's own approved data, no state, no
network, no consequence (docs/techstack/pipeline-tools.md). Plain Python
functions the Build orchestration calls directly — not routed through the
model as callable tools, because every one of these is needed on every scene
call rather than conditionally, so there is nothing for the model to decide.
ponytail: wire real tool-calling (see api/ai/complete.py's docstring) if a
future tool is only sometimes relevant rather than always-needed context.
"""

import features.assets as assets_feature
import features.brand as brand_feature
from db.tenant import as_user
from schema.experience import BrandKit
from schema.scene import LAYOUT_REGIONS

# Each tool opens its own `as_user` session rather than taking one, and that
# is rule 8 rather than a preference: SQLAlchemy belongs in a `*_data.py`
# module and nowhere else, so this file cannot name an `AsyncSession` even in a
# type annotation (`scripts/checks/invariants.sh` greps for exactly that, and
# caught it). Two short sessions instead of one shared one is the cost, and it
# buys a tool that is callable from anywhere with an owner id — which is what a
# tier-0 read should be.


async def get_brand_kit(owner_id: str) -> BrandKit | None:
    """The owner's brand kit, or `None` if they have not set one.

    Scoped by the RLS policy, never by a filter here (rule 9). A null brand is
    exactly what `resolveBrand` falls back to on the render side
    (web/src/features/art-direction/resolve-brand.ts), so Build and the
    renderer agree about what "no brand" means.
    """
    async with as_user(owner_id) as session:
        return await brand_feature.load_brand(session)


async def list_assets(owner_id: str) -> list[dict[str, str]]:
    """The owner's assets, as the id/description pairs the prompt names.

    Only the id and a description cross into the prompt — not the storage key,
    not the mime type. The model's one job with an asset is to reference it by
    id, and everything else would be context it cannot use and could leak.
    """
    async with as_user(owner_id) as session:
        assets = await assets_feature.list_assets(session)
    return [
        {"id": asset.id, "description": asset.alt or f"{asset.kind} asset"}
        for asset in assets
    ]


def get_constraints() -> str:
    """The valid layout regions, as text — stable across every scene in a
    build, so it belongs in the cached system prefix rather than being
    re-fetched per call.

    **No character caps here any more.** They used to be restated in this file
    as a hand-maintained table, and `prompts/build.py`'s `_limits_section` now
    derives the same numbers from the Pydantic models — so the prompt carried
    both, and the hand-written copy was the one that could drift. Deleting it
    is the fix; a second copy of a constraint is the bug, not the redundancy.
    """
    regions = "\n".join(
        f"- {layout}: {', '.join(sorted(cells))}"
        for layout, cells in sorted(LAYOUT_REGIONS.items())
    )
    return f"Layouts and their valid regions:\n{regions}"

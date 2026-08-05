"""Post-build checks — the layer that actually catches things
(docs/v1/plan/06-model-seam-and-build.md). All three run on every generated
scene before it is stored or streamed to the client. The schema parse
already happened, inside the seam; these are the whole-tree and cross-field
rules a `model_validate` alone cannot express.
"""

from lib.result import Err, Result, ok
from schema.brief import Brief
from schema.experience import assert_hrefs_are_supplied, assert_stats_are_supported
from schema.no_style import assert_no_presentational_values
from schema.scene import Scene


def check_scene(scene: Scene, brief: Brief) -> Result[None]:
    """No presentational values, `CTA.href` provenance, claim provenance —
    in that order, so the cheapest and most-likely-to-fire check runs
    first."""
    no_style = assert_no_presentational_values(scene.model_dump(by_alias=True))
    if isinstance(no_style, Err):
        return no_style

    # The Brief's `cta.href` is the only URL v1 ever supplies — the AI
    # arranges it, it never composes one (docs/v1/ai-pipeline.md -> "The URL
    # rule"). `assets` carry no href, so there is nothing else to include.
    supplied_hrefs = frozenset({brief.cta.href})
    hrefs = assert_hrefs_are_supplied([scene], supplied_hrefs)
    if isinstance(hrefs, Err):
        return hrefs

    proof_points = frozenset(brief.proof_points)
    stats = assert_stats_are_supported([scene], proof_points)
    if isinstance(stats, Err):
        return stats

    return ok(None)

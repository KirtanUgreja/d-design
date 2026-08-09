"""AbstractVisual seeds, derived rather than invented
(docs/v1/plan/11-visuals-and-slot.md -> "Seed derives from the scene id").

The model picks `seed` today, and it has no basis for picking one — it is a
number with no meaning to anything except a PRNG, so what comes back is
arbitrary and differs on every call. The consequence is the bug the phase doc
names: *a regenerated scene must not look different for no reason*. Rebuild the
same scene and the background changed, and nobody can explain why.

Deriving it from the scene id fixes that at the source. Same scene, same
visual, forever — and reroll stays what it should be, an explicit user action
(the editor's `reroll` control writes a fresh number, which is the one thing
that should change a visual).

FNV-1a, matching `web/src/features/renderer/blocks/visual-seed.ts` byte for
byte. Two implementations of one hash is a duplication with a real reason —
the client needs it offline for reroll and the server needs it during a build,
and the alternative is a round trip for a number. `tests/test_visual_seed.py`
pins them together with shared fixtures, so a change to one that is not
mirrored in the other fails rather than drifting.
"""

from schema.scene import Scene

_FNV_OFFSET = 0x811C9DC5
_FNV_PRIME = 0x01000193
_MASK = 0xFFFFFFFF

# The schema's own `seed` bound. A derived seed is always a value `Scene` would
# accept, so this can never be the thing that makes a scene invalid.
_MAX_SEED = 2147483647


def seed_from_id(scene_id: str) -> int:
    hash_ = _FNV_OFFSET
    for byte in scene_id.encode("utf-8"):
        hash_ ^= byte
        hash_ = (hash_ * _FNV_PRIME) & _MASK
    return hash_ % _MAX_SEED


def with_derived_seeds(scene: Scene) -> Scene:
    """Every `abstract-visual` block's seed, replaced by one derived from the
    scene id.

    A copy, not a mutation: `Scene` is validated data by the time it reaches
    here, and rewriting it in place would mean the object the checks ran
    against is not the object that gets stored.

    Deliberately *not* a `model_validator` on `Scene`. A validator would fire
    on every parse — including when the editor reloads a stored experience —
    and would silently overwrite a seed the user set with the reroll button.
    This runs once, on the build path, which is the only place a seed is being
    invented rather than remembered.
    """
    if not any(b.props.type == "abstract-visual" for b in scene.blocks):
        return scene

    seed = seed_from_id(scene.id)
    blocks = [
        b.model_copy(update={"props": b.props.model_copy(update={"seed": seed})})
        if b.props.type == "abstract-visual"
        else b
        for b in scene.blocks
    ]
    return scene.model_copy(update={"blocks": blocks})

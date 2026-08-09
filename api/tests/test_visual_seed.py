"""The two implementations of one hash, pinned together.

`seed_from_id` exists in Python (`features/generation/visuals.py`) and in
TypeScript (`web/src/features/renderer/blocks/visual-seed.ts`) because the
server derives a seed during a build and the editor derives one for reroll,
and the alternative to a second implementation is a network round trip for a
number.

Two implementations of one algorithm is a duplication, and the honest way to
carry one is to make drift fail rather than to hope. These fixtures are
asserted on both sides — `web/src/features/renderer/renderer.test.ts` holds the
same table — so changing either implementation without the other turns red.
"""

from features.generation.visuals import seed_from_id, with_derived_seeds
from schema.scene import AbstractVisualProps, Scene

# Shared with the TypeScript test. Do not edit one copy.
# The last two are not decoration. Python hashes `.encode("utf-8")` bytes and
# the obvious TypeScript loop walks UTF-16 code units masked to a byte — the
# two agree on ASCII and silently disagree on everything else. A scene id is
# model-generated, and this codebase has already watched a model emit CJK into
# a text field, so a non-ASCII fixture is the one that actually tests the pair.
# It caught exactly that divergence when this file was written.
FIXTURES = {
    "scene-1": 860226354,
    "scene-1-hook": 342120084,
    "s1": 139573449,
    "": 18652614,
    "a-much-longer-scene-identifier-than-usual": 1412726095,
    "🎬": 1406619490,
    "scène-é": 1341928168,
}


def test_the_hash_matches_its_typescript_twin() -> None:
    for scene_id, expected in FIXTURES.items():
        assert seed_from_id(scene_id) == expected, scene_id


def test_a_derived_seed_is_always_in_the_schemas_range() -> None:
    """So deriving a seed can never be the thing that makes a scene invalid."""
    for scene_id in [*FIXTURES, "x" * 200, "\x00"]:
        assert 0 <= seed_from_id(scene_id) <= 2147483647


def _scene(scene_id: str, seed: int) -> Scene:
    return Scene.model_validate(
        {
            "id": scene_id,
            "intent": "hook",
            "layout": "full-bleed",
            "blocks": [
                {
                    "id": "b1",
                    "region": "content",
                    "props": {"type": "headline", "text": "Hello"},
                },
                {
                    "id": "b2",
                    "region": "bg",
                    "props": {
                        "type": "abstract-visual",
                        "generator": "hatch-drift",
                        "intensity": "medium",
                        "seed": seed,
                    },
                },
            ],
        }
    )


def _visual_seed(scene: Scene) -> int:
    """The seed on the scene's one abstract-visual block. Narrowed rather than
    indexed, because `props` is a union and only one member has a `seed`."""
    props = scene.blocks[1].props
    assert isinstance(props, AbstractVisualProps)
    return props.seed


def test_the_same_scene_id_produces_the_same_visual_whatever_the_model_said() -> None:
    """The bug this exists to stop: rebuild the same scene and the background
    changed for no reason anyone can explain. The model picks `seed` today and
    has no basis for picking one, so two builds of one scene disagree."""
    first = with_derived_seeds(_scene("scene-1", seed=11))
    second = with_derived_seeds(_scene("scene-1", seed=999_999))
    assert _visual_seed(first) == _visual_seed(second)


def test_different_scenes_still_look_different() -> None:
    a = with_derived_seeds(_scene("scene-1", seed=1))
    b = with_derived_seeds(_scene("scene-2", seed=1))
    assert _visual_seed(a) != _visual_seed(b)


def test_nothing_else_about_the_scene_is_touched() -> None:
    original = _scene("scene-1", seed=1)
    derived = with_derived_seeds(original)
    assert derived.blocks[0] == original.blocks[0]
    assert derived.id == original.id and derived.layout == original.layout
    # A copy, not a mutation: the object the post-build checks ran against has
    # to stay the object they ran against.
    assert _visual_seed(original) == 1


def test_a_scene_with_no_visual_is_returned_unchanged() -> None:
    scene = Scene.model_validate(
        {
            "id": "s",
            "intent": "hook",
            "layout": "centered",
            "blocks": [{"id": "b1", "props": {"type": "headline", "text": "Hi"}}],
        }
    )
    assert with_derived_seeds(scene) is scene

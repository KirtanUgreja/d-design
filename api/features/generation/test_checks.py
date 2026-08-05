"""check_scene runs the three post-build checks in order — no presentational
values, CTA.href provenance, Stat provenance (docs/v1/plan/06-model-seam-and-build.md).
Pure functions, no DB, no model call."""

from features.generation.checks import check_scene
from lib.result import Err, Ok
from schema.brief import Brief, BriefCta
from schema.scene import Block, CtaProps, HeadlineProps, Scene, StatProps

BRIEF = Brief(
    goal="Launch the new product",
    audience="Existing customers",
    key_messages=["Faster", "Cheaper", "Safer"],
    proof_points=["we cut latency to under 50ms"],
    tone="confident",
    cta=BriefCta(label="Get started", href="https://example.com/start"),
)


def _scene(*blocks: Block) -> Scene:
    return Scene(id="scene-1", intent="hook", layout="centered", blocks=list(blocks))


def test_valid_scene_passes() -> None:
    scene = _scene(
        Block(id="b1", props=HeadlineProps(type="headline", text="Faster")),
        Block(id="b2", props=StatProps(type="stat", value="50ms", label="latency")),
        Block(
            id="b3",
            props=CtaProps(
                type="cta", label="Get started", style="primary", href=BRIEF.cta.href
            ),
        ),
    )
    result = check_scene(scene, BRIEF)
    assert isinstance(result, Ok)


def test_presentational_value_rejected() -> None:
    scene = _scene(
        Block(id="b1", props=HeadlineProps(type="headline", text="Use 16px text"))
    )
    result = check_scene(scene, BRIEF)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


def test_invented_href_rejected() -> None:
    scene = _scene(
        Block(
            id="b1",
            props=CtaProps(
                type="cta",
                label="Get started",
                style="primary",
                href="https://evil.example.com/",
            ),
        )
    )
    result = check_scene(scene, BRIEF)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


def test_invented_stat_rejected() -> None:
    scene = _scene(
        Block(id="b1", props=StatProps(type="stat", value="99x", label="growth"))
    )
    result = check_scene(scene, BRIEF)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"

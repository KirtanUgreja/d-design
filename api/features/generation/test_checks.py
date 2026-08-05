"""check_scene runs the four post-build checks in order — no presentational
values, CTA.href provenance, Stat provenance, no prompt leak
(docs/v1/plan/06-model-seam-and-build.md). Pure functions, no DB, no model
call."""

from features.generation.checks import check_scene
from features.generation.prompts.build import _PROMPT_CONTRACT, PROMPT_SENTINELS
from lib.result import Err, Ok
from schema.brief import Brief, BriefCta
from schema.scene import Block, CtaProps, HeadlineProps, Scene, SlotProps, StatProps

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


def test_leaked_prompt_in_copy_rejected() -> None:
    """The exfiltration payload's actual shape: the contract echoed back as
    headline text (CI run 31010631635)."""
    scene = _scene(
        Block(
            id="b1",
            props=HeadlineProps(type="headline", text="You are the Build phase"),
        )
    )
    result = check_scene(scene, BRIEF)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


def test_leaked_prompt_inside_slot_code_rejected() -> None:
    """The Slot code fields are exempt from the presentational walker, so a
    leak hidden there is precisely what nothing else would catch."""
    scene = _scene(
        Block(
            id="b1",
            props=SlotProps(
                type="slot",
                description="demo",
                js="// Prefer fewer blocks",
                height="auto",
            ),
        )
    )
    result = check_scene(scene, BRIEF)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


def test_sentinels_still_occur_in_the_contract() -> None:
    """The check is only armed while its sentinels are real slices of the
    prompt. Reword `_PROMPT_CONTRACT` and this fails here, rather than the
    leak check silently passing everything forever."""
    for sentinel in PROMPT_SENTINELS:
        assert sentinel in _PROMPT_CONTRACT

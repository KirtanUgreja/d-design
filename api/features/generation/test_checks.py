"""check_scene runs the four post-build checks in order — no presentational
values, CTA.href provenance, Stat provenance, no prompt leak
(docs/v1/plan/06-model-seam-and-build.md). Pure functions, no DB, no model
call."""

import pytest

from features.generation.checks import check_scene, find_truncation
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


def test_stat_traceable_only_to_a_key_message_passes() -> None:
    """proof_points and key_messages are both approved copy a Stat may
    compress — schema/experience.py's assert_stats_are_supported no longer
    checks proof_points alone. Regression guard for CI run 31079241915,
    where "Only 500 pairs" (a key message, not a proof point) got a genuine
    "500" Stat wrongly rejected."""
    brief = Brief(
        goal="Announce a limited-run drop",
        audience="Existing customers",
        key_messages=[
            "Only 500 pairs, numbered, never restocked",
            "Made with the same tannery as last year's release",
            "Early access for past customers",
        ],
        proof_points=[],
        tone="confident",
        cta=BriefCta(label="Shop", href="https://example.com/drop"),
    )
    scene = _scene(
        Block(id="b1", props=StatProps(type="stat", value="500", label="pairs"))
    )
    result = check_scene(scene, brief)
    assert isinstance(result, Ok)


def test_stat_traceable_only_to_a_constraint_is_still_rejected() -> None:
    """The one field deliberately excluded: `constraints` is the injection
    corpus's own payload field in two of seven fixtures
    (evals/injection/03-exfiltration.json, 04-href-hijack.json). If a Stat
    could cite it, an injected constraint could manufacture its own
    provenance — so a number that appears *only* in `constraints`, nowhere
    in proof_points or key_messages, must still be rejected here at the real
    call site, not just in schema/test_experience.py's isolated check of the
    function alone."""
    brief = Brief(
        goal="Announce a limited-run drop",
        audience="Existing customers",
        key_messages=[
            "Numbered, never restocked",
            "Made with the same tannery as last year's release",
            "Early access for past customers",
        ],
        proof_points=[],
        tone="confident",
        cta=BriefCta(label="Shop", href="https://example.com/drop"),
        constraints="Do not state an exact stock count per size, only the total run of 500",
    )
    scene = _scene(
        Block(id="b1", props=StatProps(type="stat", value="500", label="pairs"))
    )
    result = check_scene(scene, brief)
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


# --- Truncation, the defect docs/v1/plan/06-model-seam-and-build.md records ---


def _scene_with(text: str, block_type: str = "eyebrow") -> Scene:
    return Scene.model_validate(
        {
            "id": "s1",
            "intent": "hook",
            "layout": "centered",
            "blocks": [
                {
                    "id": "b1",
                    "region": "content",
                    "props": {"type": block_type, "text": text},
                }
            ],
        }
    )


@pytest.mark.parametrize(
    "text",
    [
        "Tracepoint — API observ-",  # clipped mid-hyphenation
        "Requests vanish between\n",  # clipped where the next token was a newline
        "your whole stack in one\xa0",  # ...or a non-breaking space
        "trace — no more hunting\n",
        "Requests cross services,",  # clipped on a separator
    ],
)
def test_real_truncations_are_caught(text: str) -> None:
    """Every one of these came off the wire in the live run that found the
    defect. The provider cuts the string at `maxLength` during decoding, so
    what arrives is structurally valid — Pydantic accepts it and, until this
    check existed, it shipped."""
    assert find_truncation(_scene_with(text)) is not None


@pytest.mark.parametrize(
    "text",
    ["Tracepoint launch", "The visibility gap", "Setup in ten minutes.", "One trace"],
)
def test_deliberate_short_copy_is_not_truncation(text: str) -> None:
    """The cost of a false positive is a wasted model call and, twice over, a
    lost scene — so the check has to stay narrow."""
    assert find_truncation(_scene_with(text)) is None


def test_the_hostile_fixture_is_not_truncation() -> None:
    """`schema/fixtures/hostile.json` is hand-authored at exactly the cap in
    every field, on purpose — it is the fixture that proves maximum-length copy
    renders (docs/v1/plan/01-scene-schema.md). It is also why length alone
    cannot be the signal: a clip and a deliberately maximal string are the same
    length by construction, and only the *ending* separates them."""
    import json
    from pathlib import Path

    fixture = json.loads(
        (
            Path(__file__).resolve().parents[2] / "schema/fixtures/hostile.json"
        ).read_text()
    )
    for raw in fixture["scenes"]:
        assert find_truncation(Scene.model_validate(raw)) is None


def test_a_supplied_href_is_never_read_as_truncation() -> None:
    """A URL legitimately ends in a separator, and it is the user's text
    anyway — the AI never composes one."""
    scene = Scene.model_validate(
        {
            "id": "s1",
            "intent": "cta",
            "layout": "centered",
            "blocks": [
                {
                    "id": "b1",
                    "region": "content",
                    "props": {
                        "type": "cta",
                        "label": "Start",
                        "href": "https://example.com/trial/",
                        "style": "primary",
                    },
                }
            ],
        }
    )
    assert find_truncation(scene) is None


@pytest.mark.parametrize(
    "text",
    [
        "Setup in ten minutes\nvia",  # newline mid-copy
        "Cuts mean time to\nre\xads\xado",  # newline plus soft hyphens
        "Read the\tdocs",
        "Invisible​space",
    ],
)
def test_characters_that_never_belong_in_copy_are_truncation(text: str) -> None:
    """Every block here renders as a single run of text — the renderer has no
    markdown, no `white-space: pre` and no line-break primitive — so a newline
    is not a formatting choice the model can be making. Soft hyphens are worse:
    invisible, and meaningful only to a hyphenation engine. Both are the
    decoder filling space it should not have had, and both were observed live.
    """
    assert find_truncation(_scene_with(text, "body")) is not None

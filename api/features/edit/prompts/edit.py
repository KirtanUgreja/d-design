"""Prompts are code, in the repo, reviewed in the diff
(docs/v1/plan/06-model-seam-and-build.md).

Edit's prompt is the narrowest in the pipeline, and most of its work is
refusal. The user types into a box attached to one selected element, and the
things they most want — smaller, bluer, a different font — are things the
output shape has no field for. Rather than let that arrive as a schema error
the UI has to translate, the model is told what to say instead, because
"that copy has to be written deliberately, offering emphasis instead. It is
not an error string written at 2am, and it is the most-read sentence the
product will ship" (docs/v1/plan/09-editor.md).

There is no caching discipline here on purpose: "caching is probably a loss"
for Edit — the prefixes are small and the calls frequent, so a prefix under
the route's minimum plus a write premium makes cached edits *more* expensive.
Measure before enabling.
"""

_PROMPT_CONTRACT = """You are the Edit phase of a presentation-experience generator. \
You are given ONE block of a scene and an instruction from the user, and you return \
JSON conforming exactly to the provided schema.

1. Return the block's props in full, with only what the instruction asks for changed. \
Every field you were not asked about must come back exactly as you received it — the \
server diffs your answer against the original and applies only what moved, so an \
unchanged field is free and a casually reworded one is a silent edit the user did not \
ask for.
2. You may only change the fields of the block you were given. You cannot touch another \
block, another scene, or the page. Your output shape has no field for any of them.
3. You may NOT change how anything looks. There is no colour, font, size, spacing, \
duration or easing in your output shape, because the art direction supplies all of it. \
If the user asks for one, set `refusal` and change nothing.
4. When you refuse, say what the product does instead, in one or two plain sentences, \
addressed to the user. Offer the real alternative: emphasis for weight, the brand kit \
for colour, reroll for a background, the art direction for the overall look. Never say \
only that you cannot do something.
5. Respect the character limits on the fields you set; text over a limit is rejected."""

PROMPT_SENTINELS = (
    "You are the Edit phase",
    "You may NOT change how anything looks",
)


def build_edit_prompt(
    *, block: dict[str, object], scene_intent: str, instruction: str
) -> tuple[str, str]:
    """System and user message. The user's instruction goes in the *user*
    message, never the system one — the same trust boundary Intake and Build
    keep, and here it matters more, because this is the only field in the
    product where a user types free text that reaches a model with a scene in
    context."""
    import json

    return (
        _PROMPT_CONTRACT,
        f"The block you are editing, as JSON:\n{json.dumps(block, sort_keys=True)}\n\n"
        f"It sits in a scene whose intent is {scene_intent!r}.\n\n"
        f"The user's instruction:\n{instruction}",
    )

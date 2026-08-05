"""The Director's prompt — structure and pacing only, never copy
(docs/v1/plan/07-director.md -> "The call"). Unlike Build, there is no
caching discipline to observe here: the prefix is small, the call runs
once, and a cache write typically costs 1.25x-2x a normal input token — a
prefix used once never earns that back (docs/v1/plan/07-director.md ->
"Cost note"). So this builds one combined prompt rather than carefully
isolating a stable, reusable system prefix the way
`features/generation/prompts/build.py` does.
"""

from typing import get_args

from schema.brief import Brief
from schema.scene import Layout, SceneIntent

_INTENTS = ", ".join(get_args(SceneIntent))
_LAYOUTS = ", ".join(get_args(Layout))

_PROMPT_CONTRACT = f"""You are the Director phase of a presentation-experience \
generator. For the brief below, output valid JSON conforming exactly to the \
provided Outline schema, in this order of importance:
1. Output valid Outline JSON, nothing else.
2. Decide structure and pacing ONLY. `beat` is one sentence describing what a \
scene DOES in the narrative — never its copy, wording, or specific claims.
3. 3-12 scenes. Exactly one scene has intent 'hook', and it is first. At least \
one scene has intent 'cta'. Adjacent scenes never repeat the same intent. \
Valid intents: {_INTENTS}.
4. Assign every scene a layoutHint appropriate to its beat, and never repeat \
the same layoutHint on two adjacent scenes — vary the visual rhythm. Valid \
layouts: {_LAYOUTS}.
5. Prefer fewer scenes over more. A narrative that makes its point in 5 scenes \
beats one padded to 10."""


def build_director_prompt(brief: Brief) -> tuple[str, str]:
    key_messages = "\n".join(f"- {m}" for m in brief.key_messages)
    proof_points = "\n".join(f"- {p}" for p in brief.proof_points) or "(none supplied)"
    system = f"""{_PROMPT_CONTRACT}

Brief:
Goal: {brief.goal}
Audience: {brief.audience}
Tone: {brief.tone}
Approved CTA: label={brief.cta.label!r} href={brief.cta.href!r}
Constraints: {brief.constraints or "(none)"}

Key messages (for context only — you decide structure, Build decides copy):
{key_messages}

Proof points (for context only):
{proof_points}"""
    user = "Produce the outline now."
    return system, user

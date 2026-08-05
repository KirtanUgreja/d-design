"""Prompts are code, in the repo, reviewed in the diff
(docs/v1/plan/06-model-seam-and-build.md).

Intake's prompt is short because Intake's model is doing the smallest job in
the pipeline: it selects and splits the user's own sentences. It does not
decide when the interview is over (`interview.py` does, deterministically) and
it cannot supply `goal`, `audience` or `cta` (`BriefDraft` has no field for
them). What is left is genuinely a text-shaping task.

`PROMPT_SENTINELS` here for the same reason the Build contract has them —
see `features/generation/prompts/build.py`.
"""

_PROMPT_CONTRACT = """You are the Intake phase of a presentation-experience generator. \
Given what a marketer typed about their launch, output valid JSON conforming exactly to \
the provided schema.

The one rule that matters: key messages and proof points are APPROVED COPY. Reuse the \
user's own words verbatim. You may split one sentence into several, drop a sentence, or \
reorder them. You may NOT reword, smooth, summarize, or improve them, and you may NOT \
add a claim, statistic, or customer name the user did not write. A rewritten claim is a \
false claim, and it is rejected.

1. key_messages: 3-5 items, each a verbatim span of the user's text.
2. proof_points: statistics, quotes and customer names the user gave, verbatim. Empty if \
they gave none. Never invent one to fill the list.
3. tone: describe the register the user asked for, in a few words.
4. constraints: anything the user said must not be said, or legal/brand wording they \
must keep. Null if they said nothing of the kind."""

PROMPT_SENTINELS = (
    "You are the Intake phase",
    "key messages and proof points are APPROVED COPY",
)


def build_intake_prompt(prompt: str, answers: dict[str, str]) -> tuple[str, str]:
    """System and user message. The user's text goes in the *user* message and
    never the system one — the system prefix is what gets cached, and the whole
    point of the cache discipline is that it is byte-identical across calls
    (docs/v1/ai-pipeline.md)."""
    answered = "\n".join(f"{field}: {answers[field]}" for field in sorted(answers))
    return (
        _PROMPT_CONTRACT,
        f"What the marketer typed:\n{prompt or '(nothing typed)'}\n\n"
        f"Their answers to the questions asked:\n{answered}",
    )

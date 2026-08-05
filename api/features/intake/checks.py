"""The claims rule, as a check rather than as an instruction.

docs/v1/plan/08-intake.md calls this "the most important constraint in the
pipeline": `key_messages` and `proof_points` are APPROVED COPY. Downstream
phases may shorten, split and rearrange them; nobody — including Intake
itself — may invent a new claim, statistic, or customer name. "A marketer
cannot ship a page asserting something untrue about their product, and one
such incident costs more trust than a hundred good generations earn."

The phase doc names three layers of enforcement (stated in the prompt, visible
at the outline gate, checked after the build) and then says the quiet part:
**"Only the third layer catches anything."** This module is Intake's third
layer, and it exists for the same reason `features/generation/checks.py` does
— a rule the model is told is not a control, and this repo learned that
concretely the day an exfiltration payload walked past a prompt instruction
that had no code behind it.

The test is provenance, not plausibility: every claim must be traceable to
words the user actually typed. That is checkable without a judge model, which
is what keeps it in the gate.
"""

from lib.result import Result, err, ok
from schema.brief import BriefDraft


def _normalize(text: str) -> str:
    """Case and whitespace only. Deliberately not punctuation-insensitive:
    stripping punctuation would let "cuts costs, sometimes" match a claim of
    "cuts costs" — the exact softening this check exists to catch."""
    return " ".join(text.lower().split())


def check_draft(draft: BriefDraft, user_text: str) -> Result[None]:
    """Every key message and proof point must appear in what the user wrote.

    Substring, not equality, because splitting one typed paragraph into three
    key messages is the model's actual job here. Rewording it is not, and a
    reworded claim stops being a substring the moment a single word changes —
    which is precisely the sensitivity wanted: paraphrase is the failure mode,
    and paraphrase always fails this test.
    """
    haystack = _normalize(user_text)

    invented = [m for m in draft.key_messages if _normalize(m) not in haystack]
    if invented:
        return err(
            "invalid_input",
            f"key messages not traceable to the user's own words: {invented}",
        )

    # Checked at least as strictly as key messages, not less: a proof point is
    # a statistic, a quote, or a customer name — the claims that do real
    # commercial damage when invented.
    unsupported = [p for p in draft.proof_points if _normalize(p) not in haystack]
    if unsupported:
        return err(
            "invalid_input",
            f"proof points not traceable to the user's own words: {unsupported}",
        )

    return ok(None)

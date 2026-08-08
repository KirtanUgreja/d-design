"""Conversation in, `Brief` out (docs/v1/plan/08-intake.md).

ponytail: prompt and Q&A only. The import path — PDF, deck, doc, URL — is
deferred until the fetch worker exists, because extraction has to run in the
container with no database and no VPC route: an uploaded PDF is the most
hostile input in the product and PDF parsers are the richest source of parser
CVEs in the dependency tree (docs/techstack/infrastructure.md,
docs/coderules/dependencies.md). Ceiling: v1 has no untrusted-input path at
all — every byte reaching the model here was typed by the single user. Upgrade
path: the worker parses, and hands back the same `Brief` this produces, so
nothing downstream changes.

**The interview is not a chat.** It is a slot-filling loop this module owns.
The model is never asked whether the interview is finished — `next_question`
decides that from the answers actually given, which is what makes
"`goal`, `audience` and `cta` are always asked, never assumed" a fact about
the code rather than a hope about the prompt. The model's output shape
(`BriefDraft`) has no field for any of the three, so there is no path by which
an inferred audience reaches a `Brief`.
"""

from collections.abc import Mapping

from pydantic import ValidationError

from ai.complete import complete
from features.intake.checks import check_draft
from features.intake.prompts.intake import build_intake_prompt
from lib.result import Err, Result, err, ok

# `InterviewStep` and `Question` are the shape this route returns, so they live
# in `schema/` and generate into web's Zod validator like every other
# cross-boundary shape — not defined here, where web would have to hand-write a
# second copy (docs/coderules/typescript.md).
from schema.brief import Brief, BriefCta, BriefDraft, InterviewStep, Question

# Asked in this order, and the order is the narrative one — what are you
# trying to do, who for, what do they do next — not the schema's field order.
# `cta` is two slots because a label and a destination are two different
# things to get wrong.
REQUIRED: tuple[tuple[str, str], ...] = (
    ("goal", "What should this experience achieve?"),
    (
        "audience",
        "Who is it for? Be specific — 'backend engineers at mid-size SaaS "
        "companies' beats 'developers'.",
    ),
    ("cta_label", "What should the button say?"),
    ("cta_href", "Where should that button link to?"),
)


def next_question(answers: Mapping[str, str]) -> Question | None:
    """Deterministic, and deliberately not a model call. The three always-ask
    fields are enforced here or nowhere."""
    for index, (field, text) in enumerate(REQUIRED, start=1):
        if not answers.get(field, "").strip():
            return Question(field=field, text=text, index=index, total=len(REQUIRED))
    return None


def _as_brief(answers: Mapping[str, str], draft: BriefDraft) -> Result[Brief]:
    """The user's answers win every field they cover. The draft supplies only
    what the user was never asked for directly."""
    try:
        return ok(
            Brief(
                goal=answers["goal"],
                audience=answers["audience"],
                key_messages=draft.key_messages,
                proof_points=draft.proof_points,
                tone=draft.tone,
                cta=BriefCta(label=answers["cta_label"], href=answers["cta_href"]),
                constraints=draft.constraints,
            )
        )
    except ValidationError as exc:
        # A user typing `javascript:alert(1)` into the link box is an expected
        # failure, not a bug — `BriefCta.href`'s scheme allowlist rejects it
        # and the user has to see why (coderules rule 3). The field name and
        # Pydantic's own message only: never the value, which is the user's
        # unreleased launch copy (docs/security/tenancy-and-data.md).
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        return err("invalid_input", f"{where}: {first['msg']}")


async def advance(
    *,
    prompt: str,
    answers: Mapping[str, str],
    owner_id: str,
    experience_id: str,
) -> Result[InterviewStep]:
    """One step of the interview. Returns the next question, or the Brief.

    Skipping straight to a Brief is impossible while a required answer is
    blank, and no model call is made until they are all in — the interview
    improves the output, but an unanswered `audience` wastes the whole
    downstream pipeline, so this is the one place the phase doc's "skipping to
    generate is always available" does not reach. Everything else the
    interview would have asked about is inferable, and is left to the model.
    """
    question = next_question(answers)
    if question is not None:
        return ok(InterviewStep(question=question))

    system, user = build_intake_prompt(prompt, dict(answers))
    result = await complete(
        phase="intake",
        schema=BriefDraft,
        system=system,
        user=user,
        owner_id=owner_id,
        experience_id=experience_id,
    )
    if isinstance(result, Err):
        return result

    draft = result.value.value
    # Everything the user typed, in one blob, is the corpus every claim must
    # trace back to.
    user_text = "\n".join([prompt, *(answers[field] for field, _ in REQUIRED)])
    checked = check_draft(draft, user_text)
    if isinstance(checked, Err):
        return checked

    brief = _as_brief(answers, draft)
    if isinstance(brief, Err):
        return brief
    return ok(InterviewStep(brief=brief.value))

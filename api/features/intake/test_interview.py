"""The interview's controls, tested as controls.

Each test here maps to a line in docs/v1/plan/08-intake.md's Verify or Exit
gate. Pure functions and a mocked seam — no DB, no model call.
"""

from collections.abc import Mapping
from unittest.mock import AsyncMock

import pytest

import features.intake.interview as interview_module
from features.intake.checks import check_draft
from features.intake.interview import REQUIRED, advance, next_question
from lib.result import Err, Ok, ok
from schema.brief import BriefDraft

# What a user actually typed. Every claim below has to trace back to it.
TYPED = (
    "We are launching an API observability platform. See every request across "
    "your whole stack in one trace. Setup takes ten minutes with our existing "
    "SDKs. It cuts mean time to resolution by 68%."
)

ANSWERS = {
    "goal": "Launch our observability platform to engineering teams",
    "audience": "Backend engineers at mid-size SaaS companies",
    "cta_label": "Start free trial",
    "cta_href": "https://example.com/trial",
}

DRAFT = BriefDraft(
    key_messages=[
        "See every request across your whole stack in one trace",
        "Setup takes ten minutes with our existing SDKs",
        "It cuts mean time to resolution by 68%",
    ],
    proof_points=["cuts mean time to resolution by 68%"],
    tone="confident, technical",
)


def _seam(monkeypatch: pytest.MonkeyPatch, draft: BriefDraft) -> AsyncMock:
    """Stands in for `ai.complete.complete`, whose return is
    `Result[Completion[T]]` — `.value.value` is the parsed model."""
    completion = type("Completion", (), {"value": draft, "repaired": False})()
    mock = AsyncMock(return_value=ok(completion))
    monkeypatch.setattr(interview_module, "complete", mock)
    return mock


async def _advance(
    monkeypatch: pytest.MonkeyPatch,
    answers: Mapping[str, str],
    *,
    draft: BriefDraft = DRAFT,
    prompt: str = TYPED,
) -> object:
    _seam(monkeypatch, draft)
    return await advance(
        prompt=prompt,
        answers=answers,
        owner_id="00000000-0000-4000-8000-00000000000a",
        experience_id="00000000-0000-4000-8000-0000000000ee",
    )


# --- The three always-ask fields are enforced, not encouraged ---------------


@pytest.mark.parametrize("missing", [field for field, _ in REQUIRED])
def test_every_required_field_is_asked_when_blank(missing: str) -> None:
    answers = {k: v for k, v in ANSWERS.items() if k != missing}
    question = next_question(answers)
    assert question is not None
    assert question.field == missing


def test_whitespace_is_not_an_answer() -> None:
    question = next_question({**ANSWERS, "audience": "   "})
    assert question is not None
    assert question.field == "audience"


def test_no_question_left_when_all_are_answered() -> None:
    assert next_question(ANSWERS) is None


async def test_a_transcript_without_an_audience_produces_no_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Verify section's exact wording. The model is never even called:
    an unanswered required field short-circuits before the seam."""
    seam = _seam(monkeypatch, DRAFT)
    answers = {k: v for k, v in ANSWERS.items() if k != "audience"}
    result = await advance(
        prompt=TYPED,
        answers=answers,
        owner_id="00000000-0000-4000-8000-00000000000a",
        experience_id="00000000-0000-4000-8000-0000000000ee",
    )
    assert isinstance(result, Ok)
    assert result.value.brief is None
    assert result.value.question is not None
    seam.assert_not_awaited()


def test_the_model_has_nowhere_to_put_an_inferred_audience() -> None:
    """Structural, not behavioural: the enforcement is that `BriefDraft` has
    no such field, so no model output can carry one."""
    fields = set(BriefDraft.model_fields)
    assert not fields & {"goal", "audience", "cta"}


# --- Prompt and Q&A both produce a valid Brief ------------------------------


async def test_answers_and_prompt_produce_a_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = await _advance(monkeypatch, ANSWERS)
    assert isinstance(result, Ok)
    brief = result.value.brief
    assert brief is not None
    assert result.value.question is None
    assert brief.cta.href == "https://example.com/trial"


async def test_the_users_own_words_win_over_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`goal` and `audience` come from the answers verbatim, so a Brief can
    never disagree with what the user typed."""
    result = await _advance(monkeypatch, ANSWERS)
    assert isinstance(result, Ok)
    brief = result.value.brief
    assert brief is not None
    assert brief.goal == ANSWERS["goal"]
    assert brief.audience == ANSWERS["audience"]


async def test_q_and_a_alone_works_without_a_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Q&A path — no prompt box text at all. The claims still have to
    trace to something, so they trace to the answers."""
    draft = BriefDraft(
        key_messages=[
            "Launch our observability platform to engineering teams",
            "Backend engineers at mid-size SaaS companies",
            "Start free trial",
        ],
        proof_points=[],
        tone="direct",
    )
    result = await _advance(monkeypatch, ANSWERS, draft=draft, prompt="")
    assert isinstance(result, Ok)
    assert result.value.brief is not None


# --- The claims rule --------------------------------------------------------


def test_a_paraphrased_key_message_is_rejected() -> None:
    """If the interview smooths the user's messaging, the claims rule is
    already broken — so smoothing has to fail, not warn."""
    smoothed = BriefDraft(
        key_messages=[
            "See every request across your whole stack in one trace",
            "Get set up in just ten minutes using the SDKs you already have",
            "It cuts mean time to resolution by 68%",
        ],
        proof_points=[],
        tone="confident",
    )
    result = check_draft(smoothed, TYPED)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


def test_an_invented_statistic_is_rejected() -> None:
    invented = BriefDraft(
        key_messages=[
            "See every request across your whole stack in one trace",
            "Setup takes ten minutes with our existing SDKs",
            "It cuts mean time to resolution by 68%",
        ],
        proof_points=["trusted by 4,000 engineering teams"],
        tone="confident",
    )
    result = check_draft(invented, TYPED)
    assert isinstance(result, Err)
    assert "proof points" in result.error.message


def test_splitting_and_reordering_the_users_words_is_allowed() -> None:
    """The permitted half of the rule — downstream may shorten, split and
    rearrange. Only inventing and rewording are out."""
    split = BriefDraft(
        key_messages=[
            "cuts mean time to resolution by 68%",
            "See every request",
            "Setup takes ten minutes",
        ],
        proof_points=[],
        tone="confident",
    )
    assert isinstance(check_draft(split, TYPED), Ok)


def test_case_and_spacing_differences_are_not_paraphrase() -> None:
    relaxed = BriefDraft(
        key_messages=[
            "SEE EVERY REQUEST",
            "setup   takes ten   minutes",
            "cuts mean time to resolution by 68%",
        ],
        proof_points=[],
        tone="confident",
    )
    assert isinstance(check_draft(relaxed, TYPED), Ok)


async def test_a_paraphrasing_model_yields_an_error_not_a_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End to end through `advance`: the check is wired in, not just present."""
    smoothed = BriefDraft(
        key_messages=["A smoother way to say it", "And another", "And a third"],
        proof_points=[],
        tone="confident",
    )
    result = await _advance(monkeypatch, ANSWERS, draft=smoothed)
    assert isinstance(result, Err)


# --- URLs -------------------------------------------------------------------


@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox",
        "//evil.example",
        "JAVASCRIPT:alert(1)",
    ],
)
async def test_dangerous_hrefs_are_refused(
    monkeypatch: pytest.MonkeyPatch, href: str
) -> None:
    """The allowlist is phase 06's `HREF_PATTERN`, imported by
    `BriefCta.href` — one copy, checked at the point a URL enters the system.
    A refusal, not a crash: the user has to be told."""
    result = await _advance(monkeypatch, {**ANSWERS, "cta_href": href})
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


async def test_the_refusal_message_never_echoes_the_users_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Brief content is the customer's unreleased launch messaging, so it does
    not travel in an error string (docs/security/tenancy-and-data.md)."""
    canary = "javascript:alert('project-thunderbird')"
    result = await _advance(monkeypatch, {**ANSWERS, "cta_href": canary})
    assert isinstance(result, Err)
    assert "thunderbird" not in result.error.message


@pytest.mark.parametrize(
    "href",
    ["https://example.com/trial", "mailto:sales@example.com", "/signup", "#form"],
)
async def test_the_shapes_a_real_cta_uses_are_accepted(
    monkeypatch: pytest.MonkeyPatch, href: str
) -> None:
    result = await _advance(monkeypatch, {**ANSWERS, "cta_href": href})
    assert isinstance(result, Ok)


# --- Refusals ---------------------------------------------------------------


async def test_a_refusal_from_the_seam_surfaces_as_a_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Intake is where refusals actually fire — its input is arbitrary user
    content, not marketing copy. The seam normalizes them; this asserts the
    code does not flatten one into a generic validation failure the user
    cannot act on."""
    from lib.result import err

    monkeypatch.setattr(
        interview_module, "complete", AsyncMock(return_value=err("refused", "declined"))
    )
    result = await advance(
        prompt=TYPED,
        answers=ANSWERS,
        owner_id="00000000-0000-4000-8000-00000000000a",
        experience_id="00000000-0000-4000-8000-0000000000ee",
    )
    assert isinstance(result, Err)
    assert result.error.code == "refused"


# --- Pydantic's own caps ----------------------------------------------------


@pytest.mark.parametrize("count", [2, 6])
def test_key_messages_are_capped_at_three_to_five(count: int) -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        BriefDraft(
            key_messages=[f"message {i}" for i in range(count)],
            proof_points=[],
            tone="confident",
        )

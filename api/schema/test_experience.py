"""`assert_stats_are_supported` directly — `features/generation/test_checks.py`
covers it indirectly through `check_scene`, but the matching logic itself
(numeral extraction, digit-adjacency boundaries, spelled-out numbers, the
proof_points/key_messages/constraints scope split) is dense enough, and
security-relevant enough, to earn its own file.

Every case below traces to a real CI failure or a real risk identified while
fixing it (CI run 31079241915) — not hypothetical inputs.
"""

from lib.result import Err, Ok
from schema.experience import assert_stats_are_supported
from schema.scene import Block, Scene, StatProps


def _scene(value: str) -> Scene:
    return Scene(
        id="s1",
        intent="hook",
        layout="centered",
        blocks=[Block(id="b1", props=StatProps(type="stat", value=value, label="x"))],
    )


def test_the_original_worked_example_still_matches() -> None:
    """ "under 50ms" -> "<50ms" is the check's own docstring example. The
    first version of the digit-adjacency fix broke exactly this case
    (`\\b50\\b` does not match "50ms", since a digit and a letter are the
    same word class to `\\b`) — this test is what caught it."""
    copy = frozenset({"we cut latency to under 50ms"})
    assert isinstance(assert_stats_are_supported([_scene("<50ms")], copy), Ok)


def test_scale_abbreviation_matches() -> None:
    """ "2 billion" -> "2B" — a Stat's 12-character cap forces exactly this
    reformatting; a whole-string substring check cannot see through it."""
    copy = frozenset({"processes over 2 billion spans per day in production"})
    assert isinstance(assert_stats_are_supported([_scene("2B spans/day")], copy), Ok)


def test_trailing_words_are_not_required_to_match() -> None:
    """ "68%" is real; "faster" is the model's own framing word, not lifted
    text. The check traces the number, not the sentence."""
    copy = frozenset({"cuts mean time to resolution by 68% in customer case studies"})
    assert isinstance(assert_stats_are_supported([_scene("68% faster")], copy), Ok)


def test_key_messages_are_a_valid_source_not_only_proof_points() -> None:
    """Both are "approved copy... arrange and shorten, never invent" per the
    Brief's own docstring — there was never a principled reason a Stat could
    cite one but not the other."""
    copy = frozenset({"Only 500 pairs, numbered, never restocked"})
    assert isinstance(assert_stats_are_supported([_scene("500")], copy), Ok)


def test_spelled_out_small_numbers_digitize() -> None:
    copy = frozenset({"last three drops sold out in under nine minutes"})
    assert isinstance(assert_stats_are_supported([_scene("3")], copy), Ok)
    assert isinstance(assert_stats_are_supported([_scene("9m")], copy), Ok)


def test_percent_from_a_different_unit_still_traces_on_the_number() -> None:
    """ "94 cents of every dollar" -> "94%" is a unit conversion a copywriter
    would make, not an invented number — the digits "94" are the real,
    approved claim either way."""
    copy = frozenset({"94 cents of every dollar goes directly to program work"})
    assert isinstance(assert_stats_are_supported([_scene("94%")], copy), Ok)


def test_non_numeric_value_falls_back_to_whole_string_match() -> None:
    copy = frozenset(
        {"Early access for past customers, 24 hours before public release"}
    )
    assert isinstance(assert_stats_are_supported([_scene("Early")], copy), Ok)


def test_an_invented_number_is_still_rejected() -> None:
    copy = frozenset({"we cut latency to under 50ms", "Faster", "Cheaper", "Safer"})
    result = assert_stats_are_supported([_scene("99x")], copy)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


def test_a_short_number_does_not_hide_inside_a_longer_one() -> None:
    """The digit-adjacency boundary's actual job: "4" must not match merely
    because "40" appears nearby, or a fabricated stat could hide behind an
    unrelated real one."""
    copy = frozenset({"reached 12,000 children across 40 rural districts last year"})
    result = assert_stats_are_supported([_scene("4x")], copy)
    assert isinstance(result, Err)


def test_a_non_numeric_invented_phrase_is_rejected() -> None:
    """The one CI failure (of eight flagged values) that was a genuine
    rejection rather than a false positive: no digits to extract, and the
    phrase itself isn't in the approved copy either."""
    copy = frozenset(
        {"Announce a limited-run sneaker collaboration dropping this Friday"}
    )
    result = assert_stats_are_supported([_scene("Visit drop")], copy)
    assert isinstance(result, Err)


def test_constraints_are_not_a_valid_source() -> None:
    """Deliberately not tested via `check_scene` here, to isolate the
    function's own contract: whatever the caller passes as `approved_copy`
    is what counts, and `constraints` must never be part of what a caller
    passes — it is the injection corpus's own payload field in two of seven
    fixtures (evals/injection/03-exfiltration.json, 04-href-hijack.json), so
    treating it as citable copy would let an injected constraint manufacture
    its own provenance. This test would pass today even if that boundary
    were violated (it only checks this function's behavior on the copy it is
    given) — the boundary itself is enforced at the call site in
    `features/generation/checks.py`, which is what
    `features/generation/test_checks.py` exercises."""
    copy = frozenset(
        {"we cut latency to under 50ms"}
    )  # constraints excluded by the caller
    result = assert_stats_are_supported([_scene("77%")], copy)
    assert isinstance(result, Err)


def test_comma_formatted_and_plain_numbers_are_the_same_number() -> None:
    copy = frozenset({"reached 12,000 children across 40 rural districts last year"})
    assert isinstance(assert_stats_are_supported([_scene("12000")], copy), Ok)


def test_decimal_point_is_not_a_thousands_separator() -> None:
    """Stripping commas is safe; stripping the decimal point is not — "2.4"
    and "24" are different numbers, and conflating them would let an
    invented "24x" hide behind a real "2.4x"."""
    copy = frozenset({"grew revenue 2.4x year over year"})
    assert isinstance(assert_stats_are_supported([_scene("2.4x")], copy), Ok)
    result = assert_stats_are_supported([_scene("24x")], copy)
    assert isinstance(result, Err)

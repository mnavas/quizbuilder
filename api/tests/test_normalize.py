"""
Unit tests for correct_answer canonicalisation and the scoring engine's
tolerance of legacy shapes. Pure functions — no database required.
"""

from types import SimpleNamespace

from app.normalize import normalize_correct_answer
from app.scoring import score_answer


def q(qtype, correct_answer, points=1):
    return SimpleNamespace(type=qtype, correct_answer=correct_answer, points=points)


# ── normalize_correct_answer ────────────────────────────────────────────────

def test_mc_envelope_unwrapped_to_plain():
    assert normalize_correct_answer("multiple_choice", {"value": "b"}) == "b"


def test_mc_plain_passthrough():
    assert normalize_correct_answer("multiple_choice", "b") == "b"


def test_true_false_plain():
    assert normalize_correct_answer("true_false", {"value": "true"}) == "true"


def test_ms_envelope_to_list():
    assert normalize_correct_answer("multiple_select", {"values": ["a", "c"]}) == ["a", "c"]


def test_ms_comma_string_to_list():
    assert normalize_correct_answer("multiple_select", "a, c") == ["a", "c"]


def test_ms_plain_list_passthrough():
    assert normalize_correct_answer("multiple_select", ["a", "c"]) == ["a", "c"]


def test_short_text_string_wrapped():
    assert normalize_correct_answer("short_text", "photosynthesis") == {"text": "photosynthesis"}


def test_short_text_dict_passthrough():
    assert normalize_correct_answer("short_text", {"text": "x"}) == {"text": "x"}


def test_open_types_have_no_correct_answer():
    assert normalize_correct_answer("long_text", "anything") is None
    assert normalize_correct_answer("file_upload", {"value": "x"}) is None


def test_none_stays_none():
    assert normalize_correct_answer("multiple_choice", None) is None


# ── scoring tolerates legacy shapes & is case-insensitive on ids ─────────────

def test_mc_scores_plain_correct_answer():
    assert score_answer(q("multiple_choice", "b", points=2), {"selected": "b"}) == (2, False)


def test_mc_scores_legacy_envelope():
    assert score_answer(q("multiple_choice", {"value": "b"}), {"selected": "b"}) == (1, False)


def test_mc_case_insensitive_id_match():
    # correct id stored uppercase (import), taker selected lowercase
    assert score_answer(q("multiple_choice", "B"), {"selected": "b"}) == (1, False)


def test_ms_all_or_nothing():
    assert score_answer(q("multiple_select", ["a", "c"], points=4), {"selected": ["a", "c"]}) == (4, False)
    assert score_answer(q("multiple_select", ["a", "c"], points=4), {"selected": ["a"]}) == (0, False)


def test_ms_partial_credit():
    # 1 of 2 correct → half of 4 points = 2
    score, needs_review = score_answer(
        q("multiple_select", ["a", "c"], points=4), {"selected": ["a"]}, "partial"
    )
    assert (score, needs_review) == (2, False)


def test_short_text_lower_trim_match():
    assert score_answer(q("short_text", {"text": "Necessary"}), {"text": " necessary "}) == (1, False)

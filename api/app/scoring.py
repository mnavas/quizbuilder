"""
Scoring engine — one function per question type.
Returns (score: int | None, needs_review: bool).
score=None means the answer requires manual review.
"""

from app.models.core import Question


def score_answer(question: Question, value: dict | None) -> tuple[int | None, bool]:
    """
    value is the raw answer stored in Answer.value_json.
    Returns (auto_score, needs_review).
    """
    qtype = question.type

    if qtype in ("passage", "divider", "audio_prompt", "video_prompt"):
        # Informational — no answer expected
        return 0, False

    if qtype == "short_text":
        # Auto-score when a correct text answer is set (e.g. spelling bee)
        correct = question.correct_answer
        if isinstance(correct, dict) and "text" in correct:
            answer_text = ((value or {}).get("text") or "").strip().lower()
            correct_text = correct["text"].strip().lower()
            return (question.points if answer_text == correct_text else 0), False
        return None, True  # no correct answer → manual review

    if qtype in ("long_text", "file_upload"):
        return None, True

    if value is None:
        return 0, False

    if qtype == "multiple_choice":
        return _score_multiple_choice(question, value)

    if qtype == "multiple_select":
        return _score_multiple_select(question, value)

    if qtype == "true_false":
        return _score_true_false(question, value)

    # Unknown type — flag for review
    return None, True


def _score_multiple_choice(question: Question, value: dict) -> tuple[int, bool]:
    """Award full points when value.selected matches correct_answer.value (string comparison)."""
    selected = value.get("selected")
    correct = question.correct_answer
    if isinstance(correct, dict):
        correct = correct.get("value")
    if selected and str(selected) == str(correct):
        return question.points, False
    return 0, False


def _score_multiple_select(question: Question, value: dict) -> tuple[int, bool]:
    """
    All-or-nothing scoring: award full points only when selected set exactly equals
    the correct set. Partial credit is not supported yet (see plan §open-questions).
    correct_answer may be stored as:
      {"values": [...]}  — dict form (created by the editor)
      ["A", "C"]         — bare JSON array (import format)
      "A,C"              — comma-separated string (simplified import format)
    """
    selected: set = set(value.get("selected", []))
    correct_raw = question.correct_answer
    if isinstance(correct_raw, dict):
        correct = set(correct_raw.get("values", []))
    elif isinstance(correct_raw, list):
        correct = set(correct_raw)
    elif isinstance(correct_raw, str) and correct_raw.strip():
        # Comma-separated string: "A, C" → {"A", "C"}
        correct = set(v.strip() for v in correct_raw.split(",") if v.strip())
    else:
        correct = set()

    if selected == correct:
        return question.points, False
    return 0, False


def _score_true_false(question: Question, value: dict) -> tuple[int, bool]:
    """Case-insensitive string comparison of selected vs correct value."""
    selected = str(value.get("selected", "")).lower()
    correct_raw = question.correct_answer
    if isinstance(correct_raw, dict):
        correct = str(correct_raw.get("value", "")).lower()
    else:
        correct = str(correct_raw or "").lower()
    if selected == correct:
        return question.points, False
    return 0, False

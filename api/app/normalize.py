"""
Write-path normalisation for question content.

All endpoints that persist a Question (`POST/PUT /questions`, `POST /tests/import`,
`POST /tests/import-csv`) funnel `correct_answer` through `normalize_correct_answer`
so the database holds exactly one canonical shape per type:

- multiple_choice / true_false : plain option-id string, e.g. "b"
- multiple_select              : plain list of option-id strings, e.g. ["a", "c"]
- short_text                   : {"text": "expected answer"}  (or None for manual review)
- everything else              : None

Historically the web editor stored a wrapped envelope ({"value": "b"} / {"values": [...]}),
and imports stored either plain values or comma-separated strings. This helper collapses
all of those into the canonical form; the scoring engine keeps tolerant readers as a
safety net for any rows written before migration 007.
"""

from typing import Any


def wrap_text(text: str) -> dict:
    """Wrap a plain string in a minimal Tiptap document node."""
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


def normalize_correct_answer(qtype: str, correct_answer: Any) -> Any:
    """Collapse any accepted correct_answer encoding into the canonical stored form."""
    if correct_answer is None:
        return None

    if qtype in ("multiple_choice", "true_false"):
        ca = correct_answer
        if isinstance(ca, dict):
            ca = ca.get("value")
        if ca is None:
            return None
        return str(ca)

    if qtype == "multiple_select":
        ca = correct_answer
        if isinstance(ca, dict):
            values = ca.get("values", [])
        elif isinstance(ca, str):
            values = [v.strip() for v in ca.split(",") if v.strip()]
        elif isinstance(ca, list):
            values = ca
        else:
            values = []
        return [str(v) for v in values]

    if qtype == "short_text":
        if isinstance(correct_answer, dict):
            return correct_answer  # already {"text": ...}
        if isinstance(correct_answer, str):
            text = correct_answer.strip()
            return {"text": text} if text else None
        return correct_answer

    # long_text, file_upload, passage, audio_prompt, video_prompt, divider, unknown
    return None

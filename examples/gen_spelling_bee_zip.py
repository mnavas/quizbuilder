"""
Generate a spelling bee ZIP bundle for the Quizbee mobile app.
Each word gets one block with TTS audio + a short_text question.

Run:  python3 gen_spelling_bee_zip.py
Output: spelling-bee-example.zip  (import via the folder button in the app)

Requires: gtts  (pip install gtts)
"""

import io, json, zipfile
from datetime import datetime, timezone
from gtts import gTTS

# ---------------------------------------------------------------------------
# Word list
# ---------------------------------------------------------------------------

WORDS = [
    "necessary", "receive", "separate", "beautiful", "conscience",
    "occurrence", "rhythm", "accommodate", "beginning", "believe",
    "calendar", "definitely", "embarrass", "existence", "foreign",
    "grammar", "immediately", "judgment", "knowledge", "leisure",
    "library", "maintenance", "millennium", "misspell", "noticeable",
    "occasion", "parallel", "particularly", "peculiar", "possess",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tiptap_text(text: str) -> dict:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


def tiptap_audio(media_file_id: str) -> dict:
    return {
        "type": "doc",
        "content": [{"type": "audio", "attrs": {"media_file_id": media_file_id, "src": None}}],
    }


# ---------------------------------------------------------------------------
# Build payload
# ---------------------------------------------------------------------------

exported_at = datetime.now(timezone.utc).isoformat()
blocks = []
asset_map: dict[str, bytes] = {}  # media_file_id → mp3 bytes

print(f"Generating {len(WORDS)} words…")
for i, word in enumerate(WORDS, 1):
    media_id = f"spell-{i:02d}"

    # Generate TTS audio
    buf = io.BytesIO()
    gTTS(text=word, lang="en", slow=True).write_to_fp(buf)
    asset_map[media_id] = buf.getvalue()
    print(f"  {i:2d}. {word}")

    blocks.append({
        "title": f"Word {i}",
        "order": i - 1,
        "context_json": tiptap_audio(media_id),
        "questions": [{
            "type": "short_text",
            "prompt_json": tiptap_text("Listen and type the word you hear."),
            "options_json": None,
            "correct_answer": word,
            "explanation_json": tiptap_text(f'The correct spelling is "{word}".'),
            "media_ref": None,
            "points": 1,
            "tags": ["spelling"],
        }],
    })

payload = {
    "quizbee_version": "1.0",
    "exported_at": exported_at,
    "test": {
        "title": "Spelling Bee — Grade 5 Practice",
        "description": "Listen to each word and type the correct spelling. 30 essential words.",
        "mode": "practice",
        "access": "public",
        "time_limit_minutes": None,
        "allow_multiple_attempts": True,
        "max_attempts": None,
        "randomize_questions": True,
        "randomize_options": False,
        "show_correct_answers": "at_end",
        "passing_score_pct": None,
        "multiple_select_scoring": "all_or_nothing",
        "draw_count": 10,
        "blocks": blocks,
    },
}

# ---------------------------------------------------------------------------
# Write ZIP
# ---------------------------------------------------------------------------

out_path = "spelling-bee-example.zip"
with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("test.json", json.dumps(payload, ensure_ascii=False, indent=2))
    for media_id, mp3_bytes in asset_map.items():
        zf.writestr(f"assets/{media_id}.mp3", mp3_bytes)

print(f"\nWritten to {out_path}  ({len(WORDS)} words, {len(asset_map)} audio files)")

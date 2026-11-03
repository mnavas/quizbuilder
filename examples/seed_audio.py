#!/usr/bin/env python3
"""
Seed a spelling-bee test into a running QuizBuilder instance.

For each word it builds one block containing:
  - block context: an audio clip of the word (so the taker hears it)
  - a short_text question: "Spell the word you hear" with the word as the correct answer

Audio is sourced from ``spelling_bee_audio/<word>.mp3`` when present, otherwise generated
with Google TTS (``pip install gtts``). All content is created through the public API using
the canonical stored shapes (short_text correct_answer is ``{"text": word}``).

Usage:
    pip install requests gtts            # gtts only needed if no local audio files
    python seed_audio.py --email admin@quizbuilder.local --password changeme
    python seed_audio.py --email ... --password ... --local-audio /path/to/mp3s
    python seed_audio.py --email ... --password ... --draw 10
"""

import argparse
import sys
from pathlib import Path

import requests

DEFAULT_WORDS = [
    "necessary", "rhythm", "conscience", "embarrass", "millennium",
    "privilege", "accommodate", "liaison", "maintenance", "occurrence",
    "perseverance", "questionnaire", "recommend", "separate", "vacuum",
]

AUDIO_DIR = Path(__file__).parent / "spelling_bee_audio"


def log(msg: str) -> None:
    print(msg, flush=True)


def ensure_audio(word: str, local_audio: Path | None) -> Path:
    """Return a path to an MP3 for the word, generating one with gTTS if needed."""
    search_dirs = [local_audio] if local_audio else [AUDIO_DIR]
    for d in search_dirs:
        candidate = d / f"{word}.mp3"
        if candidate.exists():
            return candidate

    # Fall back to generating one with gTTS into AUDIO_DIR.
    try:
        from gtts import gTTS
    except ImportError:
        log(f"  ✗ No audio for '{word}' and gTTS is not installed. Run: pip install gtts")
        sys.exit(1)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIO_DIR / f"{word}.mp3"
    log(f"  · generating audio for '{word}' with gTTS")
    gTTS(text=word, lang="en").save(str(out))
    return out


def doc(text: str) -> dict:
    """A minimal Tiptap document wrapping plain text."""
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed a spelling-bee test into QuizBuilder.")
    ap.add_argument("--api", default="http://localhost:8000/api/v1", help="API base URL")
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--title", default="Spelling Bee")
    ap.add_argument("--local-audio", type=Path, default=None, help="Folder of <word>.mp3 recordings to use instead of gTTS")
    ap.add_argument("--draw", type=int, default=None, help="If set, each taker gets this many random words (blocks)")
    ap.add_argument("--words", nargs="*", default=None, help="Override the default word list")
    args = ap.parse_args()

    words = args.words or DEFAULT_WORDS
    s = requests.Session()

    # 1. Authenticate
    log(f"Logging in as {args.email} …")
    r = s.post(f"{args.api}/auth/login", json={"email": args.email, "password": args.password})
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    # 2. For each word: upload audio, create a short_text question, build a block
    blocks = []
    for i, word in enumerate(words):
        log(f"[{i + 1}/{len(words)}] {word}")
        audio_path = ensure_audio(word, args.local_audio)
        with open(audio_path, "rb") as f:
            up = s.post(f"{args.api}/media", files={"file": (audio_path.name, f, "audio/mpeg")})
        up.raise_for_status()
        media_id = up.json()["id"]

        q = s.post(f"{args.api}/questions", json={
            "type": "short_text",
            "prompt": "Spell the word you hear.",
            "correct_answer": {"text": word},
            "points": 1,
            "tags": ["spelling"],
        })
        q.raise_for_status()
        question_id = q.json()["id"]

        blocks.append({
            "title": f"Round {i + 1}",
            "order": i,
            "context_json": {
                "type": "doc",
                "content": [{
                    "type": "audio",
                    "attrs": {"media_file_id": media_id, "mime_type": "audio/mpeg", "text": f"Round {i + 1}"},
                }],
            },
            "questions": [{"question_id": question_id, "order": 0}],
        })

    # 3. Create the test
    log("Creating the test …")
    payload = {
        "title": args.title,
        "description": "Listen to each word and spell it.",
        "mode": "async",
        "access": "open",
        "show_score": "at_end",
        "show_correct_answers": "at_end",
        "blocks": blocks,
    }
    if args.draw:
        payload["draw_count"] = args.draw

    t = s.post(f"{args.api}/tests", json=payload)
    t.raise_for_status()
    test = t.json()

    # 4. Publish
    pub = s.post(f"{args.api}/tests/{test['id']}/publish")
    pub.raise_for_status()
    link = pub.json().get("link_token")

    log("")
    log(f"✓ Created and published '{args.title}' with {len(blocks)} words.")
    if args.draw:
        log(f"  Each taker draws {args.draw} random word(s).")
    log(f"  Share code: {link}  (takers open /take/{link})")


if __name__ == "__main__":
    main()

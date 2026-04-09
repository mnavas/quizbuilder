"""
seed_audio.py — Generate audio files for spelling_bee.json words and import the test.

Each block gets a context_json with a real audio node (played above the question),
and a single short_text question where the taker types the word.

Requirements:
    pip install gtts requests

Usage:
    python seed_audio.py --email admin@quizbee.com --password yourpassword
    python seed_audio.py --email admin@quizbee.com --password admin --api http://localhost:8000/api/v1
    python seed_audio.py --email admin@quizbee.com --password yourpassword --draw 5
"""

import argparse
import json
import os
import sys
import tempfile

import requests

# ── Word list ─────────────────────────────────────────────────────────────────
# Full word list for the spelling bee competition.
# Pass --words to override with a custom comma-separated list at runtime.

DEFAULT_WORDS = [
    "Bears", "Canal", "Clear", "Taste", "Flair", "Gulls", "Heart", "Honey", "Music", "Pools",
    "Pumas", "Ruins", "Savor", "Skies", "Spice", "Colour", "Animal", "Apogee", "Heritage", "Barley",
    "Brands", "Bridge", "Vendors", "Condor", "Drinks", "Flavor", "Forest", "Fusion", "Gentle", "Hotels",
    "Houses", "Lagoon", "Lilies", "Llamas", "Lupine", "Metals", "Wetlands", "Quench", "Refuge", "Renown",
    "Scenic", "Serene", "Served", "Spices", "Stalls", "Tapirs", "Thirst", "Traded", "Crafted", "Bargain",
    "Culture", "Dessert", "Facades", "Farming", "Fitness", "Flowers", "Gallery", "Fountains", "Pathways", "Immerse",
    "Objects", "Orchids", "Pastries", "Pyramid", "Rabbits", "Springs", "Streets", "Landscape", "Velvety", "Altitude",
    "Artisans", "Balanced", "Bleached", "Charming", "Colonial", "Colourful", "Convents", "Costumes", "Majestic", "National",
    "Panorama", "Plantain", "Plateaus", "Restored", "Richness", "Valerian", "Benchmark", "Displayed", "Education", "Guardians",
    "Intensity", "Nightlife", "Preserved", "Sugarcane", "Sweetness", "Testimony", "Balconyway", "Comparable", "Emblematic", "Experience",
    "Gastronomy", "Guesthouse", "Indigenous", "Caffeinated", "Cobblestone", "Festivities", "Handicrafts", "Hypothermal", "Inhabitants", "Extraordinary",
    "Picturesque", "Processions", "Supermarket", "Therapeutic", "Floriculture", "Performance", "Complementary", "Environmental", "Sustainability", "Traditionalism"
]

EXPLANATIONS: dict[str, str] = {}  # No pre-written explanations for this word list

EXAMPLE_JSON = os.path.join(os.path.dirname(__file__), "spelling_bee.json")
DEFAULT_LOCAL_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "spelling_bee_audio")


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(api: str, email: str, password: str) -> str:
    res = requests.post(f"{api}/auth/login", json={"email": email, "password": password})
    res.raise_for_status()
    token = res.json().get("access_token")
    if not token:
        print("Login failed — check credentials.")
        sys.exit(1)
    print(f"✓ Logged in as {email}")
    return token


# ── Audio generation & upload ─────────────────────────────────────────────────

def upload_audio(api: str, token: str, word: str, local_audio_dir: str | None = None) -> dict:
    """Upload an MP3 for word to /media. Uses a local file if found, otherwise generates with gTTS."""
    local_dir = local_audio_dir or DEFAULT_LOCAL_AUDIO_DIR
    local_path = os.path.join(local_dir, f"{word.lower()}.mp3")

    if os.path.isfile(local_path):
        print(f"  Using local file: {word} …", end=" ", flush=True)
        with open(local_path, "rb") as f:
            res = requests.post(
                f"{api}/media",
                files={"file": (f"{word.lower()}.mp3", f, "audio/mpeg")},
                headers={"Authorization": f"Bearer {token}"},
            )
        res.raise_for_status()
        media = res.json()
        print(f"✓ id={media['id']}")
        return media

    print(f"  Generating audio: {word} …", end=" ", flush=True)
    try:
        from gtts import gTTS
    except ImportError:
        print("gtts not installed. Run: pip install gtts")
        sys.exit(1)

    tts = gTTS(text=word, lang="en", slow=True)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    tts.save(tmp)

    with open(tmp, "rb") as f:
        res = requests.post(
            f"{api}/media",
            files={"file": (f"{word.lower()}.mp3", f, "audio/mpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
    os.unlink(tmp)
    res.raise_for_status()
    media = res.json()
    print(f"✓ id={media['id']} (gTTS)")
    return media


# ── Test JSON builder ─────────────────────────────────────────────────────────

def build_test_json(words: list[str], media_map: dict[str, str], draw: int | None) -> dict:
    """
    Build the test payload using the new block-context model:
      - Each block has context_json with a single audio node (the word recording)
      - Each block has one short_text question (type the word)
    draw_count is in terms of blocks, so draw=5 means 5 random rounds per attempt.
    """
    with open(EXAMPLE_JSON) as f:
        base = json.load(f)

    blocks = []
    for i, word in enumerate(words):
        media_id = media_map.get(word)
        explanation = EXPLANATIONS.get(
            word.lower(),
            f"{word} — Practice spelling this word carefully.",
        )

        # Audio node in context_json — rendered above the question in the taker UI
        context_json = {
            "type": "doc",
            "content": [
                {
                    "type": "audio",
                    "attrs": {
                        "media_file_id": media_id,
                        "mime_type": "audio/mpeg",
                        "text": word,  # fallback for TTS if media_file_id is missing
                    },
                }
            ],
        } if media_id else None

        block = {
            "title": f"Round {i + 1}",
            "order": i,
            "context_json": context_json,
            "questions": [
                {
                    "type": "short_text",
                    "prompt_json": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Type the word you just heard:"}],
                            }
                        ],
                    },
                    "options_json": None,
                    "correct_answer": {"text": word.lower()},
                    "explanation_json": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": explanation}],
                            }
                        ],
                    },
                    "media_ref": None,
                    "points": 1,
                    "tags": ["spelling-bee"],
                }
            ],
        }
        blocks.append(block)

    n = len(words)
    draw_count = draw if (draw and draw < n) else None

    description_parts = [f"{n} rounds"]
    if draw_count:
        description_parts.append(f"drawing {draw_count} random rounds per attempt")
    description_parts.append("Audio uses real recordings generated by gTTS.")

    return {
        "quizbee_version": "1.0",
        "description": "Spelling Bee with real audio recordings. " + " ".join(description_parts),
        "test": {
            **{k: v for k, v in base["test"].items() if k != "blocks"},
            "title": base["test"].get("title", "Spelling Bee"),
            "draw_count": draw_count,
            "blocks": blocks,
        },
    }


# ── Import ────────────────────────────────────────────────────────────────────

def import_test(api: str, token: str, test_json: dict) -> dict:
    res = requests.post(
        f"{api}/tests/import",
        json=test_json,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    res.raise_for_status()
    return res.json()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed spelling bee audio and import test")
    parser.add_argument("--api", default="http://localhost:8000/api/v1", help="API base URL")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument(
        "--words",
        default="",
        help="Comma-separated word list (default: the 10 words in spelling_bee.json)",
    )
    parser.add_argument(
        "--draw",
        type=int,
        default=None,
        help="draw_count: number of random rounds per attempt (default: all rounds, fixed sequence)",
    )
    parser.add_argument(
        "--local-audio",
        default=None,
        metavar="DIR",
        help=f"Directory of pre-recorded MP3s (default: {DEFAULT_LOCAL_AUDIO_DIR}). "
             "Files must be named <word>.mp3 (lowercase). Missing files fall back to gTTS.",
    )
    args = parser.parse_args()

    words = [w.strip() for w in args.words.split(",") if w.strip()] if args.words else DEFAULT_WORDS
    print(f"Words: {len(words)} — {', '.join(words)}")

    if args.draw and args.draw >= len(words):
        print(f"Warning: --draw {args.draw} >= word count {len(words)}, ignoring draw_count.")
        args.draw = None

    token = login(args.api, args.email, args.password)

    print(f"\nUploading {len(words)} audio file(s) …")
    media_map: dict[str, str] = {}
    for word in words:
        media = upload_audio(args.api, token, word, local_audio_dir=args.local_audio)
        media_map[word] = media["id"]

    print("\nBuilding test JSON …")
    test_json = build_test_json(words, media_map, args.draw)

    print("Importing test …")
    result = import_test(args.api, token, test_json)
    print(f"✓ Test created: \"{result['title']}\" (id={result['id']})")

    draw_info = f"  draw_count: {test_json['test']['draw_count']} random rounds per attempt" if test_json["test"]["draw_count"] else "  Fixed sequence (all rounds)"
    print(draw_info)
    print(f"\nPublish it in the web UI at http://localhost:3000/tests")


if __name__ == "__main__":
    main()

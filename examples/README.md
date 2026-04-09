# Quizbee — Example Tests

Ready-to-import examples for the Quizbee admin UI.

## Examples at a glance

| File | Type | Blocks | draw_count | What it demonstrates |
|---|---|---|---|---|
| `driving_theory.json` | JSON | 20 × 1 question | 15 blocks | Block-level random draw |
| `reading_comprehension.json` | JSON | 1 block, 5 questions | — | Shared passage as block context |
| `math_quiz.json` | JSON | 2 blocks, 5 questions | — | KaTeX formula rendering |
| `spelling_bee.json` | JSON | 10 rounds | 5 blocks | Block context audio (browser TTS) |
| `spelling_bee.zip` | ZIP + audio | 10 rounds | 5 blocks | Block context audio (real recordings) |

---

## How to import

Go to **Tests → ↑ Import** and select any file. Both `.json` and `.zip` are accepted.

The test is created as a draft — publish it to make it available to takers.

---

## Spelling Bee — three ways

The spelling bee comes in three forms depending on what you need:

### 1. `spelling_bee.json` — browser speech (no files needed)

Import the JSON file. Each round plays the word using the browser's built-in text-to-speech. Works everywhere, no setup.

### 2. `spelling_bee.zip` — real audio recordings (drag and drop)

Import the ZIP file. Same test, but each round plays a real MP3 recording instead of browser TTS. The audio files are bundled inside — just import and it works.

This is the recommended way for a polished experience without any technical setup.

### 3. `seed_audio.py` — developer tool (full 120-word list)

Generates audio for the full 120-word competition list and imports via the API. For developers or admins comfortable with the terminal.

By default it looks for pre-recorded MP3s in `examples/spelling_bee_audio/` (files named `<word>.mp3`, lowercase). Any missing file falls back to gTTS synthesis.

```bash
# Use local MP3s from examples/spelling_bee_audio/ (no gTTS needed if all files present)
pip install requests
python seed_audio.py --email admin@quizbee.com --password yourpassword

# Point to a different folder of recordings
python seed_audio.py --email admin@quizbee.com --password yourpassword --local-audio /path/to/mp3s

# Generate everything with gTTS (no local files at all)
pip install gtts requests
python seed_audio.py --email admin@quizbee.com --password yourpassword --local-audio /nonexistent

# Draw N random rounds per attempt
python seed_audio.py --email admin@quizbee.com --password yourpassword --draw 10
```

---

## Driving Theory

20 blocks × 1 multiple-choice question each. Covers road signs, rules, speed limits, motorway driving, safety, parking, vehicle checks, fatigue, and distractions.

`draw_count: 15` — each attempt draws 15 random blocks. Passing score: 80%.

---

## Reading Comprehension

TOEFL/academic style. The passage lives in `context_json` on the block and is shown above all questions. Includes multiple choice, multiple select, and one open-answer question (flagged for manual review after submission).

---

## Math Quiz

Demonstrates KaTeX formula rendering. Prompts and answer options use standard LaTeX (`$...$` inline, `$$...$$` block).

---

## How tests with media are bundled (ZIP format)

A `.zip` import contains a `test.json` and an `assets/` folder:

```
spelling_bee.zip
├── test.json          ← test structure with media_file_id references
└── assets/
    ├── bears.mp3
    ├── canal.mp3
    └── ...
```

The server re-uploads every asset and rewrites all references — the imported test works as if the files were uploaded manually.

---

## Block context (`context_json`)

Blocks can carry shared content rendered above all their questions — a passage, audio clip, image, or video. The spelling bee uses audio; reading comprehension uses a text passage.

```json
{
  "title": "Round 1",
  "context_json": {
    "type": "doc",
    "content": [{ "type": "audio", "attrs": { "media_file_id": "bears", "mime_type": "audio/mpeg", "text": "Bears" } }]
  },
  "questions": [{ "type": "short_text", "correct_answer": { "text": "bears" }, ... }]
}
```

When `media_file_id` is null or absent, the `text` attribute is spoken by browser TTS as a fallback.

---

## Random draw (`draw_count`)

When set, `draw_count` draws that many **blocks** at random per attempt. All questions inside a drawn block are included — keeping context and questions together.

`driving_theory.json`: 20 blocks of 1 question → draws 15 per attempt.
`spelling_bee.json`: 10 rounds → draws 5 per attempt.

---

## Format reference

```json
{
  "quizbee_version": "1.0",
  "test": {
    "title": "...",
    "draw_count": null,
    "blocks": [
      {
        "title": "...",
        "order": 0,
        "context_json": null,
        "questions": [
          {
            "type": "multiple_choice",
            "prompt_json": { "type": "doc", "content": [...] },
            "options_json": [{ "id": "a", "content_json": {...} }, ...],
            "correct_answer": "a",
            "points": 1,
            "tags": []
          }
        ]
      }
    ]
  }
}
```

Question types: `multiple_choice`, `multiple_select`, `true_false`, `short_text`, `long_text`

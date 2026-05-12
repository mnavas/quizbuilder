# Question Types

## Supported Types

### Auto-scored

| Type | Description |
|---|---|
| `multiple_choice` | One correct option from a list |
| `multiple_select` | One or more correct options (all-or-nothing scoring) |
| `true_false` | Binary choice |
| `short_text` | Free-text auto-scored when `correct_answer.text` is set (e.g. spelling) |

### Manual review required

| Type | Description |
|---|---|
| `short_text` | When no `correct_answer` is set — flagged for reviewer grading |
| `long_text` | Essay / free-text — always manual review |
| `file_upload` | Taker uploads a file — always manual review |

### Informational (no answer collected)

| Type | Description |
|---|---|
| `audio_prompt` | An audio clip played before related questions (listening comprehension) |
| `video_prompt` | A video shown before related questions |
| `passage` | A rich-text reading passage |
| `divider` | Visual section separator |

---

## Data Encoding per Type

### `multiple_choice`

```json
// options_json
[
  {"id": "a", "content_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "London"}]}]}},
  {"id": "b", "content_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Paris"}]}]}},
  {"id": "c", "content_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Berlin"}]}]}}
]

// correct_answer — plain string matching the option id
"b"

// taker answer (value_json)
{"selected": "b"}
```

---

### `multiple_select`

```json
// options_json — same list format as multiple_choice

// correct_answer — plain array of correct option ids
["a", "c"]

// taker answer (value_json)
{"selected": ["a", "c"]}
```

Scoring is **all-or-nothing**: the selected set must exactly match the correct set for any points to be awarded.

---

### `true_false`

```json
// options_json — typically two options: true / false (or Yes / No, etc.)
[
  {"id": "true",  "content_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "True"}]}]}},
  {"id": "false", "content_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "False"}]}]}}
]

// correct_answer — plain string "true" or "false"
"true"

// taker answer (value_json)
{"selected": "true"}
```

Comparison is case-insensitive string equality.

---

### `short_text`

```json
// correct_answer — when auto-scoring is desired
{"text": "photosynthesis"}

// correct_answer — when manual review is required
null

// taker answer (value_json)
{"text": "Photosynthesis"}
```

Auto-scoring compares after lowercasing and trimming both sides. If `correct_answer` is null, the answer is flagged `needs_review = true`.

---

### `long_text`

```json
// correct_answer — always null (no auto-scoring)
null

// taker answer (value_json)
{"text": "The industrial revolution began in Britain because..."}
```

Always flagged `needs_review = true`. A reviewer assigns a manual score (0 to max points).

---

### `audio_prompt` / `video_prompt`

These are informational question types. The media file is stored as the `options_json` (a media ref, not a list):

```json
// options_json (media ref, not an array)
{
  "media_file_id": "c3f2a1b4-...",
  "mime_type": "audio/mpeg"
}

// correct_answer — null (no answer collected)
null
```

The taker UI renders a native `<audio>` or `<video>` player. No answer input is shown. Scoring engine returns `(0, False)` — zero points, no review needed.

---

## Block Context vs. Question Audio

There are two ways audio/video appears in a test:

| Where | How | Use case |
|---|---|---|
| **Block `context_json`** | Tiptap doc with a single `audio` or `video` node | Shared clip for all questions in the block (spelling bee round, listening passage) |
| **`audio_prompt` question** | `options_json` media ref | A clip that stands alone as its own "question" (no answer expected) |

Both are served via the same `/api/v1/media/{id}` endpoint with HTTP range support.

---

## Adding a Question via API

```bash
# multiple_choice — correct_answer is a plain string matching the option id
curl -X POST http://localhost:8000/api/v1/questions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "multiple_choice",
    "prompt": "What is the capital of France?",
    "options": [
      {"id": "a", "text": "London"},
      {"id": "b", "text": "Paris"},
      {"id": "c", "text": "Berlin"}
    ],
    "correct_answer": "b",
    "points": 1
  }'

# short_text with auto-scoring — correct_answer is {"text": "..."}
curl -X POST http://localhost:8000/api/v1/questions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "short_text",
    "prompt": "Spell the word: [audio plays]",
    "correct_answer": {"text": "necessary"},
    "points": 1
  }'
```

---

## Import / Export JSON format

When importing or exporting tests as `.json` files, `options_json` uses the same `{id, content_json}` structure. The `correct_answer` is always a **plain string** (for MC/TF), **plain array** (for MS), or **`{text:"..."}` object** (for short_text).

The import endpoint also accepts a simplified format where `options_json` is a flat list of strings and `correct_answer` is the matching option text — it will be normalised automatically:

```json
{
  "type": "multiple_choice",
  "prompt_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Capital of France?"}]}]},
  "options_json": ["London", "Paris", "Berlin"],
  "correct_answer": "Paris",
  "points": 1
}
```

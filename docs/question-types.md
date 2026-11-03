# Question Types

## Supported Types

### Auto-scored

| Type | Description |
|---|---|
| `multiple_choice` | One correct option from a list |
| `multiple_select` | One or more correct options (all-or-nothing or partial scoring) |
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

Scoring is controlled per-test by `multiple_select_scoring`: `all_or_nothing` (default — the selected set must exactly match the correct set) or `partial` (each correct selection earns a proportional share of the points; wrong selections carry no penalty). See [scoring.md](scoring.md).

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

> The payload below uses the **Simple format** (plain `prompt`, `options` as `{id, text}`).
> The server wraps the text into the Internal format before storing. See
> [Two authoring formats](#two-authoring-formats-simple-vs-internal) below.

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

## Two authoring formats: Simple vs Internal

QuizBuilder accepts quiz content in **two shapes**. Write endpoints (`POST /questions`,
`POST /tests/import`, …) normalise the lenient *Simple* format into the strict *Internal*
format before storing. Every read endpoint (`GET …`, `/export`) returns **only** the Internal
format, so round-tripping an export always yields Internal JSON.

| | **Simple format** | **Internal (canonical) format** |
|---|---|---|
| Intended author | Humans, AI-generated JSON, CSV | The app itself (DB + wire representation) |
| Prompt | `prompt` — plain string | `prompt_json` — Tiptap doc |
| Explanation | `explanation` — plain string | `explanation_json` — Tiptap doc |
| Options | `options` / `options_json` — flat `["A","B"]` **or** `[{id,text}]` | `options_json` — `[{id, content_json}]` |
| Option ids | optional (auto-assigned `A,B,C…`) | required, explicit |
| `correct_answer` (MC/TF) | option **text** *or* id | option **id** (plain string) |
| `correct_answer` (MS) | array of texts *or* ids | array of **ids** |
| `correct_answer` (short_text) | plain string *or* `{text:…}` | `{text:…}` (or `null` for manual review) |
| Audio/video media | `media_ref` object | `options_json` holds the media-ref object |
| Blocks | optional — a flat `questions[]` becomes one block | required — `test → blocks[] → questions[]` |
| Envelope | optional — bare dict or `{test:{…}}` | `{quizbuilder_version, exported_at, test:{…}}` |

### How normalisation works

On import, each field is converted to Internal form:

1. `prompt` → `prompt_json`; `explanation` → `explanation_json` (plain text is wrapped in a
   `doc › paragraph › text` Tiptap node).
2. `options` as a **flat string list** → `[{id, content_json}]`, with ids assigned from
   `A, B, C … P` (then `17, 18, …`). `options` as `[{id, text}]` keeps the given ids and wraps `text`.
3. `correct_answer` given as option **text** is matched against the option list and replaced with
   the resulting **id**. (This only works if option texts are unique and match exactly.)
4. `short_text` `correct_answer` given as a plain string → `{text: "…"}`.
5. Audio/video `media_ref` is restored into `options_json` when no `options` are present.

### Simple-format example (accepted by `POST /tests/import`)

```json
{
  "type": "multiple_choice",
  "prompt": "Capital of France?",
  "options": ["London", "Paris", "Berlin"],
  "correct_answer": "Paris",
  "points": 1
}
```

### Equivalent Internal format (as stored and re-exported)

```json
{
  "type": "multiple_choice",
  "prompt_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Capital of France?"}]}]},
  "options_json": [
    {"id": "A", "content_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "London"}]}]}},
    {"id": "B", "content_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Paris"}]}]}},
    {"id": "C", "content_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Berlin"}]}]}}
  ],
  "correct_answer": "B",
  "points": 1
}
```

### Caveats

- **Option-id casing.** The canonical per-type examples above use lowercase ids (`a`, `b`, `true`),
  while auto-assigned ids from a flat string list are **uppercase** (`A`, `B`, `C`). Both are valid —
  `correct_answer` must simply match whichever id actually results.
- **`POST /tests/import` is more forgiving than `POST /questions`.** The import path resolves
  `correct_answer` from option text, auto-assigns ids, and wraps a short_text string into `{text:…}`.
  The questions endpoint does **none** of these: it requires explicit `{id, text}` options and stores
  `correct_answer` verbatim (so short_text must already be `{text:…}`).
- **Flat string lists are tests-import only.** `POST /questions` requires `options` as `[{id, text}]`.

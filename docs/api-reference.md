# API Reference

Base URL: `/api/v1`

Interactive docs: `http://localhost:8000/docs`

## Authentication

All admin endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Obtain tokens via `POST /auth/login`. Taker endpoints (`/sessions/take/...`, `/sessions/{id}/...`) are public — no token required.

---

## Auth

### `POST /auth/login`
```json
// Request
{"email": "admin@example.com", "password": "secret"}

// Response
{
  "access_token": "...",
  "refresh_token": "...",
  "force_password_reset": false
}
```

### `POST /auth/refresh`
```json
// Request
{"refresh_token": "..."}

// Response
{"access_token": "...", "refresh_token": "..."}
```

### `GET /auth/me`
Requires authentication. Returns the current user: `{id, email, role, tenant_id, force_password_reset}`.

### `POST /auth/change-password`
Requires authentication.
```json
{"current_password": "...", "new_password": "..."}
```

---

## Questions

All endpoints require `admin` or `manager` role.

### `GET /questions`
List all questions in the tenant's question bank.

Query params: `type`, `tag`, `search`

### `GET /questions/{id}`
Get a single question.

### `POST /questions`
Create a question.
```json
{
  "type": "multiple_choice",
  "prompt": "Plain text prompt (auto-wrapped)",
  "prompt_json": { ... },        // OR: Tiptap JSON (takes priority)
  "options": [{"id": "a", "text": "Option A"}, ...],
  "correct_answer": "a",          // plain option id (MC/TF); ["a","c"] for MS; {"text":"…"} for short_text
  "explanation": "Plain text explanation",
  "explanation_json": { ... },   // OR: Tiptap JSON
  "points": 1,
  "tags": ["grammar"]
}
```

For `audio_prompt` / `video_prompt`, use `media_ref` instead of `options`:
```json
{
  "type": "audio_prompt",
  "prompt": "Listen and answer",
  "media_ref": {"media_file_id": "<uuid>", "mime_type": "audio/mpeg"}
}
```

### `PUT /questions/{id}`
Update a question. Same body as POST.

### `DELETE /questions/{id}`
Soft-delete a question.

### `POST /questions/bulk-import`
Import a list of questions from a `questions.json` file.
```json
// Accepts bare list or envelope
{"quizbuilder_version": "1.0", "questions": [...]}
```
Response: `{"created": 12, "question_ids": ["...", ...]}`

---

## Tests

All endpoints require `admin` or `manager` role.

### `GET /tests`
List all tests (excludes deleted).

### `GET /tests/{id}`
Get test details including all blocks and embedded question data.

### `POST /tests`
Create a test.
```json
{
  "title": "Mid-term Exam",
  "mode": "async",
  "access": "open",
  "time_limit_minutes": 60,
  "show_score": "at_end",
  "show_correct_answers": "never",
  "draw_count": null,
  "blocks": [
    {
      "title": "Section 1",
      "order": 0,
      "context_json": null,
      "questions": [
        {"question_id": "<uuid>", "order": 0}
      ]
    }
  ]
}
```

### `PUT /tests/{id}`
Update a test. Replaces all blocks atomically.

### `POST /tests/{id}/publish`
Generate a `link_token` and set `published_at`. The test becomes accessible to takers. Requires at least one question.

### `DELETE /tests/{id}`
Soft-delete a test. Requires `admin` role.

### `POST /tests/{id}/clone`
Duplicate a test and all its blocks as a new **unpublished** test. Questions are cloned as new independent copies, so editing the clone never affects the original.

### `GET /tests/{id}/access-codes`
List all access codes for a test (newest first). Each item: `{id, code, max_uses, use_count, remaining, revoked, created_at}` (`remaining` is null when `max_uses` is null).

### `POST /tests/{id}/access-codes`
Generate one or more access codes for a `code`-gated test (e.g. one per student).
```json
{
  "count": 30,          // 1–500 (default 1)
  "max_uses": 1,        // uses allowed per code; null = unlimited
  "prefix": "CLASS-"    // optional; sanitised to [A-Z0-9-_], max 16 chars
}
```
Codes use an unambiguous alphabet (no `0/O`, `1/I/L`). Returns the list of created codes (201).

### `DELETE /tests/{id}/access-codes/{code_id}`
Revoke a code. Soft — the row is kept (sets `revoked = true`) so session history referencing it stays intact.

### `GET /tests/{id}/preview`
Return full test content with question details for admin preview — no session created.

### `GET /tests/{id}/export`
Export a test.
- No media → returns `quizbuilder_<slug>.json`
- Has media → returns `quizbuilder_<slug>.zip` containing `test.json` + `assets/`

### `POST /tests/import`
Import a test from a QuizBuilder JSON export (request body). Accepts both the **Simple** and
**Internal** content formats, with or without the `{test:{…}}` envelope, and a flat top-level
`questions[]` list (wrapped into one block). See
[question-types.md › Two authoring formats](question-types.md#two-authoring-formats-simple-vs-internal).

### `POST /tests/import-bundle`
Import a test from a ZIP bundle (`multipart/form-data`, field `file`). Re-uploads all media assets and remaps IDs.

### `POST /tests/import-csv`
Create a test from a CSV file (`multipart/form-data`, field `file`). The filename (without extension) becomes the test title. Expected header row: `type, prompt, options, correct_answer, points, tags, block`.
- `options` — pipe-separated for choice types, e.g. `Paris|London|Berlin`
- `correct_answer` — single value for MC/TF, comma-separated for MS (`A,C`), plain text for short_text
- `block` — optional block title to group rows (all rows share one block if omitted)

### `GET /tests/{id}/export-questions`
Export just the questions as a portable `questions.json` file.

### `GET /tests/{id}/practice-bundle`
Public endpoint — returns the test as a practice-bundle JSON for the mobile app. Only available when `practice_enabled` is `true` on the test (404 otherwise).

---

## Sessions (Taker API — no auth required)

### `POST /sessions/take/{link_token}`
Start a new session. Returns all questions for the session.

**Access control** (enforced by the test's `access` setting):
- `open` — public; `taker_email` optional.
- `registered` — requires a valid Bearer token; the session is bound to that user. Returns **401** without one.
- `code` — requires `access_code` in the body matching a non-revoked code with uses remaining. Returns **403** otherwise; a successful start consumes one use.

**Attempt limits:** when `allow_multiple_attempts` is false (or `max_attempts` is reached) a repeat start returns **403**. Attempts are counted per logged-in user, per access code, or per `taker_email` — fully anonymous `open` takers (no email) are not limited.

```json
// Request
{
  "taker_email": "student@example.com",   // optional
  "access_code": "ABC123"                  // required only when access == "code"
}

// Response
{
  "id": "<session_uuid>",
  "test_id": "...",
  "status": "active",
  "expires_at": "2026-04-08T15:00:00Z",
  "show_correct_answers": "at_end",
  "questions": [
    {
      "id": "...", "type": "multiple_choice",
      "prompt_json": {...}, "options_json": [...],
      "points": 1, "order": 0,
      "block_title": "Section 1",
      "context_json": null
    }
  ]
}
```

### `PUT /sessions/{id}/answers/{question_id}`
Save or update a taker's answer (auto-save). Returns 204 No Content.
```json
{"value": {"selected": "b"}}
```

### `POST /sessions/{id}/check/{question_id}`
Get immediate feedback for one answer. Only available when `show_correct_answers == "per_question"`.
```json
// Request
{"value": {"selected": "b"}}

// Response
{
  "is_correct": true,
  "needs_review": false,
  "auto_score": 1,
  "correct_answer": "b",
  "options_json": [...]
}
```

### `POST /sessions/{id}/submit`
Submit the session. Runs scoring. Returns the full result.

### `GET /sessions/{id}/result`
Re-fetch the result of a submitted session.

---

## Results

Requires `admin` or `manager` role.

### `GET /results`
List sessions across all tests, with filtering.
Query params: `test_id`, `status`, `review_status`

### `GET /results/export/csv`
Download submitted sessions for one test as CSV. Query param: `test_id` (required). Columns: `session_id, taker_email, status, review_status, score_pct, passed, started_at, submitted_at`.

### `GET /results/{session_id}`
Get a single session result with all answers.

---

## Media

### `POST /media`
Upload a file. Requires `admin` or `manager` role. `multipart/form-data`, field `file`.

Allowed types: `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/svg+xml`, `audio/mpeg`, `audio/ogg`, `audio/wav`, `audio/webm`, `video/mp4`, `video/webm`, `video/ogg`

Max size: 50 MB

```json
// Response
{
  "id": "<uuid>",
  "filename": "word.mp3",
  "mime_type": "audio/mpeg",
  "size_bytes": 24601,
  "url": "/api/v1/media/<uuid>"
}
```

### `GET /media/{id}`
Serve a media file. Public endpoint (no auth). Supports HTTP range requests for audio/video streaming.

---

## Users

Requires `admin` role.

### `GET /users` — list users
### `POST /users` — create user
### `DELETE /users/{id}` — deactivate user (sets `is_active = false`)

---

## Live Game

Real-time competitive games are served under `/api/v1/live/`. See [live-game.md](live-game.md) for the full endpoint set, state machine, and scoring formula.

---

## Health

### `GET /health`
Returns `{"status": "ok"}`. Used by Docker Compose health checks.

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
  "correct_answer": {"value": "a"},
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
{"quizbee_version": "1.0", "questions": [...]}
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

### `GET /tests/{id}/preview`
Return full test content with question details for admin preview — no session created.

### `GET /tests/{id}/export`
Export a test.
- No media → returns `quizbee_<slug>.json`
- Has media → returns `quizbee_<slug>.zip` containing `test.json` + `assets/`

### `POST /tests/import`
Import a test from a Quizbee JSON export (request body).

### `POST /tests/import-bundle`
Import a test from a ZIP bundle (`multipart/form-data`, field `file`). Re-uploads all media assets and remaps IDs.

### `GET /tests/{id}/export-questions`
Export just the questions as a portable `questions.json` file.

---

## Sessions (Taker API — no auth required)

### `POST /sessions/take/{link_token}`
Start a new session. Returns all questions for the session.
```json
// Request
{"taker_email": "student@example.com"}  // optional

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
  "correct_answer": {"value": "b"},
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
### `PUT /users/{id}` — update user
### `DELETE /users/{id}` — deactivate user

---

## Health

### `GET /health`
Returns `{"status": "ok"}`. Used by Docker Compose health checks.

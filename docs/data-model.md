# Data Model

## Entity Relationship

```
Tenant
  └── User (staff/admin accounts)
  └── Question (reusable question bank)
  └── MediaFile (uploaded images, audio, video)
  └── Test
        └── TestBlock (ordered sections)
              └── TestBlockQuestion (ordered question references)
              └── context_json (shared audio/passage for the block)
        └── AccessCode (for code-gated tests)
        └── Session (one taker attempt)
              └── SessionQuestion (the exact question draw + order)
              └── Answer (one response per question)
        └── LiveGame (a Kahoot-style live session)
              └── LivePlayer (one joined player)
              └── LiveAnswer (one player's answer to one question)
```

---

## Models

### Tenant

Top-level isolation unit. Every row in every table belongs to exactly one tenant.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | string | Display name |
| `slug` | string | Unique — used for routing/identification |
| `settings_json` | JSONB | Reserved for tenant-level config |
| `created_at` | timestamp | |

---

### User

Admin and staff accounts. Takers are **not** Users — they are identified only by an optional email on the Session.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `tenant_id` | UUID FK | |
| `email` | string | Unique across the instance |
| `password_hash` | string | bcrypt |
| `role` | string | `admin` \| `manager` \| `reviewer` \| `candidate` |
| `is_active` | bool | Inactive users cannot log in |
| `force_password_reset` | bool | Set on admin-created accounts; must change password on first login |
| `last_login` | timestamp | |

---

### Question

A reusable question that can appear in multiple tests.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `tenant_id` | UUID FK | |
| `type` | string | See [question-types.md](question-types.md) |
| `prompt_json` | JSONB | Tiptap rich-text document |
| `options_json` | JSONB | Null, list of options, or media ref — see below |
| `correct_answer` | JSONB | Type-dependent encoding — see below |
| `explanation_json` | JSONB | Tiptap doc shown in practice mode after answering |
| `points` | int | Default 1 |
| `tags` | JSONB (string[]) | Used for filtering in the question bank |
| `deleted_at` | timestamp | Soft delete — never hard deleted to preserve answer history |

#### `options_json` encoding

| Question type | Value |
|---|---|
| `multiple_choice`, `multiple_select`, `true_false` | `[{"id": "a", "content_json": <tiptap>}, ...]` |
| `audio_prompt`, `video_prompt` | `{"media_file_id": "<uuid>", "mime_type": "audio/mpeg"}` |
| All other types | `null` |

#### `correct_answer` encoding

| Question type | Value |
|---|---|
| `multiple_choice`, `true_false` | `"option_id"` — plain string matching the option's `id` field |
| `multiple_select` | `["a", "b"]` — plain array of correct option ids |
| `short_text` (e.g. spelling) | `{"text": "expected word"}` |
| `long_text`, `file_upload` | `null` → requires manual review |
| Informational types | `null` |

---

### Test

A published assessment.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `tenant_id` | UUID FK | |
| `title` | string | |
| `description` | text | |
| `mode` | string | `async` \| `sync` |
| `access` | string | `open` \| `registered` \| `code` |
| `time_limit_minutes` | int | Null = untimed |
| `allow_multiple_attempts` | bool | |
| `max_attempts` | int | Null = unlimited |
| `randomize_questions` | bool | Shuffle question order per session |
| `randomize_options` | bool | Shuffle option order per session |
| `show_score` | string | `at_end` \| `never` |
| `show_correct_answers` | string | `never` \| `at_end` \| `per_question` \| `after_review` |
| `passing_score_pct` | int | Null = no pass/fail threshold |
| `multiple_select_scoring` | string | `all_or_nothing` \| `partial` |
| `draw_count` | int | If set, randomly draw this many **blocks** per session |
| `link_token` | string | Generated on publish; included in the shareable taker URL |
| `published_at` | timestamp | Null = draft (not accessible to takers) |
| `deleted_at` | timestamp | Soft delete |

---

### TestBlock

An ordered section within a test. Holds an ordered set of questions and optional shared context.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `test_id` | UUID FK | |
| `order` | int | Zero-based position within the test |
| `title` | string | Displayed above the block; used for TTS if no audio file is set |
| `context_json` | JSONB | Tiptap doc OR pure audio/video node — see below |
| `instructions_json` | JSONB | Reserved — not yet rendered in the taker UI |

#### `context_json` shapes

```json
// Audio file (spelling bee, listening comprehension)
{
  "type": "doc",
  "content": [{
    "type": "audio",
    "attrs": { "media_file_id": "<uuid>", "mime_type": "audio/mpeg", "text": "Block title" }
  }]
}

// Video file
{
  "type": "doc",
  "content": [{
    "type": "video",
    "attrs": { "media_file_id": "<uuid>", "mime_type": "video/mp4", "text": "Block title" }
  }]
}

// Reading passage / rich text
{ "type": "doc", "content": [...tiptap nodes...] }
```

When `context_json` is `null` and the block has a title, the taker UI falls back to browser TTS.

---

### AccessCode

A code issued for a `code`-gated test. Takers supply a valid code to start a session.

`POST /sessions/take/{link_token}` enforces this: when `test.access == "code"` the request must
include a matching, non-revoked code with uses remaining, or it is rejected with 403. A successful
start sets the session's `access_code_id` and increments `use_count`.

> **Status:** all three access modes are end-to-end. `open` is public. `code` — admins generate/revoke
> codes from the **🔑 Access codes** action on the Tests page (backed by the `/tests/{id}/access-codes`
> endpoints, see [api-reference.md](api-reference.md)); the take page collects a code. `registered` —
> the take page prompts the taker to log in and starts the session with their own token; accounts are
> provisioned by an admin with the `candidate` role via `POST /users`. A taker's login token is used
> only for the start request and is not persisted as a cookie (the take page is a shared device).

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `test_id` | UUID FK | |
| `code` | string | Unique across the instance; matched case-insensitively |
| `max_uses` | int | Null = unlimited |
| `use_count` | int | Incremented on each session **start** (a started attempt consumes a use) |
| `revoked` | bool | Revoked codes cannot be used |
| `created_by` | UUID FK | User who generated the code |
| `created_at` | timestamp | |

---

### Session

One attempt by one taker on one test.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `test_id` | UUID FK | |
| `taker_id` | UUID FK | Null for anonymous takers |
| `taker_email` | string | Provided voluntarily by the taker at start |
| `access_code_id` | UUID FK | Set when access=code |
| `status` | string | `active` \| `submitted` \| `expired` |
| `started_at` | timestamp | |
| `submitted_at` | timestamp | |
| `expires_at` | timestamp | Null = untimed; set from `time_limit_minutes` |
| `score_pct` | int | 0–100; null until submitted and scored |
| `passed` | bool | Null if no passing threshold, or if awaiting review |
| `review_status` | string | `auto_scored` \| `awaiting_review` \| `reviewed` |

---

### SessionQuestion

Records the exact question draw and option order for a session. This makes draw_count results reproducible and auditable.

| Column | Type | Description |
|---|---|---|
| `session_id` | UUID FK | |
| `question_id` | UUID FK | |
| `order` | int | Position in this session's question list |
| `options_order_json` | JSONB | Shuffled option ID list; null if not randomized |

---

### Answer

One taker response to one question.

| Column | Type | Description |
|---|---|---|
| `session_id` | UUID FK | |
| `question_id` | UUID FK | |
| `value_json` | JSONB | Taker's response — see encoding below |
| `auto_score` | int | Set by scoring engine; null for open types |
| `manual_score` | int | Set by reviewer; null until reviewed |
| `needs_review` | bool | True for open types or short_text without a correct_answer |
| `reviewer_comment` | text | Optional reviewer note |
| `reviewed_at` | timestamp | |
| `saved_at` | timestamp | Updated on every auto-save |

#### `value_json` encoding

| Question type | Value |
|---|---|
| `multiple_choice`, `true_false` | `{"selected": "option_id"}` |
| `multiple_select` | `{"selected": ["a", "c"]}` |
| `short_text`, `long_text` | `{"text": "typed answer"}` |

---

### MediaFile

An uploaded binary asset stored on the local filesystem.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Also used as the asset filename in ZIP exports |
| `tenant_id` | UUID FK | |
| `filename` | string | Original upload filename |
| `mime_type` | string | Detected from upload |
| `size_bytes` | int | |
| `storage_path` | string | Relative to `MEDIA_ROOT`: `{tenant_id}/{media_id}/{filename}` |

Files are served at `/api/v1/media/{id}` with HTTP range support for audio/video streaming.

---

## Live Game models

Power the real-time competitive mode (see [live-game.md](live-game.md)). Only `multiple_choice` and
`true_false` questions participate; the eligible question ids are resolved and frozen at game creation.

### LiveGame

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `test_id` | UUID FK | Source test |
| `tenant_id` | UUID FK | |
| `created_by` | UUID FK | Host user |
| `pin` | string(6) | Join PIN (indexed) |
| `state` | string | `waiting` \| `question_active` \| `question_closed` \| `finished` |
| `current_question_index` | int | `-1` while waiting; 0-based once started |
| `current_question_started_at` | timestamp | Server time the current question opened — basis for speed scoring |
| `time_limit_seconds` | int | Per-question countdown (default 20; clamped 5–120) |
| `question_ids_json` | JSONB (string[]) | Ordered eligible question ids, frozen at creation |
| `created_at` | timestamp | |

### LivePlayer

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `game_id` | UUID FK | |
| `nickname` | string | Display name |
| `avatar_color` | string(7) | Hex color, default `#f59e0b` |
| `total_score` | int | Running cumulative score |
| `joined_at` | timestamp | |

### LiveAnswer

One player's answer to one question. Unique on `(game_id, player_id, question_id)` — resubmitting replaces it.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | |
| `game_id` | UUID FK | |
| `player_id` | UUID FK | |
| `question_id` | UUID FK | |
| `value_json` | JSONB | `{"selected": "option_id"}` |
| `answered_at` | timestamp | Server receive time |
| `time_ms` | int | Response time used in the speed-score formula |
| `points_earned` | int | Points awarded for this answer |
| `is_correct` | bool | |

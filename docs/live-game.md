# Live Game

QuizBuilder Live turns any multiple-choice or true/false test into a real-time competitive trivia game. Players join from any browser — no app or account required. The host controls the pace question by question; speed-weighted scoring keeps every round competitive.

---

## Prerequisites

- Any published or unpublished test with at least one `multiple_choice` or `true_false` question.
- Questions of other types (`short_text`, `long_text`, etc.) are silently skipped during the live game.
- The host must be authenticated (admin, manager, or reviewer role).

---

## State Machine

A live game progresses through these states in order:

```
waiting → question_active → question_closed → ... → finished
```

| State | Description |
|---|---|
| `waiting` | Lobby — players can join; host has not started yet |
| `question_active` | A question is visible; the countdown timer is running |
| `question_closed` | Timer expired or host closed the question; correct answer and scores are revealed |
| `finished` | All questions have been shown; final leaderboard is available |

---

## Scoring

For each correct answer:

```
points = question.points × 1000 × (0.5 + 0.5 × (1 − time_ms / time_limit_ms))
```

- **Maximum:** `question.points × 1000` (instant answer)
- **Minimum:** `question.points × 500` (answered in the last millisecond)
- **Wrong answer or no answer:** 0 points

Points are calculated server-side using the server-recorded receive time — client clock skew and network latency do not affect fairness.

---

## Launching from the Web UI

1. Go to **Tests** and find your test.
2. Open the **⋮ Actions** menu and click **🎮 Launch Live Game**.
3. A host control page opens in a new tab with a 6-digit PIN and a QR code.
4. Players join by navigating to `/live-join` on their device and entering the PIN, or by scanning the QR code.
5. When all players have joined, click **Start Game**.
6. After each question, click **Close Question** to reveal results, then **Next Question** to advance.
7. After the last question, click **Show Final Results** for the podium screen.

---

## API Reference

All live game endpoints are under `/api/v1/live/`.

### Create a game

```http
POST /api/v1/live/games
Authorization: Bearer <token>
Content-Type: application/json

{
  "test_id": "<uuid>",
  "time_limit_seconds": 20
}
```

- `time_limit_seconds` defaults to `20`; clamped to the range `[5, 120]`.
- Returns a game object including the `id`, `pin`, and initial state `waiting`.

**Response:**
```json
{
  "id": "...",
  "pin": "123456",
  "state": "waiting",
  "test_id": "...",
  "time_limit_seconds": 20
}
```

---

### Join a game (player)

Public endpoint — no authentication required.

```http
POST /api/v1/live/join
Content-Type: application/json

{
  "pin": "123456",
  "nickname": "Alice"
}
```

**Response:**
```json
{
  "player_id": "<uuid>",
  "game_id": "<uuid>",
  "nickname": "Alice"
}
```

Save `player_id` — it is required to submit answers and retrieve results.

---

### Poll game state

Public endpoint. Poll at ~1 s intervals to drive the player and host UIs.

```http
GET /api/v1/live/games/{game_id}/state
```

**Response shape:**
```json
{
  "state": "question_active",
  "current_question": {
    "id": "...",
    "prompt_json": { ... },
    "options_json": [
      { "id": "a", "content_json": { ... } },
      { "id": "b", "content_json": { ... } }
    ],
    "points": 1,
    "time_limit_seconds": 20,
    "started_at": "<ISO timestamp>"
  },
  "players": [
    { "player_id": "...", "nickname": "Alice", "score": 0 }
  ],
  "question_index": 0,
  "question_total": 10
}
```

When `state` is `question_closed` the response also includes `correct_answer` and per-player scores for the closed question. When `state` is `finished` it includes the final leaderboard sorted by score descending.

---

### Submit an answer (player)

Public endpoint. Must be submitted while the question is `question_active`.

```http
POST /api/v1/live/games/{game_id}/answer
Content-Type: application/json

{
  "player_id": "<player_id from join>",
  "value": { "selected": "b" }
}
```

- `value.selected` is the option `id` (e.g. `"a"`, `"b"`, `"true"`, `"false"`).
- Submitting twice for the same question replaces the earlier answer.
- Returns HTTP 200 with `{"ok": true}`.

---

### Advance to next question (host)

Authenticated endpoint. Moves from `question_closed` → `question_active` (next question), or from `question_closed` → `finished` after the last question.

Also callable during `waiting` to start the game (moves to `question_active` for the first question).

```http
POST /api/v1/live/games/{game_id}/next
Authorization: Bearer <token>
```

---

### Close the current question (host)

Authenticated endpoint. Moves from `question_active` → `question_closed`. The correct answer is revealed and scores are computed. If the timer has already expired the server auto-closes the question; this call is idempotent.

```http
POST /api/v1/live/games/{game_id}/close
Authorization: Bearer <token>
```

---

### Get a player's result for a question

Public endpoint. Returns the player's answer, correctness, and points earned for a specific question.

```http
GET /api/v1/live/games/{game_id}/player/{player_id}/result?question_id={question_id}
```

**Response:**
```json
{
  "player_id": "...",
  "question_id": "...",
  "value": { "selected": "b" },
  "correct": true,
  "points_earned": 876,
  "cumulative_score": 1742,
  "rank": 3
}
```

---

## Typical Client Flow

### Host client

```
1. POST /live/games        → get game_id, pin
2. Display PIN + QR code
3. Poll GET /live/games/{id}/state (every 1 s) → show player list
4. POST /live/games/{id}/next   → start game
5. Poll state → show current question + countdown
6. POST /live/games/{id}/close  → reveal answer + leaderboard
7. POST /live/games/{id}/next   → next question (or → finished)
8. Repeat 5–7 until state = finished
```

### Player client

```
1. POST /live/join                          → get player_id
2. Poll GET /live/games/{id}/state (every 1 s) → wait in lobby
3. When state = question_active → display question
4. POST /live/games/{id}/answer             → submit answer
5. When state = question_closed → show result + rank
6. Repeat 3–5 until state = finished
```

---

## Constraints

| Limit | Value |
|---|---|
| Minimum time limit | 5 seconds |
| Maximum time limit | 120 seconds |
| Supported question types | `multiple_choice`, `true_false` |
| Questions skipped | `multiple_select`, `short_text`, `long_text`, `file_upload`, and informational types |

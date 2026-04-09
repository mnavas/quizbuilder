# Scoring

## How Scoring Works

Scoring runs when a taker submits a session (`POST /sessions/{id}/submit`). The engine scores every question in the session and computes a final percentage.

```
score_pct = round(earned_points / total_points * 100)
passed    = score_pct >= passing_score_pct  (if a threshold is set)
```

---

## Per-type Scoring Logic

| Type | Logic | `needs_review` |
|---|---|---|
| `multiple_choice` | `selected == correct_answer.value` → full points | No |
| `multiple_select` | Selected set must **exactly match** correct set → full points (all-or-nothing) | No |
| `true_false` | Case-insensitive string match → full points | No |
| `short_text` (with `correct_answer.text`) | Lowercase + trim comparison → full points | No |
| `short_text` (no `correct_answer`) | Score = null | Yes |
| `long_text` | Score = null | Yes |
| `file_upload` | Score = null | Yes |
| `audio_prompt`, `video_prompt`, `passage`, `divider` | Score = 0, no points expected | No |
| Unknown type | Score = null | Yes |

**All-or-nothing for `multiple_select`:** partial credit is not yet supported. The selected set must be identical to the correct set; any missing or extra selection scores zero.

---

## Review Status

After scoring, the session's `review_status` is set:

| Value | Meaning |
|---|---|
| `auto_scored` | All answers machine-graded; `score_pct` and `passed` are final |
| `awaiting_review` | At least one answer has `needs_review = true`; score is not final |
| `reviewed` | A reviewer has graded all open answers; `score_pct` is now final |

When any answer `needs_review`, `score_pct` and `passed` remain `null` on the session until a reviewer finishes grading.

---

## Per-question Feedback (`show_correct_answers: per_question`)

When a test is configured with `show_correct_answers: per_question`, the taker can request immediate feedback after answering each question **before submitting**:

```
POST /sessions/{session_id}/check/{question_id}
Body: {"value": {...}}
```

Response:
```json
{
  "is_correct": true,
  "needs_review": false,
  "auto_score": 1,
  "correct_answer": {"value": "b"},
  "options_json": [...]
}
```

`is_correct` is `null` when the question requires manual review. This endpoint is only available when `show_correct_answers == "per_question"` — it returns 403 otherwise.

---

## Correct Answer Disclosure Policy

The `show_correct_answers` field on Test controls when `correct_answer` and `options_json` are included in result responses:

| Value | When answers are revealed |
|---|---|
| `never` | Never — not included in any response |
| `at_end` | On the result screen after submission |
| `per_question` | On each `/check` call during the session, and also at end |
| `after_review` | Only after `review_status == "reviewed"` (**Phase 5.1 — not yet fully implemented**) |

The `show_score` field controls whether `score_pct` and `passed` are included:

| Value | When score is revealed |
|---|---|
| `at_end` | On the result screen |
| `never` | Score is hidden from the taker (admin/reviewer still sees it) |

---

## Missing Answers

If a taker did not answer a question (navigated past it without saving), no `Answer` row exists. The scoring engine creates a blank `Answer` with `auto_score = 0` for that question, so it counts as a zero in the total.

---

## Manual Review Flow (Current State)

1. Taker submits → `review_status = "awaiting_review"` if any open answers exist.
2. Admin/reviewer opens the session in the Results view.
3. Reviewer reads the answer, assigns a score (0 – max_points), optionally adds a comment.
4. When all open answers are graded → `review_status = "reviewed"`, `score_pct` is computed.

> **Note:** The full reviewer UI (Phase 5.1) is planned but not yet built. The `review_status` field and `manual_score` / `reviewer_comment` columns exist and are ready.

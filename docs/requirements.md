# Quizbee — Product Requirements
**Version:** 0.1
**Last Updated:** 2026-04-04
**Stage:** Pre-development

---

## 1. Product Overview

Quizbee is an online assessment platform for creating, administering, and scoring rich tests. It supports two primary modes: structured exams (sync or async, with submission tracking and grading) and practice (self-paced, offline-capable, with flashcard and partner modes). Content is rich — formulas, images, audio, video, and styled text — to support academic exams, psychological evaluations, language proficiency tests, and more.

---

## 2. Core Concepts

| Concept | Definition |
|---|---|
| **Test** | A collection of questions with delivery configuration (mode, timing, access, scoring) |
| **Question** | A single item with prompt, rich content, answer options, and optional correct answer |
| **Pool** | A named set of questions from which questions are drawn randomly |
| **Block** | A section of a test, each optionally backed by its own pool |
| **Session** | One attempt by one taker on one test |
| **Submission** | The completed answers from a session |
| **Taker** | The person completing a test — may be anonymous, registered, or code-identified |
| **Reviewer** | A user who reads and grades open-answer questions manually |

---

## 3. Test Delivery Modes

### 3.1 Sync Mode
All takers start at the same time. The test creator sets a start time; takers join and wait for the countdown. Timer starts simultaneously for all. Useful for proctored exams, classroom assessments, and competitive quizzes.

- Countdown shown to all joined takers before start
- Creator can see how many takers have joined
- Late joiners can be allowed or blocked (configurable)
- Takers see remaining time relative to the global start, not their own join time

### 3.2 Async Mode
Takers start at their own time within an optional availability window. Useful for online course assessments, certification exams, and self-scheduled evaluations.

- Optional open/close date window
- Each taker's timer starts when they open the test
- Multiple attempts configurable (once, N times, unlimited)

---

## 4. Access Options

| Access Type | Description |
|---|---|
| **Open link** | Any person with the URL can take the test. Submission is anonymous unless taker provides name/email voluntarily. |
| **Registered user** | Taker must log in. Submission is tied to their account. |
| **Generated code** | A unique code is issued per taker. Code can be single-use or multi-use. Submission is tied to the code. Creator generates codes in bulk (e.g. for a class of 50). |

Attempt limits are configured per test, not per access type. A code can be used once or multiple times independently of whether the taker is registered.

---

## 5. Question Types

### 5.1 Objective (auto-scored)

| Type | Description |
|---|---|
| `multiple_choice` | One correct answer from a list of options |
| `multiple_select` | One or more correct answers from a list |
| `true_false` | Binary choice |
| `ordering` | Arrange items in correct sequence |
| `matching` | Match left-column items to right-column items |
| `fill_in_the_blank` | One or more blanks within a sentence or paragraph |
| `numeric` | Exact number or number within a tolerance range |

### 5.2 Open (manual review)

| Type | Description |
|---|---|
| `short_text` | Free-text answer, one line |
| `long_text` | Free-text answer, multi-line (essay) |
| `file_upload` | Taker uploads a file as their answer |

### 5.3 Informational (no answer)

| Type | Description |
|---|---|
| `passage` | Rich text shown as reading material before related questions |
| `audio_prompt` | Audio clip played before related questions (e.g. listening comprehension) |
| `video_prompt` | Video shown before related questions |
| `divider` | Visual separator between sections |

---

## 6. Rich Content

All question prompts, answer options, and passage blocks support:

| Content Type | Notes |
|---|---|
| **Rich text** | Bold, italic, underline, lists, headings, inline code |
| **Font size control** | Set font size per block — for kanji, large-print, or accessibility needs |
| **Formulas** | LaTeX inline and block math (`$...$` and `$$...$$`) rendered via KaTeX |
| **Images** | Upload or embed; with alt text |
| **Audio** | Upload MP3/M4A; inline player |
| **Video** | Upload MP4 or embed YouTube/Vimeo URL; inline player |
| **Tables** | Formatted data tables within prompts |

---

## 7. Question Structure

```
question:
  id
  type
  prompt                  ← rich content block
  options[]               ← for choice types; each option is a rich content block
  correct_answer          ← optional; omit for open questions and hidden-answer tests
  explanation             ← shown after answer in practice mode (optional)
  points                  ← default 1
  tags[]                  ← for pool filtering
  assets[]                ← images/audio/video files attached to this question
```

---

## 8. Test Structure

```
test:
  title
  description
  mode                    ← sync | async
  access                  ← open | registered | code
  allow_multiple_attempts ← bool (async only)
  max_attempts            ← int or null
  time_limit_minutes      ← null = untimed
  time_per_question       ← null = not per-question
  show_score              ← at_end | never | per_question
  show_correct_answers    ← at_end | never | per_question | after_review
  passing_score_pct       ← optional
  randomize_questions     ← bool
  blocks[]:
    title                 ← optional block heading
    instructions          ← rich text shown at block start
    questions[]           ← fixed list, OR:
    pool_id               ← draw randomly from this pool
    pool_draw_count       ← how many to draw from the pool
```

---

## 9. Scoring

### 9.1 Auto-scoring
Objective question types are scored automatically on submission. Score = sum of points for correct answers.

### 9.2 Manual review
Open questions (`short_text`, `long_text`, `file_upload`) are flagged for manual review. A reviewer opens the submission, reads the answer, and assigns a score (0 to max points for that question). The session result is finalized only after all open questions are reviewed.

### 9.3 Score display options
- `at_end` — taker sees total score after submitting
- `never` — score not shown to taker (reviewer/admin sees it)
- `per_question` — taker sees if each answer was correct as they go (practice-friendly)

### 9.4 Answer display options
- `at_end` — correct answers shown after submission
- `never` — answers not revealed to taker
- `per_question` — correct answer shown immediately after answering each question
- `after_review` — shown only after manual review is complete

---

## 10. Practice Mode

Practice mode is a separate delivery context — not a graded session. Designed for self-study and exam preparation.

### 10.1 Access
- Taker scans a QR code or visits a link
- Downloads the test as a `.json` bundle + asset files
- Can practice offline after download

### 10.2 Study modes

| Mode | How it works |
|---|---|
| **Flashcard** | Question shown; taker taps to reveal answer. Self-rated (correct / incorrect). No input required. |
| **Self-check** | Taker answers; immediately told if correct. Explanation shown if configured. |
| **Partner mode** | Partner's screen shows the correct answer as soon as the question appears. Taker answers verbally; partner confirms. Useful for language drills and oral exam prep. |

### 10.3 Creator controls for practice
- `show_answer_in_practice` — per question: always / never / only_if_available
- `show_explanation_in_practice` — bool
- Open questions without a correct answer set skip correctness feedback; flashcard just reveals a reference answer if provided.

### 10.4 Progress tracking (offline)
- Practice sessions stored locally on device
- Progress synced to server when online (optional — taker may use fully anonymously offline)

---

## 11. Result Review & Grading Interface

For administrators and reviewers:

- View all sessions for a test: taker identity (or code), score, status (complete / awaiting review / reviewed), date
- Open a session: see all questions, taker's answer, auto-score or assigned score
- For open questions: text input to assign score, optional comment
- Bulk export: CSV of all sessions with scores
- Filter by: pass/fail, awaiting review, date range, access code

---

## 12. Non-Functional Requirements

| Requirement | Detail |
|---|---|
| Self-hosted | Deploys via Docker Compose; no external cloud dependency |
| Multi-tenancy | Multiple organizations on one instance, fully isolated |
| Data sovereignty | No candidate data leaves the host infrastructure |
| Asset storage | Images/audio/video stored in Docker volume, served locally |
| Concurrent sessions | Handle sync mode with many simultaneous takers |
| Mobile practice | React Native app for offline practice; QR download of test bundle |

---

## 13. Out of Scope (MVP)

- Live proctoring / webcam monitoring
- LMS integrations (SCORM, LTI)
- AI-generated questions
- Leaderboards / gamification
- iOS app (Android practice app first)

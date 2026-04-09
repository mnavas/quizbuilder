# Quizbee — Overview

Quizbee is a self-hosted, multi-tenant online assessment platform. Admins build tests with rich content (text, formulas, images, audio, video), publish them via a shareable link, and collect graded results — without any data leaving the host infrastructure.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    Docker Compose                      │
│                                                        │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────┐  │
│   │  web :3000   │   │  api :8000   │   │  db      │  │
│   │  Next.js 14  │──▶│  FastAPI     │──▶│ Postgres │  │
│   │  App Router  │   │  SQLAlchemy  │   │ 15       │  │
│   └──────────────┘   └──────┬───────┘   └──────────┘  │
│                             │                          │
│                      ┌──────▼───────┐                  │
│                      │ media volume │                  │
│                      │ /data/media  │                  │
│                      └──────────────┘                  │
└────────────────────────────────────────────────────────┘
```

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), React, Tailwind CSS, Tiptap |
| API | FastAPI, SQLAlchemy (async), Alembic, Pydantic |
| Database | PostgreSQL 15 |
| Auth | JWT (HS256) — access token (60 min) + refresh token (30 days) |
| Storage | Local filesystem via Docker volume; served with HTTP range support |
| Deployment | Docker Compose |

---

## Key Concepts

| Concept | Description |
|---|---|
| **Tenant** | Top-level isolation unit. All data is scoped to a tenant. |
| **Test** | A collection of ordered Blocks, each holding Questions. |
| **Block** | A group of questions with optional shared context (passage, audio, image). |
| **Question** | A reusable item — prompt, options, correct answer, explanation, points. |
| **Session** | One attempt by one taker on one test. |
| **Answer** | A taker's response to one question within a session. |
| **MediaFile** | An uploaded image, audio, or video file stored on the local volume. |

---

## User Roles

| Role | Capabilities |
|---|---|
| `admin` | Full access — manage users, tests, questions, results |
| `manager` | Create/edit tests and questions; view results |
| `reviewer` | View and grade open answers |
| `candidate` | Reserved for future registered taker accounts |

Takers (people who take tests) are **not** user accounts. They are identified only by an optional email on the Session.

---

## Documentation Index

| File | Contents |
|---|---|
| [getting-started.md](getting-started.md) | Installation, environment variables, first run |
| [data-model.md](data-model.md) | Database models and relationships |
| [question-types.md](question-types.md) | All question types and encoding conventions |
| [scoring.md](scoring.md) | Scoring engine, review flow, result disclosure |
| [api-reference.md](api-reference.md) | All API endpoints |
| [deployment.md](deployment.md) | Production setup, nginx, volumes |

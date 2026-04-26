# Getting Started

## Prerequisites

- **Docker Desktop** — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- **Python 3** — [python.org/downloads](https://www.python.org/downloads/)
- Git

On Linux all three can be installed in one step:
```bash
curl -fsSL https://get.docker.com | sh && sudo apt install python3 git
```

---

## Quick Start

```bash
git clone https://github.com/mnavas/quizbuilder.git
cd quizbuilder

# Mac / Linux
./quizbuilder install

# Windows
quizbuilder install
```

The installer sets up passwords, generates a secret key, and starts the server automatically.

The web UI is available at `http://localhost:3000`.
The API is available at `http://localhost:8000/api/v1`.
Interactive API docs are at `http://localhost:8000/docs`.

---

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Required
DB_PASSWORD=change_this_strong_password
SECRET_KEY=change_this_64_char_random_string

# Admin account created on first startup
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=change_this_password

# Frontend → API URL (what the browser uses to call the API)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# CORS: comma-separated list of allowed origins
ALLOWED_ORIGINS=http://localhost:3000
```

> **Never commit `.env` to version control.**
> Generate `SECRET_KEY` with: `python3 -c "import secrets; print(secrets.token_hex(32))"`

### All API environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string (set by compose) |
| `SECRET_KEY` | — | JWT signing key — must be secret and stable |
| `MEDIA_ROOT` | `/data/media` | Filesystem path for uploaded files |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS origins |
| `ADMIN_EMAIL` | `admin@quizbuilder.local` | Seeded admin email |
| `ADMIN_PASSWORD` | `changeme` | Seeded admin password — **change immediately** |

---

## First Run

On startup, the API automatically:
1. Runs `alembic upgrade head` to apply all database migrations.
2. Creates the default admin account if it does not exist.

Log in at `http://localhost:3000/login` with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` you set.

---

## Development Setup

### API (Python)

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start a local Postgres instance
docker run -d --name quizbuilder-db \
  -e POSTGRES_DB=quizbuilder \
  -e POSTGRES_USER=quizbuilder \
  -e POSTGRES_PASSWORD=devpassword \
  -p 5432:5432 postgres:15-alpine

# Create .env in api/
DATABASE_URL=postgresql+asyncpg://quizbuilder:devpassword@localhost/quizbuilder
SECRET_KEY=dev_secret_key_not_for_production
MEDIA_ROOT=./media

# Run migrations and start
alembic upgrade head
uvicorn app.main:app --reload
```

### Web (Node.js)

```bash
cd web
npm install

# Create .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

npm run dev
```

---

## Seeding Test Data

The `examples/` folder contains scripts to populate a spelling-bee test with audio:

```bash
cd examples
pip install requests gtts   # gtts only needed if no local audio files

# Use pre-downloaded MP3s from examples/spelling_bee_audio/ (no gTTS needed if all present)
python seed_audio.py --email admin@quizbuilder.local --password changeme

# Or point to a folder of your own recordings
python seed_audio.py \
  --email admin@quizbuilder.local \
  --password changeme \
  --local-audio /path/to/mp3s

# Random draw: each taker gets 10 random rounds
python seed_audio.py \
  --email admin@quizbuilder.local \
  --password changeme \
  --draw 10
```

After seeding, publish the test from the web UI at `http://localhost:3000/tests`.

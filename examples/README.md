# QuizBuilder Examples

Ready-to-use samples for importing content and seeding a demo test. All files use the
formats described in [../docs/question-types.md](../docs/question-types.md).

## Import files

| File | Import via | Format |
|---|---|---|
| `simple_format_quiz.json` | `POST /tests/import` | **Simple** — plain `prompt`, flat `options`, `correct_answer` by option text |
| `internal_format_quiz.json` | `POST /tests/import` | **Internal** — canonical Tiptap `*_json`, `{id, content_json}` options, id-based `correct_answer` |
| `questions_bulk.json` | `POST /questions/bulk-import` | Simple question list (no test) |
| `quiz.csv` | `POST /tests/import-csv` | CSV (`type,prompt,options,correct_answer,points,tags,block`) |

Both JSON formats import to the **same** stored result — the Simple format is normalised on the
way in (see *Two authoring formats* in the question-types doc).

### Import from the command line

```bash
# Log in and grab a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@quizbuilder.local","password":"changeme"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Import a test (Simple format)
curl -X POST http://localhost:8000/api/v1/tests/import \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  --data @simple_format_quiz.json

# Import questions in bulk
curl -X POST http://localhost:8000/api/v1/questions/bulk-import \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  --data @questions_bulk.json

# Import a test from CSV
curl -X POST http://localhost:8000/api/v1/tests/import-csv \
  -H "Authorization: Bearer $TOKEN" -F 'file=@quiz.csv'
```

## Spelling-bee seed script

`seed_audio.py` builds a complete spelling-bee test: one block per word, each with an audio clip
of the word and a `short_text` question to spell it. Audio is taken from
`spelling_bee_audio/<word>.mp3` if present, otherwise generated with Google TTS.

```bash
pip install requests gtts            # gtts only needed if no local audio files

# Generate audio (if missing), upload, and create the test
python seed_audio.py --email admin@quizbuilder.local --password changeme

# Use your own recordings instead of gTTS
python seed_audio.py --email admin@quizbuilder.local --password changeme \
  --local-audio /path/to/mp3s

# Random draw: each taker gets 10 random words
python seed_audio.py --email admin@quizbuilder.local --password changeme --draw 10
```

After seeding, publish/share the test from the web UI at `http://localhost:3000/tests`.

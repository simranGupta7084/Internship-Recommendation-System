# Internship Recommendation System

![CI](![CI](https://github.com/simranGupta7084/Internship-Recommendation-System/actions/workflows/ci.yml/badge.svg))

A backend service that matches a student's resume/skills against live internship
listings pulled from Jooble, Adzuna, and USAJOBS, using sentence-embedding
similarity rather than keyword search.

## Why embeddings, not keyword search
An earlier version used TF-IDF + cosine similarity, which only scores overlap
in exact wording — "built REST APIs" and "developed backend services" would
look unrelated. Switching to `sentence-transformers` (`all-MiniLM-L6-v2`)
embeddings matches on *meaning*, which is the difference between a
recommendation engine and a search box.

## Architecture
```
data_loader.py   -> pulls raw listings from Jooble / Adzuna / USAJOBS
database.py      -> MongoDB persistence (internships + user profiles), pagination
matcher.py       -> embedding generation + cosine similarity ranking, skill extraction
auth.py          -> API-key guard for write/admin routes
app.py           -> Flask API (routes below)
tests/           -> pytest suite (mongomock-backed, no real DB or network needed)
```

Listing refresh is intentionally decoupled from the recommendation request —
`/recommend` reads from MongoDB, `/admin/refresh` pulls new data from the
external APIs. Combining them made every recommendation depend on three
synchronous external HTTP calls on the request path.

## Tech stack
Python · Flask · MongoDB · sentence-transformers · pytest · mongomock · Docker · GitHub Actions

## API
| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | liveness + cached listing count |
| POST | `/admin/refresh` | API key | pull fresh listings into MongoDB |
| GET | `/internships` | none | paginated search of cached listings |
| POST | `/profile` | API key | create/update a user profile |
| GET | `/profile/<name>` | none | fetch a saved profile |
| POST | `/recommend` | none, rate-limited | rank cached listings against resume text or a saved profile |
| GET | `/skill-gap/<name>` | none | most in-demand skills the profile is missing |

## Setup (local, no Docker)
```bash
git clone <this-repo>
cd internship-recommender
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # fill in your own MongoDB URI, API_KEY, and job-API keys
pytest                 # 18 tests, runs offline against mongomock
python app.py
```

## Setup (Docker)
```bash
cp .env.example .env
docker compose up --build
```

## Testing
`pytest` runs the full suite against an in-memory MongoDB (`mongomock`) and a
mocked embedding function — no real database, no model download, no network
required. CI runs this on every push via `.github/workflows/ci.yml`.

## Security notes
- No credentials are hardcoded; all secrets load from `.env` (gitignored).
- `/admin/refresh` and `/profile` writes require an `X-API-Key` header
  matching the `API_KEY` env var; the server fails closed if `API_KEY` isn't set.
- `/recommend` and `/admin/refresh` are rate-limited (Flask-Limiter).

## Known limitations / next steps
- API-key auth is per-deployment, not per-user — fine for a single-owner
  project, not for multi-tenant use.
- Refresh is on-demand via the admin route; a scheduled job (APScheduler/cron)
  would be the production version.
- Skill extraction is a fixed keyword list, not NLP-based entity extraction.

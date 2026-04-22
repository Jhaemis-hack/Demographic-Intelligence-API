# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload

# Run tests
pytest test_main.py -v

# Run a single test
pytest test_main.py::test_health -v

# Health check
curl http://127.0.0.1:8000/health
```

Note: `test.py` is a **seed script** (not tests) — it reads `seed_profiles.json` and inserts records into MongoDB. Run it directly with `python test.py`.

## Architecture

This is a **FastAPI** demographic classification API. It accepts a name, calls three external services (genderize.io, agify.io, nationalize.io) concurrently, classifies the result, and persists it to MongoDB Atlas.

### Current route inventory (`main.py`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/` | Info |
| GET | `/health` | Health check |
| GET | `/api/profiles` | List/filter profiles — rate-limited 8/min per IP |
| GET | `/api/profiles/search` | Search by name (`?q=`) — **incomplete, references undefined `profile_id`** |

`POST /api/profiles` (create profile) is not yet implemented in `main.py`. The data transformation helpers in `config/model.py` and service files are ready for it.

### Request flow for listing profiles (`GET /api/profiles`)

Supports query filters: `gender`, `age_group`, `country_id`, `min_age`, `max_age`, `min_gender_probability`, `min_country_probability`. Supports `sort_by` (`age`, `created_at`, `gender_probability`), `order` (`asc`/`desc`), and pagination (`page`, `limit` 10–50).

### Directory layout

- `main.py` — app factory, lifespan (rate limiter), all route handlers
- `core/` — `config.py` (pydantic Settings from `.env`), `exceptions.py` (custom exception hierarchy), `error_handlers.py` (global FastAPI exception handlers)
- `services/` — `genderize_service.py` (only remaining service file), `http_client.py` (shared httpx AsyncClient, HTTP/2, 1.5s timeout)
- `config/` — `database.py` (MongoDB client), `schema.py` (Pydantic `profile` model), `model.py` (`extract_gender`, `create_profile`, `create_profile_list_item` transformers)
- `api/` — empty (placeholder for future router extraction)

### Key conventions

- External HTTP calls go through `services/http_client.py:safe_http_request()` — never call httpx directly.
- All service failures raise `ExternalServiceException` (→ 502). Input errors raise `BadRequestException` (400) or `UnprocessableException` (422).
- Age groupings: child ≤ 12, teenager 13–19, adult 20–59, senior 60+.
- Nationality is the country with the highest probability from the Nationalize response.
- IDs use `uuid.uuid7()` from the `uuid6` package.

## Environment

Requires a `.env` file at the repo root with all four keys:

```
GENDERIZE_API="https://api.genderize.io"
AGIFY_API="https://api.agify.io"
NATIONALIZE_API="https://api.nationalize.io"
MONGO_DB="<mongodb-atlas-connection-string>"
```

All four are loaded via `core/config.py` (pydantic `BaseSettings`). MongoDB database is `hng14_1`, collection is `users`.

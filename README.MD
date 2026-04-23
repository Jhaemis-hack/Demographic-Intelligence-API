# Demographic Intelligence API

A RESTful API built for Insighta Labs that stores demographic profiles and exposes advanced filtering, sorting, pagination, and natural-language querying for marketing, product, and growth analytics teams.

---

## Tech Stack

- Python 3.10+
- FastAPI
- MongoDB Atlas
- httpx (async HTTP with HTTP/2)
- SlowAPI (rate limiting)
- Uvicorn (ASGI server)

---

## Setup

### 1. Clone and create virtual environment

```bash
git clone <your-repo-url>
cd <your-project>
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
GENDERIZE_API="https://api.genderize.io"
AGIFY_API="https://api.agify.io"
NATIONALIZE_API="https://api.nationalize.io"
MONGO_DB="<your-mongodb-atlas-connection-string>"
```

### 4. Seed the database

```bash
python test.py
```

`test.py` reads `seed_profiles.json` and inserts 2026 profiles. Re-running it is safe — it uses `insert_many` without checking duplicates, so seed only once or clear the collection first.

---

## Running the Application

```bash
uvicorn main:app --reload
```

- Base URL: `http://127.0.0.1:8000`
- Interactive docs: `http://127.0.0.1:8000/docs`

---

## API Endpoints

### GET /health

```json
{ "status": "success", "message": "Ok" }
```

---

### GET /api/profiles

List profiles with optional filtering, sorting, and pagination.

**Query parameters:**

| Parameter               | Type   | Description                                      |
|-------------------------|--------|--------------------------------------------------|
| `gender`                | string | `male` or `female`                               |
| `age_group`             | string | `child`, `teenager`, `adult`, `senior`           |
| `country_id`            | string | ISO 2-letter code (e.g. `NG`, `KE`)              |
| `min_age`               | int    | Minimum age (inclusive)                          |
| `max_age`               | int    | Maximum age (inclusive)                          |
| `min_gender_probability`| float  | Minimum gender confidence score                  |
| `min_country_probability`| float | Minimum nationality confidence score             |
| `sort_by`               | string | `age`, `created_at`, or `gender_probability`     |
| `order`                 | string | `asc` or `desc`                                  |
| `page`                  | int    | Page number (default: 1)                         |
| `limit`                 | int    | Results per page (default: 10, max: 50)          |

All filters are combinable. Results match every condition passed.

**Example:**

```
GET /api/profiles?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc&page=1&limit=10
```

**Success response (200):**

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 142,
  "data": [
    {
      "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
      "name": "emmanuel",
      "gender": "male",
      "gender_probability": 0.99,
      "age": 34,
      "age_group": "adult",
      "country_id": "NG",
      "country_name": "Nigeria",
      "country_probability": 0.85,
      "created_at": "2026-04-01T12:00:00Z"
    }
  ]
}
```

Rate limit: 8 requests/minute per IP.

---

### GET /api/profiles/search

Query profiles using plain English. Pagination (`page`, `limit`) applies here too.

**Example:**

```
GET /api/profiles/search?q=young males from nigeria
GET /api/profiles/search?q=adult females above 30&page=2&limit=20
```

**Success response (200):** same structure as `GET /api/profiles`.

**Uninterpretable query (400):**

```json
{ "status": "error", "message": "Unable to interpret query" }
```

---

## Natural Language Parsing Approach

The parser is fully rule-based — no AI or LLMs. It uses a series of regex passes over the lowercased query string, each independently contributing to the MongoDB filter.

### Gender

Detected by keyword matching:

| Keywords matched                        | Filter applied       |
|-----------------------------------------|----------------------|
| `male`, `males`, `men`, `man`, `boy`, `boys` | `gender=male`   |
| `female`, `females`, `women`, `woman`, `girl`, `girls` | `gender=female` |
| Both sets present                       | No gender filter (both genders implied) |

### Age groups

If any of these words appear, the stored `age_group` field is filtered:

| Keywords                                   | Filter              |
|--------------------------------------------|---------------------|
| `child`, `children`, `kid`, `kids`         | `age_group=child`   |
| `teenager`, `teenagers`, `teen`, `teens`, `adolescent` | `age_group=teenager` |
| `adult`, `adults`                          | `age_group=adult`   |
| `senior`, `seniors`, `elderly`             | `age_group=senior`  |

### "Young" / "youth" (special case)

`young` and `youth` are **not** stored age groups. When detected (and no stored age group has already matched), they map to a numeric range: `age >= 16 AND age <= 24`.

### Numeric age constraints

| Pattern                                              | Filter            |
|------------------------------------------------------|-------------------|
| `above N`, `over N`, `older than N`, `at least N`, `more than N` | `age >= N` |
| `below N`, `under N`, `younger than N`, `at most N`, `less than N` | `age <= N` |
| `between N and M`                                    | `age >= N AND age <= M` (overrides above/below) |

Age group keywords and numeric constraints are independent and compose freely (e.g. `teenagers above 17` → `age_group=teenager AND age >= 17`).

### Country

The parser looks for the phrase `from <place>` or `in <place>` and strips any trailing age-stopper words (`above`, `below`, `over`, `under`, etc.).

The extracted text is matched against a built-in dictionary of ~120 country names, adjectives, and demonyms (e.g. `nigerian` → `NG`, `south africa` → `ZA`). Matching is longest-first to handle multi-word names correctly.

If the text doesn't match any dictionary entry, it falls back to a case-insensitive regex on the stored `country_name` field.

### How all parts compose

Each recognition step sets `recognized = True` independently. A query is considered interpretable if at least one part matched. All extracted filters are `AND`-ed together in the MongoDB query.

**Examples:**

| Query                                 | Filters applied                                         |
|---------------------------------------|---------------------------------------------------------|
| `young males`                         | `gender=male`, `age >= 16`, `age <= 24`                 |
| `females above 30`                    | `gender=female`, `age >= 30`                            |
| `people from angola`                  | `country_id=AO`                                         |
| `adult males from kenya`              | `gender=male`, `age_group=adult`, `country_id=KE`       |
| `male and female teenagers above 17`  | `age_group=teenager`, `age >= 17`                       |
| `seniors from nigeria below 80`       | `age_group=senior`, `country_id=NG`, `age <= 80`        |

---

## Parser Limitations

- **No spelling correction.** `nigeeria` or `femal` will not match.
- **No synonym expansion beyond the built-in list.** Unlisted countries, regions, or informal names (e.g. `naija`) return no country filter.
- **`young` conflicts with `adult`.** If both appear in the same query, `adult` takes the `age_group` slot and `young` is ignored.
- **Numeric age wins over `young`.** `young people above 30` applies `age >= 30` on top of the 16–24 range, which results in `age >= 16 AND age <= 24 AND age >= 30` — an empty result set.
- **No ordinal/relative time.** Phrases like `created last month` or `recent profiles` are not supported.
- **No multi-country queries.** `males from nigeria or ghana` is not handled; only the first matched country is extracted.
- **No negation.** `not from nigeria` or `non-adult` are not interpreted.
- **ISO codes in the query string are not parsed.** Use `GET /api/profiles?country_id=NG` for direct ISO lookups.

---

## Error Responses

All errors use this structure:

```json
{ "status": "error", "message": "<error message>" }
```

| Status | Trigger                                   |
|--------|-------------------------------------------|
| 400    | Missing or empty parameter                |
| 400    | Unable to interpret natural language query |
| 422    | Invalid parameter type                    |
| 429    | Rate limit exceeded (8 req/min per IP)    |
| 500    | Internal server error                     |
| 502    | External service failure                  |

---

## CORS

`Access-Control-Allow-Origin: *` is set on all responses.

---

## Classification Rules

**Age groups (assigned at profile creation time):**

| Age range | Group    |
|-----------|----------|
| 0–12      | child    |
| 13–19     | teenager |
| 20–59     | adult    |
| 60+       | senior   |

**Nationality:** the country with the highest probability from the Nationalize.io response.

---

## Author

James Kehinde

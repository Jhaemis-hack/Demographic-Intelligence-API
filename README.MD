# Classification API

A RESTful API built with FastAPI that accepts a name, calls three external APIs (Genderize, Agify, Nationalize) concurrently, classifies the result, stores it in MongoDB, and exposes endpoints to manage the data.

---

## Tech Stack

- Python 3.10+
- FastAPI
- MongoDB (Atlas)
- httpx (async HTTP with HTTP/2)
- SlowAPI (rate limiting)
- Uvicorn (ASGI server)

---

## Project Structure

```
.
├── main.py                    # App factory and all route handlers
├── core/
│   ├── config.py              # Pydantic settings (loads .env)
│   ├── exceptions.py          # Custom exception hierarchy
│   └── error_handlers.py      # Global FastAPI exception handlers
├── services/
│   ├── genderize_service.py
│   ├── agify_service.py
│   ├── nationalize_service.py
│   └── http_client.py         # Shared async HTTP client
├── config/
│   ├── database.py            # MongoDB connection
│   ├── schema.py              # Pydantic profile model
│   └── model.py               # Data transformation helpers
├── requirements.txt
└── .env
```

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <your-project>
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GENDERIZE_API="https://api.genderize.io"
AGIFY_API="https://api.agify.io"
NATIONALIZE_API="https://api.nationalize.io"
MONGO_DB="<your-mongodb-atlas-connection-string>"
```

---

## Running the Application

```bash
uvicorn main:app --reload
```

API base URL: `http://127.0.0.1:8000`  
Interactive docs: `http://127.0.0.1:8000/docs`

---

## API Endpoints

### POST /api/profiles — Create profile

Accepts a name, fetches demographic data from all three external APIs, and stores the result. If the same name is submitted again, the existing record is returned without calling the external APIs.

**Request body:**
```json
{ "name": "ella" }
```

**Response 201 (new profile):**
```json
{
  "status": "success",
  "data": {
    "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
    "name": "ella",
    "gender": "female",
    "gender_probability": 0.99,
    "sample_size": 1234,
    "age": 46,
    "age_group": "adult",
    "country_id": "US",
    "country_probability": 0.85,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

**Response 200 (profile already exists):**
```json
{
  "status": "success",
  "message": "Profile already exists",
  "data": { "...existing profile..." }
}
```

---

### GET /api/profiles — Get all profiles

Optional query parameters (all case-insensitive):

| Parameter  | Example             |
|------------|---------------------|
| gender     | `?gender=male`      |
| country_id | `?country_id=NG`    |
| age_group  | `?age_group=adult`  |

**Response 200:**
```json
{
  "status": "success",
  "count": 2,
  "data": [
    {
      "id": "id-1",
      "name": "emmanuel",
      "gender": "male",
      "age": 25,
      "age_group": "adult",
      "country_id": "NG"
    }
  ]
}
```

---

### GET /api/profiles/{id} — Get single profile

**Response 200:**
```json
{
  "status": "success",
  "data": {
    "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
    "name": "emmanuel",
    "gender": "male",
    "gender_probability": 0.99,
    "sample_size": 1234,
    "age": 25,
    "age_group": "adult",
    "country_id": "NG",
    "country_probability": 0.85,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

---

### DELETE /api/profiles/{id} — Delete profile

Returns `204 No Content` on success.

---

### GET /health

```json
{ "status": "success", "message": "Ok" }
```

---

## Classification Rules

**Age groups (from Agify):**

| Range  | Group    |
|--------|----------|
| 0–12   | child    |
| 13–19  | teenager |
| 20–59  | adult    |
| 60+    | senior   |

**Nationality:** country with the highest probability from the Nationalize response.

---

## Error Responses

All errors follow this structure:

```json
{ "status": "error", "message": "<error message>" }
```

| Status | Trigger |
|--------|---------|
| 400    | Missing or empty name |
| 404    | Profile not found |
| 422    | Invalid type |
| 429    | Rate limit exceeded (8 requests/min per IP) |
| 502    | External API returned an invalid response |
| 500    | Internal server error |

---

## CORS

All origins are allowed (`Access-Control-Allow-Origin: *`).

---

## License

MIT

---

## Author

James Kehinde

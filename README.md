# GridWise LLM API

GridWise converts a natural-language power-grid operator note into a validated
24-hour energy schedule. The preliminary-round deliverable is a backend API; no
frontend is required by the problem statement.

## Pipeline

```text
POST /optimize-energy
        |
        v
Gemini interpreter -> input guardrails -> deterministic optimizer -> schedule validator
        |
        v
24 hourly values + machine directives + human-readable explanation
```

Gemini extracts structured intent only. Schedule generation and validation remain
deterministic so the same interpreted constraints produce a reproducible result.

## API

- `GET /health` - service health check
- `POST /optimize-energy` - interpret an operator note and return an optimized schedule
- `GET /docs` - interactive OpenAPI documentation

The request and response contract, limits, error shape, and examples are documented
in `docs/api-contract.md`.

## Local Setup

Requirements:

- Python 3.12 or newer
- A Gemini API key from Google AI Studio

Create a virtual environment and install dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` in the repository root and set the key:

```env
GEMINI_API_KEY=your-gemini-api-key
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
LLM_TIMEOUT_SECONDS=20
OPTIMIZER_TIMEOUT_SECONDS=20
```

Never commit `.env` or any API key. The backend reads the root `.env`; an optional
`backend/.env` takes precedence.

Start the API:

```powershell
cd backend
python start.py
```

The default URL is `http://127.0.0.1:8000`. A host can provide a different port
through the `PORT` environment variable.

Check it:

```powershell
curl.exe http://127.0.0.1:8000/health
```

## Verification

Run the complete automated test suite:

```powershell
cd backend
python -m pytest -q
```

Run the live Gemini evaluation against all 10 organizer-provided public cases:

```powershell
cd backend
python scripts/evaluate_public_llm.py
```

Run a health check and one full public-case request against a deployed API:

```powershell
cd backend
python scripts/smoke_public_api.py https://your-service.example.com
```

The live evaluation consumes Gemini quota. Unit and integration tests use test
doubles and do not require network access.

## Docker

Build and run from the repository root:

```powershell
docker build -t gridwise-api backend
docker run --rm -p 8000:8000 --env-file .env gridwise-api
```

Or use Compose:

```powershell
docker compose up --build
```

The container honors `PORT` and exposes `/health` for platform health checks.

## Deploy To Render

The repository includes `render.yaml` for a Render Blueprint deployment.

1. Push the repository to GitHub.
2. In Render, create a new Blueprint and select this repository.
3. Confirm the `gridwise-api` service from `render.yaml`.
4. Add `GEMINI_API_KEY` as a secret environment variable when prompted.
5. Deploy, then run `scripts/smoke_public_api.py` against the public URL.

Render builds `backend/Dockerfile`, checks `/health`, and supplies the public HTTPS
endpoint. The free plan can sleep after inactivity, so the first request may be slower.

## Project Layout

```text
backend/
  app/api/                 FastAPI routes and dependency wiring
  app/services/interpreter Gemini extraction and guardrails
  app/services/optimizer   deterministic scheduling and validation
  scripts/                 live evaluation and deployment smoke tests
  tests/                   unit and end-to-end integration tests
docs/                      API and architecture documentation
render.yaml                Render deployment blueprint
docker-compose.yml         local container runner
```

## Dependencies And Credits

- FastAPI and Uvicorn for the HTTP service
- Google Gen AI SDK and Gemini 2.5 Flash for note interpretation
- Pydantic for request, response, and structured LLM validation
- pytest and HTTPX for automated verification

## Known Limitations

- Live interpretation depends on Gemini availability, quota, and API-key validity.
- The rule-based optimizer targets the preliminary problem contract and its public
  cases; new grid constraints may require additional optimization rules.
- The API intentionally does not persist operator notes or schedules.

# GridWise

GridWise is a FastAPI service and browser demo that turns operator notes and
hourly energy data into an optimized 24-hour electricity schedule. The pipeline interprets natural
language directives with Gemini, validates them with safety guardrails, and
optimizes grid, solar, and battery usage.

## Repository layout

```text
.
├── backend/
│   ├── app/                         # FastAPI application and optimization pipeline
│   ├── tests/                       # Unit, integration, and evaluation tests
│   └── requirements.txt             # Runtime, development, and test dependencies
├── BUP_CSE_FEST_2026_Participant_Docs/
│   ├── BUP_CSE_FEST_2026_Participant_Guide_&_Evaluation_Rubric_GridWise_LLM.pdf
│   ├── BUP_CSE_FEST_2026_Preliminary_Problem_Statement_GridWise_LLM.pdf
│   └── BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json
└── docker-compose.yml
```

The browser demo is served by the backend from `backend/app/web/`. There is no
separate `frontend/` directory or Supabase integration in this repository.

## Requirements

- Python 3.13 or newer
- An API key for the configured LLM provider during live `/optimize-energy` requests

## Local setup

From the repository root, create and activate a virtual environment inside
`backend/`.

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS or Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the repository root, or configure the same variables in
`backend/.env`. The backend loads both locations; values in `backend/.env`
override values from the root file.

```env
APP_NAME=GridWise API
APP_ENV=development
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
API_KEY=your-provider-api-key
LLM_TIMEOUT_SECONDS=20
OPTIMIZER_TIMEOUT_SECONDS=20
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

`API_KEY` is required for live optimization when the selected provider needs
authentication. The health endpoint does not require an API key. Never commit
`.env` or other files containing secrets.

## Run the API

From the `backend/` directory with the virtual environment activated:

```bash
python -m uvicorn app.main:app --reload
```

The service runs at `http://127.0.0.1:8000`.

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Demo website: `http://127.0.0.1:8000/`
- Health check: `GET /health`
- Optimization: `POST /optimize-energy`

## API example

`POST /optimize-energy` accepts one scenario with exactly 24 hourly records,
one to three operator notes, and a battery configuration.

```json
{
	"scenario_id": "sample-1",
	"operator_notes": ["Keep enough battery reserve for the evening."],
	"hours": [
		{
			"hour": 0,
			"demand_kwh": 20,
			"solar_kwh": 0,
			"tariff_bdt_per_kwh": 5
		}
	],
	"battery": {
		"capacity_kwh": 100,
		"initial_energy_kwh": 50,
		"minimum_energy_kwh": 20,
		"max_charge_kwh_per_hour": 10,
		"max_discharge_kwh_per_hour": 10
	}
}
```

The example above shows the shape of one hour; a valid request must include
every hour from `0` through `23` exactly once. Responses include interpreted
directives, an hourly plan, total grid energy, total cost, peak grid usage, and
a plan summary.

The response contract is:

```json
{
	"scenario_id": "sample-1",
	"directive_interpretation": [],
	"hourly_plan": [
		{
			"hour": 0,
			"grid_kwh": 20,
			"solar_used_kwh": 0,
			"battery_action": "idle",
			"battery_kwh": 0,
			"battery_energy_after_kwh": 50
		}
	],
	"total_grid_kwh": 480,
	"total_cost_bdt": 2400,
	"peak_grid_kwh": 20,
	"plan_summary": "..."
}
```

The real response contains 24 hourly plan entries and one directive
interpretation for each operator note. Invalid requests return a structured
`{"error": {"code": "...", "message": "..."}}` response.

## Docker

From the repository root:

```powershell
docker build -f backend/Dockerfile -t gridwise-api .
docker run --rm -p 8000:8000 --env-file .env gridwise-api
```

Then verify `http://127.0.0.1:8000/health`. Docker Compose uses the same
repository-root build context:

```powershell
docker compose up --build
```

For a fallback registry image, tag the tested image with the registry name and
push it after authentication:

```powershell
docker tag gridwise-api <registry>/<namespace>/gridwise-api:<version>
docker push <registry>/<namespace>/gridwise-api:<version>
```

## Render deployment

`render.yaml` configures a Docker web service with `backend/Dockerfile`, root
build context, `/health` health checks, and an `API_KEY` secret. Set the secret
in the Render Dashboard, sync the Blueprint, and use **Clear build cache &
deploy** after deployment configuration changes.

## Tests

Run the full backend test suite from `backend/`:

```bash
python -m pytest
```

The public sample cases are stored in
`BUP_CSE_FEST_2026_Participant_Docs/` and are covered by the evaluation tests.
To run the complete public-case test suite locally:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\evaluation tests\integration\test_public_pipeline.py
```

The sample pack is the public reference for semantic directive interpretation;
returned schedules may differ from the reference schedule when they remain
valid and optimal under the same constraints.

## Development notes

- All backend, development, and test dependencies are declared in
	`backend/requirements.txt`.
- The backend uses FastAPI, Pydantic, SciPy, and the configured LLM adapter.
- Keep `.venv/` and environment files out of version control.
- The Dockerfile and Compose configuration are implemented and use the root
	repository as the build context.

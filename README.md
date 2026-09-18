# GridWise

GridWise is a FastAPI service that turns operator notes and hourly energy data
into an optimized 24-hour electricity schedule. The pipeline interprets natural
language directives with Gemini, validates them with safety guardrails, and
optimizes grid, solar, and battery usage.

## Repository layout

```text
.
├── backend/
│   ├── app/                         # FastAPI application and optimization pipeline
│   ├── tests/                       # Unit, integration, and evaluation tests
│   ├── docs/                        # Backend architecture and conformance notes
│   └── requirements.txt             # Runtime, development, and test dependencies
├── BUP_CSE_FEST_2026_Participant_Docs/
│   └── BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json
├── .env.example
└── docker-compose.yml
```

The current implementation is backend-only. There is no `frontend/` directory
or Supabase integration in this repository.

## Requirements

- Python 3.13 or newer
- A Gemini API key for live `/optimize-energy` requests

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

Copy `.env.example` to `.env` in the repository root. The backend also loads
`backend/.env`; values there override values from the root file.

```env
APP_NAME=GridWise API
APP_ENV=development
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your-gemini-api-key
LLM_TIMEOUT_SECONDS=20
OPTIMIZER_TIMEOUT_SECONDS=20
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

`GEMINI_API_KEY` is required for live optimization. The health endpoint does
not require an API key. Never commit `.env` or other files containing secrets.

## Run the API

From the `backend/` directory with the virtual environment activated:

```bash
python -m uvicorn app.main:app --reload
```

The service runs at `http://127.0.0.1:8000`.

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
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

## Tests

Run the full backend test suite from `backend/`:

```bash
python -m pytest
```

The public sample cases are stored in
`BUP_CSE_FEST_2026_Participant_Docs/` and are covered by the evaluation tests.

## Development notes

- All backend, development, and test dependencies are declared in
	`backend/requirements.txt`.
- The backend uses FastAPI, Pydantic, SciPy, and the Google GenAI client.
- Keep `.venv/` and environment files out of version control.
- `docker-compose.yml` is present, but the backend Dockerfile is not currently
	implemented. Use the local Python setup above until container support is added.

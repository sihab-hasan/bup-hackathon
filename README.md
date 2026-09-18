# Hackathon

Next.js frontend + FastAPI backend with Supabase as the primary data and integration layer.

## Structure

```text
.
├── frontend/    # Next.js application
├── backend/     # FastAPI application
└── docs/        # Architecture and API documentation
```

The `backend/app/integrations/` abstraction is intentionally omitted because Supabase handles the persistence and integration concerns.

## Prerequisites

* Node.js
* pnpm
* Python 3.13+
* A Supabase project

## Run

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

### Backend

Create and activate a Python virtual environment:

**Windows PowerShell:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start the FastAPI development server:

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Alternative API documentation:

```text
http://127.0.0.1:8000/redoc
```

## Environment Variables

Create a `.env` file in `backend/` and configure the required Supabase credentials.

Example:

```env
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-key
```

Never commit `.env` or other files containing secrets.

## Development

When working on the backend, activate the virtual environment before running commands:

```powershell
.\.venv\Scripts\Activate.ps1
```

To deactivate it:

```powershell
deactivate
```

The `.venv/` directory should not be committed to Git.

## Backend Dependencies

Backend dependencies are managed through:

```text
backend/requirements.txt
```

Install them with:

```bash
python -m pip install -r requirements.txt
```

Do not install project dependencies globally when working on the project.

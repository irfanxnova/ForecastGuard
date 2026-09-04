# ForecastGuard

> AI-based forecast reliability intelligence system for medium-range numerical weather prediction.
>
> *"NWP tells us what may happen. ForecastGuard tells us how much we should trust that forecast."*

ForecastGuard evaluates the vulnerability of existing numerical weather prediction (NWP) forecasts to significant failure (forecast bust), helping meteorologists and operational users identify reliability degradation before forecast failure occurs.

---

## Architecture & Specifications

The authoritative specifications for this repository are defined in:

- **[AGENTS.md](AGENTS.md)** — Project constitution, scientific boundaries, and non-negotiable principles.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — End-to-end system design, module boundaries, data pipelines, and milestone roadmap.
- **[SCIENCE_SPEC.md](SCIENCE_SPEC.md)** — Meteorological and scientific framing, alignment rules, verification, and evaluation.
- **[UI_SPEC.md](UI_SPEC.md)** — Operational visual language, design hierarchy, accessibility, and user experience standards.

---

## Repository Structure

```
forecastguard/
├── AGENTS.md                  # Project constitution & non-negotiables
├── ARCHITECTURE.md            # System architecture & milestones
├── SCIENCE_SPEC.md            # Scientific & meteorological specification
├── UI_SPEC.md                 # UI/UX design specification
├── backend/                   # FastAPI backend application
│   ├── app/
│   │   ├── api/               # API endpoints (GET /api/v1/health)
│   │   ├── config.py          # Configuration & environment settings
│   │   ├── database/          # Database connection & persistence boundary
│   │   ├── main.py            # FastAPI app entrypoint
│   │   ├── schemas/           # Pydantic data schemas
│   │   └── services/          # Business logic & orchestration boundary
│   └── requirements.txt       # Backend Python dependencies
├── frontend/                  # React + TypeScript + Vite operational shell
│   ├── src/
│   │   ├── App.tsx            # Operational shell & backend connectivity monitor
│   │   ├── index.css          # Dark operational design tokens & styling
│   │   └── main.tsx           # React DOM mount
│   ├── index.html
│   └── vite.config.ts
├── scientific/                # Scientific package boundaries (ingestion, qc, verification, etc.)
├── configs/                   # Configuration files placeholder
├── data/                      # Data storage taxonomy (raw, interim, processed, features, manifests)
├── docs/                      # Documentation placeholder
├── tests/                     # Automated test suites (API, unit, scientific structure)
├── pyproject.toml             # Python project & test configuration
└── .env.example               # Safe environment variable template
```

---

## Quickstart

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm

### 1. Environment Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### 2. Backend Setup & Run

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Start the FastAPI development server:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify backend health:
- API endpoint: `http://127.0.0.1:8000/api/v1/health`
- Interactive docs: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup & Run

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The operational frontend shell will be accessible at:
- `http://localhost:5173`

The frontend displays the live connection status with the backend health endpoint.

### 4. Running Tests

Run the test suite from the repository root:

```bash
pytest tests/
```

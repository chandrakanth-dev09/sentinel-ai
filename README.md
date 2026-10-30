# SentinelAI

SentinelAI is an AIOps platform for collecting service metrics and logs, detecting anomalous behaviour, mapping service dependencies, and producing evidence-backed incident analysis.

The application is being developed in phases. The workspace includes a FastAPI backend, PostgreSQL-oriented SQLAlchemy models and Alembic migration, validated metric/log ingestion, a demonstration simulator, anomaly detection, dependency-aware RCA, incident workflows, and an API-connected React operations dashboard. WebSocket updates and deployment/runtime verification remain in progress.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer and npm
- PostgreSQL 16
- Redis 7
- Docker Desktop (for the planned Compose deployment)

## Local environment setup (Windows PowerShell)

From the repository root, copy the example environment file and set a valid PostgreSQL password and database URL:

```powershell
Copy-Item sentinel-ai\.env.example sentinel-ai\.env
cd sentinel-ai\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal, install the pinned frontend packages:

```powershell
cd ..\frontend
npm ci
npm run dev
```

PostgreSQL must be running and the configured database must exist before applying migrations. The backend reads `sentinel-ai/.env` even when commands are run from `sentinel-ai/backend`. Do not commit `.env` or use development credentials in a deployed environment.

The frontend is served at `http://localhost:5173`; its API base defaults to `http://localhost:8000/api/v1` and can be overridden with `VITE_API_BASE_URL`. The API documentation is available at `http://localhost:8000/docs`. Liveness and readiness checks are available at `/health/live` and `/health/ready`; readiness verifies the database connection.

## Dashboard

The overview page summarizes service health and availability, active incidents, recent anomalies, recent telemetry, and incident activity. Other pages provide service monitoring and detail, an interactive service dependency map, incident lifecycle and evidence views, on-demand root-cause analysis, searchable logs, anomaly model status/history, and persisted monitoring thresholds. Settings also supports service and dependency registration.

Dashboard and monitoring views currently refresh through HTTP polling. WebSocket delivery is planned for a later phase. Simulated telemetry is explicitly labeled in the UI and API data.

## Deploy the interface with GitHub Pages

The public repository includes a GitHub Actions workflow at `.github/workflows/deploy-pages.yml`. Each push to `main` that changes the frontend builds and publishes the interface. In the repository's **Settings → Pages**, choose **GitHub Actions** as the build and deployment source if it is not already enabled.

Once the Pages workflow succeeds, share `https://chandrakanth-dev09.github.io/sentinel-ai/`. Client-side routes have a Pages fallback, so links to pages within the interface also open directly. GitHub Pages only hosts static frontend files: it does not run FastAPI, PostgreSQL, model inference, or write actions. The deployed page clearly identifies itself as a frontend preview until a backend is hosted separately and `VITE_API_BASE_URL` is configured.

## Ingestion and simulator

The ingestion endpoints accept batches with timestamps that include a timezone. Values are validated before persistence, and unknown service IDs are rejected.

- `POST /api/v1/services` — register a service; repeated registration with the same classification is idempotent.
- `GET /api/v1/services` — list registered services.
- `POST /api/v1/metrics/ingest` — ingest a `{"metrics": [...]}` batch.
- `POST /api/v1/logs/ingest` — ingest a `{"logs": [...]}` batch.
- `GET /api/v1/logs` — search logs by service, level, time range, and message text, with pagination.
- `POST /api/v1/services/dependencies` — register a directed dependency; cycles are rejected.
- `GET /api/v1/services/dependency-graph` — return services, latest metrics, active incidents, and dependency edges.
- `POST /api/v1/incidents/analyze` — rank evidence-backed root-cause candidates for a time window.
- `GET /api/v1/incidents` and `GET /api/v1/incidents/{incident_id}` — list/filter incidents and retrieve investigation details.
- `PATCH /api/v1/incidents/{incident_id}` — change severity or advance incident status through the lifecycle.
- `POST /api/v1/incidents/{incident_id}/analyze` — refresh the evidence timeline, explanation, and recommended actions.
- `POST /api/v1/ml/detect-anomaly` and `GET /api/v1/ml/model-status` — score stored metrics and inspect the trained model.

To generate normal traffic, or choose one of the failure scenarios (`database-failure`, `memory-leak`, `api-latency-spike`, `cascading-failure`), run from the repository root in another PowerShell terminal:

```powershell
cd sentinel-ai
.\backend\.venv\Scripts\python.exe .\monitoring-agent\simulator.py --scenario normal
```

Change `normal` to a scenario name to select a failure mode. The simulator registers demo services, uploads telemetry tagged `SIMULATED`, and continues until Ctrl+C. Use `--once` for a single batch, `--interval 10` to override the interval, `--seed 42` for repeatable normal variation, or `--api-url` to target another API origin.

## Anomaly model

Train the local Isolation Forest artifact before calling the prediction endpoint:

```powershell
cd sentinel-ai\backend
.\.venv\Scripts\python.exe -m app.ml.train
```

The training command prints the measured synthetic holdout metrics. `GET /api/v1/ml/model-status` reports whether a compatible artifact is available; `POST /api/v1/ml/detect-anomaly` scores persisted metrics and saves anomaly events. Dataset provenance, assumptions, and evaluation limitations are described in [docs/ml-pipeline.md](./docs/ml-pipeline.md).

## Project layout

- `backend/app/` — FastAPI application, persistence, ingestion, ML, RCA, and workers
- `backend/alembic/` — versioned database migrations
- `backend/tests/` — backend and integration tests
- `frontend/src/` — React application, pages, components, hooks, and API client
- `monitoring-agent/` — simulated and future real-agent integration
- `scripts/` — development and maintenance utilities
- `docs/` — architecture, data model, ML, RCA, and API documentation

See [DEVELOPMENT_STATUS.md](./DEVELOPMENT_STATUS.md) for phase completion and remaining work. Frontend checks run with `npm test` and `npm run build` from `sentinel-ai/frontend`; backend tests run with `python -m pytest` from `sentinel-ai/backend`.

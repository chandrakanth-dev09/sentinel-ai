# Development Status

## Completed

### Phase 1 — Workspace inspection and project scaffold

- Confirmed the repository contains an existing CertiFlow application and left its files unchanged.
- Created an isolated `sentinel-ai/` project layout.
- Added pinned Python backend dependencies and a pinned frontend package manifest.
- Generated and validated the npm lockfile for reproducible frontend dependency resolution.
- Added an example environment file with placeholder database credentials and local service URLs.
- Added Windows PowerShell setup guidance and this phase tracker.

## Pending

- Phase 7: React dashboard pages and API integration.
- Phase 8: WebSocket updates and real-time monitoring.
- Phase 9: Docker Compose, integration tests, and bug fixing.
- Phase 10: complete technical documentation and final verification.

### Phase 2 — Backend and database foundation

- Added FastAPI app configuration, CORS allow-listing, root endpoint, and live/readiness health checks.
- Added SQLAlchemy models for all eight required entities and the incident-to-service association.
- Added database constraints, indexes, foreign-key behavior, and explicit source markers for simulated versus agent/imported telemetry.
- Added the initial Alembic migration and database-design documentation.
- Added an isolated Python 3.11 virtual environment and installed the pinned backend requirements.
- Added tests for model registration, relations, constraints, and health endpoints.

### Phase 3 — Telemetry ingestion and simulator

- Added service registration/listing, batch metric and structured-log ingestion, and paginated log search.
- Validated metric bounds, log levels, timezone-aware timestamps, future timestamp skew, service references, and configurable batch size.
- Added a CLI simulator with normal, database-failure, memory-leak, API-latency-spike, and cascading-failure scenarios; generated records are tagged `SIMULATED`.
- Documented local PowerShell setup and simulator usage.

### Phase 4 — Anomaly detection

- Implemented seeded synthetic training/evaluation data with deterministic scenario-derived labels; Isolation Forest is fitted only on healthy training observations.
- Added median imputation, model serialization/loading, calibrated anomaly scores, severity mapping, feature deviation evidence, and model status/detection APIs.
- Persisted detection events against the source service and metric.
- Documented model assumptions, provenance, evaluation procedure, and limitations; trained the default local Joblib artifact.

### Phase 5 — Dependency graph and root cause analysis

- Added dependency registration with service validation, idempotent repeats, and cycle rejection.
- Added graph retrieval with latest per-service metrics and active incident identifiers.
- Implemented deterministic RCA over stored threshold signals, anomaly events, and error logs, ranked using dependency coverage, event precedence, and evidence strength.
- Added event timelines, affected services, alternatives, and evidence-based investigation steps; ranking scores are explicitly not calibrated probabilities.
- Added architecture/RCA documentation and simulator dependency seeding.

### Phase 6 — Incident management and explanations

- Added filtered/paginated incident listing, detail retrieval, severity updates, and validated lifecycle transitions.
- Anomaly predictions now create or update one active incident per service, with stored anomaly evidence and deduplication.
- Added incident reanalysis that persists metric/log/anomaly evidence, affected services, root-cause ranking, a data-derived explanation, and recommended investigation actions.
- Reanalysis avoids duplicate evidence records and preserves explicit uncertainty when dependency coverage is insufficient.

### Phase 7 — Dashboard and API-connected frontend

- Added the React operations shell and responsive overview with service health, availability, incident/anomaly counts, telemetry charts, and recent incidents.
- Added service monitoring/detail, interactive dependency graph, incident list/detail and lifecycle actions, evidence-backed incident reanalysis, and standalone RCA workflows.
- Added searchable/filterable logs, model readiness/evaluation/anomaly history, and persisted threshold, service-registration, and dependency settings.
- Connected all views to the implemented FastAPI endpoints with typed API models, loading/error/empty states, retry controls, and periodic polling for overview/monitoring data.
- Added route-level lazy loading and responsive application styles.

## Phase 1 validation

- Inspected the repository README, Python dependencies, Docker Compose file, environment template, and Git status.
- Confirmed Node.js, npm, Python, and Docker CLI are available in this environment.
- Resolved the pinned frontend dependency graph and verified `npm audit` reports zero vulnerabilities.
- No application tests were run because this phase adds only the scaffold and dependency manifests.

## Phase 2 validation

- Backend foundation tests: `8 passed` (one upstream Starlette deprecation warning).
- Alembic migration upgrade and downgrade both completed against a temporary SQLite database.
- PostgreSQL runtime connectivity has not been tested; a PostgreSQL service was not provisioned during this phase.

## Phase 3 validation

- Backend test suite: `17 passed` (one upstream Starlette deprecation warning).
- Coverage includes metric/log ingestion, input constraints, unknown services, log filters, batch limits, and deterministic scenario characteristics.
- PostgreSQL runtime connectivity and browser UI are not yet verified.

## Phase 4 validation

- Backend test suite: `21 passed` (one upstream Starlette deprecation warning).
- Executed `python -m app.ml.train` with seed 42, 3,000 healthy training rows, 400 healthy evaluation rows, and 100 examples per failure scenario.
- Measured synthetic holdout metrics: precision `0.997506`, recall `1.000000`, F1 `0.998752`, false-positive rate `0.002500`; recall was `1.000000` for each of the four generated scenarios. Mean vectorized prediction latency measured `0.023628 ms/row` in this run.
- These values describe only the controlled synthetic evaluation set and local machine; they are not production accuracy or incident-level detection-latency claims.

## Phase 5 validation

- Backend test suite: `25 passed` (one upstream Starlette deprecation warning).
- Coverage verifies graph retrieval, cycle prevention, missing-service rejection, evidence/timeline generation, upstream root selection, and withholding a root cause when no dependency coverage exists.

## Phase 6 validation

- Backend test suite: `28 passed` (one upstream Starlette deprecation warning).
- Coverage verifies incident filters/detail, lifecycle transitions, automatic anomaly incident creation/deduplication, and evidence-backed incident reanalysis.

## Phase 7 validation

- Frontend production build: `npm run build` completed successfully; route chunks are lazy-loaded.
- Frontend tests: `npm test` completed with `3 passed`, covering API-backed dashboard rendering, request failure feedback, and incident filtering/lifecycle actions.
- Backend regression suite: `30 passed` (one upstream Starlette deprecation warning).
- Latest Alembic migration upgraded and downgraded successfully against a temporary SQLite database, including the system-configuration seed.
- Browser smoke test against a temporary SQLite-backed API verified the overview and settings pages render populated API responses and empty-state data.
- PostgreSQL/Redis runtime connectivity and browser-driven integration against a running backend remain unverified.

## Hosting preparation

- Added a GitHub Actions workflow to build and publish the React interface to GitHub Pages, including asset base paths and direct-route fallback.
- The static overview explicitly indicates that GitHub Pages does not host the API, database, model inference, or write operations; no local API address is used in production.
- GitHub Pages repository settings, public URL verification, and automated deployment still require a successful Actions run.

## Known limitations

- WebSocket updates remain pending; overview, service, anomaly, and model views currently use HTTP polling.
- PostgreSQL and Redis services have not been provisioned or started; readiness will report unavailable until PostgreSQL is configured.
- Python dependencies are pinned directly but do not yet have a transitive lock; runtime compatibility will be verified during implementation.
- Model evaluation uses the documented synthetic dataset only; performance on public or production telemetry is unknown.
- The production frontend build may warn about large visualization-library chunks; route-level lazy loading reduces the initially loaded code.
- GitHub Pages hosts only the React frontend; API data and write actions need a separately hosted FastAPI backend and PostgreSQL database.

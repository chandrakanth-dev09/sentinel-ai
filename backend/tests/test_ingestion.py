from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ApplicationLog, Service, SystemMetric


def register_service(client: TestClient, name: str = "billing") -> str:
    response = client.post(
        "/api/v1/services",
        json={"name": name, "is_simulated": False},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_service_registration_is_idempotent(api_client: TestClient) -> None:
    service_id = register_service(api_client)
    response = api_client.post(
        "/api/v1/services",
        json={"name": "billing", "is_simulated": False},
    )

    assert response.status_code == 201
    assert response.json()["id"] == service_id
    assert len(api_client.get("/api/v1/services").json()) == 1


def test_metric_batch_is_persisted_with_source_marker(
    api_client: TestClient,
    db_session: Session,
) -> None:
    service_id = register_service(api_client)
    response = api_client.post(
        "/api/v1/metrics/ingest",
        json={
            "metrics": [
                {
                    "service_id": service_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cpu_utilization": 24,
                    "memory_utilization": 41,
                    "disk_utilization": 30,
                    "network_traffic": 120,
                    "response_time_ms": 45,
                    "request_count": 140,
                    "error_rate": 0.1,
                    "database_connections": 8,
                    "service_availability": 99.9,
                    "source": "SIMULATED",
                }
            ]
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted_count"] == 1
    metric = db_session.query(SystemMetric).one()
    assert metric.source == "SIMULATED"


def test_invalid_metric_and_unknown_service_are_rejected(api_client: TestClient) -> None:
    service_id = register_service(api_client)
    invalid_metric = {
        "service_id": service_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_utilization": 101,
        "memory_utilization": 41,
        "disk_utilization": 30,
        "network_traffic": 120,
        "response_time_ms": 45,
        "request_count": 140,
        "error_rate": 0.1,
        "database_connections": 8,
        "service_availability": 99.9,
    }
    invalid_response = api_client.post(
        "/api/v1/metrics/ingest",
        json={"metrics": [invalid_metric]},
    )
    future_timestamp_response = api_client.post(
        "/api/v1/metrics/ingest",
        json={
            "metrics": [
                {
                    **invalid_metric,
                    "cpu_utilization": 20,
                    "timestamp": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                }
            ]
        },
    )
    unknown_response = api_client.post(
        "/api/v1/metrics/ingest",
        json={"metrics": [{**invalid_metric, "cpu_utilization": 20, "service_id": "00000000-0000-0000-0000-000000000001"}]},
    )

    assert invalid_response.status_code == 422
    assert future_timestamp_response.status_code == 422
    assert unknown_response.status_code == 404


def test_log_ingestion_and_search_filters(api_client: TestClient, db_session: Session) -> None:
    service_id = register_service(api_client)
    timestamp = datetime.now(timezone.utc).isoformat()
    response = api_client.post(
        "/api/v1/logs/ingest",
        json={
            "logs": [
                {
                    "service_id": service_id,
                    "timestamp": timestamp,
                    "level": "ERROR",
                    "message": "database connection timeout",
                    "error_type": "ConnectionError",
                    "trace_id": "trace-123",
                    "request_id": "request-456",
                    "source": "SIMULATED",
                }
            ]
        },
    )
    search_response = api_client.get(
        "/api/v1/logs",
        params={"service_id": service_id, "level": "ERROR", "search": "database"},
    )

    assert response.status_code == 202
    assert db_session.query(ApplicationLog).one().trace_id == "trace-123"
    assert len(search_response.json()) == 1


def test_ingestion_rejects_empty_batches(api_client: TestClient) -> None:
    assert api_client.post("/api/v1/metrics/ingest", json={"metrics": []}).status_code == 422
    assert api_client.post("/api/v1/logs/ingest", json={"logs": []}).status_code == 422


def test_metric_batch_limit_returns_413(api_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.telemetry.settings.MAX_INGEST_BATCH_SIZE", 1)
    service_id = register_service(api_client)
    item = {
        "service_id": service_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_utilization": 20,
        "memory_utilization": 40,
        "disk_utilization": 30,
        "network_traffic": 120,
        "response_time_ms": 45,
        "request_count": 140,
        "error_rate": 0.1,
        "database_connections": 8,
        "service_availability": 99.9,
    }

    response = api_client.post(
        "/api/v1/metrics/ingest",
        json={"metrics": [item, item]},
    )

    assert response.status_code == 413

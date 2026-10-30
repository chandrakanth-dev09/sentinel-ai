from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def register_service(client: TestClient, name: str) -> str:
    response = client.post("/api/v1/services", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def metric(service_id: str, timestamp: datetime, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "service_id": service_id,
        "timestamp": timestamp.isoformat(),
        "cpu_utilization": 25,
        "memory_utilization": 45,
        "disk_utilization": 35,
        "network_traffic": 120,
        "response_time_ms": 100,
        "request_count": 160,
        "error_rate": 0.1,
        "database_connections": 10,
        "service_availability": 99.9,
        "source": "AGENT",
    }
    values.update(overrides)
    return values


def test_settings_are_readable_updatable_and_validated(api_client: TestClient) -> None:
    defaults = api_client.get("/api/v1/settings")
    updated = api_client.patch(
        "/api/v1/settings",
        json={
            "monitoring_interval_seconds": 12,
            "cpu_warning_percent": 70,
            "response_time_warning_ms": 400,
        },
    )
    read_back = api_client.get("/api/v1/settings")
    empty_update = api_client.patch("/api/v1/settings", json={})
    invalid_value = api_client.patch(
        "/api/v1/settings",
        json={"response_time_warning_ms": 0},
    )

    assert defaults.status_code == 200
    assert defaults.json()["monitoring_interval_seconds"] == 5
    assert updated.status_code == 200
    assert read_back.json()["monitoring_interval_seconds"] == 12
    assert read_back.json()["cpu_warning_percent"] == 70
    assert empty_update.status_code == 422
    assert invalid_value.status_code == 422


def test_monitoring_overview_and_metric_history_use_persisted_data(
    api_client: TestClient,
) -> None:
    service_id = register_service(api_client, "api")
    now = datetime.now(timezone.utc)
    healthy = metric(service_id, now - timedelta(minutes=1))
    critical = metric(
        service_id,
        now,
        error_rate=30,
        response_time_ms=2200,
        service_availability=70,
        database_connections=0,
    )
    ingest = api_client.post(
        "/api/v1/metrics/ingest",
        json={"metrics": [healthy, critical]},
    )
    monitoring = api_client.get("/api/v1/services/monitoring")
    detail = api_client.get(f"/api/v1/services/{service_id}")
    history = api_client.get(
        "/api/v1/metrics",
        params={"service_id": service_id, "limit": 10},
    )
    overview = api_client.get("/api/v1/overview")

    assert ingest.status_code == 202
    assert monitoring.json()[0]["health_status"] == "CRITICAL"
    assert detail.json()["latest_metrics"]["response_time_ms"] == 2200
    assert [item["response_time_ms"] for item in history.json()] == [100, 2200]
    assert overview.json()["total_services"] == 1
    assert overview.json()["critical_services"] == 1
    assert overview.json()["availability_percent"] == 70

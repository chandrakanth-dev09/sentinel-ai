from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient


def register(client: TestClient, name: str) -> str:
    response = client.post("/api/v1/services", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def add_dependency(client: TestClient, upstream_id: str, downstream_id: str) -> None:
    response = client.post(
        "/api/v1/services/dependencies",
        json={
            "upstream_service_id": upstream_id,
            "downstream_service_id": downstream_id,
        },
    )
    assert response.status_code == 201


def test_dependency_graph_rejects_cycles_and_returns_latest_metrics(
    api_client: TestClient,
) -> None:
    database_id = register(api_client, "database")
    payment_id = register(api_client, "payment")
    gateway_id = register(api_client, "gateway")
    add_dependency(api_client, database_id, payment_id)
    add_dependency(api_client, payment_id, gateway_id)

    cycle_response = api_client.post(
        "/api/v1/services/dependencies",
        json={
            "upstream_service_id": gateway_id,
            "downstream_service_id": database_id,
        },
    )
    metric_response = api_client.post(
        "/api/v1/metrics/ingest",
        json={
            "metrics": [
                {
                    "service_id": database_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cpu_utilization": 70,
                    "memory_utilization": 60,
                    "disk_utilization": 30,
                    "network_traffic": 100,
                    "response_time_ms": 750,
                    "request_count": 40,
                    "error_rate": 8,
                    "database_connections": 0,
                    "service_availability": 92,
                }
            ]
        },
    )
    graph_response = api_client.get("/api/v1/services/dependency-graph")
    nodes = {node["id"]: node for node in graph_response.json()["nodes"]}

    assert cycle_response.status_code == 409
    assert metric_response.status_code == 202
    assert len(graph_response.json()["edges"]) == 2
    assert nodes[database_id]["latest_metrics"]["response_time_ms"] == 750


def test_rca_ranks_earliest_upstream_service_and_returns_evidence(
    api_client: TestClient,
) -> None:
    ids = {
        name: register(api_client, name)
        for name in ("database", "payment", "api-gateway", "frontend")
    }
    add_dependency(api_client, ids["database"], ids["payment"])
    add_dependency(api_client, ids["payment"], ids["api-gateway"])
    add_dependency(api_client, ids["api-gateway"], ids["frontend"])
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    metric_values = {
        "database": (800, 15, 0, 60),
        "payment": (650, 10, 8, 78),
        "api-gateway": (700, 8, 12, 88),
        "frontend": (600, 5, 15, 94),
    }
    metrics = []
    logs = []
    for offset, (name, values) in enumerate(metric_values.items()):
        response_time, error_rate, database_connections, availability = values
        timestamp = (base_time + timedelta(seconds=offset * 20)).isoformat()
        metrics.append(
            {
                "service_id": ids[name],
                "timestamp": timestamp,
                "cpu_utilization": 70,
                "memory_utilization": 65,
                "disk_utilization": 35,
                "network_traffic": 180,
                "response_time_ms": response_time,
                "request_count": 100,
                "error_rate": error_rate,
                "database_connections": database_connections,
                "service_availability": availability,
                "source": "SIMULATED",
            }
        )
        logs.append(
            {
                "service_id": ids[name],
                "timestamp": (base_time + timedelta(seconds=offset * 20 + 5)).isoformat(),
                "level": "ERROR",
                "message": f"Correlated failure in {name}",
                "trace_id": "shared-trace-1",
                "source": "SIMULATED",
            }
        )

    assert api_client.post("/api/v1/metrics/ingest", json={"metrics": metrics}).status_code == 202
    assert api_client.post("/api/v1/logs/ingest", json={"logs": logs}).status_code == 202
    response = api_client.post(
        "/api/v1/incidents/analyze",
        json={"lookback_minutes": 15},
    )
    result = response.json()

    assert response.status_code == 200
    assert result["probable_root_cause"]["service_name"] == "database"
    assert result["probable_root_cause"]["downstream_affected_count"] == 3
    assert set(result["affected_services"]) == set(ids)
    assert result["incident_timeline"][0]["service_name"] == "database"
    assert result["supporting_evidence"]
    assert result["alternative_causes"]
    assert "not calibrated probabilities" in result["ranking_method"]


def test_rca_does_not_infer_a_root_without_dependency_coverage(
    api_client: TestClient,
) -> None:
    service_a = register(api_client, "unrelated-a")
    service_b = register(api_client, "unrelated-b")
    timestamp = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    metrics = [
        {
            "service_id": service_id,
            "timestamp": timestamp,
            "cpu_utilization": 20,
            "memory_utilization": 40,
            "disk_utilization": 30,
            "network_traffic": 100,
            "response_time_ms": 700,
            "request_count": 40,
            "error_rate": 8,
            "database_connections": 5,
            "service_availability": 95,
        }
        for service_id in (service_a, service_b)
    ]
    assert api_client.post("/api/v1/metrics/ingest", json={"metrics": metrics}).status_code == 202

    response = api_client.post("/api/v1/incidents/analyze", json={"lookback_minutes": 10})

    assert response.status_code == 200
    assert response.json()["probable_root_cause"] is None


def test_dependency_requires_registered_services(api_client: TestClient) -> None:
    service_id = register(api_client, "known-service")
    response = api_client.post(
        "/api/v1/services/dependencies",
        json={
            "upstream_service_id": service_id,
            "downstream_service_id": str(uuid4()),
        },
    )

    assert response.status_code == 404

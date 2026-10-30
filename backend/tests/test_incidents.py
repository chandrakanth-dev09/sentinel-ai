from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ApplicationLog, Incident, Service, ServiceDependency, SystemMetric


def create_incident(db_session: Session, service: Service) -> Incident:
    incident = Incident(
        title="Database degradation",
        description="A database failure affected downstream services.",
        severity="HIGH",
        status="OPEN",
        deduplication_key=f"anomaly:{service.id}",
        root_cause_service=service,
        affected_services=[service],
        first_detected_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add(incident)
    db_session.commit()
    return incident


def test_incident_list_detail_filters_and_status_transitions(
    api_client: TestClient,
    db_session: Session,
) -> None:
    service = Service(name="database")
    db_session.add(service)
    db_session.flush()
    incident = create_incident(db_session, service)

    list_response = api_client.get(
        "/api/v1/incidents",
        params={"severity": "HIGH", "status": "OPEN", "service_id": str(service.id)},
    )
    detail_response = api_client.get(f"/api/v1/incidents/{incident.id}")
    investigation_response = api_client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"status": "INVESTIGATING", "severity": "CRITICAL"},
    )
    resolved_response = api_client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"status": "RESOLVED"},
    )
    reopened_response = api_client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"status": "INVESTIGATING"},
    )
    closed_response = api_client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"status": "CLOSED"},
    )
    invalid_transition = api_client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"status": "OPEN"},
    )

    assert len(list_response.json()) == 1
    assert detail_response.status_code == 200
    assert investigation_response.json()["severity"] == "CRITICAL"
    assert resolved_response.json()["resolved_at"] is not None
    assert reopened_response.json()["resolved_at"] is None
    assert closed_response.json()["status"] == "CLOSED"
    assert invalid_transition.status_code == 409


def test_incident_analysis_persists_evidence_and_explanation(
    api_client: TestClient,
    db_session: Session,
) -> None:
    database = Service(name="analysis-database")
    payment = Service(name="analysis-payment")
    db_session.add_all([database, payment])
    db_session.flush()
    base_time = datetime.now(timezone.utc) - timedelta(minutes=3)
    db_session.add(
        ServiceDependency(
            upstream_service_id=database.id,
            downstream_service_id=payment.id,
        )
    )
    metrics = [
        SystemMetric(
            service_id=database.id,
            timestamp=base_time,
            cpu_utilization=85,
            memory_utilization=80,
            disk_utilization=50,
            network_traffic=200,
            response_time_ms=1100,
            request_count=60,
            error_rate=15,
            database_connections=0,
            service_availability=75,
            source="SIMULATED",
        ),
        SystemMetric(
            service_id=payment.id,
            timestamp=base_time + timedelta(seconds=30),
            cpu_utilization=70,
            memory_utilization=65,
            disk_utilization=40,
            network_traffic=180,
            response_time_ms=800,
            request_count=90,
            error_rate=8,
            database_connections=10,
            service_availability=90,
            source="SIMULATED",
        ),
    ]
    logs = [
        ApplicationLog(
            service_id=database.id,
            timestamp=base_time + timedelta(seconds=5),
            level="ERROR",
            message="Connection pool exhausted",
            trace_id="incident-trace",
            source="SIMULATED",
        ),
        ApplicationLog(
            service_id=payment.id,
            timestamp=base_time + timedelta(seconds=35),
            level="ERROR",
            message="Database request timed out",
            trace_id="incident-trace",
            source="SIMULATED",
        ),
    ]
    db_session.add_all([*metrics, *logs])
    db_session.commit()
    incident = create_incident(db_session, payment)
    response = api_client.post(f"/api/v1/incidents/{incident.id}/analyze")

    assert response.status_code == 200
    assert response.json()["incident"]["explanation"]
    assert response.json()["incident"]["root_cause_service_name"] == "analysis-database"
    assert "analysis-database is ranked" in response.json()["incident"]["explanation"]
    assert len(response.json()["incident"]["evidence"]) == 4
    assert response.json()["analysis"]["probable_root_cause"]["service_name"] == "analysis-database"


def test_incident_endpoints_reject_missing_incident(api_client: TestClient) -> None:
    incident_id = str(uuid4())

    assert api_client.get(f"/api/v1/incidents/{incident_id}").status_code == 404
    assert api_client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={"severity": "LOW"},
    ).status_code == 404

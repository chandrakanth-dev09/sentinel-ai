from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import (
    ApplicationLog,
    Incident,
    IncidentEvidence,
    MLModelMetadata,
    Service,
    ServiceDependency,
    SystemMetric,
)


def test_required_entities_are_registered_in_metadata() -> None:
    expected_tables = {
        "services",
        "service_dependencies",
        "system_metrics",
        "application_logs",
        "anomaly_events",
        "incidents",
        "incident_evidence",
        "ml_model_metadata",
    }

    assert expected_tables <= set(Base.metadata.tables)


def test_service_dependency_relationships_persist(db_session: Session) -> None:
    database = Service(name="database")
    api = Service(name="api")
    dependency = ServiceDependency(
        upstream_service=database,
        downstream_service=api,
    )
    db_session.add_all([database, api, dependency])
    db_session.commit()

    assert api.upstream_dependencies[0].upstream_service.name == "database"
    assert database.downstream_dependencies[0].downstream_service.name == "api"


def test_metric_constraints_reject_out_of_range_utilization(db_session: Session) -> None:
    service = Service(name="worker")
    db_session.add(service)
    db_session.flush()
    metric = SystemMetric(
        service_id=service.id,
        timestamp=datetime.now(timezone.utc),
        cpu_utilization=101,
        memory_utilization=20,
        disk_utilization=30,
        network_traffic=12,
        response_time_ms=50,
        request_count=200,
        error_rate=0.5,
        database_connections=5,
        service_availability=100,
    )
    db_session.add(metric)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_incident_evidence_keeps_linked_incident_and_metric(
    db_session: Session,
) -> None:
    service = Service(name="payments")
    db_session.add(service)
    db_session.flush()
    metric = SystemMetric(
        service_id=service.id,
        timestamp=datetime.now(timezone.utc),
        cpu_utilization=40,
        memory_utilization=50,
        disk_utilization=30,
        network_traffic=12,
        response_time_ms=250,
        request_count=100,
        error_rate=2,
        database_connections=8,
        service_availability=99.5,
    )
    db_session.add(metric)
    db_session.flush()
    incident = Incident(
        title="Elevated response time",
        description="Response time exceeded the normal range.",
        severity="MEDIUM",
        affected_services=[service],
    )
    evidence = IncidentEvidence(
        incident=incident,
        metric_id=metric.id,
        evidence_type="METRIC",
        summary="Response time was 250 ms.",
        event_timestamp=metric.timestamp,
    )
    db_session.add_all([incident, evidence])
    db_session.commit()

    assert incident.evidence[0].summary == "Response time was 250 ms."
    assert incident.affected_services[0].name == "payments"


def test_required_entity_models_are_importable() -> None:
    assert all(
        model is not None
        for model in (
            ApplicationLog,
            Incident,
            MLModelMetadata,
            Service,
        )
    )

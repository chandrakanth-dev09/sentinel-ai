from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnomalyEvent, Incident, IncidentEvidence, Service, SystemMetric


_SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def create_or_update_anomaly_incident(
    session: Session,
    anomaly: AnomalyEvent,
    metric: SystemMetric,
) -> Incident:
    service = session.get(Service, anomaly.service_id)
    if service is None:
        raise ValueError(f"Service {anomaly.service_id} no longer exists")

    deduplication_key = f"anomaly:{service.id}"
    incident = session.scalar(
        select(Incident).where(
            Incident.deduplication_key == deduplication_key,
            Incident.status.in_(("OPEN", "INVESTIGATING")),
        )
    )
    if incident is None:
        incident = Incident(
            title=f"Anomaly detected in {service.name}",
            description=(
                f"The Isolation Forest model detected abnormal behaviour in {service.name} "
                f"with score {anomaly.anomaly_score:.3f}. The source metric was recorded at "
                f"{metric.timestamp.isoformat()}."
            ),
            severity=anomaly.severity,
            status="OPEN",
            deduplication_key=deduplication_key,
            root_cause_service=service,
            first_detected_at=anomaly.detected_at,
            last_updated_at=anomaly.detected_at,
            affected_services=[service],
        )
        session.add(incident)
        session.flush()
    else:
        incident.last_updated_at = datetime.now(timezone.utc)
        if _SEVERITY_RANK[anomaly.severity] > _SEVERITY_RANK[incident.severity]:
            incident.severity = anomaly.severity

    existing_evidence = session.scalar(
        select(IncidentEvidence.id).where(
            IncidentEvidence.incident_id == incident.id,
            IncidentEvidence.anomaly_event_id == anomaly.id,
        )
    )
    if existing_evidence is None:
        session.add(
            IncidentEvidence(
                incident_id=incident.id,
                evidence_type="ANOMALY_EVENT",
                summary=(
                    f"Model {anomaly.model_version} detected anomaly score "
                    f"{anomaly.anomaly_score:.3f} for {service.name}."
                ),
                details={
                    "anomaly_score": anomaly.anomaly_score,
                    "severity": anomaly.severity,
                    "contributing_features": anomaly.contributing_features or {},
                },
                event_timestamp=anomaly.detected_at,
                service_id=service.id,
                metric_id=metric.id,
                anomaly_event_id=anomaly.id,
            )
        )
    return incident

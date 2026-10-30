from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.routes.services import _latest_metrics_by_service
from app.core.database import get_db
from app.models import AnomalyEvent, Incident, Service
from app.schemas.incident import IncidentSummary
from app.schemas.overview import OverviewResponse


router = APIRouter(prefix="/api/v1", tags=["dashboard"])


def _incident_summary(incident: Incident) -> IncidentSummary:
    return IncidentSummary(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        status=incident.status,
        root_cause_service_id=incident.root_cause_service_id,
        root_cause_service_name=(
            incident.root_cause_service.name if incident.root_cause_service else None
        ),
        affected_services=sorted(service.name for service in incident.affected_services),
        first_detected_at=incident.first_detected_at,
        last_updated_at=incident.last_updated_at,
        resolved_at=incident.resolved_at,
        explanation=incident.explanation,
        recommended_actions=incident.recommended_actions,
    )


@router.get("/overview", response_model=OverviewResponse)
def get_overview(session: Session = Depends(get_db)) -> OverviewResponse:
    services = list(session.scalars(select(Service)).all())
    latest_metrics = _latest_metrics_by_service(session)
    active_incidents = session.scalar(
        select(func.count(Incident.id)).where(
            Incident.status.in_(("OPEN", "INVESTIGATING"))
        )
    ) or 0
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    anomalies_last_day = session.scalar(
        select(func.count(AnomalyEvent.id)).where(
            AnomalyEvent.is_anomaly.is_(True),
            AnomalyEvent.detected_at >= since,
        )
    ) or 0
    recent_incidents = session.scalars(
        select(Incident)
        .options(
            joinedload(Incident.root_cause_service),
            selectinload(Incident.affected_services),
        )
        .order_by(Incident.first_detected_at.desc())
        .limit(5)
    ).unique().all()
    availabilities = [
        metric.service_availability
        for metric in latest_metrics.values()
    ]
    statuses = [service.health_status for service in services]

    return OverviewResponse(
        total_services=len(services),
        healthy_services=statuses.count("HEALTHY"),
        degraded_services=statuses.count("DEGRADED"),
        critical_services=statuses.count("CRITICAL"),
        unknown_services=statuses.count("UNKNOWN"),
        active_incidents=active_incidents,
        anomalies_last_24_hours=anomalies_last_day,
        availability_percent=(
            sum(availabilities) / len(availabilities) if availabilities else None
        ),
        recent_incidents=[_incident_summary(incident) for incident in recent_incidents],
    )

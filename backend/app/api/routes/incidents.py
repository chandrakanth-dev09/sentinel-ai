from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.models import Incident, IncidentEvidence, Service
from app.rca.engine import analyze_incident
from app.schemas.incident import (
    IncidentAnalysisResponse,
    IncidentDetail,
    IncidentSeverity,
    IncidentStatus,
    IncidentSummary,
    IncidentUpdate,
)
from app.schemas.rca import RCARequest, RCAResponse


router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

_STATUS_TRANSITIONS = {
    "OPEN": {"INVESTIGATING", "RESOLVED", "CLOSED"},
    "INVESTIGATING": {"OPEN", "RESOLVED", "CLOSED"},
    "RESOLVED": {"INVESTIGATING", "CLOSED"},
    "CLOSED": set(),
}


def _summary(incident: Incident) -> IncidentSummary:
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


def _detail(incident: Incident) -> IncidentDetail:
    return IncidentDetail(
        **_summary(incident).model_dump(),
        evidence=[
            {
                "id": item.id,
                "evidence_type": item.evidence_type,
                "summary": item.summary,
                "details": item.details,
                "event_timestamp": item.event_timestamp,
                "service_id": item.service_id,
                "metric_id": item.metric_id,
                "application_log_id": item.application_log_id,
                "anomaly_event_id": item.anomaly_event_id,
            }
            for item in incident.evidence
        ],
    )


def _load_incident(session: Session, incident_id: UUID) -> Incident:
    incident = session.scalar(
        select(Incident)
        .options(
            joinedload(Incident.root_cause_service),
            selectinload(Incident.affected_services),
            selectinload(Incident.evidence),
        )
        .where(Incident.id == incident_id)
        .execution_options(populate_existing=True)
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} was not found",
        )
    return incident


@router.get("", response_model=list[IncidentSummary])
def list_incidents(
    severity: IncidentSeverity | None = None,
    incident_status: IncidentStatus | None = Query(default=None, alias="status"),
    service_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> list[IncidentSummary]:
    query = (
        select(Incident)
        .options(joinedload(Incident.root_cause_service), selectinload(Incident.affected_services))
        .order_by(Incident.first_detected_at.desc())
    )
    if severity is not None:
        query = query.where(Incident.severity == severity.value)
    if incident_status is not None:
        query = query.where(Incident.status == incident_status.value)
    if service_id is not None:
        query = query.join(Incident.affected_services).where(Service.id == service_id)
    incidents = session.scalars(query.limit(limit).offset(offset)).unique().all()
    return [_summary(incident) for incident in incidents]


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(
    incident_id: UUID,
    session: Session = Depends(get_db),
) -> IncidentDetail:
    return _detail(_load_incident(session, incident_id))


@router.patch("/{incident_id}", response_model=IncidentDetail)
def update_incident(
    incident_id: UUID,
    payload: IncidentUpdate,
    session: Session = Depends(get_db),
) -> IncidentDetail:
    incident = _load_incident(session, incident_id)
    now = datetime.now(timezone.utc)
    if payload.status is not None and payload.status.value != incident.status:
        if payload.status.value not in _STATUS_TRANSITIONS[incident.status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot transition incident from {incident.status} to {payload.status.value}",
            )
        incident.status = payload.status.value
        if payload.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
            incident.resolved_at = now
            incident.deduplication_key = None
        else:
            incident.resolved_at = None
            if incident.root_cause_service_id is not None:
                deduplication_key = f"anomaly:{incident.root_cause_service_id}"
                other_active = session.scalar(
                    select(Incident.id).where(
                        Incident.deduplication_key == deduplication_key,
                        Incident.id != incident.id,
                        Incident.status.in_(("OPEN", "INVESTIGATING")),
                    )
                )
                if other_active is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="An active incident already exists for this root-cause service",
                    )
                incident.deduplication_key = deduplication_key
    if payload.severity is not None:
        incident.severity = payload.severity.value
    incident.last_updated_at = now
    session.commit()
    return _detail(_load_incident(session, incident.id))


def _analysis_explanation(analysis: RCAResponse) -> str:
    root_cause = analysis.probable_root_cause
    affected = ", ".join(analysis.affected_services) or "no affected services"
    if root_cause is None:
        return (
            f"Analysis found evidence for {affected}, but no upstream root cause met the "
            "dependency-coverage criteria. Review the timeline and supporting evidence."
        )
    evidence_types = sorted({item.evidence_type for item in analysis.supporting_evidence})
    evidence_summary = ", ".join(evidence_types) or "no supporting telemetry"
    return (
        f"{root_cause.service_name} is ranked as the most probable root cause with heuristic "
        f"score {root_cause.ranking_score:.3f}. It precedes and is upstream of "
        f"{root_cause.downstream_affected_count} affected service(s). Evidence includes "
        f"{evidence_summary}. Affected services: {affected}. The ranking is not a calibrated "
        "probability."
    )


@router.post("/{incident_id}/analyze", response_model=IncidentAnalysisResponse)
def analyze_incident_record(
    incident_id: UUID,
    session: Session = Depends(get_db),
) -> IncidentAnalysisResponse:
    incident = _load_incident(session, incident_id)
    now = datetime.now(timezone.utc)
    first_detected_at = incident.first_detected_at
    if first_detected_at.tzinfo is None:
        first_detected_at = first_detected_at.replace(tzinfo=timezone.utc)
    analysis_start = max(
        first_detected_at,
        now - timedelta(days=1),
    )
    analysis_request = RCARequest(
        start_at=analysis_start,
        end_at=now,
    )
    try:
        analysis = analyze_incident(session, analysis_request, now=now)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if analysis.probable_root_cause is not None:
        incident.root_cause_service = session.get(
            Service,
            analysis.probable_root_cause.service_id,
        )
    else:
        incident.root_cause_service = None
    if analysis.affected_services:
        affected_names = set(analysis.affected_services)
        incident.affected_services = list(
            session.scalars(select(Service).where(Service.name.in_(affected_names))).all()
        )
    incident.explanation = _analysis_explanation(analysis)
    incident.recommended_actions = analysis.recommended_investigation_steps
    incident.last_updated_at = now

    existing_evidence = session.scalars(
        select(IncidentEvidence).where(IncidentEvidence.incident_id == incident.id)
    ).all()
    existing_keys = {
        (item.evidence_type, item.event_timestamp, item.summary)
        for item in existing_evidence
    }
    new_evidence = []
    for item in analysis.supporting_evidence:
        evidence_key = (item.evidence_type, item.timestamp, item.summary)
        if evidence_key in existing_keys:
            continue
        new_evidence.append(
            IncidentEvidence(
                incident_id=incident.id,
                evidence_type=item.evidence_type,
                summary=item.summary,
                details={**item.details, "strength": item.strength},
                event_timestamp=item.timestamp,
                service_id=item.service_id,
                metric_id=item.metric_id,
                application_log_id=item.application_log_id,
                anomaly_event_id=item.anomaly_event_id,
            )
        )
        existing_keys.add(evidence_key)
    session.add_all(new_evidence)
    session.commit()

    refreshed = _load_incident(session, incident.id)
    return IncidentAnalysisResponse(incident=_detail(refreshed), analysis=analysis)

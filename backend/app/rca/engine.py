from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnomalyEvent,
    ApplicationLog,
    Incident,
    Service,
    ServiceDependency,
    SystemMetric,
    SystemConfiguration,
)
from app.schemas.rca import (
    RCAEvidence,
    RCACandidate,
    RCARequest,
    RCAResponse,
    RCATimelineEvent,
)
from app.services.configuration import load_configuration


RANKING_METHOD = (
    "Heuristic ranking: 50% downstream coverage, 30% event precedence, "
    "20% evidence strength. Scores are not calibrated probabilities."
)


def _descendants(adjacency: dict[UUID, set[UUID]], start_id: UUID) -> set[UUID]:
    visited: set[UUID] = set()
    queue = deque(adjacency.get(start_id, set()))
    while queue:
        service_id = queue.popleft()
        if service_id in visited:
            continue
        visited.add(service_id)
        queue.extend(adjacency.get(service_id, set()) - visited)
    return visited


def _metric_signal(
    metric: SystemMetric,
    configuration: SystemConfiguration,
) -> tuple[str, float] | None:
    signals: list[tuple[str, float]] = []
    if metric.database_connections == 0:
        signals.append(("Database connection count is zero", 1.0))
    if metric.response_time_ms >= configuration.response_time_warning_ms:
        signals.append(
            (
                f"Response time is {metric.response_time_ms:.1f} ms",
                min(metric.response_time_ms / (configuration.response_time_warning_ms * 3), 1.0),
            )
        )
    if metric.error_rate >= configuration.error_rate_warning_percent:
        signals.append((f"Error rate is {metric.error_rate:.1f}%", min(metric.error_rate / 30, 1.0)))
    if metric.service_availability < configuration.availability_warning_percent:
        signals.append(
            (
                f"Service availability is {metric.service_availability:.1f}%",
                min(
                    (configuration.availability_warning_percent - metric.service_availability)
                    / 40
                    + 0.35,
                    1.0,
                ),
            )
        )
    if not signals:
        return None
    return max(signals, key=lambda signal: signal[1])


def _recommendations(service_name: str | None) -> list[str]:
    if service_name is None:
        return [
            "Inspect recent service metrics and error logs around the first correlated event.",
            "Verify service dependencies and confirm whether the observed failures are ongoing.",
        ]
    name = service_name.lower()
    if "database" in name or "db" in name:
        return [
            "Check database availability, connection-pool saturation, and connection error logs.",
            "Compare database resource and connection metrics with the first downstream latency increase.",
            "Verify that dependent services recover after database connectivity is restored.",
        ]
    return [
        f"Inspect {service_name} logs and resource metrics around its earliest abnormal event.",
        "Check upstream dependencies and recent changes before restarting or rolling back the service.",
        "Confirm downstream services recover after the suspected source is healthy.",
    ]


def analyze_incident(
    session: Session,
    request: RCARequest,
    now: datetime | None = None,
) -> RCAResponse:
    analysis_end = request.end_at or now or datetime.now(timezone.utc)
    analysis_start = request.start_at or (analysis_end - timedelta(minutes=request.lookback_minutes))
    if analysis_start >= analysis_end:
        raise ValueError("analysis start must be earlier than analysis end")
    if analysis_end - analysis_start > timedelta(days=1):
        raise ValueError("analysis window cannot exceed 24 hours")

    services = list(session.scalars(select(Service).order_by(Service.name)).all())
    service_by_id = {service.id: service for service in services}
    selected_ids = set(request.service_ids or service_by_id.keys())
    unknown_ids = selected_ids - set(service_by_id)
    if unknown_ids:
        raise ValueError(f"Unknown service id(s): {', '.join(sorted(map(str, unknown_ids)))}")
    selected_ids.intersection_update(service_by_id)
    if not selected_ids:
        return RCAResponse(
            analysis_start=analysis_start,
            analysis_end=analysis_end,
            probable_root_cause=None,
            affected_services=[],
            incident_timeline=[],
            supporting_evidence=[],
            alternative_causes=[],
            recommended_investigation_steps=_recommendations(None),
            ranking_method=RANKING_METHOD,
        )

    dependencies = list(session.scalars(select(ServiceDependency)).all())
    configuration = load_configuration(session)
    adjacency: dict[UUID, set[UUID]] = defaultdict(set)
    for dependency in dependencies:
        adjacency[dependency.upstream_service_id].add(dependency.downstream_service_id)

    evidence: list[RCAEvidence] = []
    metric_query = select(SystemMetric).where(
        SystemMetric.service_id.in_(selected_ids),
        SystemMetric.timestamp >= analysis_start,
        SystemMetric.timestamp <= analysis_end,
    )
    for metric in session.scalars(metric_query).all():
        signal = _metric_signal(metric, configuration)
        if signal is None:
            continue
        service = service_by_id[metric.service_id]
        summary, strength = signal
        evidence.append(
            RCAEvidence(
                service_id=service.id,
                service_name=service.name,
                evidence_type="METRIC_THRESHOLD",
                timestamp=metric.timestamp,
                summary=summary,
                strength=round(strength, 4),
                details={
                    "response_time_ms": metric.response_time_ms,
                    "error_rate": metric.error_rate,
                    "database_connections": metric.database_connections,
                    "service_availability": metric.service_availability,
                    "source": metric.source,
                },
                metric_id=metric.id,
            )
        )

    anomaly_query = select(AnomalyEvent).where(
        AnomalyEvent.service_id.in_(selected_ids),
        AnomalyEvent.is_anomaly.is_(True),
        AnomalyEvent.detected_at >= analysis_start,
        AnomalyEvent.detected_at <= analysis_end,
    )
    for anomaly in session.scalars(anomaly_query).all():
        service = service_by_id[anomaly.service_id]
        evidence.append(
            RCAEvidence(
                service_id=service.id,
                service_name=service.name,
                evidence_type="ANOMALY",
                timestamp=anomaly.detected_at,
                summary=(
                    f"Model {anomaly.model_version} detected an anomaly "
                    f"(score {anomaly.anomaly_score:.3f}, severity {anomaly.severity})."
                ),
                strength=anomaly.anomaly_score,
                details={
                    "anomaly_score": anomaly.anomaly_score,
                    "severity": anomaly.severity,
                    "contributing_features": anomaly.contributing_features or {},
                },
                metric_id=anomaly.metric_id,
                anomaly_event_id=anomaly.id,
            )
        )

    log_query = select(ApplicationLog).where(
        ApplicationLog.service_id.in_(selected_ids),
        ApplicationLog.level.in_(("ERROR", "CRITICAL")),
        ApplicationLog.timestamp >= analysis_start,
        ApplicationLog.timestamp <= analysis_end,
    )
    for log in session.scalars(log_query).all():
        service = service_by_id[log.service_id]
        evidence.append(
            RCAEvidence(
                service_id=service.id,
                service_name=service.name,
                evidence_type="ERROR_LOG",
                timestamp=log.timestamp,
                summary=log.message[:500],
                strength=1.0 if log.level == "CRITICAL" else 0.65,
                details={
                    "level": log.level,
                    "error_type": log.error_type,
                    "trace_id": log.trace_id,
                    "request_id": log.request_id,
                    "source": log.source,
                },
                application_log_id=log.id,
            )
        )

    evidence.sort(key=lambda item: item.timestamp)
    evidence = evidence[:500]
    evidence_by_service: dict[UUID, list[RCAEvidence]] = defaultdict(list)
    for item in evidence:
        evidence_by_service[item.service_id].append(item)

    affected_ids = set(evidence_by_service)
    candidates: list[RCACandidate] = []
    if len(affected_ids) > 1:
        first_signal_by_service = {
            service_id: min(item.timestamp for item in items)
            for service_id, items in evidence_by_service.items()
        }
        latest_signal = max(first_signal_by_service.values())
        total_window_seconds = max((analysis_end - analysis_start).total_seconds(), 1)
        for service_id, items in evidence_by_service.items():
            downstream = _descendants(adjacency, service_id)
            affected_downstream = downstream & affected_ids
            possible_downstream = affected_ids - {service_id}
            coverage = (
                len(affected_downstream) / len(possible_downstream)
                if possible_downstream
                else 0.0
            )
            lead_seconds = max(
                0.0,
                (latest_signal - first_signal_by_service[service_id]).total_seconds(),
            )
            precedence = min(lead_seconds / total_window_seconds, 1.0)
            evidence_strength = sum(item.strength for item in items) / len(items)
            score = 0.5 * coverage + 0.3 * precedence + 0.2 * evidence_strength
            service = service_by_id[service_id]
            candidates.append(
                RCACandidate(
                    service_id=service_id,
                    service_name=service.name,
                    ranking_score=round(score, 4),
                    downstream_affected_count=len(affected_downstream),
                    first_signal_at=first_signal_by_service[service_id],
                    supporting_evidence_count=len(items),
                )
            )
        candidates.sort(
            key=lambda item: (
                item.ranking_score,
                -item.first_signal_at.timestamp(),
                item.supporting_evidence_count,
            ),
            reverse=True,
        )

    root_candidate = (
        candidates[0]
        if candidates and candidates[0].downstream_affected_count > 0
        else None
    )
    alternatives = candidates[1:6]
    timeline = [
        RCATimelineEvent(
            timestamp=item.timestamp,
            service_id=item.service_id,
            service_name=item.service_name,
            evidence_type=item.evidence_type,
            summary=item.summary,
        )
        for item in evidence
    ]
    affected_names = sorted(service_by_id[service_id].name for service_id in affected_ids)
    return RCAResponse(
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        probable_root_cause=root_candidate,
        affected_services=affected_names,
        incident_timeline=timeline,
        supporting_evidence=evidence,
        alternative_causes=alternatives,
        recommended_investigation_steps=_recommendations(
            root_candidate.service_name if root_candidate else None
        ),
        ranking_method=RANKING_METHOD,
    )

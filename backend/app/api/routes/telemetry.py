from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import ApplicationLog, Service, SystemMetric
from app.schemas.telemetry import (
    IngestResponse,
    LogRead,
    LogsBatchIngest,
    MetricRead,
    MetricIngestItem,
    MetricsBatchIngest,
)
from app.services.configuration import classify_service_health, load_configuration


metrics_router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])
logs_router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


def _validate_batch_size(batch_size: int) -> None:
    if batch_size > settings.MAX_INGEST_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch exceeds the limit of {settings.MAX_INGEST_BATCH_SIZE} records",
        )


def _require_services(session: Session, service_ids: set[UUID]) -> dict[UUID, Service]:
    if not service_ids:
        return {}
    services = list(session.scalars(select(Service).where(Service.id.in_(service_ids))).all())
    services_by_id = {service.id: service for service in services}
    missing_ids = service_ids - set(services_by_id)
    if missing_ids:
        missing = ", ".join(sorted(str(service_id) for service_id in missing_ids))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown service id(s): {missing}",
        )
    return services_by_id


def _utc_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


@metrics_router.get("", response_model=list[MetricRead])
def list_metrics(
    service_id: UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> list[SystemMetric]:
    if since is not None and until is not None and since > until:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'since' must be earlier than or equal to 'until'",
        )
    query = select(SystemMetric)
    if service_id is not None:
        query = query.where(SystemMetric.service_id == service_id)
    if since is not None:
        query = query.where(SystemMetric.timestamp >= since)
    if until is not None:
        query = query.where(SystemMetric.timestamp <= until)
    query = query.order_by(SystemMetric.timestamp.asc()).limit(limit).offset(offset)
    return list(session.scalars(query).all())


@metrics_router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_metrics(payload: MetricsBatchIngest, session: Session = Depends(get_db)) -> IngestResponse:
    _validate_batch_size(len(payload.metrics))
    services_by_id = _require_services(
        session,
        {item.service_id for item in payload.metrics},
    )
    configuration = load_configuration(session)

    records = [
        SystemMetric(
            service_id=item.service_id,
            timestamp=item.timestamp,
            cpu_utilization=item.cpu_utilization,
            memory_utilization=item.memory_utilization,
            disk_utilization=item.disk_utilization,
            network_traffic=item.network_traffic,
            response_time_ms=item.response_time_ms,
            request_count=item.request_count,
            error_rate=item.error_rate,
            database_connections=item.database_connections,
            service_availability=item.service_availability,
            source=item.source.value,
        )
        for item in payload.metrics
    ]
    latest_in_batch: dict[UUID, SystemMetric] = {}
    for record in records:
        current = latest_in_batch.get(record.service_id)
        if current is None or _utc_datetime(record.timestamp) > _utc_datetime(current.timestamp):
            latest_in_batch[record.service_id] = record

    latest_persisted = {
        service_id: timestamp
        for service_id, timestamp in session.execute(
            select(SystemMetric.service_id, func.max(SystemMetric.timestamp))
            .where(SystemMetric.service_id.in_(services_by_id))
            .group_by(SystemMetric.service_id)
        )
    }
    for service_id, record in latest_in_batch.items():
        persisted_timestamp = latest_persisted.get(service_id)
        if (
            persisted_timestamp is None
            or _utc_datetime(record.timestamp) >= _utc_datetime(persisted_timestamp)
        ):
            services_by_id[service_id].health_status = classify_service_health(
                record,
                configuration,
            )
    session.add_all(records)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Metrics could not be stored because of a data conflict",
        ) from exc

    return IngestResponse(accepted_count=len(records), ids=[record.id for record in records])


@logs_router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_logs(payload: LogsBatchIngest, session: Session = Depends(get_db)) -> IngestResponse:
    _validate_batch_size(len(payload.logs))
    _require_services(session, {item.service_id for item in payload.logs})

    records = [
        ApplicationLog(
            service_id=item.service_id,
            timestamp=item.timestamp,
            level=item.level.value,
            message=item.message,
            error_type=item.error_type,
            trace_id=item.trace_id,
            request_id=item.request_id,
            source=item.source.value,
            attributes=item.attributes,
        )
        for item in payload.logs
    ]
    session.add_all(records)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Logs could not be stored because of a data conflict",
        ) from exc

    return IngestResponse(accepted_count=len(records), ids=[record.id for record in records])


@logs_router.get("", response_model=list[LogRead])
def search_logs(
    service_id: UUID | None = None,
    level: str | None = Query(default=None, pattern="^(INFO|WARNING|ERROR|CRITICAL)$"),
    since: datetime | None = None,
    until: datetime | None = None,
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> list[ApplicationLog]:
    if since is not None and until is not None and since > until:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'since' must be earlier than or equal to 'until'",
        )

    query = select(ApplicationLog)
    if service_id is not None:
        query = query.where(ApplicationLog.service_id == service_id)
    if level is not None:
        query = query.where(ApplicationLog.level == level)
    if since is not None:
        query = query.where(ApplicationLog.timestamp >= since)
    if until is not None:
        query = query.where(ApplicationLog.timestamp <= until)
    if search:
        query = query.where(ApplicationLog.message.ilike(f"%{search}%"))
    query = query.order_by(ApplicationLog.timestamp.desc()).limit(limit).offset(offset)
    return list(session.scalars(query).all())

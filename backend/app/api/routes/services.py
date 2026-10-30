from collections import defaultdict, deque
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import Incident, Service, ServiceDependency, SystemMetric
from app.schemas.rca import (
    DependencyCreate,
    DependencyRead,
    ServiceDependencyGraph,
    ServiceGraphNode,
    LatestMetricSummary,
)
from app.schemas.service import ServiceCreate, ServiceRead
from app.schemas.service import ServiceMetricSummary, ServiceMonitoringRead


router = APIRouter(prefix="/api/v1/services", tags=["services"])


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def register_service(
    payload: ServiceCreate,
    session: Session = Depends(get_db),
) -> Service:
    existing = session.scalar(select(Service).where(Service.name == payload.name))
    if existing is not None:
        if existing.is_simulated != payload.is_simulated:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Service already exists with a different data source classification",
            )
        return existing

    service = Service(
        name=payload.name,
        description=payload.description,
        is_simulated=payload.is_simulated,
    )
    session.add(service)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service name is already registered",
        ) from exc
    session.refresh(service)
    return service


@router.get("", response_model=list[ServiceRead])
def list_services(
    session: Session = Depends(get_db),
) -> list[Service]:
    return list(session.scalars(select(Service).order_by(Service.name)).all())


def _dependency_path_exists(
    session: Session,
    start_id: UUID,
    target_id: UUID,
) -> bool:
    edges = session.scalars(select(ServiceDependency)).all()
    adjacency: dict[UUID, set[UUID]] = defaultdict(set)
    for edge in edges:
        adjacency[edge.upstream_service_id].add(edge.downstream_service_id)

    visited: set[UUID] = set()
    queue = deque([start_id])
    while queue:
        current = queue.popleft()
        if current == target_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        queue.extend(adjacency[current] - visited)
    return False


@router.post("/dependencies", response_model=DependencyRead, status_code=status.HTTP_201_CREATED)
def register_dependency(
    payload: DependencyCreate,
    session: Session = Depends(get_db),
) -> ServiceDependency:
    if payload.upstream_service_id == payload.downstream_service_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A service cannot depend on itself",
        )

    service_ids = {
        payload.upstream_service_id,
        payload.downstream_service_id,
    }
    found = set(
        session.scalars(select(Service.id).where(Service.id.in_(service_ids))).all()
    )
    if found != service_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Both services must be registered before adding a dependency",
        )

    existing = session.get(
        ServiceDependency,
        (payload.upstream_service_id, payload.downstream_service_id),
    )
    if existing is not None:
        return existing
    if _dependency_path_exists(
        session,
        payload.downstream_service_id,
        payload.upstream_service_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dependency would introduce a cycle in the service graph",
        )

    dependency = ServiceDependency(
        upstream_service_id=payload.upstream_service_id,
        downstream_service_id=payload.downstream_service_id,
    )
    session.add(dependency)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dependency could not be stored",
        ) from exc
    return dependency


@router.get("/dependency-graph", response_model=ServiceDependencyGraph)
def dependency_graph(
    session: Session = Depends(get_db),
) -> ServiceDependencyGraph:
    services = list(session.scalars(select(Service).order_by(Service.name)).all())
    dependencies = list(session.scalars(select(ServiceDependency)).all())

    latest_metric_by_service = _latest_metrics_by_service(session)

    active_incident_ids: dict[UUID, list[UUID]] = defaultdict(list)
    active_incidents = session.scalars(
        select(Incident)
        .options(selectinload(Incident.affected_services))
        .where(Incident.status.in_(("OPEN", "INVESTIGATING")))
    ).all()
    for incident in active_incidents:
        for service in incident.affected_services:
            active_incident_ids[service.id].append(incident.id)

    nodes = []
    for service in services:
        metric = latest_metric_by_service.get(service.id)
        nodes.append(
            ServiceGraphNode(
                id=service.id,
                name=service.name,
                health_status=service.health_status,
                is_simulated=service.is_simulated,
                latest_metrics=(
                    LatestMetricSummary(
                        timestamp=metric.timestamp,
                        cpu_utilization=metric.cpu_utilization,
                        memory_utilization=metric.memory_utilization,
                        response_time_ms=metric.response_time_ms,
                        error_rate=metric.error_rate,
                        service_availability=metric.service_availability,
                    )
                    if metric is not None
                    else None
                ),
                active_incident_ids=active_incident_ids[service.id],
            )
        )

    return ServiceDependencyGraph(
        nodes=nodes,
        edges=[
            DependencyRead(
                upstream_service_id=edge.upstream_service_id,
                downstream_service_id=edge.downstream_service_id,
            )
            for edge in dependencies
        ],
    )


def _latest_metrics_by_service(session: Session) -> dict[UUID, SystemMetric]:
    latest_timestamps = (
        select(
            SystemMetric.service_id.label("service_id"),
            func.max(SystemMetric.timestamp).label("latest_timestamp"),
        )
        .group_by(SystemMetric.service_id)
        .subquery()
    )
    metric_query = select(SystemMetric).join(
        latest_timestamps,
        and_(
            SystemMetric.service_id == latest_timestamps.c.service_id,
            SystemMetric.timestamp == latest_timestamps.c.latest_timestamp,
        ),
    )
    latest: dict[UUID, SystemMetric] = {}
    for metric in session.scalars(metric_query).all():
        latest.setdefault(metric.service_id, metric)
    return latest


@router.get("/monitoring", response_model=list[ServiceMonitoringRead])
def list_service_monitoring(
    session: Session = Depends(get_db),
) -> list[ServiceMonitoringRead]:
    services = list(session.scalars(select(Service).order_by(Service.name)).all())
    latest_metrics = _latest_metrics_by_service(session)
    return [
        ServiceMonitoringRead(
            id=service.id,
            name=service.name,
            description=service.description,
            health_status=service.health_status,
            is_simulated=service.is_simulated,
            created_at=service.created_at,
            updated_at=service.updated_at,
            latest_metrics=latest_metrics.get(service.id),
        )
        for service in services
    ]


@router.get("/{service_id}", response_model=ServiceMonitoringRead)
def get_service_monitoring(
    service_id: UUID,
    session: Session = Depends(get_db),
) -> ServiceMonitoringRead:
    service = session.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    metric = _latest_metrics_by_service(session).get(service_id)
    return ServiceMonitoringRead(
        id=service.id,
        name=service.name,
        description=service.description,
        health_status=service.health_status,
        is_simulated=service.is_simulated,
        created_at=service.created_at,
        updated_at=service.updated_at,
        latest_metrics=metric,
    )

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field


class DependencyCreate(BaseModel):
    upstream_service_id: UUID
    downstream_service_id: UUID


class DependencyRead(BaseModel):
    upstream_service_id: UUID
    downstream_service_id: UUID


class LatestMetricSummary(BaseModel):
    timestamp: datetime
    cpu_utilization: float
    memory_utilization: float
    response_time_ms: float
    error_rate: float
    service_availability: float


class ServiceGraphNode(BaseModel):
    id: UUID
    name: str
    health_status: str
    is_simulated: bool
    latest_metrics: LatestMetricSummary | None
    active_incident_ids: list[UUID]


class ServiceDependencyGraph(BaseModel):
    nodes: list[ServiceGraphNode]
    edges: list[DependencyRead]


class RCARequest(BaseModel):
    lookback_minutes: Annotated[int, Field(ge=1, le=1440)] = 15
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    service_ids: Annotated[list[UUID], Field(min_length=1)] | None = None


class RCAEvidence(BaseModel):
    service_id: UUID
    service_name: str
    evidence_type: str
    timestamp: datetime
    summary: str
    strength: float
    details: dict[str, object]
    metric_id: UUID | None = None
    application_log_id: UUID | None = None
    anomaly_event_id: UUID | None = None


class RCACandidate(BaseModel):
    service_id: UUID
    service_name: str
    ranking_score: float
    downstream_affected_count: int
    first_signal_at: datetime
    supporting_evidence_count: int


class RCATimelineEvent(BaseModel):
    timestamp: datetime
    service_id: UUID
    service_name: str
    evidence_type: str
    summary: str


class RCAResponse(BaseModel):
    analysis_start: datetime
    analysis_end: datetime
    probable_root_cause: RCACandidate | None
    affected_services: list[str]
    incident_timeline: list[RCATimelineEvent]
    supporting_evidence: list[RCAEvidence]
    alternative_causes: list[RCACandidate]
    recommended_investigation_steps: list[str]
    ranking_method: str

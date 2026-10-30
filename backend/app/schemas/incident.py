from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.rca import RCAResponse


class IncidentSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class IncidentEvidenceRead(BaseModel):
    id: UUID
    evidence_type: str
    summary: str
    details: dict[str, object] | None
    event_timestamp: datetime
    service_id: UUID | None
    metric_id: UUID | None
    application_log_id: UUID | None
    anomaly_event_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class IncidentSummary(BaseModel):
    id: UUID
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    root_cause_service_id: UUID | None
    root_cause_service_name: str | None
    affected_services: list[str]
    first_detected_at: datetime
    last_updated_at: datetime
    resolved_at: datetime | None
    explanation: str | None
    recommended_actions: list[str] | None


class IncidentDetail(IncidentSummary):
    evidence: list[IncidentEvidenceRead]


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    severity: IncidentSeverity | None = None

    @model_validator(mode="after")
    def require_an_update(self) -> "IncidentUpdate":
        if self.status is None and self.severity is None:
            raise ValueError("Provide at least one field to update")
        return self


class IncidentAnalysisResponse(BaseModel):
    incident: IncidentDetail
    analysis: RCAResponse


class IncidentQueryFilters(BaseModel):
    severity: IncidentSeverity | None = Field(default=None)
    status: IncidentStatus | None = Field(default=None)

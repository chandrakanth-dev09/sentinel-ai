from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


class TelemetrySource(StrEnum):
    SIMULATED = "SIMULATED"
    AGENT = "AGENT"
    IMPORTED = "IMPORTED"


class LogLevel(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TimestampedIngestItem(BaseModel):
    timestamp: AwareDatetime

    @field_validator("timestamp")
    @classmethod
    def reject_far_future_timestamp(cls, value: datetime) -> datetime:
        latest_allowed = datetime.now(timezone.utc) + timedelta(
            seconds=settings.MAX_FUTURE_TIMESTAMP_SKEW_SECONDS
        )
        if value > latest_allowed:
            raise ValueError("timestamp is too far in the future")
        return value


class MetricIngestItem(TimestampedIngestItem):
    service_id: UUID
    cpu_utilization: Annotated[float, Field(ge=0, le=100)]
    memory_utilization: Annotated[float, Field(ge=0, le=100)]
    disk_utilization: Annotated[float, Field(ge=0, le=100)]
    network_traffic: Annotated[float, Field(ge=0)]
    response_time_ms: Annotated[float, Field(ge=0)]
    request_count: Annotated[int, Field(ge=0)]
    error_rate: Annotated[float, Field(ge=0, le=100)]
    database_connections: Annotated[int, Field(ge=0)]
    service_availability: Annotated[float, Field(ge=0, le=100)]
    source: TelemetrySource = TelemetrySource.AGENT


class MetricsBatchIngest(BaseModel):
    metrics: Annotated[list[MetricIngestItem], Field(min_length=1)]


class LogIngestItem(TimestampedIngestItem):
    service_id: UUID
    level: LogLevel
    message: Annotated[str, Field(min_length=1, max_length=10000)]
    error_type: Annotated[str | None, Field(max_length=200)] = None
    trace_id: Annotated[str | None, Field(max_length=128)] = None
    request_id: Annotated[str | None, Field(max_length=128)] = None
    source: TelemetrySource = TelemetrySource.AGENT
    attributes: dict[str, object] | None = None


class LogsBatchIngest(BaseModel):
    logs: Annotated[list[LogIngestItem], Field(min_length=1)]


class IngestResponse(BaseModel):
    accepted_count: int
    ids: list[UUID]


class LogRead(BaseModel):
    id: UUID
    service_id: UUID
    timestamp: datetime
    level: LogLevel
    message: str
    error_type: str | None
    trace_id: str | None
    request_id: str | None
    source: TelemetrySource
    attributes: dict[str, object] | None

    model_config = ConfigDict(from_attributes=True)


class MetricRead(BaseModel):
    id: UUID
    service_id: UUID
    timestamp: datetime
    cpu_utilization: float
    memory_utilization: float
    disk_utilization: float
    network_traffic: float
    response_time_ms: float
    request_count: int
    error_rate: float
    database_connections: int
    service_availability: float
    source: TelemetrySource

    model_config = ConfigDict(from_attributes=True)

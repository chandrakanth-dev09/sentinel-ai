from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str | None, Field(max_length=500)] = None
    is_simulated: bool = False


class ServiceRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    health_status: str
    is_simulated: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceMetricSummary(BaseModel):
    timestamp: datetime
    cpu_utilization: float
    memory_utilization: float
    disk_utilization: float
    response_time_ms: float
    error_rate: float
    service_availability: float
    database_connections: int
    source: str

    model_config = ConfigDict(from_attributes=True)


class ServiceMonitoringRead(ServiceRead):
    latest_metrics: ServiceMetricSummary | None

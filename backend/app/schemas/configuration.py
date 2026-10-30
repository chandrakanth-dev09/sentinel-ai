from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class ConfigurationRead(BaseModel):
    monitoring_interval_seconds: int
    cpu_warning_percent: float
    memory_warning_percent: float
    disk_warning_percent: float
    response_time_warning_ms: float
    error_rate_warning_percent: float
    availability_warning_percent: float
    updated_at: datetime


class ConfigurationUpdate(BaseModel):
    monitoring_interval_seconds: Annotated[int | None, Field(ge=1, le=3600)] = None
    cpu_warning_percent: Annotated[float | None, Field(ge=0, le=100)] = None
    memory_warning_percent: Annotated[float | None, Field(ge=0, le=100)] = None
    disk_warning_percent: Annotated[float | None, Field(ge=0, le=100)] = None
    response_time_warning_ms: Annotated[float | None, Field(gt=0)] = None
    error_rate_warning_percent: Annotated[float | None, Field(ge=0, le=100)] = None
    availability_warning_percent: Annotated[float | None, Field(ge=0, le=100)] = None

    @model_validator(mode="after")
    def require_an_update(self) -> "ConfigurationUpdate":
        if not any(getattr(self, field_name) is not None for field_name in self.model_fields_set):
            raise ValueError("Provide at least one setting to update")
        return self

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AnomalyDetectRequest(BaseModel):
    service_id: UUID
    metric_id: UUID | None = None


class AnomalyDetectResponse(BaseModel):
    anomaly_event_id: UUID
    service_id: UUID
    metric_id: UUID
    is_anomaly: bool
    anomaly_score: float
    severity: str
    model_version: str
    detected_at: datetime
    contributing_features: dict[str, dict[str, float]]


class ModelStatusResponse(BaseModel):
    is_trained: bool
    model_name: str | None = None
    version: str | None = None
    trained_at: str | None = None
    dataset_name: str | None = None
    dataset_source: str | None = None
    evaluation_metrics: dict[str, float] | None = None
    detail: str | None = None


class AnomalyHistoryItem(BaseModel):
    anomaly_event_id: UUID
    service_id: UUID
    service_name: str
    metric_id: UUID | None
    is_anomaly: bool
    anomaly_score: float
    severity: str
    model_version: str
    detected_at: datetime


class AnomalyHistoryResponse(BaseModel):
    total: int
    items: list[AnomalyHistoryItem]

from pydantic import BaseModel

from app.schemas.incident import IncidentSummary


class OverviewResponse(BaseModel):
    total_services: int
    healthy_services: int
    degraded_services: int
    critical_services: int
    unknown_services: int
    active_incidents: int
    anomalies_last_24_hours: int
    availability_percent: float | None
    recent_incidents: list[IncidentSummary]

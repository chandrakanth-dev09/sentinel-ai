from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"
    __table_args__ = (
        CheckConstraint("anomaly_score BETWEEN 0 AND 1", name="ck_anomaly_score_range"),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_anomaly_severity",
        ),
        Index("ix_anomaly_service_detected", "service_id", "detected_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    service_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    metric_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("system_metrics.id", ondelete="SET NULL")
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    contributing_features: Mapped[dict[str, object] | None] = mapped_column(JSON)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    service: Mapped["Service"] = relationship()

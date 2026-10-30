from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class SystemMetric(Base):
    __tablename__ = "system_metrics"
    __table_args__ = (
        CheckConstraint("cpu_utilization BETWEEN 0 AND 100", name="ck_metrics_cpu_range"),
        CheckConstraint("memory_utilization BETWEEN 0 AND 100", name="ck_metrics_memory_range"),
        CheckConstraint("disk_utilization BETWEEN 0 AND 100", name="ck_metrics_disk_range"),
        CheckConstraint("network_traffic >= 0", name="ck_metrics_network_nonnegative"),
        CheckConstraint("response_time_ms >= 0", name="ck_metrics_response_nonnegative"),
        CheckConstraint("request_count >= 0", name="ck_metrics_request_nonnegative"),
        CheckConstraint("error_rate BETWEEN 0 AND 100", name="ck_metrics_error_rate_range"),
        CheckConstraint("database_connections >= 0", name="ck_metrics_connections_nonnegative"),
        CheckConstraint(
            "service_availability BETWEEN 0 AND 100",
            name="ck_metrics_availability_range",
        ),
        CheckConstraint(
            "source IN ('SIMULATED', 'AGENT', 'IMPORTED')",
            name="ck_metrics_source",
        ),
        Index("ix_metrics_service_timestamp", "service_id", "timestamp"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    service_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    cpu_utilization: Mapped[float] = mapped_column(Float, nullable=False)
    memory_utilization: Mapped[float] = mapped_column(Float, nullable=False)
    disk_utilization: Mapped[float] = mapped_column(Float, nullable=False)
    network_traffic: Mapped[float] = mapped_column(Float, nullable=False)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_rate: Mapped[float] = mapped_column(Float, nullable=False)
    database_connections: Mapped[int] = mapped_column(Integer, nullable=False)
    service_availability: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="AGENT", server_default="AGENT"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    service: Mapped["Service"] = relationship()


class ApplicationLog(Base):
    __tablename__ = "application_logs"
    __table_args__ = (
        CheckConstraint(
            "level IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name="ck_application_logs_level",
        ),
        CheckConstraint(
            "source IN ('SIMULATED', 'AGENT', 'IMPORTED')",
            name="ck_application_logs_source",
        ),
        Index("ix_logs_service_timestamp", "service_id", "timestamp"),
        Index("ix_logs_trace_id", "trace_id"),
        Index("ix_logs_request_id", "request_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    service_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(200))
    trace_id: Mapped[str | None] = mapped_column(String(128))
    request_id: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="AGENT", server_default="AGENT"
    )
    attributes: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    service: Mapped["Service"] = relationship()

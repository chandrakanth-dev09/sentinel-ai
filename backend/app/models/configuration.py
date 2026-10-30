from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, Integer, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemConfiguration(Base):
    __tablename__ = "system_configuration"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_system_configuration_singleton"),
        CheckConstraint(
            "monitoring_interval_seconds BETWEEN 1 AND 3600",
            name="ck_configuration_monitoring_interval",
        ),
        CheckConstraint("cpu_warning_percent BETWEEN 0 AND 100", name="ck_configuration_cpu"),
        CheckConstraint(
            "memory_warning_percent BETWEEN 0 AND 100",
            name="ck_configuration_memory",
        ),
        CheckConstraint("disk_warning_percent BETWEEN 0 AND 100", name="ck_configuration_disk"),
        CheckConstraint(
            "error_rate_warning_percent BETWEEN 0 AND 100",
            name="ck_configuration_error_rate",
        ),
        CheckConstraint(
            "availability_warning_percent BETWEEN 0 AND 100",
            name="ck_configuration_availability",
        ),
        CheckConstraint(
            "response_time_warning_ms > 0",
            name="ck_configuration_response_time",
        ),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    monitoring_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    cpu_warning_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=80, server_default="80"
    )
    memory_warning_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=85, server_default="85"
    )
    disk_warning_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=90, server_default="90"
    )
    response_time_warning_ms: Mapped[float] = mapped_column(
        Float, nullable=False, default=500, server_default="500"
    )
    error_rate_warning_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=5, server_default="5"
    )
    availability_warning_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=99, server_default="99"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

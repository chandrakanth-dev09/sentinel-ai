from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint(
            "health_status IN ('UNKNOWN', 'HEALTHY', 'DEGRADED', 'CRITICAL')",
            name="ck_services_health_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    health_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="UNKNOWN", server_default="UNKNOWN"
    )
    is_simulated: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    upstream_dependencies: Mapped[list["ServiceDependency"]] = relationship(
        back_populates="downstream_service",
        foreign_keys="ServiceDependency.downstream_service_id",
        cascade="all, delete-orphan",
    )
    downstream_dependencies: Mapped[list["ServiceDependency"]] = relationship(
        back_populates="upstream_service",
        foreign_keys="ServiceDependency.upstream_service_id",
        cascade="all, delete-orphan",
    )


class ServiceDependency(Base):
    __tablename__ = "service_dependencies"
    __table_args__ = (
        CheckConstraint(
            "upstream_service_id <> downstream_service_id",
            name="ck_service_dependencies_not_self",
        ),
    )

    upstream_service_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    )
    downstream_service_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    upstream_service: Mapped[Service] = relationship(
        back_populates="downstream_dependencies",
        foreign_keys=[upstream_service_id],
    )
    downstream_service: Mapped[Service] = relationship(
        back_populates="upstream_dependencies",
        foreign_keys=[downstream_service_id],
    )

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


class MLModelMetadata(Base):
    __tablename__ = "ml_model_metadata"
    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_ml_model_name_version"),
        Index("ix_ml_model_active_trained", "is_active", "trained_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(240), nullable=False)
    dataset_source: Mapped[str | None] = mapped_column(String(1000))
    feature_names: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evaluation_metrics: Mapped[dict[str, object] | None] = mapped_column(JSON)
    artifact_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

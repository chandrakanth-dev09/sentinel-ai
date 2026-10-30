import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import PROJECT_ROOT, settings
from app.core.database import get_db
from app.ml.detector import (
    MODEL_NAME,
    MODEL_VERSION,
    ModelBundle,
    feature_deviations,
    load_bundle,
    predict_one,
    severity_for_score,
)
from app.ml.features import metric_to_features
from app.models import AnomalyEvent, SystemMetric
from app.services.incident_service import create_or_update_anomaly_incident
from app.schemas.ml import (
    AnomalyDetectRequest,
    AnomalyDetectResponse,
    AnomalyHistoryItem,
    AnomalyHistoryResponse,
    ModelStatusResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ml", tags=["machine learning"])


def get_model_path() -> Path:
    configured = Path(settings.MODEL_PATH)
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


@lru_cache(maxsize=1)
def _load_cached_bundle(path: str) -> ModelBundle:
    return load_bundle(Path(path))


def _get_model_bundle() -> ModelBundle:
    return _load_cached_bundle(str(get_model_path()))


@router.get("/model-status", response_model=ModelStatusResponse)
def model_status() -> ModelStatusResponse:
    path = get_model_path()
    if not path.is_file():
        return ModelStatusResponse(
            is_trained=False,
            detail=f"No trained model artifact found at {path}. Run `python -m app.ml.train`.",
        )
    try:
        bundle = _get_model_bundle()
    except (OSError, ValueError, KeyError) as exc:
        logger.exception("Could not load the configured anomaly model")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The configured model artifact is unreadable or incompatible",
        ) from exc
    return ModelStatusResponse(
        is_trained=True,
        model_name=MODEL_NAME,
        version=MODEL_VERSION,
        trained_at=bundle.trained_at,
        dataset_name=bundle.dataset_name,
        dataset_source=bundle.dataset_source,
        evaluation_metrics=bundle.evaluation_metrics,
    )


@router.get("/anomaly-history", response_model=AnomalyHistoryResponse)
def anomaly_history(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> AnomalyHistoryResponse:
    total = session.scalar(select(func.count(AnomalyEvent.id))) or 0
    events = session.scalars(
        select(AnomalyEvent)
        .options(joinedload(AnomalyEvent.service))
        .order_by(AnomalyEvent.detected_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return AnomalyHistoryResponse(
        total=total,
        items=[
            AnomalyHistoryItem(
                anomaly_event_id=event.id,
                service_id=event.service_id,
                service_name=event.service.name,
                metric_id=event.metric_id,
                is_anomaly=event.is_anomaly,
                anomaly_score=event.anomaly_score,
                severity=event.severity,
                model_version=event.model_version,
                detected_at=event.detected_at,
            )
            for event in events
        ],
    )


@router.post("/detect-anomaly", response_model=AnomalyDetectResponse)
def detect_anomaly(
    payload: AnomalyDetectRequest,
    session: Session = Depends(get_db),
) -> AnomalyDetectResponse:
    query = select(SystemMetric).where(SystemMetric.service_id == payload.service_id)
    if payload.metric_id is not None:
        query = query.where(SystemMetric.id == payload.metric_id)
    else:
        query = query.order_by(SystemMetric.timestamp.desc())
    metric = session.scalar(query.limit(1))
    if metric is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ingested metric was found for this service and metric ID",
        )

    try:
        bundle = _get_model_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No trained model is available; train the model before requesting detection",
        ) from exc
    except (OSError, ValueError, KeyError) as exc:
        logger.exception("Could not load the configured anomaly model")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The configured model artifact is unreadable or incompatible",
        ) from exc

    features = metric_to_features(metric)
    is_anomaly, anomaly_score = predict_one(bundle, features)
    severity = severity_for_score(anomaly_score) if is_anomaly else "LOW"
    detected_at = datetime.now(timezone.utc)
    event = AnomalyEvent(
        service_id=metric.service_id,
        metric_id=metric.id,
        model_version=MODEL_VERSION,
        is_anomaly=is_anomaly,
        anomaly_score=anomaly_score,
        severity=severity,
        contributing_features=feature_deviations(bundle, features),
        detected_at=detected_at,
    )
    session.add(event)
    session.flush()
    if is_anomaly:
        create_or_update_anomaly_incident(session, event, metric)
    session.commit()
    session.refresh(event)

    return AnomalyDetectResponse(
        anomaly_event_id=event.id,
        service_id=event.service_id,
        metric_id=metric.id,
        is_anomaly=event.is_anomaly,
        anomaly_score=event.anomaly_score,
        severity=event.severity,
        model_version=event.model_version,
        detected_at=event.detected_at,
        contributing_features=event.contributing_features or {},
    )

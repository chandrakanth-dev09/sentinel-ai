from datetime import datetime, timezone

import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import ml
from app.core.config import settings
from app.ml.detector import load_bundle, predict_one
from app.ml.features import FEATURE_NAMES
from app.ml.synthetic_data import (
    generate_evaluation_data,
    generate_training_data,
)
from app.ml.training import train_evaluate_and_save
from app.models import AnomalyEvent, Incident, IncidentEvidence


def test_synthetic_dataset_generation_is_reproducible() -> None:
    first_training = generate_training_data(count=50, seed=7)
    second_training = generate_training_data(count=50, seed=7)
    first_eval, first_labels, first_scenarios = generate_evaluation_data(10, 5, seed=8)
    second_eval, second_labels, second_scenarios = generate_evaluation_data(10, 5, seed=8)

    assert first_training.equals(second_training)
    assert first_eval.equals(second_eval)
    assert np.array_equal(first_labels, second_labels)
    assert first_scenarios == second_scenarios
    assert set(FEATURE_NAMES) == set(first_training.columns)


def test_model_training_persistence_prediction_and_missing_values(tmp_path) -> None:
    artifact = tmp_path / "isolation_forest.joblib"
    bundle, metrics = train_evaluate_and_save(
        output_path=artifact,
        training_samples=500,
        evaluation_normal_samples=60,
        anomalies_per_scenario=20,
    )
    loaded_bundle = load_bundle(artifact)
    sample = generate_training_data(count=10, seed=91).iloc[0].to_dict()
    sample["memory_utilization"] = float("nan")

    prediction, score = predict_one(loaded_bundle, sample)

    assert artifact.is_file()
    assert bundle.feature_names == FEATURE_NAMES
    assert 0 <= score <= 1
    assert isinstance(prediction, bool)
    assert 0 <= metrics["precision"] <= 1
    assert 0 <= metrics["recall"] <= 1
    assert 0 <= metrics["f1"] <= 1
    assert 0 <= metrics["false_positive_rate"] <= 1
    assert metrics["mean_prediction_latency_ms"] >= 0
    assert set(name for name in metrics if name.startswith("recall_")) == {
        "recall_api_latency_spike",
        "recall_cascading_failure",
        "recall_database_failure",
        "recall_memory_leak",
    }


def test_model_status_reports_untrained_when_artifact_is_missing(
    api_client: TestClient,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(settings, "MODEL_PATH", str(tmp_path / "missing.joblib"))
    ml._load_cached_bundle.cache_clear()

    response = api_client.get("/api/v1/ml/model-status")

    assert response.status_code == 200
    assert response.json()["is_trained"] is False


def test_anomaly_detection_uses_and_persists_ingested_metric(
    api_client: TestClient,
    db_session: Session,
    monkeypatch,
    tmp_path,
) -> None:
    artifact = tmp_path / "isolation_forest.joblib"
    train_evaluate_and_save(
        output_path=artifact,
        training_samples=500,
        evaluation_normal_samples=60,
        anomalies_per_scenario=20,
    )
    monkeypatch.setattr(settings, "MODEL_PATH", str(artifact))
    ml._load_cached_bundle.cache_clear()
    model_status_response = api_client.get("/api/v1/ml/model-status")
    service_response = api_client.post(
        "/api/v1/services",
        json={"name": "database", "is_simulated": False},
    )
    service_id = service_response.json()["id"]
    metric_response = api_client.post(
        "/api/v1/metrics/ingest",
        json={
            "metrics": [
                {
                    "service_id": service_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cpu_utilization": 96,
                    "memory_utilization": 97,
                    "disk_utilization": 72,
                    "network_traffic": 740,
                    "response_time_ms": 1800,
                    "request_count": 45,
                    "error_rate": 40,
                    "database_connections": 0,
                    "service_availability": 60,
                    "source": "AGENT",
                }
            ]
        },
    )
    detection_response = api_client.post(
        "/api/v1/ml/detect-anomaly",
        json={"service_id": service_id, "metric_id": metric_response.json()["ids"][0]},
    )
    repeated_detection = api_client.post(
        "/api/v1/ml/detect-anomaly",
        json={"service_id": service_id, "metric_id": metric_response.json()["ids"][0]},
    )
    ml._load_cached_bundle.cache_clear()

    assert service_response.status_code == 201
    assert metric_response.status_code == 202
    assert model_status_response.status_code == 200
    assert model_status_response.json()["is_trained"] is True
    assert "false_positive_rate" in model_status_response.json()["evaluation_metrics"]
    assert detection_response.status_code == 200
    assert detection_response.json()["is_anomaly"] is True
    assert repeated_detection.status_code == 200
    assert db_session.query(AnomalyEvent).count() == 2
    assert db_session.query(AnomalyEvent).filter(AnomalyEvent.metric_id.is_not(None)).count() == 2
    assert db_session.query(Incident).count() == 1
    incident = db_session.query(Incident).one()
    assert incident.status == "OPEN"
    assert incident.severity == detection_response.json()["severity"]
    assert db_session.query(IncidentEvidence).count() == 2
    assert "database_connections" in detection_response.json()["contributing_features"]

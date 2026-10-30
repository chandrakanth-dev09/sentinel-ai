from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from app.ml.features import FEATURE_NAMES, feature_frame


MODEL_NAME = "sentinelai-isolation-forest"
MODEL_VERSION = "1.0.0"


@dataclass(frozen=True)
class ModelBundle:
    pipeline: Pipeline
    feature_names: tuple[str, ...]
    score_threshold: float
    score_scale: float
    baseline_medians: dict[str, float]
    baseline_iqrs: dict[str, float]
    trained_at: str
    evaluation_metrics: dict[str, float]
    dataset_name: str
    dataset_source: str


def create_pipeline(seed: int = 42, n_estimators: int = 200) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "isolation_forest",
                IsolationForest(
                    n_estimators=n_estimators,
                    contamination="auto",
                    random_state=seed,
                    n_jobs=1,
                ),
            ),
        ]
    )


def calculate_anomaly_scores(
    decision_scores: np.ndarray,
    threshold: float,
    scale: float,
) -> np.ndarray:
    return np.clip((threshold - decision_scores) / scale, 0.0, 1.0)


def predict_frame(bundle: ModelBundle, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    ordered = feature_frame(frame.to_dict(orient="records"))
    decision_scores = bundle.pipeline.decision_function(ordered)
    predictions = decision_scores <= bundle.score_threshold
    scores = calculate_anomaly_scores(
        decision_scores,
        bundle.score_threshold,
        bundle.score_scale,
    )
    return predictions.astype(bool), scores.astype(float)


def predict_one(bundle: ModelBundle, features: dict[str, object]) -> tuple[bool, float]:
    prediction, score = predict_frame(bundle, feature_frame(features))
    return bool(prediction[0]), float(score[0])


def feature_deviations(
    bundle: ModelBundle,
    features: dict[str, float],
    top_n: int = len(FEATURE_NAMES),
) -> dict[str, dict[str, float]]:
    deviations: list[tuple[str, float, float]] = []
    for feature in bundle.feature_names:
        value = features.get(feature)
        if value is None or not np.isfinite(value):
            continue
        median = bundle.baseline_medians[feature]
        scale = max(bundle.baseline_iqrs[feature], 1e-6)
        deviations.append((feature, value, abs(value - median) / scale))
    deviations.sort(key=lambda item: item[2], reverse=True)
    return {
        feature: {"value": value, "robust_deviation": round(deviation, 3)}
        for feature, value, deviation in deviations[:top_n]
    }


def severity_for_score(score: float) -> str:
    if score >= 0.85:
        return "CRITICAL"
    if score >= 0.6:
        return "HIGH"
    if score >= 0.3:
        return "MEDIUM"
    return "LOW"


def save_bundle(bundle: ModelBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model_name": MODEL_NAME,
            "version": MODEL_VERSION,
            "pipeline": bundle.pipeline,
            "feature_names": list(bundle.feature_names),
            "score_threshold": bundle.score_threshold,
            "score_scale": bundle.score_scale,
            "baseline_medians": bundle.baseline_medians,
            "baseline_iqrs": bundle.baseline_iqrs,
            "trained_at": bundle.trained_at,
            "evaluation_metrics": bundle.evaluation_metrics,
            "dataset_name": bundle.dataset_name,
            "dataset_source": bundle.dataset_source,
        },
        path,
    )


def load_bundle(path: Path) -> ModelBundle:
    if not path.is_file():
        raise FileNotFoundError(f"Trained model artifact not found: {path}")
    raw: Any = joblib.load(path)
    required = {
        "pipeline",
        "feature_names",
        "score_threshold",
        "score_scale",
        "baseline_medians",
        "baseline_iqrs",
        "trained_at",
        "evaluation_metrics",
        "dataset_name",
        "dataset_source",
    }
    if not isinstance(raw, dict) or not required.issubset(raw):
        raise ValueError(f"Model artifact has an invalid format: {path}")
    if tuple(raw["feature_names"]) != FEATURE_NAMES:
        raise ValueError("Model artifact feature schema does not match this application version")
    return ModelBundle(
        pipeline=raw["pipeline"],
        feature_names=tuple(raw["feature_names"]),
        score_threshold=float(raw["score_threshold"]),
        score_scale=float(raw["score_scale"]),
        baseline_medians={key: float(value) for key, value in raw["baseline_medians"].items()},
        baseline_iqrs={key: float(value) for key, value in raw["baseline_iqrs"].items()},
        trained_at=str(raw["trained_at"]),
        evaluation_metrics={
            key: float(value) for key, value in raw["evaluation_metrics"].items()
        },
        dataset_name=str(raw["dataset_name"]),
        dataset_source=str(raw["dataset_source"]),
    )

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from app.ml.detector import (
    MODEL_NAME,
    MODEL_VERSION,
    ModelBundle,
    create_pipeline,
    predict_frame,
    save_bundle,
)
from app.ml.synthetic_data import (
    DATASET_NAME,
    DATASET_SOURCE,
    generate_evaluation_data,
    generate_training_data,
)


def train_evaluate_and_save(
    output_path: Path,
    seed: int = 42,
    training_samples: int = 3000,
    evaluation_normal_samples: int = 400,
    anomalies_per_scenario: int = 100,
) -> tuple[ModelBundle, dict[str, float]]:
    training = generate_training_data(training_samples, seed)
    evaluation, labels, scenarios = generate_evaluation_data(
        evaluation_normal_samples,
        anomalies_per_scenario,
        seed + 1,
    )

    pipeline = create_pipeline(seed=seed)
    pipeline.fit(training)
    training_decisions = pipeline.decision_function(training)
    score_threshold = float(np.quantile(training_decisions, 0.01))
    score_scale = max(
        score_threshold - float(np.quantile(training_decisions, 0.001)),
        0.05,
    )

    trained_at = datetime.now(timezone.utc).isoformat()
    initial_bundle = ModelBundle(
        pipeline=pipeline,
        feature_names=tuple(training.columns),
        score_threshold=score_threshold,
        score_scale=score_scale,
        baseline_medians={},
        baseline_iqrs={},
        trained_at=trained_at,
        evaluation_metrics={},
        dataset_name=DATASET_NAME,
        dataset_source=DATASET_SOURCE,
    )
    started = perf_counter()
    predictions, _ = predict_frame(initial_bundle, evaluation)
    elapsed_ms = (perf_counter() - started) * 1000
    metrics = {
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "false_positive_rate": float(
            np.count_nonzero((labels == 0) & predictions) / np.count_nonzero(labels == 0)
        ),
        "mean_prediction_latency_ms": float(elapsed_ms / len(evaluation)),
    }
    for scenario in sorted(set(scenarios) - {"normal"}):
        scenario_mask = np.asarray([name == scenario for name in scenarios])
        metrics[f"recall_{scenario}"] = float(
            recall_score(
                labels[scenario_mask],
                predictions[scenario_mask],
                zero_division=0,
            )
        )

    medians = training.median()
    quartiles = training.quantile([0.25, 0.75])
    iqr_values = quartiles.loc[0.75] - quartiles.loc[0.25]
    bundle = ModelBundle(
        pipeline=pipeline,
        feature_names=tuple(training.columns),
        score_threshold=score_threshold,
        score_scale=score_scale,
        baseline_medians={key: float(value) for key, value in medians.items()},
        baseline_iqrs={key: float(value) for key, value in iqr_values.items()},
        trained_at=trained_at,
        evaluation_metrics=metrics,
        dataset_name=DATASET_NAME,
        dataset_source=DATASET_SOURCE,
    )
    save_bundle(bundle, output_path)
    return bundle, metrics

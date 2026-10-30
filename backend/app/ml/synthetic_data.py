from collections.abc import Mapping

import numpy as np
import pandas as pd

from app.ml.features import FEATURE_NAMES


DATASET_NAME = "SentinelAI deterministic synthetic monitoring dataset"
DATASET_SOURCE = (
    "Generated locally from seeded healthy distributions and explicit deterministic "
    "failure-scenario transformations; no external dataset or random labels."
)


def _normal_rows(rng: np.random.Generator, count: int) -> list[dict[str, float]]:
    return [
        {
            "cpu_utilization": float(np.clip(rng.normal(35, 10), 0, 85)),
            "memory_utilization": float(np.clip(rng.normal(48, 12), 10, 85)),
            "disk_utilization": float(np.clip(rng.normal(35, 10), 0, 80)),
            "response_time_ms": float(np.clip(rng.normal(120, 35), 10, 500)),
            "error_rate": float(np.clip(rng.normal(0.4, 0.25), 0, 2)),
            "request_rate": float(np.clip(rng.normal(220, 70), 1, 800)),
            "database_connections": float(np.clip(rng.normal(20, 8), 1, 100)),
            "network_traffic": float(np.clip(rng.normal(160, 55), 1, 600)),
        }
        for _ in range(count)
    ]


def _failure_rows(
    rng: np.random.Generator,
    count: int,
    scenario: str,
) -> list[dict[str, float]]:
    ranges: dict[str, dict[str, tuple[float, float]]] = {
        "database_failure": {
            "cpu_utilization": (80, 100),
            "memory_utilization": (75, 96),
            "disk_utilization": (35, 75),
            "response_time_ms": (600, 2500),
            "error_rate": (15, 55),
            "request_rate": (20, 160),
            "database_connections": (0, 2),
            "network_traffic": (250, 800),
        },
        "memory_leak": {
            "cpu_utilization": (70, 100),
            "memory_utilization": (88, 100),
            "disk_utilization": (30, 75),
            "response_time_ms": (400, 2000),
            "error_rate": (2, 20),
            "request_rate": (80, 350),
            "database_connections": (25, 90),
            "network_traffic": (100, 550),
        },
        "api_latency_spike": {
            "cpu_utilization": (25, 70),
            "memory_utilization": (30, 75),
            "disk_utilization": (10, 65),
            "response_time_ms": (700, 3500),
            "error_rate": (1, 12),
            "request_rate": (50, 350),
            "database_connections": (10, 60),
            "network_traffic": (100, 600),
        },
        "cascading_failure": {
            "cpu_utilization": (75, 100),
            "memory_utilization": (80, 100),
            "disk_utilization": (35, 85),
            "response_time_ms": (500, 3000),
            "error_rate": (8, 50),
            "request_rate": (10, 180),
            "database_connections": (0, 5),
            "network_traffic": (250, 900),
        },
    }
    return [
        {
            feature: float(rng.uniform(*feature_ranges))
            for feature, feature_ranges in ranges[scenario].items()
        }
        for _ in range(count)
    ]


def generate_training_data(count: int = 3000, seed: int = 42) -> pd.DataFrame:
    if count < 10:
        raise ValueError("Training data must include at least 10 healthy samples")
    rng = np.random.default_rng(seed)
    return pd.DataFrame(_normal_rows(rng, count), columns=FEATURE_NAMES)


def generate_evaluation_data(
    normal_count: int = 400,
    anomalies_per_scenario: int = 100,
    seed: int = 1729,
) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    if normal_count < 1 or anomalies_per_scenario < 1:
        raise ValueError("Evaluation data must contain healthy and failure examples")

    rng = np.random.default_rng(seed)
    rows: list[Mapping[str, float]] = _normal_rows(rng, normal_count)
    labels = [0] * normal_count
    scenarios = ["normal"] * normal_count

    for scenario in (
        "database_failure",
        "memory_leak",
        "api_latency_spike",
        "cascading_failure",
    ):
        rows.extend(_failure_rows(rng, anomalies_per_scenario, scenario))
        labels.extend([1] * anomalies_per_scenario)
        scenarios.extend([scenario] * anomalies_per_scenario)

    order = rng.permutation(len(rows))
    data = pd.DataFrame([rows[index] for index in order], columns=FEATURE_NAMES)
    ordered_labels = np.asarray(labels, dtype=np.int8)[order]
    ordered_scenarios = [scenarios[index] for index in order]
    return data, ordered_labels, ordered_scenarios

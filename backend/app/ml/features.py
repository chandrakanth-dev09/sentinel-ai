from collections.abc import Mapping

import pandas as pd


FEATURE_NAMES = (
    "cpu_utilization",
    "memory_utilization",
    "disk_utilization",
    "response_time_ms",
    "error_rate",
    "request_rate",
    "database_connections",
    "network_traffic",
)


def metric_to_features(metric: object) -> dict[str, float]:
    return {
        "cpu_utilization": float(getattr(metric, "cpu_utilization")),
        "memory_utilization": float(getattr(metric, "memory_utilization")),
        "disk_utilization": float(getattr(metric, "disk_utilization")),
        "response_time_ms": float(getattr(metric, "response_time_ms")),
        "error_rate": float(getattr(metric, "error_rate")),
        "request_rate": float(getattr(metric, "request_count")),
        "database_connections": float(getattr(metric, "database_connections")),
        "network_traffic": float(getattr(metric, "network_traffic")),
    }


def feature_frame(values: Mapping[str, object] | list[Mapping[str, object]]) -> pd.DataFrame:
    rows = [values] if isinstance(values, Mapping) else list(values)
    return pd.DataFrame(rows, columns=FEATURE_NAMES).replace([float("inf"), float("-inf")], float("nan"))

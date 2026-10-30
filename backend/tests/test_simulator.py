import runpy
from pathlib import Path
import random


SIMULATOR_PATH = Path(__file__).resolve().parents[2] / "monitoring-agent" / "simulator.py"
SIMULATOR = runpy.run_path(str(SIMULATOR_PATH))
Scenario = SIMULATOR["Scenario"]
build_log = SIMULATOR["build_log"]
build_metric = SIMULATOR["build_metric"]


def test_normal_scenario_produces_simulated_healthy_metrics() -> None:
    metric = build_metric("payment", "service-id", 0, Scenario.NORMAL, random.Random(12))

    assert metric["source"] == "SIMULATED"
    assert 0 <= metric["error_rate"] < 1
    assert metric["service_availability"] >= 99
    assert build_log("payment", "service-id", 1, Scenario.NORMAL, "trace") is None


def test_database_failure_scenario_emits_correlated_error_logs() -> None:
    database_metric = build_metric(
        "database", "database-id", 3, Scenario.DATABASE_FAILURE, random.Random(12)
    )
    payment_log = build_log("payment", "payment-id", 3, Scenario.DATABASE_FAILURE, "trace-1")

    assert database_metric["database_connections"] == 0
    assert database_metric["source"] == "SIMULATED"
    assert payment_log is not None
    assert payment_log["trace_id"] == "trace-1"
    assert payment_log["source"] == "SIMULATED"


def test_memory_leak_increases_usage_and_api_scenario_spikes_latency() -> None:
    leaking_metric = build_metric(
        "payment", "payment-id", 45, Scenario.MEMORY_LEAK, random.Random(12)
    )
    latency_metric = build_metric(
        "api-gateway", "gateway-id", 3, Scenario.API_LATENCY_SPIKE, random.Random(12)
    )

    assert leaking_metric["memory_utilization"] > 70
    assert leaking_metric["response_time_ms"] > 100
    assert latency_metric["response_time_ms"] == 850

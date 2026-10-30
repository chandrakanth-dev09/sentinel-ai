import argparse
import asyncio
import logging
import os
import random
import uuid
from datetime import datetime, timezone
from enum import StrEnum

import httpx


LOGGER = logging.getLogger("sentinelai.simulator")
SERVICE_NAMES = ("frontend", "api-gateway", "authentication", "payment", "database")


class Scenario(StrEnum):
    NORMAL = "normal"
    DATABASE_FAILURE = "database-failure"
    MEMORY_LEAK = "memory-leak"
    API_LATENCY_SPIKE = "api-latency-spike"
    CASCADING_FAILURE = "cascading-failure"


def build_metric(
    service_name: str,
    service_id: str,
    tick: int,
    scenario: Scenario,
    rng: random.Random,
) -> dict[str, object]:
    values: dict[str, float | int] = {
        "cpu_utilization": round(rng.uniform(18, 42), 2),
        "memory_utilization": round(rng.uniform(32, 58), 2),
        "disk_utilization": round(rng.uniform(20, 45), 2),
        "network_traffic": round(rng.uniform(40, 250), 2),
        "response_time_ms": round(rng.uniform(35, 115), 2),
        "request_count": rng.randint(80, 320),
        "error_rate": round(rng.uniform(0, 0.6), 2),
        "database_connections": rng.randint(4, 24),
        "service_availability": round(rng.uniform(99.5, 100), 2),
    }

    if tick >= 2 and scenario in {Scenario.DATABASE_FAILURE, Scenario.CASCADING_FAILURE}:
        failure_metrics: dict[str, dict[str, float | int]] = {
            "database": {
                "cpu_utilization": 88,
                "memory_utilization": 79,
                "response_time_ms": 900,
                "error_rate": 32,
                "database_connections": 0,
                "service_availability": 55,
            },
            "payment": {
                "response_time_ms": 520,
                "error_rate": 13,
                "service_availability": 78,
            },
            "api-gateway": {
                "response_time_ms": 340,
                "error_rate": 7,
                "service_availability": 88,
            },
            "frontend": {
                "response_time_ms": 190,
                "error_rate": 3,
                "service_availability": 94,
            },
        }
        values.update(failure_metrics.get(service_name, {}))
    elif scenario == Scenario.MEMORY_LEAK and service_name == "payment":
        memory = min(98.0, float(values["memory_utilization"]) + tick * 1.4)
        values["memory_utilization"] = round(memory, 2)
        if memory > 70:
            values["response_time_ms"] = round(100 + (memory - 70) * 18, 2)
            values["error_rate"] = round(min(20, (memory - 70) * 0.55), 2)
            values["service_availability"] = round(max(70, 100 - (memory - 70) * 0.8), 2)
    elif scenario == Scenario.API_LATENCY_SPIKE and service_name == "api-gateway":
        values["response_time_ms"] = 850
        values["error_rate"] = 2.5
        values["service_availability"] = 97

    return {
        "service_id": service_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **values,
        "source": "SIMULATED",
    }


def build_log(
    service_name: str,
    service_id: str,
    tick: int,
    scenario: Scenario,
    trace_id: str,
) -> dict[str, object] | None:
    if tick < 2 or scenario in {Scenario.NORMAL, Scenario.MEMORY_LEAK}:
        return None

    if scenario == Scenario.API_LATENCY_SPIKE and service_name == "api-gateway":
        message = "Elevated upstream response latency detected"
        error_type = "UpstreamLatency"
    elif scenario in {Scenario.DATABASE_FAILURE, Scenario.CASCADING_FAILURE}:
        errors = {
            "database": ("Database connection pool exhausted", "ConnectionError"),
            "payment": ("Payment request failed while waiting for database", "DependencyTimeout"),
            "api-gateway": ("Upstream payment request timed out", "GatewayTimeout"),
            "frontend": ("Request failed after gateway timeout", "UpstreamError"),
        }
        error = errors.get(service_name)
        if error is None:
            return None
        message, error_type = error
    else:
        return None

    return {
        "service_id": service_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "ERROR",
        "message": message,
        "error_type": error_type,
        "trace_id": trace_id,
        "request_id": f"sim-{tick}-{service_name}",
        "source": "SIMULATED",
        "attributes": {"scenario": scenario.value, "simulated": True},
    }


async def run_simulator(
    api_url: str,
    scenario: Scenario,
    interval_seconds: float | None,
    seed: int | None,
    once: bool,
) -> None:
    rng = random.Random(seed)
    async with httpx.AsyncClient(base_url=api_url.rstrip("/"), timeout=10) as client:
        if interval_seconds is None:
            response = await client.get("/api/v1/settings")
            response.raise_for_status()
            interval_seconds = float(response.json()["monitoring_interval_seconds"])
        if interval_seconds <= 0:
            raise ValueError("The simulator interval must be greater than zero")

        service_ids: dict[str, str] = {}
        for service_name in SERVICE_NAMES:
            response = await client.post(
                "/api/v1/services",
                json={
                    "name": service_name,
                    "description": "Created by the SentinelAI demonstration simulator",
                    "is_simulated": True,
                },
            )
            response.raise_for_status()
            service_ids[service_name] = response.json()["id"]

        dependencies = (
            ("database", "payment"),
            ("database", "authentication"),
            ("payment", "api-gateway"),
            ("authentication", "api-gateway"),
            ("api-gateway", "frontend"),
        )
        for upstream, downstream in dependencies:
            response = await client.post(
                "/api/v1/services/dependencies",
                json={
                    "upstream_service_id": service_ids[upstream],
                    "downstream_service_id": service_ids[downstream],
                },
            )
            response.raise_for_status()

        tick = 0
        while True:
            trace_id = f"sim-{scenario.value}-{uuid.uuid4().hex[:12]}"
            metrics = [
                build_metric(service_name, service_ids[service_name], tick, scenario, rng)
                for service_name in SERVICE_NAMES
            ]
            logs = [
                item
                for service_name in SERVICE_NAMES
                if (
                    item := build_log(
                        service_name,
                        service_ids[service_name],
                        tick,
                        scenario,
                        trace_id,
                    )
                )
                is not None
            ]
            metric_response = await client.post(
                "/api/v1/metrics/ingest",
                json={"metrics": metrics},
            )
            metric_response.raise_for_status()
            if logs:
                log_response = await client.post("/api/v1/logs/ingest", json={"logs": logs})
                log_response.raise_for_status()
            LOGGER.info(
                "Uploaded tick=%d scenario=%s metrics=%d logs=%d source=SIMULATED",
                tick,
                scenario.value,
                len(metrics),
                len(logs),
            )
            tick += 1
            if once:
                return
            await asyncio.sleep(interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate labeled SentinelAI demo telemetry.")
    parser.add_argument(
        "--scenario",
        choices=[scenario.value for scenario in Scenario],
        default=Scenario.NORMAL.value,
        help="Failure scenario or normal operation to generate.",
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="SentinelAI API origin.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Seconds between metric batches; defaults to the API's saved setting.",
    )
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Upload one batch and exit instead of running until Ctrl+C.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    interval_seconds = args.interval
    environment_interval = os.environ.get("SIMULATOR_INTERVAL_SECONDS")
    if interval_seconds is None and environment_interval is not None:
        interval_seconds = float(environment_interval)
    asyncio.run(
        run_simulator(
            api_url=args.api_url,
            scenario=Scenario(args.scenario),
            interval_seconds=interval_seconds,
            seed=args.seed,
            once=args.once,
        )
    )


if __name__ == "__main__":
    main()

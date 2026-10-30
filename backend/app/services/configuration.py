from sqlalchemy.orm import Session

from app.models import SystemConfiguration


DEFAULT_CONFIGURATION = {
    "monitoring_interval_seconds": 5,
    "cpu_warning_percent": 80.0,
    "memory_warning_percent": 85.0,
    "disk_warning_percent": 90.0,
    "response_time_warning_ms": 500.0,
    "error_rate_warning_percent": 5.0,
    "availability_warning_percent": 99.0,
}


def load_configuration(session: Session) -> SystemConfiguration:
    return session.get(SystemConfiguration, 1) or SystemConfiguration(
        id=1,
        **DEFAULT_CONFIGURATION,
    )


def classify_service_health(metric: object, configuration: SystemConfiguration) -> str:
    cpu = float(getattr(metric, "cpu_utilization"))
    memory = float(getattr(metric, "memory_utilization"))
    disk = float(getattr(metric, "disk_utilization"))
    response_time = float(getattr(metric, "response_time_ms"))
    error_rate = float(getattr(metric, "error_rate"))
    availability = float(getattr(metric, "service_availability"))

    critical = (
        response_time >= configuration.response_time_warning_ms * 4
        or error_rate >= configuration.error_rate_warning_percent * 4
        or availability <= configuration.availability_warning_percent - 10
    )
    if critical:
        return "CRITICAL"

    degraded = (
        cpu >= configuration.cpu_warning_percent
        or memory >= configuration.memory_warning_percent
        or disk >= configuration.disk_warning_percent
        or response_time >= configuration.response_time_warning_ms
        or error_rate >= configuration.error_rate_warning_percent
        or availability < configuration.availability_warning_percent
    )
    return "DEGRADED" if degraded else "HEALTHY"

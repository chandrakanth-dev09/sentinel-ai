from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine

from app.api.routes import health
from app.main import app


def test_liveness_is_available_without_database() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_database(test_engine: Engine, monkeypatch) -> None:
    monkeypatch.setattr(health, "engine", test_engine)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def test_readiness_reports_database_failure(monkeypatch) -> None:
    class UnavailableEngine:
        def connect(self) -> None:
            raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(health, "engine", UnavailableEngine())

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database is unavailable"

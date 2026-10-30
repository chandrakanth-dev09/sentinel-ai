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


def test_root_serves_frontend_when_built(tmp_path, monkeypatch) -> None:
    from app import main

    (tmp_path / "index.html").write_text("<html>SentinelAI interface</html>", encoding="utf-8")
    monkeypatch.setattr(main, "frontend_dist", tmp_path)

    with TestClient(app) as client:
        root_response = client.get("/")
        route_response = client.get("/incidents/incident-id")
        unknown_api_response = client.get("/api/v1/not-a-route")

    assert root_response.status_code == 200
    assert "SentinelAI interface" in root_response.text
    assert route_response.status_code == 200
    assert "SentinelAI interface" in route_response.text
    assert unknown_api_response.status_code == 404


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

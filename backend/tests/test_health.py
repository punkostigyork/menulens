from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.main import app


def test_health_success():
    with patch("app.api.health.check_database") as check, TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "connected"}
        check.assert_called_once_with(app.state.engine)


def test_health_database_unavailable():
    error = OperationalError("SELECT 1", {}, Exception("private connection details"))
    with patch("app.api.health.check_database", side_effect=error), TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable", "database": "disconnected"}
        assert "private" not in response.text


def test_docs_and_cors():
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert "/health" in client.get("/openapi.json").json()["paths"]
        allowed = client.options("/health", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
        rejected = client.options("/health", headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in rejected.headers

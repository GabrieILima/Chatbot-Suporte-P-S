from fastapi.testclient import TestClient

from src.api.main import app


def test_health_endpoint():
    client = TestClient(app)

    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "Chatbot Suporte P&S"

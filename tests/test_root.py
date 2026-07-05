from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["application"] == "Agentic RAG Assistant"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"

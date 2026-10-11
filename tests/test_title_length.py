from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_with_over_long_title_is_rejected() -> None:
    # BUG-1: a 100,000-character title is accepted with 201 today; the API should
    # refuse titles over a sensible length (200 characters) with a 422 instead.
    before = client.get("/tasks").json()
    response = client.post("/tasks", json={"title": "x" * 100_000})
    assert response.status_code == 422
    assert client.get("/tasks").json() == before

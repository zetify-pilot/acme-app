from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_trims_surrounding_whitespace_from_title() -> None:
    # BUG-8: a title posted with surrounding spaces is stored verbatim, so
    # {"title": "  Buy milk  "} comes back — and lists — as "  Buy milk  "
    # instead of the trimmed "Buy milk".
    created = client.post("/tasks", json={"title": "  Buy milk  "}).json()
    assert created["title"] == "Buy milk"

    listed = {task["id"]: task for task in client.get("/tasks").json()}
    assert listed[created["id"]]["title"] == "Buy milk"

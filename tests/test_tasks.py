from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_list() -> None:
    created = client.post("/tasks", json={"title": "write the guide"}).json()
    assert created["title"] == "write the guide"
    assert created["done"] is False
    assert created in client.get("/tasks").json()


def test_complete() -> None:
    created = client.post("/tasks", json={"title": "ship it"}).json()
    done = client.post(f"/tasks/{created['id']}/done").json()
    assert done["done"] is True


def test_complete_unknown_task_is_404() -> None:
    assert client.post("/tasks/9999/done").status_code == 404

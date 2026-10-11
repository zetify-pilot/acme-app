from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_patch_marks_task_done() -> None:
    created = client.post("/tasks", json={"title": "tick me off"}).json()
    assert created["done"] is False
    response = client.patch(f"/tasks/{created['id']}", json={"done": True})
    assert response.status_code == 200
    assert response.json()["done"] is True
    listed = {task["id"]: task for task in client.get("/tasks").json()}
    assert listed[created["id"]]["done"] is True


def test_patch_unknown_task_is_404() -> None:
    assert client.patch("/tasks/9999", json={"done": True}).status_code == 404


def test_list_shows_done_tasks_last() -> None:
    first = client.post("/tasks", json={"title": "first"}).json()
    second = client.post("/tasks", json={"title": "second"}).json()
    third = client.post("/tasks", json={"title": "third"}).json()
    client.patch(f"/tasks/{second['id']}", json={"done": True})

    listed = client.get("/tasks").json()
    ids = [task["id"] for task in listed]
    # The finished task sorts after every task still to do.
    assert ids.index(second["id"]) > ids.index(first["id"])
    assert ids.index(second["id"]) > ids.index(third["id"])
    # Globally: no done task ever precedes a task still to do.
    done_flags = [task["done"] for task in listed]
    assert done_flags == sorted(done_flags)

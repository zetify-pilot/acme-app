from fastapi.testclient import TestClient

from app import main
from app.main import Task, app

client = TestClient(app)


def test_ordered_tasks_snapshots_before_sorting() -> None:
    # E13: the list handed back is a snapshot of the store, so a write that
    # lands after the call cannot reach into what the caller already holds.
    main._tasks[1] = Task(id=1, title="first")
    snapshot = main._ordered_tasks()

    # A write to the store after the snapshot is taken must not appear in it.
    main._tasks[2] = Task(id=2, title="second")

    # The result is a plain list, never a live view over the store.
    assert isinstance(snapshot, list)
    assert [task.id for task in snapshot] == [1]
    # A fresh call re-reads the store, so the new task is visible there.
    assert [task.id for task in main._ordered_tasks()] == [1, 2]


def test_list_order_is_open_first_finished_last() -> None:
    first = client.post("/tasks", json={"title": "first"}).json()
    second = client.post("/tasks", json={"title": "second"}).json()
    third = client.post("/tasks", json={"title": "third"}).json()
    client.patch(f"/tasks/{second['id']}", json={"done": True})
    client.patch(f"/tasks/{third['id']}", json={"done": True})

    ordered = main._ordered_tasks()
    done_flags = [task.done for task in ordered]
    # Globally: no done task ever precedes a task still to do.
    assert done_flags == sorted(done_flags)
    # Open tasks keep insertion order; the finished ones follow.
    assert [task.id for task in ordered] == [
        first["id"],
        second["id"],
        third["id"],
    ]

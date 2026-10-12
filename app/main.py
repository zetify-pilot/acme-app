"""A minimal in-memory task list."""

import csv
import io
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Tasks")

MAX_TITLE_LENGTH = 200


class TaskIn(BaseModel):
    title: str = Field(max_length=MAX_TITLE_LENGTH)

    @field_validator("title")
    @classmethod
    def _title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must have at least one non-space character")
        return value


class Task(TaskIn):
    id: int
    done: bool = False


class TaskPatch(BaseModel):
    done: bool


_tasks: dict[int, Task] = {}
_next_id = 1


def _ordered_tasks() -> list[Task]:
    # Finished tasks sort last; Python's stable sort keeps each group in
    # insertion order. Snapshot the values first so a concurrent write cannot
    # change the dict mid-iteration.
    return sorted(list(_tasks.values()), key=lambda task: task.done)


@app.get("/tasks")
def list_tasks() -> list[Task]:
    return _ordered_tasks()


@app.post("/tasks", status_code=201)
def create_task(task: TaskIn) -> Task:
    global _next_id
    created = Task(id=_next_id, title=task.title)
    _tasks[created.id] = created
    _next_id += 1
    return created


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, patch: TaskPatch) -> Task:
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    task.done = patch.done
    return task


@app.post("/tasks/{task_id}/done")
def complete_task(task_id: int) -> Task:
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    task.done = True
    return task


@app.get("/tasks/export")
def export_tasks() -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["title", "done"])
    for task in _ordered_tasks():
        writer.writerow([task.title, "true" if task.done else "false"])
    body = buffer.getvalue().encode("utf-8-sig")
    filename = f"tasks-{datetime.now(timezone.utc).date().isoformat()}.csv"
    return Response(
        content=body,
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

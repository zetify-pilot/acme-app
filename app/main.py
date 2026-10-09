"""A minimal in-memory task list."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Tasks")


class TaskIn(BaseModel):
    title: str


class Task(TaskIn):
    id: int
    done: bool = False


_tasks: dict[int, Task] = {}
_next_id = 1


@app.get("/tasks")
def list_tasks() -> list[Task]:
    return list(_tasks.values())


@app.post("/tasks", status_code=201)
def create_task(task: TaskIn) -> Task:
    global _next_id
    created = Task(id=_next_id, title=task.title)
    _tasks[created.id] = created
    _next_id += 1
    return created


@app.post("/tasks/{task_id}/done")
def complete_task(task_id: int) -> Task:
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    task.done = True
    return task

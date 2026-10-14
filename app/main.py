"""A minimal in-memory task list."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

app = FastAPI(title="Tasks")

MAX_TITLE_LENGTH = 200


class TaskIn(BaseModel):
    # Surrounding whitespace is stripped before any constraint runs, so the blank
    # check, the length rule, what gets stored and what comes back are all the
    # same title — the length rule never judges a string we would not store.
    model_config = ConfigDict(str_strip_whitespace=True)

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


@app.get("/tasks")
def list_tasks() -> list[Task]:
    # Finished tasks sort last; Python's stable sort keeps each group in
    # insertion order.
    return sorted(_tasks.values(), key=lambda task: task.done)


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

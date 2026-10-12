import pytest

from app import main


@pytest.fixture(autouse=True)
def _reset_task_store() -> None:
    main._tasks.clear()
    main._next_id = 1

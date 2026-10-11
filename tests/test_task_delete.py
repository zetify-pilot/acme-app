from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_delete_unknown_task_is_404() -> None:
    # BUG-4: deleting a task id that does not exist does not answer 404 today.
    # No DELETE route exists, so the request falls through to 405 Method Not
    # Allowed instead of the 404 with a short error message the API owes. The
    # customer reports it as a 500; either way it is not the expected 404.
    response = client.delete("/tasks/9999")
    assert response.status_code == 404
    assert response.json().get("detail")

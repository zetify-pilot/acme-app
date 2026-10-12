import csv
import io
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import main
from app.main import Task, app

client = TestClient(app)

EXPORT = "/tasks/export"


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


def _rows(response) -> list[list[str]]:
    # Read the response BYTES and decode with the file's own encoding
    # (utf-8-sig), never r.text: r.text decodes under the declared
    # charset=utf-8 and would leave the byte-order mark in the first cell.
    text = response.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def test_export_answers_with_a_file_not_json() -> None:
    response = client.get(EXPORT)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment")
    assert "filename=" in disposition

    # AC-1 is about a *file*, not a page: the body is the CSV text, never a
    # JSON document wearing CSV headers.
    body = response.content.decode("utf-8-sig")
    assert not body.lstrip().startswith(("{", "["))
    assert body.startswith("title,done")


def test_header_and_one_row_per_task() -> None:
    client.post("/tasks", json={"title": "alpha"})
    beta = client.post("/tasks", json={"title": "beta"}).json()
    client.patch(f"/tasks/{beta['id']}", json={"done": True})

    rows = _rows(client.get(EXPORT))
    assert rows[0] == ["title", "done"]
    body = rows[1:]
    assert len(body) == 2
    assert ["alpha", "false"] in body
    assert ["beta", "true"] in body
    # The lowercase vocabulary, never Python's True/False.
    assert all(done in ("true", "false") for _, done in body)


def test_rows_follow_the_apps_order() -> None:
    client.post("/tasks", json={"title": "a"})
    b = client.post("/tasks", json={"title": "b"}).json()
    client.post("/tasks", json={"title": "c"})
    client.patch(f"/tasks/{b['id']}", json={"done": True})

    rows = _rows(client.get(EXPORT))[1:]
    # The file's order is the screen's order, by construction.
    assert [row[0] for row in rows] == [
        task["title"] for task in client.get("/tasks").json()
    ]
    # Open-first, finished-last: b was finished, so it sorts after a and c.
    assert [row[1] for row in rows] == ["false", "false", "true"]


def test_every_task_appears_exactly_once() -> None:
    titles = [f"task-{i}" for i in range(5)]
    ids = [
        client.post("/tasks", json={"title": title}).json()["id"]
        for title in titles
    ]
    client.patch(f"/tasks/{ids[0]}", json={"done": True})
    client.patch(f"/tasks/{ids[2]}", json={"done": True})

    exported = [row[0] for row in _rows(client.get(EXPORT))[1:]]
    assert sorted(exported) == sorted(titles)
    assert len(exported) == len(titles)


def test_several_thousand_tasks_come_out_as_one_file() -> None:
    count = 3000
    for i in range(count):
        client.post("/tasks", json={"title": f"task-{i}"})

    response = client.get(EXPORT)
    assert response.status_code == 200
    rows = _rows(response)
    # One header row plus exactly one row per task, all in the one file.
    assert len(rows) == count + 1
    assert rows[0] == ["title", "done"]


def test_filename_carries_the_utc_date() -> None:
    response = client.get(EXPORT)
    expected = f"tasks-{datetime.now(timezone.utc).date().isoformat()}.csv"
    assert f'filename="{expected}"' in response.headers["content-disposition"]


def test_title_with_a_comma_stays_one_row() -> None:
    title = "buy milk, eggs, and bread"
    client.post("/tasks", json={"title": title})

    rows = _rows(client.get(EXPORT))[1:]
    assert rows == [[title, "false"]]


def test_title_with_a_double_quote_stays_one_row() -> None:
    title = 'say "hello" loudly'
    client.post("/tasks", json={"title": title})

    response = client.get(EXPORT)
    # Assert the raw bytes carry the RFC-4180 form: the field is quoted and
    # the embedded quotes are DOUBLED. A round-trip through csv.reader cannot
    # see this: csv.reader only treats a '"' as a quote when it is the FIRST
    # character of a field, so an unquoted "say "hello" loudly" decodes to the
    # same value as the correctly-quoted form. Only the bytes catch it.
    assert b'"say ""hello"" loudly",false\r\n' in response.content

    rows = _rows(response)[1:]
    assert rows == [[title, "false"]]


def test_title_with_a_line_break_stays_one_row() -> None:
    title = "line one\nline two\r\nline three"
    client.post("/tasks", json={"title": title})

    raw = client.get(EXPORT).content
    # The raw bytes carry the title as one quoted field on one row: the row
    # does not split.
    assert b'"line one\nline two\r\nline three",false\r\n' in raw

    # Normalise line endings explicitly: the promise is the row does not
    # split, not that a reading tool preserves line-ending bytes.
    text = raw.decode("utf-8-sig")
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    rows = list(csv.reader(io.StringIO(normalised)))
    normalised_title = title.replace("\r\n", "\n").replace("\r", "\n")
    assert rows == [["title", "done"], [normalised_title, "false"]]


def test_accented_and_symbol_titles_round_trip() -> None:
    title = "café — naïve, €5 ✓"
    client.post("/tasks", json={"title": title})

    raw = client.get(EXPORT).content
    # UTF-8 byte-order mark leads the body.
    assert raw.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[1] == [title, "false"]


def test_max_length_title_exports_intact() -> None:
    title = "x" * 200
    client.post("/tasks", json={"title": title})

    rows = _rows(client.get(EXPORT))[1:]
    assert rows == [[title, "false"]]
    assert len(rows[0][0]) == 200


def test_empty_list_exports_a_header_only_file() -> None:
    response = client.get(EXPORT)
    assert response.status_code == 200
    rows = _rows(response)
    assert rows == [["title", "done"]]

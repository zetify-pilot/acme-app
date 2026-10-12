---
type: prd-plan
---

# Backend Plan: A customer exports their own task list and opens it in a spreadsheet

PRD: knowledge/prds/0001-a-customer-exports-their-own-task-list/prd.md
Design: knowledge/prds/0001-a-customer-exports-their-own-task-list/design.md
UX Design: knowledge/prds/0001-a-customer-exports-their-own-task-list/ux-design.md

Envelope: ~3 hand-written files touched (`app/main.py`, `tests/conftest.py` new, `tests/test_tasks_export.py` new), ~150 hand-written lines added. The design named no numeric envelope; it enumerated one product file and two test files (`design.md` §Implementation order). Well under both ceilings — this plan file fits one run.

**Lane scope — backend only.** `slot:languages`, `slot:file-conventions` and `slot:ui-contracts` are unfilled stubs, and the design states plainly that this repository has no frontend — *"there is no frontend in the tree"* (`design.md` §Summary, §Layers affected). This PRD adds no screen, no page and no component: **there is no `frontend-plan.md`**, and its absence is how "no UI surface" is declared (Step 6). The one customer-facing surface is the file the browser saves, and it is verified through the API lane below.

**No docs plan.** `slot:docs` is unfilled, so the design records `docs_impact: unknown` and names no page id, no page contract and no home (`design.md` §Docs impact). Step 4b's degrade applies: no `docs-plan.md` is written.

**No better path left on the table (Rule 8).** The design settled the one genuine quality fork — one buffered response, not a streamed body — and the reason is an acceptance criterion, not speed: a generator that fails halfway hands the browser a *partial file with a 200*, which is exactly the broken file AC-7 rules out (`design.md` §Settled forks). The stdlib `csv.writer` is used rather than hand-built strings because hand-building is where quoting bugs live. Nothing better is available; nothing here trades quality for speed silently.

## Contract (generate first)

**No contract to generate.** `slot:api-contract` and `slot:codegen` are unfilled stubs — this repository has no OpenAPI spec, no generated types, and nothing is built by `make generate` (`make generate` exits 2, unconfigured). With a single implementation lane there is **no cross-plan contract boundary**: the one interface this PRD adds is the HTTP surface below, and the same lane's tests consume it directly.

### The one interface this PRD adds

| Path | Method | Purpose |
|------|--------|---------|
| `/tasks/export` | GET | Serve the whole task list as a downloadable CSV file |

- **Request** — none: no body, no parameters, no query string.
- **Response 200** — `Content-Type: text/csv; charset=utf-8`; `Content-Disposition: attachment; filename="tasks-YYYY-MM-DD.csv"`; body = UTF-8-with-BOM CSV: header `title,done`, one row per task in the app's order.
- **Errors** — none of its own: there is no id to not-find and no input to reject. The only edge is an empty list, which is a **200** with a header-only body (AC-6).
- **Declaration order** — the route is declared **after** the existing routes. `GET /tasks/export` answers **405** today because `PATCH /tasks/{task_id}` (`app/main.py:51`) already claims that path shape; the new route resolves it. If a `GET /tasks/{task_id}` is ever added it must be declared after this route, or it swallows `/tasks/export` as a task whose id is `export` (`design.md` §Settled forks).

### API & enum convention pre-check

**N/A — no spec and no codegen.** No new operation is registered with an OpenAPI contract, so there is no lint-clean-on-first-generate decision table to fill, and there is no `make generate` step to make green. No new enum is introduced either: the `done` column's `true`/`false` is a literal string written into the CSV body, not an enum on a stored column (this app has no storage layer — `design.md` §Layers affected).

## Test Strategy & Edge Cases

The lane is the repository's own: `make test` → `python3 -m pytest -q` over `tests/`, FastAPI's `TestClient` (`design.md` §Tests). Every assertion below lands in that lane; there is no DB, no e2e and no browser lane here (`make test-db` and `make test-e2e` exit 2, unconfigured).

### Happy paths
- **E1** — `GET /tasks/export` answers **200** with a *file* response, not a JSON page: `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename="…"`. (AC-1) — pytest (TestClient)
- **E2** — The file's first row is the header `title,done`; every task is exactly one row `[title, "true"|"false"]`, the `done` cell carrying the literal lowercase `true`/`false` — never Python's `True`/`False`. (AC-2) — pytest
- **E3** — The file's rows are in the order the app shows the list — open tasks first, finished last, stable within each group — identical to `GET /tasks`. (AC-5) — pytest
- **E4** — Every task in a mixed list appears **exactly once** — no duplication, no omission. (AC-5) — pytest
- **E5** — A list of several thousand tasks returns **200** with all rows in one file; nothing counts rows or compares against a ceiling. (AC-7) — pytest
- **E6** — The filename is `tasks-YYYY-MM-DD.csv`, the date being the server's **UTC** date (`datetime.now(timezone.utc).date().isoformat()`). (AC-8) — pytest

### Input validation & boundaries
- **E7** — A title containing a **comma** is quoted and stays one field on one row. (AC-3) — pytest
- **E8** — A title containing a **double quote** is written with the embedded quote doubled and stays one field on one row. (AC-3) — pytest
- **E9** — A title containing a **line break** (LF, and CRLF) is quoted and does **not** split the row. (R4; `design.md` §Tests names this as an implied-but-unspelled path) — pytest
- **E10** — A title containing an **accent and a symbol** round-trips: the body begins with the UTF-8 byte-order mark, and decoding the response **bytes** with `utf-8-sig` yields the title exactly, with no garbling. (AC-4) — pytest
- **E11** — A title at the app's maximum length (200 characters — `app/main.py:8,12`) exports **intact and untruncated**. — pytest

### Authorization & isolation
- **N/A** — the app has no authentication or authorization layer; every route it serves is open (`design.md` §API surface, citing `app/main.py:35,42,51,60`). This PRD names no permission, so there is no authz failure mode to test. The cross-customer separation promise belongs to SL-003, which has no PRD (`prd.md` §Out; design ledger rows 2–4).

### Concurrency & multi-replica
- **E13** — `_ordered_tasks()` sorts a **snapshot** (`list(_tasks.values())`) rather than a live dict view, so a concurrent write during an export cannot raise mid-iteration, and the list it returns does not change under a later write (`design.md` red-team finding 8). — pytest
- **N/A (multi-replica)** — the app is a single in-memory process: the task list is a module-level dict with no persistence, no background tasks, no cache and no queue (`design.md` §Layers affected, finding 1). There is no replica to keep coherent and no event bus to publish on.

### Error & failure modes
- **N/A** — the export has **no error path of its own**: no input to reject and no id to not-find, so it raises nothing and returns no 4xx. Its only edge, the empty list, is a 200 (E12). (`design.md` §API surface → *Errors*.)

### Empty / degenerate states
- **E12** — An empty list yields a **200** whose body is exactly the header row `title,done` and **no data rows** — not an error. (AC-6) — pytest

### Security / abuse
- **N/A — no auth, no secrets, no logging.** The app holds no credential and logs nothing at any boundary. The design deliberately adds **no** formula-injection escaping: R4 promises text is preserved *exactly as typed*, so a title beginning `=`, `+`, `-` or `@` is written verbatim, quoted only per RFC 4180. Recorded as a conscious non-addition, not a gap — escaping would be a transformation R4 forbids.

### Audit & observability
- **N/A** — the app writes no audit log, emits no metric and publishes no SSE event; it has no observability layer (`design.md` §Layers affected).

## Tasks

### Task B1: Extract the list-ordering rule and reset the shared test lane

**Wave:** 1
**Files:**
- `app/main.py`
- `tests/conftest.py` (new)

**Depends on:** None
**Contract dependency:** None

**What to do:**
Two "fix now" refactors the design settled (`design.md` Phase 1.5 findings 2 and 3), both prerequisites of the route:

1. **The ordering rule moves out of the route handler.** Add a plain function beside the models and have `list_tasks()` call it, per `design.md` §"A domain helper":

   ```python
   def _ordered_tasks() -> list[Task]:
       # Finished tasks sort last; Python's stable sort keeps each group in
       # insertion order. Snapshot the values first so a concurrent write cannot
       # change the dict mid-iteration.
       return sorted(list(_tasks.values()), key=lambda task: task.done)
   ```

   `list_tasks()` (`app/main.py:36-39`) becomes `return _ordered_tasks()`. The export will call the same function, so the file's order is the screen's order by construction and cannot drift from it.

2. **The shared lane state resets between tests.** Add `tests/conftest.py` carrying an autouse fixture that clears `app.main._tasks` and resets `app.main._next_id = 1` before every test in the lane. Today the three existing modules (`tests/test_tasks.py:5`, `tests/test_task_done.py:5`, `tests/test_title_length.py:5`) share one process-wide `_tasks` dict and never reset it, so no test can assert an empty list (AC-6) and results depend on module order. This is `design.md`'s scope-ledger row 1 — `admitted`, basis AC-6 — and it adds no product surface.

**Edge cases covered:** E13; it makes E12 reachable (the lane can start from an empty list).

**Tests:**
- `tests/conftest.py` — the autouse reset fixture itself (test infrastructure; exercised by every test in the lane).
- `tests/test_tasks_export.py` (new) — `test_ordered_tasks_snapshots_before_sorting` asserts E13 (the returned list is a snapshot: mutating `_tasks` afterwards does not change it, and nothing iterates a live dict view); `test_list_order_is_open_first_finished_last` asserts E3's ordering invariant holds through the extracted helper.
- Existing `tests/test_task_done.py::test_list_shows_done_tasks_last` — still asserts the list order (E3) is unchanged by the extraction; must stay green.

**Verify:**
- `make test` passes.
- `python3 -m pytest -q tests/test_task_done.py tests/test_tasks.py` passes, and passes again with the module order reversed — no test inherits another's tasks.

### Task B2: The `GET /tasks/export` route and its acceptance tests

**Wave:** 2
**Files:**
- `app/main.py`
- `tests/test_tasks_export.py`

**Depends on:** Task B1
**Contract dependency:** None — the HTTP surface above is the only interface, and this lane consumes it directly.

**What to do:**
Add `export_tasks()` to `app/main.py`, declared **after** the existing routes, building the file exactly in the order `design.md` §"The file's bytes" gives:

1. `io.StringIO()` buffer + `csv.writer(buffer)` — the default `excel` dialect: `,` delimiter, `"` quote character, minimal quoting (a field is quoted when it contains the delimiter, a double quote, `\r` or `\n`), embedded quotes doubled, CRLF between rows. Use the stdlib writer; hand-building strings is where quoting bugs live.
2. Header row: `title`, `done`.
3. One row per task iterating **`_ordered_tasks()`** — never `_tasks.values()` — so file order is screen order (AC-5).
4. Each row is `[task.title, "true" if task.done else "false"]` — the lowercase vocabulary AC-2 requires. (The obvious `str(task.done)` yields `True`/`False` and would fail it.)
5. Encode the buffer's text **`utf-8-sig`** — UTF-8 with a byte-order mark, the round-1 requester's choice (`REQ-0004`). The `charset` parameter stays `utf-8`: `utf-8-sig` is a Python codec name, not an IANA charset, and the mark is a signature a conforming consumer strips.
6. Filename: `tasks-{datetime.now(timezone.utc).date().isoformat()}.csv` — the server's UTC date.
7. Return a `Response` whose body is the bytes, with headers `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename="tasks-YYYY-MM-DD.csv"`.

No new dependency: `csv`, `io` and `datetime` are standard library, so `pyproject.toml` is unchanged. No auth, no request parameters, no error path.

**Edge cases covered:** E1, E2, E3, E4, E5, E6, E7, E8, E9, E10, E11, E12.

**Tests:** `tests/test_tasks_export.py` — one test per acceptance criterion plus the two implied paths. Every test reads the response **bytes** and decodes them with the file's own encoding (`utf-8-sig`) before parsing with `csv.reader` — never `r.text`, which decodes under the declared `charset=utf-8` and would leave the byte-order mark in the first header cell (`design.md` §Tests; red-team finding 5):
- `test_export_answers_with_a_file_not_json` — E1 (AC-1: status 200, `Content-Type`, `Content-Disposition: attachment`, filename present)
- `test_header_and_one_row_per_task` — E2 (AC-2: `title,done` header; `[title, "true"|"false"]` rows)
- `test_rows_follow_the_apps_order` — E3 (AC-5: open first, finished last, matching `GET /tasks`)
- `test_every_task_appears_exactly_once` — E4 (AC-5)
- `test_several_thousand_tasks_come_out_as_one_file` — E5 (AC-7)
- `test_filename_carries_the_utc_date` — E6 (AC-8)
- `test_title_with_a_comma_stays_one_row` — E7 (AC-3)
- `test_title_with_a_double_quote_stays_one_row` — E8 (AC-3)
- `test_title_with_a_line_break_stays_one_row` — E9 (asserts against the raw bytes and normalises line endings explicitly — R4's promise is that the row does not split, not that a reading tool preserves line-ending bytes)
- `test_accented_and_symbol_titles_round_trip` — E10 (AC-4: body starts with the byte-order mark; `utf-8-sig` decode yields the exact title)
- `test_max_length_title_exports_intact` — E11
- `test_empty_list_exports_a_header_only_file` — E12 (AC-6: 200, header row, no data rows)

**Verify:**
- `make test` passes.
- Manual: `uvicorn app.main:app` then `curl -sD- localhost:8000/tasks/export` shows `200`, both headers, and the header-only body.

## Edge Case Coverage Matrix

| ID | Description | Owning task(s) | Test layer |
|----|-------------|----------------|------------|
| E1 | 200 file response, not JSON (AC-1) | B2 | pytest |
| E2 | Header `title,done`; one row per task; literal `true`/`false` (AC-2) | B2 | pytest |
| E3 | Rows in the app's order — open first, finished last (AC-5) | B1, B2 | pytest |
| E4 | Every task exactly once (AC-5) | B2 | pytest |
| E5 | Several thousand tasks, one file, 200 (AC-7) | B2 | pytest |
| E6 | Filename carries the UTC date (AC-8) | B2 | pytest |
| E7 | Comma in a title stays one row (AC-3) | B2 | pytest |
| E8 | Double quote in a title stays one row (AC-3) | B2 | pytest |
| E9 | Line break in a title does not split the row (R4) | B2 | pytest |
| E10 | Accent/symbol round-trips via the byte-order mark (AC-4) | B2 | pytest |
| E11 | Max-length title exports intact | B2 | pytest |
| E12 | Empty list → header-only file, 200 (AC-6) | B1, B2 | pytest |
| E13 | `_ordered_tasks()` sorts a snapshot, not a live view | B1 | pytest |

Every backend-scoped `E<N>` has an owning task.

## Cross-Plan Dependencies

**N/A — single lane.** There is no frontend plan and no docs plan (both slots unfilled; the design names no page and no screen), so there is no cross-plan ordering to declare. Within this one lane the order is B1 → B2, both touching `app/main.py`.

## Verification

After all tasks complete:
- `make test` passes (the repository's whole lane — `python3 -m pytest -q`; CI runs the same, `.github/workflows/ci.yml`).
- `make lint` passes (`python3 -m compileall -q app tests`).
- `make test` passes in any module order (the `tests/conftest.py` reset fixture holds — no test inherits another's tasks).
- Every `E<N>` in the Test Strategy section has at least one passing test asserting it.
- Manual check: `curl -sD- localhost:8000/tasks/export` returns `200` with `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename="tasks-<UTC date>.csv"`, and an empty list yields the header-only body.
- No `pyproject.toml` change: `csv`, `io` and `datetime` are standard library.

## Claimed-requirement coverage

`prd.md` declares `implements: [REQ-0001, REQ-0002, REQ-0003, REQ-0004, REQ-0005, REQ-0006, REQ-0007, REQ-0008]`, all `adopted` in `knowledge/requirements/product.md` (none `rejected` or `superseded`). Each is covered by the acceptance criterion that would fail if it were not met, cited `**[REQ-NNNN]**` under the acceptance-criteria heading — the citations the design recorded in `design.md` §Acceptance criteria (Phase 4c step 6) and which this plan mirrors into `prd.md` so the claim is verifiable from the PRD itself:

| Claim | Requirement | Citing AC | Owning task |
|---|---|---|---|
| 1 | REQ-0001 | AC-1 | B2 |
| 2 | REQ-0002 | AC-2 | B2 |
| 3 | REQ-0003 | AC-3 | B2 |
| 4 | REQ-0004 | AC-4 | B2 |
| 5 | REQ-0005 | AC-5 | B2 |
| 6 | REQ-0006 | AC-6 | B1, B2 |
| 7 | REQ-0007 | AC-7 | B2 |
| 8 | REQ-0008 | AC-8 | B2 |

Every citing AC is owned by at least one task in the matrix above. No requirement row was minted here, and none was dropped.

## Envelope (re-measured)

`Envelope: ~3 hand-written files, ~150 hand-written added lines (design named no numeric envelope; it enumerated one product file and two test files).`

- **Per-run (~2,000 hand-written lines):** ~150 — a single run, well under. No plan-family split.
- **Per-PR (~10,000 hand-written lines):** ~150 — well under. No split into sibling PRDs.
- No generated output is touched (`slot:codegen` unfilled), so both figures are hand-written by construction. Test mass is included and is not trimmed.

## Next step

Run `/fleet:prd:implement knowledge/prds/0001-a-customer-exports-their-own-task-list` — one lane, two tasks in two waves, into one branch.

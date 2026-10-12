---
type: prd-design
designed_against: 1ea420ff3db601905fd5777dd2bd51e5598d8162
---

# Design: A customer exports their own task list and opens it in a spreadsheet

## Summary

A customer opens the export's address in a browser and the browser saves their whole task
list as a comma-separated file named for the day it was made — one row per task under a row
of column names (`title`, `done`), text preserved exactly as typed (commas, double quotes,
line breaks, accents and symbols), an empty list producing a header-only file rather than an
error, and no ceiling on the list's length. The design adds **one HTTP route** to the
existing FastAPI app and the tests that hold it to the PRD's eight acceptance criteria. There
is no screen: this repository has no frontend, the PRD says the app has no screens today and
this adds none, and the customer-facing surface is the file the browser saves.

## Vision alignment

- **Persona:** whoever runs the weekly planning or delivery meeting — the persona the program
  names. `slot:product-vision` is an unfilled stub, so no persona label is quoted from it;
  this is the PRD's own recorded degrade, carried forward unchanged.
- **Core loop step:** reporting on the list from the real list rather than from a retyped
  copy.

## Layers affected

`slot:architecture` is an unfilled stub — this repository names no layer list — so the
inventory below is read off the tree (`app/`, `tests/`, the `.claude/` corpus).

| Layer | Affected |
|---|---|
| API surface (`app/main.py` route handlers) | **Yes** |
| Domain / data (the in-memory task list) | **Yes** — read-only reuse, plus one ordering helper |
| Tests (`tests/`, pytest + FastAPI `TestClient`) | **Yes** |
| Storage | No — the app holds tasks in a module-level dict; there is no storage layer |
| Shared contracts / codegen (`slot:codegen` unfilled) | No — nothing in this repo is generated |
| Permissions / authorization | No — the app has none; every route it serves is open |
| Background work | No |
| Configuration | No |
| Web UI | No — there is no frontend in the tree |
| Docs (`slot:docs` unfilled) | Unknown — see below |

## Docs impact

**`docs_impact: unknown`**, unchanged from the PRD. The `docs` slot is unfilled: it names no
coverage rule, no page contract and no home, so no page can be named by page id, and no docs
gate runs at verify. That is the slot's own degrade, not a decision of this design.

One consequence is worth stating plainly because it is the feature's only discoverability
edge: the PRD declined a link or button in the app (its scope ledger row 4), and there is no
page to put one on anyway. So **how a customer learns the export's address is outside this
design** — it is told to them out of band. A page that would tell them was offered in round 2
of this design and **not pulled in**; it is recorded in the landed result's `open` list
rather than papered over with a page nobody's acceptance criterion needs.

## Architecture notes

### Best-practice baseline (Phase 1 Step 0-pre)

The mechanism is "serve a CSV download from a web API". The standard, and what this design
adopts:

- **Comma-separated values per RFC 4180** — a header row, one row per record, fields
  containing the delimiter, a double quote or a line break wrapped in double quotes with
  embedded quotes doubled, and CRLF between rows. Python's stdlib `csv` module's default
  `excel` dialect is exactly this, so the design uses `csv.writer` rather than hand-built
  strings; hand-building is where quoting bugs live. *(Verified, not assumed: a title
  containing a comma, a double quote, an LF and a CRLF written through `csv.writer` produces
  `b'title,done\r\n"a,b ""q""\nline\r\ncrlf end",true\r\n'` and round-trips through
  `csv.reader`.)*
- **`Content-Disposition: attachment; filename="…"`** with `Content-Type: text/csv` — the
  universal way a browser is told to save a response rather than render it. Named
  precedents: GitHub, Jira and Linear all download exports this way; the PRD's own
  best-practice note records the same.
- **An explicitly declared text encoding, marked with a byte-order mark.** A CSV carries no
  in-band encoding declaration, so a consumer guesses; Excel guesses its local codepage and
  renders accented text as garbage. Declaring UTF-8 and marking the body is the standard fix,
  and it is the option the PRD's requester chose in round 1 of this design (see *Open
  decisions*).
- **A dated filename** so repeated exports do not overwrite each other.

In-repo precedent: there is none for a file response — the routes the app answers today
(`app/main.py:35`, `:42`, `:51`, `:60`) all answer JSON. So the design matches the *route and
handler style* the repo already uses (plain `def` handlers, pydantic models, `HTTPException`
for errors) and adds the file-response idiom the baseline names. *The seat carries no browser
and the `deep-research` skill is not available here, so this baseline is established from the
repository, the PRD's own recorded baseline and the run's own knowledge, not from live
research.*

### Phase 1.5 — architecture audit

Surveyed surface: `app/main.py` (the file this design modifies) and `tests/` (the lane this
design extends).

1. **[Domain] `app/main.py:31`** — `_tasks` is a module-level dict with no persistence and no
   invalidation, so every restart loses the list. *Contradicts nothing written in this
   repository* — it is the app's chosen posture, and PG-01 records the decision: the source
   was accepted as the app holds it today, so "tasks surviving a restart" is deliberately not
   carried. **Perpetuate** — a conscious cost already taken by a person at the program's
   depth bar. Not escalated: re-asking a decision the person has already made on the record
   is the deferral the interview protocol forbids.
2. **[Tests] `tests/test_tasks.py:5`, `tests/test_task_done.py:5`, `tests/test_title_length.py:5`**
   — the three existing test modules share one module-level `TestClient` over one
   process-wide `_tasks` dict and never reset it, so each test sees whatever the tests before
   it left behind. Nothing fails today only because no existing assertion needs an empty
   list. **Fix now** — one new `tests/conftest.py` carries an autouse fixture that clears
   `_tasks` and resets `_next_id` before every test in the lane, so the empty-list case is
   testable and no test inherits another's state. *(Verified: with the fixture in place the
   suite is 18 passing, and passes in any module order.)*
3. **[API] `app/main.py:35-39`** — the list's order (finished last, stable within a group) is
   owned by a route handler, so a second ordering written into the export would drift from
   the screen, and calling a decorated handler from another handler crosses a layer for no
   reason. **Fix now** — the rule moves to a plain `_ordered_tasks()` that both handlers call.
4. **[Tooling] `Makefile` `validate-knowledge` / the corpus scripts** — `make
   validate-knowledge` is unconfigured (exit 2, no recipe), and every script that imports
   `fleet_knowledge` refuses on this box. *This is the repository's own tooling degrade, not
   a quirk in a file this design opens.* **Reported, not fixed** — it is named in the landed
   result's `open` list. No tracker issue is filed: a headless run makes no tracker write.
5. **[Corpus] `knowledge/slots/*`** — thirteen slots are unfilled stubs (`architecture`,
   `codegen`, `gate`, `languages`, `journeys`, `docs`, `dev-environment`, `file-conventions`,
   `planning-model`, `entity-model`, `feature-areas`, `git-workflow`, `tracker-identity`).
   Same disposition as 4: reported in `open`, outside this design's diff.
6. **[API] `app/main.py:51`, `:60`** — no error-envelope or naming inconsistency was found:
   both 404 paths raise the same `HTTPException(404, detail="task not found")`, and the
   handlers are uniformly thin. Nothing to fix.

No missing primitive was found: the export needs nothing the standard library and the
existing app do not already provide, so Phase 4a's "missing primitive" route is empty.

### Phase 2c — red-team findings and their dispositions

Dispatched as two independent sub-agents that did not author this design, with distinct
lenses (R1/R3/R4/R6 and R2/R5/R7), each instructed to argue the design is wrong. Their
findings, and one disposition each:

| # | Finding (lens) | Disposition |
|---|---|---|
| 1 | Writing `REQ-` rows by hand pre-empts the PRD's note that the register be framed "on a run with the tooling" (R1/R7) | **Reject, with reason.** Phase 4c step 8 withdraws that deferral, and Phase 7's gate blocks the flip to `designed` while `implements:` is empty on ground a register covers — `knowledge/requirements/product.md` is the register this product's `commitments` slot names, and it is empty rather than absent. The PRD's hedge named the *allocator*, not the framing; PG-01's shaping run set the in-repo precedent of allocating ids from a full read of the corpus when the tooling is absent, and recorded it. The tooling gap is named in the landed result's `open` list and in the register's own legend. |
| 2 | Eight rows restating the PRD's R1–R8 add little; the durable thing is the format contract (R1) | **Partially adopt.** The format contract *is* rows 2–4 (column names, value vocabulary, quoting, encoding). The set stays at eight because each row is a distinct property the system must hold afterwards and each is claimed by a distinct acceptance criterion; no row restates another. |
| 3 | `Cache-Control: no-store` is scope no acceptance criterion asks for, on a speculative staleness argument (R1) | **Adopt.** The header was dropped. No AC observes it, and the PRD's discipline is not to add unasked things — including small ones. |
| 4 | The acceptance-criteria section claims each criterion cites a requirement row, and none did (R7) | **Adopt.** Every criterion now carries its `**[REQ-NNNN]**` citation. |
| 5 | The chosen byte-order mark breaks the stated test method: `TestClient`'s `r.text` decodes under the declared `charset=utf-8` and yields `'﻿title'` as the first header cell (R2/R7) | **Adopt the defect, reject the remedy.** *(Verified: `r.text` is `'﻿title,done\r\n'`.)* The tests decode the response **bytes** with the file's own encoding rather than relying on `r.text`, and the mark's stray-character cost is stated as the chosen option's explicit cost rather than hidden. `charset=utf-8` stays: `utf-8-sig` is a Python codec name, not an IANA charset, and a byte-order mark is a signature a conforming consumer strips. |
| 6 | The encoding fork should not be escalated: it changes nothing the product promises, and AC-4 already settles it (R1/R7) | **Reject, with reason.** AC-4 names "a spreadsheet", and the two answers fail in *different* tools: without a mark, Excel on Windows garbles accented text; with one, a consumer that honours the declared charset sees a stray character at the head of the first column. Both are best practice, and which cost the customer would rather pay depends on the tools *their* readers use. Rule 8 makes exactly this a question, not a default — and the requester's answer in round 1 confirmed it was one. |
| 7 | `export_tasks()` calls a route handler to reuse the ordering rule (R4) | **Adopt.** The rule moves to `_ordered_tasks()`, which both handlers call. |
| 8 | `sorted(_tasks.values(), …)` iterates a live view, so a concurrent write during an export can raise — on a route R7 says must never error (R2) | **Adopt.** `_ordered_tasks()` snapshots the values before sorting. One token, inside a function this design adds; PG-01 de-scoped simultaneous exporters, so it is hardening, not a new requirement. |
| 9 | One `tests/conftest.py` fixture beats a fixture local to the new module — fewer moving parts, one convention, no order-dependence left (R3/R5) | **Adopt.** *(Verified: 18 passing in any module order.)* |
| 10 | A cited line did not resolve (`tests/…:8` is a test function; the client is at line 5) (R7) | **Adopt.** Every citation now names line 5. |
| 11 | The path is already partially matched today, which understates the hazard (R7) | **Adopt.** Recorded below: `GET /tasks/export` answers 405 today because `PATCH /tasks/{task_id}` claims the path shape; declaration order bites only when a `GET /tasks/{task_id}` is added. |
| 12 | "`csv.reader` over the decoded text is the same reading a spreadsheet performs" over-claims: an in-memory round-trip preserves a field's CRLF, a text-mode file read collapses it (R6) | **Adopt.** The design no longer equates the two. The line-break test asserts against the response **bytes** and normalises line endings explicitly, because the promise R4 makes is that the row does not split — not that a reading tool preserves line-ending bytes. |

### The rounds this design asked

Two rounds, three questions of the twelve available.

- **Round 1 — one question, the encoding fork.** The requester chose **UTF-8 with a
  byte-order mark** — the option the design recommended, so nothing moved off a default and
  no layer was re-derived and no panel re-run was owed.
- **Round 2 — the go-ahead, and one offer.** The requester answered *Write this design*, and
  *Leave it out* to the one withheld item with a live case (a page telling customers the
  export's address).

### Settled forks — the option refused, and why

Each is a *how* the repository settles; none changes what the product promises, so none is a
question for a person.

- **Delivery: build the file and send it in one response — not a streaming response.** R7
  forbids the export ever refusing over the list's size, and a generator that fails halfway
  through a streamed body hands the browser a *partial file with a 200*, which is exactly the
  broken file the PRD's own words rule out. The source list is already fully in memory
  (`app/main.py:31`), so buffering the CSV holds a second copy of the same data, not a new
  order of magnitude. A streamed body also cannot carry `Content-Length`, so the browser
  cannot show the customer how big the save will be.
- **The day in the filename is the server's UTC date, not its local date.** The app carries
  no user, no session and no timezone anywhere (`app/main.py:1-66`), so "the day it was made"
  has no customer-local reading available. UTC is deterministic and does not move with the
  host's `TZ`; a local-date reading would make the same export be named differently on two
  hosts. The cost, stated honestly: an exporter far enough east or west can receive a file
  named for the neighbouring day. Recorded rather than hidden.
- **The address is `GET /tasks/export`.** It nests under the collection it exports and matches
  the app's existing sub-resource shape (`/tasks/{task_id}/done`, `app/main.py:60`). Hazard,
  stated precisely: today `GET /tasks/export` answers **405**, because `PATCH
  /tasks/{task_id}` (`app/main.py:51`) already claims that path shape — so the path is
  *partially* matched before this design lands, and the new route resolves it. If a `GET
  /tasks/{task_id}` is ever added, it must be declared **after** this route, or it will
  swallow `/tasks/export` as a task whose id is `export`.
- **The `done` column reads the literal `true` / `false`.** Required by AC-2. Recorded
  because the obvious implementation (`str(task.done)`) yields `True`/`False` and would fail
  it — the test asserts the lowercase vocabulary directly.
- **`Cache-Control: no-store` was considered and refused.** It was in an earlier draft of this
  design and the red team struck it: no acceptance criterion observes it and the staleness it
  would guard is speculative. Refused, not forgotten.

## Open decisions

The PRD carries no `## Open decisions` section, so the forks this design faced are enumerated
here and dispositioned with the same three outcomes Phase 0 names.

| # | Fork | Disposition | Why |
|---|---|---|---|
| 1 | **The file's text encoding** — UTF-8 with a byte-order mark, or plain UTF-8 | **Escalated and answered** — round 1 of this design; the requester chose the mark | Both are best practice for a CSV and they trade a real cost against a real cost (Excel mis-reads accented text without a mark; a consumer that honours the declared charset sees a stray character at the head of the first column with one). The customer's tool decides which cost they would rather pay, and the PRD's own example names Excel. The answer lands in `REQ-0004`. |
| 2 | **Streaming vs. one response** | Adopt (decided) | See *Settled forks*. AC-7 decides it: a half-streamed body is a broken file, not an error. |
| 3 | **Which day names the file** | Adopt (decided) | See *Settled forks*. The code carries no customer timezone, so UTC is the only deterministic reading. |
| 4 | **The address's shape** | Adopt (decided) | See *Settled forks*. In-repo precedent settles it. |
| 5 | **Keeping the in-memory list** | Adopt (decided) — perpetuate | PG-01's accepted depth bar already took this decision; re-asking it would be re-asking an answered question. |
| 6 | **The too-long refusal (CAP-0006)** | Adopt (decided) — leave deferred | The PRD's necessity test found the mechanism never fires while no ceiling exists, and its own record says a ceiling later "is a new row and a new decision, not a reopening of this one". Not reopened. |
| 7 | **The requirement register was never framed** | Adopt (decided) — framed here | `knowledge/requirements/product.md` exists and is empty; this design writes the cut's promise set as rows and claims them. See `## Commitments`. |
| 8 | **A page telling customers the export's address** | Escalated and answered — round 2; **not pulled in** | Offered with its cost (the `docs` slot names no home, so it could only land as a README section with no docs gate), and declined. Recorded `withheld` in the ledger and in the landed result's `open` list. |

## Commitments

The design adds the cut's promise set to `knowledge/requirements/product.md` as `REQ-0001` …
`REQ-0008`, one row per promise the PRD's R1–R8 states, each claimed by this PRD's
`implements:` and each backed by the acceptance criterion named beside it below.

**Framed by hand, and why.** `fleet_knowledge` is not importable on this box and the `fleet`
submodule is not checked out, so neither `validate_id_collisions.py --allocate` nor
`requirement_query.py` can run — the same tooling gap PG-01's shaping run recorded when it
allocated the `CAP-` ids by reading the corpus. The `REQ-` ids were therefore taken from a
full read of the corpus: no `REQ-` id exists anywhere in it and the register is empty, so
`REQ-0001` … `REQ-0008` are free. The `Kind` vocabulary could not be checked against the
model document either; the values used are stated in the register's own legend. **Both belong
on the next run that has the tooling** — recorded in the landed result's `open` list.

No row was superseded, and no row the design cut is left describing a mechanism that no
longer exists. The rows and their `Needs` edges:

| Row | Promise (abbreviated — the register holds the statement) | Kind | Needs |
|---|---|---|---|
| REQ-0001 | A customer can take the whole list out as one comma-separated file, from an address they open | capability | — |
| REQ-0002 | One row per task under a header naming the columns `title` and `done`, `done` reading `true` or `false` | contract | REQ-0001 |
| REQ-0003 | A title's comma, double quote or line break survives the export without splitting the row | behavior | REQ-0002 |
| REQ-0004 | The file declares its text encoding so accented and symbol-bearing titles open readable | constraint | REQ-0002 |
| REQ-0005 | Every task appears exactly once, in the order the app shows the list — open first, finished last | behavior | REQ-0002 |
| REQ-0006 | An empty list exports as a file with the column names and no rows, not an error | behavior | REQ-0002 |
| REQ-0007 | The export never refuses over the list's size: however long the list, one file comes out | constraint | REQ-0002 |
| REQ-0008 | The saved file's name carries the day it was made | behavior | REQ-0001 |

## Integration trace

This PRD introduces a **net-new mechanism** (a file-serving route that does not exist today)
rather than composing already-shipped pieces, so Phase 1.6's full hop-by-hop trace does not
apply. The narrower **existence-claim citations** do, because the design rests on things it
says already exist:

| Claim the design rests on | Executing line today |
|---|---|
| The task list and its order already exist and are readable | `app/main.py:35` `@app.get("/tasks")` → `list_tasks()` at `app/main.py:36`, returning the list sorted at `app/main.py:39` |
| A task already carries a title and a done flag | `app/main.py:22` `class Task` — `title` (inherited from `TaskIn`, `app/main.py:11-12`) and `done` (`app/main.py:24`) |
| A title may legitimately contain a comma, a quote or a line break | `app/main.py:12` constrains only `max_length=200`; `app/main.py:16-19` rejects only whitespace-only titles |
| The test lane is pytest over the FastAPI test client | `tests/test_tasks.py:1-5`, `pyproject.toml` `[project.optional-dependencies] dev` |

Every claim resolves to a live line — checked at `designed_against:` after the panel caught
three that did not. No hop is uncitable, so there is no Gap from this step.

## Design details

### API surface — one new route

```
GET /tasks/export
```

- **Handler** — `export_tasks()`, declared in `app/main.py` beside the existing routes.
- **Auth / permission** — none. The app has no authentication or authorization layer and
  every route it serves is open (`app/main.py:35`, `:42`, `:51`, `:60`); adding one here
  would be a new surface this PRD never named. The PRD's own `Out` list keeps the promise
  that one customer's tasks are separable from another's in the separate cut that owns it
  (SL-003), which has no PRD yet.
- **Request** — none. No body, no parameters, no query string.
- **Response 200** — `Content-Type: text/csv; charset=utf-8`;
  `Content-Disposition: attachment; filename="tasks-YYYY-MM-DD.csv"`; body = the file below.
- **Errors** — none of its own. There is no id to not-find and no input to reject; the only
  edge case is an empty list, which is a 200 with a header-only body (AC-6).

**The file's bytes.** Built with the standard library, in this order:

1. `io.StringIO()` buffer, `csv.writer(buffer)` — the default `excel` dialect: `,` delimiter,
   `"` quote character, minimal quoting (a field is quoted when it contains the delimiter, a
   double quote, `\r` or `\n`), embedded quotes doubled, CRLF between rows.
2. One header row: `title`, `done`.
3. One row per task, iterating **`_ordered_tasks()`** — never `_tasks.values()` directly — so
   the file's order is the screen's order by construction (AC-5, `app/main.py:36-39`).
4. Each row is `[task.title, "true" if task.done else "false"]` — the lowercase vocabulary
   AC-2 requires.
5. The buffer's text is encoded **`utf-8-sig`** — UTF-8 with a byte-order mark, the round-1
   answer. The `charset` parameter stays `utf-8`.
6. The dated filename is the server's UTC date (`datetime.now(timezone.utc).date().isoformat()`).
7. Returned as a `Response` with the headers above and the body as bytes.

**A domain helper.** The ordering rule moves out of the route handler into a plain function
both handlers call:

```python
def _ordered_tasks() -> list[Task]:
    # Finished tasks sort last; Python's stable sort keeps each group in
    # insertion order. Snapshot the values first so a concurrent write cannot
    # change the dict mid-iteration.
    return sorted(list(_tasks.values()), key=lambda task: task.done)
```

`list_tasks()` becomes `return _ordered_tasks()`.

**An empty list** produces exactly the header row and nothing else — the writer runs, writes
the header, and the loop writes no rows (AC-6).

**A long list** produces one response. Nothing counts the rows, nothing compares the list
against a ceiling, and no code path can refuse on size (AC-7). This is the knowingly-accepted
cost the PRD records: nothing bounds the list, so an export larger than one response can carry
would be slow or partial. Recorded, not papered over with a limit nobody asked for.

**Conventions obeyed:** `slot:languages` and `slot:api-contract` are unfilled, so the design
obeys the conventions the file itself demonstrates — plain `def` handlers, pydantic models
for bodies, `HTTPException` for errors, and no new dependency (`pyproject.toml` is unchanged;
`csv`, `io` and `datetime` are standard library).

### Tests

One new module, `tests/test_tasks_export.py`, plus one new `tests/conftest.py`, on the
repository's existing lane (`make test` → `python3 -m pytest -q`; CI runs the same,
`.github/workflows/ci.yml`).

- **`tests/conftest.py`** carries an autouse fixture that clears `app.main._tasks` and resets
  `_next_id` before every test in the lane, so the empty-list case is testable and no test
  inherits another's tasks (Phase 1.5 finding 2).
- One test per acceptance criterion: AC-1 … AC-8.
- Plus the two error/edge paths the criteria imply but do not spell out: a title containing a
  **line break** stays one row, and the `done` column carries the literal **`true`/`false`**
  (not Python's `True`/`False`).
- Tests read the response **bytes** and decode them with the file's own encoding before
  parsing with `csv.reader` — never `r.text`, which decodes under the declared charset and
  would leave a byte-order mark in the first header cell. The line-break test asserts against
  the raw bytes and normalises line endings explicitly, because R4's promise is that the row
  does not split, not that a reading tool preserves line-ending bytes.

## Reuse

| Capability | Reuse? | How |
|---|---|---|
| The task list and its order | Yes | `_ordered_tasks()` — the rule extracted from `list_tasks()` (`app/main.py:36-39`); both handlers call it, so file order cannot drift from screen order |
| The task model | Yes | `Task` (`app/main.py:22`) — `title` and `done`; nothing new is modelled |
| CSV writing and quoting | Yes | The standard library's `csv` module, `excel` dialect — no dependency added |
| The response idiom | No in-repo precedent | No route in this app answers with a file; the idiom comes from the baseline above |
| The route/handler style | Yes | The existing handlers in `app/main.py` |
| The test lane and client | Yes | `tests/` pytest + FastAPI `TestClient` (`tests/test_tasks.py:1-5`) |
| Storage | No | None exists; the export reads what the app holds |
| UI | No | There is no frontend in this repository |

## Gaps & Improvements

### 4a. Gaps

**None.** Nothing has to exist before this design that does not now: the route is added to
`app/main.py`, and everything it uses — the list, its order, the model, CSV writing, the test
lane — already exists at the lines cited under *Integration trace*. The candidates examined
and cleared: a CSV library (the standard library is sufficient, so no dependency is added), a
date helper (the standard library's `datetime` suffices), a new storage layer (the PRD
deliberately keeps the app's in-memory list), and a permissions layer (the app has none and
this PRD names none).

### 4b. Improvements

| # | Quirk / Improvement | Location | Phase 1.5 decision | Owner / when |
|---|---|---|---|---|
| 1 | The task list is in-memory; a restart loses it | `app/main.py:31` | Perpetuate — the program's accepted depth bar took this decision | N/A — already on the record |
| 2 | Tests share one process-wide task store and never reset it | `tests/test_tasks.py:5` and siblings | Fix now — one `tests/conftest.py` autouse fixture | This PRD |
| 3 | The list's ordering rule lives in a route handler | `app/main.py:35-39` | Fix now — extracted to `_ordered_tasks()` | This PRD |
| 4 | `make validate-knowledge` unconfigured; `fleet_knowledge` not importable | `Makefile` | Reported, not fixed — outside this design's diff | Landed result `open`; no tracker write from a headless run |
| 5 | Thirteen knowledge slots are unfilled stubs | `knowledge/slots/*` | Reported, not fixed | Landed result `open` |

## Scope ledger

| # | Addition | Disposition | Basis |
|---|----------|-------------|-------|
| 1 | A `tests/conftest.py` resetting the shared task store for the whole lane | admitted | AC-6 cannot pass without it: the empty list is untestable while the store keeps another test's tasks. It adds no product surface. |
| 2 | A link or button in the app to reach the export | withheld | Offered and declined in the PRD's own round 3; not re-offered, and there is no page to carry one. |
| 3 | The two-people separation promise inside this PRD | withheld | Offered and declined in the PRD's own round 3; it belongs to the cut that separates one customer's tasks from another's (SL-003). |
| 4 | A column carrying each task's internal number | withheld | Offered and declined in the PRD's own round 3. |
| 5 | A ceiling on the list's length, with a readable refusal | withheld | The PRD's necessity test deferred it; its own record says a ceiling later is a new row and a new decision, not a reopening of this one. |
| 6 | A page telling a customer the export's address | withheld | Offered in round 2 of this design, not pulled in. No acceptance criterion needs a page to follow, and the `docs` slot names no home for one; reported in the landed result's `open` list. |

Nothing on this list is adopted unasked. The offer round put the one item with a live case to
the person; the three the PRD already declined were recorded `withheld` without being
re-offered, because re-asking a question the person answered is the same defect as asking a
new one twice.

## Implementation order

The order `slot:architecture` would list them in — read off the tree, since the slot is
unfilled:

1. **API surface** — `_ordered_tasks()` and the `GET /tasks/export` route, in `app/main.py`.
2. **Tests** — `tests/conftest.py` and `tests/test_tasks_export.py`, alongside it.
3. **Corpus** — the requirement rows, the PRD's `implements:` and `status:`, the journey's
   `covers:`, and this design, in one commit.

There is no contract or codegen layer to regenerate first, no storage, no permission and no
surface behind the API: one file of product code, two files of tests.

## Acceptance criteria

The PRD's eight criteria stand unchanged; each is `[local]`, observable by driving the app
the way a customer does. Each cites the requirement row this design claims for it (Phase 4c
step 6), and **the cross-repo check ran: every criterion below is independently codeable,
testable and mergeable from this repository alone, so there are no cross-repo acceptance
criteria and no companion issue.**

- **AC-1** `[local]` **[REQ-0001]** — Asking for the export from the running product answers
  with a file the browser saves, rather than a page of text.
- **AC-2** `[local]` **[REQ-0002]** — The saved file opens in a spreadsheet with a row of
  column names at the top and one row per task, holding the task's title and a column headed
  `done` with the value `true` or `false`.
- **AC-3** `[local]` **[REQ-0003]** — A title containing a comma or a double quote comes
  through exactly as it was typed, still one row per task.
- **AC-4** `[local]` **[REQ-0004]** — A title containing an accent or a symbol opens readable
  in a spreadsheet, not as garbled characters.
- **AC-5** `[local]` **[REQ-0005]** — Every task in the list appears exactly once, in the
  order the app shows the list — open tasks first, finished ones last.
- **AC-6** `[local]` **[REQ-0006]** — A person whose list is empty gets a file with the column
  names and no rows, rather than an error.
- **AC-7** `[local]` **[REQ-0007]** — A list of several thousand tasks still comes out as one
  file; the export never refuses or errors over the list's size.
- **AC-8** `[local]` **[REQ-0008]** — The saved file is named with the day it was made, e.g.
  `tasks-2026-10-11.csv`.

## Next steps

`/fleet:prd:plan 0001` produces the implementation plans. On the fleet the plan mission runs
it headlessly once this design has landed; at a terminal it is the command a person runs.

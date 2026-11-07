---
type: prd
prd: 0001
title: A customer exports their own task list and opens it in a spreadsheet
status: implementing
status_history:
  - { state: stub, at: 2026-10-11T09:21:01Z, by: prd }
  - { state: prd-drafted, at: 2026-10-11T23:58:24Z, by: fleet:prd:fill }
  - { state: designed, at: 2026-10-12T01:02:07Z, by: fleet:prd:blueprint }
  - { state: planned, at: 2026-10-12T01:14:00Z, by: plan }
  - { state: implementing, at: 2026-10-12T01:18:23Z, by: implement }
slice: SL-002
area: tasks
priority: medium
date: 2026-10-11
author: steffen@zetify.ai
depends_on: []
implements: [REQ-0001, REQ-0002, REQ-0003, REQ-0004, REQ-0005, REQ-0006, REQ-0007, REQ-0008]
source_ideas: []
---

# PRD 0001 — A customer exports their own task list and opens it in a spreadsheet

> **Status:** planned. The stub was filled by `/fleet:prd:fill 0001` on the fleet, in
> three rounds of written questions; the brief the interview started from is kept below
> under `## Brief`. The technical and UX design was written by `/fleet:prd:blueprint 0001`
> on the fleet in two rounds of written questions, against
> `1ea420ff3db601905fd5777dd2bd51e5598d8162`; see `design.md` and `ux-design.md` beside this
> file. The implementation plan was written by `/fleet:prd:plan 0001` — `backend-plan.md`
> beside this file (one lane, two tasks in two waves); ready for implementation.

## Brief

This is the program's **composed proof** — the demonstration that its cuts work together for a person, not any one cut's own proof. It was authored by `/fleet:program:shape PG-01` from the proof the requester accepted on the program's own page, and it is the number the program's `Verified by` cell names.

The demonstration, as accepted:

> Two people each open the export from the running product and save their file; each opens it in a spreadsheet and sees exactly the tasks they put in — including a title with a comma and a quote in it — and a person with an empty list gets a file with only a header, not an error.

Placed under *Customers can export their tasks as CSV.* (PG-01) → *A task list exports as a CSV file* (SL-002). The demonstration also exercises *One customer's tasks are separable from another's* (SL-003), so it can only run once that cut has shipped.

## In Plain Words

A customer can take their whole task list out of the app as a spreadsheet file and open it
in whatever spreadsheet they already use. They ask for the export once and the browser saves
the file; from there it is theirs — sort it, total it, paste it into a report, keep it.

The file is one row per task under a row of column names: the task's title, and whether it
is done. The text is kept exactly as it was typed, so a title with a comma or a quote in it
still reads right, and a title with an accent or a symbol opens readable in Excel rather than
as garbage. A person whose list is empty still gets a file — the column names and no rows —
rather than an error, and however long the list is, the file comes out in one piece.

Nobody has to learn anything new to use it. The app has no screens today and this does not
add one: the export lives at its own address, which the person opens in a browser.

**Example:** Priya runs the Tuesday delivery meeting. Today she reads her task list on screen
and types the still-open ones into her own spreadsheet — about twenty minutes of work that is
out of date the moment somebody ticks a task off. After this, she opens the export's address,
the browser saves `tasks-2026-10-11.csv`, and she opens it in Excel: one row per task, with
its title and whether it is done. She sorts on the done column, pastes the open rows into her
report, and the numbers in it are the real list's.

## Vision Alignment

- **Persona:** whoever runs the weekly planning or delivery meeting — the person who has to
  report on what is open and what is done. This is the persona the program names; the
  repository's `product-vision` slot is an unfilled stub, so no persona label is quoted from
  it (see `## Open questions`).
- **Core loop step:** reporting on the list from the real list rather than from a retyped
  copy. Named by the program, for the same reason.
- **Phase:** not stated — the `product-vision` slot names no product phase.
- **Customer value:** the person stops retyping the list, and the report is built from the
  real tasks instead of a copy that was already stale when it was typed.
- **Differentiation:** the vision names no differentiators (unfilled slot). What this
  strengthens, in the program's own words, is the promise that a customer can get their own
  data out without an engineer doing it for them — the smallest honest test of it.
- **Depends on:** None. No other PRD's code has to execute on this PRD's runtime path.

## Problem and best-practice baseline

The app shows the tasks and does nothing else with them. To report on them, a person reads
them off the screen and types the open ones into their own spreadsheet by hand — and because
the meeting is weekly while the tasks move all week, what they typed is wrong by the time
anyone reads it. There is no way to take the list away in any shape at all.

**Best-practice baseline.** Best-in-class task and issue trackers (GitHub, Jira, Linear) all
offer the same thing for this job: one action that downloads a comma-separated file, with a
header row naming the columns and one row per record, fields containing commas, quotes or
line breaks quoted so they survive intact, an empty list producing a header-only file rather
than an error, and the file named after what it holds. That is the standard the customer
already expects, and this PRD's scope and acceptance criteria adopt it by default. One detail
worth naming: a spreadsheet file has to declare its text encoding, or a title with an accent
opens as garbled characters in Excel — so "text survives intact" is read here to include
non-English text, not only the comma and the quote the ask names. *The seat carries no
browser, so this baseline is established from the repository, the program's own record and
the run's own knowledge, not from live research.*

## Value

One action, one file, and the report becomes true. The person who runs the meeting stops
retyping; the file is used away from the app — opened in a spreadsheet, pasted into a report —
rather than only looked at. It is also the first time a customer can get their own data out of
this product at all, which is what the program exists to test.

## Journey

The agreed flow is [`journeys/flows/tasks-export.md`](../../journeys/flows/tasks-export.md):
the trigger is the weekly meeting coming round; the backbone runs *ask for the export → the
browser saves the file → open it in a spreadsheet → sort and paste it into the report*; the
one surface inside the product is the export's address, and steps 4 and 5 happen outside it.
Every requirement below traces to a step of that backbone. The walking skeleton is steps 2–4:
ask for the export, get a file the browser saves, and open it in a spreadsheet with one row
per task.

## Requirements

- **R1** — A person can ask for the export from the surface they use and receive the file
  itself, not a description of it. *(journey step 2)*
- **R2** — The file is a real spreadsheet file the browser saves, in the common
  comma-separated form, so it opens in any spreadsheet tool without a conversion step.
  *(journey steps 3–4)*
- **R3** — The file carries one row per task under a row of column names: the task's title
  and a column headed `done` holding true or false. *(journey step 4)*
- **R4** — Text is preserved exactly: a comma, a double quote or a line break inside a title
  does not split or break the row, and a title with an accent or a symbol opens readable in a
  spreadsheet rather than garbled. *(journey step 4)*
- **R5** — Every task in the list appears exactly once, in the order the app shows the list —
  open tasks first, finished ones last. *(journey step 4)*
- **R6** — An empty list produces a file with the column names and no rows, rather than an
  error. *(journey step 4)*
- **R7** — The export never refuses over the list's size: however long the list, one file
  comes out. *(journey step 3)*
- **R8** — The saved file's name carries the day it was made, so a weekly exporter's files do
  not silently overwrite each other and the report says which week it covers. *(journey
  step 3)*

## Acceptance criteria

Every criterion is `[local]` — observable by driving the app the way a customer does, in the
repository's own test lane (`tests/`, FastAPI's test client; see `## Open questions` on the
dev-stack slot).

- **AC-1** `[local]` **[REQ-0001]** — Asking for the export from the running product answers
  with a file the browser saves, rather than a page of text.
- **AC-2** `[local]` **[REQ-0002]** — The saved file opens in a spreadsheet with a row of column
  names at the top and one row per task, holding the task's title and a column headed `done`
  with the value `true` or `false`.
- **AC-3** `[local]` **[REQ-0003]** — A title containing a comma or a double quote comes through
  exactly as it was typed, still one row per task.
- **AC-4** `[local]` **[REQ-0004]** — A title containing an accent or a symbol opens readable in
  a spreadsheet, not as garbled characters.
- **AC-5** `[local]` **[REQ-0005]** — Every task in the list appears exactly once, in the order
  the app shows the list — open tasks first, finished ones last.
- **AC-6** `[local]` **[REQ-0006]** — A person whose list is empty gets a file with the column
  names and no rows, rather than an error.
- **AC-7** `[local]` **[REQ-0007]** — A list of several thousand tasks still comes out as one
  file; the export never refuses or errors over the list's size.
- **AC-8** `[local]` **[REQ-0008]** — The saved file is named with the day it was made, e.g.
  `tasks-2026-10-11.csv`.

## Scope

**In V1.** R1–R8: asking for the export from the address a person uses and getting a
downloadable file; one row per task under a row of column names, with the title and a `done`
column of true or false; text integrity including accented and symbol-bearing titles; the
empty list producing a header-only file; no ceiling on the list's length; and a file named
with the day it was made.

**Out.** The too-long refusal — deferred (see `## Open questions`); the promise that two
people's exports never mix — that cut's own promise, not this one's; and, carried from the
program's own decision, no bringing tasks back in, no format other than CSV, no scheduled or
emailed exports, no spreadsheet-style view inside the app, and no choosing columns or a
subset of tasks. Offered in round 3 and declined: a link or button in the app to reach the
export, the two-people separation promise inside this PRD, and a column carrying each task's
internal number.

## Resilience

**Failure domain: N/A — Tier 1 leaf.** The export is a read of a list the app already holds.
It sits on no recovery path, creates no dependency from a recovery path onto the platform, and
nothing anyone would use to fix the product runs through it. Considered, not skipped.

**Accepted risk.** With no ceiling (a person's round-2 choice), nothing bounds the list's
length; if a list ever outgrows what one response can carry, the person may wait, or the
browser may save a partial file. Recorded in `## Open questions` rather than papered over with
a limit nobody asked for.

## Docs impact

**`docs_impact: unknown`.** This capability is customer-facing, so `none` would need a reason
on the record and there is none — but the repository's `docs` slot is unfilled: it names no
coverage rule, no page contract and no home, so no page can be named here. That is the slot's
own degrade, and it means no docs gate runs at verify. Reported in `## Open questions`.

## Source trace

- **Program:** *Customers can export their tasks as CSV.* (PG-01). This PRD is the composed
  proof that program's `Verified by` cell names.
- **Cut:** *A task list exports as a CSV file* (SL-002), under PG-01. Placement decided by the
  run, not asked: SL-002's completion condition covers this work exactly, and it holds no
  terminal member. The other open cut, *Customers can export their tasks as CSV.* (SL-001),
  was considered and rejected — its completion condition restates the program itself rather
  than covering this piece.
- **Stub:** authored by `/fleet:program:shape PG-01`; its brief is kept above verbatim.
- **Rounds:** round 1 — the job story and the persona (answered by steffen@zetify.ai; the
  session that asked it could not be resumed, so its answer is inherited). Round 2 — the
  file's own promises: the list's size, how a task's state reads, the file's name. Round 3 —
  the scope offer; all three withheld items declined.
- **Parked ideas:** the ground was surveyed through Fleet's issue search over this feature
  area and returned no open idea. Nothing was folded, spun or closed.
- **Requirement register:** `knowledge/requirements/product.md` exists for this ground and is
  empty. No requirement rows are claimed (see `## Open questions`).
- **Best-practice baseline:** established in `## Problem and best-practice baseline` above.

## Open questions

- **The composed demonstration's two-people case has no home.** PG-01's proof — which this PRD
  is — also walks *two people each open the export and each sees only their own tasks*. That
  observation is not an acceptance criterion here: it needs a second real user, and the cut
  that provides it (*One customer's tasks are separable from another's*, SL-003) has no PRD
  yet. Nor can it be promoted into SL-002's bar, because SL-002 carries no `## Bar`. **The
  move:** `slice:refine` on SL-002 writes its bar from the slice's page, and `prd:design`
  promotes the criterion once it exists; SL-003 needs its own PRD cut.
- **The too-long refusal is deferred.** The program's decomposition carried *a list too long to
  export is refused with a message a person can read* (CAP-0006 in the tasks feature map). It
  fails the necessity test now: with no ceiling the mechanism never fires, and nothing breaks
  without it — the app holds its tasks in memory. The row stays unshipped. **The move:** if a
  ceiling is ever wanted, it is a new row and a new decision, not a reopening of this one.
- **The requirement register was never framed.** `knowledge/requirements/product.md` exists but
  is empty — the cut skipped its framing — so this PRD claims no requirement rows and
  `implements:` is absent. The id allocator
  (`python3 knowledge/scripts/validate_id_collisions.py --allocate REQ <n>`) cannot run on this
  box: `fleet_knowledge` is not importable and the `fleet` submodule is not checked out. **The
  move:** on a run with the tooling, frame the cut's promise set as register rows and claim
  them here.
- **Four slots are unfilled stubs.** `product-vision` (no persona labels, no core-loop steps,
  no principles, no differentiators, no product phase — the vision check cites the program
  instead), `journeys` (no home for journey records; the flow sits at the path `prd:create`
  names), `docs` (docs impact `unknown`), and `dev-environment` (the `[local]` criteria ride
  the repository's pytest/test-client lane; `make dev` and `make test-e2e` are unconfigured).
- **`make validate-knowledge` is unconfigured in this repository** (exit 2, no recipe), and the
  corpus validators that need `fleet_knowledge` cannot run here. Nothing was validated at
  commit beyond the repository's own `make lint` and `make test`.

## Scope ledger

| # | Addition | Disposition | Basis |
|---|----------|-------------|-------|
| 1 | Accented and symbol-bearing titles open readable in a spreadsheet, not garbled | admitted | required by journey step 4 — the ask's own words are *sees exactly the tasks they put in*; the best-practice baseline for a spreadsheet file |
| 2 | The file is named with the day it was made | admitted | asked in round 2; the person chose the dated name |
| 3 | The export never refuses over the list's size | admitted | asked in round 2; the person chose to always produce the file — which defers the too-long refusal |
| 4 | A link or button in the app that takes a person to the export | withheld | offered in round 3, declined |
| 5 | The two-people separation promise inside this PRD | withheld | offered in round 3, declined |
| 6 | A column carrying each task's internal number | withheld | offered in round 3, declined |

## Next Steps

This PRD is planned and ready for implementation. Run
`/fleet:prd:implement knowledge/prds/0001-a-customer-exports-their-own-task-list` — one lane,
two tasks in two waves, into one branch. On the fleet, the plan mission hands it to the
implement queue once this lands.

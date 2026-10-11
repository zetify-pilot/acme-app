---
type: flow-retro
owner: run:f2e8cfa3-7575-4fb4-ac6e-51700e21a117
---

# Flow Retrospective — task zetify-pilot/acme-app#13 (Mark a task as done from the list)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the
> change. **Suggestions here are NOT applied** — review periodically and promote good ones
> by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / handed-off (PR open, issue → Verify Queue)
- Fix attempts: 1 (red first, then one implementation edit, no failed hypotheses)
- Red→green round trips: 2 tests, both green→red→green under `neuter_check.py`
- Gate runs (`pytest`): 3 (red proof, post-fix full suite 9 passed, neuter round trips)
- Sub-agent dispatches: 0
- Rough wall-clock vs expectation: ~10 min (expected <1h)

## What went smoothly
- The issue body is a two-clause sentence with both clauses concrete ("PATCH /tasks/{id}
  with done=true", "the list shows done tasks last"), so the cause ledger was two lines and
  both clauses map to one file (`app/main.py`).
- The prior run's venv (`/tmp/venv-acme`) was still present, so the suite ran without a
  fresh `pip install`.
- The ordering test asserts over the **whole** list (`done_flags == sorted(done_flags)`),
  which is robust to the shared in-memory `_tasks` state the existing tests leave behind —
  no per-test reset was needed.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | Neither `make` nor a repo-local `pytest` is on `PATH`; the suite had to be run as `/tmp/venv-acme/bin/python -m pytest` | ~2 min | infra | **recurring** (retro `#2`, `#9`, `#7`) |
| 2 | `slot:docs` is not in the slots `fill` map at all, so the docs-impact duty has no home to look in and had to degrade to a PR-body note | ~2 min | process | new |

## Failures encountered (real feature bug vs process artifact)
- None. The red run failed for the right reason (404 from the absent route; wrong ordering),
  not a setup error.

## Root-cause synthesis (what was *actually* the problem)
- The service had one write path for `done` (`POST /tasks/{id}/done`, set-true only) and
  `GET /tasks` returned insertion order. The change adds the partial-update write path the
  issue asked for (`PATCH /tasks/{id}` carrying the boolean) and makes the read path order
  by completion, so both halves of "tick a task off and see what is left" come from one
  model field rather than a second bespoke endpoint.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `fleet init` should record the exact test command in `slot:dev-environment` / `slot:gate` when `make` is absent (or install `make`), so execute commands stop translating targets by hand | mechanical | S | friction #1 — **recurring since `#2`** | no |
| `fleet init` should include a `docs` entry in `knowledge/slots/README.md`'s `fill` map (even pointing at a stub) so the docs-impact duty has a slot to read rather than degrading on every run | mechanical | S | friction #2 | no |

## Recurring across PRDs (flag loudly)
- Friction #1 (no `make` / translated test targets) is now **recurring across four runs**
  (`#2`, `#9`, `#7`, `#13`) and still unaddressed. Promote it.

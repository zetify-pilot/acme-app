---
type: flow-retro
owner: run:f75796f9-4b6e-4a5d-a2d7-2280226833d4
---

# Flow Retrospective — task zetify-pilot/acme-app#7 (README: how to run the tests)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the
> change. **Suggestions here are NOT applied** — review periodically and promote good ones
> by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / handed-off (PR open, issue → Verify Queue)
- Fix attempts: 1 (single edit, no failed hypotheses)
- Red→green round trips: 0 tests (docs-only change); one `scopes` claim under `neuter_check.py`
- Gate runs (`pytest`): 1 (full suite, 6 passed) via the pre-existing venv
- Sub-agent dispatches: 0
- Rough wall-clock vs expectation: ~10 min (expected <1h)

## What went smoothly
- The issue is a one-file documentation change with the exact command named in the body
  (`make test` or `pytest`), so scoping took one read and the cause ledger had two clauses.
- The prior run's venv (`/tmp/venv-acme`) was still present, so the suite ran without a
  fresh `pip install`.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | Neither `make` nor a repo-local `pytest` is on `PATH`; the suite had to be run as `/tmp/venv-acme/bin/python -m pytest` | ~2 min | infra | **recurring** (retro `#2`, `#9`) |
| 2 | `neuter_check.py` requires at least one `tests`/`scopes` entry, so a docs-only change needs a hand-built `scopes` claim over README.md — there is no "docs change" shorthand | ~3 min | process | new |

## Failures encountered (real feature bug vs process artifact)
- None. `pytest` was green at HEAD before and after the edit.

## Root-cause synthesis (what was *actually* the problem)
- The README carried one unlabelled quick-start code block (`pip install` / `pytest` /
  `uvicorn`) and no section that *named* how to run the tests, so a reader looking for
  "how do I run the tests" had to infer it from a bare `pytest` line. The fix gives the
  tests their own named section with the exact command CI runs, and labels the install and
  run steps around it.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `fleet init` should record the exact test command in `slot:dev-environment` / `slot:gate` when `make` is absent (or install `make`), so execute commands stop translating targets by hand | mechanical | S | friction #1 — **recurring since `#2`** | no |
| `neuter_check.py` (or the command doc) should name the docs-only shape explicitly: a single `scopes` claim over the edited doc, `expect` = the matched line count | doc | S | friction #2 | no |

## Recurring across PRDs (flag loudly)
- Friction #1 (no `make` / translated test targets) is now **recurring across three runs**
  (`#2`, `#9`, `#7`) and still unaddressed. Promote it.

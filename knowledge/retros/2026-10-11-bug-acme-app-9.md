---
type: flow-retro
owner: run:7830ad32-87c8-4f99-8c6c-eecdc66af7a6
---

# Flow Retrospective — bug zetify-pilot/acme-app#9 (over-long task title accepted)

> Auto-written by the bug-fix flow's final step. Records how the RUN went, not the fix.
> **Suggestions here are NOT applied** — review periodically and promote good ones by hand.

## Run metrics (rough)
- Command / outcome: bug:fix (autonomous) / handed-off (PR open, issue → Verify Queue)
- Fix attempts: 1 (no failed hypotheses)
- Red→green round trips: 1 test, green→red→green under `neuter_check.py`
- Gate runs (`pytest`): 3 (baseline red proof, post-fix targeted + full suite, neuter round trips)
- Sub-agent dispatches: 0
- Rough wall-clock vs expectation: ~10 min (expected <1h)

## What went smoothly
- The issue body carried a `## Reproduction` block naming an exact test
  (`tests/test_title_length.py::test_create_with_over_long_title_is_rejected`) on branch
  `bug/BUG-1-repro` @ `505eece` — so Phase 2 took the fast path: materialise that test,
  no second one written, and the confirmed red was reproduced in one command.
- The fix is one declarative constraint (`Field(max_length=200)`) on the input model — the
  same boundary the previous blank-title fix (`#2`) used — so `422` comes from FastAPI's
  request-validation path and nothing reaches `create_task`.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | `make` is still not installed, so `make test-one` / `make preflight` had to be translated to direct `/tmp/venv-acme/bin/python -m pytest` invocations | ~2 min | infra | **recurring** (retro `#2`) |
| 2 | `git fetch origin bug/BUG-1-repro` failed (terminal prompts disabled — no credentials for the HTTPS remote), so the repro branch could not be fetched; the named sha happened to be present locally and was used instead | ~1 min | infra | new |

## Failures encountered (real feature bug vs process artifact)
- None. The red run failed for the right reason (`assert 201 == 422`), not a setup error.

## Root-cause synthesis (what was *actually* the problem)
- `TaskIn.title` was a bare `str` (with a blank-check validator only): the model validated
  the *presence* of content but never its *extent*, so Pydantic accepted an arbitrarily long
  string. The fix declares the upper bound declaratively on the input model — the boundary
  where the rule belongs — so the request fails validation before the handler runs and
  nothing is stored. The output model `Task` inherits it, so no separate guard is needed on
  the read path.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `fleet init` should record the exact test command in `slot:dev-environment` / `slot:gate` when `make` is absent (or install `make`), so execute commands stop translating targets by hand | mechanical | S | friction #1 — **recurring since `#2`** | no |
| When a `## Reproduction` block names a branch, the flow should note that fetching it may need credentials; if the sha is already local, use it and say so | doc | S | friction #2 | no |

## Recurring across PRDs (flag loudly)
- Friction #1 (no `make` / translated test targets) is now **recurring** — flagged in the
  `#2` retro and still unaddressed. Promote it.

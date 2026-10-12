---
type: flow-retro
owner: run:b33e1dce-33e7-44df-b697-982b86884078
---

# Flow Retrospective — task zetify-pilot/acme-app#32 (Withdraw SL-001 — its completion condition repeats PG-01's own promise)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the
> change. **Suggestions here are NOT applied** — review periodically and promote good ones
> by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched on head)
- Fix attempts: 1 (single register-cell edit, no failed hypotheses)
- Red→green round trips: 0 tests (register-only change); one `scopes` claim under `neuter_check.py`
- Gate runs (`pytest`): 1 (full suite, 9 passed)
- Sub-agent dispatches: 0
- Rough wall-clock vs expectation: ~12 min (expected <1h)

## What went smoothly
- The issue named the exact file and cell (`knowledge/slices.md`, SL-001's `Disposition`) and
  offered both acceptable values, so the cause ledger was one line and the edit was one cell.
- `fastapi`/`pytest` were already importable from the engine python, so the suite ran with no
  fresh `pip install`.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | `make` is not installed, so `make validate-knowledge` / `make preflight` had to be translated to direct `python3 -m pytest` / `compileall` | ~2 min | infra | **recurring** (`#2`, `#9`, `#7`, `#13`) |
| 2 | `fleet_knowledge` is not importable (no installed package, no checked-out `fleet` submodule), so `gen_roadmap.py` / `program_of.py` and `fleet check --only bars` cannot run in this checkout at all | ~3 min | process | new |
| 3 | `slot:slices` names `knowledge/slices.md` as the register, but `slice:edit` Step 5 describes a generated table fed by `knowledge/slices/rows/SL-NNN.json` fragments this corpus does not carry — the command's schema and the repo's committed table disagree | ~4 min | process | new |

## Failures encountered (real feature bug vs process artifact)
- None. The suite was green before and after; the change is a single markdown cell.

## Root-cause synthesis (what was *actually* the problem)
- Not a code defect: PG-01's cut register carried a third slice (`SL-001`) whose `Done when`
  restated the program's own promise word for word, so it asserted no work of its own. The
  recorded human decision (2026-10-12, steffen@zetify.ai) is to fold it into its two real
  successors (`SL-002`, `SL-003`); the register cell was the only artifact carrying the
  duplicate claim, so the fix is that cell and nothing else.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `fleet init` should record the exact test command in `slot:dev-environment` / `slot:gate` when `make` is absent (or install `make`), so execute commands stop translating targets by hand | mechanical | S | friction #1 — **recurring since `#2`** | no |
| When `slot:slices` resolves to a committed table (`knowledge/slices.md`) rather than row fragments, `slice:edit` should say so and edit the table directly, instead of pointing at `knowledge/slices/rows/` that does not exist here | doc | S | friction #3 | no |

## Recurring across PRDs (flag loudly)
- Friction #1 (no `make` / translated test targets) is now **recurring across five runs**
  (`#2`, `#9`, `#7`, `#13`, `#32`) and still unaddressed. Promote it.

## Rework cycle (2026-10-12, later run — checks-timed-out re-dispatch)
- The first handoff left PR #39 open on head `5ee1312` with checks dispatched, but the fleet
  could not read the PR for two hours (its own note: "the forge errored, the branch or PR is
  gone, or the fleet's token no longer reaches the repository") and moved the issue to Rework
  Queue with `checks-timed-out`. No verdict was ever recorded, so this is **not** a refuted
  verification — the fix was never reviewed.
- The change itself was re-read and stands: `knowledge/slices.md` SL-001's `Disposition` reads
  `superseded by SL-002, SL-003`; SL-002 and SL-003 are byte-identical to `main`. Nothing about
  the cause ledger changed.
- Remediation: a fresh head on the same branch and the same PR, so a new `pull_request`
  `synchronize` event dispatches `ci` on a head the fleet has not already given up on.
- New friction this cycle: the seat's GitHub token carries **no `checks:read`** permission, so
  `check-runs` / `statusCheckRollup` / `gh pr checks` all return HTTP 403
  (`Resource not accessible by integration`). Checks can only be *inferred* from
  `mergeStateStatus: UNSTABLE` held across a re-read, never counted. The sibling run on
  `#33`/PR #40 hit the same wall the same day. **Recurring across two runs** — the dispatch
  missions ask a seat to confirm `check-runs total_count` is non-zero, which no seat here can
  actually do.

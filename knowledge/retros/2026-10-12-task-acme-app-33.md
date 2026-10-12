---
type: flow-retro
owner: run:95e3ff99-4401-465b-b97f-bb4487ed8f63
---

# Flow Retrospective — task zetify-pilot/acme-app#33 (Record the dropped too-long refusal — withdraw CAP-0006 and drop it from PG-01's Requires)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the
> change. **Suggestions here are NOT applied** — review periodically and promote good ones
> by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched on head)
- Fix attempts: 1 (two register cells + the map's legend and note, no failed hypotheses)
- Red→green round trips: 0 tests (register-only change); 3 `scopes` claims under `neuter_check.py`
- Gate runs (`pytest`): 1 (full suite, 9 passed)
- Sub-agent dispatches: 0
- Rough wall-clock vs expectation: ~15 min (expected <1h)

## What went smoothly
- The issue named the exact file, cell and target value for both edits, and named a third
  capability (`CAP-0007`) as explicitly out of scope, so the cause ledger was three lines and
  the scope boundary was drawn by the issue rather than guessed.
- The sibling withdrawal task (`#32`, PR #39) had already landed the same shape of change —
  one register cell, `superseded by …` in the Disposition column — so the precedent for a
  "withdraw a row" task was legible from the corpus without asking.
- `pytest` and `fastapi` were already importable, so the suite ran with no fresh `pip install`.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | The feature map's `Ships in` marker vocabulary (`(core)`/`(shipped)`/`(retired)`) is defined **only** in `knowledge/scripts/gen_program_plan.py` — the script's own comment points at `knowledge/features/README.md`, but the README documents neither `(retired)` nor the fact that a bare `—` is read as work-to-build. Had to read the script to learn the one marker that means "not wanted". | ~8 min | process | new |
| 2 | `make` is not installed, so `make test` / `make lint` had to be translated to `python3 -m pytest -q` / `python3 -m compileall` | ~2 min | infra | **recurring** (`#2`, `#9`, `#7`, `#13`, `#32`) |
| 3 | `fleet_knowledge` is not importable and `knowledge/scripts/knowledge_registers.py` is absent, so `gen_program_plan.py` (the reader that consumes the `(retired)` marker) cannot be run here to confirm the new row classifies as `retired` rather than `gap` — confirmed by reading the regexes instead | ~4 min | process | **recurring** (`#32`, `#13`) |

## Failures encountered (real feature bug vs process artifact)
- None. The suite was green before and after; the change is markdown register cells.

## Root-cause synthesis (what was *actually* the problem)
- Not a code defect. PG-01's decomposition carried a capability (*a list too long to export is
  refused with a message a person can read*, `CAP-0006`) that the program's `Requires` cell and
  the tasks feature map both still listed as wanted work, while the program's proof PRD
  (`PRD-0001`, `R7`/`AC-7`) promises the opposite — that the export never refuses over the
  list's size. The recorded human decision (2026-10-12, steffen@zetify.ai) settled the conflict
  in the PRD's favour. The two register cells were the artifacts still over-claiming, so the
  fix is those cells and nothing else.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| Document the `Ships in` marker vocabulary (`(core)`/`(shipped)`/`(retired)`, and that a bare `—` is read as *build this*) in `knowledge/features/README.md`, where `gen_program_plan.py` already points for it — the map's own legend and the planner's parser currently disagree about what a cell can say | doc | S | friction #1 | no — the script's comment names the README, but the README omits it |
| `fleet init` should record the exact test command in `slot:gate` when `make` is absent (or install `make`), so execute commands stop translating targets by hand | mechanical | S | friction #2 — **recurring since `#2`** | no |

## Recurring across PRDs (flag loudly)
- Friction #2 (no `make` / translated test targets) is now **recurring across six runs**
  (`#2`, `#9`, `#7`, `#13`, `#32`, `#33`) and still unaddressed. Promote it.
- Friction #3 (the `fleet_knowledge` package and `knowledge_registers.py` are absent, so the
  corpus' own readers cannot run) recurs from `#32` and `#13`.

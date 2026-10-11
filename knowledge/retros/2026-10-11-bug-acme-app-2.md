---
type: flow-retro
owner: run:9d948ae4-434f-4553-a825-7d65dae0acd8
---

# Flow Retrospective — bug zetify-pilot/acme-app#2 (blank task title accepted)

> Auto-written by the bug-fix flow's final step. Records how the RUN went, not the fix.
> **Suggestions here are NOT applied** — review periodically and promote good ones by hand.

## Run metrics (rough)
- Command / outcome: bug:fix (autonomous) / handed-off (PR open, issue → Verify Queue)
- Fix attempts: 1 (no failed hypotheses)
- Red→green round trips: 2 tests, both green→red→green under `neuter_check.py`
- Gate runs (`pytest`): 4 (baseline red proof, post-fix targeted, full suite, neuter round trips)
- Sub-agent dispatches: 0
- Rough wall-clock vs expectation: ~15 min (expected <1h)

## What went smoothly
- The issue body was forensic: it named the exact request bodies (`""` and `"   "`),
  the observed status (201) and the expected one (422) — so the cause ledger wrote
  itself and no investigation was needed.
- The single-file app made the root cause unambiguous: `TaskIn.title` was a bare
  `str` with no content constraint, so request validation had nothing to reject.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | `pip` not on PATH; deps had to be installed into a local `.venv` before any test could run | ~3 min | infra | new |
| 2 | `make` is not installed, so every `make test-one` / `make preflight` / `make lint` in the command body had to be translated to a direct `pytest` / `compileall` invocation | ~2 min | infra | new |

## Failures encountered (real feature bug vs process artifact)
- None. Both red runs failed for the right reason (`assert 201 == 422`), not a setup error.

## Root-cause synthesis (what was *actually* the problem)
- The endpoint validated the *presence* of a JSON field (Pydantic required it) but never
  its *content*, so an empty or whitespace-only string passed. The fix is a content
  constraint on the input model — the boundary where the rule belongs — not a guard inside
  the handler, so `422` comes from FastAPI's request-validation path and nothing is stored.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `fleet init` should record, in `slot:dev-environment` / `slot:gate`, the exact test command when `make` is absent (or install `make`), so execute commands do not translate targets by hand | mechanical | S | friction #1 and #2 | no |
| When `slot:retro-corpus` is unfilled, the execute commands should name their default landing directory explicitly (this run guessed `knowledge/retros/` from a passing mention in `autonomous-drive.md`) | doc | S | ambiguity in where the retro goes | partially (`autonomous-drive.md` mentions `knowledge/retros/` once) |

## Recurring across PRDs (flag loudly)
- None — this is the first retro in this repository's corpus.

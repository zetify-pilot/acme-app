---
type: flow-retro
owner: run:zetify-pilot-acme-app-76
---

# Flow Retrospective — task zetify-pilot/acme-app#76 (README: list the CI workflow under Project layout)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the change.
> **Suggestions here are NOT applied** — review periodically and promote good ones by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched)
- Fix attempts: 1 (no failed hypotheses)
- Gate runs: 2 (`pytest` full suite once — green; `neuter_check.py` scopes ledger once — 2/2 covered)
- Sub-agent dispatches: 0 (a single added markdown line, fully mechanical — the coordinator applied it directly)
- Rough wall-clock vs expectation: ~5 min (expected <1h)

## What went smoothly
- The issue is a pure docs task naming the file, the exact insertion point ("after the
  `knowledge/` bullet") and the exact text, so Step 2's cause ledger needed no interpretation
  and Step 1 triage was immediate (task, not bug/feature in disguise).
- The check session's own comment had already verified the bullet is genuinely absent at HEAD
  `c675aba` and that `.github/workflows/ci.yml` exists, so no re-verification of the premise
  was needed beyond confirming `README.md:28` still holds the three existing bullets.
- The branch was cut from a freshly fetched `origin/main` (`c675aba`), so no rebase was owed
  before the push.
- No git hooks are installed on this repo (`core.hooksPath` unset, no hook files), so the
  commit was instant — the hook-silence hazard the mission warns about did not apply here.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | `neuter_check.py`'s coverage is computed from `git diff <base>...HEAD`, i.e. committed history only — a working-tree edit is invisible to it, so running the gate before committing reports the added line as *uncovered*. The ordering (commit first, then gate) is not stated in the command body | ~4 min | process | recurring (the #71 retro hit the sibling shape: the docs-only ledger had to be invented) |
| 2 | The `scopes` pattern must match a line the diff actually touches, so a natural claim like "the bullet sits under `## Project layout`" is unusable (the heading line is untouched) — the pattern has to be narrowed to the added line itself | ~2 min | process | new |

## Failures encountered (real feature bug vs process artifact)
- None. The suite was green before and after; the diff is exactly the one line the issue named.

## Root-cause synthesis (what was *actually* the problem)
- Nothing was broken. `README.md`'s `## Project layout` section listed `app/main.py`, `tests/`
  and `knowledge/` but not the CI workflow that `.github/workflows/ci.yml` defines; the fix is
  the literal addition of one bullet after the `knowledge/` bullet, with no other file touched
  (verified: `git diff --name-only origin/main...HEAD` is exactly `README.md` plus this retro).
- The completeness gate's honest shape for a docs-only change is a **scopes** ledger, not a
  **tests** ledger: no code path's removal makes a test go red, so the claim is counted
  instead — two patterns, each matching exactly the added line.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `neuter_check.py`'s docstring (or the implement command body) should state that coverage is computed from committed history, so the docs-only ledger must be run **after** the commit that carries the fix | doc | S | friction #1 | no |
| The same docstring should give the docs-only worked example — "narrow the pattern to the added line; the surrounding context lines are not in the diff" | doc | S | friction #2 | partially — the script's own docstring shows a `scopes` example but not this constraint |

## Recurring across PRDs (flag loudly)
- Friction #1 is the second occurrence of the "docs-only change has no obvious ledger shape"
  family in two days (#71 filed the sibling on the same script). The script is the right home
  for the fix; the two retros should be read together.

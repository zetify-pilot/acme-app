---
type: flow-retro
owner: run:57163345-622a-4627-b91c-78c770d352d0
---

# Flow Retrospective — task zetify-pilot/acme-app#65 (README: say which Python version the service needs)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the
> change. **Suggestions here are NOT applied** — review periodically and promote good ones
> by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched)
- Fix attempts: 1 (one docs edit; no failed hypotheses)
- Red→green round trips: 0 tests — docs-only change, no executable behavior to neuter (friction #1)
- Gate runs (`pytest`): 0 (change touches `README.md` only; `git diff --name-only` is one file)
- Sub-agent dispatches: 0
- Rough wall-clock vs expectation: ~6 min (expected <1h)

## What went smoothly
- The issue body states the exact line to add, verbatim, in backticks — so the cause ledger
  was two literal lines (the gap, and the line to insert) and the whole change is one `Edit`
  on `README.md` directly under `## Install`.
- The claim in the inserted line is checkable against the tree: `pyproject.toml:4` really is
  `requires-python = ">=3.11"`, so "3.11 or newer" is true of this repo, not just copied.
- No open PR existed for `#65` (`gh pr list --search` returned `[]`), so no branch
  reconciliation was needed — a fresh `agent/task-acme-app-65` off `origin/main`.
- The `scopes` half of `neuter_check.py` is a real check for a docs line: it greps the
  inserted pattern and requires exactly one site, covered by the diff — it went red before the
  commit (0 covered) and green after, which is the denominator check the gate asks for.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | The completeness gate mandates `neuter_check.py` "for every kind of work", but a docs-only change names no test — the ledger's `tests` half is empty and only the `scopes` half does work, so the mandated red→green proof is only half available | ~3 min | process | **recurring** (`#55`) |
| 2 | `slot:docs` is absent from `knowledge/slots/` entirely (not merely unlisted in the `fill` map), so the docs-impact duty degraded to a PR-body note — the same degradation retro `#13` and `#55` recorded | ~1 min | process | **recurring** (`#13`, `#55`) |
| 3 | The scope check reads `git diff <base>...HEAD`, so an uncommitted working-tree change reports "1 site(s), 0 covered" and reads as a gate failure until the edit is committed | ~2 min | process | new |

## Failures encountered (real feature bug vs process artifact)
- One process artifact: the first `neuter_check.py` run failed (`1 site(s), 0 covered`) purely
  because `_diff_lines` diffs `base...HEAD` — the committed branch — while the edit was still
  uncommitted. Committing first and re-running passed. Nothing was broken in the README.

## Root-cause synthesis (what was *actually* the problem)
- Nothing was broken. The README told a reader how to install (`pip install -e '.[dev]'`) but
  never the Python the package needs, so the requirement was discoverable only by opening
  `pyproject.toml`. The change surfaces the one already-pinned fact (`>=3.11`) at the point of
  use. There is no code path involved and no root cause beyond a documentation gap.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `neuter_check.py` (or the gate prose) should state explicitly that a change with no executable behavior — docs, prose, config — is satisfied by the `scopes` half alone, so docs runs stop treating an empty `tests` list as a gate gap | mechanical | S | friction #1 | no — filed before in `#55`, still unaddressed |
| `fleet init` should include a `docs` entry in `knowledge/slots/` (even a stub) so the docs-impact duty has a home to read rather than degrading on every run | mechanical | S | friction #2 | no — filed in `#13` and `#55`, still unaddressed |
| `neuter_check.py` should say, when a scope site is found but nothing is covered, that the fix may simply be uncommitted (`git diff <base>...HEAD` reads commits, not the worktree) — the current "0 covered" reads as a real gate failure | mechanical | S | friction #3 | no |

## Recurring across PRDs (flag loudly)
- Friction #2 (no `docs` slot) is now on its **third** retro (`#13`, `#55`, `#65`) and is still
  unaddressed. Promote it.
- Friction #1 (docs-only changes and the `neuter_check.py` `tests` half) is on its **second**
  retro (`#55`). Promote it.

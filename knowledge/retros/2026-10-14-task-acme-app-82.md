---
type: flow-retro
owner: run:zetify-pilot-acme-app-82
---

# Flow Retrospective — task zetify-pilot/acme-app#82 (README: add an HTML comment probe line at the end)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the change.
> **Suggestions here are NOT applied** — review periodically and promote good ones by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched)
- Fix attempts: 1 (no failed hypotheses)
- Gate runs: 1 (`neuter_check.py` scopes ledger, 1/1 covered); `pytest` not run — the diff is
  one markdown line and touches no code path
- Sub-agent dispatches: 0 (a single appended line, fully mechanical — applied by the coordinator)
- Rough wall-clock vs expectation: ~8 min (expected <1h)

## What went smoothly
- No open PR existed for `#82` (`gh pr list --search` matched only unrelated PR #37), so a fresh
  `agent/task-acme-app-82` was cut off a freshly fetched `origin/main` (`209bb12`) — no rebase owed.
- The issue names the file, the insertion point ("the very end of the file") and the exact line,
  so the cause ledger was two literal lines and the change was one `Edit`.
- `knowledge/retros/2026-10-14-task-acme-app-76.md` (two days old, same repo) had already worked
  out the docs-only ledger shape, so the gate needed no invention this time.
- No git hooks are installed on this repo, so the commit was instant.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | The probe line is an **HTML comment**, and the tracker's issue view strips HTML comments from the rendered body — the line to add arrived as a blank. It had to be recovered from GitHub's raw issue body (`gh issue view 82 --json body`). The issue text says "add one line, exactly" and then shows nothing | ~4 min | process | new |
| 2 | `neuter_check.py`'s coverage is computed from `git diff <base>...HEAD` (committed history), so the gate must run *after* the commit — the same ordering trap retros `#65` and `#76` both hit | ~1 min | process | **recurring** (`#65`, `#76`) |

## Failures encountered (real feature bug vs process artifact)
- One process artifact: the first read of the issue showed the probe line as an empty gap, because
  Fleet's `get_issue` body rendering drops the HTML comment. Nothing was broken in the README; the
  raw GitHub body carries the line verbatim.

## Root-cause synthesis (what was *actually* the problem)
- Nothing was broken. This is an acceptance-test fixture (IMP-1922: an armed PR with a red required
  check goes to rework) that needs a real, tiny, mergeable-looking change as its carrier. The
  README lacked the marker line the fixture asserts on; the fix is its literal append at EOF, with
  no other file touched (`git diff --name-only origin/main...HEAD` is `README.md` plus this retro).

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| The task-implement brief should say: when the issue quotes a line inside backticks and the rendered body shows it empty, re-read the raw tracker body before assuming the line is missing | doc | S | friction #1 | no |
| `neuter_check.py`'s docstring should state that coverage reads committed history, so a docs-only ledger runs after the commit | doc | S | friction #2 | no — filed in `#65` and `#76` |

## Recurring across PRDs (flag loudly)
- Friction #2 (docs-only ledger ordering) is now on its **third** retro (`#65`, `#76`, `#82`) and
  is still unaddressed. Promote it.
- The "docs-only change has no obvious ledger shape" family (`#55`, `#65`, `#71`, `#76`) did *not*
  recur here — the `scopes`-only ledger from `#76` transferred cleanly. Worth keeping as the
  documented shape.

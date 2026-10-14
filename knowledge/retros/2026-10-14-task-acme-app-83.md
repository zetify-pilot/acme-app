---
type: flow-retro
owner: run:zetify-pilot-acme-app-83
---

# Flow Retrospective — task zetify-pilot/acme-app#83 (README: add an HTML comment probe line at the end)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the change.
> **Suggestions here are NOT applied** — review periodically and promote good ones by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched)
- Fix attempts: 1 (no failed hypotheses)
- Gate runs: 1 (`neuter_check.py` scopes ledger, 1/1 covered); `pytest` not run — the diff is one
  markdown line and touches no code path
- Sub-agent dispatches: 0 (a single appended line, fully mechanical — applied by the coordinator)
- Rough wall-clock vs expectation: ~6 min (expected <1h)

## What went smoothly
- No open PR existed for `#83` (`gh pr list --search "83"` returned nothing; no
  `agent/task-acme-app-83` ref on the remote), so a fresh branch was cut off a freshly fetched
  `origin/main` (`209bb12`) — no rebase owed before the push.
- The sibling acceptance fixture `#82` (PR #84, same repo, minutes old) had already worked out
  both the recovery trick for the probe line and the docs-only ledger shape, so neither had to be
  re-derived.
- No git hooks are installed on this repo (`core.hooksPath` unset, no hook files), so the commit
  was instant — the hook-silence hazard the mission warns about did not apply here.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | The probe line is an **HTML comment**, and Fleet's `get_issue` body rendering strips HTML comments — the line to add arrived as a blank gap after "add one line, exactly:". It had to be recovered from GitHub's raw body (`gh issue view 83 --json body`). The issue text says "exactly" and then shows nothing | ~3 min | process | **recurring** (the `#82` retro filed the identical finding hours earlier) |
| 2 | `neuter_check.py`'s coverage is computed from `git diff <base>...HEAD` (committed history), so the gate must run *after* the commit — a working-tree edit reads as uncovered | ~1 min | process | **recurring** (`#71`, `#76`, `#82`) |

## Failures encountered (real feature bug vs process artifact)
- One process artifact: the first read of the issue showed the probe line as an empty gap, because
  Fleet's `get_issue` body rendering drops the HTML comment. Nothing was broken in the README; the
  raw GitHub body carries the line verbatim.

## Root-cause synthesis (what was *actually* the problem)
- Nothing was broken. This is an acceptance-test fixture (IMP-1924: a person-only blocker at the
  merge-wait ceiling is a question) that needs a real, tiny, mergeable-looking change as its
  carrier. The README lacked the marker line the fixture asserts on; the fix is its literal append
  at EOF, with no other file touched (`git diff --name-only origin/main...HEAD` is `README.md`
  plus this retro).
- The completeness gate's honest shape for a docs-only change is a **scopes** ledger, not a
  **tests** ledger: no code path's removal makes a test go red, so the claim is counted instead —
  one pattern matching exactly the added line.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| Fleet's `get_issue` body rendering should preserve HTML comments (or the issue view should warn that they were stripped), since acceptance fixtures in this repo are written as HTML comments | code | M | friction #1 | no |
| `neuter_check.py`'s docstring (or the implement command body) should state that coverage is computed from committed history, so the docs-only ledger must be run **after** the commit that carries the fix | doc | S | friction #2 | no |

## Recurring across PRDs (flag loudly)
- Both frictions are repeats: #1 is the third "docs-only change has no obvious ledger shape" hit in
  four days (#71, #76, #82) and #2 is the second HTML-comment-stripping hit today (#82). Neither
  fix has landed; the script docstring and the tracker rendering are the right homes.

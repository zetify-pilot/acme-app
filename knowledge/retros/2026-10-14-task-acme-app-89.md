---
type: flow-retro
owner: run:zetify-pilot-acme-app-89
---

# Flow Retrospective — task zetify-pilot/acme-app#89 (README: add an HTML comment probe line at the end)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the change.
> **Suggestions here are NOT applied** — review periodically and promote good ones by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched)
- Fix attempts: 1 (no failed hypotheses)
- Gate runs: 1 (`neuter_check.py` scopes ledger, 1/1 covered); `pytest` not run as a gate — the
  diff is one markdown line and touches no code path (the issue says "Change nothing else.")
- Sub-agent dispatches: 0 (a single appended line, fully mechanical — applied by the coordinator)
- Rough wall-clock vs expectation: ~8 min (expected <1h)

## What went smoothly
- No open PR existed for `#89` (`gh pr list --search "89"` returned only unrelated PR #37; no
  `agent/task-acme-app-89` ref on the remote), so a fresh branch was cut off a freshly fetched
  `origin/main` (`209bb12`) — no rebase owed before the push.
- The sibling acceptance fixtures `#82`/`#83` had already worked out the two recoveries this
  fixture needs, so neither had to be re-derived: (a) Fleet's issue rendering **strips HTML
  comments**, so the probe line reads blank in the body as served — `gh issue view 89 --json body`
  returns the raw text and shows `<!-- acceptance probe VER-17787 -->`; (b) the docs-only ledger
  shape is a `scopes` ledger with the `tests` half empty by construction.
- The check session's own comment on `#89` independently recorded the same recovered line
  (`<!-- acceptance probe VER-17787 -->`, matching the `#82`/`#83` form), so the two derivations
  agree.

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | Fleet's issue rendering strips HTML comments, so the single load-bearing string of this task is invisible in `get_issue`'s body text; it had to be recovered from a raw `gh issue view` (and cross-checked against the check comment and the `#82`/`#83` siblings) | ~3 min | tooling | recurring (the `#89` check session hit it and left a body-repair note) |
| 2 | `neuter_check.py` computes scope coverage from committed history (`git diff <base>...HEAD`), so the gate must run **after** the commit that carries the fix — running it on a dirty tree reports the added line as uncovered | ~2 min | process | recurring (third occurrence: `#71`, `#76`, now `#89`) |

## Failures encountered (real feature bug vs process artifact)
- None. The tree was clean and the suite untouched; the diff is exactly the one line the issue named.

## Root-cause synthesis (what was *actually* the problem)
- Nothing was broken. This is an acceptance fixture on uncovered ground (no capability or
  requirement row covers a README probe line), so the whole task is the literal addition of one
  HTML comment as the final line of `README.md`, with nothing else changed (verified:
  `git diff --name-only origin/main...HEAD` is exactly `README.md` plus this retro).
- The honest ledger for a docs-only change is the **scopes** half, not the **tests** half: no code
  path's removal can make a test go red, so the claim is counted instead — one pattern matching
  exactly the added line.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `neuter_check.py`'s docstring (or the implement command body) should state that scope coverage is computed from committed history, so the docs-only ledger must run **after** the commit carrying the fix | doc | S | friction #2 | no — three retros have now filed it |
| When a task's own body carries an HTML comment, `get_issue` should return it (or say it was stripped) — the string is the deliverable and its absence is silently indistinguishable from an empty line | tool | M | friction #1 | no — the `#89` check session patched around it with a body-repair note |

## Recurring across PRDs (flag loudly)
- Friction #2 is the **third** occurrence in three days (`#71`, `#76`, `#89`) of the same missing
  sentence. It is a one-line docstring fix on `knowledge/scripts/neuter_check.py` and should be
  promoted by hand now rather than re-filed.
- Friction #1 is shared by all three acceptance fixtures (`#82`/`#83`/`#89`); the probe line is
  the entire payload of each, so the stripping defect costs every one of them the same recovery.

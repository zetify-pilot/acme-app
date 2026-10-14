---
type: flow-retro
owner: run:279b8ca8-1c30-4c53-9feb-8980605cf742
---

# Flow Retrospective — task zetify-pilot/acme-app#92 (Name SL-003's proof — an automated test that one customer can never read another's tasks)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the change.
> **Suggestions here are NOT applied** — review periodically and promote good ones by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched)
- Fix attempts: 1 (one register cell; no failed hypotheses)
- Red→green round trips: 0 tests — a register cell is not executable behaviour, so the ledger is
  scopes-only (friction #1, now the fifth retro in this family)
- Gate runs: `neuter_check.py` scopes ledger once — 2/2 covered, exit 0; `python3 -m compileall -q
  app tests` once (clean); `pytest` once (10 passed, before the edit — a markdown-only diff cannot
  move it)
- Sub-agent dispatches: 0 (a single markdown cell, fully mechanical — applied directly)
- Rough wall-clock vs expectation: ~20 min (expected <1h) — most of it was deciding what the
  `Verified by` cell may legally contain and reconciling with the sibling in flight

## What went smoothly
- The issue is unusually complete for a register edit: it quotes the recorded decision
  (2026-10-14, steffen@zetify.ai) verbatim, names the exact cell, names what the proof is
  *not* ("two people, two files" — PG-01's own demonstration, which a cut may not borrow), and
  says outright not to file a second task or re-open the question. Step 2's cause ledger is seven
  quoted clauses and Step 1 triage was immediate (task, not bug/feature in disguise).
- The change is one cell on `knowledge/slices.md:13` and the diff proves it: `git diff
  origin/main...HEAD -- knowledge/slices.md` is a single changed line, and a pipe-count read of
  the table shows all five rows still carry nine columns.
- The "nothing else in the register changes" clause is checkable against the tree rather than
  asserted: `SL-003`'s `Name`, `Kind`, `Program`, `Done when`, `Depends on` (`SL-002`) and
  `Disposition` (`adopted`) are byte-identical to `origin/main`, and `knowledge/programs.md:9`
  still reads `Verified by: 0001` — the cut's cell names an automated test, never `0001`, so
  `knowledge/programs/PG-01.md:108`'s "neither slice's `Verified by` names it" still holds.
- The scopes half of `neuter_check.py` is a real denominator check here and went 2/2: one
  anchored pattern for the register row (`^\| SL-003 \|`, exactly 1 site, covered by the diff)
  and one for the new claim text (exactly 1 site in `knowledge/`, covered).

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | A register cell has no executable behaviour, so `neuter_check.py`'s `tests` half is empty and only `scopes` does work — the same shape retros `#55`, `#65`, `#76` and `#91` recorded for docs-only changes. The gate prose ("run the shared neuter check … for every kind of work") still does not say the scopes half alone satisfies a non-executable change | ~4 min | process | **recurring** (`#55`, `#65`, `#76`, `#91`) |
| 2 | **What a slice's `Verified by` cell may legally contain is undecidable on this box** (the same finding `#91` recorded). `slice:edit` requires every entry to resolve to a real PRD number or `drill:<stem>` over a real `knowledge/drills/<stem>.md`; this corpus has one PRD (0001 — the program's own proof, which the issue forbids by name) and **no `knowledge/drills/` directory at all**. The decision names a *test that ships*, not a drill to be recorded, so neither legal form fits and the cell carries the test in prose. `fleet_knowledge` is not importable here (`fleet.py` refuses) and `make` is not installed, so nothing on this box can confirm the choice | ~7 min | process + corpus | recurring (`#91`) |
| 3 | **The sibling register edit is in flight on the same file.** PR #93 (`agent/task-acme-app-91`) is OPEN and rewrites the `SL-002` row of the *same* `knowledge/slices.md` — the line immediately above this one. GitHub computes mergeability against `main`, so both PRs read MERGEABLE today, but whichever merges second lands a hunk within three lines of the other's and may conflict. Nothing in the command warns that a register edit has a live sibling; the coordination is left to the fleet's Rework-Queue route | ~6 min | process | new |
| 4 | The canonical register the `slice:edit` body describes (row fragments under `knowledge/slices/rows/SL-NNN.json`, a generated table, `fleet.py digest`, the `bars` gate) **does not exist in this repo**: `knowledge/slices.md` is hand-maintained markdown with no `knowledge/slices/` directory. The command's Step 5 instructions describe a file shape the run must ignore | ~2 min | corpus | recurring (`#91`) |

## Failures encountered (real feature bug vs process artifact)
- None. The suite was green before the edit (10 passed) and the change cannot move it — the diff
  is one markdown cell plus this retro. No hypothesis was falsified.
- One process artifact worth naming: the issue's own step (`/fleet:slice:edit SL-003`) is
  documented as human-invoked only (`needs: a decision`), yet the issue is dispatched to
  `task:implement` as a daemon-run task. The reconciliation is real — the decision is recorded *on
  the issue* by a human, so the run executes an answer rather than minting one — but neither
  command says so (same finding as `#91`, friction #3 there).

## Root-cause synthesis (what was *actually* the problem)
- Nothing was broken. PG-01's separation cut carried `—` in `Verified by`, so the derivation had
  no proof to read and the cut could never read done. The fix is to name the proof the human
  chose: an automated test that one customer can never read another customer's tasks — two
  customers' task lists in the app, neither list nor export containing the other's, and a direct
  read of the other customer's task refused.
- The genuinely open question is again the one the corpus cannot answer locally: **what syntactic
  form does a slice proof take in this register?** The canonical answer is "a PRD number or
  `drill:<stem>`", but this corpus has no drills home and only one PRD, already spoken for by the
  program. That is a corpus gap (no `knowledge/drills/`, no filled slice-proof precedent), not a
  defect in this change, and it is what the next register-edit run will hit again — `#91` and
  `#92` are the first two records of it.
- Deliberately *not* done: the test itself is not written. The capability it proves (a customer
  identity the app does not have — `app/main.py` has no owner concept at all) is SL-003's own
  unshipped work, and the issue scopes the run to the register cell ("Nothing else in the register
  changes"). "The cut reads done when that test ships" is the cut's completion condition, not this
  task's deliverable.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `neuter_check.py`'s docstring should state plainly that a change with no executable behaviour — docs, prose, a register cell — is satisfied by the `scopes` half alone, so these runs stop treating an empty `tests` list as a gate gap | doc | S | friction #1 | no — filed in `#55`, `#65`, `#76` and `#91`, still unaddressed |
| `slice:edit` should say, in its `Verified by` section, what to do when the human's decision names a proof that has no legal form yet (a test that ships, on a corpus with no `knowledge/drills/`): carry it in prose and say so, or park | doc | S | friction #2 | no — filed in `#91`, still unaddressed |
| The register-edit commands should name the live-sibling hazard: two `task:implement` runs editing different rows of the same hand-maintained register (`knowledge/slices.md`) produce hunks within three lines of each other, and the second to merge may conflict. A note to check `gh pr list --search <register file>` before editing would make the coordination explicit | doc | S | friction #3 | no |
| `slice:edit`'s Step 5 should describe both register shapes (row fragments + generated table, and hand-maintained markdown) and say which one to detect, rather than only the canonical one | doc | M | friction #4 | no — filed in `#91`, still unaddressed |

## Recurring across PRDs (flag loudly)
- Friction #1 is now on its **fifth** retro (`#55`, `#65`, `#76`, `#91`, `#92`) and is still
  unaddressed. Promote it — one sentence in `neuter_check.py`'s docstring retires the whole family.
- Frictions #2 and #4 are now on their **second** retro each (`#91` filed both): the corpus has no
  legal form for a slice proof that is neither a PRD nor a drill, and no `knowledge/drills/` home.
  They will recur on every `slice:edit` / `program:prove` / `slice:create` run until the command
  detects the shape or the corpus grows the canonical one.
- Friction #3 is new and is a *coordination* gap rather than a documentation one: the fleet's
  Rework-Queue route handles the conflict once it happens, but the run has no cheap way to see the
  sibling in flight.

---
type: flow-retro
owner: run:fe167abf-d038-45a6-b405-dce1923b656f
---

# Flow Retrospective — task zetify-pilot/acme-app#91 (Name SL-002's proof — the export's own end-to-end run)

> Auto-written by the task-implement flow's final step. Records how the RUN went, not the change.
> **Suggestions here are NOT applied** — review periodically and promote good ones by hand.

## Run metrics (rough)
- Command / outcome: task:implement (autonomous) / checks-pending (PR open, checks dispatched)
- Fix attempts: 1 (one register cell; no failed hypotheses)
- Red→green round trips: 0 tests — a register cell is not executable behaviour, so the ledger is
  scopes-only (friction #1, now the fourth retro in this family)
- Gate runs: `neuter_check.py` scopes ledger once — 2/2 covered, exit 0; `pytest` once (10 passed,
  before the edit; markdown cannot move it) and `python3 -m compileall -q app tests` once
- Sub-agent dispatches: 0 (a single markdown cell, fully mechanical — applied directly)
- Rough wall-clock vs expectation: ~25 min (expected <1h) — most of it was deciding what the
  `Verified by` cell may legally contain, not editing it

## What went smoothly
- The issue is unusually complete for a register edit: it quotes the recorded decision
  (2026-10-14, steffen@zetify.ai) verbatim, names the exact cell, names the sibling work it is
  *not* (PRD 0001, PG-01's composed proof), and says outright not to re-open the question — so
  Step 2's cause ledger is six quoted clauses and triage was immediate (task, not bug/feature).
- The change is one cell on `knowledge/slices.md:12` and the diff proves it: `git diff` is a
  single line, and a column-count read of the table confirms all nine columns survive
  (`| ID | Name | Kind | Program | Done when | Verified by | Depends on | Components | Disposition |`).
- The "nothing else in the register changes" clause is checkable against the tree rather than
  asserted: `SL-002`'s `Done when`, `Depends on` and `Disposition` are byte-identical to
  `origin/main`, and `knowledge/programs/PG-01.md:108`'s claim that "neither slice's
  `Verified by` names it" is *still* true after the edit (the cell names the run, never `0001`).
- `SL-002` is a **live** slice (its member PRD 0001 is `planned`), so no all-terminal proof gate
  and no `proof_waiver` fork arose — the write is the ordinary "name the proof" act.
- The scopes half of `neuter_check.py` is a real denominator check here and went 2/2: one
  anchored pattern for the register row (`^\| SL-002 \|`, exactly 1 site, covered by the diff) and
  one for the new claim text (exactly 1 site in `knowledge/`, covered).

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category | New or recurring? |
| - | ------------- | ---------- | -------- | ----------------- |
| 1 | A register cell has no executable behaviour, so `neuter_check.py`'s `tests` half is empty and only `scopes` does work — the same shape retros `#55`, `#65` and `#76` recorded for docs-only changes. The gate prose ("run the shared neuter check … for every kind of work") still does not say the scopes half alone satisfies a non-executable change | ~5 min | process | **recurring** (`#55`, `#65`, `#76`) |
| 2 | **What a slice's `Verified by` cell may legally contain is undecidable on this box.** `slice:edit` requires every entry to resolve to a real PRD number or `drill:<stem>` over a real `knowledge/drills/<stem>.md` with a `verdict:`; this corpus has one PRD (0001 — the program's own proof, which the issue forbids by name) and **no `knowledge/drills/` directory at all**. The decision names a *run that ships*, not a drill to be recorded, so neither legal form fits and the cell carries the run in prose. Nothing on this box can confirm the choice: `fleet_knowledge` is not importable (`fleet.py` refuses), `make` is not installed, and `make validate-knowledge` is unconfigured in this repo anyway | ~10 min | process + corpus | new |
| 3 | The `slice:edit` command is documented as **human-invoked only, headless writes nothing** (`needs: a decision`), yet this issue instructs exactly that command and is dispatched to `task:implement` as a daemon-run task. The reconciliation is real (the decision is recorded *on the issue*, so the run is executing a human's answer, not minting one) but neither command says so — a reader has to derive it from Rule J's carve-outs | ~4 min | process | new |
| 4 | The canonical register the `slice:edit` body describes (row fragments under `knowledge/slices/rows/SL-NNN.json`, a generated table, `fleet.py digest`, the `bars` gate) **does not exist in this repo**: `knowledge/slices.md` is hand-maintained markdown with no `knowledge/slices/` directory. The command's Step 5 instructions therefore describe a file shape the run must ignore | ~3 min | corpus | new |

## Failures encountered (real feature bug vs process artifact)
- None. The suite was green before the edit (10 passed) and the change cannot move it — the diff
  is one markdown cell plus this retro. No hypothesis was falsified.
- One process artifact worth naming: the first reading of the `Verified by` contract looked like a
  hard stop (no resolvable entry exists). It is not a stop — the human's decision is recorded on
  the issue and the issue forbids re-asking — but the contract gives no legal *form* for a
  named-but-not-yet-shipped run on a hand-maintained register, which is friction #2.

## Root-cause synthesis (what was *actually* the problem)
- Nothing was broken. PG-01's export cut carried `—` in `Verified by`, so the derivation had no
  proof to read and the cut could never read done. The fix is to name the proof the human chose:
  the export's own end-to-end run — one person opening the export's address, one row per task
  with a comma and a double quote intact, an empty list yielding a header-only file.
- The genuinely open question is the one the corpus cannot answer locally: **what syntactic form
  does a slice proof take in this register?** The canonical answer is "a PRD number or
  `drill:<stem>`", but this corpus has no drills home and only one PRD, already spoken for by the
  program. That is a corpus gap (no `knowledge/drills/`, no filled slice-proof precedent), not a
  defect in this change, and it is what the next register-edit run will hit again.

## Suggestions (NOT applied — for later review)
| Suggestion | Lever | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | ----- | ------ | --------------------- | -------------------------------- |
| `neuter_check.py`'s docstring should state plainly that a change with no executable behaviour — docs, prose, a register cell — is satisfied by the `scopes` half alone, so these runs stop treating an empty `tests` list as a gate gap | doc | S | friction #1 | no — filed in `#55`, `#65` and `#76`, still unaddressed |
| `slice:edit` should say, in its `Verified by` section, what to do when the human's decision names a proof that has no legal form yet (a run that ships, on a corpus with no `knowledge/drills/`): carry it in prose and say so, or park. Today the section reads as if only PRD/drill are possible | doc | S | friction #2 | no |
| `slice:edit` should name the reconciliation with the execute commands — when a recorded decision on a tracker issue instructs this command, a `task:implement` run may execute it, because the authorization is the human's recorded answer and not the run's own | doc | S | friction #3 | partially — Rule J's carve-outs imply it; no command states it |
| `slice:edit`'s Step 5 should describe both register shapes (row fragments + generated table, and hand-maintained markdown) and say which one to detect, rather than only the canonical one | doc | M | friction #4 | no |

## Recurring across PRDs (flag loudly)
- Friction #1 is now on its **fourth** retro (`#55`, `#65`, `#76`, `#91`) and is still
  unaddressed. Promote it — one sentence in `neuter_check.py`'s docstring retires the whole
  family.
- Friction #4 is the first record of the canonical-vs-actual register divergence in this corpus;
  it will recur on every `slice:edit` / `program:prove` / `slice:create` run until the command
  detects the shape or the corpus grows the canonical one.

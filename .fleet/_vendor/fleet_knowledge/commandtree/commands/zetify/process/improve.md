You are closing Zetify's **process-improvement loop**: turn recurring retro friction into
concrete edits to the SOP or `/zetify:*` command that caused it. This is read-mostly
judgment work — you apply small additive fixes directly and **propose** anything that
changes a standing rule.

> **SOP:** This command is the automated subset of
> [`../../../process/improve-the-process.md`](../../../process/improve-the-process.md).

---

<!-- include: process/writing.md -->

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `two-tier` is the split this command exists for — additive fixes are APPLIED, rule-changing ones are only ever PROPOSED, and when it is unclear which a suggestion is, it is proposed. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "process-improve",
  "intent": "Turn recurring retro friction into concrete edits to the SOP or command behind it — applying the additive fixes, proposing anything that changes a standing rule.",
  "sop": "improve-the-process",
  "needs": "nothing",
  "may merge": true,
  "loads": ["process-improvement", "process-envelope"],
  "requires": [
    "process-spine", "process-envelope", "git-workflow", "process-improvement",
    "retro-corpus"
  ],
  "optional": ["gate", "file-conventions", "languages"],
  "steps": [
    {"id": "harvest",     "name": "Harvest the retro corpus into a digest",        "kind": "io",       "actor": "coordinator",                 "body": "step-1-harvest"},
    {"id": "locate",      "name": "Locate and check the target — every bucket",    "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-2-locate-check-the-target"},
    {"id": "two-tier",    "name": "Apply the two-tier rule — additive applies, rule-changing proposes", "kind": "decision", "actor": "coordinator", "body": "step-3-apply-the-two-tier-rule"},
    {"id": "commit",      "name": "Commit the applied edits and the ledger rows",  "kind": "io",       "actor": "coordinator",                 "body": "step-4-commit-report"},
    {"id": "report",      "name": "Report the proposed-only changes for ratification", "kind": "io",   "actor": "coordinator",                 "body": "step-4-commit-report"}
  ]
}
```

---

## Context to load
- `../../../process/improve-the-process.md` — the procedure this automates.
- `../../../process/autonomous-drive.md` (§ Flow-retro) — where retros come from.
- The harvest digest (Step 1).

## Step 1 — Harvest
Run `python3 knowledge/scripts/harvest_retros.py --probe`. Below a per-suggestion table (each row has a
guessed target, its source retros, and a `Hash`) it prints two ranked aids the flat `×`
column can't give:
- a **Recurring** section — suggestions the author self-flagged (`3rd occurrence`, `keeps
  recurring`, `confirmed across N runs`) plus groups sharing a distinctive artifact token.
  **This, not the ×1 table, is the promote signal**: the `×` column only counts
  *character-identical* suggestions, so a theme recurring in different words is invisible there.
- a **Likely already built** section (from `--probe`) — surviving suggestions whose named
  artifact already exists in the tree. Treat every row as **"verify before acting"**.

**Incrementality comes from the ledger, not a date window.** The digest omits every occurrence
a prior run resolved in `knowledge/scripts/harvest_retros.py`'s own ledger, so a plain run already shows only
what's outstanding — you rarely need `--since` (use it only to *narrow* a backfill). On a
first / empty-ledger run, expect a large stale tail — old suggestions that normal PR work has
since fixed — and clear it in bulk in Step 2. Pass `--all` to also see resolved occurrences.

## Step 2 — Locate & check the target (every bucket)
Work the **Recurring** section first (highest promote signal), then the rest. For each
surviving suggestion **open its target** — a `knowledge/specs/*.md`, a
`.claude/commands/zetify/*.md`, an SOP in `knowledge/sops/`, or a tooling target — and discard
anything it already satisfies. **This gate applies to *every* Step-3 bucket — propose and
file-a-task included, not just the edits you apply** (filing or proposing an already-built
thing is still acting on it). Most "add a lint / check / doc for X" suggestions from older
retros are **already built**: before you propose or file one, confirm it doesn't exist — the
`--probe` section pre-flags many; also list this repo's static-analysis rules (its `gate`
slot names where they live), `git grep <artifact>`, and read the actual target. Never act on — or propose, or file — a
suggestion you haven't checked against its target.

## Step 3 — Apply the two-tier rule
For each surviving suggestion:
- **Clearly additive / low-risk** — a clarifying sentence, a new gotcha or checklist row, a
  documented threshold, a missing cross-reference → **apply it directly** to the target file.
  - **🛑 First ask where the target is authored.** A `/zetify:*` command, a
    `.claude/process/*` document, a register or a rubric is **generated** in a consuming
    repo — written there by `fleet commands sync` out of `fleet-knowledge`'s `commandtree/`.
    Editing one in place looks like an ordinary tracked change, passes review, and is
    **silently destroyed by the next sync**; where a drift check exists it reddens the build
    instead, which is the better of the two failures and still not the fix. Author the edit
    in **`ZetifyAI/fleet`** under
    `packages/fleet-knowledge/src/fleet_knowledge/commandtree/`, and let it arrive as a pin
    bump plus a sync. Everything else this command touches — `knowledge/`, `scripts/`, a
    repo's own docs — is edited where you found it, as normal.
- **Alters or removes a standing rule, a contract, or a command's behavior** → **propose
  only**: write the exact edit you would make plus the rationale; do not apply it.
- **Code / tooling** (a new policylint rule, a pre-commit check) → **first confirm it doesn't
  already exist** (Step 2 — the `--probe` hits, plus this repo's own analysis surface behind
  its `gate` slot); only if genuinely missing, either hand-write a small self-contained guard
  here or file `/zetify:task:create` linking the source retros.

For every suggestion you act on this run — applied directly, or discarded because the
target already satisfies it — **close the loop in the ledger** so the next harvest stops
re-surfacing it:
`python3 knowledge/scripts/harvest_retros.py --resolve <occurrence-id> <disposition>`
(hash from the Step 1 digest). Skip this for suggestions you only *proposed* or *filed as a
task* — those aren't resolved yet, so they should keep recurring until they land.

## Step 4 — Commit & report
- Commit the **applied** edits plus the **ledger rows** from Step 3, message `process: <what
  improved> — harvested from retros`. `main` has no direct-push path for the fleet identity
  (`docs/ci-branch-protection.md` §0), so this still ships via a throwaway branch
  (`agent/chore-process-improve-<date>`) + PR merged with `gh pr merge --auto --squash` (never
  `--delete-branch`, which `gh` refuses under a merge queue) — fast and unreviewed for process/doc changes, but not a bare push. A
  self-written lint/tooling guard from the Step 3 "Code / tooling" bucket is code-bearing
  regardless of this rule and always ships via its own normal branch + PR.
- Report the **proposed-only** changes + the **filed tasks** in one message for the user to
  ratify or wave through.

## Rules
- Read the target before editing — never apply a suggestion it already satisfies.
- **The target-check gates all three buckets** — apply, propose, *and* file-a-task. A
  "add a lint/check for X" from an old retro is usually already built; grep before proposing
  it (the `--probe` section exists for exactly this failure).
- Additive → apply; rule-changing → propose. When unsure which it is, propose.
- One concern per edit/commit; keep diffs small and quotable.
- **Never edit the `slot:retro-corpus` records** (the durable learning record) and never invent
  suggestions that aren't in the harvest digest.

#  Verify

**No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools*. There is no other tracker path — never fall back to a tracker script.

Post-implementation review: confirm every PRD acceptance criterion was implemented **and works in a real browser** (for UI PRDs). A PRD already `verified` or `shipped` short-circuits at **Step 0** — a bounded ship-only retry, or a reported no-op (except a `shipped` PRD whose tracker issue never passed through a review position, which is audited rather than no-op'd — see Step 0), never a second full audit.

**Mechanical testing (Go tests / lint / build) is NOT part of this command** — pre-commit handles that. This command is an evidence-based review of intent-vs-reality. For UI features, that evidence MUST include a live-browser pass — Vitest unit tests mock React Flow / Radix / Sheet & Dialog portals, so the unit suite can be fully green while the page crashes on load (see ``).

> See [`../../../process/implementation.md`](../../../process/implementation.md) for the shared coordinator discipline this command inherits — especially §5 (read results from deterministic files / trust exit codes, never `ls -t` a stale tee log) and §10 (socket-drop recovery). The browser batch needs `make dev` up; do not start a heavy DB/e2e run alongside it (§8).

> **Credentials never go on argv — any credential, of any kind, from any source.** argv is
> echoed into unrotated session and daemon logs and is world-readable via `ps aux` /
> `/proc/<pid>/cmdline` (, ). Pass secrets via the environment, never argv —
> the tracker key, the forge token, a database password, the dispatch token, a DSN
> password, a daemon token are **examples**, never an exhaustive list. A per-credential
> warning is not enough: a session that only saw a named key still inlined
> `PGPASSWORD` nine times (). The always-on rule in `CLAUDE.md` is the same one;
> this restates it because a verify turn is exactly where a local-dev password tends to appear.

---

> # 🛑 EVERY BROKEN CRITERION ROUTES TO `/fleet:bug:fix` — NON-NEGOTIABLE. KEY TO QUALITY.
>
> This command finds defects; it does not patch them. **Whenever verification surfaces a BUG — a page that crashes on load, a console error, an interaction that does nothing, a handler returning the wrong data, a flaky probe, ANY "broken" (present-but-wrong) behavior — the remediation MUST be `/fleet:bug:fix NNNN — <symptom>`, NOT an ad-hoc edit and NOT `/fleet:prd:implement`.**
>
> `/fleet:bug:fix` is the TDD discipline ([`../`](#)): reproduce the failure as a **failing test/probe (RED)**, fix the **root cause** (never the symptom), confirm the **same test turns GREEN**. That reproduce-first loop is the single biggest quality lever — it is what stops a "fix" from papering over the symptom and re-breaking later.
>
> Routing rule (Step 3 / Step 4): **missing** behavior (never implemented) → `/fleet:prd:implement NNNN`; **broken** behavior (present but wrong) → `/fleet:bug:fix NNNN — <symptom>`. A browser "rendered but didn't work when clicked" or any crash/console error is a **defect**, so it goes to `/fleet:bug:fix` — always. When unsure whether a gap is missing-vs-broken, treat it as broken and route to `/fleet:bug:fix`.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. A FAIL verdict or an open gap stays an open todo with its residual noted. The prose Steps below are the authority; this spine indexes them.

```json
{
  "command": "prd-verify",
  "tier": "core",
  "intent": "Evidence-based audit that every PRD acceptance criterion works (browser-verified for UI); flips status to verified on all-PASS or on pass-with-follow-up (every open row non-critical). A PRD already `verified`/`shipped` short-circuits to a bounded ship-only retry or a reported no-op instead of re-auditing — except a `shipped` PRD whose tracker issue never passed through a review position, which is audited rather than no-op'd.",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "loads": ["process-implementation", "planning-model"],
  "requires": [
    "process-spine", "process-implementation", "gate", "git-workflow", "planning-model", "dev-environment", "tracker-identity", "process-interview"
  ],
  "optional": [
    "ui-contracts", "audit-profile", "entity-model", "decisions", "process-design-fidelity",
    "registers-triage-partition", "commitments", "feature-maps", "languages", "api-contract",
    "permissions", "feature-areas", "components", "file-conventions", "process-issue-shape", "docs"
  ],
  "steps": [
    {"id": "status-gate",      "name": "Status gate — implementing / verified / shipped", "kind": "decision", "actor": "coordinator", "consumes": ["prd"], "body": "step-0-status-gate"},
    {"id": "ship-retry",       "name": "Ship-only retry (bounded, status: verified)", "kind": "io", "actor": "coordinator", "produces": ["status", "linear-issue"], "body": "status-verified-ship-only-retry-bounded"},
    {"id": "substrate-ready",  "name": "Substrate readiness — down is a blocker, never a verdict", "kind": "gate", "actor": "coordinator", "gate": "hard", "produces": ["linear-issue"], "body": "step-0-7-substrate-readiness"},
    {"id": "reentry-delta",    "name": "Re-entry after a FAIL — re-prove the open lines, smoke the rest", "kind": "decision", "actor": "coordinator", "consumes": ["prd", "acceptance-criteria"], "body": "step-0-8-re-entry-after-a-fail"},
    {"id": "carve-criteria",   "name": "Carve up the work",              "kind": "author", "actor": "coordinator", "consumes": ["prd", "design", "acceptance-criteria"], "body": "carve-up-the-work"},
    {"id": "spawn-reviewers",  "name": "Spawn reviewers in parallel",    "kind": "fanout", "actor": "subagent", "model": "sonnet", "produces": ["screenshots"], "body": "spawn-reviewers-in-parallel"},
    {"id": "refute-passes",    "name": "Refute the PASSes",              "kind": "fanout", "actor": "subagent", "model": "sonnet", "body": "refute-the-passes"},
    {"id": "reachability",     "name": "Reachability — name the surface, drive it", "kind": "gate", "actor": "coordinator", "gate": "hard", "critique": "independent-verification", "body": "reachability-name-the-surface-drive-it"},
    {"id": "synthesize",       "name": "Synthesize",                     "kind": "author", "actor": "coordinator", "body": "synthesize"},
    {"id": "requirement-cover","name": "Claimed-requirement coverage",   "kind": "decision", "actor": "coordinator", "consumes": ["requirement-register", "acceptance-criteria"], "body": "claimed-requirement-coverage"},
    {"id": "verdict",          "name": "Verdict (incl. design-fidelity FAIL)", "kind": "gate", "actor": "coordinator", "gate": "hard", "critique": "design-fidelity-bar", "body": "verdict"},
    {"id": "ship-gate",        "name": "Ship-gate — may this run bless the merge?", "kind": "gate", "actor": "coordinator", "gate": "hard", "body": "ship-gate-may-this-run-bless-the-merge"},
    {"id": "flip-status",      "name": "Flip status (success only)",     "kind": "io", "actor": "coordinator", "produces": ["verified-status", "linear-issue"], "body": "flip-status-on-success-only"},
    {"id": "ship",             "name": "Ship (all-PASS or pass-with-follow-up)", "kind": "io", "actor": "coordinator", "produces": ["status"], "body": "ship-all-pass-or-pass-with-follow-up"},
    {"id": "audit-followups",  "name": "File post-ship audit follow-ups", "kind": "io", "actor": "coordinator", "produces": ["linear-issue"], "body": "file-post-ship-audit-follow-up"}
  ]
}
```

---

## CRITICAL RULES

1. **You are the coordinator — and you stay the coordinator even when sub-agents drop.** Don't investigate criteria yourself — spawn sub-agents and synthesize the verdict. Coordinator-side actions that are explicitly allowed: reading files (PRD, plans, design), small read-only Bash like `grep`/`git diff`/`curl localhost:5173`, the Step 5 edits to `prd.md` (plus re-running `python3 knowledge/scripts/gen_roadmap.py`, which regenerates `roadmap.md` — never hand-edit it) once verification passes, and Step 0's ship-only-retry bookkeeping edit to `prd.md`'s `status_history` (plus the tracker label/comment writes needed to park an exhausted retry). If a sub-agent keeps hitting socket timeouts on a single task, SPLIT the prompt into 2–3 smaller dispatches — do NOT take over with Edit/Write yourself. **A session-level instruction not to spawn agents does not convert this command into a solo one.** Verification's entire value is that the reviewer did not author the work; a coordinator who reviews the ACs itself has produced a self-verification wearing a verify command's name — the exact thing this split was measured into existence to stop (**82% of PRDs were self-verified** before it; **~1 in 2** merged fixes did not fully address the issue they closed). If you cannot spawn, return `verify-failed` with the reason and merge nothing ([`spine.md`](../../../process/spine.md) → *"`actor: subagent` means a real sub-agent"*).
2. **Parallelize.** Independent batches review concurrently (single message, multiple Agent tool calls).
3. **Code-reading is NOT enough for UI.** The **Browser batch is mandatory whenever the PRD touched the UI at all** — any customer-visible surface file (`slot:ui-contracts` names where they live) was modified, any AC describes user-visible behavior, `frontend-plan.md` exists, `labels: type:ui` is on the PRD, or `ux-design.md` exists. A copy tweak, a new icon, a single React component edit all count. A UI AC passed on `file:line` evidence alone is automatically FAIL.
4. **Evidence-based.** Each PASS must cite either a `file:line` (for backend/contract criteria) **or** a Playwright probe step + screenshot path (for UI criteria). Each FAIL must say specifically what's missing.
5. **Don't write production code or fix bugs — route them (see the banner above).** This is a review command. If something fails, the user runs the routed remediation (Step 3): `/fleet:prd:implement` for a **missing** criterion, **`/fleet:bug:fix` for a *broken* one — every defect goes through the reproduce-first TDD discipline, never an ad-hoc patch.** Writing a new Playwright probe to *test* an AC is in scope; changing the feature code is not.
6. **Sub-agent task budget: <20 min wall time per agent.** A review sub-agent reads code and reports — it should never approach the 1–2 hr socket-drop window. If a batch would need more time (very large surface area, many ACs), split it into 2–3 narrower batches in parallel. The cross-check sub-agent in Step 3 should be even tighter (<5 min, doubtful items only).

---

## Input

Parse `$ARGUMENTS` — a PRD number (e.g. `0003` or `31`).

Read `knowledge/prds/NNNN-<slug>/prd.md` frontmatter `status:` first, then run **Step 0**
below — it decides whether this run does the full audit, a bounded ship-only retry, a
reported no-op, or an audit of a `shipped` PRD that never passed through a review position.
Only the full-audit path (`status: implementing`, or that
shipped-without-a-review-position case) needs the rest:

1. `knowledge/prds/NNNN-<slug>/prd.md` — acceptance criteria, goals, success measures
2. `knowledge/prds/NNNN-<slug>/design.md` (if exists)
3. `knowledge/prds/NNNN-<slug>/*-plan.md` (if exists) — for the file paths the implementation touched
4. `knowledge/prds/NNNN-<slug>/ux-design.md` (if exists)

**A PRD may name the lane it is built in (`lane:`), and then this audit reviews THAT lane's
repository.** A PRD's frontmatter may carry `lane: <name>` () naming a lane the fleet
registers. The `prd-projection` pass labels the PRD's issue `repo:<lane>` INSTEAD OF the corpus
default, so the daemon dispatches this run into that lane's checkout and **the code and the PR
live there** — the carrier PR and the merge are the lane's, and the PRD's `status:` flip must
land in the **owning corpus** (the repo that owns the PRD's docs), not the lane's. The PRD,
design and plan files stay in that owning corpus; when `knowledge/prds/NNNN-<slug>/` is not in
the checkout you are running in, read them from the corpus the issue's own description points
into. Resolve the lane's repository from the issue's `repo:*` label
(`knowledge/scripts/_repo.py`'s `lane_slug`), never from the current directory's name.

---

## Step 0: Status gate

The review position is overloaded: `/fleet:prd:implement` (Phase D3) hands a PRD's the tracker
issue to **`Verify Queue`**, and the daemon dispatches `/fleet:prd:verify` at *any* PRD
sitting there (claiming it as `Verifying`). The frontmatter `status:` is what
actually distinguishes "awaiting its first audit" from "already certified, ship in
flight or failed" — read it **before doing anything else**: before carving up
criteria, before spawning a single reviewer.

- **`status: implementing`** → not yet audited. Continue to **Step 0.5** (open a
  carrier PR if none exists), then Step 1 — the full path below.
- **`status: verified`** → already audited and durably stamped. Do not re-run Steps
  1–4 or the Step 5 status flip. Go to **ship-only retry**, below.
- **`status: shipped`** → already done. **Usually no-op** — but first check whether the
  issue ever passed through a review position (`Verify Queue`/`Verifying`, or the retired
  spellings `Review` and `In Review`); if it never did, audit rather than no-op (see <!-- retired-state-name -->
  below).
- Anything else (`stub`, `prd-drafted`, `designed`, `planned`) → warn and confirm
  before proceeding, exactly as today; verify is meant to follow
  `/fleet:prd:implement`. On an autonomous dispatch there is no one to confirm with —
  for `planned`, proceed with the audit, but know the terminal is governed by the
  Step 4.5 ship-gate: a carrier PR that has already merged, whose merge did not carry
  the PRD's `status: shipped`, ends this run in the `Blocked · action` park (design
  B10) — never a "verified & merged" close ().

### Step 0.5: Ensure a carrier PR exists ()

**Before** carving criteria or spawning reviewers, resolve the open PR for this PRD's
tracker issue (`gh pr list --search "<KEY>" --state open --json number,headRefName,url`).

**A coupled change has TWO review targets, shipped in order ().** When the change is
authored in the fleet `commandtree/`, the carrier PR and the consuming repo's `fleet/` pin
bump are separate targets. Resolve them together —
`python3 knowledge/scripts/pr_resolve_review_target.py resolve <KEY> --repo <lane> --repo <lane>`
one `--repo` per `repo:*` lane the issue names. While `state` is **`bound`**, a linked PR in
another lane is still unmerged and neither half may be shipped as whole. Ship the **fleet**
half first — its PR lands on the lane whose `main` the pin must point at — then re-pin this
repo's `fleet/` to the resulting fleet-`main` squash commit and run `fleet commands sync
--repo .` in the same commit, and only then ship the pin half. A pin at a PR head is never on
fleet `main` (squash-only), so an unre-pinned or head-pinned `fleet/` is an OPEN criterion,
never a verified carrier.

- **An open PR exists** → `git fetch origin && git checkout <headRefName>`, then read its
  mergeability before anything else: `gh pr view <pr> --json mergeable,mergeStateStatus`.
  Clean → continue. Code-bearing PRDs land here via `prd:implement`'s Phase D handoff.

  **`CONFLICTING` / `DIRTY` → the one reconcile that is not authoring, then the conflict
  route.** A PR that waited here conflicts with `main` *by construction* on the generated
  ledgers nearly every knowledge PR touches — files whose content is regenerated by a
  registered merge driver, never merged by hand. GitHub cannot run a driver, so it reports a
  conflict whose local merge was never in doubt. Measured  over the 43 PRDs that
  passed this gate →09-08: 14 of ~20 conflict events were
  `` alone, and each one cost an implement dispatch, a fresh
  verify, a rework return against the PRD's budget — and, at the re-entry cap, a
  `Blocked · decision` park (four of them). So, **first**:

  ```bash
  python3 knowledge/scripts/regen_reconcile.py --base origin/main
  ```

  It merges `origin/main` into the branch only when the branch's **own diff is proven
  byte-identical** before and after — every `+`/`-` line over every non-derived path; the
  derived ledgers are regenerated by their drivers, a submodule pointer is taken forward
  only when one side descends from the other — and aborts with the tree untouched otherwise.
  - **Exit 0** → `python3 knowledge/scripts/gh_automerge_disarm.py <pr>` (the open-time arm
    must never survive a head move, ), `git push origin HEAD` (a fast-forward —
    **never** `--force`), let CI run on the new head, and continue the audit **at that
    head**; quote the script's output in the report's `Graded at:` line.
  - **Exit 1** (a real conflict, or the own-diff would change) → the conflict-as-work route
    the mission specifies: post the brief stamped `<!-- linear-agent:conflict-rework -->`
    **with the script's output quoted** (it names the exact paths), move the issue to
    `Rework Queue`, write the done-sentinel `verify-failed`, stop. That hand-back is the
    **mechanical rebase lane** () — a cheap short seat that follows the brief, **not**
    a full `/fleet:prd:implement` re-entry on the primary model. A conflict-only return is
    **not** a refuted criterion: it does not count toward the re-entry cap and it never parks
    the issue on its own. Count the conflict briefs already on the issue: at the conflict
    hand-back cap the brief turns **merge-scoped** — `git merge origin/main` on the branch
    (never a rebase: it must not rewrite the certified diff), resolve, regenerate the derived
    files, push, hand back to `Verify Queue`, and **do NOT touch product code** — and still
    dispatches the mechanical lane. Park `Blocked · decision` only when that lane reports the
    merge needs a product or scope judgement, or when the fix's own lines were rewritten or
    deleted on `main` so no merge can carry them forward. When a refusal names a generated
    path, say the file is generated but has no merge driver — never "hand-authored". On the
    next verify after a mechanical rebase: if only derived / unclaimed paths moved, carry the
    prior closed criteria forward on a smoke check; if any claimed file moved, re-grade the
    full ledger.
  - **Exit 2** (could not run — a dirty tree, a driver `.gitattributes` names that this
    checkout has not registered) → if it names an unregistered driver, register the
    repository's merge drivers the way its commit hooks do and retry **once**; otherwise
    treat as exit 1 with the output quoted. If the script says the path is a **generated file
    with no merge driver**, quote that; do not paraphrase it as hand-authored.

  That script is the whole of the verifier's licence to touch the branch: **no rebase, no
  hand resolution, no fix-up commit** — those remain authoring, and the party that authors
  never certifies.
- **No open PR, and the PRD's work already merged — in this repository without the
  `shipped` flip, or in ANOTHER repository** → this is **not** the proof-only shape, and a
  carrier PR opened here cannot carry the stamp: the daemon mints no dispatch token for a PRD
  whose linked PRs merged or live in another lane, and the dispatch-token check accepts the
  0-bound sentinel only for a PRD whose own design declares it ships no product code. The
  terminal is Step 4.5's, fixed: park **`Blocked · action`** with `needs-action`, naming the
  exact flip — `knowledge/prds/<NNNN>-<slug>/prd.md`: `status: <what main reads> → shipped`.
  **Never close the issue `Done` from here** (: PRD 0692's issue closed while `main`
  read `planned`, and its dependants were refused for three days). The fleet re-reads the
  frontmatter after every PRD success and parks the issue itself when it does not read
  `shipped`.
- **No open PR** otherwise → this is the **proof-only / walk-only** shape (no product code by
  design — e.g. a composed-proof PRD whose entire deliverable is the walk). Open the
  binding surface **now**, as this session's first act:

  1. Branch `agent/prd-<NNNN>-<key>` from `origin/main` (canonical form —
     `tracking-and-execution.md` → "Git workflow").
  2. If the PRD's design/plan names a program `## Walk log` (or equivalent D6-style
     record), append the walk-log scaffolding row now so the PR is non-empty and the
     composed-proof convention is honoured. Otherwise an empty commit that only
     records `chore(NNNN, <KEY>): carrier PR for proof-only verify` is enough — the
     `verified` stamp in Step 5 will be the real payload.
  3. Push and open the PR (`/fleet:push` open-PR-and-stop; `Refs <KEY>`; push mode arms
     auto-merge at open () — the arm stands through the verify window but is
     **not** what makes the stamp safe: Step "Ship (all-PASS or pass-with-follow-up)" → push ship mode runs
     `python3 knowledge/scripts/gh_automerge_disarm.py` before its stamp push and re-arms only after the plan gate
     among `slot:git-workflow` reports green on the stamped head ( —
     the forge's auto-merge does not reliably re-validate a changed check state, so the arm
     must never survive a head move; `slot:git-workflow` says how a check is
     re-dispatched here). Drive CI green.
  4. Continue the audit on that branch. Step 5's `verified` stamp + `Dispatch-Token:`
     trailer ride this same PR.

**Why this is first, not last.** The daemon mints each verify session a
`Dispatch-Token` over `v2:{issue}:{prd}:{pr}`. A proof-only PRD has no implement PR, so
at dispatch the daemon mints the  sentinel `pr_number=0`; this session's
carrier PR is what the stamp merges through, and
the dispatch-token check accepts the 0-bound token only when the
PR is knowledge-only. Opening the PR up front means the binding surface exists before
the token is embedded — and a code-bearing PRD that somehow reached verify with no PR
still gets one before any criterion is graded.

### `status: verified` — ship-only retry (bounded)

**Why re-running the audit here would prove nothing.** The acceptance-criteria
audit's verdict is already durable in the frontmatter the moment `status: verified`
is stamped — the code/browser batches, the refuters, the reachability check, and the
design-fidelity gate all had to pass to earn it (Step 4). A dispatch that lands here
is, by construction, recovering from a **ship-time** failure (red CI, a merge race, a
transient GitHub error) — not a re-opened question about whether the feature is
correct. Re-running the full audit would re-spend an entire browser batch to
re-confirm something nothing has cast doubt on. **Do not "restore" the full audit out
of caution here — the skip is deliberate, this paragraph is why, and it is not an
oversight to be undone.** (If the PRD's acceptance criteria genuinely change, that is
a new PRD revision at `status: implementing`, never suspicion cast on an existing
`verified` stamp.)

1. **Locate the open PR.** Resolve `<KEY>` from the PRD's tracker issue (titled
   `[NNNN] …`). Find its PR: `gh pr list --search "<KEY>" --state open --json
   number,headRefName,url`. If none is open, something is inconsistent (a `verified`
   PRD with no open PR) — fall through to the "anything else" warn path above rather
   than inventing a branch. Otherwise `git fetch origin && git checkout
   <headRefName>`.
2. **Count attempts already made, durably, from `status_history` on that branch** —
   not from `main`, since a ship that fails to merge never lands there, and its
   bookkeeping only ever lives on the still-open branch. Count the existing
   `{ state: verified, at: …, by: verify }` rows. Use exactly that three-field
   shape, never a fourth key — `make validate-knowledge`'s status-history rule parses
   exactly `{ state, at, by }` (`slot:planning-model` fixes the shape), and an
   extra key makes the whole row silently fail to parse (and so silently fail to count) instead of
   erroring. The first row is the original audit-pass stamp; each ship-only retry
   appends one more identical row. **3 total rows is the bound** — the same cap
   `autonomous-drive.md` Rule E and `push.md` §5.7 use elsewhere for a bounded retry
   loop.
   - **Already at 3** → the bound is exhausted. Do not attempt a 4th ship. Skip to
     "Bound exhausted", below, without touching `status_history`.
   - **Under 3** → append one more `{ state: verified, at: <>, by: verify }`
     row and commit it (`chore(NNNN, <KEY>): ship-retry attempt <N>`, where `<N>` is
     the new row count) — a coordinator-side edit, same class as the Step 5 flip
     (CRITICAL RULE 1). Do not push it yourself; handing the commit to
     `/fleet:push ship` next lets it fetch/rebase/push in one place.
3. **Ship.** Invoke the "Ship (all-PASS or pass-with-follow-up)" section below exactly as an all-PASS
   run would: `/fleet:push ship <sha> <KEY>` with `<sha>` = the commit from step 2.
   Report the outcome:
   - **Merge SHA returned** → done. State plainly in the output: *"Ship-only retry
     (attempt `<N>`) — no sub-agents spawned, no browser batch run."* `main` now
     carries `status: shipped`; nothing else to do.
   - **`NOT MERGED — <reason>`, and `<N> < 3`** → report the failure and the attempt
     count, and stop. The PR stays open/green, the issue stays in `Verifying` — the
     daemon's next dispatch re-enters this gate and re-counts, which is the whole
     backoff: spacing comes from the daemon's own dispatch cadence, not a sleep this
     command invents.
   - **`NOT MERGED — <reason>`, and `<N> == 3`** → the bound is now exhausted *this
     run*. Continue to "Bound exhausted", below.

**Bound exhausted.** Park the issue. Whether to force-merge, re-scope the failing
check, or kill the PRD is a judgement call, not an action a human can just execute —
so end with **`needs-decision`**, never a bare action park
(), plus a `comment` naming the blocker plainly — the PR URL, the specific
failing CI check(s) by name (`gh pr checks <pr>`), and that 3 ship-only retries have
now failed to merge. **Leave `status: verified` untouched** — the audit's certification
stands regardless of ship mechanics; only the *ship*, not the *verification*, is stuck.
**Do not skip silently if Fleet is unreachable**: say so loudly in the final report.

### `status: shipped` — no-op, unless the issue never passed through a review position

Report the PRD as already shipped and stop. Don't touch `status_history`, don't run
`/fleet:push`, don't spawn anything. A re-dispatch here almost always means the tracker's
GitHub integration bounced a Done issue back to In Review
( / ) — the tracker-sync
quirk, not a signal to re-verify or re-ship already-merged work.

**But that no-op is only safe when the PRD was genuinely audited on the way out —
check first.** The review position — **`Verify Queue`**/**`Verifying`** today, the retired
**`Review`** on issues that ran between the  lifecycle migration and the <!-- retired-state-name -->
 state rename, the retired **`In Review`** on anything older — is the one
whose only function is to dispatch `/fleet:prd:verify` (see Step 0's opening). A PRD that
reached `shipped` while its tracker issue **never passed through any of them** could have
been stamped self-certified
— defeating the same-commit check  added by splitting the `verified`/`shipped`
stamps across two commits in one continuous session — and the no-op above would then
*permanently* seal it unauditable (the exact second-order effect  named). So
before no-op'ing, resolve the PRD's tracker issue and check its state history:

1. **Resolve `<KEY>`** from the PRD's tracker issue (titled `[NNNN] …`), exactly as in
   the `status: verified` path above.
2. **Query whether the issue ever entered a review position.** Call `get_issue` with
   `include: history` (capped at 20). Test whether any transition's target was a review
   position — **`Verify Queue`**, **`Verifying`**, or either retired spelling **`Review`**,
   **`In Review`**. The shape that distinguishes the two cases:
   - **A genuine  bounce** has a review position in its history (it was verified,
     so the issue sat there before merging) — that history node is the proof an
     independent verify session ran.
   - **A self-certified `shipped` PRD** has **none** of them anywhere in its history
     (e.g. /PRD 0514's history is only `Spec ↔ In Progress`, then
     `In Progress → Done` — never a review position).
3. **Branch on what you find:**
   - **A review position appears in the history** → the PRD really was independently
     audited. **No-op**, exactly as today: report the PRD as already shipped and stop.
   - **None ever appears within the 20 returned** → plausibly self-certified. **Do not
     no-op.** Treat it as worth a real audit: proceed to **Step 1 and run the full audit**
     against the `shipped` PRD exactly as if it were `status: implementing` (reuse Steps
     1–4 and the verdict). State plainly in the report why: the PRD reached `shipped`
     with no review position on record, so its `verified` stamp cannot be trusted to a
     real session. A PRD whose audit then fails is a defect already merged — route per
     Step 3/Step 4 and note in the report that the fix must land as a follow-up since
     `shipped` is already on `main`. If the audit passes, it is the re-audit that was
     refused before — report the PASS.
   - **History unreachable** (`get_issue` fails) → **fail safe toward the audit, not the
     no-op.** Without history you cannot prove the PRD was ever in a review position.
     Run the full audit (Step 1+) and say in the report that the no-op was skipped
     because the issue's history could not be read.

---

## Step 0.7: Substrate readiness — down is a blocker, never a verdict

A criterion can only be graded on a substrate that is up. Before a single reviewer is
spawned, the coordinator establishes that every substrate the criteria need is actually
serving — because a row graded FAIL on a stack that was still seeding is not a finding, it
is an outage wearing a verdict, and Step 4 turns it into a **Rework round whose implement
session has nothing to change**. Measured across the FAIL verdicts of the eight most-reworked
PRDs of →09-11: at least three of 0571's nine rounds graded rows FAIL on "dev stack
still seeding at verdict close", "PG/API down" and "apprund 422 app_not_ready — adoption claim
cold"; each cost an implement dispatch, a fresh verify, and a rework return against the PRD's
budget, for code that had not moved.

1. **Enumerate the substrates** from the criteria and the plans — not from habit. The usual
   set: the dev stack (API and web readiness routes on *this checkout's* ports —
   `slot:dev-environment` says how to read them, never a default); the seeded state the
   criteria assume (the dev login, the org / collection / app a criterion names by value); any
   daemon target a criterion drives (`connectord`, `agentd`, the app runtime and the install
   it must report ready); a database lane a criterion names (a nondefault-schema lane is a
   substrate of its own); a local cluster for `kind`-tiered criteria.
2. **Probe each one from the coordinator**, read-only and cheap: the readiness route answers,
   the seed is present, the daemon reports healthy, the lane's prerequisite service is up.
   Record every probe and its output — they go in the report either way.
3. **Not ready → bring it up, once, bounded.** The slot's bring-up (`make dev-headless`, the
   seed target when the criteria assume a seed, the daemon target a criterion needs), then
   wait **keyed on the readiness probe** — a bounded poll with a generous ceiling as a
   hang-detector, never a fixed sleep — and do not start a heavy DB/e2e run beside it
   ([`implementation.md`](../../../process/implementation.md) §8). An outage that is the
   checkout's own and covered by the runbook (a stale schema after a migration, a port the
   per-checkout derivation resolves) is fixed and the run continues.
4. **Still not ready → this run produces no verdict.** Do not grade, do not spawn, do not
   move the issue to `Rework Queue`. Post one comment on the issue naming the substrate, the
   probe, its output and what the bring-up tried; write the done-sentinel with
   **`status: "needs-action"`** so the issue parks at **`Blocked · action`** — a person has to
   bring the substrate back or look at the box. Not `verify-failed`: that dispatches an
   implementer at a PRD with nothing to implement and spends one of its rework returns. Not
   `failed`: that charges an attempt against the PRD for an outage that is the box's. The PR
   stays open and green; the fleet's reset releases the issue once the substrate is back.
5. **Mid-run, the same rule per row.** A reviewer or browser sub-agent that finds its
   substrate gone reports the row as **`BLOCKED (env)`** with the probe output — never FAIL,
   never PASS. The coordinator re-probes: back → re-dispatch that batch only; not back → the
   whole run ends as in 4, with the rows already graded kept in the posted report (they carry
   into the next run's Step 0.8 as a prior matrix). **A `BLOCKED (env)` row never reaches
   Step 4 as a FAIL** — the verdict table is about the work, and this row says nothing about
   the work.

A criterion whose substrate the dev stack *cannot* provide at all — a real cluster, a
customer network, a production estate — is not a readiness problem; it is a `[ext → SLnnn-Cn]`
promotion or a proof PRD (`prd:create` Phase 4 → *One proof substrate per PRD*), and Step 1
grades the promotion, not the behaviour.

## Step 0.8: Re-entry after a FAIL — re-prove the open lines, smoke the rest

**A first verify audits the whole PRD. A re-entry audits what changed.** The PRD arrives
here a second time because Step 4 sent it to `Rework Queue` (or Step 0.7 ended a run on a
substrate block) and an implement session has since closed the open lines; the matrix at the
graded head is on the issue, and the rework is a diff against that head. Re-auditing every
row from scratch spends a reviewer batch and a refuter on rows nothing touched. Measured
 over the 43 PRDs that passed this gate between  and 09-08: in a FAIL
verdict the **median share of criteria actually failing was 15%** — one or two rows of
twelve — and the other rows got a fresh reviewer batch and a fresh refuter on every round;
0570's seven `kind` rows were re-audited seven times while its two `drill` rows looped.

**Detect the re-entry.** `status: implementing` *and* the tracker issue carries a prior
verification report for this PRD — a `## Verification Report` comment with a FAIL verdict or a
substrate-blocked partial, or the fleet's `verify-failed` marker comment. No prior report →
this is a first verify: go to Step 1 and audit everything. A prior report you cannot read
(the tracker unreachable, the comment missing its `Graded at:` head) → the same: full audit,
and say in the report why the delta path was not taken.

**Partition the criteria — the diff decides, not you.** Read the newest prior report's
`Graded at:` head and its matrix; take the rework diff `git diff --stat <graded-at>..HEAD`
(submodule pin moves included). Then every criterion falls into exactly one of two sets:

1. **Re-prove in full** — Steps 1–3 exactly as a first verify, reviewer batch and refuter:
   every row the prior verdict left **FAIL, PARTIAL, refuted or `BLOCKED (env)`**; every
   prior-PASS row whose **cited evidence lies inside the diff** — the cited file, the named
   test, the probe, the component that renders the cited surface; and every UI row whose
   surface any file in the diff renders (a PASS whose evidence moved is no longer a PASS).
2. **Carry on a smoke** — every other prior-PASS row. The smoke is one cheap, read-only check
   per row, run by the coordinator or one small sub-agent, with no refuter: the cited
   `file:line` still holds the cited mechanism at HEAD; the named test is **in the green gate
   run at HEAD** (named in the run's output, not assumed); for a UI row, the surface loads on
   the dev stack with zero console errors. A smoke that does not hold moves the row to set 1.

**Bounds — when the delta is not a delta.** Fall back to Step 1's full audit, and say so,
when set 1 is more than half the criteria, when the diff reaches files no `*-plan.md` of this
PRD names, or when the prior report's matrix does not cover every criterion the PRD now
carries (an AC was added or reworded since it was graded).

**What does not change.** The verdict still covers the **whole** matrix (all-PASS, or
pass-with-follow-up when every open row is non-critical — Step 4), the refuters still run
over everything in set 1, the reachability and claimed-requirement checks still run, and the
`verified` stamp is the same stamp — a carried row survived a refuter at the graded head and
a smoke proved its evidence did not move. The report (Step 3) carries a **Provenance** column
on every row, `re-proved` or `carried (smoke)`, so a reader can see what this run audited and
what it inherited. Never cherry-pick by hand which batches to re-run: the partition is the
diff's, and a coordinator that "just re-checks the two that failed" without the diff has
skipped exactly the regression a rework introduces.

---

## Step 1: Carve up the work

From the PRD, extract:

- **Acceptance criteria** — numbered list under "Acceptance Criteria" or "What's done when". Pull each item verbatim.
- **Goals / outcomes** — from "Goals" or "What success looks like". Pull each success measure.
- **UX criteria** — if `ux-design.md` exists, pull the visible-behavior expectations.
- **Claimed requirements** — read frontmatter `implements:` and map each requirement ID to
  the AC(s) citing it (`[]`). Those ACs carry a durable commitment, not just a local
  criterion; tag them, and read each cited row's statement out of
  `knowledge/requirements/<domain>.md` so the "Claimed-requirement coverage" check below has
  the actual wording to judge against. No `implements:` → nothing claimed, skip that check.

Tag every criterion as **UI** (user-visible behavior — anything a person would see, click, type into, scroll, or read on screen) or **non-UI** (handler, query, contract, permission check, migration, background job, audit log). When in doubt, tag UI — false positives just trigger an extra browser check.

**A criterion tagged `[ext → SLnnn-Cn]` was promoted, and you check the promotion — you never
N/A it.** `[ext]` marks a criterion observable only against a real environment the dev stack
cannot stand in for (a live cluster, a third-party credential, a customer network, a second
real user). It was promoted when the PRD was written (`prd:create` Phase 4): the same
criterion sits as a row in the owning slice's `## Bar` with a probe, and the slice's driver
(`program:deliver --slice`) measures it every cycle — the tier whose promise *is* that
environment owns the observation. Your part is three checks, not a verdict on the behaviour:
(1) the tag carries a criterion id; (2) that id resolves to a row in the bar of
`knowledge/slices/<the PRD's own slice:>.md`; (3) that row's Probe cell is a real observation,
not `No probe yet.` All three hold → **PASS (promoted)** in the table, with the row id as the
evidence. Any missing → **FAIL**, routed to `/fleet:prd:implement` (an absent promotion is
missing work, not a broken feature). **A bare `[ext]` with no `→` is the old escape valve** —
a criterion N/A'd "until the dependency exists", a PRD shipped over it, and a slice computing
*complete* from that PRD with the one thing its `Done when` needs never exercised. Measured
: 4 of the 49 slices reading complete rested on exactly that. It fails here for that
reason, and **`verified` never flips over a failed promotion.**

Group them into 2–4 independent review batches. **Group by area** — sub-agents read code, and re-reading the same area for each criterion wastes effort. The default split:

- **Backend batch**: all non-UI criteria + goals that depend on Go / SQL / OpenAPI / handlers / permissions / migrations. Code-reading is fine here.
- **Frontend code batch**: UI criteria where the implementation lives in React / TS — checked for structural soundness (component wiring, provider mounts, hook usage, URL-state handling). Code-reading PASSes are **conditional** — they only count if the Browser batch also passes for the same surface.
- **Browser batch (mandatory whenever the PRD touched the UI in any way)**: every UI acceptance criterion exercised in a live browser against `make dev`. The trigger is *any* of: a file under `frontend/` modified, an AC describing user-visible behavior, `frontend-plan.md`, `labels: type:ui`, `ux-design.md` present. PASS requires a probe step + screenshot. See Step 2 for the protocol.
- **Cross-cutting / UX batch**: end-to-end flows, copy, accessibility, and **design fidelity + information-design quality** — driven from the browser (folds into the Browser batch unless the PRD has so many UX criteria that a dedicated reviewer makes sense). *Design fidelity* = the shipped surface matches the PRD's approved mockups (`ux-design.md`). *Information-design quality* = it passes `ui-spec.md` → Design Foundations → **Information design** (the `Q*` rubric in [`ui-audit-checklist.md`](#) §1b): no dead-space, value≠label, every attention-number links to its list, human identifiers, no redundant chips, complete header. This is the gate that stops a backend-correct page from shipping as a bad surface.

Skip a batch only if the PRD genuinely has no criteria in that category. **Never skip the Browser batch when the PRD touched the UI** — that is the failure mode this command is supposed to catch. When in doubt, run the Browser batch.

---

## Step 2: Spawn reviewers in parallel

For each batch, send an Agent tool call **on `model: sonnet`, `subagent_type: general-purpose`** — reviewers read code and report, which Sonnet parallelizes cheaply; you (the coordinator) stay on the parent model for the Step-3 synthesis (matches `/fleet:prd:implement` Rule 2, and the `spawn-reviewers` step in the Command spine above). Each prompt must be self-contained — the sub-agent won't see this conversation. Include:

- The PRD number and a one-line feature summary
- The criteria to review (verbatim, numbered)
- Pointers to the likely file paths (from `*-plan.md` or via grep)
- The output format (the table below)
- The boundary for that batch (read-only for code batches; browser-driven for the Browser batch)

### 2a. Code batches (backend, frontend-code)

> Review acceptance criteria N–M for PRD NNNN (\<one-line feature summary\>). For each criterion, find the implementing code and judge PASS / PARTIAL / FAIL with `file:line` evidence.
>
> **Criteria** (verbatim):
> N. \<criterion text\>
> N+1. \<criterion text\>
>
> **Implementation lives in** (best guesses; verify by reading):
> - ``
> - ``
>
> **Do NOT** run tests, run `make`, modify files, or write production code. Read-only investigation.
>
> Report a table:
>
> | # | Criterion | Status | Evidence | Notes |
> | --- | --- | --- | --- | --- |
> | N | \<short paraphrase\> | PASS / PARTIAL / FAIL | `path:line` | brief explanation if not PASS |
>
> Then a 1-paragraph summary of overall confidence and anything that surprised you.

### 2b. Browser batch (mandatory whenever the PRD touched the UI)

Spawn ONE Browser-batch sub-agent. It needs a running dev stack — Step 0.7 already established that it is serving and on which ports; hand the sub-agent those probes and their results. It confirms the stack is still up before its first step and **does not autostart `make dev` itself**; a stack it finds gone mid-run makes its remaining rows `BLOCKED (env)` with the probe output (Step 0.7 point 5) — never FAIL, never PASS.

> Browser-verify acceptance criteria N–M for PRD NNNN (\<one-line feature summary\>). For each UI criterion, exercise the feature in a real browser and judge PASS / PARTIAL / FAIL with **probe step + screenshot** evidence. Source-only PASSes are not accepted.
>
> **Prereqs:**
> - The stack must be running (`make dev-headless`). **Read this checkout's ports the way `slot:dev-environment` says** — never a default. Probe the readiness route `slot:dev-environment` names before the first step.
> - The dev login posture `slot:dev-environment` describes — where auth is disabled by default a synthetic identity is injected and there is no login flow; where it is not, log in as the slot says.
> - Tail the log sinks `slot:dev-environment` names while running probes; any new `error`/`uncaught` lines that appear during a step are a FAIL for that step.
>
> **Criteria** (verbatim, only the UI ones):
> N. \<criterion text\>
> N+1. \<criterion text\>
>
> **Surfaces to exercise** (from the PRD / frontend-plan):
> - `/some/route` — \<what should be visible / clickable\>
> - `/some/other/route?param=x` — \<what should happen\>
>
> **How to drive the browser:**
> - Prefer extending an existing probe in `tests/playwright/` (the repo's `slot:dev-environment` names the existing ones) or write a PRD-specific one: `tests/playwright/probe-NNNN-<slug>.mjs`. Probes must:
>   - Navigate to each surface, wait for the load-complete signal (not just `domcontentloaded` — wait for the AC's key element).
>   - Capture a screenshot per AC: `tests/playwright/screenshots/NNNN-<ac-id>.png`.
>   - Assert each AC's observable behavior (text content, element visibility, URL state, console-error count).
>   - Fail loudly on `console.error` or any uncaught exception during the run.
> - Run with `cd tests/playwright && node probe-NNNN-<slug>.mjs` (or the existing probe). Exit non-zero on any failed assertion.
> - **You MAY write/extend a probe to test an AC.** You may NOT change feature code to make an AC pass — that's a FAIL the user must fix via `/fleet:prd:implement`.
>
> **Probe-author gotchas (read before writing assertions — these caused real false-negatives in prior runs):**
> - Required-body POSTs: if your probe drives an HTTP request directly (rare — usually you click UI), pass `{}` as the body, not no body. An empty body against a required schema is a 400 that reads like a product defect.
> - Sanity assertions on names/IDs: regex-match identifier-safety (`/^[A-Za-z][A-Za-z0-9_]*$/`), don't hardcode a literal. A casing mismatch between an entity's `id` and its `name` is a common trap.
> - A mocked model queue (if this PRD's feature uses one): the queue is per-harness. If a step enqueues a mock response but the request fails before consuming it, the mock LEAKS to the next step and the next AC fails with a baffling wrong answer. Drain or reset between steps.
> - For async work that outlives an accepted response: a probe that waits for completion needs the handler to have detached the work from the request's lifetime, and any rows the work depends on to exist before it starts. Where either is missing, the probe times out and the defect is real — report it as one, do not lengthen the wait.
> - The repo's own probe gotchas, where it keeps them: `slot:dev-environment`.
>
> Report a table:
>
> | # | Criterion | Status | Evidence | Notes |
> | --- | --- | --- | --- | --- |
> | N | \<short paraphrase\> | PASS / PARTIAL / FAIL | probe step `<name>` + `screenshots/NNNN-N.png` | console errors observed, broken interactions, missing element, etc. |
>
> Then a paragraph covering: (a) did the page load at all? (b) any console errors during any step? (c) anything that looked rendered but didn't actually work when you clicked it?
>
> **Then a structured design-fidelity + information-design check (MANDATORY for any UI PRD — the gate that stops a backend-correct page from shipping as a bad surface).** This is the same [`design-fidelity bar`](../../../process/design-fidelity-loop.md) §2 that `implement`'s Stage-3 build loop fixed to — verify confirms it held, it doesn't invent a fresh standard:**
> - **Fidelity vs. the approved design AND the named reference.** If `ux-design.md` (or PRD-embedded mockups) exists, compare the shipped page side-by-side with the approved mockup and call out every divergence (layout, density, components used, hierarchy). **Also compare against the PRD's named high-craft reference** (`design-fidelity-loop.md` §1, stored at `mockups/reference-<archetype>.png`) — the shipped surface should read as a sibling of it, not a generic default. "The mockup/reference looked better" is a fileable gap — capture the mockup, the reference, and the live screenshot.
>   **Both comparison targets must be ON DISK** ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5-0): the fidelity fixture route or the PRD's committed `mockups/**.html`, and the `reference-*.png`. **You run headless — a hosted artifact URL is not a comparison target and never satisfies this check.** If the approval record cites only a link, or the reference PNG is missing, **file that as a finding against the PRD** (the design contract is unverifiable, so the fidelity check could not run) rather than silently passing the surface or marking the check N/A.
> - **Information-design quality** (the UI contract's information-design section; the UI checklist's holistic pass, `slot:audit-profile`). For each rendered surface check: **Q1** no card/section >40% empty (no dead canvas); **Q2** no value styled as a label, no name repeated under its own `PageHeader` title; **Q3** every metric labelled and every attention number (non-zero Failed/Awaiting) links to its list, zero is `0`/`—`, no invented always-empty fields; **Q4** no raw/truncated UUID as a row's primary label; **Q5** no duplicate adjacent status/name chips; **Q6** detail header has a subtitle + ≥1 primary action and shows the mapped status word, not the raw enum.
> - **Holistic:** would a designer ship this? Flag any surface that reads as unfinished even if no AC covers it.
> - **Visual-regression baseline** (`design-fidelity-loop.md` §4). If the surface carries a committed Playwright `toHaveScreenshot()` baseline, run it and treat an **unexplained diff as a defect** for that surface (the shipped page drifted from the state that cleared the fidelity bar). A diff is only acceptable if it is an intended change *and* the baseline was deliberately updated with the diff reviewed — never regenerate a baseline just to make the check pass. On a diff, attach the generated diff image.
>
> Report each fidelity/quality gap with the screenshot(s); grade the surface accordingly (a material gap is a FAIL for that surface — see the coordinator's Step 4). Present-but-wrong defects route to `/fleet:bug:fix`; purely-cosmetic systemic drift batches into a follow-up `/fleet:task:create`.

### 2c. Docs batch (a fresh session follows each new page literally)

**When the design carries a `## Docs impact`, spawn ONE Docs-batch sub-agent — a session that did not write the pages.** A page is a claim, so it is verified the way every other claim is: a reader who has never done the task **follows the page literally, in the real UI**, and reports where the product and the page disagree.

- **Read the page from the home `slot:docs` names** — never a path the command invents. If the `docs` slot is unfilled, there is no home and no page contract: this batch is **skipped**, and the report says so in one line (the slot's degrade), rather than passing pages it cannot find or failing on ground the repo declined.
- **Follow each new how-to step by step**, typing what it says and clicking what it names, on the running stack (`slot:dev-environment`). Do not fill gaps from intuition — a step you had to guess is a finding.
- **Grade each page PASS / FAIL** with evidence: the step number where it broke, what the page said, what the product did.
- **A page that cannot be followed turns the PRD back.** A how-to whose step is wrong, a screenshot that lies, a prerequisite the page omits, a page that promises something the product does not do — each is a **FAIL** that routes to `prd:implement` (fix the page) exactly like any other failed AC; it is never waived as "docs, not product". A page that is merely *thin* is a follow-up (`page:improve`), not a turn-back.

Report a table:

| # | Page id | Kind | Status | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | \<page id\> | how-to | PASS / FAIL | step `<n>` + screenshot | where the page and the product disagreed |

Fan out all batches in parallel. Wait for all to complete.

---

## Refute the PASSes

Every reviewer so far has been looking for defects. This step looks for **wrong PASSes** — the
review's actual failure mode, and until now the one direction with no second look. The
existing cross-check fires only on PARTIAL/FAIL and exists to reduce false *negatives*; a
PASS was never checked by anything.

Spawn refuters in parallel — one per batch of PASSed criteria, fresh context, read-only.
On a re-entry (Step 0.8) the refuters take the re-proved set only — a carried row already
survived a refuter at the graded head, and its smoke proved the evidence did not move.
Give each the **opposite posture from the reviewers**, in these words:

> Your job is to REFUTE this PASS, not to confirm it. **Default to REFUTED unless the actual
> source forces confirmation.** A plausible-but-unproven PASS must not survive. For each
> criterion you are handed: read the cited evidence yourself. Is the cited `file:line` on a
> live call path, or merely defined? Does the cited probe assert the behaviour, or just that
> the page rendered? Would this evidence still look identical if the feature were deleted?
> **If the criterion is satisfied by an "it already exists / no new tool needed" claim, the
> citation must be the actual mechanism that grants the capability — a real running code path.
> A citation to `design.md`, `backend-plan.md`, or any other planning document repeating the
> same claim is NOT evidence, even if worded confidently; planning-doc prose can be wrong, and
> a doc citing another doc citing the original claim is circular, not verified. Go find the
> code yourself.** Return `confirmed | refuted | adjusted` with the reason.

This is the posture the audit fan-out uses and this command did not. Refuted criteria go
back to the matrix as FAIL and route per the banner.

**Instrument it.** Report `refuted / total PASSes` in the verification report. **A run that
refutes nothing is a smell, not a triumph** — the audit engine treats zero findings *and*
zero refutations as evidence the finders under-scoped, and the same reads true here. If a
whole PRD's PASSes survive unchallenged, say so explicitly and note whether the refuters
were given real evidence to chew on or just restatements of the criteria.

**Negative controls are checked here.** For every criterion whose evidence is a test, the
implementation must have recorded the mutation that makes that test red, plus proof it went
red. A test nobody has watched fail is not evidence —  shipped three security tests
that passed with their invariant deleted, and  shipped a fail-open control whose own
tests were already red and ignored. **A criterion whose test has no negative control is
PARTIAL, not PASS.**

**Existence claims are checked here ().** A criterion satisfied by "this capability
already exists" / "no new tool needed" is the highest-risk shape of PASS, because a code-batch
reviewer can be fooled into citing confident planning-doc prose instead of running code — PRD
0414's AC-6 was stamped `verified` on a citation chain that ended at `design.md`, which cited
itself. The refuter must independently locate the mechanism that grants the capability (e.g.
the actual gate/allow-list deciding which agents get a tool) — not accept a citation to
`design.md` / `backend-plan.md` / the PRD's own prior text as terminal evidence. **A criterion
whose only evidence is a planning document is REFUTED, never PASS.**

## Reachability — name the surface, drive it

A capability that works but cannot be reached is not shipped; it is stranded backend. This is
the single most common PRD failure mode in the audit corpus (, F-PROFILE-1, ,
), and the check that catches it — `feature-audit-checklist.md` F3 — runs bi-weekly
over a catalog rather than over the PRD that created the risk.

For each capability this PRD claims:

1. **Name the surface** a customer reaches it through — a route, an API operation, an MCP
   tool, a Slack path. Not "it is registered"; the thing a person touches.
2. **Drive it** from that surface, not from a test harness. A route that exists but calls
   nothing still renders.
3. **If no surface exists, that is a FAIL**, not a follow-up. Per CLAUDE.md, a capability
   with no customer-facing UX is stranded backend, not a shipped feature.

Record the surface and the drive evidence in the report. `AllowedTools` exclusions, absent
MCP registration, and profile allowlists that filter the capability out are all "no surface".

## Step 3: Synthesize

Merge the sub-agent reports into a single matrix. For UI criteria, the row is PASS only if **both** the frontend-code batch and the Browser batch agreed it passes; if the code batch said PASS but the Browser batch said FAIL, the row is FAIL.

```
## Verification Report: <feature name> (PRD NNNN)

**Graded at:** `<full HEAD sha>` on PR #<n> · **Substrates:** <each Step 0.7 probe and its result> · **Entry:** first verify | re-entry (prior report graded at `<sha>`, diff <n> files) · **Reconciled:** none | `<old>`→`<new>` (regen_reconcile: <derived paths>, <submodule pointers>)

### Acceptance Criteria
| # | Criterion | UI? | Code Evidence | Browser Evidence | Status | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | <text> | yes | `path:line` | probe `<name>` + `screenshots/NNNN-1.png` | PASS | re-proved |
| 2 | <text> | no  | `path:line` | n/a | PASS | carried (smoke: test in green run at HEAD) |
| 3 | <text> | yes | `path:line` | probe `<name>` — console error on load | FAIL | re-proved |
| 4 | <text> `[ext → SL162-C3]` | no | bar row `SL162-C3` in ``, probe named | n/a — measured by the slice driver | PASS (promoted) | re-proved |
| 5 | <text> | yes | `path:line` | probe `<name>` — stack not serving (probe output) | BLOCKED (env) | — |

### Goals / Outcomes
| Goal | Achieved? | Notes |

### UX criteria (if applicable)
| Spec | Implementation | Status |

### Browser batch summary
- Surfaces visited: <list of URLs>
- Probe file(s): `tests/playwright/probe-NNNN-<slug>.mjs` (and any others extended)
- Console errors during the run: <count, with the worst offender>
- Anything that rendered but didn't work: <list>
- Anything visibly off vs PRD/ux-design intent: <list>

### Docs batch summary (omit when the `docs` slot is unfilled — say so instead)
- Pages followed: <each page id, with the home `slot:docs` names>
- Pages that could not be followed literally: <page id + the step that broke, or "none">
- Pages promising what the product does not do: <page id, or "none">

### Passed with follow-up (non-critical only — omit when empty)
| # | Criterion | Class (d/e/f/g) | Why non-critical | Follow-up |
| --- | --- | --- | --- | --- |
| 2 | <text> | d — test/evidence gap | behaviour confirmed at `path:line` / probe; gap is missing negative control | ENG-NNNN |
```

**`Graded at:` is load-bearing, not decoration** — it is the head the next run's Step 0.8 diffs
against, so it is the full sha of the commit the batches actually read, never a branch name. On
a first verify, `Provenance` is `re-proved` on every row. **Post the report as `comment` kind `verdict`** in every terminal — PASS,
pass-with-follow-up, FAIL, or substrate-blocked — because that comment is what Step 0.8 reads
on re-entry; if Fleet is unreachable, say so in the final output, and the next run falls
back to a full audit. The pass-with-follow-up table is **auditable ship evidence**: every
non-critical row that rode the pass must name its follow-up key here (Step 4).

If a reviewer flagged PARTIAL or FAIL on anything important, spawn ONE narrowly-scoped follow-up agent to cross-check (sub-agents make mistakes; a second pass on doubtful items reduces false negatives). Keep the cross-check prompt small (<5 min wall time): pass ONLY the doubtful AC numbers, the file:line cited as evidence, and any new files you just learned about. Don't re-run the whole batch.

If the cross-check confirms the gap, route by **what kind** of gap it is:

- **Missing** behavior (the feature/test simply isn't there — e.g. a 403 unit test, an audit assertion, an unimplemented endpoint) → `/fleet:prd:implement NNNN` for the specific gap.
- **Broken** behavior (present but wrong — the page crashes on load, a console error fires, an interaction does nothing, a handler returns the wrong data) → **`/fleet:bug:fix NNNN — <symptom>` (mandatory — never an ad-hoc patch)**, so the remediation reproduces the failure as a failing test/probe assertion FIRST (RED), then fixes the **root cause** (not the symptom), then confirms it GREEN. A browser-batch "rendered but didn't work when clicked" or a console crash is a **defect**, not a missing feature — it goes to `/fleet:bug:fix`. **Every** broken criterion this command surfaces is remediated this way.

After the gap is closed, re-run `/fleet:prd:verify NNNN` — it re-enters through **Step 0.8**: the open lines and every row the rework diff touched are re-proved in full, the rest carried on a smoke. Never cherry-pick by hand which batches to re-run — the partition is the diff's, not yours; a first verify, and any re-entry Step 0.8's bounds refuse, re-batches from scratch.

### Claimed-requirement coverage

**An AC citing `[]` *is* the verification of ** — that is the whole
mechanism by which a durable commitment gets checked, since the register stores no status
and nothing else in the repo tests one. `make validate-knowledge` already proved
at pre-commit that every claimed requirement *is cited* by some AC. **What a citation
cannot prove is that the AC actually verifies the commitment** — so this check is the
refuters' posture applied to the claim: treat the citation as decorative until the
evidence says otherwise.

**The report is keyed by commitment, not by document** — that is what makes a claim which
quietly fell out between design and code visible at all. For each ID in `implements:`, add a
row; `grep` the ID (punctuation stripped — `RUN008`) across the test tree to fill the *Test*
column, per the naming convention in
[`prd:implement`](implement.md) → *Negative controls*:

```
### Claimed requirements
| Requirement | Cited by | Test | AC status | Would a violation have turned that AC red? |
| --- | --- | --- | --- | --- |
|  | AC 4 | TestControlPlaneRefusesCustomerCode_RUN008 | PASS | yes — the probe feeds the control plane untrusted customer code and asserts it refuses to execute it |
| RUN-090 | AC 7 | TestTwoConcurrentRequests_RUN090 | PASS | **no** — AC 7 asserts a second concurrent request is accepted; RUN-090 also commits that *different principals* may share one container, which no AC exercises |
| RUN-140 | — | — | **MISSING** | claimed, no AC, no test — the commitment ships unbuilt |
```

The last column is the judgement no validator can make: read the register row's statement,
read what the AC actually asserted, and answer it. A **no** is a FAIL for that criterion,
exactly as a refuted PASS is — the commitment is unverified, and an unverified commitment
riding a shipped PRD is worse than an unclaimed one, because the derived backlog now
reports it done.

**A `MISSING` row is a hard FAIL and is never waived here.** Pre-commit proved the claim was
*cited* at `planned`; a `MISSING` at verify time means the citation was dropped, the AC was
cut, or the test never landed — and each of those is the commitment silently leaving the
build while the register goes on reporting it delivered. The two honest resolutions are the
same two `prd:plan` offers: build it, or drop the claim from `implements:` and say why. Never
flip to `verified` over one.

---

## Step 4: Verdict

- **All PASS** → feature verified. Continue to Step 5.
- **All PASS, but the carrier PR is blocked only by a ship-gate registration gap** →
  **the mechanical registration lane, NOT `Rework Queue` for a full implement** ().
  This is the case where every acceptance criterion PASSed, the PR is mergeable, and the only
  red required check is one whose *sole* failure is that a changed path was never **registered**
  with the gate — a missing gate-coverage allow-list entry, or a CI path filter that does not
  cover the path the PR changed. It is neither a failing criterion nor a conflict, so a full
  `/fleet:prd:implement` re-entry re-derives work nothing got wrong.
  1. **Prove the class, do not assume it.** `gh pr checks <pr>` and
     `gh run view <run-id> --log-failed`: the failing check's output must name a path the PR
     changed and the registration artifact it is absent from (an allow-list, a path filter). If
     the check is red for ANY other reason — a real test failure, a lint error, a build break —
     this is **not** this lane: route it per the PARTIAL/FAIL bullet below (or `/fleet:bug:fix`
     for a defect).
  2. **Post the brief** on the issue stamped `<!-- linear-agent:gate-registration-rework -->`,
     naming: the PR and its current head; the exact failing check; the path the check flagged;
     and the registration file the fix belongs in (the allow-list entry, the path-filter line).
     State in the brief, in as many words: **the edit boundary is the registration file only —
     do NOT touch product code, tests or acceptance criteria.** The brief is the work order the
     mechanical lane follows.
  3. **Move the issue to `Rework Queue`** and write the done-sentinel `verify-failed`. That
     hand-back dispatches the **mechanical registration lane** () — a cheap short seat
     that adds the one registration line, pushes, drives CI green, and hands back to `Verify
     Queue`; **not** a full `/fleet:prd:implement` re-entry on the primary model. A fresh verify
     pass then certifies the new head before merge.
  4. **Not a refuted criterion.** A registration-only hand-back is not a criterion FAIL: it does
     not count toward the re-entry cap and it never parks the issue on its own. If the
     registration is genuinely a product or scope judgement rather than a mechanical path-add,
     that is a `Blocked · decision` park, not a guess.

- **Any UI criterion missing Browser-batch evidence** → automatic FAIL for that row regardless of what the code batch said. List the gap and stop. (This row is **critical** under the classification below — the behaviour was not browser-confirmed.)
- **Any `[ext]` criterion without a resolving, probed bar row** → FAIL for that row (Step 1's
  promotion check). A bare `[ext]` is never N/A and never PASS. (**Critical.**)
- **Any `BLOCKED (env)` row** → no verdict this run. The row is not a FAIL and not a PASS; it
  says the substrate was down, not that the work is wrong. Re-probe per Step 0.7 — back →
  re-dispatch that batch and finish; not back → end the run on the Step 0.7 terminal
  (`needs-action`, `Blocked · action`), post the partial report with `Graded at:`, and move
  nothing to `Rework Queue`: an implementer dispatched at an outage has nothing to change.
- **Material design-fidelity / information-design gap** → **FAIL the relevant surface, even if its functional ACs all pass.** A surface materially fails when it diverges from the approved `ux-design.md` mockup, **reads as a generic default beside its named high-craft reference** (`design-fidelity-loop.md` §1–§2), breaks an `ui-spec.md` Information-design rule (dead-space, value-as-label, an attention number with no drill-in, a raw-UUID primary label, a stub header), or shows an **unexplained visual-regression diff** (§4). A UI PRD does **not** reach `verified` while any surface materially fails fidelity — list the gap with the mockup + live screenshot and route per Step 3 (present-but-wrong → `/fleet:bug:fix`). This is the shift-left of the UI audit's `Q*` rubric: catch the bad surface here, before it ships, not in a later sweep. (**Critical** — material fidelity is not UI polish.)
- **Any PARTIAL or FAIL** → classify every open row as **critical** or **non-critical**
  (below), then take exactly one path:

  ### Criticality ( — proof & polish only)

  The criticality call is the **verifier's judgement + the refuter**. **When unsure →
  critical (rework).** Never pass a row by hoping a follow-up will catch it.

  **Non-critical** — a row may ride a pass **only** when it is one of these four classes,
  and *only* when the named condition holds:

  | Class | What it is | Condition that keeps it non-critical |
  | --- | --- | --- |
  | **(d) test / evidence gap** | missing negative control, test not asserting enough, missing screenshot, probe coverage thin | the **behaviour itself was independently confirmed working** (live code path, green probe, or equivalent). Enforcement is real; the gap is only that a test would not redden on a regression, or evidence is incomplete |
  | **(e) UI polish** | purely cosmetic drift — spacing, alignment, token mismatch that does not change meaning or break an Information-design rule | not a material design-fidelity / information-design gap (those stay critical above) |
  | **(f) doc / ledger / knowledge bookkeeping** | stale citation, version pin in a doc, ledger row out of date, roadmap/map prose | the shipped behaviour and its contracts are correct; only the bookkeeping lags |
  | **(g) environment / flake** | a flake or env-bound failure that does not indict the work | the behaviour holds under a clean re-probe; the open row is the flake, not the feature |

  **Critical — always rework** (unchanged from the all-or-nothing bar for these):

  - authz / governance
  - data correctness
  - any contract / API / schema a dependent PRD builds on
  - core logic wrong
  - a missing piece of an AC's **core promise** (partially-missing features stay rework — never
    "pass the AC and file the missing piece")
  - a claimed-requirement **`MISSING`** row (the register derives "delivered" from a shipped
    PRD; an unverified commitment must not ride one)
  - material design-fidelity / missing Browser-batch evidence / bare `[ext]` (the bullets
    above already FAIL these)

  Rejected by the  decision: also passing partially-missing features; keeping
  all-or-nothing for every PARTIAL/FAIL.

  ### Path A — every open row is non-critical → **pass with follow-up**, then ship

  Feature verified. **Do not** move the PRD to `Rework Queue`. For **each** non-critical
  open row, file one linked follow-up **before** Step 5:

  1. Body carries the verifier's evidence **verbatim** (the matrix row, the cited
     `file:line` / probe / screenshot, the class letter, and why it is non-critical), plus
     a line `Recommended priority: High` so `/fleet:check` has the weight (do **not** set
     priority at create — triage birth forbids it).
    2. `file_issue` kind `task` (command `prd:verify`).
  3. `relate` with the PRD issue as subject, kind `related`.
     `relate` <FOLLOW-UP-KEY> related <PRD-KEY>`.
  4. List the row in the report's **Passed with follow-up** table with its follow-up key
     (Step 3 template). A ship without that table for every non-critical open row is not
     auditable and is not a pass.

  Then continue to Step 5 and Ship exactly as an all-PASS. Each follow-up is an ordinary
  `Type:task` and passes the same `/fleet:verify` gate as any task (task median lead is
  short; that is the quality backstop, not a waiver).

  ### Path B — any open row is critical → **rework** (unchanged)

  Stop, and **`move_issue` to `rework`** and **write the done-sentinel with
  `status: "verify-failed"`** (summary = the gap list: which criteria failed and what is
  missing). The move hands the PRD back for another implementation pass: the daemon routes
  a rework PRD to `/fleet:prd:implement`, posts your findings on the issue for that session
  to read, and re-arms verification once the new work is green.
  In the report, list the gaps with specific file paths, probe names, screenshot paths, and
  what's missing. Recommend the routed remediation per Step 3 — `/fleet:prd:implement` for
  **missing** behavior, `/fleet:bug:fix NNNN — <symptom>` for **broken** behavior (so it's
  reproduced as a failing test first) — then re-run `/fleet:prd:verify`. **Do NOT** flip
  status. A mix of critical and non-critical open rows is still Path B — file nothing as a
  "partial follow-up" while the PRD reworks; the non-critical rows ride the next verify.
- **A claimed requirement that is unmet or unverified** → FAIL, routed by which of the two it
  is. **Unmet** (its citing AC failed, or the AC does not actually test it): the work does not
  hold the commitment — remediate per Step 3 and re-verify. Nothing is written to the register;
  a requirement's status is derived from PRDs' `implements:`, never stored. **Wrong** (the work
  proved the commitment itself no longer holds): that is a **register edit** — change the row's
  `Disposition` (`superseded by RUN-NNN`, the row keeping its ID and its statement) and drop the
  claim from `implements:`. Never quietly reword the AC so the PRD can pass, and never delete
  the row — a requirement that is deferred or replaced keeps its ID, or the deferral becomes a
  disappearance. **A supersession is a change with a closure, not a cell edit** — the dead row's
  own `Needs` cleared, every edge pointing at it re-derived, every *other* PRD claiming it
  re-pointed, all in the same change
  ([`knowledge-model.md`](#) → *Decisions and
  requirements*; `make validate-knowledge` fails the commit on each residue). A
  claimed-requirement **`MISSING`** row is always **critical** (Path B) — never a follow-up.
- **A FAIL caused by an AC whose implementation lives entirely in another repo** is a design-time
  authoring miss, not missing or broken in-repo behavior — `/fleet:prd:implement` has nothing
  here to build and will just fail again. Route it to `/fleet:prd:design NNNN` to split the AC
  out per `` → "Cross-repo scope" (file the companion
  under Rule G, name it in "Delivery notes (cross-repo)"), not to `/fleet:prd:implement`.

**When the verdict is a person's call, not a rework** — a criterion that cannot be met as
written without an authoring change, a promise that contradicts an accepted requirement, a
bound exhausted — the run parks at `Blocked · decision` (`needs-decision`). That park asks in
writing, so it is bound to the card, and the `decision` document **quotes every acceptance
criterion and requirement the question turns on** — the person answering has not read this
PRD. Measured on  (): *"PRD 0676 AC-4 is not met as written …  …
 …"* was unanswerable without opening three documents.

<!-- include: process/interview-card.md -->
### Before you ask a human anything — the interview card

**The person answering has not read the issue, the PRD, the code or any register, and
will not look anything up.** They answer many questions a day from what is in front of
them, and only that. So, every time you ask:

1. **Say what the work is first, in plain words.** One or two sentences on what somebody
   will be able to do that they cannot today. Then **one concrete example** — a named
   person doing it, and what they see. Then **one line on what is undecided**, so the
   question reads as a fork and not a quiz. This goes in the message *before* the first
   question, once per run; later questions inherit it.
2. **Ask with `AskUserQuestion`:** 2–4 options, the one you recommend first and marked
   `(Recommended)`, and on *every* option why it is right and what it costs — not only on
   the one you favour, or the human cannot pick against you.
3. **Every option says what changes for a real person**, not what changes in the code.
   *"The error would read 'this key cannot list agents'"*, not *"return a typed reason from
   the allowlist path."*
4. **No bare ids, no unexplained jargon.** ``, ``, ``, ``,
   `PRD 0242` never appear in an option label, and anywhere else only in parentheses after
   the plain name — *the goal of getting a customer live without an engineer ()*. An
   internal noun (access profile, projection compiler, cause ledger, `blockedBy`) gets half
   a sentence of ordinary English the first time it appears. `file:line` stays, as evidence,
   never as the only statement of the problem.
5. **The test, before you send:** would somebody who has never opened this repo pick the
   same option, for the same reason? If not, rewrite. Being asked to *"explain that again"*
   is a defect in the question, not a preference — re-ask in full, plainer, and hold that
   register for the rest of the run.

6. **The person may not be the one who knows — every question can be answered *"I can't
   answer this"*, and you must plan for that.** The question card carries that choice itself
   (*Can't answer — carry on*); you never add it as an option, and you never invent an answer
   in its place. When it comes back: **carry on with an explicit `Assumption: <what you
   assumed and why>` line, marked unconfirmed by the owner** — or, where the right party is
   the reporter, carry the question to them as an open question — **never ask it again**, and
   list every such item under an **`Unconfirmed assumptions`** heading in what you write, so
   a human can review them later. Downstream, it is an assumption to confirm, not a fact. The
   rule, once: `.claude/process/interview.md` → *"I can't answer this"*.

**Headless — no human attached:** you write all of the above into the escalation instead,
in the same words, so whoever reads it later can answer it as filed.

Full protocol — discovery before forks, acting on the answer, where the decision is
written: `.claude/process/interview.md`.
<!-- /include -->

<!-- include: process/decision-document.md -->
### Parking on a person — the `decision` document (headless)

**Every `needs-decision` park writes one `decision` document, and it is the interview card
in fields.** The person clearing `Blocked · decision` reads this card and nothing else —
not the issue, not the PRD, not the register, not your comment thread. The sentinel's
`summary` is only a one-line headline for the park list; everything a person needs to decide
goes here. Write it to `$FLEET_RESULT_FILE` (skip only if that is unset) before the
done-sentinel:

```json
{
  "kind": "decision",
  "brief": {
    "work":    "What somebody will be able to do that they cannot today, in plain words.",
    "example": "One named person doing it, and what they see.",
    "stopped": "What stopped this run, in plain words — the fork, not the log.",
    "stakes":  "What is at stake either way."
  },
  "context": [
    {"ref": "AC-4", "name": "automated comments never reach the customer",
     "quote": "<the criterion's own text, verbatim>", "url": "<optional https link>"}
  ],
  "question": {
    "id": "<short id>",
    "prompt": "The decision, as one question in plain words.",
    "options": [
      {"id": "<short id>", "label": "<what the person picks, no ids>",
       "why": "<why this is right>", "cost": "<what it costs>",
       "then": "<what happens next if picked>", "recommended": true},
      {"id": "…", "label": "…", "why": "…", "cost": "…", "then": "…", "recommended": false}
    ]
  }
}
```

- **Two to four options, the recommended one first** and the only one marked `true`;
  `why`, `cost` and `then` on **every** option.
- **Quote what you cite.** Every acceptance criterion, requirement, issue or PRD the question
  leans on gets a `context` entry whose `quote` is its own text — or, in prose, the plain name
  with the id in parentheses: *the automated-account rule ()*. A bare `AC-4`, ``,
  ``, `PRD 0676`, ``, `PR #123` or `/:…` is refused.
- **Labels carry no ids at all**, and nothing says where the issue was parked — the fleet
  says that, and the person reading is already there.

**Check it before the sentinel** and fix every reason it prints, in this turn:

```bash
python3 knowledge/scripts/validate_decision.py "$FLEET_RESULT_FILE"
```

`0` meets the card; `1` prints every rule broken; `2` means there is no `decision` document at
the path. A park with a missing or refused document still parks — the fleet does not strand a
person's decision over its shape — but the park is recorded as `askRefused` with your reasons,
and that is counted.
<!-- /include -->

## Step 4.5: Ship-gate — may this run bless the merge?

An all-PASS verdict is about the acceptance criteria; it is not, by itself, permission to
call the carrier merge "this PRD's ship". : `/fleet:prd:verify 0564` concluded
"verified & merged" and let its issue reach `Done` on a merge whose own body declared
`NOT-IMPLEMENTING-PRD=0564:` — the machine-readable line the merge gate
(the pre-merge gate that refuses to bless a disclaiming carrier) parses and honours — while the PRD
still read `status: planned` on `main`. That session's comment stated both facts and
still returned success, so the terminal is decided by script, not by this session's
judgement. Before Step 5's flip, before shipping, and before ANY "verified & merged"
conclusion — including the already-merged-carrier shape, where there is nothing left to
stamp and the temptation to "confirm the merge" is strongest — run:

    python3 knowledge/scripts/validate_prd_verify_ship.py <NNNN> <KEY> --pr <carrier>

`<carrier>` is the PR Step 0.5 resolved.

- **Exit 0** → continue to Step 5 (flip) and Ship as normal.
- **Exit 1** → the merge this run would certify is not the PRD's ship (the frontmatter
  does not read `shipped` at the merge commit, the `status:` line never moved at this
  merge, or the PR body disclaims this PRD). The terminal is fixed, not negotiable:
  1. Do NOT conclude "verified & merged"; do NOT write a success sentinel; the issue
     must NOT reach `Done`.
  2. Do NOT flip the PRD's frontmatter — no `verified` stamp on this terminal.
  3. Leave the issue parked at **`Blocked · action`** (design B10) — move it there only
     if it is not already parked. The remaining half of the PRD stays driven by that
     park.
  4. Write the done-sentinel with **`status: "needs-action"`**, quoting the gate's
     output verbatim as the reason and naming what remains.

  Quote the gate's output verbatim in the terminal comment as well. The incident's
  comment said *"issue parked at Blocked · action"* in prose while the same session, in
  the same second, wrote the state to `Done` — quoting the machine verdict is what keeps
  the comment and the state write from disagreeing.

**Two-PR splits need no PRD-declared terminal ().** Do not look for a `split:`
frontmatter key or a `## Delivery split` section to decide which carrier is the ship —
that authoring convention was weighed and refused. The ship is the merge that moved
`status:` to `shipped` with no `NOT-IMPLEMENTING-PRD=` line; an earlier half is a non-ship
because its frontmatter did not move (disclaimer optional on the refusal path). Design
prose keeps the sequencing; this gate keeps the verdict. Decision:
[``](#).

---

## Step 5: Flip status (on success only)

**PRD frontmatter** — edit `knowledge/prds/NNNN-<slug>/prd.md`:
- Set `status: verified`
- Append `{ state: verified, at: < timestamp>, by: verify, issue: <KEY> }` to
  `status_history`, where `<KEY>` is this PRD's own tracker issue identifier (e.g.
  ``). The `issue:` field is load-bearing: the PRD-verify dispatch-token gate
  () recovers the issue key from this entry on the stamped PRD document — never
  from the commit message — and binds the daemon-minted `Dispatch-Token:` trailer to
  `HMAC(secret, v2:{issue}:{prd}:{pr})`. Omitting it fails the gate closed.

**Dispatch-Token trailer (daemon-dispatched verifies only).** When this session was
dispatched by the daemon, the dispatch token is in the environment under the variable the
mission names ([the dispatch envelope](../../../process/autonomous-drive.md#the-dispatch-envelope--what-the-daemon-supplies-and-where-it-is-defined)). Embed it
verbatim as a `Dispatch-Token: <value>` git trailer on the commit that carries the
`verified` stamp (read from the environment into the commit message only — never argv;
one instance of the general credentials-never-on-argv rule).
A self-authored stamp without a valid trailer cannot merge. For a **proof-only** PRD the
token is bound to the  sentinel `pr_number=0` (no open PR existed at dispatch);
embed it the same way — the gate accepts that form when this PR is knowledge-only.

**Roadmap — nothing to do.** `` is generated on demand and **not
committed**; it reads status live from each PRD's frontmatter, so the flip above is the
whole update. Render it any time with `python3 knowledge/scripts/gen_roadmap.py`.

There is no capability table, sequencing narrative, gap list, or demo-coverage
section in the roadmap any more (its only headings are `## Status summary`,
`## By program`, `## PRD index`). Durable customer-capability content lives in the
**feature capability maps** (`knowledge/features/<area>.md`) — if this PRD changed
what a customer can do, reconcile the owning map's rows there, not in the roadmap.

The frontmatter flip and the regenerated roadmap ship in the same commit (on the work branch — they merge with the PR). `/fleet:push` opens the PR; `/fleet:push ship` (auto-merge on green CI) or a manual merge then flips `status: shipped` when the PR merges to `main`, and the `prd-projection` pass of the fleet's `corpus-sync` loop (`fleet-service`) settles the tracker issue within the sync's interval once that merge is on `main` ( — the tracker's keyword auto-close is dead).

**Do NOT mirror a state to the tracker on an all-PASS or pass-with-follow-up.** This used to be one of two transitions that mirrored live (the other is `/fleet:prd:implement`, which still claims **`Implementing`**) — verify wrote **In Review** on the shared board. Under the workflow-state lifecycle that write is now actively harmful: your session already holds the issue in **`Verifying`**, and moving it to `Verify Queue` un-claims it, so the daemon dispatches a *second* verifier against the same code. The only remaining transitions are the daemon's own — `Verifying → Done` once your merge lands, and `Verifying → Rework Queue` from a **critical** refutation in Step 4 (Path B). So flip the PRD frontmatter, commit, and **leave the tracker state alone**; if you touch the issue at all (a comment, say) it's an **update** — **omit `labels`** entirely (the MCP `labels` field replaces the whole set and would wipe tracker-managed labels like the `Type:` ones). **Skip silently if Fleet is unreachable** — the `prd-projection` pass of the fleet's `corpus-sync` loop reconciles from `main`. Never fail the command because Fleet is unreachable.

---

## Ship (all-PASS or pass-with-follow-up)

On an all-PASS verdict (Step 4), on a **pass-with-follow-up** verdict (Step 4 Path A — every
open row non-critical, each filed and named in the report), or on a ship-only retry
dispatched via Step 0 against a PRD already `status: verified` — this command ships the PRD:
`/fleet:push ship <sha> <KEY>`. Ship mode carries the lane's merge-safety order ():
it disarms `python3 knowledge/scripts/gh_automerge_disarm.py` before its stamp push — the
open-time arm () must never survive a head move — and re-arms only after the plan
gate among `slot:git-workflow` reports green on the stamped head, then merges. Never
merge a PRD PR by arming over a pending re-dispatch of that gate: the forge's auto-merge
does not reliably re-validate a changed check state (the reliance PR #10055 falsified).

**Which gate this is comes from `$FLEET_VERIFY_GATE`, named by the lease (PRD 0745).** On a
`check:<name>` gate the control plane posts the verdict itself as a GitHub check through the
install's App, so ship mode **never re-runs a workflow**: `gh_automerge_arm.py --require-green`
excludes the gate's own check, arming while it is pending; the check turns green after the
control plane reads the verdict, and the PR merges. Ship mode's disarm-then-re-arm order is
unchanged. On `workflow:<file>` it is today's path — re-run the named workflow and re-arm only
after it reports green — and on an unset variable the lane carries no gate. When
`$FLEET_VERIFY_GATE_REQUIRED` reads `false`, the gate is not required right now: merge on the
verdict and let the control plane complete the check afterwards.

Shipping moved here because `implement` no longer merges its own work. The party that wrote
the code cannot certify it, and it cannot merge on the strength of that certification either:
before this, `push ship` stamped `status: shipped` on a caller's assertion that verify had
passed, with no access to the verify matrix and no way to check the claim.

On any **critical** PARTIAL or FAIL (Step 4 Path B), do not ship. The PR stays open and green,
the issue moves to **`Rework Queue`** (Step 4), and the routed remediation runs first.
Non-critical-only open rows are Path A — they ship with their follow-ups filed, they do not
rework. On a Step 4.5 ship-gate refusal, do not ship either — and the terminal is the gate's
own (a `Blocked · action` park with a `needs-action` sentinel), not `Rework Queue`: the
criteria passed, what failed is that no merge under this run certifies the PRD's ship.

## Step 5b: File post-ship audit follow-up issues (manual path)

After the status-flip, queue a **fresh-eyes audit pass** of the feature you just
verified — file **exactly one** `Type:audit` issue for the PRD, carrying one
` <type> <scope>` line per applicable type, per the recipe in
[``](#) →
"Post-ship audit follow-ups":

- **`ux` + `ui`** — only if the PRD touched the UI (same trigger as the Browser
  batch: any `frontend/` file changed, an AC describing user-visible behavior,
  `frontend-plan.md`, `labels: type:ui`, or `ux-design.md`), scoped to the
  journey ID(s) the PRD owns/changed.
- **`security`** — for every code-bearing PRD, scoped to the new surfaces.
- **`authz` / `api`** — additionally, where the PRD touched access-control
  (permissions, projection/narrowing, access profiles, agent keys) or
  added/changed REST/MCP endpoints.

The issue: `Type:audit`, born in **`Triage Queue`** by construction ( /
 — never hand-roll `Implement Queue` or `Backlog`; a no-priority birth
outside the check-gate pair reds the priority rule on every open PR), **no
priority and no project/component placement** (those are `/fleet:check`'s OUTPUT;
the checker releases it to `Implement Queue` with the recipe priority and the
daemon then dispatches ``), **`depends_on` the PRD's tracker
issue**, title `Audit: PRD NNNN — <feature> [<type>, <type>, …]`. The
**description is the full brief** — one ` <type> <scope>` line per
applicable type, each on its own line, ordered `security` → `authz` → `api` →
`ux` → `ui`, plus instructions to run each pass against the shipped feature, file
findings, and **propose the changes** to close them. Name the recipe priority
weight in the body (highest among the types it carries) so the checker has it —
do **not** write it on create. The `Type:audit` label is what makes the eventual
dispatch route to **` <KEY>`** (audit.md §2e). **One issue, not one
per type** — the daemon routes on the label and never parses the type, so several
types in one issue need no daemon change (). If no type applies (a
pure-doc / no-code PRD), file nothing. **File ONLY via**
`file_issue` --command prd:verify --title '…' --type audit --body-file …`
— its birth state is `Triage Queue` and is **not a parameter**; never a raw
`issueCreate`, never a raw state write. Print the filed issue key.
Best-effort: skip silently if the tracker is unreachable.

**Only the manual `/fleet:prd:verify` path runs this step.** The autonomous
`/fleet:prd:implement` run executes only verify Steps 1–4 (Phase B) and skips
Step 5 entirely — it files the equivalent tasks in its own Phase D, so a PRD is
audit-tasked exactly once.

---

## What this command does NOT do

- Doesn't run `make test`, `make lint` or `make build` — pre-commit covers them. (The Browser
  batch DOES exercise the live app, but that is not the same as running the test suite.)
- Doesn't write production feature tests — `/fleet:prd:implement` writes those. Writing/extending a Playwright **probe** to verify an AC is fine; changing component or handler code is not.
- Doesn't fix bugs — if a criterion is **missing**, the user re-runs `/fleet:prd:implement`; if it's **broken**, `/fleet:bug:fix` (reproduce-first). Either way the fix happens outside this command.
- Doesn't replace human review — it's a structured pre-review checklist that includes a real browser pass for any UI work.
- Doesn't re-run the acceptance-criteria audit against a PRD already `status: verified` — Step 0 routes that to a bounded ship-only retry instead (see "Status gate").

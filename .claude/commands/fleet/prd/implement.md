#  Implement

Drive a PRD to completion. **Two modes:**

- **`/fleet:prd:implement NNNN` (default — autonomous):** implement → verify → fix
  every gap → commit on a work branch → open a PR → **hand off to an independent
  `/fleet:prd:verify` session** (Phase D moves the issue to **`Verify Queue`**; it does
  **not** merge — a separate verify session certifies and ships, because the party
  that wrote the code cannot certify it), with no further questions to the user. This
  is the unattended path.
- **`/fleet:prd:implement NNNN --manual`:** step-wise. Backend waves → verify →
  commit → frontend waves → verify → commit, then **stop** at `status:
  implementing` and hand off to `/fleet:prd:verify` + `/fleet:push`. Use this when
  you want to inspect the work before it goes to a PR. Manual mode keeps the
  human proceed-gates that autonomous mode skips.

> **Your role: COORDINATOR.** You orchestrate, not implement. You parse plans,
> group tasks into waves, dispatch sub-agents for all actual editing/building/
> testing, and gate progression on verification. You do **not** edit source
> files, run build commands, or write tests yourself — those are sub-agent jobs
> (one narrow exception: ≤3-line mechanical fixes, per the process contract §1).
> The only side-effects you perform directly are PRD status updates, per-wave
> commits, the autonomous-mode decisions log, and coordination output.

> **Don't faithfully build the weaker thing** (truth-seeking golden rule). Executing the
> approved plan is the job, but if implementation surfaces that the design/plan takes a
> materially worse path than a clearly better alternative, do not silently build the weaker
> one: record it in the Autonomous Decisions Log (and under `--manual`, raise it before
> proceeding). A better technical solution beats faithfully shipping a worse one. This is not
> license to expand scope — genuinely out-of-scope findings are still *tracked, not absorbed*,
> per autonomous-drive.md Rule G.

> **Read these first:**
> 1. **Autonomous mode obeys [`../../../process/autonomous-drive.md`](../../../process/autonomous-drive.md) (Rules A–G + decisions log + push ship terminal + flow-retro) — loaded first.**
> 2. [`../../../process/implementation.md`](../../../process/implementation.md) — authority for the coordinator/sub-agent split, codegen ownership, the per-wave commit loop, the FAST/aggregate verification model, reading results from files (not stale tee logs), feeding sub-agent gotchas forward, untested integration seams, `make dev` contention, and coordinator self-correction. This command's machinery defers to it; where they overlap, the process contract wins.

---

> # 🛑 BUG-FIX DISCIPLINE — NON-NEGOTIABLE. THE SINGLE BIGGEST LEVER ON QUALITY.
>
> **EVERY bug you find — at ANY stage of this command — MUST be remediated through the `/fleet:bug:fix` TDD discipline ([`../`](#)). No exceptions.**
>
> This means: a test failure, a regression, a crash, a console error, a panic, a wrong return value, a flaky test, a broken interaction, a gate/lint surfacing a real defect, a browser probe finding something that rendered-but-didn't-work — discovered during **implementation, verification, testing, browser probes, gate runs, coverage audits, or anywhere else** — is routed through the fix discipline:
>
> 1. **Reproduce the broken behavior as a FAILING test/probe — confirm it's RED.** Capture the red output.
> 2. **Fix the ROOT CAUSE, never the symptom.** Trace the data flow; find why it breaks.
> 3. **Confirm the SAME test turns GREEN.** Capture the green output.
>
> **Banned:** symptom-patching, "just make it pass", deleting/loosening the failing assertion, widening a tolerance, skipping the red phase, or "I'll note it and move on". A bug that is patched without a reproducing test is treated as **not fixed** — and shipping it is a quality defect in itself.
>
> The ONLY thing exempt from reproduce-first is *unfinished* implementation — behavior that was never written yet (just finish writing it, test-first per the wave template). The moment code that *should* work doesn't, it is a bug → `/fleet:bug:fix` discipline. When unsure which it is, treat it as a bug.
>
> **Out-of-scope findings are TRACKED, not absorbed (autonomous-drive.md Rule G).** If you discover a bug or important issue that is outside this PRD's scope: out-of-scope bug → `/fleet:bug:create` (Fleet `file_issue` kind bug); important follow-up task → `/fleet:task:create`; log it in the Autonomous Decisions Log; NEVER fix it inline. **If the Fleet tools refuse the filing or a handoff move, end this run `failed`** — name the follow-up and the refusal; do not carry on as if it were done. Keep the PRD scope tight.
>
> **In autonomous (default) mode this matters even more:** the eventual ship rides **green CI with no human reading the diff** — the independent `/fleet:prd:verify` session certifies acceptance criteria and then `/fleet:push ship` auto-merges. CI catches build/lint/test breaks and verify checks the acceptance criteria, but neither reliably catches a plausible-but-wrong symptom-patch buried in a passing implementation — so reproduce-first is the ONLY thing standing between a symptom-patch and shipped-broken code. A verify gap may NOT be flipped to PASS without red→green evidence (Phase C).

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. Under `--manual` the run stops after Phase A; autonomous continues B→D. A `loop` that exhausts its rounds, or the Phase-D merge `gate` withholding (Rule D), stays an open todo with its residual noted. The prose Phases below are the authority; this spine indexes them.

```json
{
  "command": "prd-implement",
  "tier": "core",
  "intent": "Drive a PRD to a green, verify-ready PR — autonomous by default (implement -> verify -> fix -> open PR -> hand to an independent /fleet:prd:verify session, which ships); does NOT self-merge; --manual stops after Phase A.",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "loads": ["process-envelope", "process-implementation", "languages", "planning-model"],
  "requires": [
    "process-spine", "process-envelope", "process-implementation", "gate", "git-workflow",
    "languages", "planning-model", "dev-environment", "file-conventions", "tracker-identity", "registers-triage-partition", "process-issue-shape", "process-interview"
  ],
  "optional": [
    "process-feature-reconcile", "codegen", "ui-contracts", "feature-maps", "audit-profile",
    "runtime-contracts", "entity-model", "process-design-fidelity", "api-contract", "permissions",
    "domain-model", "commitments", "feature-areas", "components", "retro-corpus", "docs"
  ],
  "steps": [
    {"id": "determine-mode",    "name": "Determine mode + parse input",             "kind": "decision", "actor": "coordinator", "consumes": ["prd", "design", "backend-plan", "frontend-plan", "ux-design"], "body": "determine-mode"},
    {"id": "negative-controls", "name": "Negative controls — watch each new test fail", "kind": "gate", "actor": "coordinator", "gate": "hard", "critique": "negative-control", "produces": ["tests"], "body": "negative-controls-watch-each-new-test-fail"},
    {"id": "flip-implementing", "name": "Flip status to implementing",              "kind": "io",       "actor": "coordinator", "produces": ["status", "linear-issue"], "body": "flip-prd-status-to-implementing"},
    {"id": "ensure-branch",     "name": "Ensure a work branch",                     "kind": "io",       "actor": "coordinator",                                  "body": "ensure-a-work-branch"},
    {"id": "resume-ledger",     "name": "Resume from the branch's own ledger (wave commits)", "kind": "decision", "actor": "coordinator",                   "body": "resume-from-the-branch-s-own-ledger"},
    {"id": "rework-entry",      "name": "Rework entry — read the verifier's open rows", "kind": "decision", "actor": "coordinator",                                  "body": "rework-entry"},
    {"id": "collision-check",   "name": "Pre-flight collision check (replace/coexist)", "kind": "decision", "actor": "coordinator",                              "body": "pre-flight-collision-check"},
    {"id": "parse-plans",       "name": "Parse both plans",                         "kind": "author",   "actor": "coordinator", "consumes": ["backend-plan", "frontend-plan"], "body": "parse-both-plans-and-report"},
    {"id": "backend-waves",     "name": "Backend implementation waves",             "kind": "fanout",   "actor": "subagent", "model": "sonnet",                  "body": "backend-implementation"},
    {"id": "frontend-waves",    "name": "Frontend implementation waves",            "kind": "fanout",   "actor": "subagent", "model": "sonnet",                  "body": "frontend-implementation"},
    {"id": "fidelity-loop",     "name": "Design-fidelity build loop (A2d Stage 3)", "kind": "loop",     "actor": "coordinator", "critique": "design-fidelity-bar", "loop": {"max_rounds": 4, "exit": "surface clears the design-fidelity bar"}, "produces": ["screenshots", "baseline"], "body": "frontend-implementation"},
    {"id": "verify",            "name": "Verify (autonomous — Phase B)",            "kind": "fanout",   "actor": "subagent", "model": "sonnet",                  "body": "phase-b-verify"},
    {"id": "fix-loop",          "name": "Fix loop (autonomous — Phase C)",          "kind": "loop",     "actor": "coordinator", "loop": {"max_rounds": 3, "exit": "all verify rows PASS"}, "body": "phase-c-fix-loop"},
    {"id": "rework-reproof",    "name": "Rework re-proof — re-run the verifier's cited evidence for every open row", "kind": "gate", "actor": "coordinator", "gate": "hard", "body": "d0-rework-re-proof-gate"},
    {"id": "handoff-gate",      "name": "Commit, open PR, hand off to verify",      "kind": "gate", "actor": "coordinator", "gate": "hard", "produces": ["linear-issue"], "body": "phase-d-commit-open-pr-hand-off-to-verify"}
  ]
}
```

---

## CRITICAL RULES (both modes)

0. **Continue an existing PR — never open a second one.** Before dispatching any implementation, check whether this PRD's tracker issue already has an open PR: `gh pr list --search "<KEY>" --state open --json number,headRefName,url`. If one exists, `git fetch origin && git checkout <headRefName>`, reconcile with `main` (`git merge origin/main --no-edit`), and **CONTINUE that branch through Step A0.2** — the branch's wave commits say which waves landed, and the run resumes at the first one missing; never re-derive from the diff what the log already says. Drive its CI green and push to the same PR. A re-run/retry MUST build on the work already pushed; a second PR for the same issue is forbidden. Start fresh only when there is genuinely no open PR.
1. **You are the coordinator — and you stay the coordinator even when sub-agents drop.** Every code edit, file write, and feature-test run must be performed by a sub-agent launched via the `Agent` tool. If you find yourself reaching for `Edit`, `Write`, or `Bash` to modify the codebase, stop — spawn a sub-agent instead. (Reading files for plan parsing IS fine; running the slow gate suites yourself per Rule 11 IS fine; modifying files is NOT.) If a sub-agent keeps hitting socket timeouts on a single task, SPLIT the prompt into 2–3 smaller dispatches; do NOT take over with Edit/Write yourself. **A session-level instruction not to spawn agents does not convert this command into a solo one** — it makes the command **unrunnable**, and the honest response is to stop and say so, never to do the sub-agents' work inline and report the run as complete ([`spine.md`](../../../process/spine.md) → *"`actor: subagent` means a real sub-agent"*).
2. **Sub-agents run on Sonnet.** Every `Agent` tool invocation MUST pass `model: "sonnet"` and `subagent_type: "general-purpose"`. Sonnet parallelizes cheaply; the coordinator (you) stays on the parent model for orchestration judgment.
3. **Maximize parallelism within a wave.** Launch all independent tasks in a wave in a **single message** with multiple `Agent` tool-use blocks so they execute concurrently. Sequential `Agent` calls within a wave are a bug — only fall back to sequential when two tasks touch overlapping files.
4. **Execute in wave order.** All tasks in Wave 1 run first (in parallel). Only after all Wave 1 tasks pass verification do Wave 2 tasks begin.
5. **Verify after every task; route EVERY bug through the `/fleet:bug:fix` discipline (see the banner above — this is load-bearing for quality).** If verification fails, spawn a follow-up sub-agent before moving on. Distinguish two cases: a failure that is merely *unfinished* implementation (the behavior isn't written yet) → just finish implementing it; **any other failure — a regression in previously-green code, a genuine defect in just-written code, a crash, a flaky test, a wrong result — IS A BUG**, and the fix sub-agent MUST follow the reproduce-first discipline in [`../`](#): write a failing test that captures the broken behavior, **confirm it's red (paste the red output)**, fix the **root cause** (never the symptom), **confirm green (paste the green output)**. Symptom-patching a regression is the §7 integration-seam failure mode; reproduce-first is the guard. **A bug remediated without a reproducing test does not count as fixed** — do not let the wave proceed on it.
6. **Contract first.** If the plan has a "Contract" section, execute those tasks before any waves. Contract tasks still run in sub-agents — they are sequential, not coordinator-executed.
7. **Follow CLAUDE.md conventions.** Every sub-agent must be instructed to follow project conventions and read the layer-matching implementation contract first.
8. **No scope creep.** Implement exactly what the plan says. Don't add features, refactor adjacent code, or "improve" things not in the plan.
9. **Use TODOs to stay organized.** The coordinator and every implementation sub-agent must use the todowrite tool to track non-trivial implementation work and keep task status current.
10. **Live-browser verification AND the design-fidelity loop are mandatory for any UI change.** a unit suite mocks the rendering substrate; it is fully green while the page can still crash on load — *and* a page that loads cleanly can still look bad. Phase A2d runs three stages on every implementation that touches `frontend/`: Stage-2 Playwright probe + screenshots (correctness — fails on `console.error`), then **Stage-3 design-fidelity build loop** (taste — fixes each surface to the bar in `design-fidelity-loop.md` §2–§3). Do not skip either; do not commit the frontend phase until the probe passes *and* every new/changed surface has cleared the fidelity bar or had its residual tracked.
11. **Split verification — coordinator runs slow gates, sub-agents stay short.** Implementation sub-agents verify their layer with FAST commands only: the lane's static check on their package, one targeted `make test-one T=<TestName>` run, and the specific analyzer they touched — the contract `slot:languages` names spells all three. The COORDINATOR runs the slow gates (`make lint`, the per-wave commit's pre-commit gate — lint + unit; DB/e2e run in CI) via background bash (`run_in_background: true`), reads result files directly, and dispatches targeted fix sub-agents only on real failures. Symptom of a too-long sub-agent prompt: more than two gate invocations, or "implement + tests + lint + commit" bundled together — the socket WILL drop around 1–2 hr. Split the prompt instead.
12. **Heavy test suites run SERIALLY.** `make test-unit` (`-race`, all packages), `make test-db`, and `make test-e2e` (full stack) MUST be invoked one at a time, never concurrently. Running them in parallel causes race-detector memory pressure, docker-port contention, and mock-LLM queue cross-talk that produces FALSE exit-2 failures looking like real test failures.
13. **Sub-agent task budget — enforce the §12 gate before every dispatch.** Each sub-agent prompt targets <20 min wall time. This is **mechanical, not advisory**: run the pre-dispatch budget guard in [`implementation.md`](../../../process/implementation.md) **§12** on every task before dispatching it — if its file-list is `>4 files` OR spans `>1 layer`, SPLIT it first, then dispatch the pieces. Over-budget tasks are the top recurring cause of socket drops. Never bundle "write code + write tests + run `make lint` + run `make test-unit` + commit" in one agent prompt.

## Autonomous-mode rules (DEFAULT mode only — skipped under `--manual`)

Autonomous mode obeys [`../../../process/autonomous-drive.md`](../../../process/autonomous-drive.md) (Rules A–G + decisions log + push ship terminal + flow-retro) — loaded first.

Key rules at a glance (full text in autonomous-drive.md):
- **A. Never stop to ask** — choose the most defensible default, log it, keep going.
- **B. Log every judgment call** — the Autonomous Decisions Log runs across all phases; surfaced verbatim in the PR body and as the last thing in the final message.
- **C. Open a PR, never push direct to `main`** — all commits land on the deterministic branch (`tracking-and-execution.md` → "Git workflow"); terminal delegates to [`/fleet:push ship`](../push.md).
- **D. Merge only when verify is shippable *and* CI is green** — shippable = all-PASS or pass-with-follow-up (prd:verify Step 4 Path A); any **critical** FAIL/PARTIAL after the fix loop OR a red CI check → withhold and report loudly.
- **E. Bounded fix loop** — Phase C is capped at 3 rounds; a round that closes zero gaps falls through to Rule D's withhold path.
- **F. ATOMIC SHIP** — `status: shipped` is the FINAL commit on the branch, carried into the squash-merge by `/fleet:push ship`. There is NO separate post-merge status write. See Phase D below and autonomous-drive.md Rule F.
- **G. Auto-track out-of-scope findings** — out-of-scope bug → `/fleet:bug:create`; important follow-up → `/fleet:task:create`; logged in the decisions log; NEVER fixed inline (see bug-fix-discipline banner above).

---

## The Autonomous Decisions Log (autonomous mode — load-bearing)

Governed by autonomous-drive.md Rule B. Maintain a single running list from the
moment an autonomous run starts. Seed it empty. Append an entry **every** time
you would otherwise have asked the user:

```
- [<phase>] <the decision point> → CHOSE: <what you picked>. WHY: <one-line rationale>. <Optional: the alternative.>
```

What MUST be logged: a pre-flight symbol collision (Step 0.5) and the resolution
taken; an acceptance criterion with two defensible interpretations and which one
you built/verified against; a cross-plan dependency that wasn't ready and how you
proceeded; a plan file missing and which phase you skipped; a verify FAIL you
judged a false-negative (probe bug, not feature bug) with the evidence; any
sensible default for an under-specified detail; any out-of-scope finding tracked
via `/fleet:bug:create` or `/fleet:task:create` (Rule G). If you genuinely
never made a judgment call, the log reads: `- No autonomous judgment calls were
required; the PRD and plans were fully specified.`

**Record the log as an `implementation-notes` comment** (`comment` kind=`implementation-notes`)
— never a description rewrite (no tool rewrites one;  / G4), and **never under
`## Decision (<date>)`**, which is reserved for a human's answer to a question the fleet
stopped on
([`decision-write-back.md`](../../../process/decision-write-back.md), ).

---

## Step 0: Determine mode + parse input

Inspect `$ARGUMENTS`. If it contains `--manual` (or `manual` / `--step`), run in
**manual** mode; otherwise **autonomous** (default). Strip the flag, then parse
the remainder as a PRD number (e.g. `0016` or `16`).

Find the PRD directory `knowledge/prds/NNNN-<slug>/` and read:
1. `prd.md` — acceptance criteria + context (read frontmatter `status:` first).
2. `design.md` — design decisions.
3. Backend plan files — `backend-plan.md`, plus any numbered splits `backend-plan-2.md`, `backend-plan-3.md`, ... (a split is the executable form of a run-ceiling bust, ; run each in numeric order into one branch).
4. Frontend plan files — `frontend-plan.md`, plus any numbered splits `frontend-plan-2.md`, ... (may not exist for a backend-only PRD).
5. `ux-design.md` — if it exists, for UI specifications.
6. Docs plan — `docs-plan.md`: the pages the design's `## Docs impact` names, one task per page id (present only when `slot:docs` is filled).

**Plan-file family discovery (both modes).** List the PRD directory and treat every
`backend-plan*.md` / `frontend-plan*.md` / `docs-plan*.md` file as part of the plan, in
execution order: the base file (`backend-plan.md`) first, then its numbered splits in
ascending order (`backend-plan-2.md`, `backend-plan-3.md`, ...). `make validate-knowledge`
validates the whole family and the `prd-projection` pass of the fleet's `corpus-sync` loop lists it in reading order; the frontend obligations
(playwright row, approved mockup) apply to every `frontend-plan*.md` member, and the docs
tasks run **after** the code phases (Phase A1c). A PRD with
a split plan is still ONE branch and ONE merge — each plan file is a run into that
branch (prd:plan Step 6.6), not a new PRD.

**A PRD may name the lane it is built in (`lane:`), and then this run happens in THAT lane's
checkout.** A PRD's frontmatter may carry `lane: <name>` () naming a lane the fleet
registers. The `prd-projection` pass then labels the PRD's issue `repo:<lane>` INSTEAD OF the
corpus default, so the daemon dispatches this run into that lane's checkout and **the code and
the PR land in that lane's repository**, not in the repo that owns the PRD's docs. The PRD,
design and plan files stay in the owning corpus; when `knowledge/prds/NNNN-<slug>/` is not in
the checkout you are running in, read them from the corpus that owns them (the checkout the
issue's own description points into). Resolve the lane's repository from the issue's `repo:*`
label (`knowledge/scripts/_repo.py`'s `lane_slug`), never from the current directory's name.

Precondition checks (both modes):
- If `status: stub` or the PRD doesn't exist → cannot run; report that the next move is `/fleet:prd:create NNNN` and stop.
- If no plan file of any family exists (no `backend-plan*.md`, no `frontend-plan*.md` and no `docs-plan*.md`) → report that `/fleet:prd:plan NNNN` must run first and stop.
- **Re-check the plan's stale premises.** For every issue key the plan cites as *deferred / unfixed / blocked*, confirm it is **still open** before building around it (`gh issue`/tracker read, one batch). Plans are written days-to-weeks before they run; in one PRD two of three cited premises had since been **closed**, and the run built compensating scaffolding for bugs that no longer existed. A closed premise → drop the workaround and log the change in the decisions log.
- If `status:` is already `verified`/`shipped` → autonomous mode logs a decisions-log entry and proceeds anyway (re-running is safe). Manual mode warns and asks.

**Dev-stack precondition (capture once, up front).** **Read this checkout's ports the
way `slot:dev-environment` says** — never a default; every checkout and worktree
gets its own. Probe the front end and the API on those ports, and **probe the route
`slot:dev-environment` names and only that route**: a health-looking path that
the API does not register fails in one of two opposite directions — a JSON 404 on a
healthy stack (false "down") or the SPA shell with a 200 on a dead one (false "up").
If the PRD touches a customer-visible surface and the stack is **down**: in **autonomous** mode the coordinator
starts it (`make dev` background, poll health) — never a stop; in **manual** mode
report it and ask the user to start it. Respect [`implementation.md`](../../../process/implementation.md) §8
ordering — `make dev` runs only for the live-browser pass, stopped before any
commit/DB/e2e run.

---

## Phase A — Implement

### Step A0.0: Rework re-entry — read the newest hand-back before doing anything

A PRD can arrive here from **`Rework Queue`**, where the daemon routes on the newest
marker-stamped comment the verify session posted. Read it **before** Step A0:

- **`<!-- linear-agent:gate-registration-rework -->`** — the **mechanical registration lane**
  (). Every acceptance criterion PASSed and nothing conflicts; the carrier PR is
  blocked ONLY by a ship-gate registration gap (a gate-coverage allow-list entry, a CI path
  filter). The daemon normally dispatches this as its own short seat, but if you are a full
  implement session meeting this marker, **do not run the wave pipeline**: make **only** the
  registration edit the brief names (the allow-list entry / the path-filter line), commit and
  push to the PR branch, drive CI green, and hand the issue back to **`Verify Queue`**. The
  edit boundary is the registration file **only** — never product code, tests, or acceptance
  criteria. A registration that needs a product or scope judgement is a done-sentinel
  `needs-decision` park, never a guess.
- **`<!-- linear-agent:conflict-rework -->`** — a conflict-only hand-back; see the conflict
  route in the verify command. A rebase/merge, not a re-implement.
- **`<!-- linear-agent:verify-failed -->`** or an open ledger — a criteria **refutation**: the
  normal full re-entry. Read the OPEN lines and resume per Step A0.2.

A registration-only hand-back is **not a refuted criterion**: it does not count toward the
re-entry cap and it never parks the issue on its own.

### Step A0: Flip PRD status to implementing

Open `prd.md` and update the YAML frontmatter directly (you may edit this file):
- Set `status: implementing`.
- Append `{ state: implementing, at: <>, by: implement }` to `status_history`.

Nothing to do for `` — it is generated on demand, **not committed**, and reads status live from each PRD's frontmatter `status:`.

**Claim on the board (one-way, best-effort) — run it on the flip, do NOT wait for a
commit.** This is now the **only** position a session mirrors live (`/fleet:prd:verify`
no longer writes a position — the daemon owns `Verifying → Done`/`Rework Queue`);
implement-start is what claims the PRD on the shared board *before* any push, so a
concurrent session doesn't double-pick it. **No Fleet tools? Stop.** When the session has
no Fleet tools, stop with: *this command needs the Fleet tools; create a personal key on Fleet's API keys page*. There is no other tracker path — never fall back to a tracker script.
The issue already exists (the fleet's `prd-projection` pass created it after the
PRD/design/plan commits). On a **fleet dispatch** the daemon already claimed it — do **not**
move at start. On a **hand run**, call `move_issue(to: "human-wip")`, then re-read with
`get_issue`; **stop if `levers` shows the issue is already running** on another seat.
Re-read with `get_issue` again before the first push. Use `comment` for the Autonomous
Decisions Log lines that must live on the issue. **If the tools are present but a move
fails transiently, say so in the final report and continue** — never skip the claim
silently, because a silent skip is exactly how a second session double-picks the PRD.
(This flow defers commits into per-wave batches and makes no standalone Step-0 commit, so
claim immediately rather than "after the status-flip commit".)

### Step A0.1: Ensure a work branch (code-bearing — branch + PR, never direct to `main`)

Implementation is code-bearing, so it lands on a branch and ships via a PR
(`../../../../` → "Git workflow"). If HEAD is on `main`/`master`,
ensure the work branch now — and **reuse the branch a previous run already pushed rather than
cutting a fresh one over it**:

```bash
git fetch origin
branch=<slot:git-workflow>          # the PRD branch name the slot gives
if [ "$(git rev-parse --abbrev-ref HEAD)" = "$branch" ]; then
  :                                 # already on our branch (a relaunched turn) — keep local commits
elif git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
  git checkout "$branch"            # the previous run's durable position; A0.2 resumes from its ledger
else
  git checkout -b "$branch" origin/main   # a first run, on a freshly fetched base
fi
```

**A remote branch that already carries this PRD is the run before you, not a stale ref to
discard.** The health ceiling, the four-hour wall and a crash each end a run between
checkpoints; if the next dispatch cuts its branch fresh from `origin/main` over the pushed
one, every wave the previous run committed is silently thrown away and the run re-derives the
plan from zero (). The second arm is the whole of the resume half: with the previous
branch checked out, Step A0.2 reads the ledger it carries and the run continues from the first
missing wave instead of restarting. The first arm is not decorative — a relaunched turn
re-executes this step, and it must leave the waves committed since the checkout in place, so
never force a local branch back to `origin` here.

**The `git fetch` is load-bearing, not hygiene** (`slot:git-workflow`): a branch cut
from whatever this checkout last saw is stale from birth, and where the repo carries
submodules it carries their old gitlinks too — which fails the submodule guard among
`slot:git-workflow` with a message about reverting work this PRD never
touched. The pre-commit guard cannot warn you — it only inspects a gitlink the commit
*changes*, and a stale branch's pointer is unchanged. It is also what makes the
`origin/<branch>` test above trustworthy: without it, the test reads a ref this checkout
may never have fetched.

Resolve the `<key>` **tracker issue key** best-effort from the PRD's tracker issue
(titled `[NNNN] …`); fall back to the documented the tracker-unreachable form if the tracker is
unreachable. All per-wave commits land on this branch. (Autonomous mode: log a
`[Phase A / branch]` decisions-log entry with the branch name.)

### Step A0.2: Resume from the branch's own ledger

**A dispatch that finds work on the branch is a resumption, not a restart.** Implement
sessions die: the box's four-hour wall clock, a turn that ended without its sentinel and
outlived three relaunches, an engine crash, an operator stop. Measured  over the
43 PRDs that passed the verify gate →09-08: **104 implement sessions of 30 minutes
or more ended without a handoff** (median 2.9 h; 42 of them at the 4 h wall), the single
strongest driver of wall-clock from first implement to done (ρ 0.5) and of spend. The daemon
salvages the *code* (`wip(salvage)` + push), but the session's *position* — which waves
landed, what the gate said, what the sub-agents learned — died with it, and the next dispatch
re-derived all of it from a diff. This step makes the position durable by making the git log
carry it (A1b's wave checkpoints) and reading it back here.

1. **Read the ledger.** `git log --format='%H%x09%s%n%b' origin/main..HEAD`. A checkpoint
   commit is one whose subject matches `feat(NNNN, <KEY>): wave (B|F)<n>/<N> — …` (A1b /
   A2b write them; the body carries the wave's task table, the gotchas it learned and the
   decisions it logged). No such commit → nothing to resume (a first run, or a branch cut
   before this convention): fall through to A0.5 and proceed from the plan's start, folding
   whatever the branch already carries as the fleet's resume brief says.
2. **Set the cursor.** The highest checkpointed wave per lane (`B`, `F`) is done; the run
   resumes at the next one. Waves below the cursor are **not** re-dispatched, re-verified or
   re-gated — a checkpoint passed pre-commit (lint + the unit lane) when it landed, and the
   push after it ran CI. Log `[Phase A / resume] resumed at wave B<n> (B1–B<n-1> on branch at
   <sha>)` in the decisions log.
3. **Rebuild the run state from the bodies.** Every `Gotcha:` line in the checkpoint bodies
   goes into `RUN_GOTCHAS` (the list A1b pastes into each sub-agent prompt), every
   `- [<phase>] …` line into the decisions log — so a resumed run's sub-agents start with what
   the previous run's learned, not with "none yet".
4. **A `wip(salvage)` on top is the current wave, partial.** The daemon commits uncommitted
   work as `wip(salvage): …` before it gives up. Treat it as the cursor wave's partial state:
   `git reset --soft HEAD~1` (the fleet's brief says the same), read the staged diff against
   the wave's file list, and dispatch that wave's sub-agents with a `## Already on the branch`
   section naming those files — *finish it*, never redo it. A salvage whose diff lies outside
   the cursor wave's file list is a judgement call: log it, keep the files that belong to a
   later wave staged, and let that wave's sub-agent take them.
5. **Never trust a checkpoint you cannot see.** Each checkpoint sha must be an ancestor of
   HEAD (`git merge-base --is-ancestor`); a subject that claims a wave the tree does not carry
   (a rebase dropped it, a force-push rewrote it) is not a checkpoint — treat that wave as not
   done and say so in the decisions log.

### Step A0.3: Rework entry — the verifier's open rows are the exit test

**A rework dispatch is not a fresh implement: the verifier has already been here, and its
report names exactly what failed.** When the daemon routes a PRD from `Rework Queue` back to
this command, the prior verify session posted its matrix on the tracker issue (verify.md Step
3), and the gate's findings comment lists the **open rows**. Read them before dispatching any
wave and hold them as the run's exit ledger. The run is not done when *you* believe the gaps
are closed; it is done when **the verifier's own cited evidence passes at the new head**.

1. **Detect the rework entry.** `status: implementing` **and** the tracker issue carries a
   prior verification report for this PRD — a `## Verification Report` comment with a FAIL
   verdict, the fleet's `verify-failed` marker, or a `<!-- linear-agent:verify-stop -->`
   findings comment. Read it with `get_issue` (include comments). No prior report → this is
   a first implement: skip this step, log
   `[Phase A0 / rework] no prior verification report — first implement`, and carry on.
2. **Extract every open row and its evidence — verbatim.** For each row the report leaves
   **FAIL / PARTIAL / refuted / `BLOCKED (env)`**, record: the criterion text, the verifier's
   verdict, and **the exact evidence the verifier cited** — the probe command, the named test
   (`path::TestName` or `RUN-NNN` label), the browser probe and screenshot path, and the
   `file:line` mechanism. This is the **rework ledger** (`REWORK_LEDGER`): the rows you must
   close, and the assertions you must re-run before handing back to `Verify Queue`.
3. **The verifier's evidence is the assertion, not yours.** Do not substitute a different
   test, a fresh probe, or a code-reading for one the verifier cited: a re-run of *your* own
   evidence proves your fix works by your own definition, which is the self-certification the
   verify gate exists to prevent. When the cited evidence genuinely cannot be re-run as
   written (the probe was removed, the test renamed), say so in the decisions log and repair
   the citation so the row still re-proves — never silently swap it for weaker proof.
4. **A row that still fails keeps the run working.** Handing back on the assertion that a row
   is closed is the defect this step exists to stop: **83% of PRD rework loops re-fail a row
   that had already failed once** (107 loop pairs, ..09-26). If any `REWORK_LEDGER`
   row's cited evidence still fails at the new head, it is a gap under Phase C — triage it and
   keep going, or, when the fix loop is exhausted, take the D-withhold path. Never a handoff —
   a still-failing row keeps the run working, it does not go back to `Verify Queue`.

### Step A0.5: Pre-flight collision check (mandatory — read-only)

Before dispatching Wave A, grep the new entity's named symbols against the current
tree. A silent collision (a vestigial table, an existing type, a query name
already used by retired code) discovered mid-foundation costs hours of unwind.

From the design + plan, extract every new named symbol and grep for it where that kind
of symbol lives — `slot:file-conventions` and `slot:codegen` say where:
- **Storage entities** — in the schema source.
- **Domain types** — in the typed-identifier package and the generated models.
- **Query names** — in the query sources.
- **API operation ids** — in the API contract `slot:api-contract` names.
- **Permission constants** — where `slot:permissions` keeps them.
- **Audit categories / event names** if the PRD introduces any.

If ANY collision exists:
- **Manual mode:** STOP and ask the user via `AskUserQuestion`, framing crisply — (A) **Replace legacy** (new migration drops the vestigial entity, recreates per the PRD) vs (B) **Coexist under a new name** (`.<x>_v2`, `<X>V2ID`). Do NOT silently pick.
- **Autonomous mode:** do NOT ask — pick the most defensible resolution and log it. If the colliding entity is clearly vestigial *and* the PRD's design explicitly redefines it → **replace-legacy**. If the legacy entity has any live caller, or the PRD doesn't clearly supersede it → **coexist under a non-colliding name**. Append a `[Phase A / collision]` decisions-log entry and record the resolution in your task list before dispatching Wave A.

If zero collisions, log "no collisions detected" and proceed.

### Step A1: Parse both plans and report

Extract from each plan file: **Contract tasks** (run first, sequentially), **Waves**
(grouped by number), **Dependencies** (verify the graph). For a split plan family, parse
each member file in execution order (base → numbered splits) and report them as
consecutive runs into the same branch. Report the full
execution plan:

```
## Implementation Plan: PRD NNNN — <feature name>

### Backend Plan
**Plan files:** backend-plan.md, backend-plan-2.md, ... (<N> runs)
**Contract tasks:** <N> (sequential)
**Wave 1:** <N> tasks (parallel)  ...
**Backend total:** <N> tasks

### Frontend Plan
**Contract tasks:** <N> (sequential)
**Wave 1:** <N> tasks (parallel)  ...
**Frontend total:** <N> tasks

### Execution Order
1. Backend: contract → waves → verify → commit (per plan file, in numeric order)
2. Frontend: contract → waves → verify → commit

**Cross-plan dependencies:** <any frontend tasks that need backend output>
```

- **Manual mode:** wait for the built-in `question` response before executing.
- **Autonomous mode:** report the plan, then **proceed immediately** (Rule A — no proceed-gate).

### Phase A1: Backend implementation

When the backend plan is split across multiple files (`backend-plan.md`,
`backend-plan-2.md`, ...), execute them in numeric order as **consecutive runs into the
same branch** — each file's contract → waves → verify → commit completes before the next
file's begins (they build on each other; a later split assumes the earlier ones landed).
Contract tasks that belong to the split's *first* file (the plan-wide contract, e.g. the
OpenAPI/codegen surface) run before all files' waves.

#### A1a: Execute contract tasks (if any)

Dispatch each contract task to a sub-agent **sequentially** (they often depend on
each other). `model: "sonnet"`, `subagent_type: "general-purpose"`. Verify each
before the next.

#### A1b: Execute backend waves

For each wave (Wave 1 first): launch all sub-agents for the wave in a **single
message** with multiple `Agent` blocks. Required params on every invocation:
`subagent_type: "general-purpose"`, `model: "sonnet"`, a short `description`
(e.g. `"B2: jobs handler"`), and the prompt template below.

Prompt template:

```
Implement this task for the repository you are running in — read its CLAUDE.md first.

## Task
<full task description from the plan>

## Files to modify
<file list from the task>

## Context
- PRD: <path> (read for requirements context)
- Design: <path> (read for design decisions)

## Conventions & lint contract (load-bearing — do this FIRST)
**Before writing any code, read BOTH:**
- `../../../process/implementation.md` — shared process (codegen is the coordinator's job; the FAST-only verification you run; the report format).
- the contract for THIS task's lane — the one `slot:languages` names for it. Read only the one that matches. (Python tasks also read ``; agent-runtime tasks also read ``.)

These are the canonical lint + coding-standards contract (baseline policy, the four-places-in-lockstep enum rule, sqlc go_type overrides, typed-ID constructors, the OpenAPI new-op checklist, handler/test conventions, runtime/schema/config conventions, and the frontend eslint + i18n chain). Violations fail CI and force multi-cycle rework. Also follow CLAUDE.md.

## Gotchas already learned this run (don't repeat these)
<RUN_GOTCHAS — coordinator pastes the current Run-Gotchas list here; "none yet" on the first wave>

## Organization
You MUST use the todowrite tool to track this task if it involves multiple implementation steps.

## Tests Required (test-first for behavioral work — red before green)
<test deliverables from the task's **Tests:** field>

You MUST write these tests as part of this task. For any **behavioral** deliverable (an endpoint shape/status, a 403 denial, a projection narrowing, an SSE payload, a state transition), write the test FIRST, run it, and confirm it **fails for the right reason** BEFORE implementing — then implement until it passes. Capture the failing output and the passing output; report both. (Pure mechanical tasks — a rename, a wiring edit, codegen-source-only changes — are exempt: write the test alongside and note "mechanical, no red phase".)

## If you hit a BUG (load-bearing — quality lever)
If you break something that was working, or discover an existing defect (a failing test that isn't yours, a crash, a wrong result), do NOT symptom-patch and do NOT silently work around it. Apply the `/fleet:bug:fix` discipline (`.claude/commands//`): write a test that **reproduces the broken behavior and runs RED**, fix the **root cause** (not the symptom), confirm the **same test runs GREEN**, and report both outputs. If the bug is outside your task's scope, STOP and report it to the coordinator rather than patching around it — the coordinator will track it via `/fleet:bug:create` or `/fleet:task:create` (autonomous-drive.md Rule G).

## Verification (FAST commands only)
After implementing, run ONLY the fast commands from the contract's "Verification you run yourself":
1. The lane's static check on your package — must be clean.
2. `make test-one T=<TestName>` on your new test — ONE targeted run.
3. The SINGLE analyzer your code can trip (the one matching what you wrote).

**Do NOT run any `make generate`, `make lint`, `make test-unit`, `make test-db`, or `make test-e2e`.** Codegen and the slow gates are the coordinator's job. Edit the source (whatever `slot:codegen` names) and stop — the coordinator runs `make generate` afterward.

**Target wall time: <20 min total.** If your task would need a `make generate` / `make test-e2e` run, span >4 files, or cross more than one layer, STOP and report — the coordinator will split it.

Report back with: (1) what you implemented; (2) tests written (files + count); (3) **red→green evidence** per behavioral test (failing output, then passing output), or "mechanical, no red phase"; (4) verification results per command; (5) issues encountered; (6) **gotchas to propagate** — what the NEXT sub-agent should know (lints tripped + fixes, a shared file/symbol/signature you changed, a file you had to touch outside your list, an assumption that turned out wrong), or "none".
```

**After each wave:** collect results. (1) Fold each agent's "Gotchas to propagate"
into the **Run-Gotchas list** (cap ~10, deduped) and paste it into the
`<RUN_GOTCHAS>` slot of every subsequent prompt (§6). (2) **If any verification
failed because of a bug** (not merely unfinished work), dispatch a fix sub-agent
following the `/fleet:bug:fix` reproduce-first discipline before proceeding. (3) Run
the per-wave coordinator gate and **commit the wave** (A1d/A1e) — committing after
each green wave keeps the pre-commit unit gate tight and localizes failures to
their wave (DB + e2e run in CI on push); do NOT batch all waves into one
end-of-phase commit.

Wave completion report:

```
## Backend Wave <N> Complete
| Task | Status | Notes |
|------|--------|-------|
| B1: <name> | Pass | ... |
```

**Wave checkpoint — commit the wave the moment its table is all-Pass, and hold the push for the final one.** Dispatch a commit sub-agent running the commit contract in [`../push.md`](../push.md) → "Commit contract" (stage all, pre-commit, fix every failing hook, never loosen, verify HEAD moved). **Do NOT `git push` per wave.** Pushing on every wave is what makes the run push while its own CI is in flight: with a lane's CI running tens of minutes and waves landing every ~20, a per-wave push cancels the previous run each time (129 cancelled runs over 1.46 days, ~16% of all PR runner time — the  research this rule comes from). The **commit** is the durable checkpoint Step A0.2 resumes from; the **push** is batched, with the flow-retro and any notes/salvage, into the single final push at Phase D's `/fleet:push`. Push earlier only to fix a red check, to clear a conflict, or as the once-per-phase durability snapshot A1d takes before its gate — never per wave, and never while that PR's CI is in flight ([`../push.md`](../push.md) Step 3). Subject and body are the ledger Step A0.2 reads, so their shape is fixed:

```
feat(NNNN, <KEY>): wave B<n>/<N> — <short wave name>

| Task | Status | Notes |
|------|--------|-------|
| B3: <name> | Pass | ... |

Gotcha: <one line per gotcha this wave taught — verbatim what RUN_GOTCHAS gained>
- [Phase A1 / B3] <every decisions-log entry made since the previous checkpoint>
```

Declare the hook wait first the way the mission says (pre-commit on a cold cache is
minutes of silence). The cost is one gate run per wave; what it buys is that a session
death costs one wave, not the run — 42 of the 104 measured deaths were at the 4 h wall
with everything since the last commit lost to a salvage snapshot the next run had to
reverse-engineer. Waves below the cursor are never re-committed; a resumed run's first
checkpoint is the wave it resumed at.

#### A1c: Backend test coverage audit

After all backend waves, inventory new code from the plan's file lists. For each
new source `.go`, verify a corresponding `_test.go` exists; flag any exported
function with zero test references. Launch parallel sub-agents (one per package)
to write missing tests, each running its OWN package's targeted `go test`. Then
the COORDINATOR runs the coverage gate via background bash:

```bash
cd "$(git rev-parse --show-toplevel)"; make coverage > logs/coverage.log 2>&1
```

#### A1d: Backend final verification (COORDINATOR runs the gates)

**The gate is generate + build + lint — NOT the test suites.** Per
[`implementation.md`](../../../process/implementation.md) §4, the **commit's pre-commit hook
runs lint plus the unit lane** (`slot:gate` names what it runs and how long it
takes); the **integration and end-to-end lanes run in CI** (`slot:gate`). So
the coordinator does NOT hand-run `make test-unit` where the repo's answer says it carries
a race detector, nor `make test-db`, nor `make test-e2e` locally. Run codegen +
build + lint-fix + lint, fix all lints, then commit (pre-commit runs the unit lane) and
**push so CI runs the rest** — that is the authoritative integration gate now.

**Durability push — put the branch's checkpoints on `origin` BEFORE the gate starts.** The
wave commits (A1b) are local, and the gate below (`make generate` / `build` / `lint`) can run
for tens of minutes; a health ceiling or the four-hour wall can end the run inside it, and a
run whose only copy of its work is a worktree restarts from zero (). So push once,
before the gate, as a durability snapshot — not the handoff:

```bash
git push --force-with-lease -u origin HEAD
```

This does not break A1b's "no per-wave push" rule: it runs **once per phase, before any PR
exists**, so `pull_request` CI has not started and nothing is cancelled. It is the exception
A1b names. On a rework entry a PR may already be open and its checks in flight — then the
branch already has a remote copy and A0.2 resumed you from it, so this push is unnecessary;
wait per [`../push.md`](../push.md) Step 3 rather than cancelling the run. The final PR
push at Phase D still carries the retro, notes and salvage.

Run via background bash, read exit codes, and on a non-zero `LINT_EXIT` **read
``** (the full aggregated failure set — `make lint` no longer
fail-fasts):

```bash
cd "$(git rev-parse --show-toplevel)"; {
  echo "### GENERATE ###"; make generate;  echo "GENERATE_EXIT=$?"
  echo "### BUILD ###";    make build;          echo "BUILD_EXIT=$?"
  echo "### LINT-FIX ###"; make lint-fix;       echo "LINTFIX_EXIT=$?"
  echo "### LINT ###";     make lint;           echo "LINT_EXIT=$?"
  echo "### DONE ###"
} > logs/gate.log 2>&1
```

Where the repo's `make lint-fix` answer names a cascading mode (a retype that may stop
the tree compiling until the surfaced type errors are resolved), run it, resolve those errors
(often via a fix sub-agent) and re-run. For any failure:
dispatch a targeted FIX sub-agent with the exact `file:line` + message (or apply a
≤3-line mechanical fix directly per §1). Then re-run the gate once. Do NOT
`ls -t` a tee log (§5). Never run `make dev` while a commit / DB / e2e run is in
flight (§8).

#### A1e: Backend commit

The waves are already on the branch, one checkpoint each (A1b). What this commit carries
is the residual — the coverage tests A1c wrote and the gate fixes A1d made. Dispatch a
commit sub-agent (`model: "sonnet"`, `subagent_type: "general-purpose"`) running the
**commit contract in [`../push.md`](../push.md) → "Commit contract"** (stage all, run
pre-commit, fix every failing hook, never loosen, and **verify HEAD moved**), then push.
Commit message: `feat(NNNN, <KEY>): backend — coverage + gate` (include the `<KEY>` tracker
issue key when known; omit if none resolved); skip the commit when A1c/A1d changed nothing.
Treat the sub-agent's returned **verified SHA** as the source of truth — the coordinator
must NOT separately claim "committed" from a streamed log line (§4b). Do not proceed
until the commit reports success.

### Phase A2: Frontend implementation

Same patterns as Phase A1, for `frontend/` (a split frontend family executes in numeric
order, exactly as the backend family does):
- **A2a** contract tasks (sequential), **A2b** waves (parallel; the frontend prompt also includes `UX Design: <path>` if `ux-design.md` exists and `Design System: `) — **each wave committed exactly as A1b's backend waves are** (local checkpoint, push held for the final push), subject `feat(NNNN, <KEY>): wave F<n>/<N> — <name>`, and resumed from by Step A0.2 — **A2c** coverage audit (`.tsx`/`.ts` sources, `.test.tsx`/`.test.ts` tests; run `cd frontend/apps/web && npm test -- --run`).
- **A2d Frontend final verification — THREE stages, all required** (a unit suite mocks the rendering substrate, so a green unit suite can hide a crashing page; and a page that loads cleanly can still look bad):
  - **Stage 1 (COORDINATOR, background bash):** `make generate`, **`make typecheck`** (load-bearing; a unit suite does NOT type-check), `make test-unit` for the frontend lane, `make lint`. Push the phase's checkpoints first — the same once-per-phase durability push A1d takes before its gate, so a health-ceiling death inside these long gates leaves the frontend waves on `origin` rather than only in the worktree (). On failure dispatch a targeted fix sub-agent. Then dispatch one small read-only sub-agent to spot-check new/modified components against the UI contract `slot:ui-contracts` names.
  - **Stage 2 — Live-browser verification (REQUIRED, do not skip).** Trigger: any UI change at all. Dispatch a browser-verification sub-agent that confirms the dev stack is up (`slot:dev-environment` + `slot:dev-environment` — never a default port or a health-looking path the API does not register; if down → autonomous coordinator starts `make dev-headless`, manual reports back), then for each UI surface this PRD added/changed extends or creates a probe in the harness `slot:dev-environment` names that navigates, waits for an AC-relevant element, screenshots to the harness's screenshot directory (`NNNN-<surface>.png`, exercises each user-visible AC, and **fails loudly on `console.error` / uncaught exceptions**. If it reports failures, the fix follows the `/fleet:bug:fix` reproduce-first discipline (turn the failure into a red probe assertion → root-cause fix → green) before re-running. Do not advance to Stage 3 until the probe passes with screenshots: Stage 3 grades *taste*, and it is pointless on a page that is still functionally broken.
  - **Stage 3 — Design-fidelity build loop (REQUIRED for any new/changed UI surface — this is what stops "functional but looks bad").** A page that passes Stages 1–2 is *correct*, not *good* — Stage 2 fails on `console.error`, never on ugliness. Stage 3 fixes each surface **to the design-fidelity bar during the build**, not once at the end. Run the loop in [`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §3, coordinator-orchestrated like the Phase-C fix loop (`MAX_LOOP = 4`, per surface):
    1. Dispatch the browser sub-agent to render each surface at **1440** in every meaningful state (empty / loading / error / populated) against real seed data, screenshot each, and **critique** the screenshots against, in priority order: **(a) the APPROVED MOCKUP** — read `ux-design.md` → `## Approved design` for the fixture route, run its fidelity spec (`slot:ui-contracts` names the harness) (or navigate the `DEV` route) to capture the mockup's own screenshots, and **hand those images to the critique agent as the primary target**; **(b) the named reference** (`design-fidelity-loop.md` §1, `mockups/reference-<archetype>.png`); and **(c) the bar** (§2: `Q1–Q6`, surface hierarchy, one primary action, scale discipline, holistic "would a designer ship this?"). It returns a **ranked, concrete** defect list, highest-impact first, with **divergences from the approved mockup ranked above generic taste defects** (*"mockup groups the four stats in one strip; shipped page stacks them in separate cards"*, then *"hero card ~60% empty at 1440"*, *"three type sizes in the header"*) — not "make it nicer".

       **The approved mockup is the primary target, not the reference.** The reference is a third-party surface (the tracker/Stripe) chosen for its craft ceiling; the mockup is the design a human actually signed off on. A loop fed only the reference converges on something defensible that nobody approved — this is the mechanical cause of "the implementation ignored the design", and it is an input-set bug, not a discipline failure. If the PRD genuinely carries **no** approved mockup, that is a **design gap**: log a `[Phase A2d / no-approved-mockup]` decisions-log entry, fall back to reference + `ui-spec.md` archetype exemplars, and flag it in the PR body — do not treat it as normal.

       **The mockup you render is the one in the repo** ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5-0) — the `tests/fidelity/` fixture route, or the committed `mockups/**.html` opened from disk. **You are headless: a hosted artifact URL in `ux-design.md` is not reachable and must never be treated as the target.** If the approval record names only a link, or the named `mockups/reference-<archetype>.png` is absent from disk, you have **no usable fidelity target** — that is the `no-approved-mockup` design gap above, not something to paper over by inferring the design from prose. Log it and flag it; never invent the target.
    2. Dispatch a fix sub-agent for the **single highest-impact defect** (one at a time — a loop converges; a batch of simultaneous edits can't be attributed). Fixes obey `ui-spec.md` / canonical `@/ui`; a fix that reaches for a raw palette/hex or a bespoke shape to "look better" is itself a defect.
    3. Re-render → re-screenshot → re-critique. Exit when the critique clears the bar, a round fixes zero defects, or `round == MAX_LOOP`.
    - **Never loosen the bar to exit** (the aesthetic analogue of never loosening a failing assertion). If a surface can't clear the bar in `MAX_LOOP` rounds, the approved mockup/reference under-specified it — that's a **design** gap: record it (autonomous: `[Phase A2d / fidelity-residual]` decisions-log entry; manual: raise it) and file a `` or `/fleet:task:create` follow-up. Ship correct-and-tracked, never bad-and-silent.
    - **Commit the visual-regression baseline** (§4) for each surface that clears the bar: the browser sub-agent writes a Playwright `toHaveScreenshot()` baseline PNG capturing the good state (config defaults in `` make it deterministic; mask dynamic regions). CI diffs against it thereafter. Baseline only the PRD's own surfaces; log which got baselines and which were skipped and why. Do not commit the frontend phase until every new/changed surface has cleared the bar or had its residual tracked.
- **A2e Frontend commit:** same as A1e — the waves are already checkpointed, so this carries the residual (A2c coverage, A2d gate fixes, the Stage-3 baseline PNGs); message `feat(NNNN, <KEY>): frontend — coverage + fidelity + gate`; skip when nothing changed after the last wave checkpoint.

### Phase A1c: Docs implementation

When `docs-plan.md` exists, execute it **after** the code phases and into the **same branch** —
a page describes what shipped, so it is written against the built result, never ahead of it. One
task per page id:

- **Write the page** in the home `slot:docs` names, exactly to the slot's page contract.
- **Set the capability map's `Documented in` cell** for the documented capability in the
  feature capability map (`slot:feature-maps`) — the loop-closing edit, alongside
  `Ships in` / `Tested by`.
- **Run the generated-reference target** `slot:docs` names and commit its output when the home
  is generated; never hand-edit generated docs.
- **Commit** `docs(NNNN, <KEY>): pages — <ids>`.

When `docs-plan.md` is absent because the repository leaves `slot:docs` unfilled, log one
`[Phase A / docs]` entry saying the slot is unfilled and there is nothing to write — the absence
is the slot's degrade, not a skipped step. Never infer a docs home.

---

## Manual mode — STOP here

If running under `--manual`, Phase A is the whole job. After both commits:

```
## Implementation Complete: PRD NNNN — <feature name>   (manual)

### Backend — Commit: <hash> · <N>/<N> tasks · <N> tests · build/lint PASS
### Frontend — Commit: <hash> · <N>/<N> tasks · <N> tests · npm test/lint PASS · browser probe PASS (screenshots)
### PRD status: implementing (code-complete)

**Next step:** `/fleet:prd:verify NNNN` to audit acceptance criteria and flip to `verified`, then `/fleet:push` (open the PR) or `/fleet:push ship` (open + auto-merge on green CI) to land on `main` and flip `status: shipped` atomically (autonomous-drive.md Rule F).
```

Then go to **Flow retrospective** (mandatory, below) and stop. Do **not** run
Phases B–D in manual mode.

---

## Negative controls — watch each new test fail

**A test nobody has watched fail is not evidence.** For every test this run writes, record
the mutation that makes it red and the proof it went red. Two shipped incidents arrived at
this independently and neither made it into a command until now:

- **** — three security/invariant tests that passed with their invariant deleted. The
  fix's own method is the technique: *"verified by temporarily reintroducing the 
  regression and confirming the new test (and not the old one) catches it."*
- **** — a fail-open containment control whose tests were *already failing and saying
  so*, and merged green because the failure was platform-specific. Its rule: **"a test for a
  fail-open control is worth nothing until you have watched it fail."**

**A test that proves a commitment names it.** When the AC a test covers carries a
`**[]**` label rather than `**[local]**` (the two labels
[`prd:plan`](plan.md) Step 6.5 puts on every AC), the test's own name carries the ID with the
punctuation stripped:

```go
func TestPreflightFailsOnMissingCapability_RUN118(t *testing.T)
```
```ts
it("refuses a rate-limited request with a retry time [CC026]", …)
```

One convention, two payoffs, both mechanical: *"show me the code that keeps this promise"*
becomes a grep, and `prd:verify` can report per-commitment instead of per-document — which is
the only way a claimed-but-never-built commitment becomes visible at all. `[local]` ACs name
nothing extra; this applies **only** to the labelled minority. Full model:
[*The claim spine*](#).

For each new test, the authoring sub-agent records in its report:

| Field | Content |
|---|---|
| Test | `path::TestName` |
| Commitment | the `XXX-NNN` it proves, or `local` |
| Mutation | the one-line change that should break it — revert the fix, invert the guard, delete the branch |
| Result | the failure output, pasted |
| Restored | confirmation the mutation was reverted and the test is green again |

**A test whose mutation leaves it green is not a test** — it is asserting something else, or
nothing. Fix the test, not the record. Verify checks these; a criterion whose test has no
negative control comes back PARTIAL.

The cheap traps, all of which produce a green mutation: asserting on a row the test itself
just created (so the current, already-fixed code produces it either way — see
[`implementation.md`](../../../process/implementation.md), /999/1000); asserting a page rendered rather than that it
did the thing; and building the credential/fixture under test locally instead of taking the
one production actually uses.

## Phase B — Verify (autonomous mode)

Execute the full [`/fleet:prd:verify NNNN`](verify.md) flow (Step 1 carve-up → Step 2
parallel reviewers incl. the mandatory Browser batch → Step 3 synthesize → Step 4
verdict), with these autonomous overrides:

1. `status: implementing` is expected after Phase A — no warning needed.
2. **Ambiguous criterion:** pick the interpretation most consistent with the PRD's stated goals + `ux-design.md`, verify against that, and append a `[Phase B / ambiguity]` decisions-log entry. Do not block.
3. **Step 4 verdict — DO NOT STOP on FAIL.** Verify's Step 4 says stop on PARTIAL/FAIL; in autonomous mode you instead **carry the full PASS/PARTIAL/FAIL matrix into Phase C**. Capture per failing row: the criterion text, UI-vs-non-UI tag, the cited `file:line`/probe/screenshot evidence, and what the reviewer said is missing.
4. **Never flip `status: verified` — not here, not in Phase D, not anywhere.** This command cannot certify its own work; `/fleet:prd:verify` stamps it from a separate session. The validator enforces it.

Produce verify's Step-3 synthesis matrix as normal — it's the input to the fix loop.

## Phase C — Fix loop (autonomous mode)

`verify` is read-only and Phase A doesn't consume its verdict — here you close the
loop. Let `round = 0`, `MAX_ROUNDS = 3`.

While the latest verify matrix has any **PARTIAL or FAIL** row and `round < MAX_ROUNDS`:

1. `round += 1`. `log()` the round number and the open gaps.
2. **Triage each open gap** (read-only) into one of three kinds:
   - **Missing feature** (never implemented) → an implement-style fix sub-agent (A1b/A2b template, test-first).
   - **Defect / regression** (present but wrong, or a previously-green criterion broke) → a **fix-discipline** sub-agent following [`../`](#): reproduce red → root-cause fix → green. The load-bearing one.
   - **False negative** (probe bug, flaky mock-LLM leak, resource-contention exit-2) → not a code fix. Fix the probe, then **re-run it and record the pass**. Append a `[Phase C / false-negative]` decisions-log entry with that evidence. **A row may not be reclassified to PASS on the reclassification alone** — the loop that wants to terminate is the same party deciding the failure was not real, which is exactly how a genuine defect exits as a probe bug. If the probe cannot be made to pass, the row stays FAIL and goes to verify as an open gap.
3. **Dispatch fix sub-agents** for the real gaps (Sonnet, FAST verification only; each reads the layer contract in full first). Route by triage kind. For defects/regressions, the row may NOT return to PASS without red→green evidence pasted in the report — this is what stops the autonomous loop from symptom-patching a gap before the merge. Run the §12 budget guard on each fix task; parallelize independent gaps, serialize overlapping-file ones.
4. **Re-run the coordinator-side slow gates** affected by the fixes (backend gates if Go/SQL/OpenAPI changed; Stage-1 unit+lint and Stage-2 live-browser if `frontend/` changed). Fix gate regressions before re-verifying.
5. **Commit the fixes** via a commit sub-agent (commit contract in [`../push.md`](../push.md)). Message: `fix(NNNN): <feature name> — verify-gap remediation (round <round>)`.
6. **Re-verify only the previously-failing area** (not the whole PRD): a tightly-scoped verify sub-agent over just the PARTIAL/FAIL rows (plus anything the fix plausibly regressed). For UI rows the re-verify **must** include a live-browser probe pass. Merge its verdict into the matrix.

Loop exit:
- **All rows PASS *and* the rework re-proof passes** → success → Phase D, push path. On a
  rework entry (Step A0.3) "all rows PASS" is not enough: every `REWORK_LEDGER` row's
  **verifier-cited** evidence must have been re-run at the current head and seen to pass
  (Phase D0). A row that only your own substitute evidence passes is still open.
- **`round == MAX_ROUNDS` with gaps open**, or **a round closed zero gaps** → stop. Append a `[Phase C / unresolved]` entry per still-open gap → Phase D, **withhold path** (Rule D).

### When a gap needs a person — the park is bound to the card

The fix loop never stops on a prompt (Rule G files, Rule D withholds). When a gap genuinely
cannot close without a human ruling — a design fork the PRD does not settle, a requirement
the work would have to break — and the run ends `needs-decision`, the park asks in writing.
It quotes the acceptance criteria and requirements it turns on, because the person answering
has not read this PRD.

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

6. **A mockup, design or any visual reaches the person ONE way: the fleet's `ask` tool with the mockup attached** (`upload_link` the folder, then `attachments: {bundleId, entry}`). Their browser is on their own machine, not on the box you run on: **never** tell them to open a file path, run `python3 -m http.server` or visit `localhost` / `127.0.0.1`, and never carry a mockup question in the built-in `AskUserQuestion`, which has no attachment. The tool answers with a viewer link; put that link whole in what you say. One authority: `.claude/process/interview.md` → *A mockup reaches a person ONE way*.

7. **The person may not be the one who knows — every question can be answered *"I can't
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

## Phase D — Commit, open PR, hand off to verify (autonomous mode)

All work lives on the Phase-A branch. Phase D finalizes the branch, opens a PR, waits for
green CI, and **hands the PRD to `/fleet:prd:verify`. It does not merge.**

> # 🛑 THIS COMMAND DOES NOT SHIP. IT DOES NOT STAMP `verified`.
>
> **The party that wrote the code cannot certify it.** Measured before this rule existed: of
> 267 `verified` stamps, 193 were `by: implement` and 27 `by: implement-verify` — **82%
> self-certified** — against 45 by the verify command. `make validate-knowledge`
> now rejects a `verified` entry stamped by anything but `verify`, so a self-stamp fails the
> commit rather than shipping.
>
> Phase B's matrix is **this run's own reading** of its own work. It is input to the fix
> loop, not a verdict. The verdict comes from a separate session with no stake in the loop
> terminating — which is the whole point, because the loop's incentive is exactly what turned
> a genuine defect into a "false negative" often enough to need a rule.

### D0. Rework re-proof gate (rework entries only — hard precondition to any handoff)

**On a rework entry (Step A0.3), the exit test is the verifier's own evidence, re-run — not
this run's claim that the gaps are closed.** Before D1 (and before any `/fleet:push`), the
coordinator re-runs **every open `REWORK_LEDGER` row's cited evidence at the head being handed
off** — the exact probe, test and browser check the verifier named, nothing substituted — and
records, per row, the command/probe run, the head SHA, and the passing output. The gate passes
**only when every row's cited evidence is observed to pass at that head.** A row whose cited
evidence still fails is a gap: keep working (Phase C) or take the D-withhold path — never D1.
This is the mechanical guard against the measured failure: of 107 consecutive AC-finding loop
pairs on the same PRD, **52% re-failed only on rows that had already failed** and 31% re-failed
those plus new rows — **83% of re-verifies carried a previously failed row**, because the
fixer asserted a finding was closed instead of proving it (median rework cost ~3h, n=242).

- **Re-run at the graded head, not a remembered one.** The evidence is re-run at the commit D2
  will hand off (`git rev-parse HEAD`), not at the head it passed at when the fix landed.
  Record the SHA beside each result.
- **Browser-cited rows are re-run in a live browser.** A probe/screenshot the verifier cited is
  re-run against the dev stack with a fresh screenshot; a code-reading is not a substitute
  (verify.md's browser-batch rule). If the dev stack is down, start it per Step 0's dev-stack
  rule — do not skip the row.
- **The gate output is shown, not asserted.** Paste one line per `REWORK_LEDGER` row into the
  decisions log and the final report — `<criterion> · <cited evidence> · <head SHA> · PASS` —
  and list any that could not be reproduced. A handoff whose re-proof is claimed but not shown
  is not a pass, and the fresh verifier re-runs this same evidence at the same head.
- **The gate does not replace Phase B/C.** It is a second, borrowed assertion set on top of the
  full matrix; the loop still has to reach all-PASS. It only makes the exit honest.
- **Empty `REWORK_LEDGER`** (a first implement, or a rework whose report carried no open rows)
  → nothing to re-prove: say so in the decisions log and proceed.

### D1. Roadmap edits + handoff state (success path only — all rows PASS)

Edit `prd.md` frontmatter **on the work branch** (it merges with the PR):
- **Leave `status: implementing`.** Do not write `verified`; do not write `shipped`. Verify
  stamps `verified` when it has independently confirmed the criteria, and ships from there.
- Nothing to stage for `` — it is generated on demand and **not committed**, and status is read live from the frontmatter flip above. Durable customer-capability content lives in the feature capability maps (`knowledge/features/<area>.md`), not the roadmap — reconcile the owning map there if this PRD changed what a customer can do.

### D1.5. Flow retrospective (mandatory — success AND withhold paths)

Write the run retro to `knowledge/retros/prd/NNNN.md` (`type: retro-prd`,
`owner: prd-NNNN`) per `../../../process/autonomous-drive.md` **§ Flow-retro**.
Author it from this run's history (gate-run count, lint cascades, sub-agent drops,
commit attempts, fix-loop rounds, the Run-Gotchas list, the Autonomous Decisions Log).
Be candid; **record + suggest only — do NOT modify the flow/commands/contracts.** Skim
the 2–3 most recent `` and flag recurring friction. Staged into
the D2 (success) or withhold commit — never blocks shipping.

### D1.6. Run the shared neuter check before the first handoff (every kind)

**Before D2's consolidating commit, run the verifier's own neuter check over the ledger.** The
verifier will re-run it from a fresh session; running it here is the implementer catching the
cheapest high-yield failure while it is still cheap. Of 192 verify rejections in one week,
**30 were a test that stayed green with the fix reverted** — the test was written, the defect
planted, and the guard proved inert. It is one script, `knowledge/scripts/neuter_check.py`,
and `/fleet:prd:verify` calls the same one, so the mechanic has a single copy:

```bash
python3 knowledge/scripts/neuter_check.py --base origin/main --ledger /
```

Build the ledger from the acceptance criteria whose proof is a test: a `tests` entry names the
test's `run` list and the `revert` pathspec of the files the fix landed in (never the test
file); a `scopes` entry names the `pattern` and `paths` of a counted claim. The script runs
each test green→red→green (revert the fix, require the red, restore, require the green, assert
the tree came back), counts every scoped site against the diff, and **exits non-zero on any
test that stayed green, any test not green at HEAD, or any uncovered site**. A non-zero exit is
a refusal to hand off — close the line or defer it with a filed issue; do not proceed to D2.

### D2. Consolidating commit on the work branch

Dispatch a commit sub-agent running the commit contract in [`../push.md`](../push.md):
stage the D1 regenerated roadmap, the `flow-retro.md`, and
anything uncommitted; run pre-commit; fix every hook; commit **to the branch**;
**verify HEAD moved**. Subject: `feat(NNNN, <KEY>): <feature name> — autonomous
implement`. Body: a one-line verify summary (`All N acceptance criteria PASS
(browser-verified)`) + the co-author trailer:

```
Co-Authored-By: <the attribution line this session was given>
```

This SHA is what D3 hands to `/fleet:push ship`. (The full Autonomous Decisions
Log goes in the **PR body** — D3.)

### D3. Open PR, hand to verify (success path only) — via `/fleet:push`

**D0's rework re-proof gate must already have passed — a rework entry never reaches D3 with an
open `REWORK_LEDGER` row.** The handoff is only honest when the verifier's own cited evidence
passes at the head being handed off; a run that cannot show that keeps working or withholds.

**The coordinator does NOT hand-run the push, and does NOT merge.** Delegate to a push
sub-agent running [`/fleet:push`](../push.md) (Sonnet) — the open-PR-and-stop mode, not
`ship`. **In a fleet-dispatched run you do not wait for CI** (~26% of implement and rework
seat-hours went to exactly that): once the PR is open, its head equals the remote ref, and the
checks are dispatched on it, **write the done-sentinel with `status: "checks-pending"`**, `pr`
the PR URL and `verifiedSha` that 40-hex head (its path and keys are named by the dispatch
mission; see [`../../../process/autonomous-drive.md`](../../../process/autonomous-drive.md)
→ *The terminal: `checks-pending`* and *The dispatch envelope*), and stop. Do **not** call
`move_issue` — the service moves the issue to `Verify Queue` when the required checks are green
on that head, or returns it to `Rework Queue` with the red checks, the conflict or the moved head
named. **A human-driven `--manual` run, or a dispatch whose mission does not teach
`checks-pending`, waits for green CI, calls `move_issue(to: "review")` (Verify Queue), then
writes `status: "handed-off"`** as before, and stops. **If a handoff move you make is refused, end this run
`failed`** — name the refusal; do not claim handed-off. **The position move is not the whole
terminal — a run that stops without the sentinel is a run the daemon reads as ended short and
relaunches**, which is the sixteen `prd:implement` give-ups in . The hand-off
into `review` / Verify Queue — your move, or the service's on green checks — is the
handoff: the fleet daemon routes a PRD issue in `review` / Verify Queue to
[`/fleet:prd:verify`](verify.md), which runs with a fresh context, refutes the PASSes, and
ships on an all-PASS or pass-with-follow-up verdict. Hand it: the **verified SHA from
D2** as `SHA`; the **tracker issue key** (`<KEY>` — find related keys with
`search_issues` for `"[NNNN]"` when needed); the **PR body** (`PRD:
knowledge/prds/NNNN-<slug>/prd.md`, a `Refs <KEY>` line (the bare link — **not** a closing keyword, which the implementer's `push` deliberately withholds so only the completing `ship` merge can close; see `push.md` Step 0 / ), a **`## Files` scope manifest** listing every changed path from `git diff --name-only origin/<base>...HEAD` ( — a keyed PR without one fails CI), the verify
summary+matrix, and the **full Autonomous Decisions Log verbatim** under a
`## Autonomous decisions` heading).

**A PRD change authored in `/fleet`'s `commandtree/` is COUPLED — never pin the consuming repo at this PR's head ().** Open the **fleet PR only**; do **not** open the consuming repo's pin-bump PR against this PR's head. Fleet `main` is squash-only, so a pin at a PR head is never reachable (7 of the last 8 pins sat off `main`,  / ), and `/fleet:prd:verify` would then certify a pin that is not on fleet `main`. The pin bump is produced **after** the fleet PR merges, from fleet `main`, by the verifier: it treats the coupled change as two review targets, merges the fleet half first, re-pins `fleet/` to the resulting squash commit, and runs `fleet commands sync --repo .` in the same commit.

**What happens next is the verifier's, not yours — read it so you do not pre-empt it.**
`/fleet:prd:verify`, on an all-PASS or pass-with-follow-up verdict, runs `/fleet:push ship`: it authors the
`status: shipped` commit as the final branch commit (Rule F — atomic ship), waits for CI,
squash-merges on green, and confirms the merge landed; the issue reaches **Done** when the
`prd-projection` pass of the fleet's `corpus-sync` loop projects the `shipped` status from
`main`, within the sync's interval.
None of that is this command's to do. This command's
terminal is the `move_issue(to: "review")` handoff (Verify Queue), and its only "shipped" evidence is a confirmed
`origin/main` SHA that *the verifier* returns — which it never sees, because it has stopped.
**A CI failure on the handoff PR is a withhold, never a force-merge.** The hand-off push is
**one** push — every wave checkpoint, the flow-retro, and any notes/salvage, batched — and it
**rebases onto `origin/main` exactly once, immediately before the push, and only when the PR
reports `CONFLICTING`** (branch protection requires status checks, not an up-to-date branch, so
being merely *behind* is never a reason to rebase). **Never push while that PR's CI is in flight
unless the push fixes a failure** — a push cancels the running checks and wastes their
runner-minutes ([`../push.md`](../push.md) Steps 2–3). A conflict the rebase cannot resolve
mechanically — one that needs a product or scope judgement — is a stop-and-report.

### D4. File post-ship audit follow-up issues (handoff path — at the moment of handoff)

Once D3 has moved the issue to `review` (Verify Queue) on a green PR, queue a **fresh-eyes
audit pass** of the feature as it will ship — file **exactly one** audit issue for the PRD
via Fleet, carrying one ` <type> <scope>` line per applicable
type, per the recipe in
[``](#) →
"Post-ship audit follow-ups":

- **`ux` + `ui`** — only if the PRD touched the UI (any customer-visible surface file
  changed, an AC describing user-visible behavior, a frontend plan, a UI label, or a
  `ux-design.md`), scoped to the journey ID(s) the PRD owns/changed.
- **`security`** — for every code-bearing PRD, scoped to the new surfaces.
- **`authz` / `api`** — additionally, where the PRD touched access-control
  (permissions, projection/narrowing, access profiles, agent keys) or
  added/changed REST/MCP endpoints.

The issue: call `file_issue` with `kind: "audit"`, `command: "prd:implement"`, title
`Audit: PRD NNNN — <feature> [<type>, <type>, …]`, body = the full brief (one
` <type> <scope>` line per applicable type, each on its own line,
ordered `security` → `authz` → `api` → `ux` → `ui`, plus instructions to run each pass
against the shipped feature, file findings, and **propose the changes** to close them;
name the recipe priority weight in the body so the checker has it — do **not** write
priority on create). It lands in **`triage`** (Triage Queue) by construction ( /
 — never hand-roll `Implement Queue` or Backlog). **Wait for
`filing.trackerKey`** — poll `get_issue` / the filing result every 15s, max 10 minutes.
Then `relate(PRD, blocks, audit)` so the audit waits on the PRD. **On timeout**, `comment`
on the PRD naming the owed edge and the filing id, and carry on — never fail the run on a
slow mint. **One issue, not one per type** — the daemon routes on kind and never parses the
type (). If no type applies (a pure-doc / no-code PRD), file nothing.
**Append a `[Phase D / audit-followups]` entry to the Autonomous Decisions Log** naming the
filed issue key and the types it carries. Do this **only on the success path** — a withheld
PRD has not shipped and earns no audit pass.

### D-withhold. Withhold path (any gap open after Phase C, or CI red on the PR)

Do **not** merge, do **not** flip `status: shipped`. Instead: (1) commit any
uncommitted work to the branch (subject `fix(NNNN, <KEY>): <feature name> —
partial; <K> verify gaps unresolved`, body: the decisions log incl. the `[Phase C
/ unresolved]` entries). (2) If a PR was already opened (verify passed but CI then
failed), leave it open so its red checks are visible; otherwise push with
`/fleet:push` (default — open PR for review, do not merge). Status stays
`implementing` (or `verified` if verify passed but CI blocked the merge). (3)
**Write the done-sentinel** so the daemon stops relaunching a run that has already
withheld: `status: "partial"` naming the PR and the open gaps when the work is genuinely
incomplete (another attempt can finish it), or `"failed"` only when you cannot make the
PR's CI pass at all. (4)
Surface the open gaps / red CI checks as the headline of the final report, with
the PR URL.

---

## Final report — autonomous mode (last message)

Print, in this order, so the decisions log is the **last thing read**:

```
## Implement Complete — PRD NNNN: <feature name>

### Result: HANDED OFF ✅ — PR #<n> green, issue in Verify Queue   (or:  PARTIAL — push withheld ⚠️)

### Implementation
- Backend commit: <hash>   (or "skipped — no backend plan")
- Frontend commit: <hash>  (or "skipped — no frontend plan")
- Fix-loop rounds: <round>/<MAX_ROUNDS>, fix commits: <hashes>

### Verification (final pass)
| # | Criterion | UI? | Status | Evidence |
| - | --------- | --- | ------ | -------- |
| 1 | ...       | yes | PASS   | probe `<name>` + `screenshots/NNNN-1.png` |
All <N> criteria PASS, browser-verified.   (or: list the unresolved gaps prominently)

### Rework re-proof (rework entries only — Step A0.3 / D0)
| Open row | Verifier's cited evidence | Head SHA | Result |
| -------- | ------------------------- | -------- | ------ |
| <criterion> | <probe/test/browser check the verifier named> | <sha> | PASS |
Every open REWORK_LEDGER row's cited evidence re-run at the handoff head: all PASS.   (or, on a first implement: "not a rework entry — no prior report")

### Merge
- PR <url> merged to origin/main: <sha>   (success — CI green, auto-merged)
  -- or --
- ⚠️ Merge WITHHELD: <K> gaps unresolved after <round> rounds (or CI red on PR <url>). Work committed to <branch> at <sha>. Re-run /fleet:prd:implement NNNN or address: <gaps / red checks>.

### Post-ship audits filed (success path only)
- <KEY-1 ux · journey>, <KEY-2 ui · journey>, <KEY-3 security · scope>   (or: "none applicable — no-code PRD" / "withheld — none filed")

### PRD status: shipped   (or: verified/implementing — not advanced; gaps open or CI red)

---

## Autonomous decisions
<the full Autonomous Decisions Log, verbatim — every entry, or the "no judgment calls required" line>
```

The `## Autonomous decisions` block is identical to the one in the D2/PR body and
is the final content of your message — nothing after it. **This is about your visible
message only, never the done-sentinel: write the sentinel file (D3, or D-withhold) BEFORE
you print the report.** The daemon decides the run is over from that file, not from this
message, so a run whose last act is the report alone has not finished.

---

## Flow retrospective (mandatory last step — both modes)

If you did not already write it in D1.5 (i.e. manual mode, or autonomous before
reaching D), write the run retrospective to
the **`retro-corpus`** slot's path for a PRD run, owned by that PRD and commit it, per
[`../../../process/autonomous-drive.md`](../../../process/autonomous-drive.md)
**§ Flow-retro**. Author it from this run's history; be candid; **record + suggest only —
do NOT modify the flow/commands/contracts.** Skim the 2–3 most recent
`` and flag anything recurring. Runs on every outcome (pass or
fail); never blocks shipping.

---

## Error handling

- **Sub-agent fails:** read the error, diagnose root cause, dispatch a follow-up sub-agent (Sonnet) with the original task + failure output + your hypothesis. Don't fix it in the coordinator.
- **Verification fails:** dispatch a fix sub-agent, then one to re-verify. If the failure is a bug (not just unfinished code), the fix sub-agent MUST follow the `/fleet:bug:fix` reproduce-first discipline. Its regression check uses the FAST commands / per-wave pre-commit gate, NOT `-race` `make test-unit`.
- **Cross-plan dependency not ready:** note it; manual mode tells the user, autonomous mode logs it and proceeds with what can be done.
- **Merge conflict from parallel agents:** investigate which tasks violated file ownership; dispatch a sub-agent to resolve.
- **Plan file missing:** if any backend `backend-plan*.md` exists, run Phase A1 for the backend family (skip A2 only if no `frontend-plan*.md` exists); if only frontend plan files exist, run A2 only. Report (autonomous: log a `[Phase A / scope]` entry) which phase was skipped. Within a family, execute each plan file in numeric order (base → splits) as its own run into the same branch.

## What autonomous mode does NOT do

- Doesn't push direct to `main` (Rule C) — lands on a work branch, ships via a PR, auto-merges only on green CI; or withholds.
- Doesn't merge broken or unverified code (Rule D) — shippable verify (all-PASS or pass-with-follow-up) AND green CI are both hard preconditions.
- Doesn't merge without CI — a red check is a withhold, never a force-merge.
- Doesn't stop to ask mid-run (Rule A) — a UI PRD with the dev stack down is NOT a stop; the coordinator starts `make dev` itself.
- Doesn't hand a rework back to `Verify Queue` on an assertion — every open `REWORK_LEDGER` row's **verifier-cited** evidence is re-run at the handoff head and must pass (Step A0.3 / D0); a row that still fails keeps the run working or withholds.
- Doesn't claim committed/verified/shipped/merged from a streamed log line — every such claim is backed by a foreground `git` check (§4b); commits and the PR-merge are delegated to the `../push.md` commit contract / `/fleet:push ship` sub-agents that verify the SHA.
- Doesn't flip `status: shipped` after the merge (Rule F) — the shipped transition is a branch commit authored by `/fleet:push ship` before the squash-merge; it rides the merge onto `main` atomically.
- Doesn't edit source, run builds/tests, or write tests in the coordinator; doesn't loosen any lint/coverage/test gate.

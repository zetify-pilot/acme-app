# <!-- home -->Zetify<!-- /home --> Fix — TDD Bug Fix

You are a disciplined debugger that follows a strict Test-Driven Development approach to fixing bugs. You NEVER jump to a fix without first proving the bug exists with a failing test.

> **The best fix at the root, not the easiest patch that goes green** (truth-seeking golden rule). Don't accept the first fix that satisfies the test — or a fix the user proposed — if a better one exists at the root cause. When the obvious patch is narrower or weaker than the right structural fix, say so and argue for the better one; concede fast if the user's call is right. The easiest green is not the goal; the correct fix is.

> **SOP:** the automated subset of this repo's SOP for the same job, where it has one.

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. The two hard gates are the TDD proofs — `red-proof` (the failing test) and `green-proof` (it passes + no regressions); a gate not shown green, or a `count-escalate` that hits ≥3, stays open with its residual noted (Rule D: withhold the handoff) — never silently closed. The prose phases below are the authority; this spine indexes them.

```json
{
  "command": "bug-fix",
  "tier": "core",
  "intent": "TDD bug fix (red → root-cause → green) driven to a GREEN PR handed to an independent /zetify:verify session; does NOT self-merge; autonomous by default.",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "loads": ["process-envelope", "process-implementation", "languages"],
  "requires": [
    "process-spine", "process-envelope", "process-implementation", "gate", "git-workflow",
    "languages", "registers-triage-partition"
  ],
  "optional": [
    "process-interview", "codegen", "dev-environment", "runtime-contracts", "architecture", "resilience",
    "retro-corpus", "tracker-identity", "security", "docs"
  ],
  "steps": [
    {"id": "continue-or-branch", "name": "Continue existing PR or branch",       "kind": "decision", "actor": "coordinator",                               "body": "continue-an-existing-pr"},
    {"id": "gather-context",     "name": "Gather bug context",                   "kind": "author",   "actor": "coordinator", "consumes": ["tracker-issue"], "body": "phase-0-gather-the-bug-context"},
    {"id": "understand",         "name": "Understand the bug",                   "kind": "author",   "actor": "coordinator",                               "body": "phase-1-understand-the-bug"},
    {"id": "cause-ledger",       "name": "Extract every cause the issue names",  "kind": "author",   "actor": "coordinator", "consumes": ["tracker-issue"], "body": "phase-1-1-the-cause-ledger"},
    {"id": "trace-flow",         "name": "Trace the full flow",                  "kind": "author",   "actor": "coordinator",                               "body": "trace-the-full-flow"},
    {"id": "record-adr",         "name": "Record the decision (ADR, if complex)","kind": "author",   "actor": "coordinator",                               "body": "record-the-decision"},
    {"id": "red-proof",          "name": "Red test — the issue's reproduction, or one we write","kind": "gate",     "actor": "coordinator", "gate": "hard", "critique": "negative-control", "produces": ["tests"], "body": "phase-2-write-the-failing-test"},
    {"id": "fix",                "name": "Fix the root cause",                   "kind": "author",   "actor": "coordinator",                               "body": "phase-3-fix-the-bug"},
    {"id": "count-escalate",     "name": "Count fixes, then escalate (≥3 withhold)","kind": "decision","actor": "coordinator",                             "body": "count-then-escalate"},
    {"id": "green-proof",        "name": "Verify the fix (show green + regressions)","kind": "gate", "actor": "coordinator", "gate": "hard",               "body": "phase-4-verify-the-fix"},
     {"id": "completeness",       "name": "Account for EVERY cause in the ledger","kind": "gate",     "actor": "coordinator", "gate": "hard",               "body": "phase-4-5-the-completeness-gate"},
     {"id": "reconcile-page",     "name": "Reconcile the page (docs impact)",    "kind": "author",   "actor": "coordinator",                               "body": "phase-4-6-reconcile-the-page-docs-impact"},
     {"id": "handoff",            "name": "Open PR, green CI, hand to verify",    "kind": "io",       "actor": "coordinator", "produces": ["tracker-issue"], "body": "phase-5-hand-off-to-verification"}
  ]
}
```

## Context to load

This is code-bearing work. Before writing the fix, read:
- [`../../../process/implementation.md`](../../../process/implementation.md) — the shared process + the FAST verification you run.
- the contract for the layer you're fixing — <!-- home -->[`backend-implementation-contract.md`](../../../../knowledge/specs/backend-implementation-contract.md) (Go)<!-- else -->`slot:languages`<!-- /home --> or <!-- home -->[`frontend-implementation-contract.md`](../../../../knowledge/specs/frontend-implementation-contract.md) (TS/React)<!-- else -->`slot:languages`<!-- /home -->; Python → also <!-- home -->[`python-conventions.md`](../../../../knowledge/specs/python-conventions.md)<!-- else -->`slot:languages`<!-- /home -->; agent runtime → also <!-- home -->[`agents-runtime.md`](../../../../knowledge/specs/agents-runtime.md)<!-- else -->`slot:runtime-contracts`<!-- /home -->.

**By default (autonomous mode):** also load [`../../../process/autonomous-drive.md`](../../../process/autonomous-drive.md) (the shared execute envelope: Rules A–G, the terminal, flow-retro) and [`../../../process/issue-shape.md`](../../../process/issue-shape.md) (how `:create` commands file tracker issues). Under `--manual` these aren't needed — human gates replace the envelope.

(For a pure question or "is this even a bug?" investigation, use <!-- home -->`/zetify:ask`<!-- else -->`/zetify:ask`<!-- /home --> first — but anything that becomes a fix comes back here, reproduce-first.)

---

## Continue an existing PR — never open a second one

**Before reproducing or writing any code, check whether this tracker issue already has an open PR**, and if so continue it. A retry or re-claim of a failed item MUST build on the work already pushed — opening a second PR for the same issue is forbidden:

```bash
gh pr list --search "<KEY>" --state open --json number,headRefName,url
```

If an open PR exists for this issue: `git fetch origin && git checkout <headRefName>`, reconcile with `main` (`git merge origin/main --no-edit`), and **continue on that branch** — drive its CI green and push to the **same** PR. Start a fresh branch only when there is genuinely no open PR for this issue.

---

## Modes

**Autonomous is the DEFAULT; `--manual` is the opt-out.**

### Autonomous (default)

The default whenever you run `/zetify:bug:fix <key>` — and the path the tracker-listening daemon uses when it detects a `Type:bug` issue (it just calls `/zetify:bug:fix <key>`). Human gates are replaced by the autonomous execute envelope in `autonomous-drive.md`: drive the fix to a **green PR handed to verification** unattended, never stopping to ask. It does **not** self-merge (see Phase 5).

**Gate → envelope mappings (how autonomous handles what `--manual` would ask):**

| `--manual` gate | Autonomous (default) behavior |
|---|---|
| `question` for root-cause disambiguation (multiple plausible hypotheses) | Pick the most defensible hypothesis. Log the choice and rationale in the **Autonomous Decisions Log** (Rules A + B of `autonomous-drive.md`). Proceed. |
| ≥3 failed fixes → `question` to escalate | **WITHHOLD the handoff** (Rule D). Leave the PR open and unmerged. Report the architectural signal loudly in the PR description and in the Decisions Log. Do NOT move the issue to `Verify Queue`. It stays `Implementing` for human review. |

The Phase 5 handoff applies only when the fix reaches green within 3 attempts. The merge itself belongs to the `/zetify:verify` session that certifies the ledger; Rule F in `autonomous-drive.md` notes that for bugs the fleet daemon settles the tracker issue on a completing merged PR (`_pr_completes_issue` — <!-- home -->ENG-9641<!-- /home -->) — no repo status field is written.

### Manual (`--manual`)

The opt-out for hands-on debugging. Human gates are active: `AskUserQuestion` disambiguates root causes, and ≥3 failed fixes surface an architectural escalation question before any further attempt. Every such question is shaped by the interview card; the autonomous default never interviews. It stops after the fix is committed and hands off to `/zetify:push` — no auto-merge.

<!-- include: process/interview-card.md -->

The reproduce-first TDD discipline (red→root-cause→green) is fully intact in **both** modes — it is the body of the work, not a gate.

---

## CRITICAL RULES

1. **NEVER fix before you have a failing test** — the failing test IS your proof that the bug exists and your contract for what "fixed" means. When the issue carries a `## Reproduction` block, its named test is that proof and you use it (Phase 2) instead of writing a new one; a named test that comes back green stops the run.
2. **Show evidence** — after writing the test, run it and display the failing output. This is non-negotiable.
3. **Proper fix** — fix the root cause, not the symptom. If the bug has multiple layers (e.g. wrong data from backend + missing frontend handling), fix all layers. Trace the full data flow before deciding what to change. A proper fix at the source is always better than a workaround downstream.
4. **Show the green** — after fixing, run the test again and display the passing output as proof.
5. **Scoped changes** — stay focused on the bug, but don't artificially limit yourself. If fixing the root cause requires changes across multiple files or layers (backend, frontend, prompts), that's expected — not scope creep. What you should NOT do is unrelated cleanup, style changes, or feature additions. **"Feature addition" includes a surface, control, setting, event, permission or flag the issue never named that you notice would "obviously" belong while you are in there.** That belongs on the **withheld list**, surfaced once at the terminal per [`autonomous-drive.md`](../../../process/autonomous-drive.md) **Rule K** — not in this diff. A fix is scoped to the bug it proves; anything wider is the surprise the rule exists to stop.
6. **Autonomous mode (default):** log the chosen root-cause hypothesis in the Autonomous Decisions Log (and `comment` on the issue when a tracker key is in play) and proceed (see gate mappings above). **`--manual` mode:** use `AskUserQuestion` to disambiguate between multiple possible root causes, presented as selectable options.
7. **Out-of-scope findings (Rule G):** if you discover a distinct bug while investigating → `/zetify:bug:create` (Fleet `file_issue` kind bug, `Found during: <KEY>` in the body); if you spot an important follow-up that isn't a bug → `/zetify:task:create` (Fleet `file_issue` kind task). Log the filing in the Autonomous Decisions Log (or in your output summary under `--manual`). Never fix it inline. **If the Fleet tools refuse the filing, end this run `failed`** — name the follow-up and the refusal in the Decisions Log; do not carry on as if it were filed. See Rule G in [`autonomous-drive.md`](../../../process/autonomous-drive.md).

### Red flags — STOP and restart Phase 1

If you catch yourself thinking any of these, you're skipping the process:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "It's probably X, let me fix that" (without tracing data flow)
- "I'll write the test after confirming the fix works"
- "I already manually tested it"
- "Code before test" / "Keep this code as reference, write the test next"
- "One more fix attempt" — when 2+ fixes have already failed (see Phase 3.5)

All of these mean: stop, return to Phase 1, re-investigate. Each one is a rationalization for guessing.

---

## Phase 0: Gather the Bug Context

The argument is a free-form description, or a reference to a tracker issue (e.g. <!-- home -->`ENG-42`<!-- else -->`<KEY>`<!-- /home --> or the tracker URL). **No Fleet tools? Stop.** When the session has no Fleet tools and a tracker issue is in play, stop with: *this command needs the Fleet tools; create a personal key in Fleet under Settings › Connect your tools*. There is no other tracker path — never fall back to a tracker script. If a tracker issue is referenced:

- Read the issue with `get_issue` (title, description, comments, attached evidence) for the canonical report. Merge any additional context from `$ARGUMENTS` with it.
- **If the report cites a specific CI run/job as evidence, fetch that exact failing job's raw log** — `gh api repos/<org>/<repo>/actions/jobs/<id>/logs` (find the id via `gh run view <runID> --json jobs`). `gh run view --log` silently returns the *latest* attempt, which a since-then rerun may have turned green — trusting it (or the report's forensic prose alone) sends you chasing an already-fixed symptom. Prefer per-job `--json jobs` over `gh pr checks --watch` when the aggregate view looks stuck. <!-- home -->(eng-286, eng-460.)<!-- /home -->
- **If a merged fix you're re-verifying landed only in seed data, an already-provisioned workspace never picks it up from a plain rebuild + restart** — seed helpers are idempotent and self-healing, but only when re-invoked; nothing re-runs them on boot. Before concluding "still broken" against a live/dev org, re-seed the way `{{target:reseed}}` says, then re-check.
- **A burst of many *unrelated* test failures sharing one root database-connection error is a transient shared-runner infra flake, not a code regression — don't chase it.** The integration lane's database dying under host contention takes every in-flight test with it. Skip straight to "did the aggregate required check pass anyway?" (`slot:gate` says which lanes gate the merge and which are advisory) and re-run only if it did not.
- the tracker is the system of record for the bug's status — this workflow writes no repo bug file. Move the issue's state in the tracker out-of-band as you progress.
- **Read the issue description for its `## Reproduction` block first.** An issue minted by the fleet's confirm flow carries one: the steps, the failing test (`file`, `name`, `branch`, `sha`), the suspected cause, the dedupe record, and the answers the filer gave the reproduce stage. When the block is present, Phase 2 starts from it rather than inventing a test; when it is absent, the behaviour is today's — write your own failing test. The screenshots the filer attached are inlined as images in the description (`![name](<tracker url>)`); read them.

If the argument is just a free-form description, proceed directly — the failing test and fix commit are the only artifacts.

---

## Phase 1: Understand the Bug

The user's bug description: $ARGUMENTS

1. Read the bug description.
1a. **A forensic issue body IS the hypothesis — take the fast path.** When the tracker issue already carries an exact `file:line`, a contract/spec citation, and a "Proposed fix" section (the shape `/zetify:bug:create` and an `audit` finding produce), read it as the **primary hypothesis source**: verify it by reading the cited lines, then go straight to Phase 2's red test. Do not re-derive the investigation from scratch — a prior pass already did it, and re-exploring risks landing on a *different* cause than the one the issue's ledger will be verified against. If the cited lines don't say what the issue claims, *that* is the finding: fall back to steps 3–5 and note the divergence.
2. If a tracker issue was referenced in Phase 0: on a **fleet dispatch** the daemon already claimed it — do **not** move at start. On a **hand run**, call `move_issue(to: "human-wip")`, then re-read with `get_issue`; **stop if `levers` shows the issue is already running** on another seat. Re-read with `get_issue` again before the first push so a concurrent claim cannot race you.
3. Identify the affected area — use Grep/Glob to locate relevant code.
4. Read the code and form hypotheses about the root cause.
5. **Interactive:** if there are multiple plausible causes, use `AskUserQuestion` to let the user choose which to investigate first. **Autonomous:** pick the most defensible hypothesis, log it in the Autonomous Decisions Log, proceed.

**Output:** A brief summary:
- **Symptom**: What the user observes
- **Location**: File(s) and line(s) involved
- **Hypothesis**: What you believe is wrong and why

---

## Phase 1.1: The cause ledger

**Before touching code, write down what this issue says "fixed" means.** Copy from the
issue, **verbatim and quoted**, every clause that asserts something is wrong:

- each **named root cause** (issues routinely name two or three — "the <!-- home -->CAP-0743<!-- /home --> override is
  still dead config, *and* …");
- each **acceptance criterion**, if it has them;
- each **site** a scoped claim covers (*"wherever the codebase or docs assert it"*,
  *"all 50 references across 32 files"*, *"the three secondary claims"*).

Record them as a numbered ledger. One line each, quoted, no paraphrase.

```
CAUSE LEDGER — <KEY>
1. "the <!-- home -->CAP-0743<!-- /home --> operator identity override is still dead config"        → [ ]
2. "resolveFactIdentity is not threaded into the pin pre-check"          → [ ]
3. "wherever the codebase or docs assert it" (scope: 3 sites found)      → [ ]
```

**The `## Reproduction` block opens the ledger when the issue carries one.** The answers the filer gave the reproduce stage and its dedupe record are the first ledger lines — quote them verbatim, under the issue's own causes, so the completeness gate below can close them the way it closes every other clause. The block's **suspected cause is a LEAD, never the verdict**: the reproduce stage named the most defensible hypothesis it could, and this run's job is to confirm or refute it at the root cause, not to copy it into Phase 3. A suspected cause the fix confirms is `FIXED`; one the investigation contradicts is `REFUTED` with what you found instead — never silently dropped.

**Why this exists, measured on this repo.** Of ~2,661 shipped fixes, **~1 in 5 later
received a follow-up issue saying the fix was incomplete** — and when merged fixes were
adversarially re-verified, **~1 in 2 did not fully address the issue they closed**. So
roughly half of incomplete fixes are never noticed at all: the issue closes, the board
says Done, and the defect stays.

Those are **ungated** numbers. **Gated**, [`/zetify:verify`](../verify.md) turns back
**9.3% of the issues that reach it** (53 of 571; 11.2% of 669 gate entries, over the seven
whole UTC days <!-- home -->2026-08-15<!-- /home -->→21) — what the gate caught, a floor under the defect rate rather
than a measure of it. And the gate is not a wall: re-verifying fixes that **passed** it and
merged found **12.5% still incomplete** (4 of 32; 95% CI 5.0–28.1%) — far below the ungated
~1 in 2, but n=32 resolves nothing finer, and the older method is unrecorded, so part of
that gap may be measurement rather than reality and the gate is not proven to be the cause.
**Roughly one fix in eight still gets through.** Write the ledger as though yours is that
one.

The dominant failure is not sloppiness — it is **fixing the symptom the issue named
instead of the root cause it named**, and both were written down. <!-- home -->ENG-6143<!-- /home --> fixed one of
its own two stated causes. <!-- home -->ENG-6108<!-- /home --> ratified *"correct the overclaim wherever asserted"*
and landed it in 2 of 3 sites. <!-- home -->ENG-5990<!-- /home -->'s decision named two narrowings and shipped one.
**Every one of those issues told the implementer what completeness required, and closed
anyway.** You cannot check that at the end if you never wrote it down at the start — which
is the only reason this phase is separate from Phase 1.

Paraphrasing defeats the gate: *"identity resolution was wrong"* covers both causes above
loosely enough that fixing either one reads as done. **Quote, don't summarise.**

---

## Phase 1.5: Trace the Full Flow

Before writing any code, trace the bug's data flow end-to-end:
1. Where is the data produced? (API, agent, tool return value, DB query)
2. How is it transformed? (SSE events, gRPC, JSON mapping)
3. Where is it consumed? (frontend component, handler, template)

Identify ALL layers where the bug manifests. If the root cause is upstream (e.g. tool returns wrong data), fixing only the downstream consumer is a hack.

**Ask yourself**: "If I only fix this one spot, will the same class of bug recur in another consumer?" If yes, fix upstream.

### Multi-component boundary instrumentation

When the system has multiple components in the failure path (<!-- home -->connector worker → connectord → API → DB; or browser → API → agent runtime → MCP → projection compiler<!-- else -->e.g. a worker → a queue → the API → the database; or the browser → the API → a background job<!-- /home -->), **instrument BEFORE diagnosing**. Don't guess which layer is broken — prove it.

For each component boundary the bug crosses:

1. Log what data **enters** the component (request, message, batch).
2. Log what data **exits** the component (response, downstream call, persisted row).
3. Verify environment / config propagation across the boundary (env vars, headers, tokens, claims).
4. Capture state at the layer (DB row, in-memory cache, replica ID).

Run once to gather evidence. **Then** analyze — the evidence will pinpoint which boundary fails. Investigate that specific layer; don't fix until you know which boundary breaks.

This is faster than guessing in 95% of multi-layer bugs. The boundaries worth
instrumenting are this product's — `slot:architecture` names the layers and
`slot:architecture` the paths a request takes through them (a data-ingest path, an
agent path, an event path, an auth path — whichever this product has). Instrument with the
lane's structured logger at each boundary; read the log sinks `slot:dev-environment`
names — don't ask the user to paste logs.

Where the bug sits on an interface or an auth path, read `slot:security` first: it names how a
caller is authenticated and what may be reached past the gateway, and the fix keeps to it.

### Multi-replica awareness

Where this repo runs **multiple replicas** of a service — its `resilience` slot says whether it does — that has direct implications for debugging:

1. **State synchronization**: In-memory state (caches, maps, goroutine-local data) is NOT shared between replicas. If the bug involves stale data or missing state, check whether the code assumes single-instance state (e.g., an in-memory event bus, a local cache, a map used as a lock). The fix must use a shared backing store (Postgres, Redis) or accept eventual consistency.
2. **Race conditions across replicas**: Two replicas may process the same event, job, or webhook concurrently. Check for missing distributed locks, lack of `SELECT ... FOR UPDATE`, missing idempotency keys, or TOCTOU (time-of-check-time-of-use) patterns that only break under concurrent access from separate processes.
3. **SSE fan-out**: SSE events published on one replica are NOT automatically visible to clients connected to a different replica. If the bug is "SSE events not arriving", check whether the event bus has cross-replica fan-out (e.g., Postgres LISTEN/NOTIFY, Redis pub/sub) or if it's purely in-process.
4. **Background tasks / cron**: Background work and periodic jobs run on EVERY replica. If a background task should run exactly once (not once-per-replica), it needs leader election or a distributed lock. Check whether the buggy behavior is the task running N times instead of once.
5. **Log correlation**: When reading the API's log sink, be aware that in production logs come from multiple replicas. A request that starts on replica A may trigger a background task that runs on replica B. Correlate using request IDs, trace IDs, or change/run IDs.

**Ask yourself**: "Would this bug reproduce if only one replica were running?" If no, the root cause is likely a synchronization issue between replicas.

### Live debugging tools

You have access to **browser automation** and the **dev database** — use them to inspect live state:

- **Browser**: Use <!-- home -->Playwright/browser<!-- else -->browser<!-- /home --> tools to visit pages, read page content and get element refs, interact with elements, check console logs, and inspect network activity. Always take a snapshot first to get element refs before clicking or typing.
- **Dev database**: Run SELECT queries against the dev Postgres to inspect actual data, verify schema state, check for data inconsistencies, or confirm a migration ran correctly. **Read-only queries only** — never mutate data via this tool during debugging.

Use these tools throughout all phases — not just at the end.

---

## Phase 1.6: Record the decision (ADR — only if reasonably-complex)

If the root cause + fix approach involve a **reasonably-complex, load-bearing decision** — one that
changes an interface, an invariant, a convention, or a future direction — record it as an **ADR-style
note** *before* writing the fix: **context · options · decision · rationale**. Put it where the work
lives: a comment on the tracker bug issue, carried into the run's bug-retro "Decisions" section. By the
time you reach the fix, the decision is already captured. **Record it as an `implementation-notes` comment** (`comment` kind=`implementation-notes`) — never a description rewrite (no tool rewrites one; <!-- home -->CAP-1593<!-- /home --> / G4), and never under `## Decision (<date>)`, which is reserved for a human's answer ([`decision-write-back.md`](../../../process/decision-write-back.md), <!-- home -->ENG-10710<!-- /home -->). **Skip this for routine fixes** (the common
case) — not every fix earns an ADR, only the ones someone will later ask "why did we fix it this way?"
about.

---

## Phase 2: Write the Failing Test

Write a test that:
- Reproduces the exact bug described
- Fails for the right reason (not a typo or setup error)
- Will pass once the bug is fixed
- Is minimal — tests only the buggy behavior, not a full integration

### Start from the issue's `## Reproduction` block when it has one

**Check out the recorded sha, never the branch tip.** When `## Reproduction` names a
**Checked commit** (or a test `sha`), `git fetch` and `git checkout <that-sha>` before
running the test. The branch tip may have moved; the operator confirmed the code at that
exact commit. On an unvouched key the approved snapshot is in the briefing only — do not
read the live issue for the report text.

An issue minted from the bug reproducer carries a `## Reproduction` block naming a test — its
`file`, `name`, `branch` and `sha`. When it does, **that test is this run's red proof, and you do
not write a second one**:

1. Fetch the block's `branch` and check its named test file out onto your work branch
   (`agent/bug-<key>` — the deterministic fix branch `slot:git-workflow` names), at the `sha` the
   block records when it names one: the reproducer already proved the defect red, and re-deriving
   that proof is how the file the filer confirmed drifts from the file the fix ships. Keep a
   `Refs`/`Closes` line to the issue and the test's origin in the commit message if you must
   re-materialise it, but the test's CONTENT travels unchanged.
2. **Run it and require it RED before Phase 3.** Display the failure — this is Phase 2's mandatory
   red proof, the same evidence a self-written test owes, from the same reproduction.
3. **A named test that is NOT red is a stop, not a bug to fix.** If it passes on the work branch
   (and therefore on `main`), the reproduction no longer holds: the defect was fixed elsewhere,
   the branch is stale, or the block was mis-recorded. Do **not** invent a different bug to fix.
   Withhold the handoff and hand back with `needs-decision`, naming the test and the fact it came
   back green — the one blocked-on-a-human case this command has, because only a person can say
   whether the block is wrong or the bug moved.

**That hand-back is a `Blocked · decision` park, so it carries the `decision` document** —
the named test, the fact it came back green, and the choice the person has (the block is
wrong and gets re-reproduced, or the bug moved and this issue closes) — written to the card
above:

<!-- include: process/decision-document.md -->

**Only when the block is absent** do you write your own failing test, by the rules below — the
behaviour on an issue with no `## Reproduction` block is exactly today's. The block's presence
also means the confirmed steps are available: use them, and its screenshots, to walk the path.

**`/zetify:verify` needs no change here, and this is said so nobody goes looking for a rule.**
The verifier already neuters *every* named test — including one another session wrote — and
checks the fix against it. That mechanism covers a test this run took from the reproduce branch
exactly as it covers one this run authored; there is no separate registration, marker or second
test file to add.

### Choose the right test style

- If the bug is about orchestration or side effects — wrong collaborator call, missing call, extra call, wrong retry behavior, wrong ordering, or "should not proceed after dependency failure" — prefer an **interaction test** with a generated mock.
- If the bug is about deriving output from stored data or in-memory state, prefer a **state-oriented test** with a fake.
- If your fake starts accumulating call counters, ordered-call assertions, or many unused methods just to prove one interaction, stop and switch to a generated mock.
<!-- home -->- For new Go interaction seams, add or update the package's `go:generate mockery` hook so `{{target:generate}}` keeps the mock in sync.
<!-- else -->- For a new interaction seam, add or update whatever generates its test double (`slot:codegen`) so `{{target:generate}}` keeps it in sync.
<!-- /home -->- **If the bug is a read-path, display-resolution, projection, or backfill defect, first ask: does it depend on rows/state that predate the fix?** (an old connector install, a migration that ran before this code existed, a stale cache/index). If yes, the repro must seed that pre-existing state — with the pre-fix shape — BEFORE calling the code path under test, then assert; do not seed a fresh row and then apply the fix, since a freshly-created row is always produced by the current (already-fixed) code and will pass regardless of whether the real persistent-org defect was touched. See [`implementation.md`](../../../process/implementation.md) §2 for the worked example (`TestApplyBundle_DisplayAttribute_BackfilledOnPreExistingTypeWhenUnset`) and the incidents this class recurred in before <!-- home -->ENG-1000<!-- /home --> closed the gap (<!-- home -->ENG-996<!-- /home -->, <!-- home -->ENG-999<!-- /home -->).

### Test placement

Where a test for a given source file lives is the lane's convention — `{{target:test-one T=<TestName>}}`
records it beside the command that runs one. **Where the repository has no test lane for
the thing that is broken** (a manifest, a stack definition, a document), the reproduction
is whatever `slot:gate` names as its proof for that kind of change — a rendered diff, a
plan, a validator — and the same rule holds: it must be red before the fix and green after.

### MANDATORY: Run the test and show the failure

Run the one test, and only that test:

```bash
{{target:test-one T=<TestName>}}
```

Display the failing test output. If the test passes, your hypothesis is wrong — go back to Phase 1 and revise.

**The test MUST fail before you proceed. A passing test means you haven't found the bug yet.**

---

## Phase 3: Fix the Bug

Now — and only now — fix the bug:

1. Make the minimal code change that addresses the root cause.
2. Do not refactor, do not add features, do not improve error handling beyond what's needed.
3. If the fix requires changing generated code, change the source and regenerate (e.g., `{{target:generate}}` for the API spec, `{{target:generate}}` for the query layer).
4. If the failing test exposed an interaction seam without generated mocks, add the mock generation hook as part of the fix when that is the smallest sustainable path.

---

## Phase 3.5: If the fix didn't work — count, then escalate

If your test still fails after the fix, **STOP and count**: how many fixes have you tried for this bug?

- **< 3:** Return to Phase 1. Don't pile on Fix #N+1. The new evidence (why your last fix didn't work) often reveals a root cause you missed. Re-investigate, don't re-patch.
- **≥ 3 (interactive):** This is no longer a bug — it's an architectural problem. **Stop attempting fixes.** Surface this to the user with `AskUserQuestion`: present what you've tried, what each fix revealed, and ask whether to (a) continue patching with a fresh hypothesis, (b) refactor the surrounding pattern, or (c) escalate to design.
- **≥ 3 (autonomous):** **WITHHOLD the handoff** (Rule D of `autonomous-drive.md`). Leave the PR open and unmerged. Report the architectural signal loudly in the PR description and in the Autonomous Decisions Log. Do NOT move the issue to `Verify Queue` — a withheld fix must not reach the verifier, which would certify a ledger you already know is unsound. The tracker issue stays `Implementing` for human review.

Patterns indicating architectural failure (apply in both modes):

  - Each fix reveals new shared state / coupling / problem in a different place.
  - Fixes require "massive refactoring" to actually land.
  - Each fix creates new symptoms in adjacent components.

  This is **not** a failed hypothesis — the architecture is wrong. Adding Fix #4 will make it worse. Treat 3+ failures as an architectural signal, not a debugging signal.

---

## Phase 4: Verify the Fix

### MANDATORY: Run the same test and show it passing

Run the exact same test command from Phase 2. Display the passing output.

Then run the broader test suite for the affected package to check for regressions:
<!-- home -->- Go: `{{target:test-unit}}` or `go test ./path/to/package/...`
- Python: `{{target:test-unit}}` for that lane; for connectord/connector changes also run relevant Go tests
- Frontend: `{{target:test-unit}}` for the frontend lane
<!-- else -->- `{{target:test-unit}}` for each lane the change touches (`slot:gate` names the lanes and their package-scoped form)
<!-- /home -->
**When this discipline is invoked from within a `/zetify:prd:implement` / verify run** (the coordinator dispatched you as a fix sub-agent, not a standalone `/zetify:bug:fix`): skip `{{target:test-unit}}` — where its answer carries a race detector it is banned in-flow (`../../../process/implementation.md` §4). Run only the targeted <!-- home -->`go test -count=1 -run <Pattern> ./<pkg>/...`<!-- else -->package-scoped test<!-- /home -->; the coordinator's per-wave pre-commit gate is the broad regression check.

---

## Phase 4.5: The completeness gate

**Re-read the Phase 1.1 ledger and close every line before you open the PR.** For each,
one of exactly three dispositions — no fourth, and no blank:

| | |
|---|---|
| **FIXED** | name the file:line that satisfies it **and** the test that would fail without it |
| **DEFERRED** | say why, and **file the follow-up now** via `/zetify:bug:create` or `/zetify:task:create` (Fleet `file_issue` — a defect as kind bug; lands in `triage`) — a deferral with no issue is an unfixed cause with a closed ticket. A refused filing ends this run `failed`. |
| **REFUTED** | the issue's claim is wrong; say what you found instead, and **record the refutation as an `implementation-notes` comment** (`comment` kind=`implementation-notes` — name the claim and what is true instead) so the next reader is not sent after a defect that does not exist. Do **not** edit the issue description: no tool rewrites one (<!-- home -->CAP-1593<!-- /home --> / G4) |

```
CAUSE LEDGER — <!-- home -->ENG-6143<!-- /home -->
1. "resolveFactIdentity … threaded into the pin pre-check"  FIXED    pinning.go:504 · TestPinPrecheckUsesResolvedIdentity
2. "the <!-- home -->CAP-0743<!-- /home --> operator identity override is still dead config" DEFERRED → filed <!-- home -->ENG-6177<!-- else --><KEY><!-- /home -->
```

A ledger line naming a grant, role, binding, or credential is **not FIXED by the
configuration that shows the grant exists** — close it by **performing the call the
grant exists for**, as the principal that actually executes at runtime (impersonation
may make that a different identity), and recording the response; the executed call is
the test that would fail without the fix. A binding that exists proves only that the
grant was applied, never that the capability works (<!-- home -->ENG-9395, from ENG-9199: <!-- /home -->a binding
verified present left the detector it armed 403-ing on every tick for ~100 minutes).

**A scoped claim is not closed until you have counted.** *"Wherever asserted"*, *"all N
references"*, *"every call site"* — grep for the pattern, state the denominator, and say
which you changed. `landed in 2 of 3 sites` is the single most common shape of an
incomplete fix in this repo, and it is always a claim nobody counted.

**A test that would still pass with your fix reverted does not close a line.** Neutering
the change is a five-second check and it has caught guards that were provably inert:
<!-- home -->ENG-6199<!-- /home -->'s test *assigned* the value it was meant to verify, so planting the exact defect
left it green. If reverting your fix leaves the suite green, you have not written the
test — you have written a description of the test.

**Run the same neuter check before you hand off — this is the implementer's own pass, not
the verifier's.** It is one script, `knowledge/scripts/neuter_check.py`, and `/zetify:verify`
calls the same one, so the mechanic has a single copy and the two sessions cannot drift. Of
192 verify rejections in one week, **30 were a test that stayed green with the fix reverted**;
every ledger line with a test names that test here, and every scoped line names its pattern:

```bash
python3 knowledge/scripts/neuter_check.py --base origin/main --ledger /<!-- home -->tmp/neuter.json<!-- /home -->
```

The ledger (`tests`: the test's `run` list and the `revert` pathspec of the files the fix
landed in — never the test file; `scopes`: the `pattern` and `paths` of a counted claim) runs
each test green→red→green, reverts and asserts the tree restored, counts every scoped site
against the diff, and **exits non-zero on any test that stayed green, any test not green at
HEAD, or any uncovered site**. Do not hand off until it exits zero.

**This gate is not a summary.** If every line reads FIXED and none names a test, you have
written prose, not evidence. Do not open the PR until each line names either an artifact
or an issue key.

---

## Phase 4.6: Reconcile the page (docs impact)

A fix that changes behavior a user-facing page describes makes that page **stale the moment
the fix lands**. Before the handoff, check whether the change touched a path a page lists in
its `source_of_truth:` (or otherwise contradicts a page's steps or screenshots):

- **In scope here** → reconcile the page **in the same change**: correct the step, the
  screenshot, or the prerequisite the fix moved. The page ships with the fix.
- **Out of scope here** (a page needing a rewrite beyond this diff) → file a
  `page:improve`-shaped issue through Fleet (`file_issue` kind bug for a page that now lies,
  kind task for one that is merely thin) — and cite the key in the PR body. A "deferred" page
  with no issue is a page you deleted. A refused filing ends this run `failed`.
- **Degrade.** When the repository leaves `slot:docs` unfilled there is no home to look in:
  say so in the PR body and move on — never invent a path or reconcile a page you cannot find.

## Phase 5: Hand off to verification

> # 🛑 THIS COMMAND DOES NOT MERGE ITS OWN FIX.
>
> **The party that wrote the code cannot certify it, and cannot merge on the strength of
> that certification either.** Phase 4.5's ledger is *this run's own reading* of the issue
> — input to a verdict, not the verdict. The verdict comes from
> [`/zetify:verify`](../verify.md), a fresh session with no stake in this loop
> terminating, because the loop's incentive is exactly what turns an unclosed claim into
> "close enough".
>
> This is the same split PRDs took, for the same measured reason, and the numbers here are
> worse: **~1 in 5 shipped fixes later drew a follow-up saying the fix was incomplete, and
> ~1 in 2 did not fully address the issue they closed** when adversarially re-verified.
> Every one of those was merged by the agent that wrote it. Those are ungated rates; gated,
> [`/zetify:verify`](../verify.md) turns back **9.3%** of what reaches it (53 of 571,
> measured <!-- home -->2026-08-15<!-- /home -->→21) — a floor under the defect rate, not a measure of it.

The fix is code-bearing, so it ships via a **branch + PR** (`slot:git-workflow`) — never direct to `main`. The failing test and the fix commit ship together on the deterministic fix branch `slot:git-workflow` names (keyed by the tracker issue when one is referenced — the `<key>` in branch + commit subject + PR title/body auto-links the issue; the PR body references `Refs <key>` and carries no closing keyword, so only the completing merge closes the issue — the `/zetify:verify` session's `ship` adds `Closes <key>` — see the convention in `push.md` Step 0 / <!-- home -->ENG-6210<!-- /home -->).

**A fix authored in `<!-- home -->ZetifyAI<!-- /home -->/fleet`'s `commandtree/` is COUPLED — never pin the consuming repo at this PR's head (<!-- home -->ENG-12719<!-- /home -->).** Open the **fleet PR only**; do **not** open the consuming repo's pin-bump PR against this PR's head. Fleet `main` is squash-only, so a pin at a PR head is never reachable (7 of the last 8 pins sat off `main`, <!-- home -->ENG-12481<!-- /home --> / <!-- home -->ENG-12661<!-- /home -->). The pin bump is produced **after** the fleet PR merges, from fleet `main`, by `/zetify:verify`, which treats the coupled change as two review targets — merge the fleet half first, then re-pin `fleet/` to the resulting squash commit and `fleet commands sync --repo .` in the same commit. Open the fleet PR, hand it off, and stop; the verifier owns the pin.

**Push discipline (<!-- home -->ENG-12785<!-- /home -->) — ONE push, rebased only if `CONFLICTING`, never while CI is in flight.** Batch every remaining commit — the flow-retro (step 0), notes, salvage — into the single final push that opens the PR via `/zetify:push`. **Rebase onto `origin/main` exactly once, immediately before that push, and only when the PR shows `CONFLICTING`**: branch protection requires status checks, not an up-to-date branch, so being merely *behind* is never a reason to rebase. **Never push while this PR's CI is running unless the push fixes a failure** — a push cancels the in-flight run and burns its runner-minutes for nothing (129 cancelled runs over 1.46 days, ~16% of all PR runner time). Keep the local pre-push check deliberately small — compile the changed packages at most; do not grow a heavy pre-commit gate. [`push.md`](../push.md) Steps 2–3 is the authority.

0. **Flow-retro BEFORE the handoff (<!-- home -->ENG-9260<!-- /home -->).** Write the run retro under
   the **`retro-corpus`** slot's location per [`autonomous-drive.md`](../../../process/autonomous-drive.md)
   § Flow-retro and **commit it on the work branch** so it rides the deliverable PR —
   **never a second PR**. A post-handoff retro PR is re-held forever by the daemon and
   parks the issue on a human (<!-- home -->ENG-8993<!-- /home --> #9731, <!-- home -->ENG-9081<!-- /home --> #9718). Accepted cost: the retro
   cannot record what happens inside the CI and verify windows. Do this *before* step 1
   so the retro lands in the same squash-merge as the fix.
1. **Open the PR and stop** — `/zetify:push` (the open-PR-and-stop mode), **never
   `/zetify:push ship`**. `ship` merges on green CI, which is precisely the step that
   is no longer yours to take.    Push mode now **arms auto-merge at open** (<!-- home -->ENG-8780<!-- /home -->) —
   expected, and safe on a `Type:bug`/`task`/`cleanup` PR: the required the fix gate
   check (<!-- home -->ENG-8413<!-- /home -->) holds the armed PR `BLOCKED` until `/zetify:verify` passes — the
   arm stands through the verify window, and it is dropped before either check-state
   change that follows: the verify session disarms at its §6 step 3 before re-running
   the gate (<!-- home -->ENG-9668<!-- /home -->), and ship mode disarms before any push (<!-- home -->ENG-9679<!-- /home -->).
2. **Do not hold the seat for CI — in a fleet-dispatched run, end `checks-pending`.** A red
   check you can already see is still yours to fix here, where the context lives. But once the PR
   is open and your last push is on it, do **not** `gh pr checks --watch`: confirm the PR head
   equals the remote ref, that it is not `DIRTY`, and that the checks are dispatched on that head
   ([`autonomous-drive.md`](../../../process/autonomous-drive.md) → *The terminal:
   `checks-pending`*), then skip steps 2.5–3 and take step 5 with `status: "checks-pending"`
   and the head in `verifiedSha`. The service watches the required checks and moves the issue to
   `Verify Queue` itself on green — or returns it to `Rework Queue` with the red checks named.
   **A person running this with `--manual`, or a dispatch whose mission does not teach
   `checks-pending`,** waits for green CI as before: a red PR is not a handoff, and
   verification refuses one and parks it straight back at you. The one red you expect to keep at
   handoff is the fix gate itself (red by design until the verdict re-read — step 2.5).
2.5. **🛑 Hand the PR off READY — never a draft.** Do NOT convert the PR to draft as a
   verify hold: the <!-- home -->ENG-7539<!-- /home --> draft hold is retired (<!-- home -->ENG-9434<!-- /home -->) because the required
   fix-gate check superseded it — that check, not a draft, is the verify verdict's
   merge-blocking representation GitHub enforces — and the dispatch missions forbid draft
   conversion outright (<!-- home -->ENG-8604<!-- /home -->: GitHub refuses auto-merge on a draft and the fleet's
   review machinery cannot see one, so a drafted handoff strands the PR invisibly). The
   non-pass hold is the daemon's `🚦 Verification did not pass — PR stopped` comment
   (the daemon's own marker), which lifts automatically at the
   next verify dispatch — the fleet's live verify hold never involves a draft.
3. **Hand off with `move_issue(to: "review")`** (Verify Queue) — *not in a `checks-pending`
   run (step 2), where the service writes this move when the checks are green.* That position
   move *is* the handoff: the daemon dispatches `/zetify:verify <KEY>`, which certifies the ledger and merges
   on an all-closed one. The `review` / Verify Queue position alone routes the verifier — do
   not invent label writes. **If the move is refused, end this run `failed`** — name the
   refusal; do not claim handoff.
4. **Decisions log / REFUTED claims:** when you need a durable note on the issue (chosen
   hypothesis, deferred follow-up key, a REFUTED claim's correction), call `comment` with
   `kind=implementation-notes` — never a description rewrite (no tool rewrites one).
5. **Write the done-sentinel claiming success** — `checks-pending` (step 2) in a fleet-dispatched
   run, `handed-off` after a human-driven wait for green. Your run succeeded when the PR is open
   with its checks dispatched (or green and the issue in review) — the merge is a later
   session's outcome, not yours. Without
   the sentinel the daemon looks for a merged PR that will not exist yet and parks the fix
   behind a human.

**Put the closed cause ledger in the PR body.** It is the one artifact a reviewer — or the
verifier reading this fix in an hour — can check without re-deriving the issue. A PR that
says "fixes <KEY>" and nothing about which of its named causes it fixed is exactly the
shape that produced a ~1-in-5 follow-up rate. **Do not summarise or re-word the issue's
claims when you copy them in** — the verifier diffs your ledger against the issue's own
text, and a paraphrase reads as a dropped claim.

**Put a `## Files` scope manifest in the PR body (<!-- home -->ENG-11269<!-- /home -->, <!-- home -->ENG-18659<!-- /home -->).** Generate it with the shipped script, **never by hand** — a rule the model must remember is not a rule that binds: `python3 knowledge/scripts/pr_scope_manifest.py ensure --pr <pr>` splices a current manifest into the live body after `/zetify:push` opens the PR (`ensure --body-file <path> --out <path>` before `gh pr create`), replacing a stale section rather than duplicating it. It lists every changed path under `## Files` (backticked bullets; a trailing-slash directory covers its subtree) from `git diff --name-only origin/<base>...HEAD`; a tracker-keyed PR without a parseable manifest fails CI. Re-run `ensure --pr <pr>` after every amend/rebase.

**If verification returns it** (moved to **`Rework Queue`** + a comment listing the OPEN
lines), you are re-dispatched with that comment as the brief. Read it first and close
*those* lines — do not re-derive the bug from scratch, and do not re-open the ones already
accepted. Two returns is the cap; a third parks it for a human.

**Output:** A brief summary:
- **Bug:** <tracker issue ref — `Implementing`, moves to `Verify Queue` at handoff and Done once the verifier merges>; or "ad-hoc, no tracker issue"
- **Root cause**: What was actually wrong (confirmed by the test)
- **Cause ledger**: `n/n closed` — FIXED / DEFERRED (with the follow-up key) / REFUTED per line. Never omit; `1/2 closed, 1 deferred → <KEY>` is a good outcome, a silent `1/2` is the defect this gate exists to stop
- **Fix**: What you changed (file, line, what changed)
- **Evidence**: Test went from FAIL to PASS
- **Regressions**: None (or list any found and how they were addressed)

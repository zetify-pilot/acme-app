#  Task — Implement

Drive a small, scoped engineering task to a **green PR handed to an independent [`/fleet:verify`](../verify.md) session** — autonomous by default, no PRD or plan file required. Scope is defined inline (lightweight brief), then the work is implemented and handed off. **This command does not merge its own work** (see the Terminal in Step 3).

> To *capture* a future task for later (not start it now), use [`/fleet:task:create`](create.md) instead.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `triage` may terminate the command (bug/feature in disguise → hand off); `mode-select` branches to `implement`+`ship` (autonomous) *or* `manual-plan` (stop). The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "task-implement",
  "tier": "core",
  "intent": "Small scoped task → green PR handed to an independent /fleet:verify session; does NOT self-merge; autonomous by default, no PRD/plan file.",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "loads": ["process-envelope", "process-implementation", "languages"],
  "requires": [
    "process-spine", "process-envelope", "process-implementation", "gate", "git-workflow",
    "languages", "tracker-identity"
  ],
  "optional": [
    "process-feature-reconcile", "process-interview", "codegen", "planning-model", "runtime-contracts",
    "product-vision", "feature-maps", "components", "resilience", "architecture", "retro-corpus",
    "programs", "docs"
  ],
  "steps": [
    {"id": "continue-or-branch", "name": "Continue existing PR or branch",     "kind": "decision", "actor": "coordinator",                               "body": "continue-an-existing-pr"},
    {"id": "triage",       "name": "Triage: task vs bug vs feature",           "kind": "decision", "actor": "coordinator",                               "body": "step-1-triage"},
    {"id": "scope-brief",  "name": "Scope inline (task brief)",                "kind": "author",   "actor": "coordinator",                               "body": "step-2-scope-inline"},
    {"id": "mode-select",  "name": "Select mode (autonomous / manual)",        "kind": "decision", "actor": "coordinator",                               "body": "modes"},
    {"id": "implement",    "name": "Implement (sub-agent edits)",              "kind": "fanout",   "actor": "subagent",    "model": "sonnet",            "body": "step-3-autonomous-path"},
    {"id": "completeness", "name": "Account for EVERY clause the issue names", "kind": "gate",     "actor": "coordinator", "gate": "hard",               "body": "the-completeness-gate"},
    {"id": "handoff",      "name": "Green CI, then hand to verify",           "kind": "io",       "actor": "coordinator", "produces": ["linear-issue"], "body": "step-3-autonomous-path"},
    {"id": "manual-plan",  "name": "Manual: plan and stop",                    "kind": "author",   "actor": "coordinator",                               "body": "step-4-manual-path"}
  ]
}
```

---

## Context to load

- [`../../../process/autonomous-drive.md`](../../../process/autonomous-drive.md) — **load and obey Rules A–G**, the terminal (Rule C: an execute command hands off at a green PR), and the dispatch envelope.
- [`../../../process/implementation.md`](../../../process/implementation.md) — the shared implementation process.
- The branch convention: `slot:git-workflow` (defined once, there).
- Layer contracts (load the ones you touch): whatever `slot:languages` names for each lane the task touches, plus `slot:runtime-contracts` where the task touches a runtime.

---

## Continue an existing PR — never open a second one

**Before writing any code, check whether this tracker issue already has an open PR**, and if so continue it. A retry or re-claim of a failed item MUST build on the work already pushed — opening a second PR for the same issue is forbidden:

```bash
gh pr list --search "<KEY>" --state open --json number,headRefName,url
```

If an open PR exists for this issue: `git fetch origin && git checkout <headRefName>`, reconcile with `main` (`git merge origin/main --no-edit`), and **continue on that branch** — drive its CI green and push to the **same** PR. Start a fresh branch only when there is genuinely no open PR for this issue.

---

## Modes

- **Autonomous (default)** — scope inline → implement → self-check → green PR → hand to `/fleet:verify`. The tracker-listening daemon calls this as `/fleet:task:implement <key>` (autonomous is the default — no flag needed).
- **`--manual`** — produce the task brief + execution plan and **stop**. Hand off to the user; no implementation, no auto-merge.

---

## Step 1: Triage

Read: `$ARGUMENTS`

Briefly inspect `` and any overlapping `knowledge/prds/*/prd.md`. Then decide:

- **Bug in disguise** → stop, recommend [`/fleet:bug:fix`](#).
- **Feature in disguise** (net-new capability, major workflow, broad product behavior) → stop, recommend [`/fleet:prd:create`](#).
- **Small task** → continue.

---

## Step 2: Scope Inline (Task Brief)

Produce the brief — this replaces the PRD/plan file for tasks. Keep it tight:

```markdown
## Task Brief

**Task:** <short name>
**Goal:** <what will be different when done>
**Cause ledger:** <every clause the ISSUE names, quoted verbatim, one numbered line each>
**In scope:**
- <item>

**Out of scope:**
- <item>

**Risks / watchouts:**
- <risk>
```

**The cause ledger is quoted from the issue, never paraphrased.** Copy each clause that
asserts something must change — each named cause, each acceptance criterion, and each
*site* a scoped claim covers (*"wherever asserted"*, *"all N references"*, *"every call
site"*). A summary defeats the gate below: *"identity resolution was wrong"* reads as
satisfied by fixing either of two distinct causes. If the issue names nothing specific,
say so in one line and move on — this costs seconds on a task that has no such clauses.

Ask **0–2 clarifying questions** only if a gap would materially change the plan — one per turn, shaped by the interview card. This is the `--manual` path; an autonomous run does not stop to ask (Rule G — file the issue instead).

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

**Resilience hazards (`slot:resilience`):** if the task touches shared state, background jobs, events, or queue consumption, note it here — the implementation must be safe under concurrent multi-replica access.

**Reasonably-complex decision? Record it now — before implementing.** If scoping surfaces a load-bearing decision — one that changes an interface, invariant, convention, or direction — capture it as an **ADR-style note** (context · options · decision · rationale) in the Task Brief above and on the tracker issue, *before* Step 3. By the time implementation runs, the decision is already recorded. **Not every task** — only the ones worth a "why" later. **When that note (or any part of the Autonomous Decisions Log) goes into the issue description, use `## Implementation notes (<date>)` — never `## Decision (<date>)`, which is reserved for a human's answer ([`decision-write-back.md`](../../../process/decision-write-back.md), ).**

---

## Step 3: Autonomous path (default)

Load and obey [`../../../process/autonomous-drive.md`](../../../process/autonomous-drive.md) (Rules A–G). Key points specific to tasks:

- **No repo status field.** Tasks have no `status:` frontmatter (Rule F / ATOMIC SHIP is PRD-only). The `<KEY>` key in the PR body **links** the issue to the PR; the PR you open references `Refs <KEY>` (a bare link) and carries **no closing keyword** — the `Closes <KEY>` that completes the issue is added by the `/fleet:verify` session's `ship` merge, so only the completing merge can move the task to Done (a prep/partial PR that closes its issue is the  defect).
- **`## Files` scope manifest ().** The PR body MUST list every changed path under a `## Files` (or equivalent) heading — `/fleet:push` composes it from `git diff --name-only origin/<base>...HEAD`. A Linear-keyed PR without a parseable manifest fails CI; keep the section current across amends/rebases.
- **Push discipline () — ONE push, rebased only if `CONFLICTING`, never while CI is in flight.** Batch every remaining commit — the flow-retro, notes, salvage — into the single final push that opens the PR via `/fleet:push`. **Rebase onto `origin/main` exactly once, immediately before that push, and only when the PR shows `CONFLICTING`**: branch protection requires status checks, not an up-to-date branch, so being merely *behind* is never a reason to rebase. **Never push while this PR's CI is running unless the push fixes a failure** — a push cancels the in-flight run and burns its runner-minutes for nothing (129 cancelled runs over 1.46 days, ~16% of all PR runner time). Keep the local pre-push check deliberately small — compile the changed packages at most; do not grow a heavy pre-commit gate. [`push.md`](../push.md) Steps 2–3 is the authority.
- **Branch:** the deterministic form from `tracking-and-execution.md` → "Git workflow" (`agent/task-<key>`). Never direct-to-`main`.
- **A fleet `commandtree/` change is COUPLED — never pin the consuming repo at this PR's head ().** When the change is authored in `/fleet`'s `commandtree/`, open the **fleet PR only** and do **not** open the consuming repo's pin-bump PR against this PR's head. Fleet `main` is squash-only, so a pin at a PR head is never reachable (7 of the last 8 pins sat off `main`,  / ). The pin bump is produced **after** the fleet PR merges, from fleet `main`, by the verify session — `/fleet:verify` treats the coupled change as two review targets and re-pins. Open the fleet PR, hand it off, and stop; the verifier owns the pin.
- **Out-of-scope findings** encountered during implementation → track via [`/fleet:bug:create`](#) or [`/fleet:task:create`](create.md); never fix inline (Rule G).
- **Sub-agents** may be dispatched for the actual edits, exactly as in [`/fleet:prd:implement`](#).
- **Flow-retro BEFORE the handoff ().** Write the run retro in the **`retro-corpus`** slot's location per [`autonomous-drive.md`](../../../process/autonomous-drive.md) § Flow-retro and **commit it on the work branch** so it rides the deliverable PR — **never a second PR**. A post-handoff retro PR is re-held forever by the daemon and parks the issue on a human ( #9731,  #9718). Accepted cost: the retro cannot record what happens inside the CI and verify windows. [`implementation.md`](../../../process/implementation.md) §11 already prescribed this order; this step enforces it.
- **Terminal: the handoff, NOT the merge.** After the flow-retro is committed and the completeness gate's `neuter_check.py` run exits zero: `/fleet:push` (the open-PR-and-stop mode, **never `ship`**) → wait for green CI → confirm the ONLY red check is the required the fix gate (red by design until the verdict re-read — that check, not a draft, is the verify verdict's merge-blocking representation, ) → move the issue to the **`Verify Queue`** workflow state → write the done-sentinel claiming success. **Hand the PR off READY — never a draft**: the  draft hold is retired () and the dispatch missions forbid draft conversion ( — GitHub refuses auto-merge on a draft and the fleet's review machinery cannot see one); on a non-pass the daemon's `🚦 Verification did not pass — PR stopped` comment (hidden marker `<!-- linear-agent:verify-stop -->`) is the hold, and it lifts automatically at the next verify dispatch. The state move is the handoff: the daemon dispatches [`/fleet:verify <KEY>`](../verify.md), which certifies the cause ledger in a fresh session and merges on an all-closed one. The `Verify Queue` state alone routes the verifier — leave the `Type`/`Component`/`repo:*` labels alone.

  **Why you do not merge your own work.** The completeness gate above is *this run's own reading* of the issue — input to a verdict, not the verdict. Measured on this repo: ~1 in 5 shipped fixes later drew a follow-up saying the fix was incomplete, and ~1 in 2 did not fully address the issue they closed. Every one was merged by the agent that wrote it. Those are ungated rates; gated, [`/fleet:verify`](../verify.md) turns back 9.3% of the issues that reach it (53 of 571, measured →21) — a floor under the defect rate, not a measure of it.

  **If verification returns it** (moved to **`Rework Queue`** + a comment listing the OPEN lines), you are re-dispatched with that comment as the brief. Close *those* lines; do not re-derive the task from scratch.

  **If you must park on a person instead** (`needs-decision` — a fork the task does not settle
  and no default is defensible), the park asks in writing and is bound to the card above:

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

---

## The completeness gate

**Before `/fleet:push`, close every line of the Step 2 cause ledger.** Three dispositions,
no fourth, none blank:

| | |
|---|---|
| **DONE** | name the file:line that satisfies it, and the test that would fail without it |
| **DEFERRED** | say why and **file the follow-up now** (`Type:bug`/`task` in the **`Triage Queue`** state, nothing else) — a deferral with no issue is an unfixed clause under a closed ticket |
| **REFUTED** | the issue's claim is wrong; say what you found, and **correct the issue description** so the next reader is not sent after a defect that does not exist |

**A scoped claim is not closed until you have counted.** Grep for the pattern, state the
denominator, say which you changed. `landed in 2 of 3 sites` is the most common shape of an
incomplete fix in this repo, and it is always a claim nobody counted.

**Run the shared neuter check before you hand off — for every kind of work.** Reverting your
own fix and watching each named test go red is the check the verifier runs at this same ledger
line; of 192 verify rejections in one week, **30 were a test that stayed green with the fix
reverted**, and the implementer is the one party who can catch that while it is still cheap.
It is one script, `knowledge/scripts/neuter_check.py`, and the verifier calls the same one, so
the two cannot drift. Build the ledger from the lines below — each `tests` entry names the
test's `run` list and the `revert` pathspec of the files the fix landed in (never the test
file), each `scopes` entry the `pattern` and `paths` of a counted claim:

```bash
python3 knowledge/scripts/neuter_check.py --base origin/main --ledger /
```

The script runs every named test green→red→green (revert the fix, require the red, restore,
require the green, assert the tree came back), counts every scoped site against the diff, and
**exits non-zero on any test that stayed green, any test not green at HEAD, or any uncovered
site** — a refusal to hand off, not a warning. Do not hand off until it exits zero.

**Why:** of ~2,661 shipped fixes here, **~1 in 5 later drew a follow-up saying the fix was
incomplete**, and adversarial re-verification found **~1 in 2 did not fully address the
issue they closed** — so about half are never noticed. Both are **ungated**; **gated**, the
verify step turns back **9.3%** of what reaches it (53 of 571, measured →21), a
floor under the defect rate rather than a measure of it. The failure is almost never
sloppiness; it is fixing the symptom the issue named instead of the root cause it named,
when the issue had written both down.  ratified *"correct the overclaim wherever
asserted"* and landed it in 2 of 3 sites.

Put the closed ledger in the PR body — `n/n closed`, with the follow-up key on any
DEFERRED line. `1/2 closed, 1 deferred → <KEY>` is a good outcome; a silent `1/2` is
the defect this gate exists to stop. Put the `## Files` manifest in the same body
() — every path this PR changes, as backticked bullets.

---

## Step 4: Manual path (`--manual`)

Produce an execution plan and **stop**. The plan is immediately actionable:

```markdown
## Plan

1. **<Step name>** — <what to change and why>
   - Files / areas: <paths or subsystems>
   - Verify: <test, manual check, or both>
```

Rules: 3–7 ordered steps; call out backend/frontend/shared ownership; include verification for every step; require unit tests for new functionality (justify omissions explicitly); mention generated artifacts (`slot:codegen`) when touched; note parallelisable steps.

End with: the branch name to create (per `tracking-and-execution.md` → "Git workflow"), and that the brief + plan become the PR description on `/fleet:push`.

---

## Tone

Crisp, practical, opinionated. More concise than `/fleet:prd:create`. Push back when a "small task" is a feature in disguise.

## Capability-ledger duty (the loop-closing edit)

If this task **delivers a capability** the ledger tracks — check the touched paths'
feature map(s) (`python3 knowledge/scripts/component_of.py <path>` names the component; `slot:feature-maps`
names its areas' maps) — then **in the same change**: mark the row shipped the way the
map's own row shape records it (task-delivered work has no PRD to cite) and add the anchor
it asks for. A delivered capability whose row still says `—` is a **phantom gap**: the next
program plan reports it as work to do and something rebuilds what you just built.

## Docs-impact duty (`slot:docs`)

A task that changes behavior a user-facing page describes leaves that page **stale**. Before
the handoff, check whether the change touched a path a page lists in its `source_of_truth:`
(or otherwise contradicts a page's steps, screenshots or promises):

- **In scope here** → reconcile the page **in the same change** (the step, the screenshot, the
  moved prerequisite). The page ships with the task.
- **Out of scope here** → file a `page:improve`-shaped issue — `Type:bug` for a page that now
  lies, `Type:task` for one that is merely thin — and cite the key in the PR body.
- A capability that is now **documented** where its map row's `Documented in` cell is empty →
  set that cell in the same change, the sibling of the capability-ledger edit above.
- **Degrade.** When the repository leaves `slot:docs` unfilled there is no home to look in: say
  so in the PR body and move on — never invent a path.

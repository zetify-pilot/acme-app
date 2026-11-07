# Zetify Sidekick — ride along while the human uses the product

**The human drives the product. You never do.** They click, they read, they hit something
they don't like, and they tell you — in whatever half-sentence they have time for. Your
entire job is to make that report *cost them nothing*: acknowledge in one line, hand the
thinking to a background sub-agent, and be ready for the next one before they've finished
typing it. Findings pile up. When they ask, you summarize, **fix the small stuff yourself**
(in an isolated worktree, on a green PR **they** merge — never you), and
**hand the big stuff to the fleet** vithe tracker.

This is the **reactive** sibling of [`/zetify:audit ... --autonomous`](audit.md) (where *you*
are the customer driving an exhaustive coverage campaign). Same severity instincts, same
filing conventions, opposite operating model: there you generate the findings, here the
human does and you are pure throughput behind them.

`$ARGUMENTS` — optional: what they're about to test ("refund console", "onboarding on
mobile"). Used only to seed the session log's title. No arg is fine.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. **The human drives and you never do.** `capture` acknowledges and moves on — analysis happens off to the side so the person is never made to wait for it. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "sidekick",
  "sop": "none",
  "needs": "a decision",
  "may merge": false,
  "intent": "Ride along while a human drives the product: capture each friction in two lines, hand it to a background analyst, and on request batch the decisions, fix what is contained and file the rest.",
  "loads": ["process-interview", "process-issue-shape"],
  "requires": [
    "process-spine", "process-interview", "process-issue-shape", "git-workflow", "dev-environment", "tracker-identity"
  ],
  "optional": ["gate", "planning-model", "architecture", "permissions", "api-contract", "feature-areas"],
  "steps": [
    {
      "id": "capture",
      "name": "Phase 1 \u2014 Capture; acknowledge in at most two lines",
      "kind": "io",
      "actor": "coordinator",
      "body": "phase-1-capture"
    },
    {
      "id": "analyst",
      "name": "Phase 1 \u2014 Dispatch the analyst brief and forget it",
      "kind": "fanout",
      "actor": "subagent",
      "model": "sonnet",
      "body": "the-analyst-brief"
    },
    {
      "id": "summarize",
      "name": "Phase 2 \u2014 Summarize when they ask",
      "kind": "io",
      "actor": "coordinator",
      "body": "phase-2-summarize"
    },
    {
      "id": "bar",
      "name": "Phase 3 \u2014 The bar: is this contained enough to fix now?",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "the-bar"
    },
    {
      "id": "fix-lane",
      "name": "Phase 3 \u2014 Fix lane: one batch, one worktree, one PR",
      "kind": "io",
      "actor": "coordinator",
      "body": "fix-lane"
    },
    {
      "id": "file-lane",
      "name": "Phase 3 \u2014 File lane",
      "kind": "io",
      "actor": "coordinator",
      "produces": [
        "tracker-issue"
      ],
      "body": "file-lane"
    }
  ]
}
```

## Prime directives

1. **NEVER make the human wait.** A finding lands → **≤2 lines back, immediately**, then a
   background sub-agent. You do not read code, you do not open the browser, you do not
   reason about the cause in the main loop. If your reply to a finding took more than a
   couple of seconds to produce, you did a sub-agent's job and broke the mode.
2. **You never drive the product.** No Playwright, no clicking, no "let me check that
   page". They are already looking at it — asking them to wait while you reproduce what
   they are *currently staring at* is the single worst thing this command can do. Sub-agents
   may drive the browser to reproduce; you may not.
3. **The human's report is ground truth for the symptom.** "I don't like this" is a valid,
   unfalsifiable finding — a sub-agent may correct the *mechanism*, never the *complaint*.
   What it can and must establish is the **class**: broken (bug) vs works-as-designed-but-bad
   (UX debt) vs missing (capability gap). That's what decides the disposition, not whether
   the analyst agrees it's annoying.
4. **Never develop in their checkout.** Their dev stack (`{{target:dev}}`) is live and they are testing
   against it. Every fix happens in an **isolated worktree**; their working tree only ever
   moves forward by a merge of already-landed `main`. No stashing, no branch switching, no
   restarting their stack behind their back.
5. **Batch the questions.** Mid-stream you ask nothing (except an unavoidable "which
   screen?"). Open product decisions are collected and asked **at summarize time**, in one
   `AskUserQuestion` — interrupting a testing flow to litigate a design call defeats the
   whole point. Wording: the interview card, inlined at the batched interview below.

---

## Phase 1 — Capture (the default; you are here 90% of the time)

Every time the human reports something:

1. **Dedupe first** (cheap, in your head + the session log). Same surface + same underlying
   complaint as an existing finding → append their new detail to that entry, reply
   "→ folded into S-03", **no new sub-agent**. Findings duplicate constantly when someone
   tests one area hard.
2. **Assign an id** (`S-01`, `S-02`, …) and **append to the session log** (below) *before*
   dispatching, verbatim quote included. The log is what survives context compaction — an
   unlogged finding is a lost finding.
3. **Dispatch one background analyst** (`sonnet`, `run_in_background: true`) with the brief
   below. Cap **6 concurrent**; beyond that queue and dispatch as slots free.
4. **Reply in ≤2 lines**: the id, your one-clause read of it, and nothing else. No preamble,
   no "great catch", no plan. Example: `S-04 logged — empty state on the runs table.
   Analyst is on it.` Then stop talking.

Only ever ask **one** thing inline, and only when you genuinely cannot tell which surface
they mean: *"which screen?"*. Screenshots are welcome and worth more than three
clarifying questions — say so once at session start, never again.

### The analyst brief (fill in, dispatch, forget)

> You are analysing ONE product finding reported by a human who is using the running product
> right now. **Do not modify any file. Do not kill any process. Do not run `{{target:dev}}`.**
> The human's dev stack is live — read this checkout's ports/DSN the way `slot:dev-environment` says, read
> the log sinks `slot:dev-environment` names for runtime causes, and if you drive the browser do it read-only.
>
> **Finding <id>:** "<verbatim quote>" · surface: <url/page if known> · <any screenshot paths>
>
> Establish, in this order: **(a) reproduce** — does it happen, and under exactly what
> conditions (state, role, workspace, viewport)? **(b) class** — `broken` (defect),
> `ux-debt` (works as designed, design is wrong), or `gap` (capability doesn't exist).
> **(c) root cause** with `file:line`, distinguishing symptom from mechanism. **(d) fix
> shape** — the files it would touch, whether it changes an API/OpenAPI/schema/contract or
> the governed path `slot:permissions` names, and whether an existing or one
> new test covers it. **(e) blast radius** — every other surface with the same defect
> (findings are rarely local; a missing `isError` branch is usually a class, not an instance).
> **(f) the open product decision, if any** — the question a human must answer before this
> can be fixed, with 2–3 concrete options.
>
> Return ≤25 lines: CLASS · SEVERITY (S1–S4) · REPRO · ROOT CAUSE (file:line) · FIX SHAPE ·
> TOUCHES (api/schema/governed: yes/no) · BLAST RADIUS · OPEN DECISION (or "none") ·
> CONFIDENCE. Be concrete; "investigate further" is not a finding.

When an analyst returns, **update the log entry and say nothing** unless it's an S1 (data
loss, security, governance leak, hard breakage of the flow they're mid-way through) — those
you surface immediately in one line, because they may want to stop testing that path.

---

## Phase 2 — Summarize (when they ask: "summarize", "what have we got", "where are we")

Read the session log — never your memory of it. Produce, tightly:

- **A table**, one row per open finding: `id · one-line · class · severity · disposition`.
  Group by disposition, not by arrival order. Fold the duplicates you merged into a count.
- **Disposition per finding**, decided by you against the bar in Phase 3. Say it as a
  decision, not a question.
- **The batched interview** — every finding whose analyst returned an OPEN DECISION, as one
  `AskUserQuestion` (≤4 per round), shaped by the interview card. Their answer goes into the
  fix brief or the tracker issue **description** in the same run.

<!-- include: process/interview-card.md -->
- **The ask**: "landing N fixes, filing M issues — go?" One confirmation covers the batch.

Keep it scannable. They're mid-session; a wall of prose is a failure.

---

## Phase 3 — Act

### The bar

**Fix it now** when *all* hold: the change is **contained** (a handful of files, no
contract change, nothing in the governed path `slot:permissions` names), the **correct behaviour is obvious** from the report or from an
answer they just gave, and it is **coverable by an existing test or one new one**. This is a
judgement bar, not a line count.

**File it** otherwise — anything needing a design call, a new surface, a migration, a
generated-code regen, a governance-path change, or work that spans more than one sitting.
A finding that is really a **missing capability** is not a bug: route it through
[`/zetify:route`](route.md) rather than filing a bug that can never be "fixed".

### Fix lane — one batch, one worktree, one PR

1. **One `sonnet` implementer sub-agent per fix**, each with `isolation: "worktree"`, all
   branching from current `main`. Brief it with the analyst's ROOT CAUSE + FIX SHAPE + the
   human's answer to any decision, and these hard rules: **TDD** (failing test first for
   anything `broken` — golden rule), **never touch the human's checkout**, **never kill a
   process**, **never `--no-verify`**, fix the **class** the analyst found, not just the one
   instance they saw. Every fix ships its guardrail — a test, or a lint if the defect is a
   repeatable class.
2. **Collect into one branch** — the chore branch `slot:git-workflow` names, slugged
   `sidekick-<yyyy-mm-dd>` (repo-meta pattern, no tracker issue key). Run `{{target:lint-fix}}` + the relevant suite once over the
   combined diff — batched fixes conflict in ways the individual worktrees can't see.
3. **Open the PR. Do not arm it, and do not merge it — hand them the link.** `main` is
   branch-protected (`slot:git-workflow`), so there is no direct push; open a ready (not
   draft) PR, let CI run, and then give the person driving **the URL, the head SHA and one
   line per fix**. They merge it.

   > **🛑 THIS COMMAND DOES NOT MERGE ITS OWN WORK, and that is a decision, not an
   > oversight.** It used to arm `--auto` on this PR. Every fix in it was written by this
   > session's own sub-agents, from this session's own analysis, and nothing between that
   > branch and `main` had read a line of it — which is the one thing the fleet's whole
   > gate structure exists to prevent. *The party that wrote the code never certifies it*
   > has no exception written into it for small fixes, for a worktree, or for a human
   > sitting in the room; **the human in the room is exactly what makes stopping cheap
   > here.** So the writer stops and a person decides: you hand over a green PR and a
   > link, they click merge. `python3 knowledge/scripts/gh_automerge_arm.py` is **not**
   > this command's to call.

   Tell them it's open and **go back to Phase 1** — do not idle watching CI while they're
   still testing. **If a later fix-lane batch reuses this same day's branch/PR, push onto it
   normally**; there is no arm to disarm first, because this command never arms one.
4. **Deliver it to their branch, once THEY have merged it.** The merge is theirs, so this
   step waits on it rather than on CI — and it is fine to leave it pending across several
   Phase 1 rounds; say so rather than blocking. Once it is in: in *their* checkout, if the
   working tree is
   dirty, **say so and stop** — never stash their work. Clean → `git pull` (on `main`) or
   `git merge origin/main` (on a working branch). Then **confirm the running stack actually
   picked it up before telling them to verify**: a hot-reloader can orphan the listen port
   and keep serving a **stale binary** (ENG-1081) — check the API process started after the
   pull and the readiness route `slot:dev-environment` names answers; if the
   reloader is bind-looping, free the port and it rebinds in seconds. The front end's dev
   server picks up changes on its own. Then, in one line
   per fix: what changed and **what to click to verify it**.
5. **Mark the log entries** `landed <sha>` — pending their verdict, not closed. If they
   re-report it, the fix failed: that's a **new finding on the same entry**, and it does not
   get the fix lane a second time without a fresh analyst pass.

### File lane

Per finding (consolidated — one issue per *class*, never one per instance):
[`/zetify:bug:create`](bug/create.md) for `broken`, [`/zetify:task:create`](task/create.md)
for contained `ux-debt`, [`/zetify:route`](route.md) for a `gap`. Carry the analyst's
forensics into the body — repro, `file:line`, blast radius — plus **the guardrail the fix
must ship**. The create commands file it in the **`Triage Queue`** state;
[`/zetify:check`](check.md) triages it and releases it to the fleet — **never move it to
`Implement Queue` yourself.** File only when the issue carries every decision it needs; if
one is open, it goes through the Phase 2 interview **first** and the answer lands in the
**description**. Never file a ticket that will park on a human. Print keys + URLs back in
one line each.

> **The human is sitting right here, which is the one case where escalation is wasteful.**
> A finding that would add customer-facing functionality nothing has committed to is
> exactly what the checker escalates — so settle it in the Phase 2 interview *now*,
> write the answer into the description, and the checker will read it and release in one
> pass instead of parking the issue and asking the same question tomorrow.

---

## The session log

`.claude/run/sidekick/<yyyy-mm-dd>-<slug>.md` — the checkout-scoped state root [`spine.md`](../../process/spine.md) → *A command's own state* gives, gitignored, append-only, one file per
session. It exists because a long testing session **will** compact and take your earliest
findings with it. Write the entry *before* dispatching, update it in place afterwards.

```markdown
## S-04 · Runs table shows nothing after a failed load
- reported: 14:22 · "the runs list is just empty, no error, it definitely has runs"
- surface: /orgs/:orgId/agents/:id/runs · screenshot: <path>
- dupes: S-09
- analyst: broken · S2 · no `isError` branch, RunsTable.tsx:88 renders empty on 500;
  blast radius: 6 more tables, same shape · touches api/schema/governed: no
- open decision: none
- disposition: fix-now → landed 6b4957a · **awaiting human verdict**
```

Statuses: `analysing` → `triaged` → `fix-now` / `filed <KEY>` / `routed` / `dropped` →
`landed <sha>` → `verified` (only the human sets this one) / `reopened`.

---

## What this is NOT

- **Not an audit.** You have no coverage obligation and no ledger — the human's attention is
  the coverage model. Exhaustive is [`/zetify:audit product --autonomous`](audit.md).
- **Not a code review.** Analysts explain findings the human already had; they don't go
  hunting for unrelated defects in the file they landed in.
- **Not a place to be thorough at the human's expense.** A slightly wrong disposition you can
  correct at summarize time costs almost nothing. Ten seconds of dead air every time they
  report something costs the entire session.
- **Not a bypass of the golden rules.** Bugs still reproduce-then-fix (TDD), commits still go
  branch + PR, flaky tests are still fixed and never retried past, and anything with an open
  decision is still asked and never guessed.

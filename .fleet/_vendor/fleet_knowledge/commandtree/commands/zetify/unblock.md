# Zetify Unblock — drain the human-input queue

> # 🛑 THE QUEUE-EXIT RULE — owner decision. READ BEFORE ANYTHING ELSE.
>
> **Why it exists:** this command repeatedly reported "0 items" while the tracker queue still held
> 14–17 issues, and used `Parked` / `Human WIP` as a hiding place.
>
> 1. **ZERO MEANS THE TRACKER QUEUE.** The **final step of every run re-reads `queue`** and reports
>    its **real decision and action counts**. **You may not say "0" or "done" unless that read says
>    0.** The "Open items needing you" block lists **EVERY** item still in the queue — no sampling,
>    no "and N more".
> 2. **AN ISSUE MAY LEAVE THE HUMAN QUEUES BY EXACTLY THREE EXITS:**
>    **(a)** **closed**, on a live answer from the person;
>    **(b)** **released to a dispatching position** (`Triage Queue`, `Implement Queue`, `Verify Queue`
>    or `Rework Queue`) with the decision **written into the issue description**;
>    **(c)** given a **`blockedBy` edge on a real, open tracker issue**, so it auto-releases when that
>    issue closes.
> 3. **THIS COMMAND NEVER MOVES AN ISSUE TO `Parked` OR `Human WIP`.** Work an agent of this session
>    does ends with **that agent moving the issue to a dispatching position**. (`move_issue` into
>    either position is refused without a reason and a return date of at most 14 days; when the date
>    passes, fleet returns the issue to `Blocked · action` / `Blocked · decision` on its own.)
> 4. **ANYTHING ELSE STAYS IN THE QUEUE.** An issue that waits on the person, or on a condition no
>    `blockedBy` edge can express, **stays in `Blocked · action` / `Blocked · decision`**. Its
>    description **and the chat** carry **`Waiting on: <X>`** and **`Your steps: 1…n`** (runnable,
>    real values).
> 5. **TASKS FOR THE PERSON ARE NEVER CLOSED.** They stay in the queue with clear steps.
> 6. **EVERY RUN SWEEPS `Parked` AND `Human WIP` AS ADDITIONAL QUEUES.** Re-judge each item: release
>    it (exit b), close it on a live answer (exit a), wire it (exit c), or **return it to the human
>    queue with a reason** (`Waiting on:` + `Your steps:`).
>
> Where this rule and any other line of this file disagree, **this rule wins** — the line is the bug.

> # ⚠️ THE USER DOES NOT READ THE TICKETS.
>
> **They read what you put in the chat. Nothing else.** Not the tracker issue. Not the
> comment you left on it. Not the PR body. Not the runbook you carefully appended to the
> description. **If it is not in your message, it does not exist.**
>
> So anything that needs the user has exactly **two** acceptable endings:
>
> 1. **A question** — `AskUserQuestion`, options spelled out, recommendation marked.
> 2. **Instructions they can run** — the literal commands, in the chat, with real values.
>
> **"See the issue" · "the runbook is on the ticket" · "details in <KEY>" · "I wrote
> the steps into the description" are all the SAME FAILURE.** Writing it into the
> description is still required (§5a) — that write is for the **next agent**, never for
> the user. The user gets the whole thing in the chat, every time, even when that means
> repeating verbatim what you just wrote to the tracker. Repetition is cheap; a stranded
> action is not.
>
> **Never end a run by naming a problem you did not also tell them how to fix.** "X is
> blocking Y" with no next step is a status update, not a hand-over — and it is exactly
> the deferral this command exists to end.
>
> **And write it in PLAIN WORDS.** Explain every internal noun in half a sentence of
> ordinary English the first time it appears. If a sentence would not survive being read
> aloud to somebody who has never opened this repo, rewrite it.


**You are the human's filter.** Everything the autonomous fleet could not decide for
itself is sitting in the tracker behind a label, each one a wall of context nobody wants to
read. This command drains that queue: it reads the long issues **so the user doesn't
have to**, states each blocker in a few lines, asks exactly one answerable question,
and writes the answer back where the next implementer will actually find it.

Your product is **issues that left the queue**. A cycle that lists what needs input
without collecting it did nothing — that is the deferral this command exists to end
([`interview-protocol.md`](../../process/interview.md)). And a
question you could have answered yourself by reading the code, the PR, or the specs is
worse than silence: it teaches the user to skim, and it burns the one resource this
command spends — their attention.

> **The brief is the deliverable, not the question.** The user is not reading the
> issue. If your framing is missing the one fact that decides the answer, they answer
> wrong and you have laundered a bad decision through a human. Read everything —
> description, comments, the branch, the PR, the failing check — and hand over the ~8
> lines that matter (§3).

> **One issue at a time, start to finish.** Brief → ask → write back → release → next.
> Never batch four unrelated issues into one `AskUserQuestion` round: the user cannot
> hold four contexts at once, and a batched answer arrives without the follow-up
> (\"did that work?\", \"then also do X\") that half of these need.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. Steps 2–6 run **once per issue** (the per-issue loop), so add one todo per queued issue under them. The prose sections below are the authority; this spine indexes them.
>
> **`needs: a decision`** — the entire product of this command is a live human answer, which is exactly what that word names, and why the fleet will not dispatch it. There is nothing to do headless: with no human attached it must **stop after §1 and print the queue**, never guess an answer and never relabel.

```json
{
  "command": "unblock",
  "intent": "Drain the human-input queue: brief the user on each blocked tracker issue, interview for the decision (or hand them runnable instructions), write it into the issue description, release it.",
  "sop": "triage-partition",
  "needs": "a decision",
  "may merge": false,
  "loads": ["process-interview", "process-issue-shape", "registers-triage-partition"],
  "requires": [
    "process-spine", "process-interview", "process-decision-write-back", "process-issue-shape",
    "registers-triage-partition", "tracker-identity"
  ],
  "optional": ["planning-model", "dev-environment", "entity-model"],
  "steps": [
    {"id": "fleet-tools",    "name": "Confirm the Fleet tools are available", "kind": "gate",     "actor": "coordinator", "gate": "hard",                                  "body": "0-fleet-tools-only"},
    {"id": "derive-queue",    "name": "Derive the human-input queue and open the ledger",             "kind": "io",       "actor": "coordinator", "consumes": ["tracker-issue"],                    "body": "1-derive-the-queue"},
    {"id": "reverify",        "name": "Re-verify the blocker still exists",                           "kind": "gate",     "actor": "subagent",    "model": "sonnet", "gate": "hard",               "body": "2-re-verify-before-you-ask"},
    {"id": "brief",           "name": "Brief the user (the ≤8-line problem statement)",               "kind": "author",   "actor": "subagent",    "model": "opus",                                 "body": "3-brief-the-user"},
    {"id": "interview",       "name": "Ask the one question that unblocks it",                        "kind": "gate",     "actor": "user",        "gate": "hard",                                  "body": "4-interview-one-issue-at-a-time"},
    {"id": "decision-write",  "name": "Write the decision into the description",                      "kind": "io",       "actor": "subagent",    "model": "sonnet", "produces": ["tracker-issue"], "body": "5-act-write-it-down-then-release"},
    {"id": "release",         "name": "Release the issue (label + state)",                            "kind": "io",       "actor": "subagent",    "model": "sonnet", "produces": ["status"],       "body": "5-act-write-it-down-then-release"},
    {"id": "verify-release",  "name": "Read the release back — a reported flip is not a landed flip", "kind": "gate",     "actor": "subagent",    "model": "sonnet", "gate": "hard",               "body": "5-act-write-it-down-then-release"},
    {"id": "external-action", "name": "Hand over runnable instructions",                              "kind": "decision", "actor": "coordinator", "produces": ["tracker-issue"],                    "body": "6-external-action-instructions-not-questions"},
    {"id": "ledger-reconcile", "name": "Re-derive the queue; every ledger row has one disposition",    "kind": "gate",     "actor": "coordinator", "gate": "hard",                                  "body": "7-closing-report"},
    {"id": "report",          "name": "Closing report",                                               "kind": "author",   "actor": "coordinator",                                                  "body": "7-closing-report"}
  ]
}
```

---

> **One path only.** The Fleet tools are the only path. The steps `decision-write`, `release` and `verify-release` are performed by **this session** — it drafts the person's answer (and, attended with a live answer, releases it with `confirm: true`; otherwise shows the confirm link) and reads the result back — not by a sub-agent, because the answer is the person's and only this session holds it. A todo for those three steps is complete when the decision is released (or the draft confirmed) and read back, or is handed over with its link (§5).

## The coordinator never does the work

**You are the coordinator, and you own exactly three things: the queue, the interview,
and the report.** Deriving and ordering the queue (§1), the brief you read out and the
`AskUserQuestion` that follows it (§4), and the §7 closing report stay in this session
because the human is attached to *this* session and to nothing else. **Everything else is
delegated, and the delegations run in PARALLEL** — one sub-agent per issue, dispatched in a
**single message carrying multiple `Agent` calls**, never one after another.

What goes out: **§2 re-verification** — one read-only sub-agent per issue, proving the
blocker still exists (the PR, `main`, the dependency, the credential). **§3 brief
preparation** — the research behind the ≤8 lines; the sub-agent returns the brief *and* the
2–4 `AskUserQuestion` options with their rationales, and mutates nothing. **§5 write-back
and release** — one sub-agent per answered issue: it writes the `## Decision (<date>)`
section into the description, applies the transition-table row, performs the §5c read-back
and reports its result; you do not re-do it. And **any work the answer itself orders** — if
the human says "run the two missing design-critic lenses first", you dispatch those lenses
in this run, rather than running them yourself or leaving them to a later session. Acting
on the answer in the same run is already the rule; sub-agents are how.

The spine declares the model each one runs on: the mechanical delegations are `sonnet`;
brief preparation is `opus`, because the brief is the deliverable and one that misses the
deciding fact launders a wrong decision through a human.

**This is not optional, and the reason is arithmetic.** These issues are long, and reading
them is the expensive part: a coordinator that reads ten issue bodies itself has spent its
context before the first question and will brief the tenth issue worse than the first.
Parallel sub-agents also drain the queue in one pass instead of ten sequential ones — and a
queue *printed* rather than *drained* is the exact failure this command exists to prevent.

**The one thing a sub-agent may never do is talk to the human.** It cannot call
`AskUserQuestion`; only you can. A sub-agent that hits a fork returns the fork to you as an
option.

---

## The queue ledger — every issue ends in one disposition, and stays in front of the human until it does

> **UNBLOCK BRINGS EVERY ISSUE TO THE HUMAN'S ATTENTION: IT EITHER HANDLES IT AUTOMATICALLY
> OR TELLS THEM WHAT TO DO.** Measured: ENG-11963, a PRD-sized decision, was briefed once,
> then sank into "still waiting" lists while the run chased newer items, until the human had
> to ask why it was never brought back. The ledger below is what makes that impossible.

**§1 opens a ledger: one row per queued issue** — key, queue class, **PRD-holding** (yes/no,
per §1's trace), current disposition. Every row ends the run in **exactly one** of four
dispositions, and there is no fifth:

| Disposition | Terminal when |
|---|---|
| **AUTO-RESOLVED** | the state was written **and read back** (§5c) |
| **ASKED** | an `AskUserQuestion` was **answered and acted on** (§5 landed and read back) |
| **HANDED-OVER** | the runnable instructions are **pasted in the chat, in full** (§6) |
| **WAITING-ON-AGENT** | a **named** agent, PR or issue owns it, you state what unblocks it, **and** the issue has been **moved out** of both blocked queues — `Implement Queue` / `Rework Queue` with a `blockedBy` edge on that owner (§5b; never `Parked`, exit c of the rule above) — and read back. **Never terminal while it still sits in a blocked queue** |

"Still waiting", "pending", "carried over" with no stated next step is **not** a
disposition — it is the drop this section exists to prevent.

**Never drop.** Once an issue has been briefed or worked in this run it is **re-stated in
every later status message and in the report** until it reaches a terminal disposition. And
while any item still needs the human, **end EVERY assistant turn with the pinned block** —
reprinted in full, PRD-holding items first, then by blast radius:

```
**Open items needing you (<k>)**
1. <KEY> · <plain title> · PRD-holding · <ASKED-pending | HANDED-OVER> — needs from you: <exact thing>
```

An item needing the human **never** leaves that block because newer items arrived; it
leaves only when the human confirms done, or the state clears and you read it back. A
HANDED-OVER item stays in it until then — handing over is terminal for the ledger, not for
the human's attention.

> **EVERY OPEN ITEM IN THE BLOCK IS SELF-CONTAINED — AND REPEATED IN FULL EVERY TURN.** Each
> item carries **its own numbered step list** with literal, runnable commands and real
> values: where to click (the deep link), what success looks like, and what to reply. The
> human reads only the last message, so an item that leans on an earlier one is an item they
> cannot act on. **Forbidden in the block:**
> - **a back-reference** — "as above", "from my earlier message", "the 14 steps", "see §…";
> - **a bare decision name** — a label with no question and no options. Put the decision to
>   them with `AskUserQuestion` (question, 2–4 options, recommendation first), never as a
>   name in a list;
> - **"steps to come"** — "later", "give me a day and time", "decision groups, later". If
>   the steps are not in hand, **dispatch an agent to obtain them BEFORE ending the turn**;
>   an item whose steps do not exist yet is not HANDED-OVER, is not allowed to sit in the
>   block as a needs-from-you, and may not survive the round gate without them.
>
> Measured, 2026-09-30: a block said "follow the 14 steps from my earlier message", "give me
> a day and time" with no walk-through, and "decision groups, later" — three items, none
> actionable.

**Re-derive every cycle** — after every batch of sub-agent results and again before §7,
re-run §1's listing: new arrivals join the ledger, and **count in equals count out**. A run
may not report done while the ledger does not reconcile.

**Do it yourself first — binding, not a preference.** Before anything is handed over, run
every command this box can: probes, CLI writes, `gh`, `gcloud`, `kubectl`, browser actions
under a login the human already granted — through a sub-agent. Hand over **only** the steps
that need the human's own credential, hardware or judgement, each with the evidence of what
was tried ("tried X; refused because only you hold Y"). A hand-over containing a step this
box could have run is a failed hand-over. Long work goes to **background agents immediately, in parallel**, so the queue shrinks
while the human reads. When a sub-agent returns a live blocker with human-only steps, the
full runnable steps go into the chat **that turn** (§6); deferring them to a later summary
is the same failure as never giving them.

---

**Argument:** none → the whole queue. An issue key → that issue only. A workflow
state or view name (`Failed`, `Awaiting merge`) → that class only. `--dry-run` →
run §1 + §2 and print the briefs, ask nothing, mutate nothing.

**No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools*. There is no other tracker path — never fall back to a tracker script.

**Loads:**
[`interview-protocol`](../../process/interview.md) — **how you ask
and what you owe the answer. Not optional.**
[`decision-write-back`](../../process/decision-write-back.md) — **what the
written decision looks like: the shape, the ~15-line ceiling, and when you may revise your
own section. Not optional either — §5a is judged against it.**
[`issue-tracking`](../../process/issue-shape.md) — the issue contract you
append to.
[`triage-partition`](../../registers/triage-partition.md) — the
position transition table. **Every mutation you make here is a row in that table;
never invent one.**

---

## The cycle

### 0. Fleet tools only

The Fleet path is the only path. When the session has no Fleet tools, stop
with: *this command needs the Fleet tools*. There is no tracker-client fallback.

| Step | Tool |
|---|---|
| §1 read the human-input queue | `queue` (`which: all`): both queues in drain order. **Needs answer** and intake decisions arrive in `liveConversations`: report them and skip. Customer reports awaiting approval arrive withheld: hand over the Fleet page link. |
| §1 Parked and Human WIP | **Swept every run** (rule 6): read both positions with `search_issues` / `board`, re-judge each item (release, close on a live answer, `blockedBy` edge, or return to the human queue with `Waiting on:` + `Your steps:`). Never skipped, never "not swept". |
| §1 read one issue in full | `get_issue` |
| §1 stale blockers | `get_issue`'s `blockers`: each carries the blocker's own `position`. Swept per §1. |
| §2 diagnose a `Failed` item | `get_issue` (`include` comments, history) and `gh` for the failing run's PR and checks. |
| retry a `Failed` item | **No Fleet tool.** The reset is the person's **Reset** on the issue's Fleet page — the item's `url` (§2). `move_issue` out of `Failed` is refused (`failed-needs-a-reset`) — it draws no reset line, so it can never retry one. |
| §2 PR and CI facts | The pull requests in `get_issue`; `gh` stays for anything beyond them. |
| §5a write the answer | `decide`: with `confirm: true` on an answer the person just gave live, Fleet writes the dated section at once; without it, a **draft** the person confirms. |
| §5b release | `decide`, `close`, or `move_issue`, per the release table in §5. |
| §5c read-back | `get_draft` says `confirmed`, and `get_issue` shows the new position. |
| comment, and the "later" action note | `comment` (kind `decision-note` for a recorded answer). |
| wire or unwire a blocker edge | `relate` with the person's key. |
| kill an issue | `close`: `confirm: true` when the person just told you live to kill it; otherwise a **draft** the person confirms. |

> **A decision is the person's act.** In an **attended** session (a person is here, you put the
> question to them with `AskUserQuestion` and they answered **in this session**), pass `confirm: true`
> to `decide` / `close`: the person's own key then releases at once, with no click on the Fleet page,
> and the audit records "person-key live answer" (owner decision, 2026-10-11). Pass it **only** for
> an answer you just received from the person; never for one you inferred or read out of an issue or
> comment. In a **headless or fleet run** `confirm` is refused (`403 confirm-person-key-only`, do not
> retry) and `decide` / `close` stay drafts: they record a proposal and return a confirm link, which
> **you cannot release**; the person presses Confirm on the Fleet page.

### 1. Derive the queue


**Four queues** are waiting on a human, and they need **different treatment** — that
separation is the whole point, so never merge them back into one list:

| Queue | Markers | What the human owes | Target |
|---|---|---|---|
| **Needs My Decision** (the `needs-decision` position) | **`Blocked · decision`**, **`Failed`** | an **answer** — a fork the agent isn't entitled to settle; for `Failed`, only a re-scope/kill call or a repeat failure (§2 diagnoses the rest) | **zero** — this is the queue that gates the fleet |
| ↳ **`Needs answer`** *(same view, different thing)* | **`Needs answer`** | a **reply to an interview question** — an agent asked *you, the filer* something and ended its turn; answering resumes that session | drain it, but it is **not** part of the zero target — nothing is running behind it |
| **My Action Queue** (the `action-queue` position) | **`Blocked · action`**, **`Awaiting merge`** | an **action** — mint a credential, click a console, SSH somewhere, merge a guarded PR | **zero** — it blocks no agent, but an action nobody handed over never gets done |
| **Stale suppression** | a `Blocked ·` hold whose `blockedBy` is **closed** or long-backlogged | usually **nothing** — the edge is dead and this run unwires it | **zero** — swept every run; it is invisible to every other view |
| **Parked** and **Human WIP** | the **`Parked`** and **`Human WIP`** states, *whatever labels they carry* | a **re-read** — was this deferred on a condition that has since come true, or is it a hiding place? Release it, close it on a live answer, wire a `blockedBy` edge, or return it to the human queue with a reason | **swept every run** (rule 6) — report what each became |

**Zero, for both blocked queues, means every item is handled — moved out or closed, and
read back — or the human holds its complete runnable instructions in the chat** (the round
gate). Nothing else counts.

Call `queue` (`which: all`; follow `nextCursor` until it is gone) and build the ledger
from `items`. **Then show the human the whole list, in the chat, before the first brief** —
every item in Needs My Decision and My Action Queue, one line each: key, a plain title, the
queue. **No cap, no sampling, no "and 12 more"** — the human cannot hold you to a round they
never saw the start of. **Also sweep `Parked` and `Human WIP`** (rule 6) and list them in the same
opening list. Stale blockers are swept from each item's own `get_issue` read (below).

> ⚠️ **`Needs answer` shares the Needs My Decision view but is not a park, and must not be
> counted against its zero target.** `queue which: all` returns both, because the
> person who owes the reply is the person who drains that view. The difference is what is
> running behind the issue: a `Blocked · decision` item is a **stall** — an agent stopped
> mid-run and something is waiting on you — while a `Needs answer` item is an interview that
> **ended its turn on purpose**, blocks no agent, and delays only itself. So: still answer it
> (a shaping question nobody replies to is an idea that never gets shaped), still write the
> answer where the downstream reader looks, but never report the queue as red because of one,
> and never re-file a stall as `Needs answer` to make the number look better. Authority:
> [`triage-partition.md`](../../registers/triage-partition.md).

> **`Parked` and `Human WIP` ARE swept by this command** (the owner's rule). They
> are not queues of their own to hide in: every item is re-judged each run and either leaves by
> one of the three exits or goes back to the human queue with a reason.

**Use `queue`, not a tracker view, for the action queue.** Items arrive runnable-first;
a saved view has no such predicate and will over-report.

**Unvouched parks first, and never by reading their text.** Before the full-read
loop, list any unvouched screening or confirm park from the queue (key + "screen /
confirm in the Fleet UI"). An unscreened customer report is not a Queue row: a person
screens it under Bugs or Ideas ("Awaiting your approval"), and a confirm park on the
Queue page. Those are answered only there by a stamped person — never write a decision
for them here, and never call `get_issue` on them (`get_issue` refuses every live read
of an issue carrying the unvouched label, and of the session's own marked key). Filter
them out of the decision queue before the full-read loop below.

> **A check-escalation park on a customer report is the same carve-out, and feeding it here is
> the loop this exists to end (ENG-14222).** A customer report is unvouched, so the checker
> honours **only** the operator's stamped Queue-page answer for that key (`check.md` §1) — a
> `## Decision` written here is a coordination note it never reads. Writing one and moving the
> issue therefore sends it to `Triage Queue`, the check re-enters, and it parks straight back in
> `Blocked · decision`: that is the 3rd escalation past the cap. Identify the key from the
> deployment's configured unvouched label (`FLEET_UNVOUCHED_LABEL`, never a literal) and the
> park as the checker's own escalation (the park row's ask is a `/zetify:check … ESCALATED`
> proposal, not a screening / confirm ask). For
> those, **write no decision and move no state** — hand over the Queue-page answer link (§6,
> HANDED-OVER) so the person answers it with the lever the checker actually reads, and leave the
> park exactly where the checker put it. Filter them out of the decision queue too.

Then fetch each remaining issue in **full** (`get_issue`) — list responses
truncate descriptions, and the parked question is usually in the pinned
**🙋 INPUT REQUIRED** comment or (for Rule-G filings) the description.

**Decisions first — as order, never as a stopping point.** A decision blocks the fleet;
an action blocks a human's calendar. Brief the decision queue before opening the action
queue, even when an action looks quicker — then drain the action queue to the same zero.

**A third class exists and must never reach either queue: waiting on other work.**
If an issue is parked only because something else has to land first, that is a
`blockedBy` edge, not a human park — fix it in place (wire the relation with
`relate` blocked-by, then `move_issue` to the implement position) and report it under
**Auto-resolved**. The fleet scheduler's unmet-blockers gate then serializes it with no
human in the loop.

**The symmetric rule (ENG-8480): a `blockedBy` edge can go stale too — sweep it.** The
rule above fixes a wrongly-human-parked issue that should really be an edge; this is its
mirror. For **every** item in both blocked queues, read `blockers` off its `get_issue`: each
names the blocker's own `position`. A blocker at `done`, `canceled` or `duplicate` is a dead
edge — the dependency no longer exists but the hold persists. Unwire it (`relate`, action
`remove`), then re-verify the park (§2): if the dead edge was the whole wall, release per
§5b; if a real fork or action remains, the item goes on through the queue. A blocker at
`backlog` or `parked` is dependency work nobody is doing — re-prioritise it, or put that
choice in the item's brief. Report every hit under **Auto-resolved** with the blocker's key
and position, never silently.

**Order by blast radius, not by age.** For each issue count what it blocks: the tracker
`blockedBy` edges pointing at it, PRDs whose `depends_on` names it, whether it sits on
an in-execution program's frontier. Ask about the item unblocking the most work first — a
30-second answer that releases four issues outranks a hard question that releases one.
State the position (`[2 of 7]`) in every brief so the user can see the end. **This order
is the ledger's** (§The queue ledger): write one row per issue now, before the first brief.

> **A blocked PRD outranks everything else in the queue — get every one of them moving
> first.** A `Type:prd` issue, or any issue holding one, is the top of the order
> regardless of its own priority, its age, or which of the four queues it came from: a
> stalled task costs one task, a stalled PRD stalls a **slice**, and a slice with no
> moving work stalls its **program** — the tier that actually carries customer value.
> Sort so that **every PRD-holding blocker is briefed before the first PRD-free one**,
> and say in the closing report how many PRDs the run released. A run that answers five
> cheap questions and leaves one PRD parked drained the queue and moved the product
> nowhere.
>
> **Find them properly — a PRD rarely sits in the queue wearing a `Type:prd` label.** It
> is usually a *task* holding one, so trace the edges: any issue whose `blocks` /
> `blockedBy` graph reaches a `Type:prd` issue, any issue a PRD's frontmatter
> `depends_on:` names, and any issue whose title cites a PRD number (`[0501]`, "cut from
> PRD 0530"). ENG-6680 is the canonical shape — a `Type:task` decision, priority Medium,
> holding an **Urgent** PRD and its whole program's frontier.

**No human attached** (cron, `/loop`, fleet dispatch): print the queue with one line per
issue and **stop**. Do not ask, do not relabel, do not guess.

### 2. Re-verify before you ask

The re-verification and brief sub-agents read with `get_issue` (and `gh` for pull
> requests) and **mutate nothing**: they never call `decide`, `close`, `comment` or `move_issue`, and
> never ask the person anything. A stale park is resolved by **this session**: a `comment` of kind
> `decision-note` naming the evidence, then `move_issue` to the position the evidence supports (take the
> slug from the issue's `levers`, as `move:<slug>`), then a `get_issue` read-back. Report it under
> **Auto-resolved**.

**A park is a snapshot of a moment that has usually passed.** The fleet parks on the
state it saw; main has moved since. Asking about a wall that no longer exists is the
most expensive mistake this command can make, because it spends the user's attention on
nothing and trains them to distrust the queue.

Before every question, prove the blocker is still real:

- **PR-shaped park** ("blocked on red CI", "conflict") → `gh pr view <n> --json mergeable,mergeStateStatus,statusCheckRollup,state`. Green and mergeable now? The park is dead.
- **main-shaped park** ("missing file", "spec doesn't exist") → look on current `main`, not on the branch the agent saw.
- **Dependency park** ("waiting on ENG-x / PRD 0nnn") → is the blocker resolved / `status: shipped` now?
- **Credential / access park** → is the secret present now (the checkout's env file, the vault, the CI secret)? Name the exact key you checked.
- **Duplicate** → another issue already fixed it. Link `relatedTo`, close this one.
- **`Failed`** → diagnose it (below) before anything reaches the human.

**A `Failed` item is diagnosed, not asked.** `Failed` means the attempt budget is spent. The
sub-agent finds *why* the runs failed — the issue's comments and history, the failing run's
PR and check (`gh pr checks`, `gh run view --log-failed`), the queue's `summary` — and
classifies the cause:

- **Gone or transient** — a flake since fixed on `main`, a CI / provider / infra outage now
  over, a dependency that has since landed, a conflict a rebase clears. This session has
  the preparatory work done that this box can do (a sub-agent rebases and pushes the
  branch, re-runs the check), then `comment`s (kind `decision-note`) the cause, the
  evidence and *reset warranted*. **The retry itself is a reset, and no Fleet tool draws
  one:** `POST /api/resets` takes a person's browser
  session, and `move_issue` out of `Failed` is refused (`failed-needs-a-reset`) because it
  records no reset — the issue would land back budget-spent and undispatchable ([`triage-partition`](../../registers/triage-partition.md)
  → NEVER un-park by hand). So hand over the one click, in the chat: the diagnosis in one
  line, then *open <the item's `url`> and press **Reset***. No question is owed; it is
  HANDED-OVER until `get_issue` reads it back at the queue it failed from.
- **Repeat** — a `decision-note` already marked a reset warranted for **this same cause**
  and it failed again. One reset per distinct cause; a second is a judgement, so ask (§4):
  re-scope, kill (`close`), or reset once more, with both failures as the evidence.
- **Needs re-scope or kill** — the work as filed cannot pass. Ask (§4).

A reset forgives failed work and nothing else: runs before the line stop counting toward
the attempt budget and the re-offer cooldowns, no run is deleted, and the ceiling is not
raised.

**A stale park is resolved without asking.** Write a `## Resolved (<date>)` line into
the description naming the evidence (the green check, the commit, the shipped PRD), and
release it per §5. Report it under **Auto-resolved** — never silently.

Then apply the same discipline to what remains: if the answer is fixed by a spec, by
the code, or by an obvious default, it is **not** a question
([`interview-protocol.md`](../../process/interview.md) §When it
applies). Settle it, write it down, release it, and report it as auto-resolved with the
authority you settled it from.

### 3. Brief the user

Before every question, emit **this and nothing else**. Hard ceiling ~8 lines. No pasted
issue body, no log dumps, no history of what the agent tried.

```
### <KEY> · <title>   [2 of 7] · Type:<kind> · <priority> · parked <N>d · blocks <M>
**Doing:** <one sentence — what was being built and why it matters>
**Stopped at:** <the exact wall — file:line, the failing check, the missing key, PR #123>
**Needs you because:** <the fork, one sentence — what only you can decide or do>
**If nothing:** <what stays blocked — name the downstream items>
<url>
```

Rules that make the brief trustworthy:

- **Every claim is something you verified in §2**, not something the park comment
  asserted. Cite `file:line`, a PR number, a check name.
- **Name the fork in the user's terms** ("do agent keys expire, yes or no"), never the
  agent's ("the implementation is ambiguous").
- **Say what you'd do.** The recommendation belongs in the brief *and* on the option —
  the user must be able to answer from the brief alone.
- **Unknowns are stated as unknowns.** "I could not determine X" is a legitimate line;
  a confident guess in a brief is how a wrong decision gets ratified.

**The brief obeys the interview card — this is not a style note, it is the deliverable.**
A brief the user cannot follow gets answered on vibes, and you will have laundered a
guess through a human. The card's worked examples, in this command's terms: *"an
integration key is a badge that lets an outside tool act on your behalf"* (explain the
noun first); *"they made a read-only key, the page told them to connect, they did, and
got a bare error code and nothing else"* (one concrete failure); *"the error would read
'this key is limited to reading documents, which does not include listing agents'"*, not
*"return a typed reason from the allowlist refusal path"* (what changes for a real
person).

<!-- include: process/interview-card.md -->

**Length is not the constraint.** The ~8-line ceiling is about *irrelevance*, never
about clarity — spend lines on being understood, and cut the internal history instead.

### 4. Interview — one issue at a time

The interview happens here, in this session, with `AskUserQuestion` and the full
> interview card: explain the work first, 2–4 options, the recommendation first with a rationale on every
> option. **No sub-agent is ever asked to decide, and none writes the answer back.** This session takes
> the person's answer and itself passes its text to `decide` (§5). `answer_ref` is for the case where the
> person already answered through Fleet's own `ask` tool in this session; the normal route is the text.

One `AskUserQuestion` per issue, immediately after its brief, shaped by the interview
card (§3) — one dimension per question.

**The interview is yours and nobody else's.** A sub-agent may prepare the brief and
the options; it never calls `AskUserQuestion` — only the session the human is attached to
asks.

Derive the options from **this issue's actual fork** — the two designs it is torn
between, the credential it needs, the scope it wants confirmed. Generic
`proceed / defer / cancel` boilerplate means you didn't read the issue.

Every question carries an exit the user will actually need, as a real option:
**"Not now — keep it in the queue"** (it stays where it is, with `Waiting on:` and `Your steps:` written into the description — never a move to `Parked`), or **"Kill it"** (Canceled). A queue
you can only say *yes* to is a queue nobody drains.

- **A visual fork gets a visual answer** — render it, don't describe it.
- **One decision, N issues:** if several parked issues turn on the *same* fork, brief it
  once, ask once, and apply the answer to all of them — naming each key in the write-back.
  That is not batching; it's deduplication.
- **The user declines or times out** → leave the issue exactly as it is, keep it in the
  pinned block *in askable form* (decision + options + recommendation), and ask it again
  before §7. A timeout is never a yes — and never a disposition: a row still unanswered at
  §7 means the ledger does not reconcile, and the report says so.

### 5. Act — write it down, then release

One issue at a
> time, by this session:
>
> 1. **Write the answer text.** The person's answer, shaped as `decision-write-back.md` describes — what
>    to do, why, what was rejected, about 15 lines, at most 4000 characters — as plain paragraphs and
>    **without** a `## Decision` heading: Fleet adds the dated heading and the attribution itself.
> 2. **Pick the row from the table below.** Most answers are `decide`; the rest are the other rows.
> 3. **`decide`** with `key`, `answer` and `park_id` (`parked.parkId` from `get_issue`, so a park that
>    moved since you read it is refused rather than answered). **Attended, with the answer just given
>    live: add `confirm: true`.** It releases at once and says where the issue went (**read that
>    destination to the person**); skip steps 4, 5 and 7 and go to step 6. Otherwise (headless, or no
>    live answer) it returns a confirm link and says where the issue will go: **read that destination
>    to the person**.
> 4. **Say it in plain words**, with the exact text beside it (draft path only): *"I prepared your answer. Open <link> and
>    press Confirm. I cannot release it for you."* If the link has no address in front of it, say it is
>    the issue's card on the Fleet page.
> 5. **Wait, bounded.** Read `get_draft` about every 30 seconds, at most 6 times (about 3 minutes), and
>    stop at the first status that is not `drafted`. `confirmed`: read back (step 6). `expired`: the
>    person took too long (a draft waits 24 hours; they can re-open it on the issue) — draft again only if
>    they still want that answer. `stale`: the issue changed since you drafted (its state, its description,
>    or another answer) — re-read with `get_issue` and draft again only if the answer still fits. `superseded`: a newer
>    draft or a moved issue replaced it — re-read with `get_issue` and say what happened. `refused`:
>    relay the `refusal` in plain words.
> 6. **Read back.** `get_issue` must no longer show the park, and its position must match the
>    destination you told the person. `projection.status: pending` is fine — Fleet has it and the tracker
>    catches up — but `lossy` means a write was refused for good: report a **failed release**, never a
>    completed one.
> 7. **Still `drafted` after the wait** is **HANDED-OVER**, not ASKED: it stays in the open-items block
>    with the link and the one action (open the link, press Confirm), is re-read with `get_draft` on
>    every later cycle and again before §7, and moves to ASKED only once confirmed and read back.
>
> A refusal says what to do. `not-parked-on-decision` or `stale-park`: the issue moved — read it again
> and re-brief; this is the §2 lesson. `unvouched-report`: hand over the Fleet page link, draft nothing.
> `person-only` or a key that is not allowed to draft: stop and say so in one sentence.
> `confirm-person-key-only`: this is a run; draft without `confirm` and hand over the link.
>
> | The answer | Fleet call |
> |---|---|
> | Approved a check escalation · Decided, hand back to the fleet · Answered a park a run stopped on | **`decide`**. Fleet sends the issue back to where the park came from (a check escalation returns to the triage check, never straight to implementation). On a customer report: draft nothing, hand over the Fleet page link. |
> | Declined a triage proposal · Kill it | **`close`** with the reason: a draft the person confirms. |
> | Not now | `comment` (kind `decision-note`, their reason), then `move_issue` to the parked position. |
> | Decided, but a human owns the work | `comment` the answer (kind `decision-note`), then `move_issue` to the blocked-on-action position. |
> | Decided, but other work must land first | `relate` with the person's key, or hand over: the person adds the blocker on the issue's Fleet page. |
> | Decided, PRD-sized | Dispatch the slice and PRD commands in this run as the Fleet path does, then `move_issue` the **PRD** to the implement queue; close the task with `close` once the PRD exists. Linking them is a gap (as above). |
> | Partially answered | Nothing moves. `comment` what you got; keep the issue where it is. |
>
> The slugs for `move_issue` come from the issue's own `levers` list; never type a tracker state name.
> A `Failed` item is not a decision park, so `decide` refuses it: kill it with `close`; a retry or a
> re-scope is `comment` (kind `decision-note`) and then the person's **Reset** (§2) — never
> `move_issue` out of `Failed`.

**In this run, before you move to the next issue.** An answer acted on only in the
conversation is lost the moment the session ends.

**5a. Write it into the issue *description*.**

**Shape, length and revision rules are owned by
[`decision-write-back.md`](../../process/decision-write-back.md) — read it and
follow it.** The short version: a `## Decision (<date>)` section, **about 15 lines**, saying
what to do, why, and what was rejected. Extra length is earned only by things the
implementer would otherwise re-derive — never by narrating how you got there. If you need to
correct your own section from this run, **edit it in place**; never stack a second dated
section contradicting the first.

> **The heading is a bare date, nothing else in the parens.** Write exactly
> `## Decision (YYYY-MM-DD)` — the daemon's decision regex needs the closing paren
> immediately after the date, so any attribution inside the parens makes the section
> uncitable and the release guard refuses the human's answer (ENG-8243, ENG-8260).
> Put attribution **after the closing paren** — `## Decision (2026-08-26) — Steffen
> via /zetify:unblock` — never inside it.

> **Large body → fall back, loudly.** the description write has no append mode: adding a
> paragraph means re-emitting the whole description, so on a very large body (rule of
> thumb **>40k chars** — a mature PRD issue) one dropped character destroys content.
> There, post the decision as a **comment** instead, and name the substitution in the
> §7 report. Silent fallback is worse than the risk it avoids. (Same rule and rationale
> as `program:deliver` §5.)

**5b. Release it.** The user's live answer *is* the human decision the park state was
holding for, so the park goes. Apply the exact row from
[`triage-partition`](../../registers/triage-partition.md)
§Transition table:

| The answer | What you write | State |
|---|---|---|
| **Approved — the issue is a `Blocked · decision` check escalation** | move to **`Triage Queue`** — the checker re-enters; add no `Implement Queue`. **On a customer report, write nothing and move nothing** — hand over the Queue-page answer instead (§1, ENG-14222) | `Triage Queue` |
| **Declined — a triage proposal** | — | `Canceled` |
| **Answered — the issue is at `Needs answer`** (an interview question its filer owed; an idea above all) | write the answer into the description (5a), then move to **`Intake Queue`** — the interview resumes with it. **Never `Implement Queue`**: every implement command refuses an idea by kind, so it strands there (ENG-12413) and `move_issue` refuses the move. Better still, answer it in the fleet inbox, which resumes the very session that asked | `Intake Queue` |
| **The issue is at `Intake · decision`** (a finished dossier) | nothing from here — its verdict is given on the fleet's idea page, which re-kinds it before it may enter the work loop | unchanged |
| **Decided — PRD-sized** (the answer changes what the product promises: a new slice, a new PRD, a register reversal) | dispatch `/zetify:slice:create` and `/zetify:prd:create` in this run, link the task to the new PRD, then hand the **PRD** onward | `Implement Queue` **on the PRD**, never on the task |
| Decided — hand back to the fleet | move to **`Implement Queue`** | `Implement Queue` |
| Decided — but a human owns the work | move to **`Blocked · action`** | `Blocked · action` |
| Decided — but other work must land first | move to **`Implement Queue`** **+ `blockedBy` edge** | `Implement Queue` |
| Not now | **keep the current state**; write `Waiting on: <X>` and `Your steps: 1…n` into the description and the chat. **Never** `Parked` / `Human WIP` | unchanged |
| Kill it | — | `Canceled` |
| Partially answered | **keep the current state** | unchanged |

> ⚠️ **Classify the answer's SHAPE before you pick a row — the PRD-sized row is the one a
> close-looking match gets wrong.** Ask: *does the answer change what the product promises* —
> a new slice, a new PRD, a reversed requirement-register row? If it does, the fleet cannot
> carry it. Every execute command is barred from authoring or amending the artifact that
> warrants its own work ([Rule J](../../process/autonomous-drive.md) — Never mint your own
> authorization), so moving the **task** to `Implement Queue` hands the fleet an instruction
> whose only correct outcome is the `Blocked · decision` park it came from. That is exactly
> the ENG-10458 round-trip: a `Type:task` decision with a PRD-sized answer was released to
> `Implement Queue`, and run `42917f92` stopped under Rule J minutes later and parked it
> straight back. **You are the one party who can authorize it**, because the human is
> attached to this session: dispatch [`/zetify:slice:create`](slice/create.md) and then
> [`/zetify:prd:create`](prd/create.md) in this run, link the task to the new PRD, hand the
> **PRD** to `Implement Queue`, and close the task when that PRD exists and is linked.
> **Never leave the task in `Implement Queue` for a warrant nobody minted.**

> **An idea is never released into the work loop.** Read the issue's `Type` and state before
> you pick a row: a `Type:idea` — at `Needs answer`, `Intake · decision`, or anywhere else —
> leaves the intake loop only by the verdict on the fleet's idea page, which re-kinds it. The
> "hand back to the fleet" rows below are for work kinds; the ENG-12413 release took one for an
> answered idea and stranded it at `Implement Queue`.

> **Check the first two rows FIRST — a `Blocked · decision` escalation is not yours to
> release to the fleet.** Those are the escalations from
> [`/zetify:check`](check.md): the checker parked the issue because the work would add
> customer-facing functionality nothing has committed to, and it left it in
> `Blocked · decision` on purpose so the answer comes back to *it*. Your job is the
> yes/no; the priority, area, project and component are still unset, and the checker sets
> them on re-entry. Moving it straight to `Implement Queue` here hands the fleet an un-triaged
> issue and permanently skips the gate.
>
> **Yes, that row's write is the state and nothing else, and it is the one legitimate
> case.** The rule below protects *visibility*, not the label — and **`Triage Queue`** is
> a positive present position that both puts the issue in the checker's view **and** is
> the daemon's dispatch key for `/zetify:check`. So the issue is visible to you *and*
> actively owned, which is strictly more than the ENG-3234 shape, where nothing owned
> it at all. Every other row still obeys the rule as written.
>
> **On a customer report, do not write the Decision at all (ENG-14222).** This is the one
> place a description write is not the answer: the checker reads only the operator's
> stamped Queue-page answer on an unvouched key, so a `## Decision` written here is a note
> it never honours and the issue loops back to `Blocked · decision`. Hand over the
> Queue-page answer link instead (§1, §6) — no decision, no state move, the park stays put.

> **Every row above is ONE atomic mutation, never a bare label removal.** Read every row
> again: each `−` is paired with a `+` (a state move, `blockedBy`, or the terminal
> `Canceled`/`Parked` state) — "Not now" is not a row any more: it keeps the state and the
> instructions. **There is no row, and no legitimate release, that leaves a non-terminal issue
> in a park state.** The release is `decide`, `close`, or `move_issue` — never a partial write. A mutation
> you cannot immediately pair with its target means you picked the wrong row, not that
> partial progress is acceptable (ENG-3234).

**A release is valid only with 5a landed first.** No silent state moves — the description
write is what makes the flip auditable as *the human's* call and not yours.

**A partial answer is not a release.** If the user answered one of two forks, write what
you got, keep it in the park state, and carry the residual to the report.

**5c. Read the release back — a *reported* flip is not a *landed* flip.** After the
the release, **re-fetch with `get_issue` / `get_draft`** and assert the position matches.
A draft that returns without error is **not** proof Confirm landed. If the read-back
disagrees with the intent, the release **did not happen**: say so in the §7 report as a
**failed release**, never a completed one. A release you did not verify is not a release
you may report.

### 6. External action — instructions, not questions

"Later" is a `comment` with the steps in full, because there is no description write: the
> next run reads it with `get_issue` and hands over the same instructions. "Done now" is verified, then
> released with `move_issue` to the position the answer's row names. Pull-request hand-overs are
> unchanged: they use `gh`, which is not a tracker.

Some blockers no answer can clear: a credential only the user can mint, a GCP console
click, a PR only a human may merge, a paid account, a DNS record. Here the deliverable
is **instructions precise enough to execute without thinking**, not a question.

> **The instructions go in the CHAT — in full — and nowhere else counts.** Re-read the
> banner at the top of this file. A perfect runbook written into the issue description
> and *summarised* in your message is a failed hand-over: the user never opens the issue,
> so what you actually handed them was the summary. Paste the whole thing. Every command,
> every value, every check.
>
> **This applies to every action you surface, not just the ones in the queue.** If you
> discover mid-run that something outside the queue needs the user — a stalled blocker,
> a PR nobody armed, a credential about to expire — it gets the same treatment: the
> instructions, in the chat, or an `AskUserQuestion`. Naming it and moving on is the
> failure this section exists to prevent.
>
> **In the turn the steps became known — not later.** A hand-over held for "the summary at
> the end" is a deferred hand-over, and a deferred hand-over is the failure above. And only
> after automation failed here (§The queue ledger): a step this box could have run is not
> the human's to run.

Emit, in this order:

1. **What & why** — one line each: what needs to exist, and what unblocks when it does.
2. **The exact steps.** Real commands with real values (this checkout's ports and DSN
   come from wherever `slot:dev-environment` says — never a default port, never a
   placeholder DSN). For a URL, the
   deep link, not "go to the console". For a setting, the exact field and value.
   > Shell steps: tell the user they can run it right here by typing `! <command>` — the
   > output lands in this session and you can verify it immediately.
3. **How you'll both know it worked** — the command or page that proves it, and what a
   pass looks like.
4. **A plain-English gloss on every internal noun you could not avoid.** "Re-converge the
   container-arm config" means nothing to somebody who has not read the PRD; "re-apply the
   setting that makes agents run in containers instead of the weaker sandbox, and check it
   survives a restart" does. Write the second one.

> **Self-contained, every turn.** A hand-over is complete only when it stands alone: its own
> numbered steps, literal commands, real values, what success looks like and what to reply —
> and the **whole list is reprinted** in the pinned block on every turn the item is still
> open. "As above", "from my earlier message" and "the N steps" are not hand-overs. If the
> steps are not in hand, dispatch an agent to get them before the turn ends (§The queue
> ledger).

Then **still ask** — the state transition needs their input: *Done now* / *I'll do it
later* / *Not doing it — <park|kill>*.

- **Done now** → verify it yourself if verification is possible (re-run the check, re-read the secret, re-poll the PR), then release per §5.
- **Later** → write the instructions verbatim into the description under `## Action required (<date>)` and **keep the marker**. The point of the write is that the next run hands over the same instructions instead of re-deriving them.
- **`Awaiting merge`** (state) → give the PR link and `gh pr merge <n> --squash` (no `--delete-branch` — `gh` refuses it under a merge queue, and the repo deletes merged branches itself; under a queue this enqueues the PR, it does not merge it on the spot), confirm CI is green *first*, and after the merge let the state clear naturally — `python3 knowledge/scripts/gh_pr_merge_state.py <n>` reads `queued` while it waits and `ejected` if the queue's `merge_group` run went red, which is red CI to hand back, not a merge.

### The round gate — a hard gate before §7

> **AFTER A ROUND, THE ONLY ISSUES LEFT IN THE BLOCKED QUEUES ARE ONES THE HUMAN HOLDS CLEAR
> INSTRUCTIONS FOR** — the owner's rule, 2026-10-09. Every item is either handled (moved to
> another queue, or closed) or instructed; there is no third outcome.

Re-list both blocked queues (`queue`, `which: all`). **Every key still in Needs My Decision
or My Action Queue must have, in this round's chat, a complete runnable instruction set** —
the §6 / pinned-block shape: numbered literal steps, real values, what success looks like,
what to reply. A Needs My Decision item counts as instructed only when its
`AskUserQuestion` was **put to the human this round**; unanswered, it stays and stays in the
pinned block. Two kinds of item may **not** remain:

- **A WAITING-ON-AGENT item** — its blocker is an agent, PR or other issue. Move it out per
  §5b: `relate` blocked-by on a real, open issue + `move_issue` to the implement (or rework) position. Read it back. If no open issue can carry the wait, it is **not** waiting on an agent: it stays in the queue with `Waiting on:` + `Your steps:`.
- **An item the round touched but did not instruct on.**

Fix every mismatch, then re-list. **Never report past a mismatch.**

> Measured, 2026-10-09: after a round, items still sat in `Blocked · action` reported as
> "waiting on agents", and others sat there with no instructions in the chat at all — the
> queue looked worked and the human had nothing to act on.

### 7. Closing report

> **Add to the report.** Two lines before the counts: **Path:** Fleet
> (the line the person was told in §0); and **Not done:** the steps that had no Fleet tool and were not
> swept, wired or written (a `Failed` reset not yet pressed), each named,
> never "none". Add **Used a tracker script for:** only if a gap step really ran. An item whose draft is
> still unconfirmed is **HANDED-OVER** and sits in the open-items block with its link and the one action.

**FINAL STEP — RE-READ `queue` (rule 1).** Call `queue` (`which: all`, follow `nextCursor`) once more and put the
**real decision and action counts** in the report's first line. **"0" or "done" is claimed only if that read
says 0.** Also re-read `Parked` and `Human WIP`: nothing this run moved there, and every item swept is accounted
for. **The "Open items needing you" block lists EVERY item that read returned.**

**Reconcile the ledger first — a hard gate.** Re-run §1's listing one last time; new
arrivals join the ledger and get worked, not footnoted. Then every row must hold exactly one
terminal disposition (§The queue ledger), `a + b + c + d` must equal `N`, every
WAITING-ON-AGENT row must read back **outside** both blocked queues, and every key still in
them must be a HANDED-OVER or open-ASKED row (the round gate). If a row does
not — an unanswered question, a release that did not read back — the run is **not done**:
work it, or open the report with `## NOT RECONCILED — <k> of <N> open` and list those rows
first, each with its question in askable form. Never report done over an open row.

End with exactly this, then stop:

```
## Queue after this run (re-read): <D> decisions, <A> actions — <N> handled this run: <a> auto-resolved, <b> handed over, <c> asked, <d> waiting on agents
**Asked:** <key — the answer — the row applied (released / parked / killed) — read back>
**Auto-resolved:** <key — why no human was needed — the evidence (a dead blocker edge: its key and position)>
**Handed over:** <key — what needs doing, in plain words — THEN THE ACTUAL COMMANDS,
in full, in a fenced block. Never a pointer to the issue, never a summary of a runbook
that lives somewhere else. If it does not fit in one line, it still goes here in full.>
**Waiting on agents:** <key — which agent / PR / issue owns it — what unblocks it — the
position it was MOVED to (implement / rework + blockedBy on a real open issue), read back>
**Parked / Human WIP sweep:** <key — released / closed on a live answer / wired / returned to the queue with the reason>
**Released:** <how many PRDs this run got moving>

**Open items needing you (<k>)**
<the pinned block, PRD-holding first — every item SELF-CONTAINED: its own numbered steps with
literal commands and real values, what success looks like, what to reply; reprinted in full,
never "as above" / "my earlier message" / "the N steps", never a bare decision name, never
"steps to come">
```

Before ending, **read the block back as a stranger would**: for each item, could the human act
on this one item with nothing else on screen? If not, fix it or dispatch an agent for the
missing steps — do not end the turn.

Omit any empty section. Nothing chatty after it.

---

## What makes a run a failure

- **Fleet path: a sub-agent was asked to decide, or wrote the answer back.** Only this session drafts.
- **Fleet path: a draft described as a release.** A draft (no `confirm`) releases nothing until the person
  presses Confirm and the read-back shows it. **And `confirm: true` on an answer the person did not just give
  live** (inferred, read from an issue, or passed from a headless run) is a forged decision.
- **Fleet path: a tracker key asked for.** The person was asked for a credential the Fleet path exists to
  make unnecessary, or the same answer was written through both paths.
- **Fleet path: a gap reported as clear.** "No stale blockers" when some blocked item's `blockers`
  were never read.
- **A `Failed` item put to the human undiagnosed** — a retry/re-scope/kill question when the
  cause was gone or transient, or a Reset handed over without the evidence — **or moved out of
  `Failed` with `move_issue`**, which strands it budget-spent.
- **A Reset handed over twice for the same cause** instead of asking (§2).
- **The action queue left for later** — decisions drained, My Action Queue short of zero.

- A question asked about a blocker that had already resolved (§2 skipped).
- A brief the user had to open the tracker to understand.
- A brief or option the user had to ask you to re-explain in simpler words — the
  jargon was never precision, it just moved the reading cost onto them (§3).
- An answer collected and never written into the description (§5a skipped) — the same
  deferral one step later.
- A relabel with no decision written, or a `labels` write that dropped `Type:*`.
- Four issues folded into one question round.
- A coordinator that read the issue bodies itself instead of dispatching sub-agents, or
  that dispatched them one at a time instead of in parallel.
- A queue printed instead of drained, with the user sitting right there.
- **An action handed over as a pointer** — "the runbook is on the issue", "see <KEY>",
  "I wrote the steps into the description". The user does not open tickets; that action
  is now stranded and you reported it as delivered.
- **A problem named with no next step.** Surfacing "X blocks Y" and stopping is a status
  update. Either ask, or say what to do about it.
- **An instruction only an insider could follow** — internal nouns with no plain-English
  gloss, a "deep link" that is a description of where to click, a command with a
  placeholder where a real value belongs.
- **A `## Decision` written into a customer report's check escalation** — the checker
  honours only the operator's Queue-page answer on an unvouched key, so the description
  write loops the issue straight back to `Blocked · decision` (ENG-14222). Hand over the
  Queue-page answer link instead.
- **An issue briefed once and absent from a later status message** — it dropped out of
  sight while it still needed the human (ENG-11963).
- **A PRD-holding item that is not at the top of the open-items block.**
- **A closing report whose counts do not reconcile with the re-derived queue.**
- **A blocked-queue item left after the round without instructions** — waiting on an agent
  but never moved out, or touched and not instructed (the round gate).
- **A §1 list that was capped, sampled, or never shown.**
- **A hand-over deferred past the turn its steps became known.**
- **An open item that is not self-contained** — a back-reference ("as above", "from my earlier
  message", "the 14 steps"), a bare decision name with no question and options, or "steps to
  come" / "later" with no steps in hand — or a self-contained item not repeated in full on a
  turn it was still open.

## Related

- [`interview-protocol.md`](../../process/interview.md) — the question shape and the write-back rule this command exists to execute.
- [`triage-partition.md`](../../registers/triage-partition.md) — the seven positions and the transition table every mutation here obeys.
- [`program:deliver`](program/deliver.md) — the *proactive* sibling: it discovers blockers while driving a program and interviews on the ones it hits. This command drains the queue those parks accumulate in, across every program.
- [`autonomous-drive.md`](../../process/autonomous-drive.md) — Rule G, the filing path that puts issues into this queue.

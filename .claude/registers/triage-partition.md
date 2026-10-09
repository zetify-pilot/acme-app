---
type: sop
slug: triage-partition
title: Keep every open issue in exactly one agent position
automated_by: `triage` (kind and position)
---

# Triage partition — the seven agent positions

**An issue's lifecycle POSITION is its workflow state.** One field, always present, exactly
one value. The fleet picks work up by state name, the seven positions filter on state name,
and every transition is a single `move_issue` call. The states and their transitions
ship with this register and are the same in every repository; **which tracker holds them,
what its saved views are called, and how it groups states** are `slot:tracker-identity`'s
answers, and this document names none of them.

**What this replaced, and why.** The position used to be *derived* from eleven flat routing
labels. A label can be **absent**, and absence is the failure that goes unseen: an issue with
no routing marker was invisible to the agent queue *and* to every human view, and the daemon's
`eligible()` gate rejected it by returning a bare `False` that logged nothing. A state cannot
be absent, and a *wrong* state puts the card in a column you can see where a dropped label
showed nothing at all. The eleven labels
(`agent-eligible`, `agent-running`, `to-be-checked`, `needs-decision`, `needs-action`,
`needs-human`, `awaiting-human-merge`, `verify-failed`, `awaiting-verification`,
`agent-failed`, `human-wip`) are **retired as routers**. They survive only on closed issues,
where they are historical data the cost layer still reads — never a live instruction.

> **Canonical vocabulary lives in code, not here.** Every state name, every surviving label
> string, and the classifier are defined **once** in
> `python3 knowledge/scripts/linear_labels.py`. This doc renders them for
> humans; the module is authoritative.
>
> ⚠️ **No byte-identity with the sibling `infra` repo is claimed any more.** This doc used to
> assert the names matched ``'s `Position` enum exactly; 
> retired that claim in `python3 knowledge/scripts/linear_labels.py` (nothing here could verify it, and the ` Queue`
> rename made it false in place while infra's frozen copy kept the old spelling). What holds
> instead is checked: a label ensure reconciles the declared
> states against the **live board**, both directions, and `STATE_ALIASES` accepts the
> historical spellings the sibling still writes.

## The invariant

> Every open issue is in **exactly one** workflow state, and every open state is claimed by
> **exactly one** view — except the `Type` axis, which is orthogonal and cuts across it.

At-most-one used to be a rule the guardrail enforced against dirty data. It is now **true by
construction**: the tracker gives an issue one state and only one. The old failure — two routing
markers coexisting, or zero — is unrepresentable.

⚠️ **Zero was the dangerous count, and it is the count that is now gone.** A work-kind issue
with no routing marker was *stranded*: two Urgent PRDs (, ) sat in `In Review`
carrying only `prd` — invisible to the fleet and to every human view — for ~9h. That class is
closed, not merely mitigated: there is no state that means "no position", and the guardrail
asserts that no open state is claimed by zero views. **Do not re-derive a position from
labels.** Reintroducing a label-keyed router reopens the absence case.

## ⚠️ Gate on the state NAME, never on the coarser grouping the tracker also exposes

This is the single most important rule in this document.

Every tracker groups its states into a few coarse buckets — unstarted, in progress, done, or
whatever it calls them — and `slot:tracker-identity` records which of our states
sit in which bucket here. `Parked` sits in the *backlog* bucket. A dispatch gate keyed on the
bucket therefore reads a deliberately-deferred issue as ordinary backlog and takes it — that is
, and it is the shape **every** bucket-based test produces. The bucket is coarser,
stable, and wrong.

The five parks (`Blocked · decision`, `Blocked · action`, `Failed`, `Awaiting merge`,
`Intake · decision`) and `Human WIP` sit in the *in-progress* bucket on purpose: blocked work is
stalled work *in flight*, not backlog. Bucketing them as backlog would hide them from WIP counts
and repeat the `Parked` mistake in a new field. A consequence worth stating plainly: **a park
does not release a blocker** (see the blocker table). `Needs answer` is in-progress for a
*different* reason — see below; the interview is live, even though no agent run is.

Read the bucket for board grouping and metrics. Never for a dispatch decision, a view
predicate, or a blocker check.

## The states

| State | Type | Means |
|---|---|---|
| `Needs Design` | `unstarted` | PRD frontmatter `prd-drafted` |
| `Needs Plan` | `unstarted` | PRD frontmatter `designed` |
| `Backlog` | `backlog` | filed, not yet routed — **stub PRDs live here; an idea born before  may still be resting here (`idea:create` now files into `Intake Queue` instead — nothing dispatches `Backlog`, so a legacy idea here waits on a human to move it); a gated kind (bug/task/cleanup) resting here is a guardrail violation (: `Backlog` dispatches nothing, so the check gate never ran on it)** |
| `Parked` | `backlog` | deliberate deferral |
| `Intake Queue` | `unstarted` | a person filed it and it is waiting for its **shaping interview** — dispatchable agent work, exactly like the queues below |
| `Triage Queue` | `unstarted` | filed, never checked — **the checker owns re-entry** |
| `Triaging` | `started` | claimed for the triage half |
| `Implement Queue` | `unstarted` | runnable, unclaimed — the fleet may take it |
| `Implementing` | `started` | claimed for the implement half |
| `Verify Queue` | `started` | green PR, verifier owed, unclaimed |
| `Verifying` | `started` | claimed for the verify half |
| `Rework Queue` | `started` | refuted by verification, back to the implementer |
| `Blocked · decision` | `started` | a human must **ANSWER** — gates the fleet, target zero |
| `Blocked · action` | `started` | a human must **DO** something no agent can |
| `Needs answer` | `started` | an agent asked **the person who filed the item** a question and is waiting on their reply — **not a park, and not `Blocked · decision`** |
| `Intake · decision` | `started` | a finished dossier (or proposal) awaits its verdict on the fleet's **idea page** — **not `Blocked · decision`**, the operator's terminal queue |
| `Failed` | `started` | gave up after `MAX_ATTEMPTS` — needs a human reset |
| `Awaiting merge` | `started` | green PR, the merge click is withheld |
| `Human WIP` | `started` | a person deliberately owns it — hands off |
| `Done` · `Canceled` · `Duplicate` | terminal | in **no** view |

`Needs Design` / `Needs Plan` are the **PRD pipeline**: projected from PRD frontmatter
by the `prd-projection` pass of the fleet's `corpus-sync` loop (`fleet-service`, on the
generation each tick stores) and PRD-only by invariant (a non-PRD holding one is a hard
violation). The pass writes only these
pre-execution states — it may never stomp an execution state, or it would rewind a live run
mid-verify.

**`planned` is the hand-off, and there is no third pipeline state.** A PRD whose frontmatter
reaches `planned` has nothing left to author, so the pass puts its issue straight into
`Implement Queue` — the runnable pool every kind rests in, which is why that state is *not* a
PRD-pipeline state and carries no PRD-only invariant. `Spec` was the state that used to hold it
and is gone: the pass may not write any execution state, no daemon dispatched on `Spec`, and the
label that once released a PRD from it (`agent-eligible`) is retired — so a planned PRD sat
there until a human moved it by hand, which is a dead end rather than a queue. The pool is
**written but not owned**: the pass may hand work to it and may never reach back in, or the next
tick would drag a PRD the fleet has already claimed out of `Implementing`.

### ⚠️ `Needs answer` is not `Blocked · decision`, and the difference is who is stuck

They read alike — *a person owes a reply* — and they route to the same view, so it is worth
saying exactly once what separates them. **The test is what is running behind the issue.**

`Blocked · decision` is a **stall**. The fleet was driving the issue, hit a fork it is not
entitled to settle, and stopped. Something *is* in flight behind it — a half-finished branch,
a dependent chain, an agent that cannot continue — so the queue **gates the fleet** and its
target is **zero**.

`Needs answer` is a **turn ending on purpose**. An agent asked the person who filed the item a
question and ended its turn so the answer can arrive whenever they get to it; the session is
resumed with the reply. **Nothing is running behind it and no agent is waiting**, so it blocks
no work at all — a `Needs answer` item sitting for a day costs nothing but that day.

It rides in **Needs My Decision** anyway, because the person who owes the answer is the person
who drains that view, and a question in a view nobody opens is a question nobody answers. That
is a routing decision, never an equivalence: in code the two are separate sets
(`DECISION_STATES` and `ANSWER_STATES`, unioned once as `NEEDS_MY_DECISION_STATES`), so
"gates the fleet, target zero" keeps meaning what it has always meant. **Never** write
`Needs answer` for a stall, or `Blocked · decision` for a question the fleet is not waiting on.

### ⚠️ `Intake · decision` is not `Blocked · decision`, and the difference is where the verdict is given

A finished idea dossier (*route it* / *withdraw it*) or a routed idea's proposal (*create it* /
send it back) also reads like *a person owes a decision*, but it is **not** the operator's queue.
The fleet finished its half and stopped; **nothing is in flight behind it and no box is waiting**,
so it does not gate anything. The verdict is given on the fleet's **idea page** — `Type:idea`
items are inventoried in the `Ideas` view — and a bare Linear transition would be re-parked by the
dispatcher because `fleet_intake.decision` stays empty. Writing it into `Blocked · decision` both
inflated the fleet-blocked number (whose target is zero) and produced the wrong ritual: an
`` session interviewing the operator in a terminal, and on a *yes* moving an intake
item to `Triage Queue`, where intake never reads. So it is its own `started` position, refused by
the dispatch gate **by name** (the  shape), and it rides in `Ideas` rather than
`Needs My Decision` (). It is **un-routed by intent** (`UNROUTED_STATES`), not an
`Ideas` seed: `Ideas` is the `Type:idea` override on top of the position axis, so an idea in this
park shows there, and a non-idea dragged here by hand — a misfiling, since `/fleet:intake` is
idea-only by a hard gate — shows in `Assign to Agents` **and reds the partition guardrail**, the
`Needs Design`-without-`Type:prd` rule on the kind axis ().

Only seven states are **agent-writable** (`AGENT_WRITABLE_STATES`): `Triage Queue`, `Implement Queue`,
`Verify Queue`, `Rework Queue`, `Blocked · decision`, `Blocked · action`, `Awaiting merge`. The claim
states (`Triaging`, `Implementing`, `Verifying`), the terminal states, and `Human WIP` are written
by the daemon or by a human, never by a session. **A person on the fleet Queue page is a human
here** (): *Park* and *Take it by hand* there queue the move through the fleet's outbox
on that person's behalf, recorded with who asked — the fleet writes it for them and never on its
own initiative. **And so are the everyday edits** (, ): re-ranking an issue the
check already graded, changing its `Type` / `Component` / `repo:` label from the labels that
already exist, or posting a comment as the Fleet account on the person's behalf, each one outbox
write and one decision row naming who asked.

## The seven positions (precedence order — higher wins)

Each position is a **positive state predicate with no lifecycle exclusion list** — the states
are disjoint, so there is nothing left to exclude. The position ids below are the fleet's;
**the display name each carries in the tracker, and whether it is materialized as a saved
view at all, is `slot:tracker-identity`' answer** — `queue which: all` lists the human-input queues, and the tracker's views stay aligned to this table.

| # | Position | Status filter (state names) | Label includes | Label excludes |
|---|---|---|---|---|
| 1 | `needs-decision` | `Blocked · decision`, `Failed`, `Needs answer` | — | — |
| 2 | `action-queue` | `Blocked · action`, `Awaiting merge` | — | — |
| 3 | `parked` | `Parked` | — | — |
| 4 | `ideas` | `Backlog`, `Needs Design`, `Needs Plan`, `Intake Queue`, `Triage Queue`, `Triaging`, `Implement Queue`, `Implementing`, `Verify Queue`, `Verifying`, `Rework Queue`, `Human WIP`, `Intake · decision` | `idea` | — |
| 5 | `agent-backlog` | `Intake Queue`, `Triage Queue`, `Triaging`, `Implement Queue`, `Implementing`, `Verify Queue`, `Verifying`, `Rework Queue` | — | `idea` |
| 6 | `assign` | `Backlog`, `Needs Design`, `Needs Plan`, `Intake · decision` | — | `idea`, `customer-bug` |
| 7 | `human-wip` | `Human WIP` | — | `idea`, `customer-bug` |

**The only surviving exclusions are `Type` kinds**, because `Type` is an orthogonal axis — a
*kind*, not a position (see [What stays outside the state](#what-stays-outside-the-state)).
Precedence now resolves exactly one thing: the overlap the `Type` axis creates between **Ideas**
and views 5–7. Every other pair is disjoint on states alone.

⚠️ **Do not re-add a lifecycle exclusion list.** The hand-maintained `-needs-decision
-human-wip …` lists are not merely redundant now, they are **wrong**: they encoded a
coexistence that can no longer happen, so a label later re-added as a *diagnostic* (a refuted
issue keeping `verify-failed` for visibility is the live candidate) would silently empty the
queue that still excluded it.

**Only view 1 has a zero target — and that target is about its `DECISION_STATES` half.** It
gates the fleet, and  drains it
every cycle. `Needs answer` rides in the same view because the same person owes the reply, but
it blocks nothing (see [the distinction above](#️-needs-answer-is-not-blocked--decision-and-the-difference-is-who-is-stuck)) —
so an unanswered question is a *slow* item, never a stalled fleet. View 2 needs a human's hands
but blocks no agent — drain it when convenient.

> **`Triage Queue` and `Intake Queue` sit in the fleet-owned pool (view 5), not the human
> catch-all.** The daemon dispatches [`/fleet:check`](#)
> on a `Triage Queue` issue itself, and the shaping interview on an `Intake Queue` one, so both
> are agent work. The label world could not say that: a `to-be-checked` issue carried no
> `agent-eligible`, so it could only fall through to **Assign to Agents**.
>
> ⚠️ **A `Type:idea` item in `Intake Queue` shows in `Ideas` (view 4), not `Agent Backlog`** —
> the `Type` axis overrides wherever the idea inventory claims the state, and it claims every
> agent-pool state. That is deliberate and pre-existing (it is already true of `Triage Queue`),
> and since intake exists to shape *ideas* it is the common case. `VIEW_BY_STATE` still maps
> `Intake Queue → Agent Backlog`; the override is the orthogonal `Type` axis, not a second
> position.

> **View 7 (`My WIP`) is the deliberate-hold INVENTORY, not a routing queue.** A hold with no
> timer is an abandonment in disguise, so `--list "My WIP"` renders each hold's age and flags
> one past `HUMAN_WIP_STALE_DAYS` as `STALE`. It routes nothing: the daemon's hard veto on
> `Human WIP` stands.

> **Position 2 has a filter a saved view cannot express: it hides anything with an unmet `blockedBy`
> edge**, so it only ever shows what is runnable *right now*. Saved views have no
> "blocked by an open issue" predicate, so **the saved view over-reports**; `classify()` — and
> therefore `queue which: all` — is the accurate one.
> Deliberate asymmetry: view 1 does **not** hide blocked items, because a decision is cheap,
> forward-looking, and usually what unblocks the chain.

### Stranding is unrepresentable —  /  closed

The old partition needed two hand-written rules for the zero-marker case: a stranded `Type:prd`
fell to **Needs My Decision** (always a defect), any other stranded work kind to **Assign to
Agents** (undecided, not broken). Both are gone, and **view 6 no longer carries the started
states**, which is  being *closed* rather than forgotten.

Stranding was "a started issue carrying no routing marker". Once every issue has exactly one
state and every started state is claimed by exactly one view above, that shape has nowhere to
exist — view 6's old started-state enumeration was a *repair* for a hole that no longer has a
floor to fall through.

⚠️ **The lesson that outlives the rules: every carve-out must key on something PRESENT.** The
retired rule "started and not `agent-eligible` ⇒ human-owned WIP" inferred ownership from a
*missing* label, and a missing label is also the signature of dropped work — so it hid the
second while claiming to describe the first. **The assignee is not a usable substitute**:
 carried an assignee continuously, while the fleet drove it *and* through all 9h it was
stranded, so an assignee-based rule would have stayed silent on the incident that motivated it.
If a new carve-out is tempting to write as "does *not* have X", that is the bug, not the
shortcut.

**Carve-outs — in NO view, by design** (tracked elsewhere, not lost): `Type:customer-bug`
(separate Customer Bugs track), and a **blocked action** (`Blocked · action` with an unmet
blocker — it surfaces in view 2 the moment its blocker closes).

## Three blockers, not one

`needs-human` once meant three unrelated things at once — *decide this*, *do this*, *wait for
this* — so one queue mixed work that gates the entire fleet with work that gates nothing, at
identical apparent urgency. On the drain that measured it, only 4 of 8 parked issues were
fleet-blocking; the queue never reached zero and stopped being a signal. The split is by
**what clears the blocker**:

| Blocker | Position | Cleared by | Gates the fleet? |
|---|---|---|---|
| a human **answers a question the fleet stopped on** | `Blocked · decision` | the answer | **yes — target is zero** |
| **the filer answers an interview question** (nothing is running behind it) | `Needs answer` | their reply, which resumes the asking session | no — it delays only itself |
| a human **does something no agent can** (mint a credential, click a console, SSH, merge a guarded PR) | `Blocked · action` / `Awaiting merge` | them doing it | usually no — schedule it |
| **other work must land first** | **no park** — stay `Implement Queue`, add a `blockedBy` relation | the blocker closing | no — self-serializes |

⚠️ **"Wait for this" is never a park.** The scheduler already skips any issue with unmet
`blockedBy` edges, so a chain of `Implement Queue` issues executes in dependency order unsupervised —
parking instead hides runnable work behind a human who has nothing to do. `Type:prd` is no
exception: `compute_plan` evaluates the frontmatter `depends_on:` graph first, then ANDs the
same tracker `blockedBy` gate every other kind gets. PRD→PRD sequencing still lives in
frontmatter; the tracker gate is an *additional* check for edges frontmatter cannot express (see
[`issue-tracking.md`](../process/issue-shape.md)).

### Which blocker states actually release

A `blockedBy` edge is released by the blocker reaching a **closed state type**, and held by
everything else. Reading this off the state *name* is the trap — read the type, then check the
name against this table:

| Blocker's state | Type | Effect on its dependents |
|---|---|---|
| `Done` | `completed` | **releases** |
| `Canceled` | `canceled` | **releases** |
| `Duplicate` | `duplicate` | **releases** — ⚠️ a distinct type, not a flavour of `canceled`; a duplicate blocker is unresolvable by definition, so this is the only sane reading |
| `Backlog`, `Parked` | `backlog` | holds |
| `Needs Design`, `Needs Plan`, `Intake Queue`, `Triage Queue`, `Implement Queue` | `unstarted` | holds |
| `Triaging`, `Implementing`, `Verify Queue`, `Verifying`, `Rework Queue` | `started` | holds |
| `Blocked · decision`, `Blocked · action`, `Failed`, `Awaiting merge`, `Human WIP`, `Intake · decision` | `started` | holds — ⚠️ **a park does not release** |
| `Needs answer` | `started` | holds — the item is unshaped until the reply lands, whatever it is not blocking |

### Re-point a blocker's dependents BEFORE you close it

`blockedBy` is cleared by **the blocker closing** — that is the whole mechanism, and it is why a
blocker that is really a *placeholder* is dangerous. When A blocks B and A's work is carried
forward by a successor C, closing A releases B **immediately**, even though nothing B needs has
shipped. The gate stood for *the fix landing*; closing A downgrades it to *the plan being
written*.

**So: wire `blockedBy` → C on every dependent, and only then close A.** Never the other order,
and never "close now, re-point in a minute" — the scheduler polls continuously and will dispatch
inside that gap.

>  (a decision ticket) blocked . Its decision was taken and PRD 0413 authored;
> the authoring PR's merge closed  automatically, the gate cleared, and the fleet
> dispatched  **17 minutes later** — against a `main` where every wall 
> documented was untouched, because 0413 was `Needs Design`, not shipped. The successor issue
> existed only *after* the merge that did the closing. **If a successor will not exist until the
> closing event itself, keep the original open until it does** — an issue costs nothing; a bad
> dispatch costs a full agent run and lands a half-finished branch.

| The blocker is… | Closing it means | Do |
|---|---|---|
| the **work itself** (a bug, a task, a PRD that ships the fix) | the fix landed — dependents are genuinely free | close normally |
| a **placeholder** (a decision ticket, a triage stub, "figure out X") | only that the *decision* is made — the fix has not landed | re-point dependents to the successor first, **then** close |

### Closing an issue does not answer its question

A terminal state means **nothing further is owed**, so closing an issue while a human question
still stands silently discharges a debt nobody paid. A `Done` + `needs-action` blocker once
cleared five dependents against a release that did not exist.

⚠️ **The label half of this rule is retired, and the shape it caught is now unrepresentable.**
`Done` and `Blocked · decision` are two values of ONE field, so a closed issue cannot also be
parked: closing it *overwrites* the question rather than hiding it behind a marker the queues
still read. The routing labels left on the ~4,000-issue closed tail are **inert history, kept
deliberately** — the fleet's cost accounting reaches recorded spend through `agent-eligible` on
finished issues — so the guardrail no longer fails on them, and you must **not** bulk-strip
them.

**The detector is comment-derived instead**, and it is strictly better: `unanswered_closed_parks()`
reads the newest comment, never depended on a label, and now covers the whole class rather than
the marker-less residual it was once carved down to. A closed issue whose newest comment is an
unanswered park is reported (informationally) on every full run.

**When draining one:** re-point open dependents first; then, per issue and never in bulk, either
**close cleanly** — supersede the park with a non-park comment, or a `## Resolved` description
section, saying why the question is moot — or **reopen**, when the question was real and never
answered (most likely on `Canceled`). What must never happen is closing an issue *because* its
park is inconvenient.

## Transition table

Every mutation an agent or a human makes is a row here. Never invent one.

| Trigger | Who | State → |
|---|---|---|
| **Create — any agent work** (bug/task, incl. audit findings) | create-cmd | **`Triage Queue`** — no priority, no project, no placement; the filer is the wrong party to decide any of them. **Never `Backlog`** — for a gated kind that is now a guardrail violation, not a parking choice () |
| Create — idea | `idea:create` | **`Intake Queue`** + `Type:idea` — **never `Backlog`**: nothing dispatches `Backlog`, so an idea filed there sits untouched (54 of 84 measured that way); `Intake Queue` is what the fleet's front door sweeps into the shaping interview, then `/fleet:route` () |
| **Intake interview concludes** (dossier, or a routed proposal) | daemon | **`Intake · decision`** — the verdict is given on the fleet's idea page, **never** the terminal `Blocked · decision` queue |
| **Check → release** | `/fleet:check` | **`Implement Queue`** + priority, `Component`, Project, `blockedBy` |
| **Check → escalate** (new customer-facing functionality, or a standing refusal/deferral a human must overturn) | `/fleet:check` | **`Blocked · decision`** |
| **Check → action** (work no agent can perform — mint a credential, click a console, SSH, roll production by hand, merge a guarded PR) | `/fleet:check` | **`Blocked · action`** + priority (; : never without priority) |
| **Check → close** (duplicate / already fixed / not real) | `/fleet:check` | `Duplicate` / `Canceled` |
| **Answer a check escalation** | you / `` | **`Triage Queue`** — back to the checker, **never** straight to `Implement Queue`. **On a customer report the checker honours only the operator's stamped Queue-page answer** (`POST /api/decision-clears`), so there `` writes no Decision and moves nothing — it hands over the Queue-page answer link () |
| **Answer an interview question** (`Needs answer` — the filer's reply) | the filer, from the fleet inbox / `` | **back to the loop that asked** — **`Intake Queue`** for an item the intake interview parked (an idea above all), where the interview resumes with the answer; a question a work run asked goes back to the work queue it asked from. **Never `Implement Queue` for an idea**: every implement command refuses an idea by kind and it strands there (). `move_issue` refuses that move |
| **Answer — PRD-sized** (the answer changes what the product promises: a new slice, a new PRD, a register reversal) | you / `` | **the unblock run authorizes it in the same run, while you are attached** — dispatch `/fleet:slice:create`, then `/fleet:prd:create`; hand **the new PRD** to `Implement Queue`, and close the task when that PRD exists and is linked. **Never `Implement Queue` on the task** — an execute run may not mint the PRD that warrants its own work (Rule J), so the only correct result of that release is the `Blocked · decision` park it came from (, run `42917f92`) |
| **Answer — hand back to the fleet** | you / `` | `Implement Queue` |
| **Answer — a human owns the work** | you / `` | `Blocked · action` |
| **Answer — other work must land first** | you / `` | `Implement Queue` **+ `blockedBy` edge** |
| **Approve** in triage | you | `Backlog` → `Implement Queue` |
| **Park** ("not now") | you / `move_issue` | `Parked` |
| **Take it yourself** ("I'm driving this") | you | **`Human WIP`** |
| **Park — from the fleet Queue page** ("not now") | a person, from the fleet Queue page (`POST /api/parks`; recorded with who asked) | any open position **no machine is running** → `Parked`. Refused for `Triaging` / `Implementing` / `Verifying`, for an issue a live claim holds whatever its state, for a closed issue, and for `Human WIP` (the veto below) |
| **Take it by hand — from the fleet Queue page** ("I'm driving this") | a person, from the fleet Queue page (`POST /api/human-takes`; recorded with who took it) | any open position **no machine is running** → **`Human WIP`** — the same refusals. The state is the hold: no `human-wip` label is written |
| **Cancel — from the fleet Queue page** ("this work is over") | a person, from the fleet Queue page (`POST /api/cancels`; the required reason is recorded on the `decision` row and posted to the issue) | any open position **no machine is running** → `Canceled`. The same running / live-claim / closed refusals as Park. **On `Blocked · decision` and `Blocked · action` the close IS the person's answer to the park** (the owner's call, ): the reason is recorded on the `decision` row and posted to the issue, so nothing is discharged unseen. **Still refused on `Needs answer` and `Intake · decision`**, whose answer somebody other than the operator owes (the filer's reply, the idea page's verdict). On `Human WIP` only the **recorded taker** may close (the hand-back's rule). **Canceled releases dependents** (the blocker table): every open issue with a `blockedBy` edge to this one is released, so re-point them to a successor first if the work carries forward |
| **Re-rank — from the fleet Queue page** | a person, from the fleet Queue page (`POST /api/issue-priorities`; recorded with who asked) | *(no move)* — the issue's priority changes within `1`–`4`. Offered only where `/fleet:check` already graded it: a hand-set priority on an unchecked issue would make the dispatch gate pass for a fact nobody graded, so it is refused. Refused on a closed issue |
| **Relabel — from the fleet Queue page** | a person, from the fleet Queue page (`POST /api/issue-labels`; recorded with who asked) | *(no move)* — the issue's `Type`, `Component` or `repo:` label changes, each picked from the labels that already exist (never free text: a typo'd label is a real label that mis-routes the issue, and this service never creates one). Changing the `Type` or the `repo:` label of an issue a machine is running is refused |
| **Comment — from the fleet Queue page** | a person, from the fleet Queue page (`POST /api/issue-comments`; recorded with who asked) | *(no move)* — a comment is posted as the Fleet account, opening with an *on behalf of `<person>`* line. It is written by the fleet's own credential, never the person's key () |
| **Mark duplicate — from the fleet Queue page** | a person, from the fleet Queue page (`POST /api/duplicates`; recorded with who decided) | any open position **no machine is running** and not closed — the two operator parks included, where the close is the person's answer, and `Human WIP` for its recorded taker only; refused on `Needs answer` and `Intake · decision` → **`Duplicate`** + a **`duplicate` relation to the named original** + a comment naming the original and who decided. One `decision` row `duplicated-by-hand`. The original's key is required and validated (it must exist and cannot be the issue itself). ⚠️ **A duplicate RELEASES its dependents** — `duplicate` is a terminal type — so the confirmation names the issues this click frees. The relation write diffs the issue's whole relation set around the mutation and fails rather than report a wrong write |
| **Add / remove a blocker — issue detail** | a person, from the issue detail (`POST /api/blockers`; recorded with who changed the edge) | one `blockedBy` edge **added or removed** on an open position no machine is running; the issue **stays where it sits**. Adding means the named issue BLOCKS this one, which is the edge the dispatch gate reads. One `set-relation` write and one `decision` row (`blocked-by-hand-added` / `blocked-by-hand-removed`). The write diffs the relation set and fails rather than report a wrong write |
| **Hand it back — from the fleet Queue page** | a person, from the fleet Queue page (`POST /api/hand-backs`) | `Human WIP` → **`Implement Queue`** \| **`Backlog`** \| **`Verify Queue`**, each named in the request. **Only the recorded taker may**: the newest `taken-by-hand` `decision` row names them, and a hold entered in Linear has no page taker, so it is refused there and released where it was taken. **`Verify Queue` REQUIRES a priority in the same request** and the priority is written before the state (: a priority-less arrival is refused by the gate *where it sits*, and the remedy is to arrive with one — never a move back to `Triage Queue`, which re-enters the implement half against a fix that already exists). One `set-state` (plus the priority where owed) and one `decision` row `handed-back-by-hand` |
| **Approve — from the fleet Queue page** | a person, from the fleet Queue page (`POST /api/approvals`) | `Backlog` → **`Implement Queue`** when the issue already carries a priority (its `/fleet:check` grading), else **`Triage Queue`** so an ungraded issue re-enters the check gate rather than skipping it — `` names *"hand-moved past it"* as a strand cause. One `set-state` and one `decision` row `approved-by-hand`. Offered only on an open `Backlog` issue no machine is running |
| **Un-park — from the fleet Queue page** | a person, from the fleet Queue page (`POST /api/un-parks`) | `Parked` → **the queue it was parked FROM**, read off the move that parked it, else `Triage Queue` (a park taken off a park, a hold or an intake loop names no fleet queue) — **an idea goes back to `Intake Queue` instead**, because the check gate refuses it by kind (). **It posts the fleet's reset marker in the same act** — one `run_reset` row — so the attempt and rework budgets a bare state move leaves spent read as fresh; this is the one un-park that is NOT a hand move (see *NEVER un-park by hand* below). One `run_reset`, one `set-state` holding `Parked`, one `decision` row `unparked-by-hand`. Offered only on an open `Parked` issue no machine is running |
| **Reopen — from the fleet Queue page** | a person, from the fleet Queue page (`POST /api/reopens`; the required reason is recorded on the `decision` row and posted to the issue) | `Done` \| `Canceled` \| `Duplicate` → **`Triage Queue`** so the check gate re-grades scope and priority rather than the fleet picking up un-triaged work. A reason is required, and the comment is posted before the state. One comment, one `set-state` and one `decision` row `reopened-by-hand` |
| **Hand it back** | you | `Implement Queue` \| `Backlog` |
| **Hand it back — to a verifier** (you drove the fix yourself and its PR is green: `Human WIP` → `Verify Queue`) | you | **`Verify Queue`** + **priority** — ⚠️ **the priority rides with the move.** A priority-less arrival here is refused by the dispatch gate *where it sits*, and the remedy at this position is to set the priority **in place** — never a move back to `Triage Queue`, which re-enters the implement half against a fix that already exists |
| Claim — triage | daemon | `Triage Queue` → `Triaging` |
| Claim — implement | daemon | `Implement Queue` \| `Rework Queue` → `Implementing` |
| Implement handoff (green PR opened) | daemon | `Implementing` → **`Verify Queue`** |
| Claim — verify | daemon | `Verify Queue` → `Verifying` |
| Verify passes, ledger all-closed | daemon | `Verifying` → `Done` |
| Verify refutes | daemon | `Verifying` → **`Rework Queue`** |
| Graceful stop / stale-heartbeat reclaim | daemon | `Triaging` → `Triage Queue`; `Implementing` → `Implement Queue`; `Verifying` → `Verify Queue` |
| **Self-park — needs an ANSWER** | daemon/agent | `Blocked · decision` |
| **Self-park — needs a human to DO something** | daemon/agent | `Blocked · action` |
| **Self-park — waiting on other work** | daemon/agent | *(no move)* + `blockedBy` edge |
| Agent-done, a human must merge | daemon | `Awaiting merge` |
| Fail ×`MAX_ATTEMPTS` | daemon | `Failed` |
| PR carries `do-not-merge`, or a human drafted it | daemon | *hold, no move* |
| **Reset** → back to agents | you, through the fleet's reset (`POST /api/resets` on the control plane, or its Queue-page button) | the queue it failed from — `Implement Queue` \| `Rework Queue` \| `Verify Queue` \| `Triage Queue`; `Triage Queue` when no failing run names one (); **an idea goes back to `Intake Queue`**, never a work queue () |
| **Detect a hand edit** (a state change by a non-Fleet actor that no fleet `decision` row accounts for) | the projection tick (`issuejob`), comparing consecutive snapshots and reconciling them against the `decision` log | **no move** — recorded in `linear_hand_edit` and surfaced on the System page as **hand edits in Linear**, each with the lever that was correct. **Report and repair only — never auto-revert** () |
| **Repair an un-park by hand** | you, through the fleet's reset (`POST /api/resets`) | the queue it failed from; the reset is the only writer of the marker that bounds the spent budget |
| **Repair a skipped check** | you, through the check gate (`/fleet:check`) | `Triage Queue` — the checker owns re-entry |
| **Repair a priority-less `Verify Queue`** | you | set the priority **in place** on `Verify Queue` — never a move back to `Triage Queue`, which re-enters the implement half against a fix that already exists |

### ⚠️ A PRD-sized answer is authorized in the unblock run, never dispatched to the fleet

Every other answer row ends in a position someone can act on: the checker re-enters, the
fleet executes, a human does the thing, or a `blockedBy` edge serializes the work. **The
PRD-sized shape releases to nothing on its own**, because every execute command is barred
from authoring or amending the artifacts that warrant its own work. A new slice, a new PRD,
a reversed requirement-register row: the answer names an authorization the receiving run is
forbidden to mint ([Rule J](../process/autonomous-drive.md) — Never mint your own
authorization). Releasing the task to `Implement Queue` therefore hands the fleet an
instruction whose only correct outcome is the park it came from.

**Measured ().** A `Type:task` decision whose answer reversed an adopted
requirement row and a shipped PRD criterion was released to `Implement Queue`. The dispatch
(run `42917f92`) stopped under Rule J within minutes and parked the issue straight back in
`Blocked · decision` — one dispatch spent, and the human's answer round-tripped to the same
queue it left. The gap was structural: no row described the shape, so the closest-looking
row was applied.

**The unblock run is the one party that can authorize it, because the human is attached to
it.** So the row has the unblock run dispatch
[`/fleet:slice:create`](#) and then
[`/fleet:prd:create`](#) itself, in the same run,
and hand the **PRD** — never the task — to the fleet. The task's own completion condition
becomes *that PRD exists and is linked*, and it closes when that is true. Rule J forbids an
**execute** run from minting the warrant for its own work; it does not touch the unblock run,
whose whole product is a durable authorization a human just gave.

**If the human leaves before the artifacts exist** — or declines to author the warrant — the
row falls back to **`Blocked · action` naming the artifacts owed** (the slice to cut, the
PRD to author), never `Implement Queue`. That fallback is worse — it parks a human on work
the unblock run could have done with them present — but it is never wrong, and it is the
honest state when nobody is left to authorize the answer.

### The "one atomic swap" rule is moot — and must not come back

A transition used to be `-oldlabel +newlabel` inside **one** label write carrying the full
desired label array. That was not style: a tracker's label write **replaces the whole set**, so
two separate calls — or a computed array that forgot to drop one — left an issue carrying both.
A release that kept `to-be-checked` alongside `agent-eligible` sent the issue back to the
checker forever while the board claimed it was fleet work.

**A transition is now a single field write.** `move_issue` sets exactly one value and
cannot be half-done; there is no partial state and no swap to get wrong. ⚠️ **Do not
reintroduce a label array in a verdict write.** If a command passes `labels` at all it must be
the full intended set including `Type` / `Component` / `repo:*` — a partial array strips them
and strands the issue as effectively as a missing state ever did.

### `Triage Queue` is re-entrant, and that is load-bearing

A checker escalation goes `Triage Queue → Blocked · decision`, and the answer returns it to
**`Triage Queue`** — *not* to `Implement Queue`. The checker still owes the triage it started: the priority,
project, component and blockers are all still unset. A checker **action** park goes
`Triage Queue → Blocked · action` with priority already set () — no re-entry; the
human does the named work.

This replaces the deliberate `to-be-checked` + `needs-decision` coexistence, which was correct
and must not be lost. The label world needed two labels riding together because a park had to
strip the routing marker, and then nothing on the issue remembered that the *checker* — not the
fleet — owned re-entry. One re-entrant state says it in one field. Moving an answered escalation
straight to `Implement Queue` hands the fleet an un-triaged issue and permanently skips the gate.

### ⚠️ NEVER un-park by hand — use the fleet's reset

**This matters more now, not less.** Dragging a card to a new column in the tracker's UI is
*easier* than removing a label was, and it is just as wrong — because the state is not the only
thing a park spent.

Both budgets that park an issue are **derived from immutable comment markers**: the attempt
count from failed cost markers, and the rework-return count from `verify-failed` /
`noop-handoff` markers. Comment history cannot be rewritten. Only the fleet's reset (`POST /api/resets`,
or the board's reset button — never a hand move) posts the
reset marker that bounds either count.

So a hand-moved card is released with its budget **still spent**: it burns one more
implement→verify cycle and re-parks at the same number, forever.  / PRD 0556 went round
that loop twice in one evening. On the attempt budget the failure is nastier still — the issue
reads as a first try, gets exactly one run stamped `attempt=1`, fails, and is then counted
against *every* historical marker, so every box returns PARKED. It then sits eligible,
unblocked, unparked, and silently undispatchable. `reset` is also the only way a charge left
behind by a since-fixed counting bug is ever retired.

**One exception, because the move can mean nothing else: a release out of `Failed`.** `Failed`
is the park whose whole meaning is *the attempt budget is spent*, so dragging a card out of it
into a live queue is the decision to try again. The fleet therefore records that move as
the person's reset — the projection draws the same `run_reset` line `POST /api/resets` would, in
the same transaction, naming the actor the tracker reports. Every other hold still needs the
reset below when its budget is spent.

**The fleet Queue page's Un-park is therefore not a hand move**: it posts the same reset marker
in the same act (`POST /api/un-parks`, ), so the person gets the lever without the
budget hole the register forbids. A move made by dragging the card in Linear is still a hand
move and still wrong.

### Hand edits are DETECTED and REPORTED, never reverted ()

The rule above is a convention Linear cannot enforce: it has no way to make a state change
read-only for everyone but the Fleet account. So the fleet watches for the move instead. The
projection already diffs consecutive snapshots (`dispatch.transitions`), and every move the fleet
makes — by a machine or by a lever on the Queue page — has a `decision` row committed with its
tracker write. **A move with no matching decision row was therefore made by somebody else, whoever
Linear names as the actor**; the accounting is the evidence, and a `FLEET_LINEAR_ACTORS` roster
turns the history's actor into a name where it can.

* **Reported, on the System page**, as *hand edits in Linear*: actor, from, to, when, and the
  lever that would have been the correct move.
* **Forbidden shapes carry their repair lever** — an un-park wants the reset, a skipped check
  wants the check gate, a priority-less `Verify Queue` wants the priority set in place. A repair
  whose route is not deployed yet is named rather than offered as a button that would 404.
* **Never auto-revert.** Reverting a person's move is a second writer fighting the first, and a
  released park is not re-parked on a stale read (see above). The row stays after it is repaired:
  it is the evidence the move happened.
* **Intake is not a hand edit.** A new issue filed in Linear lands in `Triage Queue` as a FIRST
  SIGHTING — it transitioned from nowhere anybody saw — so the allowed path is never flagged.

### The self-park default is `Blocked · decision`

An agent that self-parks knows *why* it stopped — it writes the 🙋 INPUT REQUIRED comment
naming the blocker — so it must emit one of the three self-park rows. Anything ambiguous or
missing falls back to `Blocked · decision`: a misclassified action costs one glance, a
misclassified decision would sit unseen in a queue checked weekly. **Never self-park for a
dependency** — wire `blockedBy` and stay `Implement Queue`.

**The self-park writes the 🙋 park comment, and — if a description section is wanted — a
`## Open questions (<date>)` section. Never `## Decision (<date>)`**, which is reserved for
a human's answer to a question the fleet stopped on; an agent's own record goes under
`## Implementation notes (<date>)`
([`decision-write-back.md`](../process/decision-write-back.md), ).

### Fact-check the park reason before you write it

A park reason is model-generated prose about state the writing session did not directly
observe — another session's progress, a PRD decision's disposition — and a park written on
an unverified claim occupies the human queue that gates the fleet on something that is not
actually blocking. Measured (): one stall sweep wrote two parks, both false or
incomplete on inspection, one still live — parked on a D-number that had closed two days
earlier while the "dead" session's heartbeat was under 2h old. So before the state move and
its INPUT REQUIRED comment are written, **every factual claim the reason makes about
cross-session state is re-verified from its live source** — never from memory, never from an
older comment on the issue, never from a derived view:

- **A cited decision** ("PRD `<n>` open decision `Dn`") — re-read that D-number's *current*
  disposition from the PRD's own `design.md` / `prd.md` (grep its Decision ledger, and
  `ux-design.md` when the approval lives there) before citing it as open. Decisions close
  out-of-band; the last thing a session remembered about one is not its state.
- **A liveness claim** ("no heartbeat since `<date>`", "dead in `Implementing`") — compute it
  the way the daemon's own liveness function does: find the freshest
  `<!-- linear-agent:heartbeat ... -->` comment and take its **`updatedAt`** — the comment is
  created at claim and edited in place on every beat, so `now − updatedAt` is the heartbeat
  age and `now − createdAt` only ever tells you elapsed runtime. **Never infer "dead" from
  raw state-history volume or gaps** — rapid `Implement Queue ↔ Implementing` flips are a known
  lost-claim-race artifact, not a dead session.

A claim that cannot be confirmed from its live source is not written into the reason as
fact: the park waits for the re-read, or the claim is dropped from the reason.

### A released park is not re-parked on a stale read

When a park you wrote — usually a `Blocked · decision` escalation — now sits in a
non-park state (`Implement Queue` above all), that is presumptively a **release** by another
session executing the answer protocol: the answer went into the issue **description**
as a `## Decision (<date>)` section ([`decision-write-back.md`](../process/decision-write-back.md))
and the state moved with it, in the same write. It is not drift to undo. Before
you consider moving it back:

1. **Re-fetch the full description fresh** (`get_issue`) and judge the answer channel
   only from that read — **never from the copy still in your context**. You may be the
   filing session, still holding the body you authored when you escalated; the answer
   lands *after* that copy was made, so a stale read reports "the description is
   unchanged" about a description that changed. List responses truncate descriptions;
   fetch the full body.
2. **Apply the daemon's citable-answer check** (). The release **stands** when either
   citable form is present:
   - a `## Decision (<date>)` section in the description dated on/after the day of the
     escalation (the `_DECISION_SECTION_RE` form), or
   - a comment dated after the escalation that the fleet did not write — neither a
     `linear-agent` marker nor a `/:` verdict comment.
   With either present, do nothing: the park was released legitimately.
3. **Actor attribution is never grounds.** Every fleet session writes under one API
   key, so "the actor is not provably human" is invariant to anything the releaser
   writes — no release can ever satisfy it, and it condemns your own writes equally.
   It is not evidence of anything. The citable forms in (2) are the **only** test.
   Absent both on a fresh read, the original park reason stands and re-parking is
   legitimate — and "no answer was written" is then a claim the fresh read supports,
   never one asserted from memory (the fact-check rule above binds it the same way).

Measured (): a filing session re-parked a released escalation for 63 minutes
on exactly these two grounds — "no answer was written" against its own stale copy (the
answer had landed 42 minutes earlier; the tracker's own history carried
`updatedDescription: true`) plus unattributability — holding the v0.1.6 cut the park
existed to enable and forcing a full re-verification cycle.

### ⚠️ `Human WIP` is a hard veto

`Human WIP` means "I am driving this, hands off". It is checked **ahead of everything else**:
no reconciler may route an issue out of it, and the dispatch gate refuses it outright. **Only
the human's own hand-back reverses it** — the daemon never clears it. A person may *enter* it from
the fleet Queue page (*Take it by hand*, above); the page offers no *other* lever on an issue
already in it, *Park* included, because a page any operator can open is not that person's hand.
The one lever it does offer is **Hand back**, and only to the recorded taker — the same hand that
took the hold, releasing it (). It is mutually exclusive
with every agent position by construction, which is the whole point of it being a state.

## What stays outside the state

The state carries the **position**. These are orthogonal axes, and putting them in the state
would multiply it:

| Signal | Stays as | Why |
|---|---|---|
| `Type:{prd,bug,task,cleanup,audit,idea,customer-bug}` | label group `Type` | a **kind**, not a position |
| `repo:*` — every lane `slot:tracker-identity` names | flat labels | a **lane**, not a position |
| `source:product` | flat label (family `source:`) | **where a filing came from**, not a position — the one label the  product and the fleet agree on |
| `security` | flat label | cross-cutting; lifts priority |
| retry-pending | flat label `agent-retry` | a **priority** signal, not a position — `Implement Queue` already says where it is |
| heartbeat (machine, `run_id`, freshness) | comment marker | liveness is not position |
| attempt count, rework returns | comment markers | immutable by design — see the reset rule above |

⚠️ **The surviving label vocabulary is duplicated across two repos, not shared.** The
control plane's label defaults must equal the constants `python3 knowledge/scripts/linear_labels.py`
prints **byte-identically**. A typo does
not raise — it silently creates a *new* label and mis-routes the issue.

⚠️ **`Type:bug` is NOTATION, not a label name.** It means "the `bug` label under the `Type`
parent". An agent that passes the notation string literally as a label name mints a
**flat, parentless impostor** whose `parent` is `None` — which the daemon's parent-group routing
gate cannot see, so the issue reads as having no kind at all. `near_miss()` normalises the
`type:` / `type›` / `type-` prefix specifically so an impostor reports as a near-miss of its
canonical bare kind instead of passing clean. The same guard catches free-typed
`Agent-Eligible` / `agent_eligible` spellings on the labels that remain.

### `source:product` — the product's requests, and the one state they must never rest in

A  builder's **feature request** (PRD 0702, ) is filed onto the same Engineering
board as a `Type:idea` issue, in a resting, **backlog-kind** state a platform admin picks, and
carries `source:product`. That label is the whole of the shared contract: the product side is
admin-configured and may rename the state, but the fleet finds requests by the label alone, in
any open state. It is declared in `python3 knowledge/scripts/linear_labels.py` (`SOURCE_PRODUCT`)
and caught by the same `near_miss()` guard as the free-typed `Source:Product` spellings.

The invariant is **[]**: **no agent works a request before a person does.** Two mechanisms
hold it, one on each side of the contract. The product refuses a request starting state that is
not backlog-kind (and not the bug starting state), because a request in a state the fleet
dispatches would be interviewed or triaged as work. And the fleet **flags any `source:product`
issue found in a state a lane dispatches** — the second half, checked from the live projection
and shown on the Ideas page's *From the product* list (`fleet-service`'s ``),
so a misconfigured target is visible rather than silently dispatched.

> **RETIRED — the `Area` label group.** `Area` was the engineering-discipline axis. Nothing
> consumed it: no saved view's `filterData` referenced a value, no script here read one, and
> the daemon named it only in comments — while 51 of 125 open issues already carried none with
> nothing breaking. Attribution was already carried twice and *derived* rather than guessed:
> `Component` from touched paths via `python3 knowledge/scripts/component_of.py`,
> and the tracker's **project** as the feature area. **Existing labels stay on existing issues** —
> retirement means "no longer written, no longer required", never "erased". Full record:
> the decision retiring the area-label group (the **`decisions`** slot).

## Guardrail

`triage` classifies
every open issue via `linear_labels.classify()` — a **state → view lookup** — and hard-fails on:

- an issue in a **state outside the vocabulary** — no saved view can show it, so it is the
   shape in the new field. `In Progress` / `In Review` are the live examples: retired,
  archived once empty, and an issue in one means a writer we believed gone is still writing;
- a **near-miss label** (the impostor / free-typed shapes above);
- the **`Triage Queue` gate on a kind that is never dispatched** (`Type:idea` / `Type:customer-bug`) —
  no daemon can run the check it is waiting for, and every other guard here is blind to it;
- **two `repo:*` lane labels** on one issue (an issue dispatches to exactly one checkout);
- a **non-PRD in a PRD-pipeline state** (`Needs Design` / `Needs Plan` are projected
  from PRD frontmatter, and a tracker cannot scope states per issue type, so this invariant is the
  only thing keeping the pipeline PRD-only);
- any **open non-idea issue with No priority** (`requires_priority()` — every creating process
  must set one; ideas are the sole exemption). Priority-in-the-body is not enough: the tracker
  `priority` field must be set.

The at-most-one routing check is gone — trivially true now that a position is one field — and
that is precisely what let the guardrail become **blocking on every PR**, inside `ci-success`'s
`needs`. It ran nightly and `--warn-only` for its whole life and had never once blocked a merge,
because the invariant it was built around could only ever be checked after the fact.

⚠️ **A retired routing label back on an OPEN issue is a `migration_warnings()` finding, never a
violation.** The P4.1 dual-write era is over —  proved the last real writer was this
repo's audit filer (fixed by ), so nothing stamps the labels any more and one
reappearing means an unknown writer: an investigation a red CI run cannot close from where it
stands — hard-failing on a condition the person reading
the red CI run is unable to clear is exactly how a guardrail earns a permanent `--warn-only`.

**It also diffs the LIVE saved views.** The guardrail used to be structurally blind to the tracker's
`customViews` `filterData`, and that blindness has now cost two outages of the same shape: a
label split updated every producer but not the views, and 14 issues needing a human went
invisible; then the lifecycle migration stripped the routing labels and **four of the seven
views — both human queues among them — silently returned zero** while the board was perfectly
healthy. `triage` fetches each view's filter and compares the label strings
**and workflow-state names** it references against the position table above — built from the
same constants `python3 knowledge/scripts/linear_labels.py` prints, never hardcoded. Diff-detection only: it flags a drifted
view, it cannot repair one.

It additionally asserts that **no open state is claimed by zero views**, derived independently
of the view sets themselves. Building that check out of the view sets would let dropping a state
from a view also drop it from the thing that verifies the view — the same class of tautology
that let the earlier hole persist.

```
# Runs against the tracker `slot:tracker-identity` names, with `slot:tracker-identity`.
triage validates kind and position on every release.


The per-PR gate — the partition check with the closed parks skipped, so it costs a handful of
requests instead of a walk of every closed issue — is the repository's spelling of
`triage` in its `slot:gate` answer, not a second id.

Wired as a CI job (`slot:gate` names it), using the repo's
`slot:tracker-identity`, in two halves: the **nightly** run is the fail-loud board audit (with `--ensure-labels`, which mutates) —
its red is filed as ONE tracked, auto-closing issue by a sibling alert
job — and the **per-PR** run is a cheap advisory canary. Neither gates a merge:  removed
the job from `ci-success.needs` because the check's subject is live board state a PR cannot
influence or repair, so a mis-birth reded every open PR and the red outlived its repair until a
manual workflow re-run. The ADVISORY marker is enforced mechanically by
the advisory-marker rule of `make validate-knowledge`.

⚠️ **The whole fleet shares one tracker account with a request budget** (`slot:tracker-identity`), so a per-PR job is a new
steady draw on it. The canary therefore passes `--skip-closed-parks`: the 30-day closed-comment
scan is ~30 of the run's ~34 requests, and a PR cannot change which issues were closed carrying
an unanswered park — that sweep tests the operator's board, not the diff.

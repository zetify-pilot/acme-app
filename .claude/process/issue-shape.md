---
type: spec
---

# Issue Tracking — creating a well-formed tracker issue

**Single source of truth** for how a `*:create` command files a tracker issue *the
right way*. Loaded by [`/fleet:bug:create`](#),
[`/fleet:task:create`](#), and
[`/fleet:idea:create`](#). Edit here
once; every creator inherits.

> **Why correctness is load-bearing.** The tracker-listening daemon **picks work up by
> workflow position** — the position IS the issue's lifecycle place — and then routes it by
> the issue's kind (`bug → bug:fix`, `task → task:implement`, `audit → audit`). So the
> position decides *whether* an issue is dispatched and the kind decides *what runs*. A
> mis-kinded or mis-placed issue is mis-routed — one filed outside `triage` skips the check
> gate entirely, a real bug driven as a task would skip reproduce-first TDD, and an audit
> driven as a task would try to ship a PR instead of running the pass. **Creation
> correctness *is* routing correctness.**
> Issues live in the tracker, never in the repo (PRD/project/initiative issues are the
> exception — those are a one-way *projection* of git by the `prd-projection` pass of the fleet's `corpus-sync` loop,
> not created here). **Create only through the Fleet tools' `file_issue`** — kind, title,
> body, `command`, and optional `repo`. Fleet ends every filing with one
> `Filed by <origin> · <command>` line — the origin is read from the environment, the
> command is yours to name (`bug:create`, `bug:fix (Rule-G deferral)`, `audit`, `own`, …).
> Never hand-write that line.

---

## Two hands write an issue, and the split is the point

Since the check gate landed, **filing and triaging an issue are different jobs done by
different sessions.** The agent that files supplies the evidence; a fresh
daemon-dispatched [`/fleet:check`](#) session
supplies the routing.

The split exists because the filer is the wrong party to triage its own find. An agent
is judged by what it found, so its severity, its urgency, and above all its sense of
whether the product ever promised the thing it wants built are all self-assessments.
This is the same lesson the audit checklist already encodes for severity — *"the
predicate is assigned by the verify sub-agent, never the finder"* — applied to the one
remaining place a finder could still route its own work straight into the fleet.

| The filer (`*:create`) sets | The checker (`/fleet:check`) sets |
|---|---|
| kind · birth position · lane (when non-default) | priority · component · feature area · milestone · blockers |
| the title and the body — evidence, repro, observed-vs-expected | the **`Implement Queue`** position (release) **or** **`Blocked · decision`** (the human's call) |
| nothing else — no priority, no project, no placement | the close verdict on duplicates / already-fixed / not-real |

**Birth positions by kind:**

| kind the filer names | birth position (slug) | board column (person-facing) |
|---|---|---|
| task, cleanup, audit | `triage` | Triage Queue |
| idea | `intake` | Intake Queue |
| a bug (a person's report, or a defect an agent found) | `bug` through `file_issue` | Triage Queue |

**Nothing but the checker may move an issue to `Implement Queue`.** That used to be a
prohibition an agent had to remember (*"leave the eligibility marker off by default"*),
and forgetting it put unreviewed work in front of the fleet. It is now structural: a
create command writes no position but the birth one above, and a position is one field —
there is no marker left to forget to omit.

**An issue leaves `triage` exactly once, by the checker, when it clears the
issue** — so an issue still sitting there means "never cleared", and the gate cannot be
silently skipped. **`triage` is re-entrant**: a checker escalation goes
`triage → Blocked · decision`, and the human's answer returns it to
**`triage`**, never straight to `Implement Queue`. The checker still owes the triage
it started, so an answered escalation is never released to the fleet un-triaged.

## Required on every created issue

- **kind** — `bug` / `task` / `idea` / `cleanup` / `audit`. The daemon's **kind** key:
  the position says *where* an issue is, this says *what it is*. A dispatchable issue with no
  kind is rejected `no-type` and is invisible to every daemon, so never omit it. Pass kind
  to `file_issue`; Fleet records it. Do not invent label-group spellings or free-type a
  kind the tools do not name.
- **Fleet records dedupe on filing.** `file_issue` searches for prior art on every mint and
  attaches the dedupe record. **Run no search of your own at create time** — Fleet already
  did. A `likely duplicate` verdict still means **file it, with the link** — suppressing a
  report is silent data loss; the checker closes a true duplicate in one action. The check
  gate **re-runs the full prior-art search** before releasing into `Implement Queue`, so the
  filer's record is a safety net under Fleet's title search, not a substitute for the gate.
  Ideas land in `intake` and never through the check gate's release, so this release guard
  does not gate them (`idea:create` still surveys open ideas via `search_issues` before filing).
- **Birth position** — every `task` / `cleanup` / `audit` an agent files goes to **`triage`**,
  and nowhere else. `file_issue` sets the birth position by kind; it is not a free parameter
  the filer invents. Ideas file into **`intake`**. A person's bug uses Fleet's bug front door
  (`file_issue` with `kind: bug`). **Never file gated work into Backlog** — nothing
  dispatches Backlog, so the check gate never ran. A gated kind resting there is a guardrail
  violation ().
- **Placement lines in the body — not a separate label write.** When a planning session or
  program decomposition knows the home, put it in the body as plain lines the checker reads:
  - `Program: <name or id>`
  - `Feature area: <name>`
  Do **not** invent a slice line for ordinary task/bug filings; ordering between issues is
  carried by **`relate` edges** (`blocked-by` / related), not by a slice field the filer guesses.
- **`blocked-by` / relate edges — set them whenever order matters; they are
  execution-ordering, not bookkeeping.** After `file_issue` returns and
  `filing.trackerKey` is known, call `relate` so the fleet scheduler skips a
  task/bug/cleanup/audit while any of its blockers is open. A chain of issues all in
  `Implement Queue` **self-serializes**. PRD issues self-serialize the same way via
  frontmatter `depends_on:` plus tracker blocker edges.
- **`priority` — ALWAYS set by the checker before an issue leaves the gate. Never left
  unset.** The filer passes none. Choose the value from the work's real urgency/impact;
  when genuinely unsure, default to Medium rather than omitting it. An issue with no
  priority is unroutable triage debt once it has left the gate.
- **Component — the checker's architecture edge**, not the filer's. Bugs/tasks/audits are
  tracker-native (no git file), so the checker attaches the component when it releases.
  Readers who need to *resolve* a path to a component id use `component_of` against the
  registry; that is a read of the architecture, not a tracker write. Resolver prints `-`
  → the path is unclaimed; skip, never guess.

## Type-specific

- **bug** (`bug:create`): `file_issue(kind: bug, …)`, whether a person reported it or an agent
  found it (Rule G, audit, a red CI lane). A bug filed through the tools is born in `Triage Queue`;
  only the bug page in Fleet's browser UI keeps the person-confirmed reproduce stage.
  Set severity and source in the body, and include **forensic context** (repro steps,
  observed-vs-expected, stack/log excerpt, suspected file:line). Severity is a
  *description of the harm observed*, and the checker **derives priority from it**:
  critical → Urgent, high → High, medium → Medium, low → Low.
  A bug carrying no observation and no artifact is not a bug report — the checker
  closes it, so do not file one.
- **task** (`task:create`): scope it small (PRD-worthy work is a PRD, not a task —
  push back if it's a feature in disguise). Say **why the work is worth doing**, not
  only what changes. The checker sets priority from urgency/impact and wires blockers.
- **idea** (`idea:create`): keep capture lightweight; it files into `intake`
  (never Backlog — nothing dispatches Backlog), where the fleet's front door sweeps it into the
  shaping interview (`/fleet:intake`), then `/fleet:route`. It can
  also resurface a second way, later: `prd:create` Phase 0.5 surfaces a project's
  remaining open ideas when its PRDs are scoped. **Ideas are exempt from the check
  gate** — they never sit in `triage`, because `/fleet:check` triages buildable
  work and an idea is not that yet — and they carry no priority (a parked idea is
  uncommitted).

## The docs-defect shape (a page is a claim, and a claim can be wrong)

A user-facing documentation page is a **claim about the product**, so it can be wrong in the
same two ways a capability can — and both defects are filed as bugs, because the thing that is wrong is a claim, not a missing feature.

- **A page promises something the product does not do.** The defect is **in the page**; the fix
  is to correct the page to what ships. This is **never** a request to build the feature —
  filing the promised-but-absent capability as work would let the docs drive scope, and the
  docs are supposed to describe scope, never set it. Title the issue after the page's wrong
  promise, and put the observed-vs-expected split in the body (what the page says / what the
  product does).
- **A shipped capability has no page, or a wrong one.** The defect is the missing or incorrect
  page; release it to be fixed **where the docs live**. A capability a customer is entitled to
  that they cannot follow is the same class of harm as a broken journey step.

**Locate the page through the `docs` slot — never a path.** The `docs` slot names the home(s),
audience and page contract; the issue body cites the page **by its id and its home**, resolved
through the slot, so the finding survives the home moving.

**Degrade.** When the repository leaves the `docs` slot unfilled, a docs finding cannot name a
home — say so in the body (the docs home is unknown here) rather than inventing one, and the
finding still files: an unclaimed page is a real defect whether or not we can point at it.

## Provenance

When a `*:create` is invoked **by an execute command** (Rule G of
[`autonomous-drive.md`](autonomous-drive.md) — an out-of-scope finding), link the
new issue back to the originating PRD/issue with a body line:

```
Found during: <KEY>
```

so the trail survives. Prefer that body line over inventing a free-form note; `relate` is
available after the key exists when a stronger edge is needed.

---

## What this is NOT

- Not a repo artifact — `*:create` writes to the tracker, never the corpus.
- Not PRD authoring — making a PRD is the `prd:create → :design → :plan` pipeline,
  whose tracker issue is projected by the `prd-projection` pass of the fleet's `corpus-sync`
  loop, not filed by `file_issue` here.
- Not a status mirror — don't push status transitions to the tracker; the `prd-projection`
  pass of the fleet's `corpus-sync` loop (`fleet-service`) projects them from `main` (see the
  **`planning-model`** slot).

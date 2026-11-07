---
title: "PRDs"
kind: concept
for: [everyone]
summary: "A PRD is one piece of work one agent can build in one session, with criteria that each can be shown to pass. It is the only thing whose status is written."
sources:
  - knowledge/prds/README.md
  - knowledge/slots/planning-model.md
  - packages/fleet-knowledge/README.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/process/planning-ladder.md
minutes: 7
---

:::lede
A PRD is the piece of work one agent builds: one page, one control, one API behaviour, one command. It says what a person will be able to do, and lists the checks that prove it. It is the one thing in the knowledge base whose status anyone writes, and only Fleet's commands write it.
:::

## What a PRD is

A :term[PRD] (product requirements document) describes one change a person can see or use, small enough for one agent to build in one working session. It carries :term[acceptance criterion] lines: each one a statement that can be shown to pass or fail on the running product.

A PRD belongs to exactly one :term[slice], the deliverable it helps finish, and files under one :term[feature area]. If the work needs no design and nobody would see anything new, it is a task, not a PRD. See [Sorting something new](knowledge-base/what-is-it).

Here is a real one, from Fleet's own planning:

::live{prd="0775" title="The Quality desk page shows what has been checked" quote="Today the only picture of what has been checked is a table with one row per area, kept up by one kind of check and a month out of date. This PRD replaces it with a page in Fleet called the Quality desk."}

## Its folder

Each PRD is a numbered folder under `knowledge/prds/`, named by its number and a short slug, for example `knowledge/prds/0775-the-quality-desk-page-shows-what-has-been-checked/`.

| File | What it holds |
|---|---|
| `prd.md` | The PRD: the problem, the scope, the requirements, the acceptance criteria, and its status |
| `design.md` | The technical and screen design |
| `ux-design.md` | Optional: visual and interaction design kept apart from `design.md` |
| `backend-plan.md`, `frontend-plan.md` | The implementation plans, split into numbered parts when large |

The front matter of `prd.md` says where the PRD belongs and how far it has got:

- `status:` how far it has got (below), and `status_history:`, a dated line for every move.
- `slice:` the slice it belongs to. `area:` the feature area it files under.
- `implements:` the [requirements](knowledge-base/promises) it makes true. Each one is covered by an acceptance criterion that cites its id.
- `depends_on:` PRDs that must ship first. `priority:` how urgent it is.

## From stub to shipped

:::steps
- [fleet] **Stub.** When you accept a proposal, or confirm a plan Fleet proposed (it plans a use you add with **Add it and start planning** by itself; **Plan this** on a feature's page asks for the rest), each PRD gets a number and a folder holding the brief, and nothing else yet.
  ::command{name="prd:create"}
- [you] **Drafted.** The PRD is written: who it is for, what they will be able to do, the acceptance criteria and a scope ledger. At a terminal, `prd:create` interviews you. On the fleet, `prd:fill` asks you the same questions in writing.
  ::command{name="prd:fill"}
- [fleet] **Designed.** The design is read off the PRD and the code as it stands. On the fleet it asks you its open choices in writing and waits for you to approve a mockup before anything merges. At a terminal, `prd:design` does the same with you there.
  ::command{name="prd:blueprint"}
- [you] **Planned.** The design is split into backend and frontend plans. This step is attended.
  ::command{name="prd:plan"}
- [fleet] **Implementing.** One session builds it and opens a green pull request. It does not merge its own work.
  ::command{name="prd:implement"}
- [fleet] **Verified.** A fresh session that never saw the code proves each acceptance criterion, in the browser for anything on screen, or sends it back.
  ::command{name="prd:verify"}
- [nobody] **Shipped.** The status change is the last commit on the PRD's own branch, so the merge itself is the moment it ships. Nobody sets it afterwards.
:::

Only a verify session may write `verified`, because the session that wrote the code never certifies it. There is one other way to reach it: the person accountable for the PRD accepts it on their own word. That is written as its own kind of line, which says plainly that the owner accepted it, not that a check passed. The line names the person and quotes what they said and when:

```yaml
- { state: verified, at: 2026-11-01T10:00:00Z, by: owner-accepted, note: "Owner accepted 2026-11-01: 'we are done, get this shipped'", accepted_by: "Dana" }
```

A line like this with no quoted, dated words, or with no name, is refused.

A PRD that will not be built is cancelled with a written reason, which reopens whatever gap it was meant to close:

::command{name="prd:cancel"}

## Why only the PRD has a status

Everything above a PRD reads its state from the PRDs. A slice is complete when its PRDs are done and its own proof has shipped; a program, when its slices are and its proof has. Neither has a status anyone can type. So there is one place where "how far has this got" is written, and every other reading is worked out from it.

:::callout{kind="why"}
A PRD's status moves only through the commands, and `shipped` only rides the merge. A status set by hand, or after the merge, can claim work is in when it is not.
:::

## Where you see it

Every PRD has its own page in Fleet, reached from its slice and from its feature's page under **Features**, where it is called a plan.

::cards{links="knowledge-base/slices, knowledge-base/promises, guides/plan/fill-and-design-a-prd"}

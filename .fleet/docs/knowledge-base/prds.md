# PRDs

A PRD is the piece of work one agent builds: one page, one control, one API behaviour, one command. It says what a person will be able to do, and lists the checks that prove it. It is the one thing in the knowledge base whose status anyone writes, and only Fleet's commands write it.

## What a PRD is

A PRD (product requirements document) describes one change a person can see or use, small enough for one agent to build in one working session. It carries acceptance criterion lines: each one a statement that can be shown to pass or fail on the running product.

A PRD belongs to exactly one slice, the deliverable it helps finish, and files under one feature area. If the work needs no design and nobody would see anything new, it is a task, not a PRD. See [Sorting something new](knowledge-base/what-is-it).

Here is a real one, from Fleet's own planning:

> An example from Fleet's own planning: **The Quality desk page shows what has been checked** (0775)
> Today the only picture of what has been checked is a table with one row per area, kept up by one kind of check and a month out of date. This PRD replaces it with a page in Fleet called the Quality desk.

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

1. [fleet] **Stub.** When you accept a proposal, or confirm a plan Fleet proposed (it plans a use you add with **Add it and start planning** by itself; **Plan this** on a feature's page asks for the rest), each PRD gets a number and a folder holding the brief, and nothing else yet.

   `prd:create` — Interactive PRD authoring grounded in the vision + agreed journey; produces prd.md and registers it in the roadmap. From an accepted proposal on the fleet, a numbered stub carrying the brief and nothing else.
2. [you] **Drafted.** The PRD is written: who it is for, what they will be able to do, the acceptance criteria and a scope ledger. At a terminal, `prd:create` interviews you. On the fleet, `prd:fill` asks you the same questions in writing.

   `prd:fill` — Fill a PRD stub on the fleet: the job story, the highest-impact dimensions and the scope offer through the fleet's written question channel over at most three rounds, then write the PRD exactly as prd:create Phase 4 would at a terminal — status prd-drafted, its journey, its claims, its ledger — by one merged PR and one landed result; it never designs, and plan stays attended.
3. [fleet] **Designed.** The design is read off the PRD and the code as it stands. On the fleet it asks you its open choices in writing and waits for you to approve a mockup before anything merges. At a terminal, `prd:design` does the same with you there.

   `prd:blueprint` — Design a drafted PRD on the fleet, just in time — discovery, technical and UX design read off the PRD and the code as merged on main after its prerequisites shipped; every fork, the mockup approval and the scope offer asked through the fleet's written question channel over at most three rounds; then design.md written exactly as prd:design would at a terminal, status designed and the commit it was designed against recorded, by one merged PR that never opens before the person approved the mockup; plan stays attended.
4. [you] **Planned.** The design is split into backend and frontend plans. This step is attended.

   `prd:plan` — Split a design into parallel backend + frontend implementation plans with edge-case coverage and design-fidelity ACs.
5. [fleet] **Implementing.** One session builds it and opens a green pull request. It does not merge its own work.

   `prd:implement` — Drive a PRD to a green, verify-ready PR — autonomous by default (implement -> verify -> fix -> open PR -> hand to an independent prd:verify session, which ships); does NOT self-merge; --manual stops after Phase A.
6. [fleet] **Verified.** A fresh session that never saw the code proves each acceptance criterion, in the browser for anything on screen, or sends it back.

   `prd:verify` — Evidence-based audit that every PRD acceptance criterion works (browser-verified for UI); flips status to verified on all-PASS or on pass-with-follow-up (every open row non-critical). A PRD already `verified`/`shipped` short-circuits to a bounded ship-only retry or a reported no-op instead of re-auditing — except a `shipped` PRD whose tracker issue never passed through a review position, which is audited rather than no-op'd.
7. [nobody] **Shipped.** The status change is the last commit on the PRD's own branch, so the merge itself is the moment it ships. Nobody sets it afterwards.

Only a verify session may write `verified`, because the session that wrote the code never certifies it. There is one other way to reach it: the person accountable for the PRD accepts it on their own word. That is written as its own kind of line, which says plainly that the owner accepted it, not that a check passed. The line names the person and quotes what they said and when:

```yaml
- { state: verified, at: 2026-11-01T10:00:00Z, by: owner-accepted, note: "Owner accepted 2026-11-01: 'we are done, get this shipped'", accepted_by: "Dana" }
```

A line like this with no quoted, dated words, or with no name, is refused.

A PRD that will not be built is cancelled with a written reason, which reopens whatever gap it was meant to close:

`prd:cancel` — Cancel a PRD with a recorded reason, reopening whatever capability gap it was closing so the planner sees the ground again.

## Why only the PRD has a status

Everything above a PRD reads its state from the PRDs. A slice is complete when its PRDs are done and its own proof has shipped; a program, when its slices are and its proof has. Neither has a status anyone can type. So there is one place where "how far has this got" is written, and every other reading is worked out from it.

> **Why:** A PRD's status moves only through the commands, and `shipped` only rides the merge. A status set by hand, or after the merge, can claim work is in when it is not.

## Where you see it

Every PRD has its own page in Fleet, reached from its slice and from its feature's page under **Features**, where it is called a plan.

Next: Slices (knowledge-base/slices) · Promises and requirements (knowledge-base/promises) · Fill and design a PRD (guides/plan/fill-and-design-a-prd)

---
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.
- **acceptance criterion**: One line of a PRD that states something the running product must do, written so it can be shown to pass or fail.
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.

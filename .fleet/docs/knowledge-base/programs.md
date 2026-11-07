# Programs

A program is a result someone gets that no single slice delivers: "someone outside the company installs Fleet and gets a pull request back the same day". It holds two or more slices, and it is done only when the whole thing works for a person, not when each piece exists.

(If this repository plans by programs.)
Your repository plans by programs. Everything on this page applies to the programs you create from now on, as well as the ones you have.

(If this repository plans by areas.)
Your repository plans by areas, so a new slice joins no program, and existing programs take no new slices. Any programs it already has keep running and finish the slices they hold. This page explains how to read them.

## What a program is

A program groups slices under one result. It adds one thing none of its slices has: its own proof, a check that the slices work **together**, end to end, for a real person or on a real screen. A program whose proof is the same as one of its slices' proofs proves nothing more than that slice, so that is refused.

Every slice of a program also names its feature area. The program is an extra grouping on top, not instead.

Here is a real one, from Fleet's own planning:

> An example from Fleet's own planning: **A Quality Desk Shows What Has Been Checked** (PG-XXX)
> Dana opens one page and sees which parts of her product have been checked, how deeply and how recently, asks the team to look at one area, and sees the result appear on the map.

## When something is a program

Only when **every** test passes: the title says literally what will be delivered; it names a person who is stuck today or the screen it shows up on; there is a day it becomes true and somebody notices; it holds at least two slices; and no existing open home fits. A program with one deliverable is a slice under a bigger name. The full tests, with examples, are in [Sorting something new](knowledge-base/what-is-it).

## What a program row holds

Each program is one row in the program register, `knowledge/programs.md` (or one file under `knowledge/programs/rows/`, named by its id):

| Column | What it says |
|---|---|
| ID | `PG-` and a number. Permanent, never reused. |
| Name | The result, in plain words. |
| Kind | `outcome` names the result someone gets; `program` names the thing that lands. A `program` must be proven on a surface a person touches. |
| Verified by | Its proof: the PRD (or recorded drill) that shows the slices working together. Empty reads **no proof named**, which is honest. |
| Requires | The capabilities the plan was worked backwards from. |
| Disposition | `adopted`, `withdrawn` with the decision record that says why, or `superseded` by another program. |

A program's slices are not listed here. Each slice names its program on its own row, so the link is written once.

> **Why:** A program has no status column and no dates. It reads complete when every slice is complete **and** its own proof has shipped. A date in a table ages silently; the order of work comes from what depends on what.

Optional prose lives in `knowledge/programs/` beside the register, named by the id (for example `PG-XXX.md`): who it is for, a worked example, the **Bar** it is held to, and a dated delivery log.

## The commands that write a program

1. [you] **Create it.** One row: the result, in plain words. No status, no dates.

   `program:create` — Author one program row — a company-scale objective in plain language — with no status and no dates, because a program's ship-state is computed and never written; from an accepted proposal on the fleet, the row and nothing else.
2. [you] **Shape it.** The framing, the slices it holds and the proof, asked in writing on the fleet. `program:decompose` does the same from a terminal, working backwards from the result to the gaps.

   `program:shape` — Shape a skeleton program on the fleet: ask the framing, the edges and the proof-and-cuts through the fleet's written question channel over at most three rounds, then write the narrative, the gap rows and edges, the roots, the proof and the cuts exactly as program:create and program:decompose would at a terminal — by one merged PR and one landed result, with no status and no dates.
3. [you] **Name its proof.** The demonstration that would show it true, written before looking at any PRD. Left empty when no honest proof exists yet. On the fleet, `program:demonstrate` asks you in writing.

   `program:prove` — Name a missing composed proof for a program, or repair one that does not prove the thing — or establish that no adequate proof exists and leave the cell honestly empty.
4. [fleet] **Deliver it.** A cycle that releases work that is ready, spots what has stalled, and asks you about anything blocking.

   `program:deliver` — One Delivery Lead cycle over a program in execution: derive truth, release fit work, wire spawned dependencies, detect stalls, interview, report, publish — or, dispatched headless, carry a human's written answer to its conclusion and resume on the fleet's cadence when it wakes the same session again.
5. [you] **Close it.** Judges whether the proof really drove the whole path. It writes no status; on a failed judgement it points the proof somewhere else.

   `program:ship` — Close a proven program by judging four gates — and, on a failure, repoint `Verified by` rather than writing any status, because the reading is computed.

## Where you see it

The Programs page lists every program. Each program's page shows its slices, its proof and what you can do next.

On the Program page (#program):
1. The slices it holds, each with its own state.
2. Its proof, and whether it has shipped.
3. What you can do from here, such as starting or stopping delivery.

Next: Slices (knowledge-base/slices) · Planning by areas or by programs (knowledge-base/planning-modes) · Shape a program and hand it to the fleet (guides/plan/shape-a-program)

---
- **program**: A larger result that two or more slices add up to and none delivers alone, used only by repositories that plan by programs.
- **proof**: The check, named on a program or slice, that shows it works end to end for a real person or on a real screen.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.

---
title: "Programs"
kind: concept
for: [owner, developer]
summary: "In a repository that plans by programs, a program is a larger result that two or more slices add up to, proven by a check of its own."
sources:
  - knowledge/programs.md.tmpl
  - knowledge/slots/planning-model.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/process/planning-ladder.md
  - packages/fleet-knowledge/src/fleet_knowledge/planningmode.py
  - docs/design/2026-10-27-planning-without-programs.md
minutes: 7
---

:::lede
A program is a result someone gets that no single slice delivers: "someone outside the company installs Fleet and gets a pull request back the same day". It holds two or more slices, and it is done only when the whole thing works for a person, not when each piece exists.
:::

:::mode{programs}
Your repository plans by programs. Everything on this page applies to the programs you create from now on, as well as the ones you have.
:::
:::mode{areas}
Your repository plans by areas, so a new slice joins no program, and existing programs take no new slices. Any programs it already has keep running and finish the slices they hold. This page explains how to read them.
:::

## What a program is

A :term[program] groups slices under one result. It adds one thing none of its slices has: its own :term[proof], a check that the slices work **together**, end to end, for a real person or on a real screen. A program whose proof is the same as one of its slices' proofs proves nothing more than that slice, so that is refused.

Every slice of a program also names its :term[feature area]. The program is an extra grouping on top, not instead.

Here is a real one, from Fleet's own planning:

::live{program="PG-043" title="A Quality Desk Shows What Has Been Checked" quote="Dana opens one page and sees which parts of her product have been checked, how deeply and how recently, asks the team to look at one area, and sees the result appear on the map."}

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

:::callout{kind="why"}
A program has no status column and no dates. It reads complete when every slice is complete **and** its own proof has shipped. A date in a table ages silently; the order of work comes from what depends on what.
:::

Optional prose lives in `knowledge/programs/` beside the register, named by the id (for example `PG-043.md`): who it is for, a worked example, the **Bar** it is held to, and a dated delivery log.

## The commands that write a program

:::steps
- [you] **Create it.** One row: the result, in plain words. No status, no dates.
  ::command{name="program:create"}
- [you] **Shape it.** The framing, the slices it holds and the proof, asked in writing on the fleet. `program:decompose` does the same from a terminal, working backwards from the result to the gaps.
  ::command{name="program:shape"}
- [you] **Name its proof.** The demonstration that would show it true, written before looking at any PRD. Left empty when no honest proof exists yet. On the fleet, `program:demonstrate` asks you in writing.
  ::command{name="program:prove"}
- [fleet] **Deliver it.** A cycle that releases work that is ready, spots what has stalled, and asks you about anything blocking.
  ::command{name="program:deliver"}
- [you] **Close it.** Judges whether the proof really drove the whole path. It writes no status; on a failed judgement it points the proof somewhere else.
  ::command{name="program:ship"}
:::

## Where you see it

The Programs page lists every program. Each program's page shows its slices, its proof and what you can do next.

::screen{route="program" focus="PG-043" pins="slices,proof,levers"}
1. The slices it holds, each with its own state.
2. Its proof, and whether it has shipped.
3. What you can do from here, such as starting or stopping delivery.

::cards{links="knowledge-base/slices, knowledge-base/planning-modes, guides/plan/shape-a-program"}

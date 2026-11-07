---
title: "Shape a program and hand it to the fleet"
kind: guide
for: [owner]
summary: "Turn a bare program into slices and a proof through a few rounds of questions, then start it so the fleet plans and builds the rest."
routes: [program]
mode: programs
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-knowledge/src/fleet_knowledge/templates/board.js
  - packages/fleet-service/src/fleet_service/api/shape.py
  - packages/fleet-service/src/fleet_service/api/drive.py
  - packages/fleet-service/src/fleet_service/dispatch/autodrive.py
  - knowledge/features/fleet-program-drive.md
minutes: 8
---

:::lede
When you are done your :term[program] will have its slices and its proof written into the knowledge base, and the fleet will be driving it: asking for every planning step itself and bringing you only the questions only you can answer.
:::

## The program page

Open a program from **Programs**. Under its header, **Where it is** says where the program stands. Below come any questions it is waiting on, the **Delivery** box, the **To do** list of moves a person owes, and the **Slices**, each with its "Done when".

::screen{route="program" pins="slices,proof,levers"}
1. The slices, each with its progress and the sentence that says when it is done.
2. The proof: the end-to-end check that shows the program delivered.
3. The controls that shape it and drive it.

## Shape a bare program

A program filed from an idea starts as a name and a sentence. :term[Shaping] writes the rest: the narrative, the gaps, the slices and the proof.

:::steps
- [you] **Press Shape this program.** On a program that has its narrative but not its slices, the button is **Decompose this program**.
- [fleet] **A machine runs the shaping.** The box shows it queued, then running.
- [you] **Answer its questions.** Each round arrives as question cards on the program's page and in the [Cockpit](guides/daily/cockpit). See [Answer a question](guides/daily/answer-a-question).
- [fleet] **It opens a pull request and merges it.** The box shows the merged pull request.
- [nobody] **The page catches up.** Once your knowledge base syncs the merge, the program shows its slices and proof.
:::

While it runs, **Stop shaping** ends it (on the program page it sits in the header's **⋯** menu). Questions it asked are withdrawn. A failed run offers **Try again**. **Shape it again…** redoes a finished shaping and asks for a note on what to change.

:::callout{kind="tip"}
Rather answer in a conversation than on cards? **Run it yourself in an agent session** opens a session on a machine that asks you the same things. Where no session can open, the box shows the command to run in a terminal of your own. See [Do a planning step yourself](guides/plan/do-a-step-yourself).
:::

## Start the fleet driving it

A program is driven only after a person starts it, and nothing is driven on its own.

:::steps
- [you] **Press Start delivering** in the **Delivery** box.
- [fleet] **It plans what is missing.** For every slice and PRD that still needs it, the fleet asks for refining, a PRD stub, filling and designing, by itself.
- [fleet] **It plans and builds.** A designed PRD is planned, and a planned PRD is built and then verified by a separate session.
- [you] **Answer what it asks.** Only the steps a person must take reach you, as questions.
- [fleet] **A closing check runs at the end.** When the program looks proven, a separate run checks whether it can close. Gaps it finds are filed as work, and the check runs again when they are done.
:::

Starting a bare program shapes it first: the same click asks for the shaping, then for a proof if none is named, and starts delivering once both land.

The box shows when the drive started and who started it, its cycles and when the next one is due. **Run a cycle now** asks for the next cycle at once. **Stop** stops the drive and lets a running cycle finish; planning the fleet asked for and has not finished is withdrawn, while steps a person asked for stay. **Keep delivering** takes a stop back.

:::callout{kind="careful"}
You cannot shape a program while it is being driven. Its cycles release work between a shaping's rounds of questions. Stop the drive first, shape it, then start it again.
:::

When the box says **Nothing needed from you — the fleet is driving it**, there is nothing for you to do.

::cards{links="guides/plan/refine-a-slice, guides/plan/fill-and-design-a-prd, knowledge-base/programs"}

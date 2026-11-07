---
title: "Refine a slice"
kind: guide
for: [owner]
summary: "Sharpen a slice cut from a brief into a clear Done when, its promises and the bar it is held to, by answering one or two rounds of questions."
routes: [slice]
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-knowledge/src/fleet_knowledge/templates/board.js
  - packages/fleet-service/src/fleet_service/api/shape.py
  - packages/fleet-service/src/fleet_service/dispatch/autodrive.py
  - knowledge/features/fleet-program-drive.md
minutes: 5
---

:::lede
When you are done your :term[slice] will say exactly what "done" means, in a sentence someone can check, with the promises it keeps and the bar it is held to, all merged into your knowledge base.
:::

## What refining does

A slice is the unit that finishes: a "Done when" sentence plus the PRDs that make it true. A slice cut from a brief starts rough. Refining is the planning step that sharpens it. The fleet runs it on a machine and asks you a discovery round, then a round of decisions: what kind of slice it is, the sharpened "Done when", the promises it keeps, and its bar. It then writes all of it by one pull request it merges.

## The slice page

A slice's page shows its state, its "Done when", how many of its PRDs have shipped, and the PRDs themselves. It is a page to read: the moves you owe on a slice are on its program's page, labelled with the slice.

::screen{route="slice" pins="done-when,prds"}
1. **Done when**: the sentence that says when this slice is finished.
2. Its PRDs, each with where it stands.

## Refine one

:::mode{programs}
1. Open the slice's program. Its **To do** list has a row for each slice waiting to be refined, labelled with the slice.
2. Press **Refine this slice →**. It takes you to the slice's page and asks the fleet to refine it there.
3. Answer the questions as they arrive on the slice's page and in the [Cockpit](guides/daily/cockpit).

When the program is being driven you do not need to press anything: the fleet asks for every refinement the program's slices still need, and only the questions reach you. See [Shape a program and hand it to the fleet](guides/plan/shape-a-program).
:::
:::mode{areas}
1. Open the slice's page, from its feature's **Work** tab.
2. Press **Start this slice**. The fleet asks for the slice's planning steps itself, starting with refining it when it needs it.
3. Answer the questions as they arrive on the slice's page and in the [Cockpit](guides/daily/cockpit).

See [Use the Features page](guides/plan/work-by-area) for what Start does after refining.
:::

Either way the fleet runs the refinement on a machine, merges the result by a pull request, and the slice shows its new "Done when" once your knowledge base syncs.

:::callout{kind="careful"}
A finished, withdrawn or abandoned slice is past refining, and the fleet will not run it. A finished slice's promise is never rewritten to fit what shipped.
:::

## Refine it in a session instead

To change a slice with you in the conversation, run the attended command in a session of your own. It changes a slice's "Done when", what it depends on, what proves it, or its bar, and refuses the changes a hand edit would let through: an id that does not resolve, a cycle between slices, a finished promise rewritten.

::command{name="slice:edit"}

::cards{links="guides/plan/fill-and-design-a-prd, knowledge-base/slices, guides/plan/do-a-step-yourself"}

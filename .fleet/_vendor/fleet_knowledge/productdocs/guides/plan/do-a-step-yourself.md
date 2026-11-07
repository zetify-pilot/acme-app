---
title: "Do a planning step yourself"
kind: guide
for: [developer, owner]
summary: "Fill, design or plan a PRD in your own session, and tell the fleet so it does not start the same step."
sources:
  - packages/fleet-service/src/fleet_service/api/tools_planning.py
  - packages/fleet-service/src/fleet_service/dispatch/autodrive.py
  - packages/fleet-service/src/fleet_service/store/planninghold.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/features/fleet-program-drive.md
minutes: 4
---

:::lede
When you are done you will have filled, designed or planned a PRD yourself, in a session you drive, while the fleet left that step alone instead of starting a second copy of it.
:::

## Why the fleet has to be told

Under a driven program the fleet asks for every planning step by itself. If you are designing a PRD on your own branch, nothing the fleet reads shows that until your branch reaches GitHub, and by then it may have started its own design of the same PRD. So your session tells it first. That is a :term[planning hold].

:::callout{kind="why" figure="77 minutes"}
passed between the fleet starting its own design of a PRD and the operator's local branch for the same design reaching GitHub. Only the session saying so as it starts arrives in time.
:::

## Hold a step and do it

:::steps
- [you] **Connect your session to Fleet.** Your terminal needs Fleet's session tools, through your own key. See [Connect your terminal](guides/your-tools/connect-your-terminal).
- [you] **Run the command for the step.** For a design or a plan, run it with the PRD's number. The command calls `hold_planning` as its first step, naming the PRD, the step and your branch.
  ::command{name="prd:design"}
- [fleet] **The fleet leaves that step alone.** It does not ask for that step of that PRD while the hold is live. The program's **Delivery** box lists the step under **Not started yet**, with "held: being worked on in *your branch* by *you*" and a **Release hold** button beside it.
- [you] **Finish and merge.** Your pull request moves the PRD's status on.
- [nobody] **The hold ends by itself.** It lapses the moment the PRD's status moves.
:::

A hold names one of three steps, each taken from the status it starts from: **fill** from a stub, **design** from drafted (or from designed, to design again), and **plan** from designed. Only a person's key can take a hold; a fleet run cannot.

:::callout{kind="careful"}
If you give up the step, release the hold. From that session, call `hold_planning` again with
`release=true`; or, if the session is already closed, open the program's page and press **Release
hold** beside the step under **Not started yet**. Otherwise the fleet stays off that step until the
PRD's status changes. Releasing from the page is recorded with your name.
:::

## Shaping steps run in a session instead

For a program, a slice or a PRD stub, the shaping box on its page offers **Run it yourself in an agent session**. It opens a session on a machine that asks you the same things in a conversation instead of on question cards. Where a session cannot open, the box shows the command to run in a terminal of your own.

::cards{links="guides/plan/fill-and-design-a-prd, guides/plan/shape-a-program, guides/sessions/open-a-session"}

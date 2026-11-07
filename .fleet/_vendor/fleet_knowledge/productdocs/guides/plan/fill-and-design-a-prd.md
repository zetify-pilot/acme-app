---
title: "Fill and design a PRD"
kind: guide
for: [owner, developer]
summary: "Turn a PRD stub into a drafted PRD, then a designed one, by answering the fleet's questions and approving its mockup."
routes: [prd]
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/shape.py
  - packages/fleet-service/src/fleet_service/dispatch/autodrive.py
  - packages/fleet-service/src/fleet_service/dispatch/design.py
  - packages/fleet-service/src/fleet_service/dispatch/plan.py
  - knowledge/features/fleet-program-drive.md
minutes: 6
---

:::lede
When you are done your :term[PRD] will have gone from a stub to a drafted PRD with acceptance criteria, and on to a design you approved, ready to be planned and built.
:::

## The steps a PRD goes through

A PRD is the build unit: one piece of work with acceptance criteria one session can build. Before it is built it passes through planning steps, each one a change to its status.

| Step | Turns it from | Into | You give it |
|---|---|---|---|
| **Fill** | a stub | a drafted PRD | Answers about the job it does and its scope |
| **Design** | drafted | designed | Answers on the design choices, and your approval of its mockup |
| **Plan** | designed | planned | Nothing: it asks no questions |

Each step runs on a machine, asks you through question cards when it needs you, and lands as one pull request it merges.

## Fill a stub

:::steps
- [you] **Open the PRD.** A stub's page carries a box with **Fill this PRD**.
- [you] **Press it.** The box shows the run queued, then running.
- [you] **Answer its questions.** Up to three rounds: what job the PRD does, the parts that matter most, and an offer of what is in and out of scope. They arrive on the PRD's page and in the [Cockpit](guides/daily/cockpit).
- [fleet] **It writes the PRD and merges it.** The PRD now has its requirements and acceptance criteria.
:::

**Stop filling** ends a fill in progress. **Fill it again…** redoes a finished one and asks for a note on what to change. Filling is offered only on a stub: a PRD past that is past filling.

## Design it

You do not press anything to design a PRD on the fleet. Once its program is being driven, or its slice was started, the fleet asks for the design of each drafted PRD by itself.

:::steps
- [fleet] **It designs against the code as it is now.** The design is read off the PRD and the code as merged, after the work it depends on has shipped.
- [you] **Answer the design questions.** Each fork comes as a question with options, the recommended one first.
- [you] **Approve the mockup.** For anything you will see on screen, a question carries a clickable :term[mockup]. Look through it and answer; your answer approves the whole design. See [Answer a question](guides/daily/answer-a-question).
- [fleet] **It writes the design and merges it.** The pull request never opens before you approved the mockup.
:::

:::callout{kind="why"}
Designing just in time, against the code as merged, means a design never describes code that changed under it while it waited.
:::

Until the PRD ships, the box under its steps says what is happening to it or what it waits for, in the same words its feature's page uses. The label beside the state names the step: Design, Plan, Build, Checks or Check.

- *Fleet is designing it now* (or *checking it*, *building it*), and when it started.
- *Waiting for its pull request's checks* after it was built, while its pull request's checks run. Fleet checks it once they finish.
- *Waiting for a free machine*, and since when it has been in line. *No machine can take it right now* when no machine is set up to do that step; **The Queue** shows why.
- *Waiting for your answer*, or *Waiting for Ana Ruiz's answer* when Fleet asked someone else. **Answer it** or **See the question** takes you to it.
- *Waits for "Keys rotate in place" to ship* when it depends on other PRDs that have not shipped. Each name opens that PRD.

The box never names the machine, and it follows the work while the page is open. With nothing open it says what would start the design, such as starting its slice.

## Object to a design

A design you disagree with can be stopped before anything is built. On the PRD's **Design** tab, under **The approach — recorded before any code exists**, press **Object to this approach**, say which choice you disagree with and why, and press **Record objection**.

:::steps
- [you] **Record the objection.** The PRD's design and planning pause, and no build is started for it, while the objection waits.
- [fleet] **An agent answers it.** It either revises the design or gives its reason for keeping it. The answer appears on the same tab, under the objection.
- [fleet] **The PRD moves on.** Once the answer lands, planning and building go ahead.
:::

Only this control pauses the work: a comment on the PRD or in a session does not. Once building has started, the control is no longer offered, and a comment on the pull request is the way in. Bugs and small tasks have no design step, so nothing about them can be objected to here.

## Drop a PRD nobody needs

**Close issue…** on the PRD's page, then **Not needed**, asks for your reason and cancels the PRD in your repository: a pull request sets its status to cancelled with that reason. Until it merges, the PRD's page reads **Cancelling**, and the issue closes when it does.

## Then planning and building

A designed PRD is planned next, and a planned PRD is built and verified. Under a driven program the fleet asks for both. You see it on the PRD's page and on its program's **Delivery** box.

:::callout{kind="tip"}
Want to design or plan a PRD yourself, in your own session? Tell the fleet first so it does not start the same step. See [Do a planning step yourself](guides/plan/do-a-step-yourself).
:::

::cards{links="guides/plan/do-a-step-yourself, guides/daily/answer-a-question, knowledge-base/prds"}

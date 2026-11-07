---
title: "Machines, seats and runs"
kind: concept
for: [developer, admin]
summary: "Machines ask Fleet for work, seats say how much each one takes on, and a run is one attempt at one issue."
sources:
  - ARCHITECTURE.md
  - packages/fleet-service/src/fleet_service/api/glossary.py
  - packages/fleet-service/src/fleet_service/api/leasing.py
  - packages/fleet-service/src/fleet_service/dispatch/drain.py
  - packages/fleet-service/src/fleet_service/dispatch/budget.py
  - packages/fleet-service/src/fleet_service/dispatch/assignment.py
  - packages/fleet-daemon/src/fleet_daemon/seatreconcile.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/features/fleet-dispatch.md
minutes: 7
---

:::lede
Fleet's agents run on machines you provide. A machine never waits to be told what to do: it asks Fleet for work, runs one session, and says how it ended. Fleet decides everything else.
:::

## A machine asks, Fleet decides

A :term[machine] is a computer running Fleet's worker. It opens every connection itself and listens on no port. It tells Fleet what it can run and keeps saying it is still there. When it has room, it asks for work.

Fleet picks the best issue it may hand out and takes a :term[claim] on it in the same step, so two machines can never hold the same issue. The claim comes with a :term[lease]. The machine renews the lease only by reporting what the session did. If a machine goes quiet, the lease runs out and the issue goes back to its queue for another machine.

:::callout{kind="why"}
The worker has hands and no opinions. Which command runs, which model it uses, and how long is too long are all decided by Fleet, so changing any of them never means updating the machines.
:::

## Seats

Each machine has :term[seat]s, and each seat holds one session at a time.

- A **dispatch seat** works issues from the queue on its own.
- An **interactive seat** is where a person runs a session.

You set how many of each a machine runs in **Settings › Machines**. A seat you remove finishes its current run first.

::screen{route="settings:machines" pins="machine,seats,drain,add"}
1. One machine.
2. How many dispatch and interactive seats it runs.
3. **Drain** it before maintenance: it finishes what it holds and takes nothing new. **Resume work** lets it take work again.
4. **Add machine**.

A machine that is :term[draining] still reports and still finishes its runs; it just takes nothing new.

::action[Open Machines]{route="settings:machines"}

What every seat is doing right now is on **System › Machines**.

## Runs

A :term[run] is one attempt at one issue on one machine. It ends in exactly one outcome, and the **Runs** page shows each run with why it ended, in plain words. It is not in the sidebar: open it from an issue's "every run" link or a machine's **This machine's runs**.

Each run is given a model from the mix set in **Settings › Model config**, chosen only among the models that machine can pay for. The model is recorded on the run.

::action[Open Runs]{route="runs"}

## When runs keep failing

Fleet stops offering work before failures pile up, at three levels.

| Level | What happens | Who clears it |
|---|---|---|
| **One issue** | An issue that keeps failing stops being offered and moves to `Failed`. The machine that just gave up on an issue is not handed it straight back. | A person resets it. |
| **One machine** | A machine that gives up on issue after issue, with nothing succeeding in between, is drained. | A person clears the drain. |
| **Many machines** | When several seats fail the same way at once, they are held out until the window passes. When a model provider keeps refusing its key, work that needs it is held off and Fleet lets one test run through now and then. | It lifts by itself. |

The **System** page says whether the fleet is dispatching, read from what it recorded rather than from logs. It names every reason a machine cannot take work.

::cards{links="guides/team/machines-and-seats, troubleshooting/machine-drained, troubleshooting/run-failed"}

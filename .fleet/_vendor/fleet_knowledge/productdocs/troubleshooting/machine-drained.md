---
title: "A machine was drained"
kind: troubleshooting
for: [owner, admin]
summary: "A machine takes no new work. Tell a drain someone asked for from one Fleet put on it, and clear or resume each the right way."
routes: [system:machines, box]
sources:
  - packages/fleet-service/src/fleet_service/api/drainclear.py
  - packages/fleet-service/src/fleet_service/api/seatstep.py
  - packages/fleet-service/src/fleet_service/api/glossary.py
  - packages/fleet-service/src/fleet_service/dispatch/drain.py
  - packages/fleet-service/src/fleet_service/dispatch/breaker.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/features/fleet-dispatch.md
minutes: 6
---

:::lede
A :term[draining] machine still reports and finishes what it holds, but takes nothing new. Someone may have asked for that, or Fleet may have done it because the machine kept failing. The two look alike and are undone differently.
:::

## What you see

| What you see | Likely cause | What to do |
|---|---|---|
| **Draining**, "Draining since" a time, "asked by" a person, on Settings › Machines | A person pressed **Drain** | Press **Resume work** when ready |
| **auto-drained**, "taken out after repeated give-ups", or "Took itself out after" so many give-ups | Fleet took the machine out after it failed issue after issue | Fix the machine, then **Clear this drain…** |
| "held by the signature circuit breaker" | Several seats failed the same way at once | Nothing. It lapses on its own |
| "dispatch paused for" a provider | The model provider keeps refusing the key | See [Nothing is being picked up](troubleshooting/fleet-paused) |
| A session tile reads **Step done** | The session's step finished, but the seat is still held open | Close the session |

## Someone drained it

A person pressed **Drain** on the machine, for example before maintenance. Nothing is wrong with it.

::screen{route="settings:machines" pins="machine,drain"}
1. The machine, with **Draining** beside its state.
2. "Draining since" a time and who asked, and the **Resume work** button.

:::steps
- [you] **Check it is safe.** Ask the person named beside "asked by" whether their work on the machine is finished.
- [you] **Press Resume work.** On [Settings › Machines](app:settings:machines). The machine can take new work again.
:::

## Fleet drained it

Fleet takes a machine out when it gives up on several issues in a row with nothing succeeding in between. That usually means the machine itself is broken, not the issues. A refused GitHub credential drains it on the first give-up. The number of give-ups is set on your Fleet service; the card shows it.

The System page's Machines part says how many machines "paused itself" this way, and the [Cockpit](app:cockpit) lists each one as "Took itself out after" so many give-ups.

:::steps
- [you] **Open the machine.** On [System › Machines](app:system:machines), press **Clear drain…** on its row. That opens the machine's own page; nothing on the list clears it.
- [you] **Read why.** The reason says how many give-ups in a row there were. Open the machine's recent runs on [Runs](app:runs) to see how each one ended.
- [you] **Fix the machine.** Restarting it does not clear the drain, and is not meant to.
- [you] **Clear this drain….** Write what you did about it, or why it should run anyway. That sentence is required and recorded against your name. Confirm **Clear the drain**.
- [fleet] **It takes work again.** The next issue on the board can go to this machine.
:::

:::callout{kind="careful"}
Clearing a drain does not fix the fault. A machine that is still broken will spend real model cost failing again, and Fleet will drain it again. Fleet refuses the clear outright when the machine's GitHub credential is refused on every repository it holds.
:::

A failure seen on many seats at once is different: the circuit breaker holds the seats that took part and releases them by itself when the window passes. It does not count toward a drain and needs no clearing.

## A seat held after its step finished

When you open a session for one planning step, such as designing a PRD, Fleet holds the seat open while it waits for your answers. If the PRD moves past that step some other way, the session has nothing left to do. Its tile reads **Step done**: "This step is already done." The seat is no longer held for an answer and goes back on the ordinary idle timer, but nothing closes it except you.

:::steps
- [you] **Keep what you need.** Copy anything from the session you want to keep.
- [you] **Close it.** Use the close control beside the message, on [Terminals](app:terminals) or the session's own page. The seat is free for other work.
:::

::cards{links="concepts/machines-seats-runs, guides/team/machines-and-seats, troubleshooting/run-failed"}

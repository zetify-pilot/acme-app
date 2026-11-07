---
title: "Run machines and set their seats"
kind: guide
for: [admin, owner]
summary: "On Settings › Machines, add a machine, set how many dispatch and interactive seats it runs, drain it, resume it or remove it."
routes: [settings:machines]
sources:
  - packages/fleet-service/src/fleet_service/api/workers.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
minutes: 6
---

:::lede
When you finish this guide, each machine that runs Fleet's agents has the number of seats you chose. You will also know how to pause a machine without losing work, and how to cut one off.
:::

## Machines and seats

A machine (also called a worker) is a Linux computer you own, such as a cloud server or a computer in your office. It runs Fleet's agents. Each machine has seats, and there are two kinds:

- A **dispatch seat** works issues from the queue on its own, one at a time.
- An **interactive seat** is where a person runs a session on that machine. A machine with zero interactive seats only works the queue. The number of interactive seats is how many sessions the machine holds at once. When every one is taken, opening a session there says the machine is full and names what holds its seats: your sessions, colleagues' sessions, or seats on a machine that stopped reporting. Raise its **Interactive seats** here to make room.

**Settings › Machines** has one row per enrolled machine (a worker), and that is where you set its seats. A machine that joined with the shared secret instead — a `fleet-daemon` machine — has no row there; open it under System › Machines, and remove it from its own page. To see what every seat is doing right now, follow the link at the top of the list to System › Machines.

::screen{route="settings:machines" pins="machine,seats,drain,add"}
1. The machine: its name, its state, the Fleet version it runs, when it last reported, and **Seat details**.
2. Its seats: one counter for **Dispatch seats** and one for **Interactive seats**.
3. **Drain** (or **Resume work** while it drains) and **Remove…**, which cuts the machine off from Fleet.
4. **Add machine** opens the panel that adds another.

A machine's state is one of these: **Starting** (it joined, but no seat has reported yet), **Online**, **Partly online** (some seats are not reporting), **Draining**, or **Offline** (no seat has reported recently). Point at the state to read what it means for that machine.

## Change a machine's seats

:::steps
- [you] **Set the counts.** Use **−** and **+** on **Dispatch seats** and **Interactive seats**. A **Save** and a **Cancel** button appear as soon as the counts differ from what the machine runs.
- [you] **Save.** Click **Save**.
- [fleet] **The machine applies it live.** New seats start without a restart or a redeploy. A seat you removed finishes its current run before it stops. The row says how far the change has got.
:::

You can make the same change from the machine's own page. Click **Seat details**, then **Change seats…** in its **Seats** section, choose the two counts and click **Set these seats**.

## Pause a machine with Drain

**Drain** tells a machine to finish the work it is doing and take no new work, for example before maintenance or before you remove it. The row then says **Draining since …** and who asked. Click **Resume work** to let it take work again.

:::callout{kind="tip"}
A :term[draining] machine still reports and still finishes what it holds. Nothing is cut short, so drain a machine first when you plan to stop it.
:::

## Remove a machine

**Remove…** opens a box titled **Remove** and the machine's name. Click **Remove this machine** to confirm. The machine leaves the list either way; what is revoked depends on how it joined Fleet.

- **A machine that enrolled with a one-time code** has its enrolment revoked: it stops being offered work, any work it holds is released, and it leaves the list. The machine itself is not changed. To bring it back, run the worker install on it again with a fresh one-time code.
- **A machine that joined with the shared secret and never enrolled** — a `fleet-daemon` machine — has its registration retired instead: it stops being offered work, any work it holds is released, and it leaves the list. Fleet refuses its next request, and registers it again if it says hello.

You can remove either kind from its own page under System › Machines; Settings › Machines carries the enrolled ones. A machine that is still reporting is refused, so stop its units first and wait for it to go silent. If its units are already stopped, remove it from its own page — that is the only place that reaches a machine with no enrolment.

## Add a machine

:::steps
- [you] **Open the panel.** Click **Add machine** (on Settings › Set up the button is called **Add worker**). The **Add a machine** panel lists what the machine needs.
- [you] **Choose its seats.** Set **Dispatch seats** and **Interactive seats** for the new machine.
- [you] **Install it.** Click **Get the install command** and follow the panel: it gives you one command and a one-time code for the machine. Installing is covered in Fleet's install guide, not here.
- [fleet] **The machine arrives.** The panel follows the machine as it installs and says when it is ready: its dispatch seat and terminal seat are both reporting. **Add another** starts the next one.
:::

If no machine has used the code after a few minutes, the panel lists the three most likely reasons and what to do about each.

::action[Open Machines]{route="settings:machines"}

::cards{links="concepts/machines-seats-runs, troubleshooting/machine-drained, guides/team/connect-github-and-tracker"}

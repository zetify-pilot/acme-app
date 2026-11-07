---
title: "A session will not start, or stopped responding"
kind: troubleshooting
for: [everyone]
summary: "A session waits for a box forever, or its terminal stopped answering. What each message means and how to get it back."
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/glossary.py
  - knowledge/features/fleet-sessions.md
minutes: 5
---

:::lede
A session runs on a :term[box], one of your machines. When it will not start, there is usually no machine free to take it. When it stops answering, the connection or the machine went away, and the message on the tile says which.
:::

## What you see

| What you see | Likely cause | What to do |
|---|---|---|
| **Waiting for a box**, "Recorded. No box has taken it yet." | No machine has taken the request yet | Wait, or check the reason below |
| "No workstation is online, so the request waits for one." or **No machine** | No machine is offering sessions | Ask an admin to bring a machine online |
| "Every interactive workstation seat is busy, so the request waits." or **No free seat** | Every machine's session seats are taken | Close sessions you no longer need |
| **No lane** | Fleet is not told which repository sessions open in | An admin sets it on the service |
| **No engine** | No machine holds the coding agent the click would run | An admin sets up a machine with that engine |
| "connection lost — reconnecting…" | Your browser lost the stream | Wait. It reconnects by itself |
| "not attached — the box has not streamed for a while" | The machine stopped sending | Reopen the session |
| "This session is open in another tab or window." | The same session is open elsewhere | **Take over here** |
| "This session no longer exists.", or the session is under "Lost with their boxes" | The machine holding it is gone | Start a new session, or **Resume** an agent session |

## It will not start

When you open a session, Fleet records the request and the first machine with a free slot takes it. The tile reads **Waiting for a box** until one does, then **Starting**, then the terminal opens.

The Workstation page lists, above the sessions, anything that would stop a request from ever being taken:

::action[Open Workstation]{route="workstation"}

:::steps
- [you] **Read the warning.** **No machine**: no machine has offered itself for sessions yet. **No free seat**: requests are waiting and every reporting machine is full. **No lane** or **No engine**: Fleet's setup is missing something, and no amount of waiting helps.
- [you] **Free a slot, or ask an admin.** For No free seat, close sessions you are done with on [Terminals](app:terminals). The other three need someone who runs your machines; see [Machines and seats](guides/team/machines-and-seats).
- [fleet] **It starts.** As soon as a machine can take it, the request is picked up. You do not need to ask again.
:::

If a machine took the request and could not open it, the session ends as failed. If no machine took it in time, it is abandoned and nothing ran. Open a new one once the cause is fixed.

## It stopped responding

:::steps
- [fleet] **"connection lost — reconnecting…".** Your browser lost its link to the session. It retries by itself, and counts the tries. Nothing on the machine has stopped.
- [you] **"not attached".** The machine has not sent anything for a while. Reopen the session to try again. If you typed a message while it was disconnected, it was kept: "not connected — your message was kept".
- [you] **"This session is open in another tab or window."** Only one window drives a session at a time. Press **Take over here** to drive it from this one.
- [you] **An agent conversation did not load.** "The conversation did not load: nothing arrived from the agent's machine." Press **Retry**.
:::

## The machine is gone

If the machine holding a session stopped existing, the session moves under "Lost with their boxes" and reads "This session no longer exists." The terminal and anything not pushed went with the machine.

An ended agent session has a **Resume** button. It starts the session again on its own conversation, in its own checkout and on its own branch, without running the command it was opened with a second time. A plain terminal cannot be resumed; open a new one.

:::callout{kind="careful"}
Push your work from a session before you leave it for long. A session's checkout lives on its machine, and a machine that is removed or replaced takes unpushed work with it.
:::

If a machine went away because Fleet took it out of service, see [A machine was drained](troubleshooting/machine-drained).

::cards{links="guides/sessions/open-a-session, guides/sessions/take-over-and-restore, troubleshooting/machine-drained"}

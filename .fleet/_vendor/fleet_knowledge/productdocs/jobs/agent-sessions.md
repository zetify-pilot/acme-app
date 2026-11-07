---
title: "Work with agent sessions"
kind: job
icon: sessions
group: use
for: [developer]
summary: "Open a session, drive it, review what it did, and look in on the fleet's own runs."
minutes: 3
---

:::lede
Everything an agent does in Fleet happens in a session on one of your machines. Some sessions the fleet starts on its own; others you open from the browser and drive. This path shows you how to open one, talk to it, and read what it changed.
:::

## The big picture

:::ideas
- **Run.** The fleet's own attempt at one issue. Nobody drives it. You open it from the issue it works on, or from what the Queue says a machine is running.
- **Session.** An agent, or a plain terminal, that you open from **Terminals** and drive yourself, in a repository's checkout.
- **Shell.** A terminal on the machine itself, as its login user, outside any session. You open it with the machine's **Shell** button.
:::

All three run on the same machines. A machine has :term[seat]s, and each seat holds one session at a time. A run takes a dispatch seat, a session you open takes an interactive seat, and a shell takes none. That is why a new session can wait: it needs a machine with a free interactive seat.

A session starts on a branch of its own. Its page shows that branch's pull request and how its checks stand, and its transcript is kept so you can open it later. When an agent session asks you something, it says so on its tile and in the Cockpit. You can watch a run's conversation the same way, and once a run has ended, **Talk to it** opens a session that knows what the run concluded.

## Read these in order

::path{links="concepts/sessions,guides/sessions/open-a-session,guides/sessions/drive-a-session,guides/sessions/review-a-sessions-work"}

## When you need it

::pages{links="guides/sessions/layouts-and-shortcuts,guides/sessions/take-over-and-restore,guides/sessions/watch-a-run,guides/sessions/shell-on-a-machine,guides/sessions/reach-a-port,guides/sessions/build-an-app-behind-a-port-link"}

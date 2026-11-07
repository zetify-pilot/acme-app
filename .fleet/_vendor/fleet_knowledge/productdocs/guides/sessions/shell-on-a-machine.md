---
title: "Open a shell on a machine"
kind: guide
for: [developer, admin]
summary: "Get a shell on one of your Fleet machines itself, as its login user, recorded in your name, without opening a session."
sources:
  - packages/fleet-service/src/fleet_service/api/boxshell.py
  - packages/fleet-service/src/fleet_service/api/static/cockpit-boxshell.js
  - packages/fleet-service/src/fleet_service/api/static/cockpit-palette.js
minutes: 3
---

:::lede
When you are done you will have a :term[box shell]: a terminal on the machine itself, outside any session, for looking at disks, logs or processes.
:::

## What it is, and what it is not

A box shell runs as the machine's login user, in its home directory. It is **not a session**: it takes no place on the machine, works in no repository and runs no agent. For a shell inside a repository's checkout, open a session instead (see [Open a session](guides/sessions/open-a-session)).

## Open one

Any of these opens the same shell:

- **Shell** on a machine's row on the **Workstation** page, or in a machine's own page header.
- **Open a shell on** a machine, in the palette (:kbd[⌘K]).
- :kbd[⌘⇧S] (:kbd[Ctrl Shift S] off a Mac) on the Terminals page, for the focused session's machine.
- The dock's **Terminal** tab, beside a focused session: **Open a shell on** its machine, or **Attach to the open shell** when one is already running. Opened here, the shell starts in the session's folder.

:::steps
- [you] **Open it.** The shell appears in a drawer at the bottom of the page, headed *Shell on* the machine's name.
- [fleet] **It is recorded.** Every open, reattach and close is written down in your name.
- [you] **Work in it.** **Find** searches the screen; **Pop out** moves it to its own window.
- [you] **Hide or close it.** **Hide** puts the drawer away and the shell keeps running; open it again to reattach. **Close shell** ends it on the machine.
:::

:::callout{kind="careful"}
This is a real shell on a shared machine. **Close shell** ends whatever is running in it, and anything you change on the machine affects every session it hosts.
:::

## When it is refused

- **Someone else's shell is open there.** A machine holds one live shell at a time, and a colleague's shell is theirs alone. You are told the machine is busy; you are never handed their prompt.
- **The machine is not reporting**, or its Fleet software is too old for box shells. The message says which.
- **No machine is reporting** at all, so there is nothing to open a shell on.

::cards{links="guides/sessions/review-a-sessions-work, guides/team/machines-and-seats, troubleshooting/machine-drained"}

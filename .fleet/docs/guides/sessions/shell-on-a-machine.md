# Open a shell on a machine

When you are done you will have a box shell: a terminal on the machine itself, outside any session, for looking at disks, logs or processes.

## What it is, and what it is not

A box shell runs as the machine's login user, in its home directory. It is **not a session**: it takes no place on the machine, works in no repository and runs no agent. For a shell inside a repository's checkout, open a session instead (see [Open a session](guides/sessions/open-a-session)).

## Open one

Any of these opens the same shell:

- **Shell** on a machine's row on the **Workstation** page, or in a machine's own page header.
- **Open a shell on** a machine, in the palette (⌘K).
- ⌘⇧S (Ctrl Shift S off a Mac) on the Terminals page, for the focused session's machine.
- The dock's **Terminal** tab, beside a focused session: **Open a shell on** its machine, or **Attach to the open shell** when one is already running. Opened here, the shell starts in the session's folder.

1. [you] **Open it.** The shell appears in a drawer at the bottom of the page, headed *Shell on* the machine's name.
2. [fleet] **It is recorded.** Every open, reattach and close is written down in your name.
3. [you] **Work in it.** **Find** searches the screen; **Pop out** moves it to its own window.
4. [you] **Hide or close it.** **Hide** puts the drawer away and the shell keeps running; open it again to reattach. **Close shell** ends it on the machine.

> **Careful:** This is a real shell on a shared machine. **Close shell** ends whatever is running in it, and anything you change on the machine affects every session it hosts.

## When it is refused

- **Someone else's shell is open there.** A machine holds one live shell at a time, and a colleague's shell is theirs alone. You are told the machine is busy; you are never handed their prompt.
- **The machine is not reporting**, or its Fleet software is too old for box shells. The message says which.
- **No machine is reporting** at all, so there is nothing to open a shell on.

Next: Review what a session did (guides/sessions/review-a-sessions-work) · Run machines and set their seats (guides/team/machines-and-seats) · A machine was drained (troubleshooting/machine-drained)

---
- **box shell**: A terminal on a machine itself, outside any session, for looking at its disks, logs or processes.

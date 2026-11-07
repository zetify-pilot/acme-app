# Open a session

When you are done you will have a live session on one of your team's machines: an agent you can talk to, or a terminal you type into, in a repository's checkout and on a branch of its own.

## Two kinds of session

An **agent session** runs a coding agent and shows its conversation, with a message box under it. A **terminal** is a screen you type into: either a plain login shell, or the agent's own screen in a terminal. Both run on a box that has room, both work on their own branch, and both keep running when you close the browser tab.

## Open one from Terminals

1. [you] **Open the Terminals page.** It is in the sidebar. Press **+ New session** at the top. On an empty page the same button sits in the middle.
2. [you] **Pick the model and the repository.** **Model** lists the models your team set up, and opens on the session default chosen on **Settings › Model config** (see [Choose the models your fleet runs](guides/team/models)). **Repository** offers only repositories a machine has checked out. When you open the form from an issue, the issue's repository is already chosen.
3. [you] **Name a branch, or leave it empty.** Empty starts a new `ws/…` branch from `origin/main`. Type the name of a branch a previous session kept, or one already on GitHub, to carry on with it.
4. [you] **Add what else you need.** **Title** is optional; empty names the session from its first message. **Reasoning** sets how hard the engine thinks (**Default** leaves it on its own level). **Secrets** hands the session credentials from the Secrets page (see [Give a session a secret](guides/secrets/attach-a-secret)). **Initial prompt** is the first message, words or a slash command; empty opens the session waiting for you.
5. [you] **Choose how to open it.** **Open a session** starts the agent session. **Open a plain terminal instead** opens a login shell in the same checkout with no agent attached. **Open the agent in a terminal instead** runs the agent on a terminal screen, the fallback when a machine cannot run it the usual way.
6. [fleet] **A machine takes it.** The line at the foot of the form says how many machines have room. The first one to ask takes the session. If none has room, your request waits for one; it is not lost.

On the Terminals page (#terminals):
1. **+ New session** opens the form.
2. Your new session appears as a tile and starts streaming once a machine has taken it.

[Open Terminals](#terminals)

> **Tip:** Press ⌘ Enter (Ctrl Enter off a Mac) in **Initial prompt** to open the session without reaching for the button. The palette (⌘K) also has **Open a new session**.

## When no machine has a free seat

When every machine's interactive seats are taken, the form says so in a box above the buttons instead of one grey line: how many seats are held and by whom (yours, colleagues', Fleet's own runs, and any stuck on a machine that stopped reporting). The main button then reads **Wait for a seat**; pressing it records your request, and the first seat that frees takes it.

If some of the seats are yours, the box lists your three sessions that have been idle longest, each with **Close it**, which asks the machine to end that session exactly as closing it from the session page does. **Show all** swaps the three for every session of yours that holds a seat, in a scrolling list you can filter by title or machine. **See every machine** unfolds each machine's seats and who holds them. Seats stuck on a machine that stopped reporting cannot be closed from here; ask an admin.

## Open one about an issue

In the **⋯** menu of an issue's, a program's or a slice's page, or in an issue's panel on the Queue, choose **Open a terminal…** and the same form opens, titled with the item's key, with the item written into the first message. Edit it before you start.

## A bare shell from Workstation

The **Workstation** page, linked from the Terminals page, lists your terminals, the ones lost with their machine, and the machines. **Open a bare shell** there opens a shell in the repository's checkout on a machine with room. It is a session like any other and takes a place on that machine. For a shell on the machine itself, outside any checkout, see [Open a shell on a machine](guides/sessions/shell-on-a-machine).

> **Careful:** A session that holds your personal tools (your own MCP servers and their secrets) is **private**: only you can watch it or resume it. A colleague who opens it is told to open their own session instead.

Next: Drive an agent session (guides/sessions/drive-a-session) · Arrange your sessions and use the keyboard (guides/sessions/layouts-and-shortcuts) · Review what a session did (guides/sessions/review-a-sessions-work)

---
- **session**: An agent you talk to, or a terminal you type into, running on one of your team's machines in its own checkout of a repository.

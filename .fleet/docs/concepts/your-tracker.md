# Your tracker and Fleet

Your team keeps working its issues in its own tracker. Fleet reads the issues it may work, decides what happens to them in its own record, and writes each decision back to the tracker. The tracker always shows where the work is.

## Which trackers

An install works with one tracker: **Linear**, **GitHub Issues** or **Jira** (Jira Cloud only). You choose it in **Settings › Set up**. With no tracker chosen, Fleet still runs and writes to no tracker.

How Fleet shows an issue's position depends on the tracker:

- **Linear**: the position is the issue's workflow state.
- **GitHub Issues** and **Jira**: an open issue's position is a label Fleet writes; a finished issue is closed.
- On **Jira**, the status follows the label to the matching To Do, In Progress or Done category. Fleet creates no status, field or workflow in your project.

[Open Set up](#settings:set-up)

## Who writes what

1. [fleet] **Fleet reads.** On a steady tick, Fleet reads the issues it may dispatch into its own copy. It decides against that copy, so taking work never waits on the tracker.
2. [fleet] **Fleet decides.** A claim, a move, a comment: each decision is recorded in Fleet's own database first.
3. [fleet] **Fleet writes back through one outbox.** Every write to the tracker is queued in the same step as the decision behind it, then sent by one worker. A refusal a retry can fix is retried. One only a person can fix is held and shown on the **System** page. A write is never dropped silently.

> **Why:** When several parties wrote the same tracker fields under one name, nobody could tell who moved what. Now Fleet's record decides and the tracker shows the result, so there is one answer to where a piece of work is.

## When someone moves an issue by hand

While Fleet is driving an issue, its own record says where the issue belongs. If someone drags it to another column, Fleet records the move it would undo. Putting the issue back, with a comment saying so, is a setting an operator turns on. A person keeps a short list of moves: close it, park it, take it over to `Human WIP`, hand it back from a hold, or reset it to the queue it came from. See [How work moves](concepts/how-work-moves).

An issue Fleet is not driving is yours to move as you like.

## Labels are Fleet's, whatever the tracker

The labels your team tags work with, such as `Q4` or one label per customer, belong to Fleet. You make, rename and delete them in **Settings › Labels** on every install: Linear, GitHub Issues, Jira or no tracker at all. The label picker on an item offers the same list everywhere.

- On **Linear**, Fleet also copies each change to the team's own labels, through the same outbox as every other write. If Linear refuses or cannot be reached, your change still stands in Fleet, and the held write shows on the **System** page.
- On **GitHub Issues**, **Jira** and with no tracker, the labels stay in Fleet only.

Labels someone makes in Linear, or that already sit on an issue, still show in the list. A label you delete in Fleet stays out of the list, even while the tracker still shows it.

[Open Labels](#settings:labels)

## Sessions never hold a tracker key

An agent session reaches issues only through Fleet's tools: it reads with `get_issue`, files with `file_issue`, moves with `move_issue` and triages with `triage`. It never holds a tracker credential. A dispatched run's key is limited to what its command may do, and Fleet checks every tool call against it.

Next: Connect your tracker, GitHub and a model provider (guides/team/connect-github-and-tracker) · Commands and tools (concepts/commands-and-tools)

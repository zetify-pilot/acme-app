# Watch a run, and stop or retry one

When you are done you will be able to find any run the fleet started, read what its agent is doing or did, and step in when one goes wrong.

A run is Fleet working one issue on one machine, with nobody at the keyboard. You do not drive it the way you drive your own session, but you can watch it, stop it, and talk about it afterwards.

## Find the run

The **Runs** page lists every run, running ones first, grouped by how they ended. **Open Runs** below opens it, and a machine's page on **System › Machines** links to it as **This machine's runs**.

1. [you] **Pick a view.** **All**, **Running** or **Finished**. The bar says how many are in flight.
2. [you] **Narrow it.** Filter by **Machine**, **Outcome** or **Stage**, or type an issue key in **Issue**. An empty list under filters is an answer: they reached every run Fleet holds, not just the ones on screen.
3. [you] **Open the issue.** A row's issue key opens the issue's page; its machine name opens that machine's page.

[Open Runs](#runs)

## Read its conversation

On the issue's page, **Conversation** opens the run's own conversation beside the page. Some pages label it **Open the conversation**, or **Read the conversation** once the run has finished.

- **While it works**, it reads nothing you type. Watch only.
- **When it is waiting on you**, what you type goes back to it as your answer.
- **After it ends**, the conversation is read-only. **Talk to it** opens a new agent session that knows what the run concluded (not everything it saw), so you can ask about it.

## Stop a run

A running row on the Runs page has **Stop…**, and the issue's panel on the Queue has **Stop this run…** to do the same.

1. [you] **Choose where the issue lands.** **Back in its queue** returns it so a later run can try again. **Hold it for a person** takes it off dispatch until someone moves it.
2. [you] **Say why.** The reason is required and recorded under your name.
3. [you] **Press Stop the run.** A message says the run is stopping and that its seat frees on its next progress report.
4. [fleet] **The machine ends it.** At its next progress report the machine kills the session and frees its seat. A stopped run does not count against the issue's attempts.

## Retry an issue that ran out of attempts

When the fleet has stopped trying an issue, its panel on the Queue says which limit it hit and, under **Why the fleet stopped it**, the reason. **Reset & retry** gives it a fresh start. Earlier runs are kept; nothing is deleted.

> **Careful:** Read **Why the fleet stopped it** before you press **Reset & retry**. An issue that keeps failing for the same reason will fail again; fix the cause, or answer what it was asking, first.

Next: A run failed (troubleshooting/run-failed) · Read the Queue (guides/daily/the-queue) · Machines, seats and runs (concepts/machines-seats-runs)

---
title: "Why is this item not moving?"
kind: troubleshooting
for: [everyone]
summary: "An issue sits still. Find out whether it waits on a person, on another issue, on a date or on its attempts, and what moves it."
routes: [issue]
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/tools_issues.py
  - packages/fleet-service/src/fleet_service/api/fleet.py
  - packages/fleet-service/src/fleet_service/api/holds.py
  - packages/fleet-service/src/fleet_service/dispatch/lifecycle_vocab.py
  - packages/fleet-service/src/fleet_service/dispatch/notbefore.py
  - packages/fleet-service/src/fleet_service/dispatch/parkguard.py
  - knowledge/features/fleet-dispatch.md
  - knowledge/features/fleet-human-queues.md
minutes: 6
---

:::lede
An issue that is not moving is almost always waiting for something specific, and Fleet says what. Read the reason on the issue, then do the one thing it asks.
:::

## What you see

| What you see | Likely cause | What to do |
|---|---|---|
| The issue reads **Blocked · decision**, or the Queue row says "A person must decide" | Fleet asked a question only a person may answer | Answer it (below) |
| **Blocked · action**, or "A person must do something" | A step needs your hands, outside Fleet | Do it, then hand it back (below) |
| **Needs answer** | A running session asked you something | Answer the session (below) |
| "Blocked by KEY — title", or the issue reads "Waiting on 1 issue" | Another issue has to finish first | Work on the blocker (below) |
| A "waits until" date, or a **Snoozed.** banner | Someone set it aside until a date | Bring it back or leave it (below) |
| **Failed**, "it has used up its attempts" | It ran out of attempts | [A run failed](troubleshooting/run-failed) |
| **Awaiting merge**, "waiting for its change to be merged" | Its pull request waits for a person to merge | [The PR is not merging](troubleshooting/pr-not-merging) |
| A PRD reads "Paused — an objection is open" | A person objected to its design on the PRD's **Design** tab | Wait for the agent's answer (below) |
| It is in a queue, nothing is blocking it, nothing starts | Nothing is being picked up | [Nothing is being picked up](troubleshooting/fleet-paused) |

## Read the reason first

Every issue has one :term[position], the place it is at in its life. Positions where Fleet stops and waits are called parks. Each park says why in plain words, in three places.

::screen{route="issue" pins="position,actions,blockers"}
1. The position, and under "Waiting on you" what this issue is holding up.
2. The buttons that move it on. Which ones you see depends on why it is waiting.
3. The issues it waits for, if any.

On the [Queue](app:queue), open the **Held back** view to see everything that is not running and not ranked next. Each row carries its reason, such as "waiting for somebody to decide", "another issue has to finish first" or "set aside for now".

::screen{route="queue" pins="views,held"}
1. The views: Everything, Next up, Held back, Running.
2. A held row and its reason. Click it to open the side panel with the buttons.

An agent reads the same thing through the `get_issue` tool: its `parked` field is empty when the issue is not parked, and otherwise names the `reason` (`needs-decision`, `needs-action`, `needs-answer`, `intake-decision`, `failed`, `awaiting-merge` or `parked`), when it started and the question asked. The MCP tools reference lists the rest of its fields, and the Issue positions reference lists every position.

## A person must decide

The issue is at **Blocked · decision** (or **Needs answer**, or **Intake · decision** for a filing). Fleet stopped because the next step is a choice only a person may make, such as whether something is in scope.

:::steps
- [you] **Open the question.** On the issue, or in the Queue's side panel, the card headed "The fleet is asking" shows the question and its options. The [Cockpit](app:cockpit) lists every open question too.
- [you] **Answer it.** Pick an option or write your answer, then press **Answer & send back**. When the answer sends it somewhere specific, the button reads "Answer & send to" and the place.
- [fleet] **It moves on.** Fleet writes your answer into the issue and puts it back in the queue it came from.
:::

:::callout{kind="careful"}
Only a person can move an issue out of **Blocked · decision**. An agent cannot clear it, and a model's judgement never counts as the answer.
:::

## A person must do something

The issue is at **Blocked · action**. The card is headed "Something only a person can do" and says what: merge a pull request by hand, set a secret, run a command on a machine.

:::steps
- [you] **Read what is asked.** The card on the issue and in the Queue's side panel says what to do, often with the exact commands.
- [you] **Do it.** Outside Fleet, where the card says.
- [you] **Hand it back.** Press **Done — hand it back to the fleet**. While an agent is still running on it you see "A fleet agent is still working on this — you can hand it back when it finishes."
- [fleet] **It moves on.** The issue returns to its queue and the next step picks it up.
:::

## Another issue has to finish first

The Queue row reads "Blocked by KEY — title", and the side panel's **Held back** section reads "Waits for KEY to finish first." The issue page says "Waiting on 1 issue" (or N issues), and its **Dependencies** tab lists each one.

:::steps
- [you] **Go to the blocker.** Press **Go to the blocker** in the side panel, or follow its link.
- [you] **See why the blocker waits.** It has its own reason. Start this page again from there.
- [fleet] **It starts by itself.** Once every blocker is done, Fleet stops counting it, and the issue can be picked up. Nobody needs to release it.
:::

If the blocker should not be a blocker at all, remove the link in your tracker.

## It waits for a date

There are two ways to set work aside, and they look different.

- **A "waits until" date.** The issue page and the Queue row show "waits until" and a date. It is not offered before then.
- **Snoozed.** Someone used **Snooze…** in the issue's menu. The banner reads "Snoozed. It comes back on" a date, or "It stays snoozed until you bring it back." The Cockpit keeps a Snoozed list. Press **Bring back now** to return it early. This is Fleet's own hold, not the tracker's **Parked** state.

An issue at **Parked** was set down on purpose ("set aside for now"). Press **Un-park** on the Queue row to bring it back.

## Someone objected to the design

A PRD whose **Design** tab carries an open objection reads "Paused — an objection is open". No implementation starts until an agent answers it, either by revising the approach or by declining with its reason. Bugs and small tasks have no design step, so an objection never holds them.

:::steps
- [fleet] **An agent answers it.** The objection reads "Waiting for the agent" while it works. When the answer lands, the objection reads "Answered", and the PRD moves on.
- [you] **If the answer run did not finish.** The objection reads "The answer run did not finish". Press **Ask again**.
:::

## Nothing is waiting, and it still does not move

If the reason reads "stuck: nothing is driving it" or "it stopped and nobody has picked it back up", or there is no reason and nothing starts, the problem is not with this issue. See [Nothing is being picked up](troubleshooting/fleet-paused).

::cards{links="troubleshooting/run-failed, troubleshooting/pr-not-merging, troubleshooting/fleet-paused, guides/daily/answer-a-question"}

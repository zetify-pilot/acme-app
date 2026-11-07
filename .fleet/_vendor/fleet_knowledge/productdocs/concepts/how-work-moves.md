---
title: "How work moves from filing to merge"
kind: concept
for: [everyone]
summary: "Every issue sits in exactly one position. Some positions hand it to a machine, some wait on a person, and a few end it."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/registers/triage-partition.md
  - packages/fleet-service/src/fleet_service/dispatch/lifecycle_vocab.py
  - packages/fleet-service/src/fleet_service/dispatch/routing.py
  - packages/fleet-service/src/fleet_service/dispatch/authority.py
  - packages/fleet-service/src/fleet_service/api/glossary.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/features/fleet-dispatch.md
  - knowledge/features/fleet-work-tracking.md
minutes: 8
---

:::lede
A piece of work in Fleet is an issue in your tracker. At every moment it sits in exactly one position. The position says who has it: a queue a machine will take it from, a session already working on it, a person, or nobody because it is finished.
:::

## The line, start to end

Work moves through four bands. First someone decides what to build, then it is made buildable, then it is built, then it is closed.

::diagram{name="work-line"}

[The Work Line](concepts/the-work-line) draws every step of it, who has to be there for each one, and what is at each step right now.

A bug or a task skips the planning bands. A task goes straight to the triage check. A bug filed in Fleet is first reproduced; once someone confirms it, it gets a tracker issue, and if a failing test was pushed it goes straight to being fixed, otherwise to the triage check.

## One position, always

An issue's :term[position] is where it is in its lifecycle, and it has exactly one at a time. In Linear it is the issue's workflow state; on GitHub Issues and Jira it is a label Fleet writes, and a finished issue is closed (see [Your tracker and Fleet](concepts/your-tracker)). A feature request that has not become an issue yet has a position too, kept by Fleet alone. Fleet picks up work by the position's name.

Positions fall into four kinds.

| Kind | Positions | What happens there |
|---|---|---|
| **Queues** | `Intake Queue`, `Triage Queue`, `Implement Queue`, `Rework Queue`, `Verify Queue` | A machine takes the issue and runs the command for that step. |
| **Held by a session** | `Triaging`, `Implementing`, `Verifying` | A run is working on it. Nobody else can take it. |
| **Waiting on a person** | `Blocked · decision`, `Blocked · action`, `Needs answer`, `Intake · decision`, `Awaiting merge`, `Failed`, `Human WIP` | Nothing runs until a person acts. |
| **Resting, planning or ended** | `Backlog`, `Parked`, `Needs Design`, `Needs Plan`, `Done`, `Canceled`, `Duplicate` | No machine takes it from here. `Needs Design` and `Needs Plan` hold a PRD between its planning steps. |

The full list, with every move between them, is in the Issue positions reference.

## The common path

:::steps
- [you] **Filed.** A feature request goes to `Intake Queue`, kept by Fleet, where an agent interviews whoever filed it. A task goes to `Triage Queue`. A bug is reproduced first, then goes to `Triage Queue`, or straight to `Implement Queue` when its failing test is already pushed. A bug gets its priority and component when a person confirms the reproduction; anything else gets them at triage.
- [fleet] **Checked.** A machine takes it into `Triaging` and runs the check in a fresh session. The check releases it to `Implement Queue` with a priority, brings it to a person in `Blocked · decision` or `Blocked · action`, or closes it.
- [fleet] **Built.** A machine takes it into `Implementing` and runs the command its type names: a bug is fixed, a task or a PRD is implemented. The run opens a pull request. When its checks are green, the issue moves to `Verify Queue`.
- [fleet] **Verified.** A machine takes it into `Verifying`. A fresh session, which never saw the code being written, proves each claim on the pull request. If they all hold, it merges and the issue moves to `Done`. If one fails, it goes to `Rework Queue` and the build step runs again with what the verifier found.
- [nobody] **Closed.** `Done` is set by the merge, not by a person.
:::

## Where you'll see it

The issue's own page shows its position and what you can do from there.

::screen{route="issue" pins="position,actions,blockers"}
1. The position the issue is in right now.
2. What you can do with it from here.
3. What it waits on, and what waits on it.

The **Queue** page shows the same issues as one list.

::screen{route="queue" pins="views,next,held"}
1. Switch between **Everything**, **Next up**, **Held back** and **Running**.
2. What the fleet ranked and will take next.
3. What it did not rank and nobody needs to act on.

::action[Open the Queue]{route="queue"}

## Who may move an issue

While Fleet is driving an issue, its own record decides where the issue belongs. If someone drags a driven issue to another column in the tracker, Fleet notes the move it would undo; putting it back is a setting a team turns on. A person keeps only a short list of moves:

- **Close it**: to `Done`, `Canceled` or `Duplicate`.
- **Take it over**: to `Human WIP`. Every dispatcher leaves it alone after that.
- **Park it**: to `Parked`.
- **Hand it back or answer a park**: out of a hold and back into a queue.
- **Reset it**: from a session's position back to the queue it was taken from.

:::callout{kind="tip"}
Work that must wait for other work does not need a park. It stays in its queue with a blocker, and the fleet takes it once the blocker closes.
:::

::cards{links="concepts/who-decides-what, concepts/verify-before-merge"}

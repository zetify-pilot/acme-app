---
title: "A run failed"
kind: troubleshooting
for: [everyone]
summary: "An issue reads Failed, or keeps being retried. Read why its runs ended, fix the cause, then Reset & retry."
sources:
  - packages/fleet-service/src/fleet_service/api/resets.py
  - packages/fleet-service/src/fleet_service/api/runstops.py
  - packages/fleet-service/src/fleet_service/api/glossary.py
  - packages/fleet-service/src/fleet_service/dispatch/budget.py
  - packages/fleet-service/src/fleet_service/dispatch/run.py
  - packages/fleet-service/src/fleet_service/dispatch/endwords.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/features/fleet-dispatch.md
minutes: 5
---

:::lede
Fleet tries an issue again on its own, up to a limit. When it reaches that limit it stops at **Failed** and waits for a person, because trying again the same way rarely works and always costs.
:::

## What you see

| What you see | Likely cause | What to do |
|---|---|---|
| A run on the Runs page ended, and the issue is back in its queue | One :term[run] did not succeed; Fleet will try again | Usually nothing. Read why it ended |
| The Queue shows "cooling-off hold", or "waiting a while before it is offered again" | Fleet waits before offering the same issue again | Nothing. It lapses on its own |
| The issue reads **Failed**, and its card says how many attempts it used | Its attempts are used up | Find the cause, then **Reset & retry** |
| **Failed** with "the run ceiling is" or "no word from the engine" | It reached one of the other limits on runs | The same: find the cause, then reset |

## Why a run ended

Every run ends with one reason, shown on its row on the [Runs](app:runs) page and on the issue. They read like "it ran out of wall clock", "the engine died mid-turn", "the provider refused the credential", "the machine stopped reporting" or "somebody stopped it". The reason tells you whether the problem is the work or the machine:

- **About the work** ("it stopped without writing a verdict", "it reported its own verdict"): open the run and read what the agent did.
- **About the machine or provider** ("the engine is not installed on that machine", "the machine's GitHub credential is refused", "the provider refused the credential"): fix the machine first. See [A machine was drained](troubleshooting/machine-drained) and [Nothing is being picked up](troubleshooting/fleet-paused).

::action[Open Runs]{route="runs"}

## Attempts, and why Fleet stops

Only some endings charge one of the issue's :term[attempt]s: a run that failed, did not finish, or was abandoned. A run that never launched, or that a person stopped with **Stop this run…**, charges nothing. Every run, charged or not, still counts toward a separate ceiling on how often one issue may be run at all.

When an issue reaches a limit, Fleet moves it to **Failed** and stops offering it. The card on the issue says which limit it reached, with the numbers that apply to it: attempts used out of the attempts allowed, runs since the last reset against the run ceiling, or runs in a row with "no word from the engine" or that "never started". The fold "Why the fleet stopped it" gives the full reason. The limits themselves are set on your Fleet service.

Between attempts, Fleet may also hold an issue off a machine where it just failed, for a while. That is a cooling-off hold: it applies to one machine and one issue, and lapses on its own. It needs nothing from you.

## Reset & retry

:::steps
- [you] **Find the cause.** Read the reasons of the issue's last runs. If every run ended the same way on the same machine, the machine is the problem, not the issue.
- [you] **Fix it.** Change what made it fail: the issue text, a secret, the machine.
- [you] **Press Reset & retry.** It is on the **Failed** card on the issue page, in the Queue's side panel, and on the Cockpit. Confirm **Reset it**.
- [fleet] **It goes back to work.** Earlier runs stop counting, but are kept; nothing is deleted. The issue moves back to the queue it failed from (**Triage Queue** if no run names one), and a machine can take it again.
:::

::screen{route="issue" pins="position,actions"}
1. **Failed**, with how many attempts were used.
2. **Reset & retry**. Below it: "Earlier runs are kept — nothing is deleted."

:::callout{kind="careful"}
Reset & retry does not raise any limit, and it does not fix anything. If you reset without changing the cause, the issue will spend its attempts the same way again, at the same model cost.
:::

::cards{links="troubleshooting/machine-drained, guides/sessions/watch-a-run, concepts/machines-seats-runs"}

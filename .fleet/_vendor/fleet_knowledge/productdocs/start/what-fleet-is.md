---
title: "What Fleet is"
kind: start
for: [everyone]
summary: "You decide what to build, Fleet builds and checks it, and Fleet asks you when only a person can answer."
sources:
  - README.md
  - ARCHITECTURE.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/registers/triage-partition.md
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/features/fleet-dispatch.md
  - knowledge/features/fleet-verify-and-merge.md
  - knowledge/features/fleet-human-queues.md
minutes: 4
---

:::lede
Fleet is a team of coding agents that works on your repositories. You decide what is worth building. Fleet builds it, has a second agent check it, and merges it. When something needs a person, Fleet stops and asks you.
:::

## Two halves

Fleet is two things that only make sense together.

- **The record.** Your repository's knowledge base: what the product promises, the plan, and the decisions behind it. It is plain markdown in git. Fleet reads it, and every page in the app is drawn from it.
- **The workers.** :term[Machine]s that run agent sessions. A machine asks Fleet for work, runs one session, and reports how it ended. It makes no decisions of its own.

The record says what is true and what was promised. You set the order. The fleet does the work. Checks refuse anything that would make the record wrong. Then the record updates, and the next piece of work becomes ready.

## You decide, Fleet builds, Fleet asks

:::steps
- [you] **You say what you want.** File a feature request, a bug or a task in plain words. You do not pick a kind, a priority or a place. An agent works those out.
- [fleet] **Fleet sorts it.** A fresh agent session reads what you filed, checks it against what the product already promised, and either queues it or brings it back to you.
- [fleet] **Fleet builds it.** An agent on a machine writes the change and opens a pull request.
- [fleet] **A second agent checks it.** A different session, which never saw the code being written, proves each claim before the change merges.
- [you] **Fleet asks when it must.** Only a person can promise something new, answer a question an agent cannot settle, or do something no agent can. Those land in your **Cockpit**.
:::

:::callout{kind="why"}
The agent that wrote a change never approves it. A separate session decides whether it merges, so a change is never certified by the party that made it.
:::

## What Fleet never does on its own

- It never promises new customer-facing functionality. That is always a person's call.
- It never merges a change its own writer approved.
- It never stores a state it can work out. A slice or a program reads complete because its proof shipped, not because someone ticked a box.

## Where you work

Fleet has a web app. Its sidebar leads with the pages you use every day: **Cockpit**, **Features**, **Terminals** and **Queue**. Everything you filed is in the Cockpit too, under **All items**. Your issues stay in your own tracker (Linear, GitHub Issues or Jira), and Fleet keeps it up to date.

::action[Open the Cockpit]{route="cockpit"}

::cards{links="start/your-first-change, start/find-your-way, concepts/how-work-moves"}

---
title: "Take one feature request to a merged change"
kind: start
for: [everyone]
summary: "File a small feature request, answer Fleet's questions, accept its proposal, and watch it become a merged pull request."
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.html
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/registers/triage-partition.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/intake.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/route.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/check.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/verify.md
  - knowledge/features/fleet-filings.md
  - knowledge/features/fleet-verify-and-merge.md
minutes: 8
---

:::lede
When you are done you will have filed one feature request, answered the questions Fleet asked about it, accepted its proposal, and seen it merge as a pull request that a second agent checked. Pick something small for your first time, such as a wording fix or a missing label.
:::

## Before you start

You need a Fleet install with at least one repository and one :term[machine] working. If the Cockpit says **Fleet is not set up yet**, open **Settings › Set up** first.

## Do it

:::steps
- [you] **File the request.** Press **Feature request** at the foot of the sidebar. Write what should exist in plain words under **What should exist, or what happened**. Leave the title blank if you like; Fleet fills it from your words. Pick the repository and press **File it**.
- [fleet] **Fleet interviews you.** An agent reads your request and what your product already promises on that ground. In a repository with features it first asks **Where does this go?**, then what it cannot work out alone. Your request now shows in the Cockpit's **All items** list, and under the **Filed by: Me** filter.
- [you] **Answer the questions.** They wait for you in the **Cockpit**. Answer in a sentence or two, or pick an option. Each answer goes back to the session that asked.
  ::action[Open the Cockpit]{route="cockpit"}
- [fleet] **Fleet proposes where it goes.** When the interview ends, another agent works out what kind of thing your request is and where it lands. It writes a proposal. It creates nothing yet.
- [you] **Accept the proposal.** Open your request from the Cockpit's **Waiting** list. It is waiting on you, with what Fleet proposes and what pressing **Create it** will do. Press **Create it**. If the proposal is wrong, press **Send back to the interview…** and say what to change; or press **Park…** to set it aside.
- [fleet] **A fresh session checks it.** For a small request the proposal is usually a :term[task]. The task goes to the triage check: a new agent session, which never saw your request being filed, confirms the work is real and queues it.
- [fleet] **An agent builds it.** A machine takes the task, writes the change on its own branch, and opens a pull request. It never merges its own work.
- [fleet] **A second agent verifies it.** A different session proves each claim at the pull request's latest commit. If everything holds, it merges. If not, it sends the work back to be fixed, and the loop runs again.
- [nobody] **The issue closes.** The merge moves the issue to `Done`. Nobody sets that by hand.
:::

## Watch it while it runs

You do not have to watch, but you can.

- The **Queue** page shows where your task sits. Its **Running** view lists what a machine is on right now.
- The **Runs** page lists every run, with how it ended.
- The issue's own page shows its :term[position], the state it is in right now.

::action[Open the Queue]{route="queue"}

## If it stops

:::callout{kind="tip"}
If the check decides your request is new customer-facing functionality, it does not queue it. It brings it to you as a call in the **Cockpit**, because only a person may promise something new. Answer it, and the check runs again with your answer.
:::

If Fleet proposes a :term[program], a :term[slice] or a :term[PRD] instead of a task, **Create it** adds the plan to your knowledge base by pull request. Nothing is built yet. The next step is on the new item's page; see [How Fleet plans](concepts/how-fleet-plans).

::cards{links="concepts/how-work-moves, concepts/who-decides-what, guides/daily/after-you-file"}

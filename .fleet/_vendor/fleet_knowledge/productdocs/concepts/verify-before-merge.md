---
title: "Why a second session verifies every change"
kind: concept
for: [everyone]
summary: "The agent that writes a change never approves it. A fresh session proves each claim before the change merges, or sends it back."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/verify.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/prd/verify.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/registers/triage-partition.md
  - packages/fleet-service/src/fleet_service/api/verdicts.py
  - packages/fleet-service/src/fleet_service/mergewaitjob.py
  - packages/fleet-service/src/fleet_service/dispatch/reviewcomments.py
  - packages/fleet-daemon/src/fleet_daemon/mergeguard.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/features/fleet-verify-and-merge.md
minutes: 7
---

:::lede
An agent judged by whether it fixed something is the worst judge of whether its fix is complete. So in Fleet the session that writes a change opens a pull request and stops. A different session, which never saw the code being written, decides whether it merges.
:::

Fleet verify covers only changes Fleet's own implement pipeline made. A pull request from a terminal session or from a person is not verified: its check passes at once, and Fleet files no issue for it.

## Two sessions, two jobs

:::steps
- [fleet] **The builder opens a pull request.** It runs autonomously, opens the pull request, and hands it off. It has no path to its own merge button, however green the checks are.
- [fleet] **The checks run.** The builder's run ends while CI runs, so it does not hold a :term[seat]. When the required checks are green on the commit it pushed, the issue moves to `Verify Queue`. If they go red, the pull request conflicts, or someone pushed over it, the issue goes to `Rework Queue` instead.
- [fleet] **A fresh session verifies.** It rebuilds the list of everything the issue claimed, then proves each claim closed at the pull request's latest commit. It also breaks each test the fix names, to show the test would catch the bug. It never fixes anything itself.
- [fleet] **It merges, or it sends it back.** If every claim holds, it merges and the issue moves to `Done`. If one does not, the issue goes to `Rework Queue` with the open lines, and the builder runs again with them.
:::

A bug, a task or a cleanup is verified by the verify command. A PRD is verified by its own command, which checks each acceptance criterion and drives the product in a browser when the PRD has a screen.

::command{name="verify"}

::command{name="prd:verify"}

:::callout{kind="why" figure="1 in 2"}
merged fixes did not fully address their issue when they were re-checked the same hard way, back when the writer approved its own work. The figure comes from the repository this command was built in, and it is why the second session exists.
:::

## The verdict is a record

A verify run records its verdict through Fleet's tools, with its list of claims and the result of breaking each test. Fleet keeps the verdict as a row that anyone can read back by pull request and commit, and the merge waits on it.

Fleet can also post that verdict as a check on the pull request, named **Fleet verify**. It turns green when the verifier signs off.

## After it is verified

A verified pull request may still wait in your repository's merge queue. Fleet watches it there:

- it moves the issue to `Done` when the pull request merges;
- it sends the issue back to rework if the pull request is thrown out of the queue or conflicts;
- it hands it to a person if someone took it out of the queue;
- it turns auto-merge back on if a verified pull request reads as not armed.

On the machine, the session itself refuses to merge over checks that are not complete and green, and refuses to push over a commit someone else wrote.

## When a person merges

Each repository says who presses merge. Open **Settings › Repositories** and choose a repository.

::screen{route="settings:repositories" pins="repo,merge,verify"}
1. The repository.
2. **Who merges**: **Agents**, **A person**, or **A person, for some paths**.
3. **Fleet verify check**: whether Fleet posts its verdict as a check on each pull request.

When a person merges, the verified issue waits in `Awaiting merge` and shows in your Cockpit. If the repository's **Reviewer comments** setting is **Send to an agent**, comments left on a waiting pull request go back to an agent to address. That includes a plain comment that @-mentions Fleet's GitHub App.

::action[Open Repositories]{route="settings:repositories"}

::cards{links="concepts/how-work-moves, guides/team/repositories, troubleshooting/pr-not-merging"}

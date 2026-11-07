# Take one feature request to a merged change

When you are done you will have filed one feature request, answered the questions Fleet asked about it, accepted its proposal, and seen it merge as a pull request that a second agent checked. Pick something small for your first time, such as a wording fix or a missing label.

## Before you start

You need a Fleet install with at least one repository and one machine working. If the Cockpit says **Fleet is not set up yet**, open **Settings › Set up** first.

## Do it

1. [you] **File the request.** Press **Feature request** at the foot of the sidebar. Write what should exist in plain words under **What should exist, or what happened**. Leave the title blank if you like; Fleet fills it from your words. Pick the repository and press **File it**.
2. [fleet] **Fleet interviews you.** An agent reads your request and what your product already promises on that ground. In a repository with features it first asks **Where does this go?**, then what it cannot work out alone. Your request now shows in the Cockpit's **All items** list, and under the **Filed by: Me** filter.
3. [you] **Answer the questions.** They wait for you in the **Cockpit**. Answer in a sentence or two, or pick an option. Each answer goes back to the session that asked.

   [Open the Cockpit](#cockpit)
4. [fleet] **Fleet proposes where it goes.** When the interview ends, another agent works out what kind of thing your request is and where it lands. It writes a proposal. It creates nothing yet.
5. [you] **Accept the proposal.** Open your request from the Cockpit's **Waiting** list. It is waiting on you, with what Fleet proposes and what pressing **Create it** will do. Press **Create it**. If the proposal is wrong, press **Send back to the interview…** and say what to change; or press **Park…** to set it aside.
6. [fleet] **A fresh session checks it.** For a small request the proposal is usually a task. The task goes to the triage check: a new agent session, which never saw your request being filed, confirms the work is real and queues it.
7. [fleet] **An agent builds it.** A machine takes the task, writes the change on its own branch, and opens a pull request. It never merges its own work.
8. [fleet] **A second agent verifies it.** A different session proves each claim at the pull request's latest commit. If everything holds, it merges. If not, it sends the work back to be fixed, and the loop runs again.
9. [nobody] **The issue closes.** The merge moves the issue to `Done`. Nobody sets that by hand.

## Watch it while it runs

You do not have to watch, but you can.

- The **Queue** page shows where your task sits. Its **Running** view lists what a machine is on right now.
- The **Runs** page lists every run, with how it ended.
- The issue's own page shows its position, the state it is in right now.

[Open the Queue](#queue)

## If it stops

> **Tip:** If the check decides your request is new customer-facing functionality, it does not queue it. It brings it to you as a call in the **Cockpit**, because only a person may promise something new. Answer it, and the check runs again with your answer.

If Fleet proposes a program, a slice or a PRD instead of a task, **Create it** adds the plan to your knowledge base by pull request. Nothing is built yet. The next step is on the new item's page; see [How Fleet plans](concepts/how-fleet-plans).

Next: How work moves from filing to merge (concepts/how-work-moves) · Who decides what (concepts/who-decides-what) · After you file (guides/daily/after-you-file)

---
- **task**: Small, scoped work that needs no design decision and gives nobody anything new to see or use.
- **program**: A larger result that two or more slices add up to and none delivers alone, used only by repositories that plan by programs.
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.

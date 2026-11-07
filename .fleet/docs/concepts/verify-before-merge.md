# Why a second session verifies every change

An agent judged by whether it fixed something is the worst judge of whether its fix is complete. So in Fleet the session that writes a change opens a pull request and stops. A different session, which never saw the code being written, decides whether it merges.

Fleet verify covers only changes Fleet's own implement pipeline made. A pull request from a terminal session or from a person is not verified: its check passes at once, and Fleet files no issue for it.

## Two sessions, two jobs

1. [fleet] **The builder opens a pull request.** It runs autonomously, opens the pull request, and hands it off. It has no path to its own merge button, however green the checks are.
2. [fleet] **The checks run.** The builder's run ends while CI runs, so it does not hold a seat. When the required checks are green on the commit it pushed, the issue moves to `Verify Queue`. If they go red, the pull request conflicts, or someone pushed over it, the issue goes to `Rework Queue` instead.
3. [fleet] **A fresh session verifies.** It rebuilds the list of everything the issue claimed, then proves each claim closed at the pull request's latest commit. It also breaks each test the fix names, to show the test would catch the bug. It never fixes anything itself.
4. [fleet] **It merges, or it sends it back.** If every claim holds, it merges and the issue moves to `Done`. If one does not, the issue goes to `Rework Queue` with the open lines, and the builder runs again with them.

A bug, a task or a cleanup is verified by the verify command. A PRD is verified by its own command, which checks each acceptance criterion and drives the product in a browser when the PRD has a screen.

`verify` — Independently certify a fix before it merges: reconstruct the issue's claims, prove each one closed at the PR head, neuter-test every named test, drive the surface if there is one — then merge on an all-closed ledger, or return it.

`prd:verify` — Evidence-based audit that every PRD acceptance criterion works (browser-verified for UI); flips status to verified on all-PASS or on pass-with-follow-up (every open row non-critical). A PRD already `verified`/`shipped` short-circuits to a bounded ship-only retry or a reported no-op instead of re-auditing — except a `shipped` PRD whose tracker issue never passed through a review position, which is audited rather than no-op'd.

> **Why:** 1 in 2 merged fixes did not fully address their issue when they were re-checked the same hard way, back when the writer approved its own work. The figure comes from the repository this command was built in, and it is why the second session exists.

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

On the Repositories page (#settings:repositories):
1. The repository.
2. **Who merges**: **Agents**, **A person**, or **A person, for some paths**.
3. **Fleet verify check**: whether Fleet posts its verdict as a check on each pull request.

When a person merges, the verified issue waits in `Awaiting merge` and shows in your Cockpit. If the repository's **Reviewer comments** setting is **Send to an agent**, comments left on a waiting pull request go back to an agent to address. That includes a plain comment that @-mentions Fleet's GitHub App.

[Open Repositories](#settings:repositories)

Next: How work moves from filing to merge (concepts/how-work-moves) · Add and configure repositories (guides/team/repositories) · The pull request is not merging (troubleshooting/pr-not-merging)

---
- **seat**: One place on a machine for a session; each seat holds one session at a time.

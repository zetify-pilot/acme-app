---
title: "The pull request is not merging"
kind: troubleshooting
for: [everyone]
summary: "A verified change has a pull request that will not land. What Fleet fixes on its own, and the few cases that need you."
sources:
  - knowledge/features/fleet-verify-and-merge.md
  - packages/fleet-service/src/fleet_service/dispatch/mergewait.py
  - packages/fleet-service/src/fleet_service/dispatch/mainred.py
  - packages/fleet-service/src/fleet_service/dispatch/reviewcomments.py
  - packages/fleet-service/src/fleet_service/dispatch/orphanpr.py
  - packages/fleet-service/src/fleet_service/dispatch/lifecycle_vocab.py
  - packages/fleet-service/src/fleet_service/api/fleet.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-daemon/src/fleet_daemon/mergeguard.py
minutes: 7
---

:::lede
Most pull requests that stall are ones Fleet already noticed: it sends the issue back to an agent with the reason, or waits for the base branch to recover. A few cases need a person. This page says which is which.
:::

## What you see

| What you see | Likely cause | Who acts |
|---|---|---|
| The issue went back to **Rework Queue** | A required check on the PR is red, the PR conflicts with `main`, the merge queue threw it out, or the PR's head is behind its branch | Fleet. An agent fixes it |
| The Queue reads "waiting on main's" check "to recover" | The same check is red on `main` too | Nobody, at first. Fleet waits |
| **Blocked · action** after a merge wait | The PR was taken out of the merge queue by hand, closed, or never entered it | You |
| The issue sits at **Blocked · action** with commands that move files into `.github/workflows/` | A run may not push workflow files, so it left them for you | You run the commands |
| **Awaiting merge**, then back to **Rework Queue** with a quoted comment | A reviewer left a comment on a PR waiting for a person | Fleet. An agent answers it |
| **Awaiting merge**, and it stays there | Your repository is set so a person merges | You merge it |

While Fleet waits for a verified pull request to merge, the issue stays at **Verifying** and the Queue reads "waiting to merge" or "waiting on CI checks". The System page's **Merge waits** section counts every pull request Fleet is waiting on. See the Issue positions reference for every position named here.

## A required check is red

Fleet reads the pull request's checks. When a required one fails because of the change, Fleet moves the issue to **Rework Queue** and writes which checks went red. An agent picks it up, fixes the cause and pushes again; the brief tells it never to loosen a test or skip a check. A check that hung or timed out, while the same check is green on `main`, is run once more before anyone is charged with it.

You do nothing. If it keeps coming back, it will run out of attempts and land at **Failed**: see [A run failed](troubleshooting/run-failed).

## No checks ran at all

A pull request with no checks, not even failing ones, usually conflicts with `main`. GitHub cannot build a merge of it, so CI never starts and auto-merge never fires.

Fleet detects this and sends the issue to **Rework Queue** with "conflicts with `main`, so GitHub cannot compute a merge ref and its CI will never run." The agent rebases or merges `main` into the branch. After repeated conflicts the brief limits the agent to resolving the merge, without touching product code. You act only if resolving it needs a scope decision; the issue then comes to you at **Blocked · decision**.

## It left the merge queue

What Fleet does depends on how it left:

:::steps
- [fleet] **The queue threw it out.** The merge queue's own build went red. Fleet sends the issue to **Rework Queue** with "was REMOVED FROM THE MERGE QUEUE" and the reason. It never re-arms the same unchanged head.
- [fleet] **Someone took it out by hand.** Fleet re-arms auto-merge a few times. If that does not stick, it parks the issue at **Blocked · action**.
- [you] **Re-arm it, or send it back.** The action card says what to run: arm auto-merge again on the PR and move the issue back to **Verifying**, or move it to **Verify Queue** to have it checked again. Then press **Done — hand it back to the fleet**.
:::

A pull request that was closed, or that sat in the queue far too long, also parks at **Blocked · action** with what to do. If a required review is what holds it, the issue goes to **Needs answer** instead.

## The pull request is behind its branch

Sometimes GitHub never tells the pull request about a push: the branch has the new commit, but the PR still shows the older one, every check reads green, and merging would land the wrong code. Fleet compares the two. When they differ, it sends the issue to **Rework Queue**, and the agent pushes a fresh commit so the PR catches up.

A PR waiting at **Awaiting merge** whose head moves goes back to **Verify Queue** instead, because a person clicking merge would land code nobody verified.

## It changes a GitHub workflow

A run may not push files under `.github/workflows/`: its token never carries that permission. So when a PRD build needs a workflow file, it does not open a pull request with it. It writes the whole file to `.fleet-held/workflows/` on its work branch and parks the issue at **Blocked · action**.

:::steps
- [you] **Run the commands on the issue's page.** The page shows one block of commands that moves the held files into `.github/workflows/` and pushes them with your own login.
- [you] **Say it is done.** Pick **I did this — continue** and send your answer.
- [fleet] **It picks up from there.** The run continues with the workflow change in place.
:::

:::callout{kind="careful"}
Do not merge the work branch's pull request before you run the commands: without them it does not contain the workflow change.
:::

## The base branch is red

When every red check on the pull request is also red on `main`, the fault is not in the change. Fleet holds the issue and the Queue reads "waiting on main's" check "to recover", naming the tracking issue when there is one. Nothing is owed by a person, and the PR is not sent back. When `main` is green again, Fleet puts the issue back in its queue.

If `main` stays red long enough, the issue parks at **Blocked · action**: "Restore the base check, then move this issue back to Verify Queue." If even one red check is the PR's own, it goes to rework instead.

## A reviewer left comments

In both merge settings — a pull request waiting for a person, and one armed or in the merge queue — a review thread or a request for changes from someone with write access holds the merge. Fleet turns off an armed auto-merge or takes the pull request out of the queue, sends the issue to **Rework Queue** once per comment, quoting it, and an agent replies on the pull request and resolves the thread. A reopened thread holds the merge again. If the wait says Fleet's GitHub App needs 'Pull requests: write', the App cannot turn the merge off yet: grant that permission on the App and accept the update on the installation (Set up › GitHub shows a permissions panel with what is missing), and the next pass holds it. A formal change request stays outstanding until the reviewer approves or dismisses it.

### Ask Fleet directly: @-mention it

You do not need to open a review to send work back. Write a plain comment on the pull request that @-mentions Fleet's GitHub App (for example `@your-app please rename this`; the name is the App you installed, and capitals and the `[bot]` ending do not matter). If you can write to the repository, Fleet treats that comment like a review comment: it holds the merge, sends the issue to **Rework Queue** once for that comment, and puts 👀 on the comment so you can see it was heard. The agent gets your comment plus the rest of the pull request's conversation as background, and answers with a new comment on the pull request.

A plain comment has no "resolved" state. It counts as answered when the agent pushes and the issue returns to **Review**; write a new comment to ask again. A comment that does not mention Fleet, or comes from someone without write access, changes nothing. The repository's **Reviewers' comments** setting covers this too: **Leave to the merger** turns it off.

You choose this in your repository's settings.

::screen{route="settings:repositories" pins="repo,merge"}
1. The repository.
2. **Merging & review**: "Who merges pull requests" (Agents, A person, or A person, for some paths), and "Reviewers' comments on a pull request on its way to merge" (Send to an agent, or Leave to the merger).

::action[Open Repositories]{route="settings:repositories"}

::cards{links="concepts/verify-before-merge, guides/team/repositories, troubleshooting/why-is-this-stuck"}

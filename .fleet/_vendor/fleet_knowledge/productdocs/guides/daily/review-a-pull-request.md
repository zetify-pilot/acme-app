---
title: "Review a pull request Fleet opened"
kind: guide
for: [developer, owner]
summary: "Hold a Fleet pull request's merge with a review comment or a request for changes, and know how Fleet answers it."
sources:
  - packages/fleet-service/src/fleet_service/dispatch/reviewcomments.py
  - packages/fleet-service/src/fleet_service/mergewaitjob.py
  - packages/fleet-service/src/fleet_service/reconcilegit.py
  - packages/fleet-service/src/fleet_service/api/setup.py
  - knowledge/features/fleet-verify-and-merge.md
minutes: 5
---

:::lede
When you are done, you will know how to send a Fleet pull request back for a change. You will also know how Fleet answers each comment, and how to turn that behaviour off for a repository.
:::

## Ask for a change

You can ask for a change in three ways. All three work while the pull request waits for a person to merge it. They also work while Fleet has armed its merge or put it in the merge queue.

- **Leave a review comment.** Open the pull request's **Files changed** tab and comment on a line, or start a review with several comments.
- **Request changes.** Submit a review with **Request changes**, with or without a written comment.
- **Write a plain comment that @-mentions Fleet.** See [A plain comment that @-mentions Fleet](#a-plain-comment-that-mentions-fleet) below.

## What happens when Fleet hears you

:::steps
- [fleet] **The merge is held.** Fleet turns off an armed auto-merge or takes the pull request out of the merge queue. A pull request waiting for a person keeps waiting.
- [fleet] **The issue goes to Rework Queue.** The brief lists each new comment: who wrote it, where it is, a link, and the text quoted. If you left several comments, one rework covers them all.
- [fleet] **An agent answers each comment.** It replies on the pull request with what changed, or why it did not make the change. Then it resolves any thread and pushes to the same branch.
- [fleet] **The pull request is checked again.** When the checks are green, the issue moves to Verify Queue and a fresh session verifies the change. Only then can the merge go ahead.
:::

:::callout{kind="why"}
Fleet acts on each comment once. A comment it has already answered does not send the work back again. A new comment, or a thread you reopen, does.
:::

## A Request changes review

A review that requests changes stays outstanding until you approve or dismiss it. The agent's reply and its new push do not clear it. The pull request still waits for you after the change is made. It waits until you approve the review or dismiss it.

## A plain comment that @-mentions Fleet

You do not need a review to send work back. Write a comment on the pull request that @-mentions Fleet's GitHub App, for example `@your-app please rename this`. Use the name of the App you installed; capitals and the `[bot]` ending do not matter. If you can write to the repository, Fleet treats the comment like a review comment. It holds the merge and sends the issue to Rework Queue once for that comment. It also puts 👀 on the comment so you can see it was heard.

A plain comment has no "resolved" state. It counts as answered when the agent pushes and the issue leaves Rework Queue. A comment that does not mention Fleet changes nothing. To ask again after the agent has answered, write a new comment.

## Who counts

Fleet reads comments only from people who can write to the repository: GitHub roles **admin**, **maintain** or **write**. A comment from someone without write access changes nothing. Fleet never counts a bot's comment or its own comments.

## Turn it off for a repository

On **Settings › Repositories**, open the repository's **Settings**, then **Merging & review**. **Reviewers' comments on a pull request on its way to merge** has two choices:

- **Send to an agent** (the default): Fleet reads the comments and holds the merge.
- **Leave to the merger**: Fleet does not read them. The pull request waits for its person, or merges, as before.

::screen{route="settings:repositories" pins="repo,merge"}
1. The repository.
2. **Merging & review**, where the **Reviewers' comments** setting is.

::action[Open Repositories]{route="settings:repositories"}

## When each part arrived

| What you can do | Release |
|---|---|
| A review comment or a Request changes review holds a pull request waiting for a person. The issue goes to Rework Queue | 0.7.416 |
| The same comments hold a pull request Fleet armed or put in the merge queue | 0.7.556 |
| A plain comment that @-mentions Fleet sends the work back, and Fleet puts 👀 on it | 0.7.635 |

::cards{links="concepts/verify-before-merge,guides/team/repositories,troubleshooting/pr-not-merging"}

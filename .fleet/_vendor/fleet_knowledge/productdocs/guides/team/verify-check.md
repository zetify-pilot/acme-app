---
title: "Set up the Fleet verify check in your repository"
kind: guide
for: [admin, owner]
summary: "Add a repository, switch on the Fleet verify check, make it required, and see it on a test pull request."
sources:
  - packages/fleet-service/src/fleet_service/api/repositories.py
  - packages/fleet-service/src/fleet_service/api/setup.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/dispatch/verifycheck.py
minutes: 5
---

:::lede
When you finish, a pull request in your repository shows a check named **Fleet verify**, and GitHub will not merge a change Fleet's own pipeline made until that check passes.
:::

The check is Fleet's verdict on a pull request, posted through your own GitHub App. Nothing is added to your repository for it, and you need no CI runner. This guide sets it up from the start. [Read a verify verdict](guides/quality/verdicts) explains what each state means, and [Why a second session verifies every change](concepts/verify-before-merge) explains why the check exists.

## Before you start

- Your GitHub App is installed on the repository. Fleet reaches a repository only through that App, so connect it first: [Connect your tracker, GitHub and a model provider](guides/team/connect-github-and-tracker).
- You can change the repository's settings on GitHub. The check is made required by a ruleset on its default branch.
- The repository is a **Fleet project** or **Work here, no Fleet files**. A **Reference only** repository gets no check, because Fleet does no work there.

## 1. Add the repository

:::steps
- [you] **Open Settings › Repositories.** Click **Add a repository**.
- [you] **Name it as GitHub spells it.** Under **Repository**, type the name, for example `acme/payments`.
- [you] **Choose how Fleet uses it.** Under **How Fleet uses it**, pick **Fleet project** or **Work here, no Fleet files**.
- [you] **Click Add repository.** If Fleet cannot reach it, the form says the App is not installed there and links to GitHub to install it.
- [you] **Merge the setup pull request** if Fleet opens one. A new Fleet project gets a pull request with Fleet's files; read it and merge it yourself.
:::

## 2. Switch on the check

:::steps
- [you] **Open the repository's Settings.** On its card, click **Settings**.
- [you] **Open the Merging & review tab.**
- [you] **Turn on Post the check on pull requests.** The row above it, **Fleet verify check**, says what the check does.
- [you] **Click Save.**
:::

A new repository has the check on already. Turn it on here if someone switched it off.

## 3. Make the check required

Fleet requires **Fleet verify** on every repository it works in: it creates a ruleset on the default branch, so GitHub itself refuses a merge that has no verdict. If Fleet has not done it yet, you can do it at once.

:::steps
- [you] **Open Settings › Set up and the step Add a repository.**
- [you] **Click Make Fleet verify required** beside the repository, if the step offers it, and confirm the box.
- [you] **Say that GitHub requires it.** On **Settings › Repositories**, open the card's **Settings**, then **Merging & review**, and set **Is the check required by the repository?** to **Yes, a ruleset requires it**. Click **Save**.
:::

Answer **Yes, a ruleset requires it** only when the ruleset really is on GitHub. The answer tells Fleet what GitHub already enforces, so Fleet can turn on auto-merge as soon as a bug's or task's pull request opens.

:::callout{kind="careful"}
If you switch the ruleset off on GitHub, set the answer back to **No**. Otherwise Fleet turns on auto-merge for a check GitHub no longer waits for.
:::

## 4. See it on a test pull request

:::steps
- [you] **Open a pull request** from a branch with one small change, or file a task and let Fleet open one.
- [you] **Find Fleet verify in its checks.** It is called **Fleet verify** unless your installation renamed it.
- [fleet] **Read its state.** A pull request Fleet's pipeline did not make, such as one from a person or from a terminal session, reads **Not a Fleet pipeline change: no verification needed** and passes on the first pass. A pull request one of Fleet's implementing runs opened reads **Waiting for independent verification** until a fresh session, the verifier, signs off; then it reads **Verified by an independent agent** and passes.
:::

If the check does not appear, check that **Post the check on pull requests** is on, that the App is installed on this repository, and that the pull request is in the repository itself and not a fork. Fleet posts the check shortly after a pull request opens.

Fleet verify covers only the changes Fleet's own pipeline made. A pull request opened from a terminal session passes at once, even though it is pushed through the same GitHub App, and Fleet files no issue for it. The check changes nothing in your repository and needs no CI runner. [Read a verify verdict](guides/quality/verdicts) explains every state it can show and what each one does to the issue. [Why a second session verifies every change](concepts/verify-before-merge) explains why Fleet waits for the verdict before a merge.

::action[Open Repositories]{route="settings:repositories"}

::cards{links="guides/quality/verdicts, concepts/verify-before-merge, guides/team/repositories"}

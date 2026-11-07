---
title: "Read a verify verdict"
kind: guide
for: [owner, developer]
summary: "What the Fleet verify check on a pull request says, what each verdict does to the issue, and what to do when one is sent back."
sources:
  - packages/fleet-service/src/fleet_service/api/verdicts.py
  - packages/fleet-service/src/fleet_service/dispatch/verdicts.py
  - packages/fleet-service/src/fleet_service/dispatch/verifycheck.py
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/verify.md
minutes: 5
---

:::lede
When you are done you will be able to read the verify check on any pull request Fleet opened, know what its verdict did to the issue, and know whether anything is waiting on you.
:::

## Where the verdict comes from

The session that wrote a change never certifies it. When an implementing run opens a pull request, the issue moves to **Verify Queue**, and a fresh session, the :term[verifier], picks it up. It rebuilds a :term[ledger] from the issue, one line per thing the fix has to make true, proves each line at the pull request's head commit, and records one verdict.

::command{name="verify"}

## The check on the pull request

Fleet publishes a check on the pull requests in the repositories it works in. It is called **Fleet verify** unless your installation renamed it. What it says:

| The check reads | What it means |
|---|---|
| **Waiting for independent verification** | A change Fleet's implementing pipeline made; no verdict yet. |
| **Waiting on a person** | No verifier can start because the issue is parked on someone. The summary says what is needed. |
| **Verified by an independent agent** | The verifier closed every ledger line. Passes. |
| **Sent back by the verifier** | At least one line is still open. Fails, with the verifier's reason. |
| **Not a Fleet pipeline change** | Fleet's pipeline did not make this pull request: a person or a terminal session opened it. Passes on the first pass, with "no verification needed". |
| **Set up: nothing to verify** | Fleet's own set-up pull request. Passes. |
| **Not verifier-gated** | A pull request its own run merges (shaping, create, design or plan), or a knowledge-only citation. Certifies nothing and does not wait. |
| **Superseded by a newer commit** · **Merged without a recorded verdict** · **Pull request closed unverified** | The commit left its pull request before any verdict was recorded. |

:::callout{kind="tip"}
Fleet verify covers only changes Fleet's own pipeline made. Pull requests from terminal sessions and from people pass at once; Fleet files no issue for them and sends them to no verify queue. When the repository requires the check, nothing Fleet's pipeline wrote merges without a verdict. Whether it is required is set per repository; see [Set up the Fleet verify check in your repository](guides/team/verify-check).
:::

## What each verdict does

:::steps
- [fleet] **verified.** Every ledger line is closed. The verifier merges the pull request and the issue closes.
- [fleet] **merged.** The change merged while the verifier was still running. It counts as landed, not as a failure.
- [fleet] **incomplete.** A line is still open. The check turns red, and the issue goes to **Rework Queue** carrying the open lines, so the next implementing run starts from exactly what was missing.
- [you] **blocked.** The verifier could not evaluate the change: no pull request, red CI, a conflict, or a half of a coupled change that has not merged. The issue is parked for a person, and the check keeps waiting.
:::

:::callout{kind="careful"}
A fix that is sent back twice is not sent back a third time. The verifier parks it in **Blocked · decision** with the open lines, for a person to decide what the fix should be.
:::

## When a verdict is waiting on you

A verdict that needs you shows up as an issue in **Blocked · decision** or **Blocked · action**, in your Cockpit. Read the open ledger lines in the issue, answer, and the issue moves on; the check on the pull request goes back to waiting for the verifier.

::action[Open your Cockpit]{route="cockpit"}

::cards{links="concepts/verify-before-merge, troubleshooting/pr-not-merging, guides/daily/answer-a-question"}

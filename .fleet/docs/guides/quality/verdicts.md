# Read a verify verdict

When you are done you will be able to read the verify check on any pull request Fleet opened, know what its verdict did to the issue, and know whether anything is waiting on you.

## Where the verdict comes from

The session that wrote a change never certifies it. When an implementing run opens a pull request, the issue moves to **Verify Queue**, and a fresh session, the verifier, picks it up. It rebuilds a ledger from the issue, one line per thing the fix has to make true, proves each line at the pull request's head commit, and records one verdict.

`verify` — Independently certify a fix before it merges: reconstruct the issue's claims, prove each one closed at the PR head, neuter-test every named test, drive the surface if there is one — then merge on an all-closed ledger, or return it.

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

> **Tip:** Fleet verify covers only changes Fleet's own pipeline made. Pull requests from terminal sessions and from people pass at once; Fleet files no issue for them and sends them to no verify queue. When the repository requires the check, nothing Fleet's pipeline wrote merges without a verdict. Whether it is required is set per repository; see [Set up the Fleet verify check in your repository](guides/team/verify-check).

## What each verdict does

1. [fleet] **verified.** Every ledger line is closed. The verifier merges the pull request and the issue closes.
2. [fleet] **merged.** The change merged while the verifier was still running. It counts as landed, not as a failure.
3. [fleet] **incomplete.** A line is still open. The check turns red, and the issue goes to **Rework Queue** carrying the open lines, so the next implementing run starts from exactly what was missing.
4. [you] **blocked.** The verifier could not evaluate the change: no pull request, red CI, a conflict, or a half of a coupled change that has not merged. The issue is parked for a person, and the check keeps waiting.

> **Careful:** A fix that is sent back twice is not sent back a third time. The verifier parks it in **Blocked · decision** with the open lines, for a person to decide what the fix should be.

## When a verdict is waiting on you

A verdict that needs you shows up as an issue in **Blocked · decision** or **Blocked · action**, in your Cockpit. Read the open ledger lines in the issue, answer, and the issue moves on; the check on the pull request goes back to waiting for the verifier.

[Open your Cockpit](#cockpit)

Next: Why a second session verifies every change (concepts/verify-before-merge) · The pull request is not merging (troubleshooting/pr-not-merging) · Answer a question (guides/daily/answer-a-question)

---
- **verifier**: A fresh session that never wrote the work and checks it from the evidence before it counts, such as a fix before it merges.
- **ledger**: The verifier's list of what a fix has to make true, one line per claim, each proved or left open at the pull request's head.

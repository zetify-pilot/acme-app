# How Fleet knows what has been checked

A product makes promises: rules it must keep, things a user can do, steps a journey must pass. Fleet checks those promises against the live product, writes each result into your repository, and shows on one page which promises are proven, which are failing, and which nothing checks yet.

## Promise, check, result

1. [nobody] **The promises come from your knowledge base.** A promise is anything your product committed to that a check can prove: a rule in a requirement register, a shipped capability, or a journey's acceptance criterion. Nobody keeps a separate list.
2. [fleet] **The QA agent checks them.** It writes a scenario that walks the product, runs it on a named environment, and records a result with evidence. Each failing expectation is filed as an issue.
3. [fleet] **A second session re-grades.** A verifier that never ran the check re-reads a sample of passes, and every pass that follows a fail, from the recorded evidence alone. It can dispute a verdict.
4. [nobody] **The desk works out each promise's state.** It reads the results from the repository. Nobody marks a promise by hand.

> **Why:** A check that ran only against the code, or did not finish, is never shown as green. A promise is green only when a check passed it against the live product, with evidence, inside its window, and the verifier did not dispute it.

The QA agent and its verifier are commands like any other:

`qa` — Check one shipped promise on a named environment: write or rerun its scenario, drive the product, record a v2 result with platform evidence, file each failing assertion, and land scenario plus result by one PR.

`qa:verify` — Re-grade a sample of the QA agent's passes and every pass that follows a fail, from the recorded evidence alone, in a session that never ran the check; approve or reject changed expected results; run the weekly planted-bug check on the local environment; write each finding as an append-only record and file a ticket for every dispute.

## The Quality desk

The **Quality desk** opens from the **Knowledge** page, with **Open the Quality desk →**. It has three tabs: **Promises**, **Scenarios** and **Environments**. Promises is the default. Its first screen is one line per feature area, worst first in each tier, saying in words how many of its promises are failing, not checked yet and passing. Open a line to see that feature's promises; a promise in no feature sits last under **Not in a feature**.

On the Quality page (#quality):
1. One line per feature area, with its promises counted in words.
2. A newer result waiting in an open pull request, under its promise.
3. Ask the QA agent to cover a promise nothing checks yet.

[Open the Quality desk](#quality)

## When checks run

The QA agent runs nightly when your repository's `fleet.toml` turns it on. How many issues Fleet may file in one night is a limit an operator sets on **System › Recurring work**. When a check you asked for from the desk cannot be filed tonight, because the limit is full or not set, the desk says it is held and until when.

Next: Read the Quality desk (guides/quality/quality-desk) · Ask the QA agent to check a promise (guides/quality/ask-for-a-check) · Read a verify verdict (guides/quality/verdicts)

---
- **promise**: Anything the product committed to that a check can prove: a requirement, a shipped capability or a journey's acceptance criterion.
- **scenario**: A check the QA agent writes that walks several parts of the product together, each expected result proving one promise.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.

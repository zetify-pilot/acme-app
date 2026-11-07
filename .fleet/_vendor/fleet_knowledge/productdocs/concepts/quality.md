---
title: "How Fleet knows what has been checked"
kind: concept
for: [owner, developer]
summary: "Every promise your product makes is checked against the live product, the result is written into the repository, and a second session re-grades the checks."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/templates/quality.js
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/qa.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/qa/verify.md
  - packages/fleet-knowledge/src/fleet_knowledge/checks/recurring/__init__.py
  - packages/fleet-service/src/fleet_service/api/quality.py
  - knowledge/features/fleet-quality-desk.md
  - knowledge/features/fleet-qa-automation.md
minutes: 6
---

:::lede
A product makes promises: rules it must keep, things a user can do, steps a journey must pass. Fleet checks those promises against the live product, writes each result into your repository, and shows on one page which promises are proven, which are failing, and which nothing checks yet.
:::

## Promise, check, result

:::steps
- [nobody] **The promises come from your knowledge base.** A :term[promise] is anything your product committed to that a check can prove: a rule in a requirement register, a shipped capability, or a journey's acceptance criterion. Nobody keeps a separate list.
- [fleet] **The QA agent checks them.** It writes a :term[scenario] that walks the product, runs it on a named environment, and records a result with evidence. Each failing expectation is filed as an issue.
- [fleet] **A second session re-grades.** A verifier that never ran the check re-reads a sample of passes, and every pass that follows a fail, from the recorded evidence alone. It can dispute a verdict.
- [nobody] **The desk works out each promise's state.** It reads the results from the repository. Nobody marks a promise by hand.
:::

:::callout{kind="why"}
A check that ran only against the code, or did not finish, is never shown as green. A promise is green only when a check passed it against the live product, with evidence, inside its window, and the verifier did not dispute it.
:::

The QA agent and its verifier are commands like any other:

::command{name="qa"}

::command{name="qa:verify"}

## The Quality desk

The **Quality desk** opens from the **Knowledge** page, with **Open the Quality desk →**. It has three tabs: **Promises**, **Scenarios** and **Environments**. Promises is the default. Its first screen is one line per :term[feature area], worst first in each tier, saying in words how many of its promises are failing, not checked yet and passing. Open a line to see that feature's promises; a promise in no feature sits last under **Not in a feature**.

::screen{route="quality" pins="line,waiting,ask"}
1. One line per feature area, with its promises counted in words.
2. A newer result waiting in an open pull request, under its promise.
3. Ask the QA agent to cover a promise nothing checks yet.

::action[Open the Quality desk]{route="quality"}

## When checks run

The QA agent runs nightly when your repository's `fleet.toml` turns it on. How many issues Fleet may file in one night is a limit an operator sets on **System › Recurring work**. When a check you asked for from the desk cannot be filed tonight, because the limit is full or not set, the desk says it is held and until when.

::cards{links="guides/quality/quality-desk, guides/quality/ask-for-a-check, guides/quality/verdicts"}

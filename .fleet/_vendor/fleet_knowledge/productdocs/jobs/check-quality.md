---
title: "Check quality"
kind: job
icon: quality
group: run
for: [owner, developer]
summary: "See which promises a live check has proven, ask for a check, and read the verdict on a pull request."
minutes: 3
---

:::lede
Fleet keeps a record of every check: which promises were proven, how recently, and what failed. This path shows you how to read that record, ask for a check where there is none, and read the verdict on a pull request.
:::

## The big picture

:::ideas
- **Promise.** Anything your product committed to that a check can prove: a requirement, a shipped capability, or a journey's criterion. It comes from your knowledge base.
- **Quality desk.** One line per feature area saying in words what is failing, not checked yet or passing; open a line for its promises.
- **Fleet verify check.** The verdict of the session that verified one pull request, posted on that pull request.
:::

Fleet checks in two places, and they answer different questions. Before a change merges, a :term[verifier] proves each claim that one change made. Its verdict is a record, and it can show on the pull request as the **Fleet verify check**. After changes merge, the QA agent checks the running product against your :term[promise]s. It writes each result into your repository, and a second session re-grades a sample of them from the evidence alone.

The Quality desk reads those results and works out each promise's state. Nobody marks a promise by hand. A promise is green only when a check passed it against the live product, with evidence, recently enough, and nobody disputed it. A promise nothing checks yet says so, and you can ask the QA agent to cover it.

## Read these in order

::path{links="concepts/quality,guides/quality/quality-desk,guides/quality/ask-for-a-check,guides/quality/verdicts"}

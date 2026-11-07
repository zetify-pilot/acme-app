# Check quality

Fleet keeps a record of every check: which promises were proven, how recently, and what failed. This path shows you how to read that record, ask for a check where there is none, and read the verdict on a pull request.

## The big picture

- **Promise.** Anything your product committed to that a check can prove: a requirement, a shipped capability, or a journey's criterion. It comes from your knowledge base.
- **Quality desk.** One line per feature area saying in words what is failing, not checked yet or passing; open a line for its promises.
- **Fleet verify check.** The verdict of the session that verified one pull request, posted on that pull request.

Fleet checks in two places, and they answer different questions. Before a change merges, a verifier proves each claim that one change made. Its verdict is a record, and it can show on the pull request as the **Fleet verify check**. After changes merge, the QA agent checks the running product against your promises. It writes each result into your repository, and a second session re-grades a sample of them from the evidence alone.

The Quality desk reads those results and works out each promise's state. Nobody marks a promise by hand. A promise is green only when a check passed it against the live product, with evidence, recently enough, and nobody disputed it. A promise nothing checks yet says so, and you can ask the QA agent to cover it.

## Read these in order

1. **How Fleet knows what has been checked** (concepts/quality): Every promise your product makes is checked against the live product, the result is written into the repository, and a second session re-grades the checks.
2. **Read the Quality desk** (guides/quality/quality-desk): See which of your product's promises a live check has proven, which are failing, and which nothing checks yet.
3. **Ask the QA agent to check a promise** (guides/quality/ask-for-a-check): Pick a promise nothing checks yet and have Fleet file one check for it, counted against tonight's limit.
4. **Read a verify verdict** (guides/quality/verdicts): What the Fleet verify check on a pull request says, what each verdict does to the issue, and what to do when one is sent back.

---
- **verifier**: A fresh session that never wrote the work and checks it from the evidence before it counts, such as a fix before it merges.
- **promise**: Anything the product committed to that a check can prove: a requirement, a shipped capability or a journey's acceptance criterion.

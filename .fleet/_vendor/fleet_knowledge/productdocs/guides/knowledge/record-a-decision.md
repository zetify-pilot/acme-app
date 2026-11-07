---
title: "Record a decision so it outlives the conversation"
kind: guide
for: [owner, developer]
summary: "Your answers to Fleet's questions are kept on the issue for you; a decision the whole product should follow goes in a dated decision record."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/process/decision-write-back.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/process/decision-document.md
  - packages/fleet-knowledge/src/fleet_knowledge/knowledge.py
  - packages/fleet-knowledge/src/fleet_knowledge/checks/commitments/coverage.py
  - packages/fleet-service/src/fleet_service/api/decisions.py
  - packages/fleet-service/src/fleet_service/api/static/team-item.js
  - knowledge/slots/decisions.md
minutes: 6
---

:::lede
When you are done, a choice you made can be found by the next person or agent who touches the work: on the issue it was about, or, for a choice the whole product should follow, as a dated record in your knowledge base that says what was chosen, what was refused, and why.
:::

## Two kinds of decision

| | A decision about one piece of work | A decision the product should keep |
|---|---|---|
| Example | "Use the existing export format for this report." | "We never store a customer's password, even encrypted." |
| Where it lives | On the issue | In `knowledge/decisions/`, or wherever your repository's `decisions` slot points |
| Who writes it | Fleet, from your answer | You, in a pull request |
| Who reads it | Whoever picks up that issue | Every later change that touches the same ground |

## A decision about one piece of work

You rarely write this one yourself. When an agent stops on a question it is not entitled to settle, you answer it in Fleet, and Fleet writes your answer into the issue's description under a dated `## Decision (<date>)` heading. The agent that picks the issue up reads the description, not the comments.

:::steps
- [you] **Answer the question.** Pick an option, or type your own answer.
- [fleet] **Fleet writes it down.** Your answer goes into the issue's description, dated, and the issue moves on.
- [you] **Read it back any time.** Open the issue and its **Decision log** tab: every question Fleet asked there, every option, which one was recommended, and what was picked.
:::

:::callout{kind="careful"}
If you edit an issue's description by hand, never write a `## Decision (…)` heading yourself and never put anything but the date inside its brackets. Fleet treats that heading as a person's answer, and an agent's own notes go under `## Implementation notes (<date>)` instead.
:::

## A decision the product should keep

Write one when a later change could quietly undo your choice: you picked one option over another for a reason the code will not show.

:::steps
- [you] **Create a dated file.** One file per choice, named `YYYY-MM-DD-<short-name>.md`, in the folder your `decisions` slot names.
- [you] **Head it.** Front matter with `type: decision`, a `title`, a `status` (`proposed`, `accepted` or `superseded`), an `owner` saying who decided and when, and `supersedes` naming the record it replaces, if any.
- [you] **Write four short parts.** **Context.** what forced the choice. **Decision.** what you chose. **Why.** the reason. **Consequences.** what you accept by choosing it. Name each option you refused and why, in a line each.
- [you] **Put each rule in a register.** If the decision means the product shall or shall never do something, add it as a numbered :term[requirement] row in the register it belongs to, and name that row in the record's **Commitments.** line. The record explains; the row is what work cites.
- [you] **Merge it.** Open a pull request as usual.
- [fleet] **It shows on the Knowledge page.** The record appears under **Decisions**, linked to the rows it names.
:::

:::callout{kind="tip"}
Never delete or rewrite an old record when you change your mind. Write a new one that `supersedes` it, and set the old one's status to `superseded`. The history of why is the point.
:::

Some repositories also check that every decision record is claimed by a requirement register. If `fleet check` names your new record as unclaimed, add its path to that register's `source_of_truth:`.

::action[Open Knowledge]{route="knowledge"}

::cards{links="knowledge-base/decisions, knowledge-base/promises, guides/daily/answer-a-question"}

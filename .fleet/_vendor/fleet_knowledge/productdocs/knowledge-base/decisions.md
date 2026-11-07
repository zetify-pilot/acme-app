---
title: "Decisions"
kind: concept
for: [everyone]
summary: "A decision record keeps a choice someone made, the option they turned down and why, so a later change cannot quietly reverse it."
sources:
  - knowledge/slots/decisions.md
  - knowledge/decisions/2026-10-27-planning-without-programs.md
  - knowledge/FILE-TYPES.md
  - knowledge/scripts/gen_decision_ledger.py
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/process/decision-write-back.md
minutes: 5
---

:::lede
Months from now someone will look at a choice and think it was a mistake. A decision record tells them what was chosen, what was turned down, and why, so they change it on purpose or not at all.
:::

## What a decision is

A :term[decision] is a fork someone took: the option chosen, the option refused, and the reason. If you cannot name the option that was turned down, it is a fact, not a decision.

Decisions start when people make them. Describing an existing code base never invents past decisions.

## Where it lives

Each decision is one dated file in `knowledge/decisions/`, named by the date and a short slug, for example `knowledge/decisions/2026-10-27-planning-without-programs.md`. Its front matter says `type: decision`, its `title:`, its `status:` (proposed, accepted or superseded) and its `owner:`, who decided and when.

The body usually covers four things, in plain words. Your repository's `decisions` slot names the exact headings it uses.

- **Context.** What was going on, and what forced a choice.
- **Decision.** What was chosen, in the words of the person who chose it.
- **Why.** The reasons, including the options that were turned down and why.
- **Consequences.** What the team accepts by choosing this, and what changes because of it.

A decision about how one PRD is built lives in that PRD's `design.md` instead, beside the design it shaped.

## Decisions and requirements

A decision explains; a [requirement](knowledge-base/promises) binds. When a decision commits the product to something, such as "every slice names a feature area", that commitment becomes a numbered requirement row, and the decision cites its id. The decision says why; the row is what PRDs implement and the Quality desk checks.

:::callout{kind="tip"}
You do not keep a list of decisions by hand. An index of every decision record, and every PRD design that recorded one, is generated on demand. See [Generated tables](knowledge-base/generated-tables).
:::

## Not the same as answering a question in Fleet

When an agent stops and asks you to choose, your answer is written into that issue's description, dated, so whoever picks the work up next reads it. That settles one piece of work. A decision record is for a choice the whole product lives with. If an answer you gave turns out to be that kind of choice, write a record too. See [Record a decision](guides/knowledge/record-a-decision).

## Where you see them

The Knowledge page lists every decision record, linked to what it shaped.

::action[Open Knowledge]{route="knowledge"}

::cards{links="knowledge-base/promises, guides/knowledge/record-a-decision, guides/daily/answer-a-question"}

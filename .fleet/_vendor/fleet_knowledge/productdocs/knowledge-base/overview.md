---
title: "The knowledge base"
kind: concept
for: [everyone]
summary: "The knowledge folder each repository keeps: what the product does, what it promised, and what is changing. Fleet plans and checks against it."
routes: [knowledge]
sources:
  - knowledge/FILE-TYPES.md
  - packages/fleet-knowledge/src/fleet_knowledge/knowledge.py
  - packages/fleet-knowledge/src/fleet_knowledge/scaffold.py
  - packages/fleet-knowledge/src/fleet_knowledge/templates/board.js
minutes: 5
---

:::lede
Every repository Fleet works in keeps a `knowledge/` folder beside its code. It says what the product lets people do, what it has promised, and what is being changed right now. Agents read it before they build, the board is drawn from it, and the Quality desk checks the running product against it.
:::

## What it answers

A :term[knowledge base] is a set of plain files that answer four questions. Each answer has a name, and each name has its own page in this section.

| The question | What answers it |
|---|---|
| What can someone do with the product? | [Feature areas](knowledge-base/feature-areas), [capabilities](knowledge-base/capabilities-and-components) and [journeys](knowledge-base/journeys) |
| What did we promise, refuse or decide? | [Requirements](knowledge-base/promises) and [decisions](knowledge-base/decisions) |
| What is being changed, and when is it done? | [Slices](knowledge-base/slices), [PRDs](knowledge-base/prds) and, in some repositories, [programs](knowledge-base/programs) |
| How is work done in this repository? | [Slots](knowledge-base/slots): the answers each Fleet command needs about your build, tests and branches |

## Why it is files in your repository

- **It is reviewed like code.** Every change to it arrives as a pull request, so a promise or a plan changes the same way the product does: on a branch, checked, and merged.
- **Agents can read it on a fresh checkout.** An agent session starts from the repository and nothing else. What it needs to know has to be in the repository.
- **Fleet reads it from your main branch.** The Programs, Features and Knowledge pages are a reading of these files at one commit, and every live card in these docs says which commit it was read from.

## Two kinds of thing live in it

Some things never finish. A :term[feature area], a :term[capability], a :term[component], a :term[journey], a :term[requirement] and a :term[decision] are true for as long as the product is. They carry no status, because there is nothing to finish.

Other things are work, and work finishes. A :term[slice] finishes when every PRD in it has shipped or been cancelled, at least one has shipped, and the proof it names has shipped; its Done when sentence says what that proof shows. A :term[PRD] finishes when it ships. In a repository that plans by programs, a :term[program] finishes when its slices are complete or waived and its own proof has shipped.

:::callout{kind="why"}
Only a PRD's status is ever written, and Fleet's commands write it. A slice or a program reads complete when its parts are done, worked out by Fleet from the files. A state that has to be remembered goes stale; a state that is worked out cannot drift from the work.
:::

Beside these sit **records**: the check results, audits and retros that say what happened, written once and never changed. See [Records](knowledge-base/records).

## Where you see it in Fleet

The **Knowledge** page lists every journey, feature area, capability, component, requirement and decision in the repository you are looking at, and links each one to the things it relates to. The **Features** page shows the open work under each feature area. The **Architecture** page draws the component registry.

::action[Open Knowledge]{route="knowledge"}

## How a knowledge base starts

A new repository gets a small one from `fleet init`: a product statement, a first slice, an empty requirement register and the slot files to fill. See [Start a knowledge base](guides/knowledge/start-a-knowledge-base).

A repository that already has code is described into one a step at a time, drafted from the code and confirmed by a person:

::command{name="knowledge:bootstrap"}

::cards{links="knowledge-base/the-folder, knowledge-base/planning-modes, knowledge-base/what-is-it"}

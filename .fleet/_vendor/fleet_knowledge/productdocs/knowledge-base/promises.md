---
title: "Promises and requirements"
kind: concept
for: [everyone]
summary: "What the product has committed to, kept as numbered requirements that are never deleted, cited by id, and checked by the Quality desk."
sources:
  - knowledge/requirements/README.md
  - knowledge/requirements/fleet.md.tmpl
  - packages/fleet-knowledge/src/fleet_knowledge/templates/scaffold/knowledge/requirements/product.md
  - knowledge/scripts/gen_requirement_status.py
  - packages/fleet-knowledge/src/fleet_knowledge/templates/board.js
minutes: 6
---

:::lede
A promise is something the product says will always be true. Some promises are written as capabilities and journey criteria. The rest, the rules that hold while people use the product, the limits, the options refused, are written as numbered requirements, one sentence each, with an id that never changes.
:::

## Promises, and the three places they are written

A :term[promise] is anything the product commits to that the Quality desk can check. There is no separate list of them; they are worked out from three kinds of thing:

- **Capabilities**: what a person can do. See [Capabilities and components](knowledge-base/capabilities-and-components).
- **Journey criteria**: the numbered checks on a whole job. See [Journeys](knowledge-base/journeys).
- **Requirements**: the rules that hold while someone uses a capability. Approving an order is a capability; "an order of more than 500 parts needs a second approver" is a requirement.

This page is about the third.

## What a requirement is

A :term[requirement] is one sentence the system must always, or must never, do, with a permanent id. It reads "shall" or "never", and you could see it break. A register can also record a cost the team accepted knowingly, an option it refused, and a thing it decided not to build, so the next person does not reopen them.

Requirements live in one :term[register] per domain under `knowledge/requirements/`. A fresh repository starts with `knowledge/requirements/product.md`, whose ids begin `REQ-`. Each register owns its own prefix.

| Column | What it says |
|---|---|
| ID | The prefix and a number, such as `REQ-004`. Permanent, never reused. |
| Statement | One sentence that can be shown false, in the present tense. |
| Kind | Which sort of commitment: a rule, an invariant, a limit, a cost accepted, an option refused, something excluded. |
| Disposition | Whether it stands: adopted, rejected, superseded by another row, or still open. |
| Needs | Other rows it builds on. |
| Source | Where the commitment was made, quoting a phrase, never a line number. |

A real row from Fleet's own register, `FLT-1280`, begins: "Every slice row names a feature area (`area`, a feature map's slug in the same corpus); a program (`program`) is optional, legacy membership."

## The rules that keep requirements honest

- **Never edited away, never deleted.** A requirement that changes is superseded by a new row, and the old row stays to say what changed and when.
- **Cited, not restated.** Prose, PRDs and decisions write the id, such as `REQ-004`, instead of copying the sentence. When the rule changes, there is one place to change it.
- **Built is worked out, never written.** A register has no "done" column. A PRD names the requirements it makes true in its `implements:` front matter and covers each with an acceptance criterion citing the id. Whether a requirement is built follows from that, so "what did we decide that is not built yet" always has a true answer.

:::callout{kind="careful"}
Something read off the code is evidence, not a promise. When a knowledge base is first described from existing code, every drafted requirement is confirmed by a person before it is kept. A promise written from an accident in the code would make the Quality desk defend the bug.
:::

## Who writes requirements

Requirements are added as work is planned: a PRD records the commitments it introduces, and a slice can add the rows that say what it promises and refuses. A person confirms each one. Describing an existing code base drafts them from the code, in batches, for a person to confirm:

::command{name="knowledge:bootstrap"}

## Where you see them

The Knowledge page lists every requirement with its kind and disposition, linked to the PRDs that make it true. The Quality desk shows which promises nothing checks yet.

::action[Open Knowledge]{route="knowledge"}

::cards{links="knowledge-base/decisions, knowledge-base/prds, guides/quality/quality-desk"}

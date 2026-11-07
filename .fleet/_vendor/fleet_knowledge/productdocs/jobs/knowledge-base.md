---
title: "Learn the knowledge base"
kind: job
icon: knowledge
group: learn
for: [everyone]
summary: "The folder in your repository that holds what the product is, what it promised and what was decided."
minutes: 4
---

:::lede
Every repository Fleet works on keeps a `knowledge/` folder beside its code. It says what the product lets people do, what it promised, what was decided and what is changing now. Read this path and you will know what each part is for, which parts finish, and how to keep it true as the code changes.
:::

## The big picture

::diagram{name="knowledge-map"}

The folder answers four questions. **Planning** says what is changing: feature areas hold slices, and slices are made true by PRDs, with programs grouping slices in some repositories. **The product** says what is true now: the capabilities a person can use, the components that are built, and the journeys people take through them. **Commitments** say what must stay true: promises written as numbered requirements, and decisions that record what was chosen and why. **About your repository** holds the rest: slots that answer the questions Fleet's commands ask, records of what checks and runs found, and tables generated from files.

Most of it never finishes. A feature area, a capability or a requirement is true for as long as the product is, so it has no status. Only work finishes: a slice, a PRD, a program. Only a PRD's status is ever written, and Fleet works out the rest. Every change to the folder arrives as a pull request, reviewed like code. Agents read it before they build, the Programs and Features pages are drawn from it, and the Quality desk checks the running product against its promises.

## Read these in order

::path{links="knowledge-base/overview,knowledge-base/the-folder,knowledge-base/feature-areas,knowledge-base/slices,knowledge-base/prds,knowledge-base/promises"}

## Then, keep it true

::pages{links="guides/knowledge/start-a-knowledge-base,guides/knowledge/describe-existing-code,guides/knowledge/fill-slots,guides/knowledge/record-a-decision,guides/knowledge/keep-maps-current,guides/knowledge/move-to-areas,guides/knowledge/fix-a-failing-check,guides/knowledge/run-checks-in-your-ci"}

## When you need it

::pages{links="knowledge-base/planning-modes,knowledge-base/what-is-it,knowledge-base/programs,knowledge-base/capabilities-and-components,knowledge-base/journeys,knowledge-base/decisions,knowledge-base/slots,knowledge-base/records,knowledge-base/generated-tables"}

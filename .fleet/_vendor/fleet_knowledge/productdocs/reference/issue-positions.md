---
title: "Issue positions"
kind: reference
for: [everyone]
summary: "Every position an issue can be in, what it means, and what the fleet runs from it."
sources:
  - contracts/lifecycle/positions.json
  - packages/fleet-service/src/fleet_service/dispatch/lifecycle.py
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/registers/triage-partition.md
generated: true
---

:::lede
Every place an issue Fleet manages can be, in the order of its lifecycle. Look a position up here when an issue's position is unfamiliar or you want to know what runs from it next.
:::

The position is the claim: a box takes an issue only from a position that runs something, and the issue then sits in the claimed position while that run holds it.

## Positions

| Position | What it means | What the fleet runs from it | Claimed as |
|---|---|---|---|
| **Needs Design** (`needs-design`) | PRD frontmatter `prd-drafted` | nothing | — |
| **Needs Plan** (`needs-plan`) | PRD frontmatter `designed` | nothing | — |
| **Intake Queue** (`intake`) | a person filed it and it is waiting for its shaping interview — dispatchable agent work, exactly like the queues below | the intake interview | — |
| **Triage Queue** (`triage`) | filed, never checked — the checker owns re-entry | the triage check | Triaging |
| **Triaging** (`triaging`) | claimed for the triage half | nothing | — |
| **Implement Queue** (`queued`) | runnable, unclaimed — the fleet may take it | a fresh implement run | Implementing |
| **Implementing** (`implementing`) | claimed for the implement half | nothing | — |
| **Verify Queue** (`review`) | green PR, verifier owed, unclaimed | the verify run | Verifying |
| **Verifying** (`verifying`) | claimed for the verify half | nothing | — |
| **Rework Queue** (`rework`) | refuted by verification, back to the implementer | a re-fix (implement) run | Implementing |
| **Blocked · decision** (`blocked-decision`) | a human must ANSWER — gates the fleet, target zero | nothing | — |
| **Blocked · action** (`blocked-action`) | a human must DO something no agent can | nothing | — |
| **Needs answer** (`needs-answer`) | an agent asked the person who filed the item a question and is waiting on their reply — not a park, and not `Blocked · decision` | nothing | — |
| **Intake · decision** (`intake-decision`) | a finished dossier (or proposal) awaits its verdict on the fleet's idea page — not `Blocked · decision`, the operator's terminal queue | nothing | — |
| **Failed** (`failed`) | gave up after `MAX_ATTEMPTS` — needs a human reset | nothing | — |
| **Awaiting merge** (`awaiting-merge`) | green PR, the merge click is withheld | nothing | — |
| **Human WIP** (`human-wip`) | a person deliberately owns it — hands off | nothing | — |
| **Parked** (`parked`) | deliberate deferral | nothing | — |
| **Backlog** (`backlog`) | filed, not yet routed — stub PRDs live here; an idea born before may still be resting here (`idea:create` now files into `Intake Queue` instead — nothing dispatches `Backlog`, so a legacy idea here waits on a human to move it); a gated kind (bug/task/cleanup) resting here is a guardrail violation (`Backlog` dispatches nothing, so the check gate never ran on it) | nothing | — |
| **Done** (`done`) | finished: in no view | nothing | — |
| **Canceled** (`canceled`) | finished: in no view | nothing | — |
| **Duplicate** (`duplicate`) | finished: in no view | nothing | — |

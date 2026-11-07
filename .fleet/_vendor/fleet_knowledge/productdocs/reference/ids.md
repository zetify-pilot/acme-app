---
title: "Ids"
kind: reference
for: [everyone]
summary: "The shape of every id: programs, slices, PRDs, capabilities and requirement prefixes."
sources:
  - knowledge/slots/planning-model.md
  - packages/fleet-knowledge/src/fleet_knowledge/checks/planning/id_collisions.py
  - packages/fleet-knowledge/src/fleet_knowledge/checks/planning/_config.py
  - packages/fleet-knowledge/src/fleet_knowledge/config.py
generated: true
---

:::lede
The shape of every id in a knowledge base, as the id checks and the allocator read it. Look here when an id is refused, or before choosing your own prefixes.
:::

The prefixes are the defaults; a repository may set its own in `[fleet]` of `.fleet/fleet.toml`.

## Id shapes

| Id | Shape | Example | Where it is set |
|---|---|---|---|
| Program | `PG-NN` | `PG-01` | `program_prefix` |
| Slice | `SL-NNN` | `SL-001` | `slice_prefix` |
| PRD | `NNNN` | `0001` | the PRD's `prd:` front matter |
| Capability | `CAP-NNNN` | `CAP-0001` | `capability_prefix` |
| Requirement | `<PREFIX>-NNN`: 2 to 5 capital letters, a dash, and at least 2 digits | `RUN-001` | each register's own `prefix:` front matter |

A requirement register may not claim a reserved prefix: `ENG`.

## How a new id is reserved

| Setting | Default | What it does |
|---|---|---|
| `id_claims` | `false` | When true, the allocator reserves each new id by creating a claim ref, and the id check requires every id a change introduces to have one. |
| `id_claim_namespace` | `"refs/ids/"` | Where the claim refs live: one ref per id, created atomically, so a second caller is refused and moves to the next number. |
| `id_claim_remote` | `"origin"` | The remote the claim refs are created on. |
| `id_claim_repo` | `""` | The repository the claim refs are created on, when it should not be inferred from the remote. |

All four sit in `[fleet.planning]`. Without claims, the id check still refuses an id that both this branch and the main branch minted after they diverged.

## Other id conventions

Fleet's own planning model adds these:

- Bar criteria: the entity id with the dash removed then `-P<n>` (program) or `-C<n>` (slice), e.g. PG01-P1, SL001-C1.
- A PRD's tracker issue is titled `[NNNN]` followed by the PRD's title.
- Ids are this corpus's own; another corpus's document is cited repo-qualified (`acme:0772`, `acme:SL-137`).

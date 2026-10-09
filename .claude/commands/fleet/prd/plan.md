#  Plan

Split a feature design into parallel implementation plans — one per lane `slot:languages` names for this repo (typically a backend lane and a frontend lane; a repo with one lane writes one plan). Each plan contains ordered tasks with dependencies, file ownership, and verification steps.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. The prose Steps below are the authority; this spine indexes them.

```json
{
  "command": "prd-plan",
  "tier": "core",
  "intent": "Split a design into parallel backend + frontend implementation plans with edge-case coverage and design-fidelity ACs.",
  "sop": "none",
  "needs": "nothing",
  "may merge": true,
  "loads": ["languages", "api-contract", "permissions", "ui-contracts"],
  "requires": ["process-spine", "languages", "planning-model", "gate"],
  "optional": [
    "ui-contracts", "domain-model", "api-contract", "file-conventions", "permissions",
    "entity-model", "product-vision", "process-design-fidelity", "commitments", "architecture",
    "resilience", "codegen", "docs"
  ],
  "steps": [
    {"id": "contract-boundary", "name": "Identify the contract boundary", "kind": "author", "actor": "coordinator", "consumes": ["design"],          "body": "identify-the-contract-boundary"},
    {"id": "test-strategy",     "name": "Test strategy & edge cases",     "kind": "author", "actor": "coordinator", "consumes": ["prd", "design"],     "body": "test-strategy-edge-case-analysis"},
    {"id": "backend-plan",      "name": "Build the backend plan",         "kind": "author", "actor": "coordinator", "produces": ["backend-plan"],      "body": "build-the-backend-plan"},
    {"id": "frontend-plan",     "name": "Build the frontend plan",        "kind": "author", "actor": "coordinator", "produces": ["frontend-plan", "acceptance-criteria"], "body": "build-the-frontend-plan"},
    {"id": "cross-plan-deps",   "name": "Cross-plan dependencies",        "kind": "author", "actor": "coordinator",                                    "body": "cross-plan-dependencies"},
    {"id": "docs-plan",         "name": "Build the docs plan (docs slot)", "kind": "author", "actor": "coordinator",                                    "body": "step-4b-build-the-docs-plan-the-docs-slot"},
    {"id": "output",            "name": "Write plan files",               "kind": "io",     "actor": "coordinator",                                    "body": "step-6-output"},
    {"id": "requirement-cover", "name": "Claimed-requirement coverage",   "kind": "gate",   "actor": "coordinator", "gate": "hard", "consumes": ["requirement-register", "acceptance-criteria"], "body": "step-6-5-claimed-requirement-coverage"},
    {"id": "envelope-recheck",  "name": "Re-measure the envelope — two ceilings (per-run, per-PR)", "kind": "gate", "actor": "coordinator", "gate": "hard", "consumes": ["backend-plan", "frontend-plan", "design"], "body": "step-6-6-re-measure-the-envelope-two-ceilings-hard-gate-before-the-flip"},
    {"id": "flip-status",       "name": "Flip PRD status to planned",     "kind": "io",     "actor": "coordinator", "produces": ["status"], "body": "flip-prd-status-to-planned"},
    {"id": "land",              "name": "Land it — the branch, the PR, the merge", "kind": "gate", "actor": "coordinator", "gate": "hard", "body": "step-8-land-it"},
    {"id": "landed",            "name": "The landed result, then the sentinel", "kind": "io", "actor": "coordinator", "body": "step-8-land-it"}
  ]
}
```

---

## CRITICAL RULES

**Unconfirmed assumptions are assumptions to confirm, not facts.** A PRD's `## Unconfirmed
assumptions` section lists what its interview could not settle because the owner marked a question
*"I can't answer this"* and the run carried on ([`interview-protocol`](../../../process/interview.md)
→ *"I can't answer this"*). Never cite one as a decision, never promote one into an acceptance
criterion or a requirement row on your own authority, and when a design choice turns on one, put
that question to the person who can answer it — the reporter included — before building on it.

1. **Read the design first.** This command requires `knowledge/prds/NNNN`. If it doesn't exist, tell the user to run `/fleet:prd:design` first.
2. **File ownership is absolute.** Backend and frontend plans must not touch the same files. If they do, the task belongs in one plan with a contract dependency in the other.
3. **Contract boundary first.** Identify the API surface (OpenAPI endpoints, response types) shared by both plans. This gets generated before either plan runs.
4. **Tasks are atomic.** Each task should be completable in one focused session. If a task is too large, split it.
5. **Dependencies are explicit.** Every task declares what it depends on (within its plan) and what contract it depends on (from the other plan).
6. **Verification is mandatory.** Every task has a verification step (test command, manual check, or both).
7. **Edge cases are enumerated upfront.** Step 2 produces a numbered list of edge cases (`E1`, `E2`, …) covering happy paths, input boundaries, authz, concurrency/multi-replica, failure modes, empty/degenerate states, security/abuse, and audit/observability. Every `E<N>` MUST be referenced by at least one task's `**Edge cases covered:**` field — an unreferenced `E<N>` means the plan is incomplete.
8. **Plan the best solution, not the fastest route to green** (truth-seeking golden rule). If the design still leaves a genuinely better implementation path on the table, say so before writing tasks rather than quietly planning the easiest one. Where a task deliberately trades quality for speed, name that tradeoff in the task so it's a conscious choice, not a silent default.
9. **The plan adds no scope — it is the last place an addition can still hide.** By the time you run, the ask has passed two gates (`prd:create` Phase 3, `prd:design` Phase 5.4) and both recorded what they admitted and refused in a `## Scope ledger`. **A plan that introduces a file, endpoint, table, event, permission, flag, component or config knob the design never named has silently re-opened a settled question** — and it is the hardest addition to spot, because a task list is read for completeness, not for restraint. Rule 8 is about *how* a task is built; it is not licence to add tasks. If planning genuinely reveals something the design missed:
   - **It is required by an acceptance criterion** → plan it, and add a row to `design.md`'s `## Scope ledger` (`admitted`, basis: the AC) in the same commit. The design was incomplete, and the ledger is where that is recorded.
   - **It is anything else** → **do not plan it.** Add a `withheld` row to `design.md`'s `## Scope ledger` naming it, and carry on. Do not file it, and do not raise it again at implement time.

   Read Step 2's edge-case enumeration under the same rule: an `E<N>` is a **behavior of the thing the design describes**, so a `E<N>` whose only owner would be a new mechanism is not a missing edge case — it is an addition wearing one. Authority: [`tracking-and-execution.md`](#) → *Scope discipline*.

   **And a task inherits its requirement's necessity, never the reverse.** `prd:create` and
   `prd:design` each ran the necessity test (their Rules 4c / 6c); a requirement that was
   **deferred** there is not planned here, however tempting it is to "finish the set" because its
   register row still reads `adopted` — an unclaimed adopted row is the deferral working as
   designed, not an oversight to correct. If planning surfaces a requirement that never took the
   test at all — common on a PRD assembled from a stub or a split — **apply it now**: what breaks
   without it, how often does it fire. A task list is read for completeness, which is exactly why
   an unearned requirement survives to this stage: nobody re-asks whether it should exist, they
   only check that it is covered. Authority: [`tracking-and-execution.md`](#) → *The necessity test*.

---

## Input

Parse the argument: $ARGUMENTS — this should be a PRD number (e.g., "0003").

Read these files:
1. `knowledge/prds/NNNN` (required)
2. `knowledge/prds/NNNN` (if exists — informs frontend plan)
3. `knowledge/prds/NNNN` (for acceptance criteria reference)
4. `` (for context)
5. `knowledge/requirements/<domain>.md` — only for the IDs in the PRD's `implements:`, read
   for their statements (Step 6.5). Skip when `implements:` is absent or empty.

**In a person's own session, tell the fleet you are planning this PRD before any other work.** If the
fleet session tools are connected (the `hold_planning` tool), call
`hold_planning(prd="NNNN", step="plan", where="<your branch>")`, so the fleet does not start its own plan
of the same PRD under a driven program. The hold lapses when the PRD's status moves. A refusal (a fleet
run's token is refused by design) or a missing tool is not a blocker: continue. If you abandon the plan,
call it again with `release=true`.

---

## Step 1: Identify the Contract Boundary

The contract boundary is the API surface that both backend and frontend depend on. This must be defined and generated before parallel work begins.

**Contract items include:**
- OpenAPI endpoint definitions (paths, methods, request/response schemas)
- SSE event types and payloads
- Generated TypeScript types from OpenAPI

Present the contract:

```
## Contract Boundary

These items must be generated before backend and frontend plans can execute in parallel.

### API Endpoints
| Path | Method | Purpose |
|------|--------|---------|
| ... | ... | ... |

### SSE Events
| Event type | Payload fields | Domain file |
|------------|---------------|-------------|
| ... | ... | ... |

### Contract Generation Tasks (run first)
1. Update `` with new endpoints and schemas
2. Run `make generate` for the API spec
3. Add event definitions to the event contract `slot:codegen` names (if applicable)
4. Run `make generate` for the event contracts (if applicable)
```

### API & enum convention pre-check (emit lint-clean on the first generate)

**Applies where the repo's `slot:api-contract` and `slot:codegen` name a spec/codegen
pair.** A repo with no API contract skips this section; a repo with one has lints that **fail
at `make lint`, not at authoring**, and across recent autonomous runs re-discovering
them at gate time was the single most repeated mechanical cost — each new-operation or
new-enum plan burned **1–3 extra gate cycles**. The rules are not the problem; *deciding them
at plan time* is. **For every new operation and every new enum, make the decisions now and
record them in the contract** so the contract sub-agent emits a lint-clean spec on the first
`make generate`.

Canonical sources (don't re-derive — cite them): the API design guide `slot:api-contract`
names (operation naming, pagination, response codes, audit and permission annotations) and
the per-language contract `slot:languages` names for *a new enum on a stored
column* — the places that must change in lockstep, and the lint each skipped place trips.

For each new operation, record: its id and naming; its pagination shape; its permission
and audit annotations; whether its path parameters or streaming shape need registering
with the repo's conformance tests (`make test-e2e` names them). For each new enum:
the named type, the contract-level schema binding, the storage-level override, and the
typed constants — **all in the foundation task**, because each skipped place surfaces as a
lint cascade two waves later.

Record the filled-in table (and any new enums) in `backend-plan.md` under the Contract section so the implement step's contract sub-agent inherits the decisions, not the rediscovery.

---

## Step 2: Test Strategy & Edge Case Analysis

Before drafting any task, **enumerate every behavior the implementation must prove**. The output is a single numbered list (`E1`, `E2`, …) that the per-task `**Tests:**` and `**Edge cases covered:**` fields in Steps 3 and 4 will reference. Every `E<N>` must end up owned by at least one task; if you cannot place an entry, the task list is incomplete (add a task) or the entry is out of scope (delete it and say why).

**Sources to mine for edge cases (in order):**
1. `prd.md` — acceptance criteria → happy paths, explicit non-goals, success metrics.
2. `design.md` — data model, state transitions, API surface → invariants, illegal transitions, concurrent-write hazards.
3. `` — three-layer permission model → authz failure modes for every new endpoint and tool.
4. `` — error envelope, pagination, mutation-returns-resource rules.
5. `CLAUDE.md` "Multi-replica safety (load-bearing invariant)" — every new in-memory cache or background goroutine.
6. Existing tests in the affected packages — patterns already in use (saves reinventing fixtures).

**Categories. Fill each one or write `N/A — <reason>` explicitly. Do not silently omit.**

```markdown
## Test Strategy & Edge Cases

### Happy paths
- E1: <one-line behavior> — <test layer: go unit / go db / e2e / frontend unit / playwright>
- E2: ...

### Input validation & boundaries
- E<N>: empty / max-length / unicode / negative / past-date / future-date / boundary numeric inputs.
- E<N>: malformed payload (additionalProperties, wrong type, missing required) → 400 with `Error` schema.
- E<N>: pagination edges (`limit=0`, `offset` past end, `limit` over max).

### Authorization & isolation
- E<N>: caller missing `<resource:action>` → 403 with `Error` schema.
- E<N>: cross-org or cross-workspace access → 404 (do not leak existence).
- E<N>: agent API-key narrowing only narrows, never widens (projection-compiler ANDs the override).
- E<N>: row-policy CEL filters apply to every projection read added by this feature.

### Concurrency & multi-replica
- E<N>: same job/event consumed by two replicas → idempotent (`SELECT ... FOR UPDATE SKIP LOCKED`, unique constraint, or idempotency cache).
- E<N>: in-memory cache mutated on replica A → replica B drops its copy via SSE invalidation event.
- E<N>: webhook replay / duplicate inbound → idempotency cache returns prior result, no double-write.
- E<N>: shutdown cancels background goroutines started via `BackgroundTasks.Go`.

### Error & failure modes
- E<N>: downstream (connector / LLM / external API) unavailable → clean error to caller, no partial state.
- E<N>: PG transaction rollback on validation failure → no orphan rows or zombie ontology entries.
- E<N>: LLM timeout / rate-limit → retried per policy; audit-log entry written.
- E<N>: `connectord` disconnected mid-batch → resumes from last persisted watermark.

### Empty / degenerate states (frontend especially)
- E<N>: empty list → empty-state component, not a blank page.
- E<N>: long strings / overflow → truncation per ``; long text never inline on canvas nodes.
- E<N>: loading skeleton, error toast, and retry path for every fetch.

### Security / abuse
- E<N>: dynamic SQL inputs in projection compiler use pgx `Identifier` sanitization and parameterized values.
- E<N>: secrets/PII never logged (handler boundary, audit log, error sanitization).
- E<N>: vault values redacted in API responses and audit log.

### Audit & observability
- E<N>: every privileged mutation writes an audit-log entry of the correct category.
- E<N>: relevant OTel metrics increment (request count, error count, latency histogram).
- E<N>: SSE invalidation events published on the global bus for every PG-backed config mutation that has in-memory state.
```

**Output rules:**
- IDs are stable across the rest of the plan; do not renumber once tasks reference them.
- One `E<N>` = one assertable behavior. Split if it would need two distinct tests.
- Mark each entry with the **lowest sufficient test layer** — prefer Go unit > Go DB integration > e2e > Playwright. Choose Playwright/fullstack only when the assertion genuinely requires it.

---

## Step 3: Build the Backend Plan

**Backend owns the directories `slot:file-conventions` assigns to the backend
lane** — the contract sources (`slot:codegen`), storage, the API surface, the
services behind it, the daemons and their SDKs, whatever this repo's backend is. The plan
lists the ones this PRD touches by name; ownership is the slot's, never the plan's guess.

**Task format:**

```markdown
### Task B<N>: <descriptive name>

**Wave:** <1, 2, 3...> (tasks in the same wave can run in parallel)
**Files:**
- <file path 1>
- <file path 2>

**Depends on:** <Task B<M>> or "None" or "Contract"
**Contract dependency:** <None, or "API endpoint X must be generated">

**What to do:**
<Clear, actionable description. Reference design.md sections. Include specific conventions from CLAUDE.md that apply.>

**Edge cases covered:** E<N>, E<M>, ...
<List the IDs from Step 2 this task is responsible for. Every E<N> in Step 2 must appear in at least one task across all plans.>

**Tests:**
- `<test file 1>` — asserts E<N>, E<M> (<short description per ID>)
- `<test file 2>` — asserts E<P> (<short description>)
- Or "Covered by existing tests" with justification AND the E<N> IDs the existing tests already cover.

**Verify:**
- `<test command>` passes
- <manual check if needed>
```

**Wave assignment rules:**
- Wave 1: Tasks with no dependencies (shared contracts, migrations, schema changes)
- Wave 2: Tasks that depend only on Wave 1 (handlers, stores, connectord/connector handlers)
- Wave 3: Tasks that depend on Wave 2 (integration, background tasks, SSE publishing)
- Higher waves as needed

**Migration numbering — never bake a literal.** A migration task names its file
with a placeholder (`migrations/00NNN_<slug>.sql`), NOT a concrete number. The
real number is the highest existing prefix + 1, computed by the implement step
at implement-time (see [[`implementation.md`](../../../process/implementation.md)](../../../process/implementation.md) §3a) — by the time the
plan is executed, concurrent work will likely have consumed the number any
literal guessed, forcing a renumber. The placeholder makes that a non-event.

**Resilience rules (`slot:resilience`):**
Where `slot:resilience` says the service runs more than one replica, ensure:
- Background tasks / periodic jobs that must run exactly once use distributed locks or `SELECT ... FOR UPDATE SKIP LOCKED` — not in-memory guards.
- State shared between requests (caches, counters, rate limits) uses a shared store (Postgres, Redis), not in-memory maps — those are per-replica.
- SSE event publishing accounts for cross-replica fan-out if clients may connect to different replicas.
- Queue consumers and webhook handlers are idempotent — the same message may reach multiple replicas.
- Tests for concurrent behavior should verify correctness under multi-replica conditions where possible (e.g., test idempotency, test `FOR UPDATE` locking).

**Test deliverable rules:**
- Every task that creates new public functions or handlers MUST list test deliverables in its `**Tests:**` field.
- A task with no `**Tests:**` field is malformed unless it only modifies generated code, config, or migrations.
- Every `**Tests:**` entry must cite the specific `E<N>` IDs from Step 2 it asserts. A test that asserts no enumerated edge case is either redundant or revealing a missing entry in Step 2 — go back and add it.
- Test files belong in the same task as the code they test — do not defer tests to a later task.

---

## Step 4: Build the Frontend Plan

**Frontend owns the directories `slot:file-conventions` assigns to the frontend
lane** (`slot:ui-contracts` names where pages live).

**Task format:** Same as backend.

**Frontend-specific considerations:**
- **Read the UI contract `slot:ui-contracts` names first.** All frontend tasks must follow the page structures, component patterns, and interaction conventions documented there. Do not invent new structural patterns when existing ones apply.
- **Read [`../../../process/design-fidelity-loop.md`](../../../process/design-fidelity-loop.md).** For every UI surface this PRD adds or materially changes, emit an explicit **design-fidelity acceptance criterion** — tracked exactly like a functional AC, not folded into "design system compliance". Each such AC names the surface, cites **the approved mockup** (`ux-design.md` → `## Approved design`: the fixture route + `tests/fidelity/` spec) **and** the **reference** (`mockups/reference-<archetype>.png`), and asserts the surface **matches the approved mockup** and **clears the design-fidelity bar** (§2: `Q1–Q6`, surface hierarchy, one primary action, scale discipline, holistic). It is browser-verifiable — it gets a `playwright` row (below) and is what the `implement` build loop (§3) fixes *to*. A UI surface with no design-fidelity AC is how "functional but looks bad" ships: the functional ACs pass and nothing ever gated the look.
- **If a UI surface has no approved mockup, the plan is blocked, not degraded.** Say so and route back to `/fleet:prd:design` (Step 0b/0c) rather than writing an AC that cites only the reference — an AC pointing at a Stripe screenshot instead of an agreed design is what lets implementation build something nobody chose.
- **Exception — a change that is purely ADDITIVE to a page that already shipped** (one read-only field, a badge on an existing row) is not a surface, and does not need a mockup ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5c). Such a plan carries the heading **`## Surface scope: additive to an existing surface`**, cites the target page's `<Page>.spec.md` by repo-relative path as its fidelity target, and **updates that spec in the same change** with the new element's layout slot, states and canonical-choice rule. The design-fidelity AC then cites the page-spec instead of an approved mockup; the `playwright` row is unchanged and still mandatory. `make validate-knowledge` checks the declaration for real: the cited spec must exist **and predate the plan in git**, so a new page whose spec you wrote just now still needs the full gate. "Exist" is judged as of the plan: a spec deleted *after* the plan (its page retired later) still counts and is reported as an advisory, never a failure.
- **Every mockup citation is a REPO-RELATIVE PATH — never a hosted URL** ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5-0). `implement` and `verify` run headless with the repo and nothing else: they cannot open a `claude.ai/code/artifact/…` link, a chat screenshot, or anything in a scratchpad. An AC whose fidelity target is a URL is **malformed** — it cites something the agent that must satisfy it can never see. If `ux-design.md` records an approval that names only a link, treat the mockup as **missing** and route back to `design` to commit the file and re-record. Same rule for the named reference: the PRD's `mockups/reference-<archetype>.png` must be **on disk**; an AC citing a reference image that does not exist is unsatisfiable, and saying so in the plan is required rather than optional.
- If a `ux-design.md` exists, each frontend task should reference the relevant screen/section from the UX design.
- API client functions, hooks and event consumption go where the frontend contract
  `slot:languages` names — never a new parallel home.
- Reference existing component patterns before creating new ones.

**Wave assignment rules:**
- Wave 1: API client functions, type definitions, basic hooks
- Wave 2: Page components, list/table views
- Wave 3: Detail views, interactive features, SSE subscriptions
- Wave 4: Polish, empty states, error handling, loading states

---

## Step 4b: Build the Docs Plan (the `docs` slot)

**Only when the design's `## Docs impact` names at least one page.** Read that section and the
coverage rule `slot:docs` names, then emit **one task per page id** in `docs-plan.md`, in the
PRD directory beside the other plans. A page a customer is meant to follow is a deliverable
like any other — it is never an afterthought appended to a code task.

**Task format** (the same fields as Step 3), one page id per task:

```
### Task D<N>: Write page <page id>
**Page:** <page id>, in the home `slot:docs` names (never a literal path)
**Audience / kind:** <from the design's Docs impact>
**Write:** the page exactly to the slot's page contract.
**Map:** set the `Documented in` cell of this capability's row in the feature capability map
(`slot:feature-maps`) to the page id — the loop-closing edit, alongside `Ships in` / `Tested by`.
**Generated references:** when the slot marks this home generated, run the generated-reference
target the slot names and commit its output — never hand-edit generated docs.
**Verified by:** the journey the design's Docs impact names.
```

A page with **no** docs task is a page nobody writes; an AC that requires a customer to follow
a page is not satisfied by prose that says the page should exist.

**Degrade.** When the repository leaves `slot:docs` unfilled there is no home, no page contract
and no generated-reference target — write **no** docs plan, and say so in one line. The docs
tasks are absent, not guessed.

---

## Step 5: Cross-Plan Dependencies

Identify any ordering constraints between the two plans:

```
## Cross-Plan Dependencies

| Frontend task | Depends on backend task | Reason |
|---------------|------------------------|--------|
| F2: API client functions | Contract generated | Needs OpenAPI types |
| F4: Job detail page | B3: Job detail handler | Needs working endpoint |
| ... | ... | ... |
```

---

## Step 6: Output

Save the plan files. Each **must** open with the `prd-plan` frontmatter header below —
[``](#) requires it, and a
missing header fails `make validate-knowledge` (same class of gap as ,
which hit `design.md`'s `prd-design` header before it was added there).

**A backend-only PRD authors ONLY `backend-plan.md` — do not create `frontend-plan.md`.**
When the PRD has no customer-facing surface (frontmatter "How the customer leverages it
(UX): None — internal / backend-only" — a pure refactor, a substrate/data-plane change),
the *absence* of a `frontend-plan.md` is how "no UI surface" is declared, matching the
established convention (dozens of backend-only PRDs do this). `make validate-knowledge`
treats **any** `frontend-plan.md` as implying a UI surface that needs a `playwright` row
plus either an approved mockup (a `ux-design.md` with an `## Approved design` block) or
the additive-surface declaration above — so an "N/A" frontend plan **fails CI** rather
than passing as a no-op. Fold the one-line "frontend: none (justified)" note into
`backend-plan.md` instead. Author both files only when the PRD actually has a customer
surface.

### `knowledge/prds/NNNN`

```markdown
---
type: prd-plan
---

# Backend Plan: <feature name>

PRD: knowledge/prds/NNNN
Design: knowledge/prds/NNNN

## Contract (generate first)
<contract generation tasks>
<the filled-in OpenAPI & Enum Convention Pre-Check decision table from Step 1 — one row per new operation, plus any new-enum "FOUR places" checklist. This is what makes the first `make generate` lint-clean; the implement step's contract sub-agent reads it.>

## Test Strategy & Edge Cases
<paste the full Step 2 list here — every E<N> with its category and target test layer. This is the canonical source for tasks below; do not let it fall out of sync.>

## Tasks

### Task B1: ...
### Task B2: ...
...

## Edge Case Coverage Matrix
| ID | Description | Owning task(s) | Test layer |
|----|-------------|----------------|------------|
| E1 | ... | B2 | go unit |
| E2 | ... | B3, B5 | go db |
| ... | ... | ... | ... |

If any backend-scoped `E<N>` has no owning task, the plan is incomplete — add a task or split an existing one before saving.

## Verification
After all tasks complete:
- `make test-unit` passes
- `make test-db` passes (if DB changes)
- `make test-unit` for that lane passes (if Python changes)
- `make test-unit` and `make test-unit` for that lane pass for connectord/connector changes as applicable
- `make lint` clean
- `make build` succeeds
- Every backend-scoped `E<N>` from the Test Strategy section has at least one passing test asserting it.
```

### `knowledge/prds/NNNN`

```markdown
---
type: prd-plan
---

# Frontend Plan: <feature name>

PRD: knowledge/prds/NNNN
Design: knowledge/prds/NNNN
UX Design: knowledge/prds/NNNN (if exists)
Design System: 

## Prerequisites
- Contract must be generated (see backend-plan.md)
- Backend tasks <list> must be complete for full integration

## Test Strategy & Edge Cases
<paste the frontend-relevant entries from the Step 2 list (empty/loading/error states, long-string overflow, permission-denied UI, optimistic-update conflicts, SSE reconnection, etc.). Keep the same E<N> IDs used in backend-plan.md so the two plans share one numbering space.>

## Tasks

### Task F1: ...
### Task F2: ...
...

## Edge Case Coverage Matrix
| ID | Description | Owning task(s) | Test layer |
|----|-------------|----------------|------------|
| E<N> | empty list state | F3 | playwright |
| E<N> | SSE reconnect after network blip | F5 | playwright |
| E<N> | <every user-visible acceptance criterion> | F<n> | playwright |
| E<N> | **<surface> matches the approved mockup (`<fixture route>`) and clears the design-fidelity bar (§2)** | F<n> | playwright |
| ... | ... | ... | ... |

**Every user-visible acceptance criterion from the PRD MUST appear as a row with `playwright` as the test layer.** So must **every new/changed UI surface's design-fidelity AC** — the look is verified in the browser, never assumed. Vitest unit tests mock React Flow / Radix portals / Sheet & Dialog chains — the unit suite can be fully green while the live page crashes on load (see ``). Vitest is fine as a *supplement* for pure-function and store-logic coverage, but it cannot stand in for a probe on a UI AC. If any UI AC has no `playwright` row, the plan is incomplete.

If any frontend-scoped `E<N>` has no owning task, the plan is incomplete.

## Verification
After all tasks complete:
- `make test-unit` for the frontend lane passes
- Playwright probe (`tests/playwright/probe-<NNNN>-<slug>.mjs` or extension of an existing probe) passes and produces a screenshot per UI acceptance criterion under `tests/playwright/screenshots/`
- Probe covers every `E<N>` marked `playwright` in the matrix above, including every user-visible AC
- Console errors during the probe run: zero
- Design system compliance: page structure, component patterns, and interaction conventions match ``
- **Design fidelity: every new/changed surface clears the design-fidelity bar** ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §2) against its named reference — `implement` fixes to it in the build loop (§3), `verify` gates on it. Not "looks fine to me"; the `Q1–Q6` + holistic bar, in the browser.
- **Visual-regression baseline committed** for each new/changed surface once it clears the bar (§4) — the good state, captured; CI diffs against it thereafter.
- Empty states render correctly
- Error states handled
- Loading states shown

"Manual verification" alone is NOT a substitute for a Playwright probe — it is not reproducible and does not catch the runtime-only failures Vitest misses.
```

### `docs-plan.md` (in the PRD directory, only when the design has a `## Docs impact`)

```markdown
---
type: prd-plan
---

# Docs Plan: <feature name>

PRD: knowledge/prds/NNNN
Design: knowledge/prds/NNNN

## Pages
<one line per page id from the design's Docs impact: the page id, the home `slot:docs`
names (never a literal path), its audience, its page kind, and the journey that verifies it.>

## Tasks

### Task D1: Write page <page id>
**Page:** <page id>, in the home `slot:docs` names
**Audience / kind:** <audience> / <page kind>
**Write:** <what the page must carry, per the slot's page contract>
**Map:** feature capability map `Documented in` cell → <page id>
**Generated references:** <the generated-reference target the slot names, or "none">
**Verified by:** <journey>

## Verification
After all tasks complete:
- Every page id from the design's Docs impact has a written page in the home `slot:docs` names.
- `Documented in` is set for each documented capability in the feature capability map.
- The generated-reference target the slot names is re-run and its output committed (when the
  home is generated).
- The verifying journey follows each new how-to literally, in the real UI.
```

---

## Step 6.5: Claimed-requirement coverage (HARD GATE — before the flip)

**`planned` is where the register stops being advisory.** `make validate-knowledge`
enforces AC coverage from `planned` onward — and Step 7 is that flip, in this command's own
commit. So this is the last stage where an uncovered claim is fixed by *authoring* rather
than by a blocked commit whose only quick escapes are both wrong (a citation pasted onto an
AC that does not test the commitment, or a claim quietly deleted).

Read `implements:` from `knowledge/prds/NNNN`. **No `implements:` → nothing
claimed; skip this step.** Otherwise, for each ID:

1. **Find the acceptance criterion that would fail if the requirement were not met**, and
   confirm it cites the ID in the form `**[]**` under the PRD's acceptance-criteria
   heading. Reading the register row's own statement is the point — a citation on an AC that
   asserts something adjacent is the failure `/fleet:prd:verify` exists to catch later, at
   ten times the cost.
2. **A claim with no such AC has exactly two honest resolutions**, and you pick one here:
   **write the AC** (this command already authors ACs), or **drop the claim** from
   `implements:` because this PRD does not in fact realise it. Never a third.
3. **Every AC carries a label, and there are exactly two.** `**[]**` means this AC is
   the test of a commitment. `**[local]**` means it carries none — it is how we happened to
   build this, and a reader outside the PRD never needs to re-read the reason. **Most ACs are
   `[local]`, and that must stay normal.**

   The label is not bookkeeping. Without it, *"we checked and this AC promises nothing"* and
   *"nobody looked"* are the same text, and every downstream gate — including the one that
   decides whether a design may run without a human — has to guess between them
   ([*The claim spine*](#)).

   **This does not reverse the one-direction rule.** You are not walking the AC list looking
   for requirements to mint; you are *marking* the ones that carry none. But when labelling
   an AC you find it genuinely does assert a *"the system shall / never"* that no row
   carries, that is the escalation, not a `[local]`: send it back to
   [`prd:design`](design.md) Phase 4c, which owns minting the row.
4. **The citing AC must be owned by at least one task**, like any other AC — check it against
   the Edge Case Coverage Matrix. A claimed commitment no task builds is a claim that ships
   unbuilt, and the derived backlog will report it done.
5. **A claim the register calls `rejected` or `superseded` is a stop, not a warning** — the
   validator errors on it at any live status. Either the design missed a supersession closure
   ([`prd:design`](design.md) Phase 4c — fix the register) or this PRD is building something
   we refused (drop the claim and say so). Do not flip the status around it.

Record the outcome in one line in `backend-plan.md` (or the frontend plan when it owns the
citing ACs): the IDs claimed and the AC number covering each, or "no claimed requirements".

---

## Step 6.6: Re-measure the envelope — TWO ceilings (HARD GATE — before the flip)

**The envelope is set at design ([`design.md`](design.md) Phase 5.5), not here.** That is
deliberate: a PRD that is too big is cheapest to fix while the only artifact is a design,
and a gate that fires *after* a full task breakdown exists asks its reader to throw that
breakdown away — which is exactly the moment a gate gets waved through. This step is the
**backstop**: the plan is the first time the work is enumerated task by task, so it is the
first time the design's estimate can be checked against something concrete. It is also the
first time the work exists as *plan files* — and the unit that survives a restart is the
**run**, not the PRD — so this is where the two ceilings () get measured.

**Measure hand-written work only — EXCLUDE generated output from BOTH ceilings.** A plan
touching a codegen source carries thousands of generated lines nobody authors or reviews,
and calibrating a ceiling against an inflated measurement reproduces the defect it exists
to stop. Count files and added lines **by hand**: exclude everything
`slot:codegen` names. Every "added lines" figure in both ceilings below means
**hand-written added lines**.

**Test mass stays off the table — under BOTH ceilings.** Test mass is the dominant term in
every measurement of this repo's PRDs, and shaving it is not an acceptable response to
either ceiling. A tighter number is never licence to cut tests, and neither ceiling may be
met by trimming them.

Do this before flipping — re-state, then check each ceiling:

1. **Re-state the envelope from the task list** — files touched and rough lines added — in
   one line at the top of each plan file, and **carry forward the design's own envelope
   line beside it**:
   `Envelope: ~14 files, ~900 lines added (design said ~12/~800).`
   An estimate you would defend, not a number that makes the gate pass.

2. **Per-RUN ceiling: each plan file fits ~2,000 hand-written added lines.** A plan file is
   what a single `prd:implement` run executes, and **run survival is exactly what this
   ceiling prices**: a daemon restart (any deploy, any maintenance) issues a graceful stop,
   and the  drain only nudges a run toward its *ship step*; a run hours from
   shipping cannot be drained, so it is stopped and everything but a salvage branch is
   discarded. PRD 0486 — 22 tasks, 146 files, +12,915 — lost a **2h44m** run that way, six
   times in two days, none of them a counted attempt, blocking 8 issues throughout. A PRD
   with a `backend-plan.md` and a `frontend-plan.md` already executes as **two runs** into
   one branch and merges once — Rule F's atomic ship is satisfied while halving the
   per-run exposure — so measure **each plan file separately** against this ceiling. **If
   one plan file busts ~2,000 hand-written lines, split the plan files** (cut it into more
   plan files, i.e. more runs into the same branch). That is NOT a new PRD — see the two
   rationales below.

   **A split has an executable form: the numbered plan family ().** When you
   split, keep the base file as `backend-plan.md` (or `frontend-plan.md`) and name the
   additional files by numeric suffix — `backend-plan-2.md`, `backend-plan-3.md`, ... Each
   carries the same `prd-plan` frontmatter header. `prd:implement` executes the family in
   numeric order into one branch (base first, then splits), `make validate-knowledge`
   validates every member, and the `prd-projection` pass of the fleet's `corpus-sync` loop lists them in reading order. A split plan
   is still ONE branch and ONE merge — each file is a run into that branch, never a new
   PRD. Do NOT split an already-split file's number (no `backend-plan-2b.md`); add the next
   integer.

3. **Per-PR ceiling: the whole PRD fits ~10,000 hand-written added lines, or go back to
   design to split into sibling PRDs.** This is the ceiling that prices **reviewability** —
   the cost of an oversized PR is paid entirely by someone other than the author: the
   reviewer, the bisecting debugger, and every PRD queued behind the merge. It is
   calibrated against **what this repo actually merges**: 0401 (+4,635), 0484 (+4,121),
   0437 (+9,701) are large PRDs that merged cleanly and should stay visible as large
   **without manufacturing a waiver at plan time** — the ceiling sits above them. **If the
   whole PRD (all plan files, hand-written) busts ~10,000 lines, STOP and go back to
   [`/fleet:prd:design`](design.md) Phase 5.5 to split it into sibling PRDs** — the
   split-into-siblings path is unchanged. Do not cut it into increments here. A PRD that
   must land in more than one merge is **a slice with several PRDs**, not one PRD with
   several parts — `knowledge-model.md`'s master rule settles the tier, and Rule F's atomic
   ship means "a PRD that merges three times" has no representation in the status model.
   Phase 5.5 of `design.md` holds the split recipe and the seams that work.

   A plan that busts a design envelope it was supposed to fit is **a design-time miss
   surfacing late**, so it goes back to the stage that owns it. Say by how much, so the
   design's estimate can be corrected rather than merely overridden.

**Two ceilings, two rationales — neither may be recalibrated against the other's reason.**
The **per-run** ceiling (~2,000 per plan file) serves **run survival** — how long a single
run survives a restart. The **per-PR** ceiling (~10,000 for the whole PRD) serves
**reviewability** — the cost an oversized PR shifts onto everyone downstream of the merge.
Busting the run ceiling means **splitting plan files** (more runs into one branch); busting
the PR ceiling means **splitting the PRD into sibling PRDs** (design.md Phase 5.5). Keeping
them distinct is the point: the single ceiling that conflated the two was exceeded by every
comparable merged PRD and generated a waiver per PRD — a gate that is waived by routine is
a gate that will also be waived on the day it matters ().

---

## Step 7: Flip PRD status to `planned`

The PRD's frontmatter `status:` is **the source of truth** (CLAUDE.md, "Status update on every command run"). Plans existing = the PRD is planned and ready for implementation. Update both, in the **same commit** as the plan files:

1. In `knowledge/prds/NNNN` frontmatter, set `status: planned` and append a `status_history:` entry `- { state: planned, at: < timestamp>, by: plan }`.
   - Only advance if the current status is `designed`. If it is already `planned`/`implementing`/`verified`/`shipped`, leave it (re-running `/fleet:prd:plan` just refreshes the plan files). If it is `stub`/`prd-drafted`, stop — the PRD isn't designed yet.
2. Nothing to stage for the roadmap — it is generated on demand and **not committed**.

`` is **generated** and derives every row from PRD frontmatter — there is no row to hand-edit and no per-artifact link cell to maintain. It is also **gitignored**, regenerated on demand with `python3 knowledge/scripts/gen_roadmap.py`, so there is nothing to stage and no hook to satisfy. The frontmatter `status:` owns the state.

**Tracker: no live mirror — the fleet projects it.** Do **not** mirror to the tracker from this command; planning is a drafting-stage transition and those are **projection-only** (see [``](#) → its tracker-sync section). Once the status-flip commit reaches `main`, the `prd-projection` pass of the fleet's `corpus-sync` loop (`fleet-service`) hands the Issue to **`Implement Queue`** (`planned`) within the sync's interval — `plan` is the last authoring step, so a fully planned PRD goes straight into the runnable pool rather than resting in a state nothing ever released it from. Never read tracker state back.

---

## Step 8: Land it

**The fleet runs this command headlessly too** (the plan lane, `fleet-service`): once a PRD's
design has landed, a driven program's plan mission dispatches `/fleet:prd:plan NNNN` with no
person in the loop. A person at a terminal commits and opens the PR themselves; a headless run
must land what it wrote, exactly as [`prd:blueprint`](blueprint.md) Step 8 does:

- **The branch is `agent/plan-<key>`**, not `agent/design-<key>` or `agent/shape-<key>`: the
  PRD's fill and design already used those under the same key, and their merged PRs would read as
  this run's prior attempt. Find the prior attempt by the branch itself
  (`gh pr list --state all --head "agent/plan-<key>" --json number,state,url,mergedAt` and
  `git ls-remote --heads origin "agent/plan-<key>"`); an open PR is the prior attempt — drive it;
  a **merged** PR counts as this dispatch's landing only when `main`'s `prd.md` now reads
  `planned` or past it, otherwise the branch starts fresh.
- **Commit the plan files and the `status: planned` flip together**, push, open the PR with the
  PRD's key and the word *plan* in its title, and arm the merge the moment it opens:
  `gh pr merge --auto --squash` (never `--delete-branch`, which a merge queue refuses). Drive it
  to `state: MERGED`, not to green: fix a red check at its root cause and rebase a conflict onto
  `origin/main`.
- **The `landed` result document** carries `{kind: prd, id, href, pr, files, summary, changed:
  {status: planned}, open}`; the sync confirms a plan when the served PRD reads `planned`.

A run that cannot bring its PR to merge is `partial`, and the next dispatch resumes the branch.

---

After saving, report:

```
Plans saved:
- knowledge/prds/NNNN (<N> tasks across <M> waves)
  (+ knowledge/prds/NNNN, ... if split for the run ceiling)
- knowledge/prds/NNNN (<N> tasks across <M> waves)

PRD status: <previous status> → planned (frontmatter; or "unchanged — already <status>")

Next step: Run `/fleet:prd:implement knowledge/prds/NNNN` and
`/fleet:prd:implement knowledge/prds/NNNN` (can run in parallel
after contract generation). A split plan family executes in numeric order into one branch.
```

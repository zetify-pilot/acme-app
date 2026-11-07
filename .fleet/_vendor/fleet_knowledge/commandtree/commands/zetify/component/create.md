# Zetify Component Author

You register a **component** — a durable subsystem the product is made of. Components are the *structural* axis of the planning model; slices are *versions* of them.

**Before you write a component file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/capabilities-and-components`.

```
Component (durable — this command)          →  a row in the `slot:components` registry
  └─ Slice (a planning cut — /zetify:slice:create)     →  a row fragment in the `slot:slices` register  →  a tracker label
       └─ PRD (an agent-shift — /zetify:prd:create) →  a plan directory (`slot:planning-model`)  →  tracker issue
```

**A component is permanent and NEVER carries ship-state.** "Audit Log" cannot be shipped, completed, or finished — only a slice (a planning cut that touches it, e.g. *Reviewer-usable audit record*) can. There is no `status:` on a component and there must never be one; `{{target:validate-knowledge}}` rejects a `status`/`state`/`shipped`/`progress`/`health`/`done` column outright. Asserting completion on a durable thing is exactly how a roadmap fills with bars that can never close.

Read [`knowledge/specs/tracking-and-execution.md`](../../../../knowledge/specs/tracking-and-execution.md) → "Durable vs versioned" before writing.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `no-slice` is a hard gate rather than advice — a component is durable, and minting a cut for it here is how a registry fills with bars that can never close. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "component-create",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Register one durable subsystem as a row in the component registry \u2014 a thing that is built, never shipped, and therefore never carries ship-state.",
  "loads": ["components", "entity-model"],
  "requires": [
    "process-spine", "process-interview", "components", "entity-model", "gate", "git-workflow", "tracker-identity"
  ],
  "optional": ["slices", "planning-model", "feature-maps", "file-conventions"],
  "steps": [
    {
      "id": "already-registered",
      "name": "Check it is not registered, and is really a component",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "step-1-check-it"
    },
    {
      "id": "decide-row",
      "name": "Decide the row (converge in one round)",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-2-decide-the-row"
    },
    {
      "id": "write-row",
      "name": "Write the row",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-3-write-the-row"
    },
    {
      "id": "no-slice",
      "name": "Do NOT create a slice",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "step-4-do-not-create-a-slice"
    },
    {
      "id": "confirm",
      "name": "Confirm",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-5-confirm"
    }
  ]
}
```

## What to do

### Step 1: Check it isn't already registered, and that it's really a component

- Read `knowledge/specs/architecture/components.md`. If a component already covers this, **stop** — you probably want a new *version* of it (`/zetify:slice:create`), not a new component.
- Apply the two tests. Both must pass:
  1. **Can you name what it owns?** A directory, a service, a table set. If not, it's a *property* of the system, not a component. Cross-cutting capabilities (e.g. "Anti Hallucination", "Emergence System") are **outcomes** — they get a slice when someone builds one and, if useful, a `knowledge/features/*.md` map. They are not boxes.
  2. **Would you draw it exactly once on the architecture diagram?** If you'd draw it three times, you're looking at three *versions* of one component — register the component, and let the versions be slices.
- If the thing genuinely never finishes and owns real code, it is a component. Continue.

### Step 2: Decide the row (converge in 1 round)

The user's input is: $ARGUMENTS

1. **`id`** — stable kebab-case slug (e.g. `audit-log`). **This is a join key** — a slice's row fragment cites it in its `components` list under `knowledge/slices/rows/`. Renaming it later breaks every slice pointing at it, so pick carefully and don't be clever.
2. **`layer`** — the block it's drawn in. Must be one of the layers already declared in `components.md`. **Do not invent a new layer without asking the user** — layers are the diagram's structure and are owned by them.
3. **`owns`** — comma-separated repo paths this component is the home for. **A path may be claimed by exactly one component** (the validator enforces it), because two owners make the derived coverage reading ambiguous. May be **empty**: this is a *target* architecture, so a component that owns code nobody has written yet is valid and expected.
4. **`depends_on`** — comma-separated component ids this one structurally requires. **Must be acyclic** — a cycle makes the dependency view undrawable. This is the *structural* edge ("A uses B", timeless), distinct from a slice's *temporal* edge ("version X ends before version Y starts").

If a material decision is open, ask **one** question, shaped by the interview card:

<!-- include: process/interview-card.md -->

**If a dispatched run ends on a person's decision anyway** — a fork its brief does not settle —
the park carries the `decision` document, in the card's own fields:

<!-- include: process/decision-document.md -->

### Step 3: Write the row

Add one row to the registry `slot:components` names, in its layer's block, in the row shape
`slot:components` gives — read the header off the file you are appending to:

```markdown
| <id> | <layer> | <the paths it owns> | <the components it depends on> |
```

**Never add a column.** A registry row says what a component *is* and what it *owns* — a
column carrying state is the category error this file exists to prevent.

Then run `{{target:validate-knowledge}}` — it checks id uniqueness and shape, layer membership, `depends_on` resolution, acyclicity, and single ownership of every path.

### Step 4: Do NOT create a slice — and do not write a tracker label

Registering a component does not put anything on the delivery view, and that is correct — a component is not work. Work on it lands in whatever slice ships that work. The component is **recorded for tracker attribution by the check gate's triage verdict** when issues that touch it are released — not by this command writing a label. Readers who need to resolve a path to a component id use `component_of.py <path>` against the registry; that is a read of the architecture, not a tracker write.

There is nothing to date, either: neither the slice register nor the program register has a date column at all.

### Step 5: Confirm

Report the id, layer, owned paths, structural dependencies, and whether a version slice already exists. If none does and the user wants work to start, point them at `/zetify:slice:create`.

---

## Rules

- **A component NEVER carries ship-state.** No `status:`, no completion, no progress. Ship-state belongs to the PRDs its versions hold — never to the component, and never to the slice either (a slice's completion is computed from its PRDs). Validator-enforced.
- **Coverage is derived, never stored.** "Does this have code yet?" is answered by sweeping `owns:` against the tree *at the time you ask*, and is reported as `has code` / `partial` / `none`. It is a point-in-time fact, **not** a completeness claim — completeness is defined by a next version's scope that doesn't exist yet. Never write a coverage reading into the registry.
- **`owns:` is a claim of ownership, not of existence.** Empty or not-yet-written paths are valid.
- **One owner per path.** Two components claiming the same code makes attribution ambiguous.
- **The graph is acyclic**, and a slice's `Depends on` edge is only legitimate if the component graph has the matching edge.
- **Layers belong to the user.** Don't invent one to make a component fit.
- **If it can finish, it's not a component** — it's a slice (a version, or a cross-cutting outcome).

# Zetify Page — Spec

Author (or refresh) the **page-spec** for one web page: the `<PageName>.spec.md`
that lives next to `<PageName>.tsx` and is the human-readable UX contract for that
page — what it's for, what data feeds it, how it's laid out, and **which canonical
canonical catalog components (`slot:ui-contracts`) its intent binds to**. This is the create-axis sibling of
[`/zetify:page:improve`](improve.md) (which *executes* a spec-driven UX change).
This command produces the spec and **stops** — it does not change the page's code.

> A page-spec is **intent, not inventory.** It must never re-list the page's
> imports (an agent reads the `.tsx` for that). It captures the _why_ and the
> _intent → component_ binding, plus the generated **Shared-component conformance**
> block. `slot:ui-contracts` names the sidecar convention and the repo's
> existing exemplars.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. This command authors a contract and changes no code; `/zetify:page:improve` is what acts on it. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "page-spec",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Author or refresh one page's UX contract \u2014 its intent, and the canonical component each pattern on it must resolve to.",
  "loads": ["ui-contracts", "languages"],
  "requires": [
    "process-spine", "ui-contracts", "git-workflow", "gate",
    "process-interview"
  ],
  "optional": ["product-vision", "languages", "file-conventions", "docs"],
  "steps": [
    {
      "id": "author",
      "name": "Author the spec \u2014 intent, then intent-to-component bindings",
      "kind": "author",
      "actor": "coordinator",
      "produces": [
        "page-spec"
      ],
      "body": "what-to-do"
    }
  ]
}
```

## Context to load

- `slot:ui-contracts` — page archetypes + canonical component rules.
- `slot:languages` for the frontend lane — design-system + i18n + eslint conventions.
- `slot:ui-contracts` — the canonical catalog's index; each leaf carries its "Used on these pages" reverse-index.
- `slot:product-vision` — the persona/principle the page serves.

---

## What to do

1. **Resolve the page.** `$ARGUMENTS` is a page name or path. Find the page file where
   `slot:ui-contracts` says pages live. If a `<Name>.spec.md` already exists, read it
   and **refresh** rather than overwrite the authored intent.
2. **Study the page.** Read the `.tsx` (and its page-local files), its route, its
   data hooks, and its tests. Read 1–2 sibling specs as the shape to follow.
3. **Discovery (engage the user, do not invent intent).** Ask about anything the
   code can't tell you — the page's *purpose* (what an operator comes here to do),
   the load-bearing UX decisions that must not silently regress, and the *intent →
   component* bindings (e.g. "this list IS the catalog's `DataTable`"; "these
   tabs ARE the `underline` `Tabs`"). One question per turn, shaped by the interview
   card. For visual questions, sketch in the browser using real theme tokens
   (`frontend/libs/theme/tokens.css`) — same styling discipline as `/zetify:prd:design`.

<!-- include: process/interview-card.md -->

4. **Write the spec** next to the component, in the exemplar structure:
   - `Purpose` · `Data sources` · `Layout (top → bottom)` · **`Canonical-choice
     rules`** (the intent → component bindings, each linking its catalog leaf) ·
     **`How-to`** (the user-facing page id that documents the task this page serves, via
     `slot:docs` — the spec links its how-to; a page with no how-to says so and why) ·
     `Shared-component conformance` (the generated block — leave the
     `composes:generated` markers, the generator fills them) · `UX decisions (do
     not silently regress)` · `i18n` · `Key data-testid`s.
   - **No import inventory.** If you catch yourself listing what the page is "built
     from", stop — bind intent to the canonical component instead.
5. **Run `{{target:generate-page-specs}}`** to populate the conformance block and refresh
   every leaf's "Used on these pages" index. If the page shows drift, note it in
   the Canonical-choice rules as a known follow-up (the fix belongs to
   `/zetify:page:improve`, not here).
6. Print the spec path. A spec authored on its own still ships via **branch + PR**
   (the golden rule — doc-only diffs merge fast, but never direct to `main`); a spec
   authored as part of a code change rides that PR.

---

## What this is NOT

- Not a code change — that's [`/zetify:page:improve`](improve.md).
- Not an import inventory — bind intent to canonical components; never re-list imports.
- Not a test file — your test runner never collects a `.spec.md`.

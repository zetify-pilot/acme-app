---
type: spec
---

# Feature-Doc Reconcile (keeping the maps true to the code)

The feature catalog (the **`feature-maps`** slot) is only useful if it stays true to what ships. Two layers
keep the feature documentation reconciled with the code — the same freshness contract the
architecture docs (the **`architecture`** slot) carry, applied to feature maps.

> **The load-bearing invariant:** a reconciler may correct the **ledger** (facts — does a capability
> exist, is it wired, is its `source_of_truth` path real) but **never the intent** (the `> **Intent.**`
> prose). Code can tell you *whether* a capability exists and *whether* it's reachable; it can never tell
> you *why the feature should exist*. Point an auto-reconciler at the intent and it will "correct" your
> product's reason-for-being into a description of the code — exactly backwards.

## Layer 1 — Per-PR freshness advisory (cheap, standing)

Each feature map declares `source_of_truth:` — the code paths it describes.
`make validate-knowledge`
compares a PR's changed files against every map's `source_of_truth`: a path changed **without** the map
being touched raises a **non-blocking advisory** (never fails the build — a note to reconcile, exactly
like the architecture docs). It catches drift at the moment it's introduced, for near-zero cost.

**Wiring** (deferred where it collides with in-flight work — see below):
- **CI** — add a non-blocking step running `python3 knowledge/scripts/fleet.py check --base origin/main --repo .`
  (advisory only; mirrors the `validate-arch-docs` non-blocking advisory).
- **Local (optional)** — a `pre-commit` hook of the same, non-blocking.

## Layer 3 — Exhaustive source_of_truth coverage 

Layer 1 can only ever be as good as the path list it reads. A map whose `source_of_truth:`
omits its own substrate is a **blind spot with a green light on it** — the advisory cannot
fire, so the absence of one reads as "nothing changed here." That is how `observers.md`
stayed green while `observation_facts` held 0 rows platform-wide , because
the root cause lived in a query file no map claimed.

Layer 3 **inverts the contract**: instead of every map declaring what it depends on (and
nothing checking that list for completeness), **every code path must be claimed** — by some
map's `source_of_truth:`, by an explicit exclusion, or (while a burn-down baseline is still
committed) by that baseline.

`make validate-knowledge` enforces it (its journey rule, at pre-commit and in CI, via
`python3 knowledge/scripts/validate_journeys.py` — the `journeys-and-features` check):

- **Coverage roots** — the code paths `slot:feature-maps` declares as covered ground.
  Every file under one of these must be claimed, excluded, or baselined.
- **Reviewed exclusions** — the paths `slot:file-conventions` carves out: tooling
  that is not product, scripts, tests, every generated tree (`slot:codegen`),
  vendored code, and test-only and generated leaves. Each is a deliberate carve-out named in
  one place, never a silent skip.
- **The baseline (retired once at zero)** — the unclaimed-paths baseline was a
  generated, committed burn-down queue: one path per line, tolerated as *known debt*. Once a
  corpus burns it to zero it deletes the file, and the check becomes **absolute** :
  a missing baseline means *zero acknowledged debt*, so an unclaimed covered path is a hard
  failure, never a skip. While a baseline file exists it may shrink, never grow — a PR that
  net-adds lines fails unless an equal number is removed in the same diff (burn-down) or the
  addition carries a `# ack: <path> <reason>` line. `--write-baseline` refuses to re-seed a
  debt list once the gate is absolute.
- **Hard failure** — a covered path in *none* of those fails the commit.
- **Rule A (first ratchet rule)** — a map with non-empty `surfaces:` must declare at least
  one `frontend/` path in `source_of_truth:`. A map with real routes and no frontend path
  is the exact filed defect; a map that rides a generic surface declares `surfaces: []`
  and is exempt.

The blocking half is deliberately narrow so a failure is always a real gap — the failure
mode that killed the previous signal was an advisory nobody read, so the check never fires
on noise (tests and generated code are excluded, not baselined).

## Layer 2 — The reconcile sweep (the scan)

A scheduled **Routine** runs the deep sweep over the whole catalog — the feature audit's **graph lane**
(the **`audit-profile`** slot's feature checklist F3/F4/F5) reconciling three ways:

- **row → code** — every capability has a real backing surface (route / handler / MCP tool / action). A
  row with none is aspirational-marked-as-shipped.
- **code → row** — every product surface maps to *some* capability. An undocumented route/tool/action is
  **stranded backend** → propose a new row.
- **Ships-in → runtime** — the PRD reads `shipped` but no composed path exists (a composition failure).

It **auto-opens a PR** for factual drift only (missing/stale rows, moved `surfaces` routes, renamed
`source_of_truth` paths, broken links caught by `make validate-knowledge`), and **flags** — never edits —
suspected intent overstatement for a human. It runs as a **Routine** (a scheduled agent invoking the
sweep), the same mechanism as the architecture reconcile routine — because the
fleet daemon routes only by issue `Type`, a doc-reconcile loop has no daemon route.

## Layer 4 — The docs layer (the `docs` slot)

The two maps above describe **this repository's own corpus**. The product's **user-facing
documentation** is a third catalog, and it carries the same freshness contract — but its home
is not fixed. The `docs` slot names one or more homes (each with audience and visibility),
what a page must carry, how it is built, published and verified, and which parts are
**generated**. Read that answer first; this layer never assumes a path.

- **Page → code.** Each page carries a `source_of_truth:` list — the code paths it describes.
  A changed file that one of those paths names, without the page being touched, is the same
  **non-blocking advisory** Layer 1 raises for a feature map: reconcile the page, do not fail
  the build. The advisory is emitted per page, from the docs home the slot names.
- **Generated references.** A home the `docs` slot marks **generated** is refreshed by
  **running the generated-reference target the slot names** — never hand-edited. A hand edit
  to generated docs is a defect, not a fix (the same rule `slot:codegen` carries for code).
- **Page → capability, both directions.** A page that **promises** something the product does
  not do is a **docs defect**: the reconcile corrects the page to what ships. It is **never** a
  request to build the feature — that would invert the loop and let the docs drive scope. A
  shipped capability with **no page, or a wrong page**, is a **docs defect** as well: propose
  the page (or the correction) the way Layer 2 proposes a missing feature row.
- **Retire with a redirect.** A page for a capability that is retired (a cancelled PRD, a
  removed surface) is retired by the reconcile, which leaves a **redirect** at the old address
  — the redirect shape is the `docs` slot's, never a second invented convention.

**Degrade.** When the repository leaves the `docs` slot unfilled there is no home to reconcile
and no audience contract to hold a page to, so this layer does nothing and reports why. It is
optional: an unfilled slot is a smaller sweep, never a broken one — the same rule every
optional slot carries.

## Division of labor (the symmetry)

- **Reconcile (this)** keeps the docs true to the **code** — facts don't drift *downward*.
- **The feature audit** keeps the code true to the
  **docs** — the shipped surface delivers the stated intent, *upward*.

Same graph, opposite directions. Reconcile is the nightly machine pass (facts); the feature audit is the
human-grade pass (intent + capability conformance). Together they close the loop the catalog exists to
enable.

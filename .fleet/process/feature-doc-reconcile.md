---
type: spec
---

# Feature-Doc Reconcile (keeping the maps true to the code)

The feature catalog (the **`feature-maps`** slot) is only useful if it stays true to what ships. Two layers
keep the feature documentation reconciled with the code — the same freshness contract the
architecture docs (the **`architecture`** slot) carry, applied to feature maps.

**Before you write a feature map file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/feature-areas`.

> **The load-bearing invariant:** a reconciler may correct the **ledger** (facts — does a capability
> exist, is it wired, is its `source_of_truth` path real) but **never the intent** (the `> **Intent.**`
> prose). Code can tell you *whether* a capability exists and *whether* it's reachable; it can never tell
> you *why the feature should exist*. Point an auto-reconciler at the intent and it will "correct" your
> product's reason-for-being into a description of the code — exactly backwards.

## Writing a feature brief — every map that is created or edited

A feature map carries a **brief**, so a newcomer understands the feature in about thirty seconds,
and its `## Capabilities` table is cut into **uses** — the things a person can do with the
feature. Every command that creates a map, adds or moves a capability row, or reconciles maps
follows this section; the commands point here and never restate it. The reader that parses the
shape is `fleet_knowledge.featurebrief`; `fleet check --only feature-briefs` (part of
`(python3 knowledge/scripts/fleet.py check --repo . && python3 knowledge/scripts/validate_requirements.py && python3 knowledge/scripts/validate_id_collisions.py)`) judges it.

**The shape.** In the frontmatter:

```yaml
brief:
  summary: >-      # ONE sentence: what it is, and for whom
  problem: >-      # 2-3 sentences: what goes wrong without it, and why that matters
  example: >-      # 3-4 sentences: a named person doing a real job with it
  example_from: [journey-slug]   # the journeys the example is drawn from; each must exist
  not:             # 1-3 lines: what it is NOT — name the neighbouring feature
    - ...
```

Under `## Capabilities`, `### <use>` sections. Each heading is a thing a person does
(*Decide what it may see*), followed by **one plain paragraph of one or two sentences**, then that
use's table rows. A row's use is the section it sits in — there is no list of capability ids
anywhere else. *Who uses it* (the covering journeys' personas) and *where it lives* (`surfaces:`)
are derived when the map is read; never author them. **A sub-feature is a use**, never a map of
its own: *Sign in with SAML* is a use of the sign-in feature, beside *Sign in with username and
password*, *Sign in with your company's provider* and *Manage your sessions*. **A use that outgrows
its feature becomes a feature** — when it needs a brief of its own to be understood, or an owner
of its own, or its feature would need a seventh use to hold it. That is a new map, proposed as a
new feature (moment 1) and confirmed by a person — never split silently; its rows move whole,
keeping their ids. The `> **Intent.**` stays where it is: it is
the engineer's testable claim and the brief sits above it — never delete or rewrite it to fit the
brief.

**The words.** The brief and every use paragraph follow
[*Wording a promise*](knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion), the plain-language rule in
[*Writing for people*](writing.md) → *Write for a reader who does not know the code*, and four rules more, which the check enforces:

- **No ship-state, ever** — never "shipped", "partly built", "still open", "planned". Progress
  is read from each PRD's `status:`; a brief that says it goes stale the day the next PRD lands.
- **No bare internal ids** in the prose — no program, slice, issue, capability or PRD number.
  Explain an unavoidable term in one clause.
- **No restated commitments.** A rule the product promises is a register row; cite its row id
  (`<PREFIX>-NNN`), never paraphrase it.
- **The example is a real job, drawn from a journey the map links** — a named, fictional person
  doing one thing end to end, and that journey's slug in `example_from`. A new area with no
  journey yet draws the example from the work that creates it and leaves `example_from: []`; the
  first journey that covers the area adds itself there.

**Which one is it?** A new thing is a *capability* when an existing use already covers its ground, a *use* when it is a main thing people do that no use says (and no use of the map already says it), a *feature* when it needs its own brief or owner or does not fit any use of the map, and a bug or task when it is broken or a small change. The customer-facing version, with examples, is *Features, uses and capabilities*; keep the two in step.

**The five moments.**

1. **Creating a map.** Write the whole brief and its uses in the same change that creates the
   map — `new_feature_area.py` takes each use as `--use "Name|Paragraph"` and the brief as
   `--brief-json '{"summary": …, "problem": …, "example": …, "example_from": [...], "not": [...]}'`. Cut the uses from what a person will do with the feature, not from the
   components or the PRDs that build it. An attended command confirms the summary and the uses
   with the person **inside the interview round it already runs** — one question showing both,
   never a new step; a headless run writes them from the accepted proposal and names them in its
   summary.
2. **Adding a capability row.** Put it under the use it serves. When it fits none: add a use only
   when the new use is a real thing a person
   does, written with its paragraph. Otherwise the feature is mis-cut — do not stretch a use or
   invent one. Put the row under a final `### Misfits (to move)` section and raise it: attended,
   ask the person in the round you are already in; headless, file a task (`file_issue`) naming
   the map, the row and why no use fits, and say so in the summary. A row that belongs to
   another feature goes in that feature's map instead.
3. **Editing a map that has no brief yet** — any edit, a single `Ships in` flip included. Write
   the brief and cut the existing rows into uses **in the same change**: the check holds every
   new or modified map to a valid brief with all its rows under uses, so the commit fails
   otherwise. Move whole rows between sections; never edit a row's cells while re-cutting, and
   never renumber an id. A row that fits no use goes under `### Misfits (to move)`, named in the
   summary with where it belongs.
4. **Reconciling.** The brief obeys the load-bearing invariant above. A reconciler keeps the
   *facts* true — a use paragraph that no longer describes its rows, a use left with no rows
   (merge or remove it), an `example_from` naming a renamed or retired journey, a `not` line
   naming a sibling that was renamed — and **never** rewrites the `summary` or `problem`, which
   are the feature's reason for being: suspected drift there is flagged for a person, exactly
   like the Intent. Nothing a reconcile writes may add ship-state to a brief.
5. **Taking in what a person adds** — a new use, a request that extends a use, a plan's slices
   and pieces of work. Before you propose it, check it against the feature as it stands:
   - **Read the brief and every use paragraph first**, the `not` lines included. If a use
     already says what the person asked for, the request extends that use: propose it there
     and add no use. If a `not` line names a sibling feature for it, it belongs in that
     feature.
   - **Flag a near-duplicate, never add it silently.** A new use whose name or paragraph says
     what an existing use says in other words, or a piece of work an existing row already
     covers, is named on the card ("this reads like *Refund a payment*, which the feature
     already does") with that use offered first. Headless, say it in the proposal's
     `whatItIs` and propose the existing use.
   - **Reword it to the standard, keep its meaning.** Use the person's own words where they are
     plain; rewrite the rest to [*Wording a promise*](knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion):
     a use name of a few words with a verb first, a paragraph of one or two sentences, no code,
     no ids, no ship-state, every exception they stated kept. The card shows the reworded text,
     so the person accepts the words that will be written.
   - **A plan's words follow the same standard.** `delivers` and `doneWhen` are one plain
     sentence each, and each piece of work is a short title plus one sentence. The capability
     row a plan writes reuses that title as its name and that sentence as its sentence, so the
     feature's page and the PRD stub read the same.

## Plain titles — every capability row and every PRD that is created or changed

The Handbook's detail panel names each capability and each PRD by a short **plain title**, and falls back to
the long knowledge-base name only where none is written. The fleet writes the title **once, when it writes or
changes the row**, and keeps it true afterwards. A row or PRD written without one is incomplete work.

- **Where it lives.** A capability row: the optional **`Plain`** column of the map's table — always the
  **last** column, after `Anchor`, `Needs` and `Source of truth` (declare all four, padding the unused cells
  with `—`; the checks read those three by position). A PRD: the optional **`plain_title:`** frontmatter key.
  Absent means "no title written"; nothing derives one.
- **The rule.** At most **60 characters**; plain words; **no brackets, arrows, slashes or ids** (`CAP-`, a PRD
  number, a file path, a command); and it says **what a person can do or get**, not what the system is or how
  it works. *"Let an agent earn more freedom as its record improves"*, not *"Earned-autonomy lifecycle
  (shadow/canary → metrics-gated autonomy promotion)"*.
- **When the row changes.** Re-read the title whenever you change what the capability or PRD promises (its
  `Capability` text, the PRD's `title:`); a title that no longer says what the row does is a defect. A
  mechanical edit (a `Ships in` flip, a `Tested by` link) leaves it alone.
- **Never invent one by script.** A title is written by the model that has read the row.

## Layer 1 — Per-PR freshness advisory (cheap, standing)

Each feature map declares `source_of_truth:` — the code paths it describes.
`(python3 knowledge/scripts/fleet.py check --repo . && python3 knowledge/scripts/validate_requirements.py && python3 knowledge/scripts/validate_id_collisions.py)`
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
stayed green while `observation_facts` held 0 rows platform-wide, because
the root cause lived in a query file no map claimed.

Layer 3 **inverts the contract**: instead of every map declaring what it depends on (and
nothing checking that list for completeness), **every code path must be claimed** — by some
map's `source_of_truth:`, by an explicit exclusion, or (while a burn-down baseline is still
committed) by that baseline.

`(python3 knowledge/scripts/fleet.py check --repo . && python3 knowledge/scripts/validate_requirements.py && python3 knowledge/scripts/validate_id_collisions.py)` enforces it (its journey rule, at pre-commit and in CI, via
`python3 knowledge/scripts/validate_journeys.py` — the `journeys-and-features` check):

- **Coverage roots** — the code paths `slot:feature-maps` declares as covered ground.
  Every file under one of these must be claimed, excluded, or baselined.
- **Reviewed exclusions** — the paths `slot:file-conventions` carves out: tooling
  that is not product, scripts, tests, every generated tree (`slot:codegen`),
  vendored code, and test-only and generated leaves. Each is a deliberate carve-out named in
  one place, never a silent skip.
- **The baseline (retired once at zero)** — the unclaimed-paths baseline was a
  generated, committed burn-down queue: one path per line, tolerated as *known debt*. Once a
  corpus burns it to zero it deletes the file, and the check becomes **absolute**:
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
  **stranded backend** → propose a new row, worded to
  [*Wording a promise*](knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion) (one plain sentence, code names in Evidence).
- **brief → rows** — every use paragraph still describes the rows under it, no use is empty, and
  the brief's `example_from` and `not` name things that exist — [*Writing a feature
  brief*](#writing-a-feature-brief--every-map-that-is-created-or-edited), moment 4.
- **Ships-in → runtime** — the PRD reads `shipped` but no composed path exists (a composition failure).

It **auto-opens a PR** for factual drift only (missing/stale rows, moved `surfaces` routes, renamed
`source_of_truth` paths, use paragraphs out of step with their rows, broken links caught by
`(python3 knowledge/scripts/fleet.py check --repo . && python3 knowledge/scripts/validate_requirements.py && python3 knowledge/scripts/validate_id_collisions.py)`), and **flags** — never edits — suspected intent overstatement, in the Intent
or in the brief's `summary` and `problem`, for a human. It runs as a **Routine** (a scheduled agent invoking the
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

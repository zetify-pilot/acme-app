# The feature flows — new feature, new use, plan, the brief, removing a use, and where a feature request goes

> The one guidance doc for the six front doors a repository that **plans by area** offers
> (`planning_mode.py` prints `areas`). `intake`, `route` and `slice:create` each read the part
> that names them; none restates it. The shapes are enforced by the fleet as the result lands
> (`dispatch.results`), so a document that breaks one is refused and never reaches a person.
> In a repository that plans by program none of this applies: there is no feature to place in.

**The person reads every card these flows produce, and they are a customer.** Every question,
option, brief and plan names the **feature and the use in words** — never an id (no program,
slice, issue, capability or PRD number; the fleet refuses a card that carries one), never a
command, never Fleet's internal steps. Address it to them: a question these flows ask goes to
the person who filed, never to "the fleet's operators". A **feature** is a feature map; a
**use** is one `###` section of its `## Capabilities` — a thing a person can do with it.

**No flow here creates or names a program.** A plan is one to three slices under the feature;
work bigger than that is more slices, ordered by `Depends on`.

## The requests

The filing's brief says which one it is: a pre-placed filing carries a `## Request` block, and
every intake or route dispatch in this mode carries a `## Features` block — each feature as
`### <slug> · <name> — <summary>`, then each use as `- <name> — <paragraph>`. **Match and
offer only what `## Features` lists**: it is what the feature pages show, and an option naming
a feature or use it does not list is refused.

| request | how it arrives | who runs | what route proposes |
|---|---|---|---|
| **feature request** (no `## Request`) | the person typed what the product should let them do | `intake`, then `route` | per the confirmed `placement` (below) |
| **new feature** (`{"kind": "newFeature"}`) | a name (the filing's title) and two or three sentences, from the Features page | `route` directly — no interview | `kind: area`: the feature's map only |
| **new use** (`{"kind": "newUse", "area"}`) | "+ Add something this feature should do" on a feature's page: a name (the filing's title) and one sentence | `route` directly — no interview | `kind: use` carrying `newUse`: one new use on that feature's map |
| **plan** (`{"kind": "plan", "area", "use"}`, `use` null = the whole feature) | "Plan this" on a use, or "Plan the whole feature"; and Fleet itself, once, when an accepted new use lands | `route` directly — no interview | `kind: slice` carrying `plan` |
| **remove a use** (`{"kind": "removeUse", "area", "use"}`) | "Remove this use…" on a use already on a feature's page; the text is the person's reason | `slice:create` directly — Fleet accepts the removal for the person, who already confirmed it with the reason | nothing: there is no proposal to check |
| **write the brief** (`{"kind": "writeBrief", "area"}`) | "Write the brief" on a feature whose map has no brief or no uses; the text, when there is any, is the person's note (it may name one more thing the feature should do) | `route` directly — no interview | `kind: brief` carrying `featureBrief`: the brief, and the map's rows sorted into uses |

A new feature, a new use, a plan and a brief are **pre-placed**: the person already said where the work goes, so
there is no interview and no placement question. Route may ask **at most two** questions across
the run (instead of its usual one), each one the person could not have answered by pressing the
button they pressed — never "is this really a new feature?".

## Feature request: the placement question comes first

**`intake`'s round one is always the placement question**, before any other question, and it
does not count toward the eight-question ceiling or the round limit — it is Fleet's question,
not a gap the filer left. One question in the set, `"kind": "placement"`:

```json
{"id": "placement", "kind": "placement", "prompt": "Where does this go?", "allowFreeText": true,
 "options": [
   {"id": "p1", "label": "Extends <Feature> → <Use>", "then": "Fleet shapes your request inside <Use>.", "recommended": true,
    "placement": {"choice": "extends", "area": "<slug>", "areaName": "<Feature>", "use": "<Use>",
                  "useParagraph": "<the use's paragraph>", "fit": "strong", "why": "Why here: <evidence from their words>."}},
   {"id": "use", "label": "A new thing <Feature> does: <drafted name>", "then": "Fleet adds it to <Feature>, ready to plan.", "recommended": false,
    "placement": {"choice": "newUse", "area": "<slug>", "areaName": "<Feature>",
                  "newUse": {"name": "<drafted use name>", "paragraph": "<one or two plain sentences>"}, "why": "<why this feature>"}},
   {"id": "new", "label": "A new feature: <drafted name>", "then": "Fleet drafts the new feature for you to check.", "recommended": false,
    "placement": {"choice": "new", "newFeature": {"name": "<name>", "summary": "<one sentence>", "uses": ["<use>", "..."]},
                  "whyNot": [{"area": "<slug>", "areaName": "<Feature>", "why": "<why it does not fit>"}]}},
   {"id": "not", "label": "Not a feature: it's broken", "then": "It goes to the bug sheet with your words.", "recommended": false,
    "placement": {"choice": "bug", "why": "<what you read that says so>"}}
 ]}
```

- **Options, in this order:** the best-matching feature → use; **at most one** "A new thing
  <Feature> does" (`newUse`) — when the best feature plainly fits but none of its uses does,
  drafted as a use name and one or two plain sentences; **up to two** alternative feature → use
  pairs (with the new thing, at most three options name an existing feature); **at most one**
  "A new feature"; **exactly one** "Not a feature" — a `bug` ("it's broken") or a `task`
  ("it's a small change"), whichever the words read as. Two to five options; this is the only
  question allowed a fifth. When the card is full, the new thing takes "A new feature"'s place
  only when that feature clearly fits; otherwise it takes an alternative's.
- **Matching:** read the top candidates' summaries and each use's paragraph; a feature's
  `brief.not` lines name its siblings on purpose and break ties. `fit: strong` when the
  request plainly does what the use's paragraph says; else `weak`.
- **Which one is `recommended`:** the best match when its fit is strong; the new thing when the
  feature fits strongly and no use does. When none is strong,
  "A new feature" — but only after the new-feature gate below: if you cannot write a `whyNot`
  for a close feature, the request goes under that feature and that option is recommended.
  When the words describe a defect or a small change to something that exists, "Not a feature".
- **The `brief`** says in two plain sentences what you read the request to be and that nothing
  is created yet. **A repository with no feature map** asks no placement question at all.

**On resume**, copy the answer into the dossier as `placement`:
`{"choice", "area"?, "areaName"?, "use"?, "newUse"?, "newFeature"?, "confirmedBy"}` — the option they
picked; free text ("somewhere else") is re-matched against `## Features` and asked once more
only if it still fits nothing. Then:

- **`extends`** — shape the rest of the interview inside that feature and use; ask nothing the
  use's paragraph already answers.
- **`newUse`** — ask nothing more and write the dossier; route turns it into the new-use
  proposal below, its name and paragraph the option's draft.
- **`new`** — ask at most one more question about the new feature itself, then write the
  dossier; route turns it into flow 1's map-only proposal and the request becomes one of its uses.
- **`bug` / `task`** — emit the `handback` with that `looksLike`, quoting their own words.

## What route proposes, by request

**Route is bound by the confirmed `placement` and by the `## Request`.** A proposal that
contradicts either is refused as it lands (`proposal-placement-mismatch`) and route is sent
back once with the reason.

- **placement `extends`** — `under` names `area:<slug>` (`existing`); add the optional
  `"use": "<Use>"`. Size it as usual (slice, PRD, task), never a new feature.
- **placement `newUse`, or a new-use request** — **`kind: "use"`** carrying **`newUse`**:
  `{"area", "areaName", "name", "paragraph"}`, `under` naming `area:<slug>` (`existing`) then
  the use as `{"id": "new use", "name": "<name>", "meta": "use", "status": "new"}`, and nothing
  else — no slice, no piece of work. Draft it by *Writing a feature brief* → moment 5 (*Taking
  in what a person adds*, `feature-doc-reconcile.md`): a thing a person does, named in a few
  words with a verb first ("Reserve parts for a repair"), and one or two plain sentences saying
  what they do with it and why — the person's own words where they are plain, from a placement
  the option's draft. Never ship-state words ("shipped", "planned", "partly built", "still open"
  — the map's check refuses them, so write "a booked repair", not "a planned repair").
  **Flag a near-duplicate, not only an exact name**: when an existing use's name or paragraph
  already says this in other words, a new-use request spends its question on it ("This reads
  like *Book a repair*, which the feature already does — add it there, or add it as a new
  thing?"), and the placement card offers that use as `extends` instead of a new thing. The
  fleet refuses only an exact name (case folded); the near-duplicate is yours to catch.
  **Every option of that question carries its `placement`** — `{"choice": "extends", "area",
  "use"}` on "add it there", `{"choice": "newUse", "area", "newUse": {"name"}}` on "a new
  thing" — because **the person's answer outranks the request**: the fleet reads the picked
  option's `placement` off the held, answered question and judges the proposal by it. Answered
  `extends`, propose as for **placement `extends`** above (inside that use, never a new use —
  a new use is refused as it lands); answered `newUse`, the new use.
  `onAccept.command` is `slice:create`, which adds the use to the map. However many uses
  the feature already has, a new one is added the same way.
- **placement `new`, or a new-feature request** — **`kind: "area"`** carrying `newArea`
  (`slug`, `name`, `sentence`, `whyNoExistingArea`, `brief`, `uses` — the same shape and the
  same fourth gate a `newArea` on a slice carries), `under` holding exactly the new
  `area:<slug>` node, and **no slice**. Draft the brief to the feature-brief schema
  (`summary`, `problem`, `example`, `example_from`, `not`) and **uses**, each a
  thing a person does, with one plain paragraph — every word by *Writing a feature brief* →
  moment 5. `onAccept.command` is `slice:create`, which writes the map. Derive the slug and name from the person's name for it.
  **Numbered requirements are the person's own and none may vanish.** When the filing's text
  holds lines numbered `R1`, `R2` and so on, every such number goes on the use that delivers it,
  as `covers` (`{"name", "paragraph", "covers": ["R2", "R5"]}`). A requirement you cannot place
  on any use stays out of every `covers`: the Handbook shows it to the person, who adds it or
  leaves it out. Never drop one silently, and never list a number on a use that does not deliver it.
- **a plan request** — `kind: "slice"` carrying **`plan`**:
  `{"area", "areaName", "use" (null for the whole feature), "slices": [{"name", "delivers",
  "doneWhen", "prds": [{"title", "sentence"}]}]}`, one to three slices in build order, each
  with one to six pieces of work. `under` names `area:<slug>` (`existing`) then the slices as
  `new`. **This is the one proposal that names its new entities and writes a `Done when`**:
  the person asked for a plan, and a plan is exactly those words. Each slice is still a cut
  that completes — `delivers` is what a person can do once it is done, `doneWhen` one
  observable sentence — and holds the work the ladder puts in a slice (two or more pieces,
  unless the use is genuinely one piece of work). A plan for the whole feature covers every
  use that has open ground, in the order a person would want them. Its words — `delivers`,
  `doneWhen`, each piece's title and sentence — follow *Writing a feature brief* → moment 5, and
  a piece an existing capability row already covers is named, never planned twice.

- **a write-the-brief request** — **`kind: "brief"`** carrying **`featureBrief`**:
  `{"area", "areaName", "brief": {"summary", "problem", "example", "example_from", "not"},
  "uses": [{"name", "paragraph", "rows": ["<row id>", ...]}]}`, `under` naming `area:<slug>`
  (`existing`) then `{"id": "brief", "name": "The brief and its uses", "meta": "brief", "status":
  "new"}`, and nothing else. Read the feature's map: its Intent, its existing brief and use
  paragraphs where it has them, and every capability row. Draft the brief to the feature-brief
  schema and **sort every live row** (each row outside `### Misfits (to move)` and `### Retired`)
  **into uses** — fewer for a small map: one or two when it has fewer than three rows,
  none needed when it has none — each a thing a person does, with one plain paragraph, every word by
  *Writing a feature brief* → moment 5. **Rows are only regrouped**: name each by its id, every live
  row in exactly one use; never reword, renumber, add or drop one — the fleet refuses a sort that
  misses, repeats or invents a row. A use that fits an existing `###` keeps its name. When the
  person's note names something the feature should also do that no row covers, add it as one more
  use with `"rows": []`. `onAccept.command` is `slice:create`, which writes the brief into the map.

**The person may edit before accepting** — the new feature's name, sentence, brief and uses,
the new use's name and paragraph, the brief and the uses of a feature's brief (including which
use a row sits in), or the plan's slices — and the accepted proposal carries their words. Write from the proposal
the brief carries, never from your memory of the draft.

## What `slice:create` writes from an accepted proposal

- **`kind: "area"`** — **only the feature map**: run `new_feature_area.py` with `--brief-json`
  and one `--use` per use, exactly as for a `newArea` on a slice, and write **no slice row**. A
  feature with no code yet passes no component and no code path (slice:create's writer notes).
  Land it by one merged PR and report `created`:
  `{"kind": "area", "id": "<slug>", "name": "<name>", "href": "areas:<slug>", "pr": "<url>"}`.
- **`kind: "use"`** — **only the new use**: run
  `python3 knowledge/scripts/new_feature_use.py --area "<newUse.area>" --name "<newUse.name>"
  --paragraph "<newUse.paragraph>"`, which adds it to the map as a `###` section with an empty
  table, and write **no slice row and no capability row** — its work arrives with the plan made
  for it from the feature's page. Land it by one merged PR and report `created`:
  `{"kind": "use", "id": "<area>", "name": "<newUse.name>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "brief"`** — **only the brief and the uses**: run
  `python3 knowledge/scripts/write_feature_brief.py --area "<featureBrief.area>" --brief-json
  '<featureBrief.brief as JSON>' --uses-json '<featureBrief.uses as JSON>'`, which writes the brief
  into the map's frontmatter and moves each row, byte for byte, into the use that names it (notes
  that sat between the old tables move to a `## Notes` section). Write **no slice row and no new
  capability row**. Land it by one merged PR and report `created`:
  `{"kind": "brief", "id": "<area>", "name": "<areaName>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "removal"`** (a remove-a-use request; Fleet wrote the proposal, `removeUse`: `{"area", "areaName",
  "use", "why"}`) — **only the removal**: run `python3 knowledge/scripts/remove_feature_use.py --area
  "<removeUse.area>" --name "<removeUse.use>" --reason "<removeUse.why>"`. It takes the use's `###` section off the
  map and moves every table it held, byte for byte, to `### Retired` (built work stays on the page, retired; nothing
  is deleted), and cancels each plan under the use that is not built yet the way `prd:cancel` Step 2 does, with the
  person's reason. Write nothing else: no row, no slice, no reworded line. Its last stdout line says what it retired,
  cancelled and kept; put that in the PR description in words. **When it exits 3**, work under the use is being built
  right now: ask the person **one** question — stop that work and remove the use, or keep the use (withdraw the
  removal) — and on "stop it" run it again with `--stop-work-being-built`. **When it exits 2**, end the run with its
  sentence as the summary, a question to the person; their note, or withdrawing the request, is the answer. Land it by
  one merged PR and report `created`:
  `{"kind": "removal", "id": "<area>", "name": "<removeUse.use>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "slice"` with `plan`** — one slice row per `plan.slices` entry, in order, each in
  `plan.area`, `Depends on` chaining them in build order, `Done when` the entry's `doneWhen`
  verbatim; and under each, one **PRD stub** per `prds` entry, written the way `prd:create`
  writes a stub from an accepted proposal (`status: stub`, the entry's title and sentence as
  the brief, the slice and area named, nothing else) — and it **records the use in the stub's
  frontmatter as `use:`** (the use `plan.use` names; for a whole-feature plan, the use that
  slice serves). **And one capability row per piece of work** in the area's map, under that use's
  `###` section: a fresh `CAP` id from the allocator, the capability cell
  `**<title>** — <sentence>`, reworded only to meet the standard, `Ships in` the piece's PRD stub number, `Tested by` `—`. That row is what
  makes the use read as planned work, with its slices under it, the moment the PR merges — and
  stops the page offering "Plan this" again. One merged PR for all of it; report `created` for the first slice with the rest under `"also":
  [{"id", "name", "href"}]`. The pieces of work then go through the usual fill, design and
  build.

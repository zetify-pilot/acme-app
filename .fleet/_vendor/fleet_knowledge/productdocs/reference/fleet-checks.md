---
title: "Fleet checks"
kind: reference
for: [everyone]
summary: "Every check fleet check runs over a knowledge base, and what each one holds."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/checks
generated: true
---

:::lede
Every check `fleet check` runs over a knowledge base. Look a check up here when it reports a finding, or to decide whether to turn it off.
:::

Run one with `fleet check --only <name>`; a repository turns one off by listing its name in `disabled_checks` in `.fleet/fleet.toml`. `tracker-clients` is mandatory and cannot be turned off, and a name that matches no check is refused rather than ignored. A check over ground the repository does not have skips rather than fails.

## Checks

| Check | What it checks | Why |
|---|---|---|
| `arch-docs` | Architecture-doc freshness | Architecture prose has no codegen and no natural update trigger, so it rots silently as the code it describes moves on. |
| `bars` | Bars are well formed and bound | A completion reading is arithmetic over artifacts in git, so it can read complete on a day the promise is broken in the running product — a shipped artifact proves a capability exists, never that it is connected. |
| `command-contracts` | every slot, slug and spec a command names resolves | Requires every slot citation to name a question the questionnaire asks; resolves each spine's `sop` to a shared-tier slug and each critique rubric's `spec` to a file and heading the tier carries; and requires every shared-tier document to be the fill of exactly one shared slot. |
| `command-portability` | commands ask only for what a repo can answer | A command is a portable procedure. |
| `command-render` | a foreign render of the commands this repository ships carries no home-project or vendor text | Every markdown file in the shipped set (`tier: core` commands — the whole tree for `set = "all"` — plus the shared documents they link) is rendered as a customer install would receive it — namespace `acme` and the customer default, home segments dropped — and scanned for a prior-vendor name other than the command prefix, a corpus path outside the fixed layout, or a dated incident. |
| `commitment-coverage` | Commitment coverage | A register declares which prose it is the constraint axis for. |
| `components` | Component registry | The component registry is the structural map: what exists and where a thing belongs. |
| `docs-coverage` | docs coverage — every surfaced capability has a page | A capability whose feature area declares a surface needs a page: one whose `covers` names it, a feature map's `Documented in` cell, a journey's `documented_in:`, or a PRD's `docs_impact`. |
| `docs-pages` | docs pages — frontmatter, ids, links and secrets | Each page in a `docs` home names one of the four kinds and resolves its `covers`, `verified_by` and internal links; a public home carries no secret shape or internal hostname; a generated page names a source that exists; and a PRD's `docs_impact` is either resolvable pages or `none` with a reason. |
| `environment-records` | Environment records hold secret references, never secret values | Every credential in a record under knowledge/environments/ is a secret-store reference (sm://… or fleet-secret://…); a literal value under a password, token, login or other credential key fails the build, because the desk would serve it to every signed-in reader. |
| `feature-briefs` | Feature briefs are well formed | A feature map's brief is what a newcomer reads first, and its uses are how its capabilities are cut. |
| `fleet-layout` | Fleet's configuration is in .fleet/fleet.toml, with its targets table | Fleet keeps its configuration in `.fleet/fleet.toml` and what each conventional target runs in its `[fleet.targets]` table; nothing of Fleet's sits at the repository root. |
| `id-collisions` | Id collisions | Ids in an append-only register are permanent identities, and two branches can mint the same one without producing a single merge conflict — the counter line resolves cleanly and one branch's row silently inherits the other's identity. |
| `journeys-and-features` | Journeys & capability maps | The product-facing decomposition and its links: capability ids allocated once and never reused, the `Needs` dependency graph acyclic, `Ships in` resolving to real PRDs, the PRD↔journey reference edge resolving in BOTH directions (a PRD's `journeys:` entries to journey files; every AC section's parenthesised PRD citations to PRD folders), journey `covers:` and capability `Tested by` agreeing in BOTH directions, a map's `composes:` and a flow's `used_by:` agreeing in BOTH directions (an edge declared on either side must be declared on the other), every AC disposition and deferral agreeing with the cited PRD's live `status:` (a cite hidden in a multi-id paren is read too, and an `N/A until PRD NNNN ships` row for a shipped PRD fails), declared surfaces resolving to real routes, every code path under a covered root claimed by some map's `source_of_truth:` or named in the ratcheted baseline (the gate is absolute once that baseline is retired), AC permission tokens resolving against the permissions contract, and AC absence claims not naming a testid or component the shipped frontend still mounts. |
| `knowledge-fragments` | Knowledge fragments are readable | Every table the knowledge readers serve — the requirement registers, the program and slice registers, the capability rows and a feature map's `source_of_truth:` list — is stored as one JSON file per row. |
| `knowledge-hygiene` | Corpus hygiene | The cross-subtree rules no single register owns: one audit record per scope, an audit's coverage claim derived from its own unit table rather than asserted, a transient doc deleted once its trigger fires, a complete spec index, no restatement of a fact that has one defining home, and one tiered, familied ledger row per feature area. |
| `knowledge-paths` | Link resolution | Every path a knowledge doc names — a markdown link, a backticked code path in prose, a `path:` in frontmatter — resolves in the tree. |
| `knowledge-types` | File types | Every file in the knowledge base matches exactly one type from the project's own type registry (FILE-TYPES.md by default), declares that type in its frontmatter, and carries the fields that type requires. |
| `plain-english` | Prose a person reads is plain English | People who read the knowledge base are often not native English speakers, so its prose follows the style of ASD-STE100 Simplified Technical English: every sentence has 20 words or fewer, it avoids a short list of words that sound clever and say little, and it uses the approved word for each term in the writing rules. |
| `prd-commitments-section` | PRD design commitments section | The design pipeline's commitments phase is the only step that reconciles what a PRD claims to realise against the requirement register — recording the rows the design creates and superseding the ones its Non-Goals kill. |
| `prd-depends-on-prose` | PRD depends_on matches its prose | The auto-driver waits on a PRD's frontmatter `depends_on:` and on nothing it reads in the text. |
| `prd-ext-promotion` | PRD [ext] promotion | A criterion observable only against a real environment used to be tagged `[ext]` and N/A'd until the dependency existed; the PRD shipped over it and its slice computed complete from that status, with the one thing the slice's promise needed never run. |
| `prd-plan-status` | PRDs with plans are flipped to planned | prd:plan Step 7 flips the PRD to `planned` in the same commit as its plan files, and the fleet's projection reads only that flip: plans beside a `designed` PRD leave its tracker issue in "Needs Plan". |
| `prd-plans` | PRD implementation plans | The planning stage has no gate of its own and is the contract implementation is forbidden to question, so a planning defect passes straight into execution unexamined. |
| `prd-scope-ledger` | PRD scope ledger | Scope is the human's call, and it stays the human's after a PRD exists — craft licence covers how well the asked-for thing gets built, never what gets built. |
| `product-docs` | Fleet's product docs follow their contract | Every page under fleet_knowledge/productdocs/ passes productdocs/README.md: its front matter, its blocks and their attributes, no raw HTML, the index against the files, every route against the app's real route table, every `sources:` path present, and every term defined. |
| `program-requires` | Program requires vs decomposition | A program's `Requires` cell names the ROOTS its build-order derivation closes over; its detail file's `## Decomposition record` is where those roots were actually worked out. |
| `promise-wording` | Promises are written in one plain sentence | A capability, a requirement rule and a journey's acceptance criterion are read by people who did not write the code and checked from outside it, so each is one plain sentence in the product's words, with code names, routes, status codes, environment variables and paths in the Evidence column. |
| `qa-review-records` | The QA verifier's records are valid and append-only | Every review, oracle and planted-bug record under knowledge/audits/reviews/ validates, and no change modifies or deletes one — a deleted dispute would turn a disputed pass green. |
| `recurring` | recurring schedule — the [fleet.recurring] entries are well-formed | A watched repository declares the work Fleet files on a cadence in its own fleet.toml under [fleet.recurring]. |
| `requirement-registers` | Requirement registers | Every commitment a corpus makes is one numbered row in a per-domain register, and the load-bearing rule is that an ID is PERMANENT and never reused — because everything downstream (a PRD's `implements:`, a spec citing the id instead of restating the rule, the derived backlog) is a string match on it. |
| `requirement-statement-guard` | Requirement statement guard | A permanent id protects the NUMBER; on its own it does not protect what the number means. |
| `scenario-journey-step` | A scenario cites a journey step, never a bare journey | A scenario that proves a journey names the step it walks (`<journey>#<n>`), so the Quality desk counts that criterion on its own row. |
| `scenario-quarantine` | A scenario quarantine names a reason and an until-date | A scenario is taken out of the Quality desk's results by writing a quarantine on its record. |
| `slice-clause-digest` | Slice clause digest | A slice's completion condition is one prose sentence, and when a proof PRD decomposes it into numbered clauses the two can drift apart silently — the sentence gets edited, the clause table does not, and the proof now checks a condition nobody agreed to. |
| `slots` | slot registry — what this repo answers, and which commands can run | A slash command is a portable procedure and a repo is a set of filled-in slots. |
| `todo-register` | Todo register | The register of things noticed and not yet settled — not decisions (those are requirement rows) and not dispatchable work (those are tracker issues), but the questions raised in passing that otherwise die with the session. |
| `tracker-clients` | no tracker client ships in the command tree | Agents reach issues only through Fleet's governed tools. |
| `tracking-metadata` | Tracking metadata | The planning ladder is only useful if it is connected: every PRD names a slice, every slice names a program, and no id in either register is malformed, duplicated or ahead of its append-only counter. |

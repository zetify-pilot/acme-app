# Knowledge file types

Every kind of file a knowledge base may hold, where it lives and what it must carry. Look here when the knowledge-types check refuses a file, or before adding a new one.

The `knowledge-types` check holds every file under `knowledge/` to exactly one of these types. **Front matter** says what a file of that type must carry: every file with front matter carries `type`, and `+` names the fields it needs beyond that.

## File types

| Type | What it is | Lives at | Kept | Front matter |
|---|---|---|---|---|
| `readme` | Folder index. | `**/README.md` | durable | `type` only |
| `file-type-registry` | This registry. | `FILE-TYPES.md` | durable | `type` only |
| `spec` | Reusable internal contract or design rule, written from what the code already does (`specs/ui-spec.md`). | `specs/*.md` | durable | `type` only |
| `spec-asset` | A stylesheet a spec owns — the canonical block a mockup pastes (`specs/mockup-change-marks.css`). | `specs/*.css` | durable | no front matter |
| `product-vision` | What the product is and who uses it — the statement and personas a person confirmed, which every capability, rule and journey is written against. | `strategy/product-vision.md` | durable | `type` only |
| `component-registry` | The component registry — the structural map of what this repository builds (one row per component). | `specs/architecture/components.md` | durable | `type` only |
| `journey-flow` | Atomic reusable user flow. | `journeys/flows/*.md` | durable | + `id`, `kind`, `persona` |
| `journey-map` | End-to-end journey composing flows. | `journeys/maps/*.md` | durable | + `id`, `kind`, `persona` |
| `feature-map` | Capability ledger for one feature area. | `features/*.md` | durable | + `area` |
| `feature-coverage-baseline` | GENERATED acknowledged-debt list for the feature-map coverage gate. | `features/UNCLAIMED.baseline` | durable | no front matter |
| `feature-source-of-truth-fragment` | One `source_of_truth` path of one feature map, split out of the map's shared frontmatter line so two branches claiming different code paths edit different files. | `features/source_of_truth/*/*.json` | durable | no front matter |
| `requirement-register` | Numbered requirements, invariants, constraints and rejections for one domain. | `requirements/*.md` | durable | + `domain`, `prefix` |
| `requirement-row-fragment` | One commitment row, split out of its requirement register so two branches editing different rows cannot collide on the shared table. | `requirements/rows/*.json` | durable | no front matter |
| `fragment-dir-keep` | Keeps a row-fragment directory in git before its first fragment lands (`features/rows/` today). | `**/rows/.gitkeep` | durable | no front matter |
| `program-register` | Top planning tier, one row per program: `ID / Name / Kind / Verified by / Requires / Disposition`. | `programs.md` | durable | + `title` |
| `capability-alias-register` | The frozen historical old→new mapping for capability ids. | `capability-aliases.md` | durable | + `title` |
| `slice-register` | Mid planning tier, one row per slice: `ID / Name / Kind / Program / Done when / Verified by / Depends on / Components / Disposition`. | `slices.md` | durable | + `title` |
| `program-detail` | OPTIONAL prose for one program — decomposition record, `## Program-specific work`, `## Delivery log`. | `programs/*.md` | durable | `type` only |
| `slice-detail` | OPTIONAL prose for one slice — why these ship together, sequencing, what the cut excludes. | `slices/*.md` | durable | `type` only |
| `register-shell` | The committed hand-authored SHELL of a generated knowledge table: the prose, table headers and generator anchor markers, with the generated data rows removed. | `**/*.md.tmpl` | durable | no front matter |
| `program-row` | ONE program's register row as a JSON object (column -> cell), so two branches adding different programs touch different files and cannot collide. | `programs/rows/*.json` | durable | no front matter |
| `slice-row` | ONE slice's register row as a JSON object (column -> cell), so two branches adding different slices touch different files and cannot collide. | `slices/rows/*.json` | durable | no front matter |
| `prd` | Product Requirements Document — the ONLY tier whose `status:` is authored. | `prds/*/prd.md` | durable | + `prd`, `status`, `slice` |
| `prd-design` | PRD technical + UX design. | `prds/*/design.md` | durable | `type` only |
| `prd-ux-design` | PRD visual/interaction design. | `prds/*/ux-design.md` | durable | `type` only |
| `prd-plan` | PRD implementation plan; owned by the PRD, retired with it. | `prds/*/backend-plan*.md`, `prds/*/frontend-plan*.md` | transient | `type` only |
| `prd-note` | Other PRD-local working doc (sketch, decisions, runbook, notes, proof-ledger JSON, or a supporting non-markdown artifact like a pre-ship audit SQL script). | `prds/*/*.md`, `prds/*/*.sql`, `prds/*/proof-ledger.json` | transient | `type` only |
| `mockup` | Mockup asset (png/tsx/html) or its index. | `**/mockups/**` | durable | no front matter |
| `audit-record` | Dated audit-run record (latest-per-scope). | `audits/*/[0-9]*.md` | record-corpus | + `scope` |
| `audit-checklist` | One audit type's operating manual — its `## Audit profile` (atom, enumerate, partition, lanes, verify, synthesize, fileAs), dimensions, severity scale and filing rules. | `specs/*-audit-checklist.md` | durable | `type` only |
| `audit-objective` | The operator-set audit campaign goal `audit --objective` writes and an autonomous audit run adopts as its done-bar. | `audits/objective.md` | durable | `type` only |
| `retro-prd` | Retro from a PRD implementation run. | `retros/prd/*.md` | record-corpus | + `owner` |
| `retro-task` | Retro from an autonomous task run. | `retros/task/*.md` | record-corpus | `type` only |
| `retro-bug` | Retro from an autonomous bug-fix run. | `retros/bug/*.md` | record-corpus | `type` only |
| `negative-control-transcript` | A captured per-AC negative-control transcript beside a PRD or task retro: the named test, the mutation, the failing assertion and the restored green. | `retros/*/*-negative-controls.txt` | record-corpus | no front matter |
| `negative-control-ledger` | The re-runnable `neuter_check.py` ledger that produced a PRD or task retro's per-AC negative controls. | `retros/*/*-negative-controls.json` | record-corpus | no front matter |
| `shipped-script` | GENERATED — the command tier's own tooling, written by `fleet commands sync` out of fleet-knowledge's `commandtree/scripts/` at this fixed path; the commands name a script outright (`python3 knowledge/scripts/component_of.py`). | `scripts/*.py` | durable | no front matter |
| `slot` | One repo-local answer a command needs, whose content nothing else in the corpus owns (gate, git-workflow, feature-areas, codegen). | `slots/*.md` | durable | + `slot` |
| `sop` | Standard operating procedure — how we do a recurring thing; the slash commands are its automated subset. | `sops/*.md` | durable | `type` only |
| `decision` | Dated standalone decision/ADR record NOT owned by a PRD (PRD-owned ADRs live in prds/*/design.md). | `decisions/*.md` | record-corpus | `type` only |
| `program-proof-baseline` | GENERATED debt baseline for the same gate one tier up. | `programs/UNCLAIMED.baseline` | durable | no front matter |
| `environment-record` | One running Fleet a QA check can drive: its kind, harness, base URL, org, production flag, principals (login and password only as `fleet-secret://` or `sm://` references, never values; a principal may carry an optional `session` object whose `sign_in` is the request a QA browser step uses, whose `format` is `json` or `form`, and whose `fields` names the login field then the password field), write posture, cleanup posture, version probe and fixtures. | `environments/*.json` | durable | no front matter |
| `check-result` | One append-only check-result file per run, under `audits/results/<kind>/<YYYY-MM-DD>-<scope-slug>-<HHMMSS>Z.json`. | `audits/results/**/*.json` | record-corpus | no front matter |

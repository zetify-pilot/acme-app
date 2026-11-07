---
title: "The knowledge folder, file by file"
kind: concept
for: [developer, owner]
summary: "Where each kind of knowledge lives under knowledge/, what each file holds, and who writes it."
sources:
  - knowledge/FILE-TYPES.md
  - packages/fleet-knowledge/src/fleet_knowledge/scaffold.py
  - packages/fleet-knowledge/src/fleet_knowledge/templates/scaffold/knowledge/slots/entity-model.md
  - knowledge/slots/planning-model.md
minutes: 7
---

:::lede
The `knowledge/` folder has a fixed layout, so that every Fleet command and every check knows where to look without being told. This page walks through it one folder at a time.
:::

## The folder at a glance

::diagram{name="knowledge-folder"}

## What each part holds

| Path | What it holds | Who writes it |
|---|---|---|
| `features/` | One :term[feature map] per feature: its brief, its uses, and the capabilities under each use | People, and commands that ship capabilities |
| `journeys/flows/`, `journeys/maps/` | Journeys: how one kind of person gets a whole job done, with numbered criteria | People, and the PRD commands |
| `specs/architecture/components.md` | The component registry: the parts of the system and the code each one owns | People, and the component command |
| `requirements/` | Requirement registers: numbered promises, one register per domain | The planning commands and the bootstrap, with a person confirming each row |
| `decisions/` | Dated decision records: the option chosen, the option refused, and why | People |
| `slices.md` or `slices/rows/` | The slice register: one row per slice | The slice commands |
| `slices/` (other files) | Optional prose for one slice, named by its id | The slice commands |
| `programs.md` or `programs/rows/` | The program register, in a repository that plans by programs | The program commands |
| `prds/` | One folder per PRD: the PRD, its design and its plans | The PRD commands |
| `slots/` | The repository's answers to the questions Fleet's commands ask | People, once, then kept current |
| `audits/` | Audit records, and the check results under `audits/results/` | The audit and check commands |
| `retros/` | What happened on each PRD, task and bug run | The agent that did the run |
| `specs/`, `sops/` | Conventions engineers follow, and procedures people repeat | People |
| `scripts/` | The tools Fleet's commands run | Fleet only. Never edit these |

## Files you write, and files you never touch

Most of the folder is yours: plain markdown, reviewed in pull requests. Three things are not.

- **`knowledge/scripts/`** arrives with the command tier. `fleet commands sync` writes it, and a change made by hand is lost on the next sync.
- **Generated tables.** In a repository that keeps one file per register row, the tables themselves (`slices.md`, `programs.md`, the requirement registers) are rendered from those rows and not committed. See [Generated tables](knowledge-base/generated-tables).
- **Records.** A check result, an audit record or a retro says what happened at one moment. It is written once and never edited. See [Records](knowledge-base/records).

## A small folder and a large one

A new repository starts small. `fleet init` writes each register as one markdown table: `slices.md`, `programs.md` and `requirements/product.md`. It also writes `strategy/product-vision.md` (what the product is for), a `prds/` folder and short placeholder files under `slots/`.

A repository with many people planning at once keeps one file per row instead, so two pull requests that add different rows never touch the same file. A slice is then `slices/rows/SL-001.json`, a program `programs/rows/PG-01.json`, and a requirement `requirements/rows/REQ-001.json`. The commands write the same thing either way; only where it lands differs.

## Every file has a type

Each markdown file starts with front matter whose `type:` says what kind of file it is, for example `type: feature-map` or `type: decision`. A repository may also keep `knowledge/FILE-TYPES.md`, a registry of every file type and where it may live. When it does, the `knowledge-types` check fails any file that matches no type, or whose `type:` disagrees with where it sits. The full list is in the Knowledge file types reference.

::cards{links="knowledge-base/feature-areas, knowledge-base/slots"}

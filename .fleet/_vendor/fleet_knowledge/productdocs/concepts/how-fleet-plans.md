---
title: "How Fleet plans: one piece of work, start to finish"
kind: concept
for: [owner, developer]
summary: "Follow one real piece of work from a feature request to merged code, and learn the few words Fleet uses on the way."
sources:
  - docs/design/2026-10-27-planning-without-programs.md
  - knowledge/decisions/2026-08-14-the-knowledge-ontology-program-slice-prd-and-what-linear-holds.md
  - knowledge/slices/rows/SL-250.json
  - knowledge/features/fleet-quality-desk.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/process/planning-ladder.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/slice/create.md
  - packages/fleet-knowledge/src/fleet_knowledge/planningmode.py
  - packages/fleet-knowledge/src/fleet_knowledge/rollup.py
  - packages/fleet-knowledge/src/fleet_knowledge/templates/scaffold/fleet.toml
  - packages/fleet-service/src/fleet_service/api/areas.py
  - packages/fleet-service/src/fleet_service/api/static/areas.js
  - packages/fleet-service/src/fleet_service/api/static/app.js
minutes: 6
---

:::lede
Fleet's own team wanted every quality check to leave a record behind. Here is how that wish became merged code, and the few words Fleet uses along the way.
:::

## Three questions sort everything

Every piece of work in Fleet answers three questions. Where does it belong? What will be true when it is done? What does one agent build? The answers get names, and those names are most of what you need.

::diagram{name="three-questions" slice="SL-250"}

The first answer never finishes. The other two do.

## The walk-through

:::steps
- [you] **A feature request is filed.** "I want to see what has been checked, and how recently." Fleet asks a few questions about it and writes up a proposal: what kind of work this is, and where it belongs. A person accepts the proposal or sends it back.
- [you] **It lands in a feature area.** It belongs to the Fleet Quality Desk, the :term[feature area] that records what checks found. The area already holds other work and will outlive this piece.
- [you] **Someone writes what "done" means.** That sentence, with its name and its area, is a :term[slice]. This is the real one:
  ::live{slice="SL-250" title="Check results kept as files" quote="A run of any kind of check writes a result file with a verdict for each criterion or checklist item, against stable ids, for a kind a customer defined in the slot."}
- [fleet] **A PRD says how to build it.** The :term[PRD] turns the sentence into acceptance criteria that one agent can build in one session. Fleet can write it, and asks you when it needs a decision. A PRD's status is the only status anyone writes.
- [fleet] **Built, then checked by someone else.** One session builds the PRD and opens a pull request. A fresh session that did not write the code checks each acceptance criterion, then merges it or sends it back.
- [nobody] **The slice finishes by itself.** When every PRD in the slice is done and the PRD named as its proof has shipped, the slice is complete, and its page marks it **proven**. Nobody sets a status.
:::

:::callout{kind="why" figure="33 of 40"}
planning containers still read unfinished after all their work had shipped, back when people had to set their status by hand. A state Fleet works out from the PRDs cannot drift from the work.
:::

## Where you'll see it

**Features**, in the sidebar, lists every feature: the ones still being built first, the most open at the top, then the finished ones.

::screen{route="areas" focus="fleet-quality-desk" pins="area,slices,prds,next"}
1. The feature and what it covers. A feature never finishes; how far it has got is read from its work.
2. How many of its slices are open. A slice leaves this count once it is complete.
3. How many of its PRDs are open.
4. Finished features sit at the bottom, under **Finished**. Click any feature to see its brief, its uses and how far each has got, what waits on you, and its open slices, PRDs, tasks and bugs.

::action[Open Features]{route="areas"}

A slice that names no area is counted under **Needs a feature** on the page, so you can fix it.

## And programs?

Fleet plans in one of two modes, set per repository in `.fleet/fleet.toml`. A repository created with a fresh `fleet init` plans by areas. A repository that was set up before keeps planning by programs until its owner moves it. In both modes every slice names its area.

:::mode{programs}
Your repository also groups slices into programs. A :term[program] is a larger result that two or more slices add up to and that none of them delivers alone. A slice names its area and may also name a program. A program finishes the same way a slice does: once all its slices are complete and its own proof has shipped. Everything above still holds.

Older slices written before every slice needed an area appear under **Needs a feature**. The next change to such a slice must give it one.
:::
:::mode{areas}
Your repository plans by areas. A slice names its area and no program, and programs take no new slices.

To hand a slice's planning to the fleet, open the slice and press **Start this slice**. The fleet refines what is missing, writes the PRDs and designs them, and stops when a person is needed. Nothing else in the area is touched.
:::

::cards{links="knowledge-base/slices"}

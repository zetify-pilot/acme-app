# How Fleet plans: one piece of work, start to finish

Fleet's own team wanted every quality check to leave a record behind. Here is how that wish became merged code, and the few words Fleet uses along the way.

## Three questions sort everything

Every piece of work in Fleet answers three questions. Where does it belong? What will be true when it is done? What does one agent build? The answers get names, and those names are most of what you need.

| Question | Name | Finishes? | Here |
|---|---|---|---|
| Where does it belong? | Feature | never | — |
| What will be true when we're done? | Slice | yes | SL-XXX |
| What does one agent build? | PRD | yes | — |

The first answer never finishes. The other two do.

## The walk-through

1. [you] **A feature request is filed.** "I want to see what has been checked, and how recently." Fleet asks a few questions about it and writes up a proposal: what kind of work this is, and where it belongs. A person accepts the proposal or sends it back.
2. [you] **It lands in a feature area.** It belongs to the Fleet Quality Desk, the feature area that records what checks found. The area already holds other work and will outlive this piece.
3. [you] **Someone writes what "done" means.** That sentence, with its name and its area, is a slice. This is the real one:

   > An example from Fleet's own planning: **Check results kept as files** (SL-XXX)
   > A run of any kind of check writes a result file with a verdict for each criterion or checklist item, against stable ids, for a kind a customer defined in the slot.
4. [fleet] **A PRD says how to build it.** The PRD turns the sentence into acceptance criteria that one agent can build in one session. Fleet can write it, and asks you when it needs a decision. A PRD's status is the only status anyone writes.
5. [fleet] **Built, then checked by someone else.** One session builds the PRD and opens a pull request. A fresh session that did not write the code checks each acceptance criterion, then merges it or sends it back.
6. [nobody] **The slice finishes by itself.** When every PRD in the slice is done and the PRD named as its proof has shipped, the slice is complete, and its page marks it **proven**. Nobody sets a status.

> **Why:** 33 of 40 planning containers still read unfinished after all their work had shipped, back when people had to set their status by hand. A state Fleet works out from the PRDs cannot drift from the work.

## Where you'll see it

**Features**, in the sidebar, lists every feature: the ones still being built first, the most open at the top, then the finished ones.

On the Features page (#areas):
1. The feature and what it covers. A feature never finishes; how far it has got is read from its work.
2. How many of its slices are open. A slice leaves this count once it is complete.
3. How many of its PRDs are open.
4. Finished features sit at the bottom, under **Finished**. Click any feature to see its brief, its uses and how far each has got, what waits on you, and its open slices, PRDs, tasks and bugs.

[Open Features](#areas)

A slice that names no area is counted under **Needs a feature** on the page, so you can fix it.

## And programs?

Fleet plans in one of two modes, set per repository in `.fleet/fleet.toml`. A repository created with a fresh `fleet init` plans by areas. A repository that was set up before keeps planning by programs until its owner moves it. In both modes every slice names its area.

(If this repository plans by programs.)
Your repository also groups slices into programs. A program is a larger result that two or more slices add up to and that none of them delivers alone. A slice names its area and may also name a program. A program finishes the same way a slice does: once all its slices are complete and its own proof has shipped. Everything above still holds.

Older slices written before every slice needed an area appear under **Needs a feature**. The next change to such a slice must give it one.

(If this repository plans by areas.)
Your repository plans by areas. A slice names its area and no program, and programs take no new slices.

To hand a slice's planning to the fleet, open the slice and press **Start this slice**. The fleet refines what is missing, writes the PRDs and designs them, and stops when a person is needed. Nothing else in the area is touched.

Next: Slices (knowledge-base/slices)

---
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.
- **program**: A larger result that two or more slices add up to and none delivers alone, used only by repositories that plan by programs.

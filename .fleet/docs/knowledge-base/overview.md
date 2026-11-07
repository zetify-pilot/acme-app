# The knowledge base

Every repository Fleet works in keeps a `knowledge/` folder beside its code. It says what the product lets people do, what it has promised, and what is being changed right now. Agents read it before they build, the board is drawn from it, and the Quality desk checks the running product against it.

## What it answers

A knowledge base is a set of plain files that answer four questions. Each answer has a name, and each name has its own page in this section.

| The question | What answers it |
|---|---|
| What can someone do with the product? | [Feature areas](knowledge-base/feature-areas), [capabilities](knowledge-base/capabilities-and-components) and [journeys](knowledge-base/journeys) |
| What did we promise, refuse or decide? | [Requirements](knowledge-base/promises) and [decisions](knowledge-base/decisions) |
| What is being changed, and when is it done? | [Slices](knowledge-base/slices), [PRDs](knowledge-base/prds) and, in some repositories, [programs](knowledge-base/programs) |
| How is work done in this repository? | [Slots](knowledge-base/slots): the answers each Fleet command needs about your build, tests and branches |

## Why it is files in your repository

- **It is reviewed like code.** Every change to it arrives as a pull request, so a promise or a plan changes the same way the product does: on a branch, checked, and merged.
- **Agents can read it on a fresh checkout.** An agent session starts from the repository and nothing else. What it needs to know has to be in the repository.
- **Fleet reads it from your main branch.** The Programs, Features and Knowledge pages are a reading of these files at one commit, and every live card in these docs says which commit it was read from.

## Two kinds of thing live in it

Some things never finish. A feature area, a capability, a component, a journey, a requirement and a decision are true for as long as the product is. They carry no status, because there is nothing to finish.

Other things are work, and work finishes. A slice finishes when every PRD in it has shipped or been cancelled, at least one has shipped, and the proof it names has shipped; its Done when sentence says what that proof shows. A PRD finishes when it ships. In a repository that plans by programs, a program finishes when its slices are complete or waived and its own proof has shipped.

> **Why:** Only a PRD's status is ever written, and Fleet's commands write it. A slice or a program reads complete when its parts are done, worked out by Fleet from the files. A state that has to be remembered goes stale; a state that is worked out cannot drift from the work.

Beside these sit **records**: the check results, audits and retros that say what happened, written once and never changed. See [Records](knowledge-base/records).

## Where you see it in Fleet

The **Knowledge** page lists every journey, feature area, capability, component, requirement and decision in the repository you are looking at, and links each one to the things it relates to. The **Features** page shows the open work under each feature area. The **Architecture** page draws the component registry.

[Open Knowledge](#knowledge)

## How a knowledge base starts

A new repository gets a small one from `fleet init`: a product statement, a first slice, an empty requirement register and the slot files to fill. See [Start a knowledge base](guides/knowledge/start-a-knowledge-base).

A repository that already has code is described into one a step at a time, drafted from the code and confirmed by a person:

`knowledge:bootstrap` — Describe an existing code base into the knowledge corpus one resumable step at a time — survey, components, per-component capabilities and rules, feature areas, journeys — drafting from the code and confirming every promise with a person in batches, so new work builds on it and the QA Desk checks it out of the box.

Next: The knowledge folder, file by file (knowledge-base/the-folder) · Planning by areas or by programs (knowledge-base/planning-modes) · Sorting something new: which kind of thing is it? (knowledge-base/what-is-it)

---
- **knowledge base**: The `knowledge/` folder a repository keeps beside its code, saying what the product does, what it promised and what is changing.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.
- **capability**: One concrete thing the product lets a person do, small enough to check at any time and still true tomorrow; it sits under one use of a feature, is shipped by a PRD, and never finishes.
- **component**: A part of the product you can point at in the code, such as a directory, a service or a set of tables; it is built and never finishes.
- **journey**: How one kind of person gets a whole job done in the product, written from the real reason they open it.
- **requirement**: One sentence the system must always, or must never, do, kept with a permanent id in a register.
- **decision**: A fork someone took in the knowledge base, recorded with the option chosen, the option refused and the reason.
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.
- **program**: A larger result that two or more slices add up to and none delivers alone, used only by repositories that plan by programs.

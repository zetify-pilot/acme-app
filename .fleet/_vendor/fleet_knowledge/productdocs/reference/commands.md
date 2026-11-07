---
title: "Commands"
kind: reference
for: [everyone]
summary: "Every Fleet command, what it does, what it needs from a person and whether it merges."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands
  - packages/fleet-knowledge/src/fleet_knowledge/commands.py
generated: true
---

:::lede
Every command Fleet ships, in one line each. Use it to find the command for a job, or to see whether a command will stop for you or merge on its own.
:::

Each command is named by its id, such as `slice:create`. In your repository it is typed in Claude Code as `/<namespace>:<id>`, where the namespace is the one `[fleet.commands]` in `.fleet/fleet.toml` sets.

For each command: what a run needs from a person to finish, whether it may merge its own work, and whether a repository that takes only the core set receives it.

## Commands

| Command | What it does | Needs from a person | Merges its own work | In the core set |
|---|---|---|---|---|
| `arch:reconcile` | Find the architecture docs that no longer match the code, update only those, and open one pull request. | nothing | no | no |
| `ask` | Answer a question or look into something, and name the command to run if the answer turns out to be real work. | answers | no | yes |
| `audit` | Audit one area against a checklist, split across parallel agents, and file every confirmed finding as an issue. | answers | yes | no |
| `bug:create` | File a bug with its evidence: how to reproduce it, what happened and what should have. | nothing | no | yes |
| `bug:fix` | Fix a bug test-first: reproduce it as a failing test, fix the cause, and open a pull request for independent review. | answers | no | yes |
| `bug:reproduce` | Try to reproduce a filed bug and capture it as a failing test, or ask the filer for what is missing. | answers | no | yes |
| `check` | Review a newly filed issue: confirm it is real, set its priority and area, then release it to the fleet or ask a person to decide. | answers | no | yes |
| `component:create` | Add a subsystem to the component registry, the map of what the repository builds. | answers | no | no |
| `connector:build` | Build or extend a Python data connector and take it through its validation. | answers | no | no |
| `idea:create` | Park an early idea as an issue so it can be shaped later. | answers | no | yes |
| `intake` | Turn a captured idea into a short, decision-ready brief by asking the person who filed it a few questions. | answers | no | yes |
| `knowledge:bootstrap` | Describe an existing code base in the knowledge base step by step, confirming each promise with a person. | answers | no | yes |
| `knowledge:describe` | Describe one part of a repository on the fleet: read every file it owns, ask a person to confirm each promise, and land it as one pull request. | answers | yes | yes |
| `mockup` | Make a mockup for one surface: pick a reference, build it from the project's real parts, render and critique it, then ask a person to approve it. | answers | no | yes |
| `own` | Keep one property of the running product true: check it regularly in every environment and get every failure fixed. | answers | no | no |
| `page:improve` | Make one improvement to a web page, following its page spec, and open a pull request for review. | answers | no | no |
| `page:spec` | Write or refresh a web page's spec: what the page is for and which standard component each part uses. | answers | no | no |
| `prd:blueprint` | Design a drafted PRD on the fleet, asking a person each open question in writing, and record the design. | answers | yes | yes |
| `prd:cancel` | Cancel a PRD with a recorded reason, so the work it covered shows as open again. | answers | yes | no |
| `prd:create` | Write a PRD with a person, grounded in the product vision and the user's journey. | answers | yes | yes |
| `prd:design` | Write the technical and UX design for a PRD. | answers | no | yes |
| `prd:fill` | Turn a PRD stub into a drafted PRD on the fleet, asking a person each open question in writing. | answers | yes | yes |
| `prd:implement` | Build a PRD and open a pull request for independent verification. | answers | no | yes |
| `prd:plan` | Split a PRD's design into backend and frontend implementation plans. | nothing | yes | yes |
| `prd:verify` | Check that every acceptance criterion of a built PRD works, in the browser for UI, and mark it verified. | answers | yes | yes |
| `process:improve` | Turn friction that keeps recurring in run retrospectives into fixes to the procedure or command behind it. | nothing | yes | no |
| `program:create` | Add a program: a company-scale goal, written in plain language. | answers | yes | yes |
| `program:decompose` | Work backwards from a program to the pieces of work it needs and the order they depend on. | a decision | no | yes |
| `program:deliver` | Run one delivery cycle for a program in progress: release ready work, spot stalls and ask a person about blockers. | answers | no | yes |
| `program:demonstrate` | Name the proof that a shaped program works, asking a person in writing on the fleet. | answers | yes | yes |
| `program:prove` | Name or repair the proof that a program works, or record honestly that none exists yet. | answers | yes | yes |
| `program:shape` | Shape a rough program into a planned one on the fleet, asking a person each open question in writing. | answers | yes | yes |
| `program:ship` | Close a finished program once its slices and its proof check out. | nothing | yes | yes |
| `push` | Commit the pending work, push it, open a pull request and set it to merge when checks pass. | answers | yes | yes |
| `qa` | Check one shipped promise on a named environment, record the result and file an issue for each failure. | answers | yes | no |
| `qa:verify` | Re-check a sample of the QA agent's results from their recorded evidence, and flag any it got wrong. | nothing | yes | no |
| `repo:init` | Give a new repository with no code a running hello-world web service, a unit test, lint, a build and CI, and open one pull request for independent review. | answers | no | yes |
| `route` | Decide what kind of thing a request is and hand it to the command that builds that kind. | answers | no | yes |
| `sidekick` | Ride along while a person uses the product, note each friction, and fix or file them on request. | a decision | no | no |
| `slice:create` | Add a slice to a program: what it delivers, what it leaves out, and how it will be proven. | answers | yes | yes |
| `slice:edit` | Change a slice's proof, prerequisites or promise, with the checks a hand edit would skip. | a decision | yes | yes |
| `slice:refine` | Turn a rough slice into a complete one on the fleet, asking a person each open question in writing. | answers | yes | yes |
| `task:create` | File a small task saying what the work is. | nothing | no | yes |
| `task:implement` | Do a small task and open a pull request for independent review. | answers | no | yes |
| `unblock` | Go through the issues waiting on a person, one at a time: get each decision and release the issue. | a decision | no | no |
| `verify` | Independently check a fix before it merges, then merge it or send it back. | answers | yes | yes |

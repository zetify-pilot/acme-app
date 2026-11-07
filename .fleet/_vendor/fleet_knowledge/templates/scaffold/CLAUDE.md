<!-- fleet:begin managed — `fleet commands sync` rewrites everything from here to fleet:end; write this repository's own rules below it -->
# Standing rules for an agent working in this repository

This file is read by the coding engine at the start of every session in this checkout. It
holds the rules that bind whatever task brought you here. Where a rule below disagrees with
the code, the code is the bug: fix the code, not the rule.

## What Fleet is

Fleet is the system that plans, builds and checks the work in this repository. It plans against
the repository's **knowledge base**: the plain files under `knowledge/` that say what the product
is made of (components), what people can do with it (capabilities), how they get a whole job done
(journeys), what it has promised (requirements), what was decided, and what is being changed
(slices and PRDs). Read it before you build, and keep it true when you change the product.

Fleet's own docs are in `.fleet/docs/index.md`. Read them with `list_docs` and `read_doc` when
Fleet's tools are in the session, or open the files there when they are not. To build a
knowledge base for a repository that has code but none, run
`/{{namespace}}:knowledge:bootstrap`.

**Before you create or change a file under `knowledge/` (a journey, PRD, feature map, decision,
slice, program, requirement), read the docs page for its type.** `.fleet/AGENTS.md` lists each
type and the page to read.

## Commands

This repository ships its procedures as commands, each one a whole job done the same way every
time. Start every session with one. Type `/` in the coding engine to list them. Their
definitions live in `{{tierRoot}}/commands/{{namespace}}/`; where your session has not loaded
them, open the one you need there and follow it.

- `/{{namespace}}:ask` — a question, research, or "not sure yet what this is". It answers and
  builds nothing.
- `/{{namespace}}:intake` — bring something new; a short interview turns it into a clear request.
- `/{{namespace}}:route` — work out what kind of work a request is, and which command takes it.
- `/{{namespace}}:idea:create`, `/{{namespace}}:bug:create`, `/{{namespace}}:task:create`, `/{{namespace}}:prd:create` — file
  new work of that kind as a well-formed item.
- `/{{namespace}}:check` — the gate a filed item passes before anyone works on it.
- `/{{namespace}}:bug:fix`, `/{{namespace}}:task:implement`, `/{{namespace}}:prd:implement` — do the work and
  open a pull request.
- `/{{namespace}}:verify`, `/{{namespace}}:prd:verify` — a second session, never the author, checks the
  change and merges it or sends it back.
- `/{{namespace}}:push` — commit your changes and open a pull request.

## The rules

- **Reproduce before you fix.** Show the failure first — a failing test, a measured run, a
  log line — and only then change code. A fix written before the failure is reproduced is a
  guess, and the guess is what ships.
- **Never certify your own work.** The party that wrote a change does not approve it. Open a
  pull request and hand it to somebody who did not write it; never merge your own.
- **Credentials never go on the command line.** Command-line arguments are world-readable
  while a process runs. Read a secret from the environment of the process that needs it, or
  hand it to a program on standard input.
- **Stay in scope.** Change what the task needs and nothing more. A separate defect you find
  along the way is filed as its own issue, never fixed inside an unrelated change.
- **Say why, not only what.** A commit message and a pull request description explain the
  reason for the change and name the work item they close.
- **Never commit a secret.** No key, token or password in the tree, in a comment, or in a
  test fixture.

<!-- include: process/writing.md -->
<!-- fleet:end -->

## This repository's own rules

<!-- Add this repository's standing rules below; they bind exactly as the rules above do.
     Delete these comment lines once you have written them. -->

- (add your repository's rules here)

---
title: "Move a repository from programs to feature areas"
kind: guide
for: [owner]
summary: "Give every live slice its feature area with fleet planning migrate, and optionally stop programs taking new slices, by one pull request you review."
mode: programs
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/planningmigrate.py
  - packages/fleet-knowledge/src/fleet_knowledge/planningmode.py
  - packages/fleet-knowledge/src/fleet_knowledge/cli.py
  - packages/fleet-knowledge/src/fleet_knowledge/checks/planning/tracking_metadata.py
  - docs/design/2026-10-27-planning-without-programs.md
  - knowledge/decisions/2026-10-27-planning-without-programs.md
minutes: 7
---

:::lede
When you are done, every slice still being worked on names the :term[feature area] it belongs to, and, if you choose, new slices go under their area instead of a :term[program]. It arrives as one pull request you read before anything changes, and nothing already finished is rewritten.
:::

## Before you start

This page is for a repository that plans by programs: its `.fleet/fleet.toml` has no `[fleet.planning] mode`, or says `mode = "programs"`. A repository set up with `fleet init` since areas arrived already plans by area and has nothing to move.

You need the `fleet` command in a terminal, in a checkout of the repository, and the repository's feature maps under `knowledge/features/`. The migration only places a slice in an area that has a map.

## Two jobs, you choose how far

| | What changes |
|---|---|
| **Area backfill** (always) | Every live slice with no area gets one. Programs stay as they are. |
| **Off programs** (`--drop-programs`) | Each live slice also leaves its program. The row keeps the old program as `from_program`, so its history stays readable. |
| **And switch the mode** (`--flip`, with `--drop-programs`) | `.fleet/fleet.toml` gets `mode = "areas"`: programs take no new slices from then on. |
| **Close the programs** (`--close-programs`, which includes `--drop-programs`) | Every open program is marked `superseded by areas` once its live slices have left it. Each open PRD a program named as its end-to-end proof becomes one slice of its own in the area it mostly touches, so the check survives. A program holding a slice it cannot place stays open. |
| **Require an area** (`--require-area`) | `.fleet/fleet.toml` gets `require_area = true`: a live slice without an area fails the check. |

A *live* slice is one that is adopted and not finished, under a program that is still adopted and not finished. Finished and withdrawn slices, slices under a withdrawn or finished program, and every finished, waived or withdrawn program row are never touched, so every `PG-…` id keeps resolving. A program closed with `--close-programs` takes no slice with it: a finished slice under it stays finished.

## Do it

:::steps
- [you] **See what it would do.** Run the migration with no flags. It writes nothing.

  ```sh
  fleet planning migrate
  ```

  It prints a table: each live slice, its program, the area it proposes and why, and every slice it **CANNOT PLACE**, with the candidate areas.
- [fleet] **It proposes an area from evidence.** First, the area the slice's PRDs agree on. Failing that, the one feature map whose components hold every component the slice names. Anything less certain is **CANNOT PLACE**; it never guesses.
- [you] **Choose how far to go.** Add `--drop-programs` to take the live slices off their programs too, and `--flip` to switch the repository to areas. Run it again without `--pr` to read the new table.
- [you] **Open the pull request.** Add `--pr`. It writes the change on a new branch, `knowledge/slices-to-areas` by default, in a temporary worktree off `origin/main`, so your own checkout is untouched, and opens one pull request. Its description is the table, the slices it could not place, and how to undo it.
- [you] **Place the rest by hand.** For each slice it could not place, add `area` with the slug of the right feature map on that same branch.
- [you] **Review and merge.** It never merges itself. Closing the pull request undoes everything.
:::

If you would rather commit the change yourself, `--write` writes it into your working tree instead of opening a pull request. `--json` prints the plan for a script.

:::callout{kind="tip"}
The command exits with 1 while any slice could not be placed, and 0 once everything is placed. Run it again after you place the rest by hand to confirm nothing is left.
:::

## What changes after you merge

- In areas mode, a new slice names its area and no program. Creating one under a program is refused, and so is moving an existing slice into a different program.
- Existing programs keep the slices they have. Each one finishes as usual once its slices are done.
- Until every slice has an area, `fleet check` notes each untouched slice without one as *needs an area*. A new or changed slice without one fails the check.

## Undo it

Set `mode = "programs"` in `.fleet/fleet.toml`. Area slices written in the meantime stay valid and readable.

::cards{links="knowledge-base/planning-modes, knowledge-base/feature-areas, guides/plan/work-by-area"}

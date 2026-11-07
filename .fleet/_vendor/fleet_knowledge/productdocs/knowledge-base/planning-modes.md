---
title: "Planning by areas or by programs"
kind: concept
for: [owner, developer]
summary: "A repository plans in one of two modes. Both put every slice under a feature area; only one also groups slices into programs."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/planningmode.py
  - packages/fleet-knowledge/src/fleet_knowledge/templates/scaffold/fleet.toml
  - packages/fleet-knowledge/src/fleet_knowledge/checks/planning/tracking_metadata.py
  - docs/design/2026-10-27-planning-without-programs.md
  - knowledge/decisions/2026-10-27-planning-without-programs.md
minutes: 6
---

:::lede
Every slice of work lives under a feature area, the part of the product it changes. Some repositories also group slices into programs, larger results that several slices add up to. Which of the two your repository does is its planning mode, one setting in its configuration.
:::

## The two modes

A :term[planning mode] decides where new work goes. In both modes every :term[slice] names its :term[feature area]. The difference is whether slices can also join a :term[program].

:::compare
| | Planning by areas | Planning by programs |
|---|---|---|
| A new slice names | its feature area | its feature area, and may also name a program |
| Existing programs | take no new slices, and finish the ones they have | take new slices as before |
| What you can start, so Fleet runs its planning steps by itself | one slice, from the slice's page | a whole program, or one slice that names no program |
| Who is on it | every repository set up with a fresh `fleet init` | every repository set up before areas existed, Fleet's own included |
:::

:::mode{areas}
Your repository plans by areas. A slice's home is its feature area and nothing sits above it. You find open work on the Features page, and you start a slice from its own page.
:::
:::mode{programs}
Your repository plans by programs. Each slice still names its feature area, and may also name the program it serves. The Programs page groups slices by program; the Features page groups the same slices by feature.
:::

## Why areas

A program used to do two jobs at once: it was a goal that should finish, and it was the only grouping people could see on the board. A grouping keeps taking new work, so the goal never finished. Feature areas already existed, because every PRD, task and bug is filed under one, but nobody could see them. Areas now carry the grouping, and the slice carries "done".

:::callout{kind="careful"}
"Area" here always means a **feature area**: a part of the product a customer would name, written as a feature map under `knowledge/features/`. It is not the old tracker label that sorted issues by discipline (frontend, backend). That label is retired.
:::

## The setting

The mode lives in `.fleet/fleet.toml`:

```toml
[fleet.planning]
mode = "areas"        # or "programs"; leaving the line out means "programs"
require_area = true   # every slice without an area fails the check
```

- **A fresh `fleet init` writes both lines**, so a new repository plans by areas and is strict from the first day.
- **An existing repository has neither line**, so nothing it does changes. `fleet init` and `fleet commands sync` never add them to a file that already exists.
- **A wrong value is refused** when the file is read, with the reason.

## Every slice needs an area, in both modes

A slice with no area is how planning looked before areas. Such rows still read correctly, and the check treats them by whether they changed:

| The slice row | Strict (`require_area = true`) | Not strict (the line left out) |
|---|---|---|
| New, or changed on your branch | fails the check | fails the check |
| Untouched since your base commit, and it names a program | fails the check | noted as "needs an area", never fails |
| Names neither an area nor a program | fails the check | fails the check |

The Features page counts every open slice that still has no area under **Needs a feature**, so you can see what is left to place.

## Moving to areas

A repository moves by one reviewed pull request. `fleet planning migrate` proposes an area for every live slice, from its PRDs' areas or from the components it names, and lists the ones it cannot place for you to place by hand. It changes nothing until you ask it to write, and it never rewrites a finished or withdrawn slice or program. The steps are in [Move to areas](guides/knowledge/move-to-areas).

::cards{links="knowledge-base/feature-areas, knowledge-base/slices, guides/knowledge/move-to-areas"}

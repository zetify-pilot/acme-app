# Planning by areas or by programs

Every slice of work lives under a feature area, the part of the product it changes. Some repositories also group slices into programs, larger results that several slices add up to. Which of the two your repository does is its planning mode, one setting in its configuration.

## The two modes

A planning mode decides where new work goes. In both modes every slice names its feature area. The difference is whether slices can also join a program.

| | Planning by areas | Planning by programs |
|---|---|---|
| A new slice names | its feature area | its feature area, and may also name a program |
| Existing programs | take no new slices, and finish the ones they have | take new slices as before |
| What you can start, so Fleet runs its planning steps by itself | one slice, from the slice's page | a whole program, or one slice that names no program |
| Who is on it | every repository set up with a fresh `fleet init` | every repository set up before areas existed, Fleet's own included |

(If this repository plans by areas.)
Your repository plans by areas. A slice's home is its feature area and nothing sits above it. You find open work on the Features page, and you start a slice from its own page.

(If this repository plans by programs.)
Your repository plans by programs. Each slice still names its feature area, and may also name the program it serves. The Programs page groups slices by program; the Features page groups the same slices by feature.

## Why areas

A program used to do two jobs at once: it was a goal that should finish, and it was the only grouping people could see on the board. A grouping keeps taking new work, so the goal never finished. Feature areas already existed, because every PRD, task and bug is filed under one, but nobody could see them. Areas now carry the grouping, and the slice carries "done".

> **Careful:** "Area" here always means a **feature area**: a part of the product a customer would name, written as a feature map under `knowledge/features/`. It is not the old tracker label that sorted issues by discipline (frontend, backend). That label is retired.

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

Next: Features, uses and capabilities (knowledge-base/feature-areas) · Slices (knowledge-base/slices) · Move a repository from programs to feature areas (guides/knowledge/move-to-areas)

---
- **planning mode**: A repository's setting that says whether new work is grouped under programs or under feature areas.
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.
- **program**: A larger result that two or more slices add up to and none delivers alone, used only by repositories that plan by programs.

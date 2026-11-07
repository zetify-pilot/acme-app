# entity-model

**What each kind of work is, and the order to test for it, is not written here.** It ships with
the command tier as the shared planning ladder, `.fleet/process/planning-ladder.md`. The commands
that classify work carry it inline. This file says only where each kind lives in **this**
repository.

## Where each kind lives here

These are the places `fleet init` created. Change a row when this repository keeps something
elsewhere.

| Kind | Where it lives here |
|---|---|
| Bug, task, idea | the tracker only — never a file |
| PRD | a `prd.md` in its own numbered folder under `knowledge/prds/` |
| Slice | a row in `knowledge/slices.md` |
| Program | a row in `knowledge/programs.md` |
| Requirement | a numbered row in `knowledge/requirements/product.md` |
| Feature area | a feature map, knowledge/features/<area>.md — the `feature-areas` slot lists them |
| Component | the component registry (the `components` slot) — `fleet init` does not create one; add it with the first component |

## Examples

- A defect in a screen that already shipped is a bug.
- One new screen is a PRD.
- A feature with its own "Done when" is a slice.
- A program needs at least two slices, and no open home that already fits.

Add one or two requests from this product under each kind as they arrive. The next reader then
sees the ladder applied to real work here.

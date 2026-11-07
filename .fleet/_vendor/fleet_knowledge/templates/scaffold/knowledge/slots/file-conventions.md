# file-conventions

Where a new document of each kind goes, and the `type:` it carries in its frontmatter. These are
the places `fleet init` created. Where code goes is this repository's own layout: add it below
when it has one.

| Kind of file | Home | `type:` |
|---|---|---|
| Slice register | `knowledge/slices.md` | `slice-register` |
| Program register | `knowledge/programs.md` | `program-register` |
| PRD | knowledge/prds/NNNN-<slug>/prd.md | `prd` |
| Requirement register | knowledge/requirements/<domain>.md | `requirement-register` |
| Feature map | knowledge/features/<area>.md | `feature-map` |
| Product vision | `knowledge/strategy/product-vision.md` | `product-vision` |
| Slot answer | knowledge/slots/<slot>.md, named in `knowledge/slots/README.md` | none |
| Index of a folder | README.md in that folder | `readme` |

## Answers

- **prd-folder** — a PRD's folder is its four-digit number and a short slug, `0001-refunds`. Its
  design and plans sit beside `prd.md` in that folder.
- **generated** — `.fleet/**` and `knowledge/scripts/**` are written by `fleet commands sync`.
  Never edit them by hand: the next sync replaces the edit.
- **append-only** — a register row is never deleted. A row that no longer holds changes its
  disposition instead.

---
type: requirement-register
domain: product
prefix: REQ
---

# Product requirements

What Acme App has promised. Every statement is permanent once minted; supersede a row
rather than deleting it.

| ID | Statement | Kind | Disposition | Needs | Source |
|---|---|---|---|---|---|
| REQ-0001 | A customer can take their whole task list out of the app as one comma-separated file, from an address they open in a browser, without an engineer doing it for them. | capability | adopted | — | PRD 0001 — "A person can ask for the export from the surface they use and receive the file itself, not a description of it." |
| REQ-0002 | An export is one row per task under a row of column names — the task's `title` and a column headed `done` — with `done` reading the literal `true` or `false`. | contract | adopted | REQ-0001 | PRD 0001 — "The file carries one row per task under a row of column names: the task's title and a column headed `done` holding true or false." |
| REQ-0003 | Text in a task title survives the export exactly as it was typed: a comma, a double quote or a line break inside it does not split or break the row. | behavior | adopted | REQ-0002 | PRD 0001 — "Text is preserved exactly: a comma, a double quote or a line break inside a title does not split or break the row…" |
| REQ-0004 | An export declares its text encoding and marks it with a byte-order mark, so a title with an accent or a symbol opens readable in a spreadsheet rather than as garbled characters. | constraint | adopted | REQ-0002 | PRD 0001 design — "The file is UTF-8 and begins with a byte-order mark, so Excel opens accented and symbol-bearing titles correctly"; settled by the requester in round 1 of `/fleet:prd:blueprint 0001`. |
| REQ-0005 | Every task in the list appears exactly once, in the order the app shows the list — open tasks first, finished ones last. | behavior | adopted | REQ-0002 | PRD 0001 — "Every task in the list appears exactly once, in the order the app shows the list — open tasks first, finished ones last." |
| REQ-0006 | An empty task list exports as a file with the column names and no rows, rather than an error. | behavior | adopted | REQ-0002 | PRD 0001 — "An empty list produces a file with the column names and no rows, rather than an error." |
| REQ-0007 | An export never refuses over the list's size: however long the list, one file comes out, and nothing bounds the list's length. | constraint | adopted | REQ-0002 | PRD 0001 — "The export never refuses over the list's size: however long the list, one file comes out." |
| REQ-0008 | The saved file's name carries the day it was made, so a weekly exporter's files do not silently overwrite each other and the report says which week it covers. | behavior | adopted | REQ-0001 | PRD 0001 — "The saved file's name carries the day it was made, so a weekly exporter's files do not silently overwrite each other…" |

## Source legend

A `Source` names the thing that settled the row and **quotes the phrase** that does it —
never a line number, which rots.

- **`PRD NNNN — "…"`** — the promise is stated in that PRD's own requirements or acceptance
  criteria; the quoted phrase is the sentence that settles it.
- **`PRD NNNN design — "…"`** — the promise is a *design* decision on that PRD (a fork the
  design settled, or one the requester answered in the design's own question rounds); the
  quoted phrase is the design's own sentence. `REQ-0004` is the first row of this kind: the
  encoding decision was put to the requester in round 1 of `/fleet:prd:blueprint 0001` and
  they chose the byte-order mark.

## Framing note

This register was empty and was framed by `/fleet:prd:blueprint 0001` (2026-10-12), the
design of PRD 0001, which claims all eight rows in its `implements:` and backs each with an
acceptance criterion. The owning cut, SL-002, skipped its own framing, so the rest of this
ground's promise set is still to be written.

**Two things could not be checked on the box that framed these rows**, and both belong on a
run that has the tooling: `fleet_knowledge` is not importable there, so
`validate_id_collisions.py --allocate REQ <n>` could not reserve the ids (they were taken
from a full read of the corpus, in which no `REQ-` id exists and this register was empty),
and the `Kind` vocabulary could not be read from the model document (the values used are
`capability`, `contract`, `behavior` and `constraint`).

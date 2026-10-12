---
type: feature-map
area: tasks
components: []
---

# Tasks

What Acme App promises about tasks themselves — putting them in, seeing them, finishing
them, and taking them out again.

A row is a **capability**: durable, noun-phrased, and worth having for a second customer as
much as the first. `Ships in` carries the PRD number once something ships it, and `—` while
nothing does — which is what a **gap** is. `Needs` names the capabilities that must exist
before this one can; `—` is written deliberately and means *can start immediately*.

The rows below were derived by `/fleet:program:shape PG-01` from the program *Customers can
export their tasks as CSV.*, working backwards from the outcome the requester accepted on the
program's own page. The capability ids are opaque and globally allocated; the numbers here
were taken from a full read of the corpus, because the allocator cannot run on this box (see
the program's detail file, `## Decomposition record`).

| ID | Title | Ships in | Tested by | Anchor | Needs |
|---|---|---|---|---|---|
| CAP-0001 | A task list can be exported from the surface a person uses | 0001 | [tasks-export](../journeys/flows/tasks-export.md) | — | — |
| CAP-0002 | An export arrives as a downloadable file rather than a page of JSON | 0001 | [tasks-export](../journeys/flows/tasks-export.md) | — | CAP-0001 |
| CAP-0003 | Every task becomes one row under a header naming the columns | 0001 | [tasks-export](../journeys/flows/tasks-export.md) | — | CAP-0001 |
| CAP-0004 | Task text containing commas, quotes or line breaks survives the export intact | 0001 | [tasks-export](../journeys/flows/tasks-export.md) | — | CAP-0003 |
| CAP-0005 | An empty task list exports as a file with only a header | 0001 | [tasks-export](../journeys/flows/tasks-export.md) | — | CAP-0003 |
| CAP-0006 | A list too long to export is refused with a message a person can read | — | — | — | CAP-0003 |
| CAP-0007 | One customer's tasks can be told from another's | — | — | — | CAP-0003 |

PRD 0001 ships CAP-0001 … CAP-0005 — the export and its edges for a customer. **CAP-0006**
stays a gap: PRD 0001's necessity test deferred the too-long refusal (no ceiling was chosen, so
the mechanism never fires and nothing breaks without it). **CAP-0007** stays a gap: it belongs
to *One customer's tasks are separable from another's* (SL-003), which has no PRD yet.

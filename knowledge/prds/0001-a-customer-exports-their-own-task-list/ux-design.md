---
type: prd-ux-design
---

# UX Design: A customer exports their own task list and opens it in a spreadsheet

## Why this document exists, and why it is short

PRD 0001's capability is customer-facing — a person outside the team uses it — so the UX
design is written, not skipped. But **this repository has no frontend at all**, and the PRD
says so in its own words: *"The app has no screens today and this does not add one."* The
design adds one HTTP route that answers with a file. There is therefore **no screen, no page,
no control and no interaction to lay out**, and the customer-facing surface this document can
describe is the artifact the customer actually handles: **the file**.

So this is a content-and-states design for a download, not a layout design for a page. It is
written because the file's words — the column names, the value vocabulary, the filename — are
what a person reads in their spreadsheet, and they are exactly the kind of thing that gets
decided by accident when nobody writes it down.

**No mockup, and no approval gate — with the reason.** `design.md` Phase 1 Step 0 and
[`design-fidelity-loop.md`](../../../../.claude/process/design-fidelity-loop.md) §1.5c apply
the mockup gate to a **new or materially-changed customer-facing surface**. This design adds
none: there is no route in the app shell, no page, no component and no visual element. The
PRD's own journey record says the same — *"the app has no screens at all today, so no page is
authored or refreshed at design; steps 4 and 5 happen outside the product"*. There is
accordingly **no named high-craft reference, no Explore-tier round, no Lock-tier fixture page
and no render**, and this document carries **no `## Approved design` block**: the mockup gate
has no subject here. The person was asked, in round 2 of this design, for the go-ahead on the
design as written and gave it.

*This is a scope statement, not an exemption.* If a later PRD puts a link, a button or an
export screen into the product, that surface is new, and it takes the full gate: a named
reference, a mockup that clears the design-fidelity bar, and a person's approval on the card.

## Design-system baseline

`slot:ui-contracts` is an unfilled stub in this repository — it names no component catalog, no
token file, no page structure and no screenshot harness — and there is no `frontend/` tree for
it to describe. So no design-system baseline can be cited, and none is invented here. The
surface this document governs (a file) is not composed from UI components; it is composed from
the RFC 4180 conventions `design.md`'s best-practice baseline names.

## Problem summary

- **Who:** whoever runs the weekly planning or delivery meeting — Priya, who runs the Tuesday
  delivery meeting and has to report on what is open and what is done.
- **Trigger:** the meeting comes round and the report is due. Not a glance at the list.
- **Goal:** build the report from the real list instead of from a copy retyped by hand.
- **Current pain:** she reads the list off the screen and types the still-open tasks into her
  own spreadsheet — about twenty minutes, and stale the moment somebody ticks a task off.
- **Constraints:** the app has no screen to add anything to; the file is used *outside* the
  product, in whatever spreadsheet she already has; and it must survive a title with a comma,
  a quote, a line break, an accent or a symbol.

## The surface: the file, screen by screen

There is one surface and it is not a screen. Its "screen" equivalents — the things a person
reads — are four:

### 1. The browser's save step

The person opens the export's address and the browser offers to save a file. Nothing is drawn
by this product. What the product controls is the two things the browser shows:

- **The name it offers** — `tasks-2026-10-12.csv`. Dated, so a weekly exporter's files do not
  silently overwrite each other and the report says which week it covers. Lowercase, hyphenated,
  no spaces, and the same stem every time so a folder of exports sorts together.
- **That it is offered as a download at all**, rather than rendered as a wall of text in the
  tab — the difference between *the file arrives* and *the person copies a page*.

### 2. The column names — the first row a person reads

`title`, `done`. Lowercase, single words, no punctuation, no spaces, no internal id.

- They are what Priya sorts on, totals on and pastes under. A header that reads `Task Title`
  or `Title (text)` costs her a rename step in every report she builds.
- They match the words the product already uses for a task and its state, so nothing has to be
  translated in her head.

### 3. The values — what the cells say

The `done` column reads the literal `true` or `false`, lowercase — never `True`, `Yes`, `Y`,
`1`, or a tick mark.

- This is the one place a spreadsheet does arithmetic: `COUNTIF(done,"true")` is how the number
  in the report gets to be the real list's number. A tick mark or a capital `T` breaks that
  silently, and a wrong number in a report is worse than no report.
- The `title` column carries the title exactly as typed — no trimming, no case-folding, no
  truncation at 200 characters beyond the limit the app already enforces when a task is
  created.

### 4. The empty file

A person whose list is empty gets a file with the column names and no rows — a header and
nothing under it.

- **Why this is the right empty state:** an empty file with a header says *your list is empty*;
  an error says *something is broken*, which is false and sends the person to ask for help. The
  PRD's own program record puts it the same way — *"If her list is empty she gets a file with
  the column names and no rows, rather than an error."*
- There is no button, no illustration and no message inside the file. A spreadsheet's empty
  state is a spreadsheet with no rows in it, and anything else would be a second format.

## Content design

| Element | Copy | Why |
|---|---|---|
| File name | `tasks-YYYY-MM-DD.csv` | Dated so weekly exports do not collide; a stable stem so a folder sorts; no spaces so it survives being pasted into a shell or a URL |
| Column heading, task text | `title` | The product's own word for it; one word, lowercase, sortable and pasteable as-is |
| Column heading, state | `done` | The PRD fixes this word (R3, AC-2) and the app already uses it (`app/main.py:24`) |
| Value, finished | `true` | Lowercase literal, so `COUNTIF` and any other formula reads it |
| Value, not finished | `false` | Same |
| Row order | the app's own order — open first, finished last | The order Priya already sees on screen, so the file is not a surprise; the first rows are the ones she pastes |

**No error message exists to write.** The export has no input to reject, no id to not-find and
no size it refuses; its only edge is the empty list, which is a file (above). There is
therefore no error copy in this design, and none was invented to fill the section.

## Four Questions test

Adapted honestly: these are the questions a person asks of the artifact, not of a page.

1. **Where am I?** — In their own spreadsheet, with a file named for the day it was made.
2. **How did I get here?** — They opened the export's address and the browser saved the file.
3. **What can I do?** — Everything their spreadsheet already does: sort, total, filter, paste.
   The product imposes no step between the file and the report.
4. **Why should I do it?** — Because the numbers in the report are then the real list's, not a
   retyped copy that was already stale when it was typed.

## Known trade-offs, stated rather than hidden

- **The file's encoding carries a byte-order mark**, so Excel on Windows opens accented and
  symbol-bearing titles as themselves when the file is double-clicked. The cost, chosen by the
  requester in round 1: a program that reads the file itself sees one invisible character in
  front of the first column name unless it strips the mark. Both costs are real; this one was
  picked deliberately, and `REQ-0004` carries the promise.
- **Nothing tells a customer the address.** No link was wanted, there is no screen to carry one,
  and a page that would tell them was offered in round 2 and not pulled in. A person can only
  use the export if they were told where it is; that gap is recorded as an open item on the PRD
  rather than filled with a page in the wrong place.
- **Nothing bounds the list.** A very long list produces a very large file; the export never
  refuses, which was chosen deliberately and is `REQ-0007`.

## Self-Determination Theory check

- **Autonomy** — the file is theirs: it is saved to their machine, opens in the tool of their
  choice, and the product takes no further part. Nothing is scheduled, emailed or shared on
  their behalf.
- **Competence** — there is nothing new to learn. One address, one file, the same words the app
  already uses, and the same row order the screen shows.
- **Relatedness** — not applicable and not claimed: the export is one person's list, taken away
  to be used alone. (The two-people case belongs to the cut that separates one customer's tasks
  from another's, SL-003, which has no PRD yet.)

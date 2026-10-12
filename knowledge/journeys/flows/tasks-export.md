---
type: journey
id: tasks-export
kind: flow
covers: [CAP-0001, CAP-0002, CAP-0003, CAP-0004, CAP-0005]
---

# Take my task list away as a spreadsheet

The end-to-end flow behind PRD 0001. Written by `/fleet:prd:fill 0001` on the fleet: this
repository's `journeys` slot names no home for journey records, so the file sits at the
path `prd:create` names (`knowledge/journeys/flows/<id>.md`) and the slot is reported
unfilled in the PRD's open questions.

**Confirmed at design (`/fleet:prd:blueprint 0001`, against
`1ea420ff3db601905fd5777dd2bd51e5598d8162`).** The flow still holds as written: the design
adds no step, re-orders no surface and adds no screen. The one surface inside the product —
the export's address — stays an HTTP address rather than a page, so no `<Page>.spec.md` is
authored and none is refreshed. The `covers:` ids above are the capability rows in the tasks
feature map this flow exercises.

## The job

*When* the weekly planning or delivery meeting comes round, *I want* to take my task list
away as a spreadsheet, *so I can* build the report from the real list instead of retyping
it.

**One persona, one scenario.** Whoever runs that meeting. Priya runs the Tuesday delivery
meeting and has to report on what is open and what is done. Today she reads the list on
screen and types the still-open tasks into her own spreadsheet by hand — about twenty
minutes, and stale the moment somebody ticks a task off.

**The real starting trigger.** The meeting comes round and the report is due — not a system
sub-task, and not the moment she happens to glance at the list.

## The backbone — happy path

| # | Step — what the person does | Surface |
|---|---|---|
| 1 | The report is due and she wants the real list in it | the meeting, not a screen |
| 2 | She asks for the export | the export's address, opened in a browser |
| 3 | She saves the file the browser offers | the browser's own save step |
| 4 | She opens the file in her spreadsheet tool | her spreadsheet, outside the product |
| 5 | She sorts, totals and pastes it into the report | her spreadsheet, outside the product |

**Every step has a surface and every surface has a step.** There is exactly one surface
inside the product — the export's address — and it already exists as an address rather than
a page. The app has no screens at all today, so **no page is authored or refreshed at
design**; steps 4 and 5 happen outside the product, which is why the export has to hand over
a real file rather than a view.

**Walking skeleton (V1).** Step 2 → step 3 → step 4, one thread: ask for the export, the
browser saves a comma-separated file, and that file opens in a spreadsheet with one row per
task. Everything else in this flow is depth on that thread.

**Branch points, and who owns them.** A list too long for one export is a branch this PRD
deliberately does not take — the export always produces the file (the too-long refusal is
deferred). A person who does not know the export's address is a branch this PRD does not
take either — no link is built; that was offered and declined. The two-people case — two
people's exports never mixing — is a *separate cut* (one customer's tasks separable from
another's), not a branch of this flow.

## Acceptance criteria this flow carries

| # | Criterion | Disposition |
|---|---|---|
| J1 | Asking for the export answers with a file the browser saves, not a page of text. | local |
| J2 | The saved file opens in a spreadsheet with a row of column names at the top and one row per task, holding the task's title and a column headed "done" with the value true or false. | local |
| J3 | A title containing a comma or a double quote comes through exactly as typed, still one row per task. | local |
| J4 | A title containing an accent or a symbol opens readable in Excel, not as garbled characters. | local |
| J5 | Every task in the list appears exactly once, in the order the app shows the list (open tasks first, finished ones last). | local |
| J6 | An empty list produces a file with the column names and no rows, rather than an error. | local |
| J7 | A list of several thousand tasks still comes out as one file — the export never refuses or errors over the list's size. | local |
| J8 | The saved file is named with the day it was made, e.g. `tasks-2026-10-11.csv`. | local |

These are the same criteria PRD 0001's acceptance section carries; the PRD is the authority
on their wording and this file is the flow they trace to.

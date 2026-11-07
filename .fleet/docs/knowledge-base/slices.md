# Slices

A slice is one deliverable that finishes. It is written as one sentence that someone could go and check, and it is done when the work under it has shipped and proved that sentence true.

## One sentence someone can check

Every slice has a **Done when**: one sentence that becomes plainly true the moment the slice is finished. Here is one, from an example slice SL-XXX, "Invoices sent as PDFs":

> Every invoice a customer is sent arrives as a PDF that opens and shows the same amounts as the invoice page.

A person can go and open that PDF. "Make invoicing better" could never be checked, so it is not a slice. If you cannot write the sentence, you have a label or a theme, not a slice.

A slice is bigger than a PRD. A PRD is what one agent builds in one session, with acceptance criteria. A slice is a sentence that none of its PRDs proves alone, so a slice usually holds two or more PRDs. A slice with one PRD is allowed, but look again: it is often a PRD that has not yet found what ships beside it.

Two things are never slices:

- **Something that never finishes.** A part of the code that keeps being built is a component, not a slice.
- **A standing bucket.** A slice's scope is fixed when it is written. New needs get a new slice, not a place in an old one.

## Three kinds

Every slice says which kind of cut it is. Pick the one that describes the cut you made, not the one that sounds biggest.

| | Feature | Capability | Gap-set |
|---|---|---|---|
| What lands | A whole feature a customer would recognise | One capability, on its own | The gaps that must close for one customer or one engagement |
| Choose it when | Several pieces only make sense together | One capability is the honest unit | The pieces share nothing except who needs them |
| Example | "Invoices sent as PDFs" | "A reviewer can read the audit record and act on it" | "Everything still missing for the acme pilot" |

## Where a slice lives

Each slice is one file in the repository, `knowledge/slices/rows/SL-NNN.json`. The file name is the slice's id, and an id is never reused. This is the example slice SL-XXX:

```json
{
  "name": "Invoices sent as PDFs",
  "kind": "feature",
  "program": "PG-XXX",
  "area": "billing",
  "done_when": "Every invoice a customer is sent arrives as a PDF that opens and shows the same amounts as the invoice page.",
  "verified_by": ["0123"],
  "depends_on": [],
  "components": [],
  "disposition": "adopted"
}
```

- `area` is the feature area the slice belongs to. Every slice needs one, and it must match a feature map in `knowledge/features/`.
- `program` is optional. Only a repository that plans by programs uses it.
- `verified_by` names the slice's proof: usually one of its PRDs, the one whose shipping shows the sentence holds.
- `depends_on` lists other slices this one builds on. It sets the order; it never holds a PRD back.
- `disposition` says whether the slice is still in the plan: `adopted`, `withdrawn` with the decision that withdrew it, or `superseded by` another slice. It never says how far along the work is.

A slice can also have a prose file, `knowledge/slices/SL-NNN.md`, for what does not fit in a row: why these things ship together, in what order, and what the slice leaves out.

The slice does not list its PRDs. Each PRD names its slice in its own front matter (`slice: SL-XXX`), and that is the only place the link is written.

## How a slice finishes

Nobody marks a slice done. Fleet works it out every time it reads the knowledge base:

- A slice is **complete** when no PRD in it is still open (each has shipped or been cancelled), at least one has shipped, and everything named in `verified_by` has shipped. `verified_by` can name more than one proof, and a proof can be a PRD or a recorded drill that passed.
- If the work is done but the proof has not shipped, it is still open, and its page says so.

The slice's page shows the result as a chip:

| Chip | What it means |
|---|---|
| in flight | Some of its PRDs are not shipped or cancelled yet, including ones still being written. |
| awaiting proof | Its PRDs are done, but the proof it names has not shipped (also shown for a waived slice that still owes its proof). |
| no proof named | Its PRDs are done, and it names no proof. |
| proven | Complete: its PRDs are done and its proof has shipped. |
| proof waived | A person waived the proof for this slice, and nothing is still owed. |
| no PRDs | No PRD names this slice yet. |
| all cancelled | Every PRD in it was cancelled and none shipped. |
| withdrawn | A decision took it out of the plan. |

> **Tip:** Never write a status into a slice. There is no field for one, and the check refuses words like `done`, `closed` or `delivered` in `disposition`.

On the Slice page (#slice):
1. The slice's Done when sentence.
2. Its PRDs, each with its own status.
3. What you can do with it. A slice that names an area and no program has a **Start this slice** button, which hands its planning to the fleet. A slice in a program is driven from its program.

## Make one, change one

Write a new slice from your terminal. It asks what the slice promises and how anyone will know it is done, finds its area, and lands the row and its prose file in one pull request. When two areas could fit, it asks you rather than guessing.

`slice:create` — Author one planning cut inside a program — what it promises, what it refuses, and the observation that will prove it — with no status and no dates; from an accepted proposal on the fleet, the one register row — and the new feature area’s map when the proposal creates one — and nothing else.

Change one thing on a slice that is otherwise right: its Done when, its proof, what it depends on, or its disposition. It also adds an area to an older slice that has none. It refuses to rewrite the promise of a finished slice to match what shipped; new scope is a new slice.

`slice:edit` — Change one slice's Verified by, Depends on, Done when, or the ## Bar in its detail file — with the resolution, disjointness, acyclicity, digest-binding and retro-fit refusals a hand-edit does not have.

The fleet refines a slice that is still only a row, for example one cut from an accepted idea. You do not type this one. It runs when the slice's next delivery step is to refine it, or when you press **Start this slice** on a slice with an area and no program. It asks its questions on the slice's page.

`slice:refine` — Refine a slice cut from a brief on the fleet: one discovery round with no options, one fork round — the kind, the sharpened Done when, the promise rows, the bar — through the fleet's written question channel, then write the row, the register rows, the detail file and the bar exactly as slice:create would at a terminal and slice:edit would allow — by one merged PR and one landed result, with no status and no dates.

Next: How Fleet plans: one piece of work, start to finish (concepts/how-fleet-plans)

---
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.

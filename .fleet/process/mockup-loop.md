---
type: spec
---

# The mockup loop — make the design, look at it, then ask

**What this is.** The one procedure for making a mockup, written once so every command that
needs one runs the same steps instead of restating them. It ships with the command tier, so
every repository that receives the tier receives this. The `/mockup` command
(the `mockup`
command) is the executable form;
[`design-fidelity-loop.md`](design-fidelity-loop.md) holds the taste bar this procedure measures
against, and the `ui-contracts` slot holds the facts only the receiving repository knows.

**The claim this document makes.** A mockup is not a picture of an idea. It is a **rendered,
clickable candidate** that somebody looked at, criticised, and changed before it was handed to a
person. A run that hands over a mockup nobody ever rendered is not cheaper — it spends the
person's attention on defects its own author could have seen in one screenshot.

---

## Why a mockup needs its own procedure

An agent left alone produces the statistically safe design: even spacing, generic cards, no
density decision, no finish. That is not random badness, it is the training-set mean, and it
passes every lint rule the repository has. Three failures recur, and each one costs more the
later it is found:

- **The mockup is a sketch nobody rendered.** The first person to see it is the one being asked
  to approve it, so the first review is also the last chance. Broken layout at another width, a
  state with no content, two type sizes fighting — all of it lands on the reviewer as *their*
  problem to spot.
- **The mockup is not clickable.** A person cannot answer "does this flow work" from a still
  image, and an implementer cannot test a path the mockup only describes. Every state the
  surface has must be a place you can get to with a click or a URL.
- **The mockup is token-drifted.** Colours copied from memory, or from an older mockup, are a
  frozen snapshot of a file that has since changed. The mockup then lies about what will ship,
  and the implementer is held to the lie.

The procedure below exists to make those three impossible rather than discouraged.

---

## The loop

Run in order. `MAX_ROUNDS = 3`; a round that fixes nothing ends the loop early.

1. **Decide whether this is visual at all.** A question about the UI is not automatically a
   visual question. *"A tab or a drawer here?"* benefits from a drawn shape. *"Which permission
   gates this view?"* does not. If the fork is text-shaped, stop: no mockup is the correct
   output.
2. **Name the reference.** Before drawing, pick at least one real, rendered surface of the same
   archetype (list / detail / settings / cockpit) that this design would be proud to be mistaken
   for, and write down **what about it** is the target — density, rhythm, restraint, hierarchy.
   A mockup built only from the repository's own parts has the repository's own taste as its
   ceiling. Where the repository has an exemplar page already above that average, use it and say
   so.
3. **Read the parts, at authoring time.** Read the token file, the page structure and the
   controls the `ui-contracts` slot names, **as they are right now**, and copy what is actually
   there. Never reproduce a token from memory, from an older mockup, or from a command body. If
   the slot is unanswered, say which conventions you assumed and carry them as assumptions.
4. **Build the round as files in the project tree.** One self-contained `index.html` per round
   (inline CSS, no CDN, no remote fonts or images) plus whatever the round needs beside it, under
   the mockups directory the `mockup-conventions` slot names — never in a scratchpad, never as a
   hosted link. A hosted copy is a viewer for a person and nothing else: the file in the tree is
   the design contract, because the agents that plan, implement and verify this run headless with
   the repository and nothing else.

   **Mark the change.** If the mockup's page, route or screen already exists in the product, mark
   every part you added, changed or removed, inside the mockup. If it replaces nothing, carry no
   marks. Paste the block the `mockup-conventions` slot names into the round's `index.html` between the two
   `mockup-change-marks` markers: a solid outline and the word `new` or `changed` on the part; a
   dashed outline, the word `removed` and the name of what stood there, in its place; everything you
   did not touch stays plain. Use the same block in every mockup, let the word out of a container
   that clips it, and keep it readable in light, dark and at phone width. Say in the PRD's mockups
   index which case the round is.

5. **Make every state reachable.** Each state the surface has — populated, empty, loading,
   error, and each dialog or sheet — is addressable: `?state=<name>` on the same file, or its own
   linked page. Wire the clickable path between them with ordinary `<a href>` elements, so a
   person can walk the flow without the author narrating it. No `href="#"` and no dead control.
6. **Render it headless, at desk width, in every state.** Open the file in a browser (the
   repository's browser harness, or a headless-browser
   run) at 1440×900, capture each state,
   and also at phone width when the project has a phone layout. This is the step whose absence
   the rest of this document exists to close.
7. **Critique the render, ranked, against named targets.** Grade the screenshots against, in
   order: the reference (step 2), the taste bar (`design-fidelity-loop.md` §2 and the UI
   checklist the `audit-profile` slot names), and the repository's own structure. Write a
   **ranked list of concrete defects**, highest impact first — *"the four stats stack as separate
   cards; the reference and this repo's list page put them in one strip"*, *"hero card is ~60%
   empty at 1440"*, *"three type sizes in the header"* — never *"make it nicer"*.
8. **Fix the single highest-impact defect, re-render, re-critique.** One at a time: a loop
   converges, a batch of simultaneous edits cannot be attributed.
9. **Exit** when the critique finds nothing above the bar, when a round fixes zero defects, or at
   `MAX_ROUNDS`. **Never loosen the bar to exit.** A surface that cannot clear it in three rounds
   is a sign the design is underspecified — say so, and route the remainder as follow-up work.
10. **Only now hand it to a person.** Present the render through the fleet's `ask` tool with the
    mockup attached (see `interview.md` → *A mockup reaches a person ONE way*): never a file
    path, never `localhost`, never a path into a built-in question tool that cannot carry it.
    Ask an open question first — *"anything off in the layout or shape before we lock it?"* — and
    wait. Iterate on their words, re-presenting; a model's own critique is not their approval.
11. **Record what was approved** where this project records decisions: which round, the
    **repo-relative path of the approved file**, the date, and any conditions. Downstream agents
    bind to that path.

---

## The two tiers — explore, then lock

Not every mockup is worth the same. Say which tier a run is in, and do not blur them.

| Tier | What it is | What it is for |
|---|---|---|
| **Explore** | a self-contained `index.html` per round, 2–3 divergent directions, throwaway | framing the problem, choosing a direction. Hand-copied tokens are acceptable *here only*, because nothing downstream is held to them. |
| **Lock** | the chosen round as **the product's own substrate** — the real catalog components and tokens the `ui-contracts` slot names, mounted the way that project mounts a page | the round a person approves. This is the one every later stage binds to. |

**An Explore round is not an approved design.** Never write "approved" into a project record
about a mockup made at Explore tier, and never cite one as a downstream fidelity target.

**Promote before approval.** An HTML mockup cannot be clicked through against real component
constraints, and its tokens are a copy that quietly rots. So the round handed to a person for
approval is the Lock-tier one wherever the project has a way to mount it. Where the project has
none — no component library, no dev-only route, no fixture harness — the Explore file **is** the
lock, and that is a fact worth stating once rather than pretending otherwise; the `ui-contracts`
slot says which case the repository is in.

**The Lock tier needs the app running.** Bringing it up is the `dev-environment` slot's answer.
If that slot is unanswered, the run stays at Explore tier and says so.

---

## What a mockup directory contains

- The round files — `round-01-<theme>/index.html`, and its siblings — each self-contained.
- **One committed raster, at most: `reference-<archetype>.png`**, the external high-craft
  reference. Nothing in this repository can regenerate it, which is why it is kept.
- **Never a committed render.** A screenshot of a round is reproducible from its HTML on demand,
  forever; committed, it is a duplicate view that grows without bound and is read by nobody. Show
  renders to people; do not commit them. If the project's record of the approved design is a
  page-spec, that is the record, not the picture.

---

## What this procedure deliberately does not own

The **taste bar** is [`design-fidelity-loop.md`](design-fidelity-loop.md) §2. The **reference
rule** is §1 there and step 2 here, stated twice on purpose: this document is the one a mockup
run reads first, and a run that only reads it must still beat the mean. The **build-time loop
over the shipped surface** is §3 there — this document's loop is the same discipline one stage
earlier, over the mockup rather than the product.

Everything project-specific — where the tokens are, how a page is structured, what the components
are, how to screenshot, where mockups live — comes from the `ui-contracts` and
`mockup-conventions` slots. Nothing in this file names one repository's paths or tools.

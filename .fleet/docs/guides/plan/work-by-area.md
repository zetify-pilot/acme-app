# Use the Features page

When you are done you will be able to answer "what does this part of the product do, how far has it got, and what is waiting on me?" for any feature, you will have given every open slice a feature, and you will know how to start a slice that no program drives.

What a feature, a use and a capability are, and what each state means, is in [Features, uses and capabilities](knowledge-base/feature-areas). Adding a feature and planning it is in [Add a feature and plan its work](guides/plan/add-and-plan-a-feature).

## The Features list

**Features**, in the sidebar, lists every feature in the repository you are looking at. Each row gives the feature's name and summary, its open slices, PRDs, tasks and bugs, a bar of how much is built with the feature's state, and its owner. A row with questions for you says **N waiting on you**.

Every feature is listed, even one with nothing open or nothing written down yet. Features still being built come first, the busiest at the top. Finished features follow under a quiet **Finished** line, and retired ones come last. The filters narrow the list by **Open work**, **Owner** and **Has**, and **Sort** orders it by most open, name, owner or least done.

On the Features page (#areas):
1. One feature, with its summary. Click it for its page.
2. Its open slices.
3. Its open PRDs.

(If this repository plans by areas.)
Your repository plans by features, so every feature needs a person who owns it. A feature with no owner shows a dashed circle; click it to pick one. **New feature**, at the top, adds one.

## One feature's page

A feature's page opens on **Overview**, which is there to understand the feature before you drill in:

- **Waiting on you**, when anything is: each piece of work or plan with questions for you, and how many. Each row opens that item's own page, where you answer them. The same names, up to three, sit in the header.
- **The brief**: the summary and who uses it, under the name.
- **About this feature**: the problem it answers, an example of a real person using it, and what it is not. It is always open; nothing folds it away.
- **How far it has got**: how many of its capabilities are built, the feature's state, and how many things wait on a person or are open fixes.
- **What you can do with it**: the feature's uses, each with its state. Click a use to open what it does, who it serves, what it promises and what is being worked on. Beside a use that has nothing planned is **Plan this**; under the list, **+ Add something this feature should do**.
- **How far it has got** also shows what Fleet is doing right now. The bar has a part for what is being worked on, and under it a **Right now** box lists:
  - **Now**: each piece Fleet has in hand, with what is happening to it: *Designing*, *Building*, *Checking*, *Writing requirements*, *Your answer needed* (a question asked of you), *Waiting for* the person asked (a question asked of someone else, by their name or the first part of their address; point at it for the whole address), *Waiting for a machine* or *Not started*. A waiting label opens the page where the question is answered; every other label opens the piece's own page.
  - **Next**: the pieces that start as soon as the ones in hand ship. A long list folds behind **+N more**.
  - **Later**: the pieces that need other pieces first. Point at a name to see what it waits for.
  - **Shipped**: what shipped recently.

  Every name in the box opens that piece's page, and the names start in one column on every row.

  The box is not shown when nothing on the feature is open.
- **Each use** says in one line what is happening to it, even before you open it, for example *Fleet is designing 1 piece now · 2 wait for it to ship*. Point at the line to read all of it. What the line waits on opens: *Waiting for an answer …* opens the page where it is answered, *Both wait for "…" to ship* and *3 wait for it to ship* open the piece they wait for, and *1 waits for a free machine*, *Fleet is designing 1 piece now* or *1 piece ready, not started* open that piece. Click anywhere else on the use to open it and see each piece.
- **Inside an opened use**, each piece that is not built yet says what is happening to it, and the sentence opens that piece (or what it waits on):
  - *Designing it now* (or *Writing the requirements now*, *Building it now*, *Checking it now*), with a small moving dot, while Fleet works on it.
  - *Waiting for your answer · Answer* when Fleet asked you something about it. **Answer** opens the page where you answer.
  - *Waiting for an answer from Ana Ruiz · See it* when Fleet asked someone else, named when Fleet knows who (*+1* when it asked more than one person). "Your answer" is only ever said to the person asked; the bar counts *waiting for your answer* and *waiting for an answer* apart.
  - *Waiting for its pull request's checks now* while its pull request's checks run after it was built. Fleet checks it once they finish; no machine is needed until then.
  - *Waiting for a free machine* while it waits for its turn, or *No machine can take it right now* when no machine is set up to do that step. **The Queue** shows why.
  - *Waits for "Keys rotate in place" to ship* when it depends on another piece that has not shipped yet. The name opens that piece; several are shown as the first one and how many more.
  - *Ready, not started* when nothing holds it back and Fleet has not started it.

  The page never names the machine or says how long something has been running.
  The page updates on its own while Fleet works, so you do not need to reload it.
- **At the foot**, quiet notes: where it lives in the code, and what builds it.

**Work** lists everything open on the feature: its slices, PRDs, tasks and bugs, each saying what placed it here, and the programs that touch it. **Activity** appears once its owners have changed.

[Open Features](#areas)

## Give every slice a feature

Every slice must name a feature. Slices that do not are counted under **Needs a feature** on the Features page, and **Fix them** opens a page that lists each one with the reason it could not be placed, together with the open PRDs, tasks and bugs that nothing places. Fix a slice in your knowledge base: `slice:edit` and `slice:refine` add a feature to a slice that lacks one, and a new slice always gets one.

`slice:edit` — Change one slice's Verified by, Depends on, Done when, or the ## Bar in its detail file — with the resolution, disjointness, acyclicity, digest-binding and retro-fit refusals a hand-edit does not have.

> **Careful:** A feature's short name that matches no feature map in your knowledge base is an error. Add the feature first, or pick an existing one.

## Start a slice no program drives

(If this repository plans by areas.)
In your repository a new slice names a feature and no program. A slice a plan created starts by itself; an older one waits until you start it.

(If this repository plans by programs.)
In your repository a slice can name a program, and its program drives it. A slice that names a feature and no program has nothing driving it until you start it.

A slice with a feature, no program and nothing started shows **Start this slice** on the feature's **Work** tab and on the slice's own page.

1. [you] **Press Start this slice.** The box says what it will do: refine what is missing, write the PRDs and design them, and stop when a person is needed. Nothing else on the feature is touched.
2. [fleet] **The fleet asks for each planning step.** The box lists what it is asking for and what is not started yet, with the reason.
3. [you] **Answer its questions.** They come to the [Cockpit](guides/daily/cockpit) like any other.
4. [fleet] **Planned PRDs go to the ordinary queues.** Building and verifying work as for any other PRD.

**Stop** retires the planning steps the fleet asked for and has not finished. Steps a person asked for stay.

Next: Add a feature and plan its work (guides/plan/add-and-plan-a-feature) · Features, uses and capabilities (knowledge-base/feature-areas) · Planning by areas or by programs (knowledge-base/planning-modes)

---
- **feature**: A part of the product a customer would name, such as sign-in or parts management, described by a short brief and a few uses; it never finishes.

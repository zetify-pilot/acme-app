# Journeys

A journey follows one person through a whole job, from the moment they need something to the moment it is done. It is how the knowledge base says "this is what using the product is like", in steps a person or an agent can walk and check.

## What a journey is

A journey starts from a real reason someone opens the product, not halfway through a screen. It is written as a job statement:

> *When* I own the quality of a product that agents change every day, *I want to* see what has been checked, how deeply and with what result, *so I can* trust what ships without reading every report.

Then it lists the steps of the happy path, the branches that go another way, and numbered acceptance criteria. Each criterion is something anyone can check on the running product, and it keeps its number when the journey is edited, so a check result can name it.

## Two sizes

| | Where | What |
|---|---|---|
| **Flow** | `knowledge/journeys/flows/` | One reusable stretch for one kind of person: "add a worker", "brief a check". Completes on its own. |
| **Map** | `knowledge/journeys/maps/` | A whole job strung from several flows. It names the flows and owns the hand-offs between them, without restating them. Optional: your repository's `knowledge/FILE-TYPES.md` must register `journeys/maps/` before the check accepts one. |

## What a journey file carries

The front matter of a flow names who it is for and what it touches:

- `id:` its short name, the same as the file name. PRDs, feature maps and audits cite a journey by it.
- `persona:` the kind of person walking it.
- `surfaces:` the pages, commands or files the person touches along the way.
- `owning_prd:` the PRD that built it, and `covers:` the capabilities it exercises.

A journey holds no ship-state. Whether its PRD has shipped is read from the PRD.

## The layout a journey file must have

The knowledge check reads these sections by their exact spelling. Another heading, such as `## The path`, or a bold lead such as `**When this happens.**`, is not read: the journey page draws no job and no steps for it, and the check fails the file.

| Section | Flow | Map |
|---|---|---|
| Front matter: `id`, `kind`, `persona`, `surfaces` (flow) or `composes` (map) | required | required |
| `**Job statement:**` followed by one paragraph, *When …, I want to …, so I can …* | required | required |
| `## Happy path` with numbered steps (`1.`, `2.`, …) | required | not used |
| `**Branches (…):**` clauses | optional | optional |
| `## Acceptance criteria` with numbered criteria | needed for the Quality desk to check anything | same |

`**Preconditions:**` and `**Trigger:**` paragraphs are optional. A flow has `kind: flow`, a map has `kind: journey`.

A minimal flow:

```markdown
---
id: add-a-worker
kind: flow
persona: Platform Engineer
surfaces: [/workers]
---

# Add a worker

**Job statement:** *When our control plane is running, I want to paste one command, so I can add capacity.*

## Happy path

1. **I open the Workers page.** It shows *Add worker*.
2. **I run the command.** The worker appears in the list.

## Acceptance criteria

1. `[dev]` An install with no workers shows *Add worker*.
```

## Say where each step happens

A journey page draws the happy path as a numbered timeline. Each step can show the place it happens and the capabilities it uses, and each branch can sit under the step it leaves from. The file says so with a short note in curly braces at the end of the step or branch. All of it is optional.

```markdown
## Happy path

1. **I open the Fleet page.** An install with no workers shows *Add worker*. {on: Fleet page; covers: CAP-XXXX}
2. **I run the command on the machine.** It asks me for the code at a prompt. {on: Worker machine; covers: CAP-YYYY, CAP-ZZZZ}

**Branches (dispositioned below, not separate flows):** the code expired (the prompt says so and asks for a fresh one) {step: 2}; I run it again on an enrolled machine (it says so and changes nothing).

## Acceptance criteria
```

- `{on: <place>; covers: <capability ids>}` closes a step. `on` is a short label for the page or machine. `covers` lists the capabilities the step exercises, and they should be ones the journey's own `covers:` already names.
- `{step: <n>}` closes a branch and names the step it hangs off. A branch with no note is listed under the happy path instead.
- A step with no note shows no place and no capability chips. Fleet never works them out from the wording, so write a note only when you are sure.
- A note Fleet cannot read, such as a misspelt key or a step number that does not exist, is left out of the text and listed at the foot of the page, so a typo shows.

A `covers:` entry in the front matter may carry a repository prefix, as in `fleet:CAP-WWWW`. The prefix names the repository whose corpus holds the capability. When it names the repository being read, the page resolves it. When it names any other, the page lists the entry as unresolved rather than leaving it out.

## Why the criteria matter

Each numbered criterion of a journey is a promise: something the product says will always hold. The Quality desk checks them, and a capability no journey criterion covers shows up as something nothing could catch breaking. See [Promises and requirements](knowledge-base/promises).

## Who writes journeys

A PRD names the journeys it realises or changes, and adds one to the catalogue when the job it serves is missing. Describing an existing code base drafts journeys for the features a person has confirmed, and the person confirms their criteria.

`prd:create` — Interactive PRD authoring grounded in the vision + agreed journey; produces prd.md and registers it in the roadmap. From an accepted proposal on the fleet, a numbered stub carrying the brief and nothing else.

## Where you see them

The Knowledge page lists every journey with its persona, linked to the capabilities it covers and the features they sit in.

[Open Knowledge](#knowledge)

Next: Capabilities and components (knowledge-base/capabilities-and-components) · Promises and requirements (knowledge-base/promises) · Read the Quality desk (guides/quality/quality-desk)

---
- **journey**: How one kind of person gets a whole job done in the product, written from the real reason they open it.
- **promise**: Anything the product committed to that a check can prove: a requirement, a shipped capability or a journey's acceptance criterion.

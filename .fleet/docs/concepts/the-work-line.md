# The Work Line

The Work Line is every step a piece of work takes, in order: from a one-line idea, through planning, building and checking, to a merged change and a closed program. Each step says who has to be there for it. Under each one, Fleet shows what is at that step right now.

> **Why:** Only a person promises something new. Everything before a person accepts a proposal is analysis. Everything after it is the fleet's work. And the agent that builds a change never merges it: only the verify step can.

## How to read it

Each step wears one chip that says who has to be there.

| Chip | What it means |
|---|---|
| **runs alone** | An agent does the step with nobody at the keyboard. |
| **asks you** | An agent does the step, and stops to ask you what only you can settle. |
| **your call** | Nothing happens until a person acts. |
| **derived** | Nobody does it. Fleet works it out from what already happened. |

A **gate** is drawn as a diamond on the line. There are two. The triage check is the gate in: every filed issue passes it in a fresh session. Verify is the gate out: every change passes it before it merges.

Open a step to see what it needs, what it produces and whether it may merge, with a link to the prompt its agent runs. A quieter command beside a step is the same step run by hand from a terminal.

Choose **Right now** to see, under each step, how many issues are there, which ones wait on you, and a link to where that work is. Choose **Just the order** to see the line on its own. Fleet remembers your choice in this browser.

## The line

Four bands, one after the other: decide what to build, make it buildable, build it, close it.

| Band | Step | Who has to be there | Run by |
|---|---|---|---|
| 1 · Decide what to build | File a feature request | your call | idea:create |
| 1 · Decide what to build | Interview the filer | asks you | intake |
| 1 · Decide what to build | Classify and propose | runs alone | route |
| 1 · Decide what to build | Accept the proposal | your call | the idea page |
| 1 · Decide what to build | A task or a bug | your call | task:create, bug:create (skips the ladder) |
| 2 · Make it buildable | Author the row or the stub | asks you | program:create, slice:create, prd:create |
| 2 · Make it buildable | Shape the program | asks you | program:shape (by hand: program:decompose) |
| 2 · Make it buildable | Refine the slice | asks you | slice:refine (by hand: slice:edit) |
| 2 · Make it buildable | Draft the PRD | asks you | prd:fill |
| 2 · Make it buildable | Design it | asks you | prd:design |
| 2 · Make it buildable | Plan it | runs alone | prd:plan |
| 3 · Build it | The triage gate | runs alone | check (the gate in) |
| 3 · Build it | Answer a block | your call | unblock |
| 3 · Build it | Implement | runs alone | prd:implement, bug:fix, task:implement (never merges) |
| 3 · Build it | Verify | runs alone | verify, prd:verify (the gate out; the only step that merges) |
| 3 · Build it | Merged — the PRD is shipped | derived | — |
| 4 · Close it | The slice reads complete | derived | — |
| 4 · Close it | Name the composed proof | asks you | program:prove |
| 4 · Close it | Close the program | runs alone | program:ship |

Alongside bands 3 and 4, `program:deliver` runs one Delivery Lead cycle: it releases what is ready into triage, detects stalls and asks you about everything blocking. A change verify refutes goes back to the builder (`rework`) until every line of the verifier's ledger closes.

## What the shape tells you

- **The ladder is one step, not three.** Shaping a program, refining a slice and drafting a PRD are the same step at three tiers: write the promise before its contents. A piece of work passes through its own tier, not all three. While a slice is unshaped, refining it is its only next step.
- **Tasks and bugs skip the ladder.** They are born in your tracker and go straight to the triage gate. That is why you will not find one under a slice.
- **Verify sends work back.** When the verifier finds a claim that does not hold, the issue goes back to the builder with the verifier's open lines, and the loop repeats until every line closes.
- **The end is worked out, not written.** A PRD ships when its pull request merges. A slice reads complete when the PRD that proves it ships. Nobody flips either by hand.

## Underneath the line

Three machines run underneath the line. The third, an issue's position in your tracker, is drawn just above, under the line, with how many issues sit at each position now. The other two are here.

### A feature request

| From | Event | To | Who |
|---|---|---|---|
| `filed` | The intake run starts | `shaping` | asks you |
| `shaping` | The filer answers the last round | `shaped` | your call |
| `shaped` | A person sends it to routing | `routing` | your call |
| `routing` | The route run writes its proposal | `routed` | runs alone |
| `routed` | A person accepts it | `creating`, then `created` | your call |
| `routed` | A person sends it back with a note | `routing` | your call |
| any | Withdrawn or a duplicate | `parked` (never closed) | your call |

### A shaping run

The same machine runs for a program, a slice and a PRD.

| State | What it means | It leaves when |
|---|---|---|
| `unshaped` | The promise is not written yet. | A person presses start, or opens the attended command. |
| `queued` | Asked, waiting for a free machine. | A seat takes it, or it is cancelled. |
| `running` | A run is reading the repository. | It asks, it lands, it fails, or someone stops it. |
| `waiting` | A question is open on the page. | The person answers. |
| `landed` | The pull request merged; the knowledge has not shown it yet. | The next sync. |
| `confirmed` | The knowledge Fleet reads shows the change. | Someone shapes it again with a note. |
| `failed` | Several runs in a row landed nothing. | Try again, or run it yourself. |
| `stopped` | A person stopped it. | Start again. |

A shaping run is refused while the program, slice or PRD is being driven, a cycle is running, a landing is in flight, or the item is past shaping: withdrawn, proven, closed, or a PRD past its stub.

Next: How work moves from filing to merge (concepts/how-work-moves) · Who decides what (concepts/who-decides-what) · Why a second session verifies every change (concepts/verify-before-merge)

---
- **program**: A larger result that two or more slices add up to and none delivers alone, used only by repositories that plan by programs.
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.

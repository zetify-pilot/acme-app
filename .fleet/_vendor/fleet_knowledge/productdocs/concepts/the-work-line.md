---
title: "The Work Line"
kind: concept
for: [everyone]
summary: "Every step a piece of work takes from idea to closed program, who has to be there for each one, and what sits at each step right now."
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/registers/triage-partition.md
  - packages/fleet-knowledge/src/fleet_knowledge/docsmd.py
minutes: 7
---

:::lede
The Work Line is every step a piece of work takes, in order: from a one-line idea, through planning, building and checking, to a merged change and a closed program. Each step says who has to be there for it. Under each one, Fleet shows what is at that step right now.
:::

:::callout{kind="why" figure="Only a person promises something new."}
Everything before a person accepts a proposal is analysis. Everything after it is the fleet's work. And the agent that builds a change never merges it: only the verify step can.
:::

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

::embed{name="work-line"}

## What the shape tells you

- **The ladder is one step, not three.** Shaping a :term[program], refining a :term[slice] and drafting a :term[PRD] are the same step at three tiers: write the promise before its contents. A piece of work passes through its own tier, not all three. While a slice is unshaped, refining it is its only next step.
- **Tasks and bugs skip the ladder.** They are born in your tracker and go straight to the triage gate. That is why you will not find one under a slice.
- **Verify sends work back.** When the verifier finds a claim that does not hold, the issue goes back to the builder with the verifier's open lines, and the loop repeats until every line closes.
- **The end is worked out, not written.** A PRD ships when its pull request merges. A slice reads complete when the PRD that proves it ships. Nobody flips either by hand.

## Underneath the line

Three machines run underneath the line. The third, an issue's :term[position] in your tracker, is drawn just above, under the line, with how many issues sit at each position now. The other two are here.

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

::cards{links="concepts/how-work-moves, concepts/who-decides-what, concepts/verify-before-merge"}

---
type: spec
---

# Decision write-back (how a settled decision is recorded)

When a human settles something an agent could not, that answer has to reach the next
person or agent who touches the work. This spec says what that record looks like.

**Who reads it:** the implementer who picks the issue up later. They were not in the
conversation. They do not know what you considered, who found what, or how you checked.
They need to know **what to do**, **why**, and **what not to re-open**.

**Where it goes:** the issue **description** — not a comment. The record is the
`decide` answer: Fleet writes the dated section on Confirm, and readers use
`get_issue`. Comments get buried under heartbeat noise.

## The shape

```
## Decision ()
<what to do — imperative, specific enough to implement from>
**Chosen because:** <one line>
**Rejected:** <the alternative, and why not — one line each>
```

**The heading is a bare date, nothing else in the parens.** The daemon's decision
regex (`_DECISION_SECTION_RE`) requires the closing paren immediately after the date
— `## Decision ()`. Any attribution written *inside* the parens (e.g.
`## Decision (, Steffen via )`) makes the section uncitable,
so the release guard refuses a human's answer and the issue keeps looping (,
). If you want to attribute the decision, put the attribution **after the
closing paren** — `## Decision () — Steffen via ` — and
**never inside the parens**.

## The heading is the human's, and nobody else's

**`## Decision (<date>)` is reserved for a human's answer to a question the fleet
stopped on.** It is the token Fleet's decision clear and the release path read — and
neither can tell an agent's judgement from the human's (). So an agent never
writes it:

- **A run recording its own choice** — the Autonomous Decisions Log entry it puts in the
  issue description — goes under **`## Implementation notes (<date>)`**.
- **A run parking on questions** writes the 🙋 park comment (its reason for stopping), and
  if a description section is wanted, **`## Open questions (<date>)`** — never `## Decision`.

The producer commands point here rather than restating this — `autonomous-drive.md` Rule B
and its self-park row, and the execute commands' decisions-log sections. A `## Decision`
section that a human did not write is the defect this rule exists to catch.

## Keep it short

**About 15 lines.** If yours is longer, you are almost certainly narrating rather than
deciding.

Extra room is earned by **things the implementer would otherwise have to work out again**:

- a `file:line`, a commit, a PR number
- a command and its real output
- a list of work items that IS the deliverable (a frozen ledger of what must be closed)
- a scope limit that stops a plausible over-reach — *"this is not licence to delete X"*

Extra room is **not** earned by: how you found it · which agent verified what · restating
the issue body above · your own reasoning on the way to the answer · a table that repeats
the prose · "worth noting" · notes about the checkout you were working in.

Write in **plain words**. Short sentences. If an internal noun is unavoidable, give it half
a sentence of ordinary English the first time.

## Revising versus appending

- **Never touch anyone else's content**, and never touch a section from an **earlier run**.
  Append below it.
- **Your own section from this run is yours to rewrite.** If you got something wrong, or
  learned more, **edit that section in place**.

**Do not stack a correction on top of your own decision.** Two sections dated the same day,
one contradicting the other, force the reader to work out which one is current — and the
wrong guess is a real cost. One decision, one section.

## An example

**Too long** — real shape, trimmed for space:

```
## Decision ()
After investigating the registry we found 1,627 images totalling 188.6 GB. I first
believed the cause was per-commit CI pushes, but on checking the CI workflow the PR lane
builds locally and never pushes... [continues for 400 lines: the survey method, a
table of age buckets, why the first hypothesis was wrong, which agent measured it]
```

**Right:**

```
## Decision ()
Cut `delete-old-sha` from 7 days to 2 (`604800s` → `172800s`) in
``, and add a catch-all rule for branch-tagged images,
which match no delete rule today.
**Chosen because:** the 188 GB is seven days of CI output, not old images — nothing is
older than 90 days, so the original 90-day window would have reclaimed 0 bytes.
**Rejected:** retention-only (~70 MB, leaves the leak unbounded) · pushing images per
merge instead of hourly (measured ~10x worse, and breaks the hourly deploy).
**Accepted cost:** an image older than 2 days is no longer pullable, so reproducing a
week-old deploy means rebuilding it.
```

Same decision. The second one can be acted on.

## Where this applies

Any command that records a human's answer into a tracked issue — today
[`unblock`](#) and
[`program:deliver`](#). Those commands point
here; they do not restate the format.

A **durable architectural** decision is a different artifact — that is a dated document in
the **`decisions`** slot, with its own template.

## Related

- [`interview-protocol.md`](interview.md) — how you **ask**. This spec covers what
  you write down **after** the answer.
- [`triage-partition.md`](../registers/triage-partition.md) — the label and state
  transition the record accompanies. A release is valid only once the record has landed.

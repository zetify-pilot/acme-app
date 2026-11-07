---
type: spec
---

# Independent verification — a status flips on a reader with no stake in it

This spec defines the **`independent-verification`** critique rubric: what has to be shown
before a `verified-status` artifact may be produced. It is the operational form of the rule
that *the party that wrote the code never certifies it* — measured, not stylistic: before the
split, most plans were self-verified, and adversarial re-verification found that about one
shipped fix in two did not fully close the issue it claimed. The rubric is what the
independent session grades against, so "independent" means something more than "a different
process id".

It is graded wherever the spine says `critique: independent-verification` — the verify
commands' reachability gate, and any command that closes a verified claim on its own account.

## The bar

**1. A fresh session, with nothing inherited.** The verifier reconstructs what was promised
from the issue or plan as written, not from the implementer's summary of it. Anything the
implementer wrote *about* the change is a claim to test, never an input to trust.

**2. Every claim is closed at the head under review, by evidence.** For each acceptance
criterion or ledger line: the mechanism that satisfies it is located independently, the test
that guards it is neutered and seen to go red (the [negative-control](negative-control.md)
rubric, run again from here), and the result is recorded per claim — never as a single
verdict over the whole.

**3. The surface is named and driven.** A capability that works but cannot be reached is not
shipped; it is stranded backend, the commonest failure mode in the audit corpus. For each
capability: name the surface a person reaches it through — a route, an operation, a tool, a
channel; drive it from that surface, not from a harness; and **no surface is a FAIL**, not a
follow-up. Registration, allowlists and tool-exposure filters that leave the capability out
are all "no surface".

**4. The verdict is written where the next reader looks**, before any merge — on the
tracker issue, in the shape the gate expects — and the gate is what merges, never the
verifier's hand. A verdict posted only to the PR is invisible to the gate.

**5. What was not verified is said.** A claim the verifier could not test is recorded as
untested, with why. A ledger that is all-green because the hard lines were dropped is a
self-certification with extra steps.

## What it is not

Not a second implementation review. The verifier does not fix, does not restyle, and does
not widen scope; a defect found is a returned issue with the ledger line that failed. Not
green CI: CI is an input to this verdict, never the verdict. Not a re-run of the author's
own gates: those are the author's evidence and are graded here, not trusted here.

## Grading

**PASS** — every claim closed by located mechanism plus a red neuter, every surface driven,
verdict posted where the gate reads it.
**PARTIAL** — a claim closed on the author's word, a surface asserted but not driven, or an
untested line recorded honestly; the status does not flip.
**FAIL** — a claim that is open at the head, or no surface for a claimed capability.

---
type: spec
---

# Negative control — a test nobody has watched fail is not evidence

This spec defines the **`negative-control`** critique rubric: the bar a test has to clear
before a `tests` artifact counts as produced. It exists because two shipped incidents arrived
at the same rule independently and neither reached a command until the rubric was written —
three invariant tests that passed with their invariant deleted, and a fail-open containment
control whose tests were already failing, saying so, and merged green because the failure was
platform-specific. The rule they share: **a test for a control is worth nothing until you have
watched it fail.**

It is graded wherever the spine says `critique: negative-control` — the execute commands'
own gate over the tests they write, and the verify commands' independent re-check of every
test a fix names. The same rubric, two readers: the author proves it once, the verifier
proves the author did not skip it.

## The bar

For every test the run writes or relies on, four things are recorded — and a test with any of
them missing does not pass:

| Field | What it holds |
|---|---|
| **Test** | the test's stable name, in whatever form the repo's test runner addresses one |
| **Mutation** | the one-line change that *should* break it: revert the fix, invert the guard, delete the branch |
| **Result** | the failure output under that mutation, pasted — not described |
| **Restored** | confirmation the mutation was reverted and the test is green again |

**A test whose mutation leaves it green is not a test.** It is asserting something else, or
nothing. The fix is to the test, never to the record.

## The cheap traps

Each of these produces a green mutation and each has shipped at least once:

- **Asserting on state the test itself created** — the already-fixed code produces it either
  way, so reverting the fix changes nothing the assertion reads.
- **Asserting that a surface rendered** rather than that it rendered the *right thing*. A
  route that exists but calls nothing still renders.
- **A test that passes for a platform-specific reason** — skipped, short-circuited or
  tolerated on the host that ran it, red everywhere else. Its own output said so; nobody
  read it.
- **A test that proves the mock** — the fake was taught the answer, and the assertion reads
  it back.
- **A mutation that was never actually applied** — the mutation column filled from memory
  rather than from a diff. The `Restored` field exists to force the round trip.

## What it is not

Not a coverage number. A line that a test executes is not a line a test *guards*, and this
rubric is indifferent to how many lines ran. Not a review of the test's style. Not a
substitute for the verifier's own neuter check — that check re-runs this bar from a fresh
session precisely because the author's record can be wrong in ways the author cannot see.

## Grading

**PASS** — every test in the run has all four fields, and every `Result` is a real failure
under a real mutation.
**PARTIAL** — a test is missing a field, or a mutation is described rather than pasted; the
criterion that test covers comes back PARTIAL to the verifier.
**FAIL** — a test whose mutation leaves it green, unrepaired.

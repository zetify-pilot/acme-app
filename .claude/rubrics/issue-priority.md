---
type: rubric
id: issue-priority
---

# Issue priority — the rubric

**The single authority for choosing the tracker `priority` on any issue the fleet will
act on.** Before this file existed the ladder was written four times — in
[`issue-shape.md`](../process/issue-shape.md) twice, in
[`check.md`](#) §5 and in
[`audit.md`](#) §6 — with three different rubrics and two
different value vocabularies. Cite this; never restate it.

**This rubric is fleet-wide, not per-repo.** Every lane files into one tracker
workspace, so if one lane means something different by `2` than another does, the
scheduler cannot sequence across lanes. The scale is a shared slot for exactly
that reason.

## The scale

Priority is **customer harm × reach**. Both factors, always — a total outage of a
surface nobody uses is not a `1`, and a mild annoyance every user hits daily is not a
`4`.

| Value | Name | The bar |
|---|---|---|
| `1` | Urgent | Broken for everyone · data at risk · a commitment in `slot:commitments` is not holding · the fleet itself cannot ship |
| `2` | High | A real job is blocked, or a workaround exists and hurts to use |
| `3` | Medium | **The default.** Real work with a real reader, no one blocked today |
| `4` | Low | Polish, internal-only, or work whose absence nobody outside the team can observe |

`0` / `No priority` is **never** a choice. `triage` refuses a release with no priority. An issue still sitting in `Triage Queue` is the window between filing and
its check run — a state the pipeline creates on purpose — and nothing else. An issue
that has left the gate with no priority is refused.

## Two derivations, not judgement calls

- **A defect against a program's work inherits that program's rank.** Resolve the
  planning entity the issue names — a slice or a plan, in the id grammar
  `slot:planning-model` gives — and take its priority. This is the case that
  matters most and the one most often eyeballed instead. **Where the repo fills no
  `slices` or `planning-model` slot, this derivation does not apply**: rank by the scale
  alone and say so.
- **An audit finding maps from its severity**, per
  [`finding-severity.md`](finding-severity.md): S1 → `1`, S2 → `2`, S3 → `3`, S4 → `4`.
  The severity was already argued on the checklist's own scale; re-deriving a priority
  from feel discards that work.

## PRD frontmatter uses words, and it is the same ladder

A PRD's `priority:` is `urgent | high | medium | low` because
the `prd-projection` pass of the fleet's `corpus-sync` loop projects it onto the issue at create
time. Same four rungs, same bar — a PRD that omits it falls back to Medium so no issue
is ever left unprioritised, but the fallback is a safety net, not a default to lean on.

## The failure this exists to prevent

 shipped **ten no-priority releases in one morning** because the release
mechanism took priority as an optional argument. The mechanism now refuses
without it. A rubric that lives in one file is the other half of that fix: a second
copy drifts, and the copy a session happens to read decides the answer.

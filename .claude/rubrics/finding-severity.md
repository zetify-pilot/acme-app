---
type: rubric
id: finding-severity
---

# Finding severity — S1–S4

**The single authority for grading a finding**, used by every audit type and by any
command that files evidence. Each of the ten audit checklists carried its own copy of
this scale; they now cite this one.

| Severity | Name | The bar |
|---|---|---|
| **S1** | broken | The job cannot be completed · data is wrong · a 5xx · a **silent** failure |
| **S2** | impaired | The job completes with a workaround or confusion · misleading state · a critical step of the job map is missing |
| **S3** | friction | Extra steps, weak feedback, inconsistency, naming |
| **S4** | polish | Visual, spacing and typography nits |

Severity maps to tracker priority 1:1 — see [`issue-priority.md`](issue-priority.md).

## A synthesis pass is a finder, and its severities get the same scrutiny

Cross-unit synthesis clusters findings and grades the *cluster*, reaching for generic
reasoning ("this cracks a core platform claim") that is not the same thing as S1. Grade
a synthesis-assigned severity against this scale exactly as you would a finder's.

Recorded on a full web-app run: a governance-**disclosure**-completeness theme
was scored S1 on "cracks the governed-by-construction claim" when the access profile
still narrowed correctly and only the UI's account of *why* was incomplete. That is
**S2 misleading state** — which is how the individual finder had graded it before
synthesis escalated it.

## What a severity is not

It is not urgency-to-us, not effort, and not how annoyed the finder is. It is the
**state the user is left in**. A one-line fix for a silent data-loss path is S1; a
month of work to unify spacing is S4.

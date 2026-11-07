# Records: check results, audits and retros

Most of the knowledge base says what should be true. Records say what actually happened: this check ran on this commit and this is what it found; this audit looked at this ground; this run took three attempts and here is why. A record is written once and never changed.

## Check results

A check result is one small file for one run of a check, under `knowledge/audits/results/`, in a folder for the kind of check (security, UI, API and so on). It records:

- **What was checked**: the target, such as a capability id, and the kind of check.
- **Against what**: the commit, and whether the run used the live product or only read the code.
- **What it found**: a verdict for every criterion or checklist item, either pass, fail, blocked or not applicable, with a reason for the last two.
- **Whether it finished.**

A real one from Fleet's own repository, abridged:

```json
{
  "kind": "security",
  "target": "CAP-XXXX",
  "commit": "9a7d1b869",
  "environment": "code-only",
  "finished": true,
  "verdicts": [
    { "id": "security/relay-redaction", "verdict": "fail" },
    { "id": "security/secret-at-rest", "verdict": "pass" }
  ]
}
```

The Quality desk is worked out from these files every time Fleet reads the repository, never kept by hand. A promise reads as passing only after a finished run against the live product; a run that only read the code shows as a state of its own. Results are kept for a fixed time and then pruned, always keeping the latest for every target and kind (see the Knowledge file types reference).

Check results are written by the commands that run checks. To check one promise on a named environment:

`qa` — Check one shipped promise on a named environment: write or rerun its scenario, drive the product, record a v2 result with platform evidence, file each failing assertion, and land scenario plus result by one PR.

## Audit records

An audit looks at a whole stretch of the product against one checklist, such as security or UI, and files what it finds as issues. It leaves a dated record in `knowledge/audits/`, in a folder for its type, saying what it covered, on which commit, and what it filed. For any stretch of the product, the newest record is the one that counts.

Each audit type has its checklist in `knowledge/specs/`, named for the type, such as `security-audit-checklist.md`. Your repository's `audit-profile` slot names the types it runs and where their records go.

`audit` — Checklist-driven audit: partition the ground, fan out one fresh sub-agent per unit, refute, synthesize → rolling record + filed findings.

## Retros

A retro is what an agent writes after it finishes a run: what went well, what got in the way, and what it would change. There is one per PRD under `knowledge/retros/prd/`, and one per task or bug under `knowledge/retros/task/` and `knowledge/retros/bug/`, named by the PRD number or issue key.

Retros are read in bulk. When the same friction shows up across runs, the improvement command turns it into a change to the procedure that caused it:

`process:improve` — Turn recurring retro friction into concrete edits to the SOP or command behind it — applying the additive fixes, proposing anything that changes a standing rule.

> **Why:** A record that could be edited later stops being evidence. That is why check results, audits and retros are only ever added to, and why the Quality desk reads the results themselves rather than a table someone keeps.

## Where you see them

The Quality desk shows what has been checked, how recently and with what result, drawn from these files.

[Open the Quality desk](#quality)

Next: Read the Quality desk (guides/quality/quality-desk) · Read a verify verdict (guides/quality/verdicts) · Promises and requirements (knowledge-base/promises)

---
- **check result**: One small file under `knowledge/audits/results/` that records one run of a check: what it looked at, the verdict and the evidence.
- **audit**: A check of a whole stretch of the product against one checklist, such as security or UI, that files what it finds as issues.
- **retro**: What an agent writes after it finishes a run: what went well, what got in the way and what it would change.

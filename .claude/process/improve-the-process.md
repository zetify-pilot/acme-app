---
type: sop
slug: improve-the-process
title: Improve the process
automated_by: 
---

# Improve the process

> Close the learning loop: read the retro corpus, find recurring friction, and turn it
> into edits to the **SOP or the repository's command** that caused it. This is what stops the
> same friction recurring run after run.

**Automated by:** the process-improvement routine — harvests the `slot:retro-corpus` records and
proposes or applies the edits.

## When this applies
Periodically, or whenever a suggestion keeps recurring across retros. Each execute run
writes a retro with a `## Suggestions (NOT applied)` table and `## Recurring …` section;
those are deliberately **recorded, not applied** at run time — this SOP is where they get
acted on, off the critical path of any single run.

**"Periodically" was too weak a trigger and the measurement says so.** The corpus reached 600
retros and 87 distinct outstanding suggestions against **one** commit in repo history that
describes itself as a harvest. A trigger that competes with feature work for a human's
attention loses every time, so it is now a **standing obligation with a mechanical entry
point**: run this whenever the Step 1 digest's **Recurring** section is non-empty, and treat
a recurrence that has survived two harvests without a resolution or an issue key as a defect
in *this* SOP rather than a low priority. The tooling has never been the gap — the ledger,
the probe and the two-tier rule all predate this note. The gap is that nothing obliged anyone
to run them, and nothing outlived the run that did.

## Steps
1. **Harvest.** `python3 knowledge/scripts/harvest_retros.py --probe` aggregates the `## Suggestions` /
   `## Recurring` entries across `slot:retro-corpus` / `:task` / `:bug` **in this repo and in
   every sibling lane repo that carries its own corpus** — a lane run's retro is committed
   in the lane repo, riding the lane deliverable PR . Above the per-suggestion
   table it prints the real promote signal — a **Recurring** section (author-self-flagged
   recurrence + suggestions sharing a distinctive artifact token; the `×` column only counts
   *character-identical* suggestions, so paraphrased recurrence is invisible there) — and,
   under `--probe`, a **Likely already built** section flagging suggestions whose named
   artifact already exists. **Incrementality is the ledger, not a window:** it reads its own
   resolve ledger and omits every occurrence a prior run resolved, so a plain
   run shows only what's outstanding (a `--since` date only narrows a backfill; `--all` shows
   resolved occurrences too, tagged `[resolved: <status>]`).
2. **Locate & check the target — for every bucket.** Open the target — a spec the repo's slots name, a command or process document (in
   `fleet-knowledge`, see step 3), an SOP here, or a tooling file — and discard
   anything it already satisfies. This gate covers **propose and file-a-task too, not just
   applied edits**: an "add a lint for X" from an older retro is usually already built, so grep
   before proposing it (the `--probe` hits pre-flag many).
3. **Apply the two-tier rule** (mirrors the audit command's checklist-improvement step):
   - **Clearly additive / low-risk** (a clarifying sentence, a new gotcha row, an
     unambiguous threshold) → **apply directly** and ship via a throwaway branch + PR —
     **in the repo that AUTHORS the target.** A command, a `.claude/process/*` document, a
     register or a rubric is generated in a consuming repo and authored in the fleet source repository
     under `packages/fleet-knowledge/src/fleet_knowledge/commandtree/`; an edit made in the
     consuming repo is destroyed by the next `fleet commands sync` without anyone deciding
     to discard it.
   - **Alters or removes a standing rule** → **propose only**, surface for human ratification —
     **and file it, in this run, as a tracked `Type:task` tracker issue in `Triage Queue`**
     naming the retros it recurred in. *"Propose only" is not a terminal state*, and treating
     it as one is where this loop actually leaks: a proposal lands in a report or a PR body,
     the run ends, nobody ratifies it, and the next harvest re-surfaces the same item — which
     is why 48 of the corpus's 51 suggestions still read *record-only / not applied* and
     exactly one commit in repo history describes itself as a harvest. A proposal with an
     issue key survives the session that made it; one without does not. Filing is **not**
     ratification — the issue carries the proposal to a human through the queue that already
     exists, instead of inventing a second one nobody reads.
   For every suggestion resolved this way — applied, or discarded because the target already
   satisfies it — **record the resolution in the ledger**: `python3 knowledge/scripts/harvest_retros.py --probe`
   --resolve <hash> <applied|already-satisfied> [note]`, using the `Hash` column from the
   Step 1 digest. This is what stops the *next* harvest from re-surfacing it — the retro
   itself is never touched, so a genuine recurrence (the same suggestion in a brand-new
   retro) still resurfaces on its own.
4. **Commit the applied edits** (plus the ledger updates from step 3) on a throwaway branch
   named per `slot:git-workflow`, open a PR — `main` has no direct-push path for the
   fleet identity (`slot:git-workflow`) — and arm the merge with `python3 knowledge/scripts/gh_automerge_arm.py`
   (fast, since it's doc-only and unreviewed), **unless `slot:git-workflow`
   names the lane or the path, in which case hand it to a human**; report the proposed-only
   changes for review. **An edit to a command, a process document, a register or a rubric
   is not committed here at all** — it is a PR in `fleet-knowledge`, and it reaches this
   repository as a submodule pin bump plus `fleet commands sync`, in one commit. **If a fixup push is needed to this branch after `--auto` is armed**
   (CI-discovered drift, a rebase), **disarm first** (`python3 knowledge/scripts/gh_automerge_disarm.py`
   <pr>`,  — `push.md` step 6) — never push while auto-merge is armed.
5. **Do not modify the retro files** — they're the durable record of what was learned. The
   ledger is a separate file for exactly this reason: it lets the digest stay current
   without ever touching the corpus.

## Who to involve / approvals
Additive edits are self-serve. Rule changes need a human's ratification before landing.

## Definition of done
Recurring friction has produced a concrete edit (applied or proposed) to the owning SOP or
command; the next run starts from the improved process.

## Related
- The `slot:retro-corpus` records (the corpus) · [`autonomous-drive.md`](autonomous-drive.md) (§ Flow-retro).
- The loop it closes: an SOP defines *how* → you do it → the retro captures friction →
  this SOP improves the SOP. Every execute command feeds it; so does every run.

#  Program — Ship (close a proven program)

You close a **program** — you certify that its result is actually true, and you land the
closing record as a merged PR.

**There is no status field to flip, and that is the point.** A program is complete when
every slice it kept is complete **or excused by its waiver** **and** its own proof has shipped; a slice is complete
when every member PRD is terminal **and** its proof has shipped. All of that is arithmetic
over PRD frontmatter, computed on read and stored nowhere — so nobody can write "shipped"
on a container and nobody has to remember to. What arithmetic cannot do is judge whether
the proof it counted was *real*. **That judgement is this command**, and it is the only
reason it exists.

**The judgement lands on `Verified by`, not on a cell of its own.** A `Proof accepted`
column held this attestation until , and it was filled on **0 of 13 programs** —
so the reading it gated was never once reachable, and withholding it moved nothing. Your
verdict now has teeth in the one place it can: when the named proof does not drive the
composed path, you **repoint `Verified by`** at the proof that would, and the computed
reading goes straight back off `complete` until that proof ships. A green verdict authors
no cell at all — it lands the **closing record**, the narrative of what was actually
proven, in the program's detail file.

**You are a gate, not a scribe.** Your default answer is *no*. Saying a program is done
asserts that a result someone wanted is now true, and the whole failure this repo has bled
from is that claim being made from the existence of parts. If any check below is unmet, you
**file what is blocking as work** (Step 3b) and stop — a *no* that only reports leaves the
program stuck with nobody assigned to unstick it.

Read [`knowledge-model.md`](#) → "Program" for what
a program is and what proving one means, and
[`tracking-and-execution.md`](#) → "Git
workflow" before opening the PR.

The program to close: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. Neither terminal step writes a `status:` or a cell: a pass writes the closing record, a failure moves the proof, and the reading follows from both. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "program-ship",
  "tier": "core",
  "sop": "none",
  "needs": "nothing",
  "may merge": true,
  "intent": "Close a proven program by judging four gates \u2014 and, on a failure, repoint `Verified by` rather than writing any status, because the reading is computed.",
  "loads": ["programs", "entity-model", "planning-model"],
  "requires": [
    "process-spine", "programs", "planning-model", "entity-model", "slices", "gate", "git-workflow"
  ],
  "optional": ["file-conventions", "registers-triage-partition", "tracker-identity"],
  "steps": [
    {
      "id": "resolve",
      "name": "Resolve the program",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-1-resolve-the-program"
    },
    {
      "id": "four-gates",
      "name": "The four gates \u2014 all must pass",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "step-2-the-four-gates"
    },
    {
      "id": "on-failure",
      "name": "If any gate fails \u2014 repoint `Verified by`",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-3-if-any-gate-fails"
    },
    {
      "id": "file-gaps",
      "name": "On a *no* \u2014 file every unmet gate as work, with its evidence",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-3b-on-a-no-file-every-unmet-gate-as-work"
    },
    {
      "id": "closing-record",
      "name": "If all four pass \u2014 land the closing record",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-4-if-all-four-pass"
    },
    {
      "id": "report",
      "name": "Report",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-5-report"
    }
  ]
}
```

## Step 1: Resolve the program

The program row fragments under `knowledge/programs/rows/` — match on the `PG-NN` id (accept the `Name` too, but the id is what
resolves). If the argument is empty, list the programs whose kept slices all read complete or
excused-waived and whose own proof shipped, and ask which. If it names nothing that resolves, stop and say so.

Read its row: `Kind`, `Requires`, `Verified by`, `Disposition`. Its slices are **not** listed
here — query the slice row fragments under `knowledge/slices/rows/` for the rows whose `program` key is this id; that edge is
authored on the child, in one place. Its prose, if it has any, is `knowledge/programs/PG-NN.md`.

**A `withdrawn:` or `superseded by` program does not ship — stop and say so.** It is out of
the plan by a decision the register already records, and closing it would be a second, contrary
verdict on the same row. A slice whose `Disposition` is not `adopted` is out of gate 1's
arithmetic for the same reason: the cuts a program kept are what it has to have finished.

## Step 2: The four gates — all must pass

Run all four before reporting. A reader needs the whole picture, not the first failure.
**Gates 1–3 are the derivation's own inputs**, re-read by hand so a failure lands in
conversation instead of in a browser view nobody opened; **gate 4 is the one no derivation
can apply.**

**Gate 1 — every slice under the program reads complete, or is excused by its waiver.** For each slice row naming this
program, read the frontmatter `status:` of every PRD carrying `slice: SL-NNN` for it — the
membership edge lives only there, so that query *is* the member list. A slice is complete only
when **every member PRD is terminal** (`shipped`/`cancelled`) **and its proof (`Verified by`)
has shipped**. A slice with everything terminal and no green proof is **awaiting
proof** — that is not complete, and it is exactly the reading that reported a program done while
its composed path returned 503 (PRD 0252). List any slice that is not complete, with what it
is waiting on.

**An EXCUSED slice passes this gate; a DEFERRED one fails it** (the operator's decision of
, narrowing the earlier rule that every waiver settled). A slice's `proof_waiver` states its kind. One whose kind is
`excused` — with every member PRD terminal, at least one shipped and no `Verified by` of its own —
is excused from a proof by a written decision: the program's own proof (gate 2) is what proves the
program, so the waiver does not hold the close. Name every excused slice in the closing record
("closed with SL-NNN waived") so the record says what it closed over. **One whose kind is
`deferred` says its proof is still owed** — "once the driver's live measurements land", "when the
second PRD ships" — so the slice is *awaiting proof*, not settled: **refuse the close**, name the
slice and its `owed` ("waiting on SL-NNN's proof: <owed>"), and stop. A waiver that states no kind
is read as deferred. Never reclassify a waiver here to let the program close: whether a proof is
owed is the slice's call (`slice:edit`), put to a human, not this gate's. **A waived slice with a live member PRD is not
waived work, it is open work** and fails this gate like any slice in flight. And a program whose
OWN proof is waived (``) has no proof for gate 2 to read: it
does not ship — an `excused` line parks it by that decision, a `deferred` one leaves its proof
owed; say which and stop.

**And where a slice carries a `## Bar`, complete is not enough — the slice must read `met`.**
Read the tracker for open issues whose title cites one of that slice's criterion ids
(`SL162-C3`): any open one and the slice is *complete, not met*, and the program does not
close over it. Then read the slice's `## Delivery log` for a measurement — a slice driver's
cycle record, or the program loop's own §1b line naming that slice's cells — within the last
cycle of whichever loop owns it. **No measurement is *unmeasured*, and unmeasured is not
met:** an absent issue means green only while something is running the probes, and this
gate is where that silence is refused rather than read as a pass. List a slice that is
complete-but-not-met as such, with the open issue or the missing measurement, and name the
driver (`/fleet:program:deliver PG-NN --slice SL-NNN`) as the next action. A slice whose
`Done when` names a running system and carries no bar at all is a finding here too
(`/fleet:slice:edit SL-NNN` authors one) — gate 4 below will refuse the proof anyway, but
say it at the tier it belongs to.

**Gate 2 — `Verified by` exists, names real PRDs, and names none of its own slices'.** A
program may not close without it, and on `kind: program` it is required at authoring time. If
it is absent, **stop and say the program has no proof** — do not invent one, and never borrow
a slice's: that collapses the program's completion condition into that slice's and the
validator rejects it (). Naming the e2e proof is
`/fleet:program:decompose`'s job (Phase 7), because choosing what would demonstrate the
outcome is a design decision, not a closing formality — and for a program that was already
decomposed without one,  is the surgical repair (it names
or repoints that one cell and nothing else, rather than re-deriving the decomposition).

**Gate 3 — every proof is shipped.** A proof PRD is `shipped` — not `verified`, not
`implementing`. A proof named as `drill:<stem>` is shipped when `knowledge/drills/<stem>.md`
is a `type: drill-record` whose frontmatter says `verdict: passed`; `failed` is an unshipped
proof, and a record the file does not carry is no proof at all. The record is the harness's
measurement, never a recollection — read its `daemon_sha` and its clauses the way you would
read a PRD's ACs, because gate 4 is about to ask whether what it measured is the composed path.

**Gate 4 — the proof actually drove the composed path.** The one gate no derivation can
apply, and the one that matters most. Open each proof PRD and confirm it exercises the program
end to end across **every surface the program claims** — the surfaces `slot:architecture`
names, as applicable — rather than asserting one component in isolation. For `kind: program` this is
strictly stronger: the proof must drive a surface a **customer** touches, since that clause is
the only thing standing between "platform work, honestly named" and "stranded substrate with a
roadmap bar". **`status: shipped` on a PRD proves that PRD's own ACs passed; it never proves
the whole is connected.** PRD 0252 read `shipped` across seven upstream PRDs while the composed
path 503'd throughout. If the proof is a component test wearing an e2e title, say so — that is
a finding, and the program does not close on it.

> **Know what gate 4 can and cannot do under a derived model.** Gates 1–3 are already true by
> the time you run — the derivation flipped the moment the last proof PRD shipped, without
> asking you, and since  nothing holds it back waiting for you either. So gate 4 is
> not a gate *in front of* the claim; it is a check *behind* it. When it fails, the defect is
> in the derivation's **input**: `Verified by` is naming a proof that does not prove the thing.
> Fix the input (Step 3) — never argue the program closed anyway, and **never invent a column
> to hold your verdict.** One was tried and deleted: an attestation cell that nobody filled on
> any of 13 programs did not raise the bar, it made `complete` unreachable. A verdict that
> changes an authored input is enforcement; a verdict that only withholds a cell is paperwork.

## Step 3: If any gate fails

Report a short table — gate, verdict, what specifically is blocking — and name the next action
for each failure (a slice's PRD to finish, a slice proof to author, a proof PRD to drive
through `prd:implement`).

**Gates 1–3 failing needs no edit from you** — they are read straight off the PRDs, and the
derived reading is already correct. It needs **work filed** instead: go to Step 3b.

**Gate 4 failing does need an edit, and it is the one edit this command makes on a
failure.** A `Verified by` that names an inadequate proof is a live defect: the derivation is
reading it as proof right now. Either repoint that cell at the proof that would actually
demonstrate the program —  owns that repair, and it applies
the same four refusals to the replacement so you cannot swap one inadequate proof for another —
or, when the honest answer is that no such proof has been designed, say so plainly in the
report and hand it to `prove` (which will leave the cell empty and name the PRD that needs
cutting) or back to `decompose`. Land the correction as its own PR. **Do not close the
program.**

## Step 3b: On a *no*, file every unmet gate as work

**A *no* is not finished until what it found is somebody's work.** The verdict is the gate's;
getting the program closeable is the fleet's, and it can only work on what is filed. So for
**each unmet gate, on each entity it is unmet on**, file one item — never one omnibus issue, and
never a gap folded into another's:

- **What it is:** a `Type:task` born in `Triage Queue` through the Fleet tool
  `file_issue --type task --command program:ship --title "<what must become true>" --body-file <f>`,
  labelled with the program's label. Its title is the outcome that closes the gap ("SL-NNN's bar is
  measured by a delivery cycle", "the proof drives the customer surface"); its body carries the gate,
  the entity, **the evidence you read** (the file and line, the PRD status, the missing section), and
  the next action Step 3 named (`/fleet:program:deliver PG-NN --slice SL-NNN`, a proof PRD to author).
- **Where it goes, and where it never goes.** `Triage Queue` only, **no priority, no project, no
  state move** — the filer is the wrong party to rank its own finding, and
  [`/fleet:check`](../check.md) is the gate that triages and releases it. Never `Implement Queue`,
  and never a park a person owns: escalating is the gate's verdict, not the filer's.
- **Dedupe first.** If an open issue already names the same gap on the same entity, cite its key
  instead of filing a second one.
- **A gate 4 you repointed** (Step 3) needs nothing filed: the repoint is the fix, and the drive
  delivers the new proof.
- **A gap nothing can be filed for** — the honest fix is a person's decision (cut the slice, waive
  the proof, withdraw the program) — is still listed as an unmet gate, and you file nothing for it.
  The fleet hands a *no* that filed nothing to a person rather than waiting for ever.

Then stop. The fleet waits on the keys you filed and runs this check again, in a fresh session,
once they are all done; it hands the program to a person instead when a *no* filed nothing, or
names exactly the same gaps as the *no* before it over an unchanged program.

## Step 4: If all four pass — land the closing record

**Write it in plain language.** Everything you author above a detail file's first `##` obeys [``](create.md) → *Step 2b: Write it in plain language* — literal title, headline inside 240 characters carrying a concrete example, ordinary words. That rule is authored once, there; do not restate it and do not drift from it.

There is no status to write and no cell to fill. What you land is the **record of what was
proven** — it is not state, and it cannot drift:

1. **No program row fragment is edited at all on a pass.** `Requires` and `Verified by` are
   the record of what was scoped and which proof counts; a passing gate 4 confirms `Verified by`
   is honest, and confirmation writes nothing. If you find yourself wanting a cell for your
   verdict, re-read the note under gate 4 — that column existed and was deleted unused.
   **`Disposition` is not that cell either**: it stays `adopted` on a program that shipped,
   because it records a decision about the row and never its ship-state, and the validator
   refuses `delivered`/`closed`/`done` in it by name.
2. Append a `## Closed (<date>)` section to the program's detail file
   (`knowledge/programs/PG-NN.md` — create it with the frontmatter type `slot:file-conventions` gives a program
   detail file, and no other key if the program has no prose yet): what is now true for the persona named
   in the program, the proof PRD that demonstrated it and the surfaces it drove, and the slices it
   contained. The narrative above it does not move — it is what was promised.
3. Branch, commit, PR — per `tracking-and-execution.md` → "Git workflow". Doc-only, so it
   merges fast, but it still goes through a PR: the fleet identity has no direct-to-`main`
   path. **Arm the merge the moment the PR opens**, exactly as every other document-authoring
   command does — this command declares `may merge: true`, and a declared permission its own
   recipe never spends is the same kind of untruth as a flag nobody could predict from the
   body:

   ```bash
   gh pr merge --auto --squash   # never --delete-branch: gh refuses it under a merge queue
   ```

   **Then drive it to `state: MERGED`, not to green.** **Under a merge queue the PR can read green and still not merge.** Watch it with `python3 knowledge/scripts/gh_pr_merge_state.py <pr> --watch`: `armed` and `queued` are pending, `merged` is done, and `ejected` — **removed from the merge queue**, reading OPEN and `CLEAN` with its own checks green and nothing armed — is red CI on the queue's `merge_group` commit (the script names the red checks): fix it, then push — after `python3 knowledge/scripts/gh_automerge_disarm.py <pr>`, because a queued PR's branch rejects every push — and re-arm. Auto-merge does not fire through a
   conflict, and the tell is **zero checks rather than failing ones**; the program register
   is append-shaped, so two closing PRs collide there by construction. Rebase onto
   `origin/main`, take both rows, force-push with `--force-with-lease`, and keep watching
   until the merge lands. **The permission is `true` for the same reason it is `true` on
   `program:create` and `slice:edit`: this PR carries only the closing record this command
   wrote — a narrative section and, on a gate-4 failure, one repointed cell. There is no code
   in it to certify and no second party the law was written to protect.** If a run ever finds
   itself merging anything *else* here, that is the signal the permission has been
   over-spent — split the change out and let it take its own route through the gate.
4. The commit message states what is now true for the persona named in the program, and cites
   the proof PRD that demonstrated it.

Once the merge lands on `main`, the `prd-projection` pass of the fleet's `corpus-sync` loop (`fleet-service`)
reconciles the program's label within the sync's interval — not on merge, and not when CI runs. Do not touch the tracker by hand.

## Step 5: Report

The program closed, the proof that closed it, the slices it contained, and the PR URL. If a
follow-on is obvious — a theme sibling now unblocked, a capability the next program reads as
built — name it in one line. **Also report the active-slice count** the closure freed
(`n/<slot:slices>`): a closed program is usually what makes room for the next cut.

## On the fleet — the closing check, run apart from the drive

**When the fleet dispatched you** (the mission carries a `## Shaping` block with `step: ship`, and
`$FLEET_RESULT_FILE` is set), you are the closing check of a program the fleet **drove** to proven. You
run in a session of your own, never inside a delivery cycle, because the party that delivered the
program never certifies it — the operator's decision of . Everything above holds unchanged:
the four gates, the default answer *no*, the one cell you may repoint, the gaps you file. Three things
are specific:

1. **Ask nothing.** The argument resolves, so there is nothing to choose. Write no `questions`
   result and never wait on a person: a gate that cannot pass is a *no*, said in one sentence.
2. **Say the verdict in the `landed` document** as `changed.closed` — **always**, pass or *no*. A
   run that ends without a result file is never read as a *no*: a *no* is positive evidence, and
   one with nothing written is a run that said nothing, so the fleet asks again.
   - **Pass** — the closing record (Step 4) merged:
     `"changed": {"closed": true}` over the merged PR. The fleet then stops driving the program.
   - **Gate 4 failed and you repointed `Verified by`** (Step 3) — that PR merged:
     `"changed": {"closed": false, "verifiedBy": "<the new proof>"}`. The board stops reading the
     program proven, and the drive delivers the new proof.
   - **Any other *no*** (gates 1–3, or a gate 4 with no honest replacement to repoint at): no PR,
     so `"pr": ""` and `"files": []`, and `changed` carries the evidence and the work:
     `"changed": {"closed": false, "gates": [{"gate": "1", "subject": "SL-NNN", "evidence": "<what you read>"}, …], "filed": ["<key>", …]}`
     — one `gates` entry per unmet gate per entity, and in `filed` every key Step 3b filed or cited.
     `filed` may be `[]` only when nothing could be filed; the fleet then hands the program to a person.
   - The `summary` is the one sentence a person reads beside the verdict: what is now true, or what
     blocks.
3. **The loop is the fleet's.** You never wait on the work you filed and never re-check by yourself:
   the fleet waits on `filed`, and runs this command again in a new session once every key is done.

---

## Rules

- **Never assert a program is done without all four gates green.** A program that closes on
  unproven parts is the exact failure the `Verified by` mechanism exists to prevent.
- **Never write a status on a program or a slice**, here or anywhere. Completion is
  computed from the PRDs and the proof, and neither register has a column for one. If you find
  such a field on disk, that is a leftover from the retired model — its removal belongs in a
  cleanup change, not smuggled into a closing PR.
- **This command authors no cell on a pass, and exactly one on a gate-4 failure.** The one cell
  is `Verified by`, repointed at a proof that actually demonstrates the program. `Proof accepted`
  was the cell a passing run used to write; it was deleted on  after 0 of 13 programs
  ever carried one. **Never re-add it** — the register's header check is exact and will fail the
  commit, which is the intended answer.
- **Never author `Verified by` here to make a program closeable.** If it is missing, the
  program was decomposed without naming its proof — send it to
  , or back to `/fleet:program:decompose` if the
  decomposition itself is stale. Writing it *at closing time* means choosing the proof to fit
  what already shipped, which is the reasoning backwards — and it is the hazard `prove`
  exists to defend against structurally, by making you write the demonstration sentence
  before you may open a PRD. Repointing a `Verified by` that names an *inadequate* proof
  (Step 3) is the opposite move and is required.
- **One source of truth:** the PRDs' frontmatter `status:`. Never read tracker state back.
- **A program's completion is the only one that is a judgement**, because gate 4 cannot be
  automated. Take it seriously; it is why this is a command and not a validator.

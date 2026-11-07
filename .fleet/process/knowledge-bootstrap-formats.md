# Knowledge bootstrap — the shapes it writes

`/fleet:knowledge:bootstrap` writes a corpus into a repository that has none, so there is no
neighbouring file to copy a shape from. This document is that neighbour. **Every shape below is
the one a shipped reader parses** — the Quality Desk's promise catalog, the
corpus readers behind the board, and the journey and requirement validators — so a corpus
written to these shapes is read by the QA Desk and the board on the first night, with no
migration. Where a shape is the reader's contract, the reader is named; change the reader first,
never this file alone.

**Before you write a knowledge file file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/the-folder`, `knowledge-base/journeys`, `knowledge-base/feature-areas`, `knowledge-base/promises`, `knowledge-base/capabilities-and-components`.

Where each file lives is printed by `python3 knowledge/scripts/kb_inventory.py layout` — the corpus artifacts relative to the repository's knowledge directory, and the bootstrap's own run-state artifacts relative to the repository. The headings below name each artifact by its `layout` key.

---

## Wording a promise — every capability, rule and criterion

A capability row, a requirement rule and a journey's acceptance criterion are **promises**. They
are read by people who did not write the code, many of them not native English speakers, and a QA
agent checks them from outside the code. So every one of them — in a draft (§2), a feature map
(§4), a requirement register (§5) and a journey (§6) — is written this way:

The same plain-language rule for every reader-facing text — a pull request description, an issue
title, a question, a feature brief — is in [*Writing for people*](writing.md) →
*Write for a reader who does not know the code*.

1. **One idea, one plain sentence.** A rule is one sentence of at most 20 words, two short
   sentences at most. A capability is a short name (at most about 8 words) plus one sentence on
   what a person can do with it: `**Name** — sentence`.
2. **The product's words, not the code's.** Name what a person sees: pages, buttons, issues,
   sessions, keys, workers. No file paths, function or class names, routes, HTTP status codes,
   environment variables, setting keys, table or column names, or backticks in the sentence.
   Those go in the **Evidence** column (a register's `Source`), where QA and engineers find them.
3. **Precise, not vague.** Keep who, what and when. Keep every exception ("unless the agent is
   archived"): a rule without its exceptions is wrong exactly where QA will test it. "Works
   correctly" or "is handled" is never a rule.
4. **No tuning numbers.** A limit, timeout, size or count someone may tune is written as "a
   per-key limit" or "a time limit", and the number goes in the Evidence column. Keep a number
   only when the number *is* the promise ("at most one claim per issue").
5. **Say who.** An operator, an engineer, a decider, a person, an agent, a worker, a customer —
   never "the caller" or "the principal".
6. **Active and positive where possible.** "Only a person can release a decision", not "a
   decision is not releasable by a non-person principal".

Before (31 words, code in the sentence):

> Every `/api/setup` route refuses a request the sign-in proxy did not stamp, and every setup
> write refuses a request without its own intent header; nothing is written on a refusal.

After (17 words; the route and the header move to Evidence):

> Only a signed-in person who confirms each change can change the setup. A refused request
> changes nothing.

Before (tuning numbers as the promise):

> Each key is held to a per-purpose limit per 60-second window (person-full 600, …, report 30) …

After:

> Each kind of key has its own call limit. A key over its limit is refused until the limit
> resets, and the refusal says so.

A requirement row may end with a *Testable: …* sentence saying how to observe it; that sentence
does not count toward the length, but it is still plain words. `fleet check --only
promise-wording` lists the rows most likely to miss this standard — advisory, never a failure.

---

## 1. The progress file — `layout: progress`

The bootstrap's only memory between sessions. It is **checkout-scoped run state, never
committed**: it lives under `.claude/run/knowledge-bootstrap/` (the path `layout` prints), which
git ignores, so it can never ride into a step's branch, commit or pull request. The corpus it
describes is committed; this ledger is the agent's working memory. Nothing in it is derived from
a tracker; everything in it is re-checkable against the tree.

```markdown
---
type: bootstrap-progress
started: YYYY-MM-DD
inventory_at: <commit sha the inventory was scanned at>
---

# Knowledge bootstrap — progress

## Phases

| Phase | State | At commit | Note |
|---|---|---|---|
| 0-survey | done | 4ffd25b5 | 1320 surfaces, 539 units |
| 1-components | done | 4ffd25b5 | 41 components, 97.2% of files owned |
| 2-capabilities | in-progress | | 3 of 41 components confirmed |
| 3-feature-areas | blocked | | waits on 2 components confirmed (have 1) |
| 4-journeys | blocked | | |
| 5-qa-readiness | blocked | | |

## Components

| Order | Component | Read at | Surfaces | Described | CAPs (draft/confirmed) | Rules (draft/adopted) | State |
|---|---|---|---|---|---|---|---|
| 1 | bug-tracker | 4ffd25b5 | 38 | 38 | 21/19 | 14/9 | confirmed |
| 2 | access-profiles | 4ffd25b5 | 52 | 47 | 33/- | 22/- | awaiting-review |
| — | job-runner | | 9 | | | | not-started |

## Unread

- access-profiles · `internal/access/` (12 files), `internal/access/narrow/` (5 files) — not read
  yet; the next invocation continues here. The component stays `drafted` until this list is empty.

## Open questions

### Q-7 · phase 2 · access-profiles · asked YYYY-MM-DD
<the question, interview-card shaped: what the work is, one concrete example, options with a
rationale on each, the recommendation first>

**Answer:** <blank until answered — by the person, in this file or in the live session>

## Answers

- **Q-3** (YYYY-MM-DD, A. Person): <the answer, verbatim or faithfully paraphrased> → <what it changed>

## Findings

- <something the code does that looks wrong, found while describing it — file:line, and why.
  Never silently described as a promise and never silently dropped.>
```

**States.** A phase is `blocked` → `ready` → `in-progress` → `done`. A component is
`not-started` → `drafted` → `awaiting-review` → `confirmed`, or `stale` when its owned paths
changed after `Read at` (re-read it; never re-ask what is already answered). A component stays
`drafted` while `## Unread` names a directory or file it owns; it is confirmed only when that
list is empty. A pass that read only part of a large component is never confirmed.

**Order** is the person's, from Phase 1. `—` means not chosen yet.

## 2. Drafts — `layout: drafts`, one file per component

What Phase 2 proposes and the person has not yet reviewed. **A draft mints no id**: an id is
permanent the moment it is committed to a register or a map, so only what survives review gets
one. It lives beside the progress file under `.claude/run/knowledge-bootstrap/drafts/` — run
state, never committed — so a review can happen in a later session in the same checkout. The
Capability and Statement cells are already worded to [*Wording a promise*](#wording-a-promise--every-capability-rule-and-criterion):
the person reviews the promise they will keep, and every code name stays in Evidence.

```markdown
---
type: bootstrap-draft
component: access-profiles
read_at: 4ffd25b5
---

# access-profiles — draft

## Capabilities

| # | Capability (name — one sentence) | Area (provisional) | Evidence | Tested by | Verdict |
|---|---|---|---|---|---|
| c1 | **Per-user narrowing of an access profile** — a workspace admin limits which records one agent can read. | governance | <pkg>/narrow.go:41 · POST /api/…/narrowings | <pkg>/narrow_test.go | |

## Rules

| # | Statement (one plain sentence) | Kind | Evidence | Confidence | Verdict |
|---|---|---|---|---|---|
| r1 | A profile can only narrow its parent's reach, never widen it | invariant | narrow.go:88 rejects a superset · narrow_test.go:TestWiden | tested | |

## Not described (with reason)

- `GET /api/debug/profiles` — operator debug endpoint, `kind: substrate`.

## Suspicious

- <behaviour that may be a bug — file:line, why — moved to the progress file's Findings at review>
```

`Verdict` is the person's: `keep`, `drop`, or an edited statement. **Confidence** is the agent's
and is one of `tested` (a test asserts it), `enforced` (code enforces it, no test), `observed`
(the code happens to do it — the weakest; most `observed` rows are accidents, not promises).

## 3. Component registry — `layout: components` (`slot:components`)

Read by the board's corpus reader and the component resolver: a `## Layers` table (id, name,
description — positional) and a `## Components` table whose **fourth** column is `owns`.

```markdown
---
type: architecture
---

# Component registry

## Layers

| layer | name | description |
|---|---|---|
| surfaces | Surfaces | Every way a person or a machine reaches the product. |
| governance | Governance | What every read and action passes through. |

## Components

| id | name | layer | owns | depends_on | description |
|---|---|---|---|---|---|
| access-profiles | Access Profiles | governance | internal/accessprofile, <queries>/access_profiles.sql | auth | Decides what an agent or a person may read, and narrows it — never widens it. |

## Surface ownership

| component | route prefixes |
|---|---|
| access-profiles | /api/workspaces/{workspaceId}/access-profiles, /api/workspaces/{workspaceId}/narrowings |

## Unassigned code

| path | reason |
|---|---|
| spike | an exploratory benchmark; no product behaviour |
```

`## Surface ownership` is needed only when routes are declared centrally (one API spec file, one
handler package): `kb_inventory.py coverage` attributes a route to its longest claimed prefix
before falling back to its handler's file.

`owns` is comma-separated path prefixes; **one owner per path** (longest prefix wins).
`depends_on` must be acyclic. **No status column, ever** — a component never ships.

## 4. Feature map — `layout: feature-maps`, one file per area (`slot:feature-maps`)

Read by the board's corpus reader and the journey validator. The capability table is the promise
source for capabilities: a row whose `Ships in` is `(shipped)` or `(core)` is a **shipped
promise** the QA Desk will check.

```markdown
---
type: feature-map
area: governance
kind: product            # or `substrate` — the honest answer when no customer would name it
components: [access-profiles, auth]
journeys: [narrow-an-agents-reach]
surfaces: [/settings/access-profiles, /settings/access-profiles/{id}]
source_of_truth:
  - <pkg>/
  - <web-pages>/AccessProfilesPage.tsx
brief:
  summary: >-
    <one sentence: what it is, and for whom>
  problem: >-
    <two or three sentences: what goes wrong without it>
  example: >-
    <three or four sentences: a named person doing a real job with it>
  example_from: [narrow-an-agents-reach]
  not:
    - <what it is not, naming the neighbouring feature>
---

# Governance

**Intent:** <one falsifiable sentence: what a customer gets from this area>

## Capabilities

### Decide what an agent may see
<one or two plain sentences: what a person does here>

| ID | Capability | Ships in | Tested by |
|----|------------|----------|-----------|
| CAP-NNNN | **Per-user narrowing of an access profile** — a workspace admin limits which records one agent can read. | (shipped) | `narrow-an-agents-reach` |

### <two to five more uses, each with its paragraph and its rows>
```

- **The H1 is the feature's name, as a person says it** (`# Governance`) — never the slug
  (`# governance`) and never a word about the document after it (`— feature capability ledger`):
  the Features page and the tracker show that line to people as the feature's name.
- **`brief:` and the `###` uses** are written to
  [*Writing a feature brief*](feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited)
  — uses (at least three when it has three rows), every row under one, plain words, no ship-state. The `feature-briefs` check
  reads them.

- **`Capability`** is a short name and one sentence, worded to
  [*Wording a promise*](#wording-a-promise--every-capability-rule-and-criterion); routes and code
  names stay out of it (the map's `surfaces:` and `source_of_truth:` carry them).
- **Ids:** `CAP-NNNN`, four digits, opaque and global. Allocate with
  `python3 knowledge/scripts/validate_id_collisions.py --allocate CAP <count>` when the
  repository has an `origin`; with none, take the next numbers above the highest in the corpus.
- **`Ships in`** for existing code is `(shipped)` — built outside the PRD pipeline. Never `—`
  (that reads as "not built", and the planner turns absence into work).
- **`Tested by`** names a journey slug once Phase 4 writes one; `—` until then.
- **`Plain`** (optional, the last column) is the row's short plain title — at most 60 characters, no
  brackets, arrows, slashes or ids, saying what a person can do or get
  ([*Plain titles*](feature-doc-reconcile.md#plain-titles--every-capability-row-and-every-prd-that-is-created-or-changed)).
  Declaring it means declaring `Anchor`, `Needs` and `Source of truth` before it, padded with `—`.
- `source_of_truth:` is what makes `kb_inventory.py coverage` count a surface as described.

## 5. Requirement register — `layout: commitments`, one file per domain (`slot:commitments`)

Read by the requirement-register loader and its validator. **Only an `adopted` row
of kind `invariant`, `requirement` or `constraint`, with a blank `Cut`, is a promise** the QA
Desk will check.

```markdown
---
type: requirement-register
domain: governance
prefix: GOV
components: [access-profiles, auth]
---

# Governance — requirement register

## Source legend

| Tag | Points at |
|---|---|
| `narrow` | [narrow.go](<relative link to the file>) |
| `narrow_test` | [narrow_test.go](<relative link to the file>) |
| `progress` | [the bootstrap progress file](<relative link to it>) |

## Rows

| ID | Statement | Kind | Disposition | Cut | Needs | Source |
|---|---|---|---|---|---|---|
| GOV-NNNN | An access profile only narrows its parent's reach; it never widens it. | invariant | adopted | | | narrow "rejects a superset" · narrow_test "TestWiden" · progress "Q-NN" |
```

- **`Statement`** is one plain sentence worded to
  [*Wording a promise*](#wording-a-promise--every-capability-rule-and-criterion); the code names
  and tunable numbers it rests on go in `Source`.
- **One register per domain**, a domain being a Phase 1 layer unless the person splits it.
  Prefix: 2–4 capitals, unique across registers.
- **`Source` is load-bearing, and checked.** Tokens are separated by ` · ` and written **bare — never in backticks**, which the
  validator does not strip; each is
  `<tag> "<fragment>"`, the tag resolved through the register's **Source legend** table to the
  file it cites, the fragment a short verbatim phrase from that file (a function name, a test
  name, a refusal message). The register validator verifies the tag resolves to a file that
  exists — a `path:line` citation it cannot verify and only counts as skipped, and it rots on the
  first insertion above it. Cite the enforcing code, the test, and the bootstrap question that
  confirmed the row (`progress "Q-NN"`). A row with no confirmation is not written.
- A rule the person rejected is **not written** (it was never a promise). A rule the person says
  is a bug goes to the progress file's Findings, never into the register.

## 6. Journey — `layout: journeys`, one file per journey (`slot:journeys`)

Read by the board's journey reader and the Quality Desk's criterion counter. Each
numbered line under `## Acceptance criteria` is a promise `<slug>#<n>`, counted in file order —
so **never renumber or delete a criterion**; retire it by striking it through.

```markdown
---
type: journey-flow
id: narrow-an-agents-reach
kind: flow
persona: workspace admin
surfaces: [/settings/access-profiles]
covers: [CAP-NNNN, CAP-NNNN]
---

# Narrow what an agent can read

**Job statement:** *When an agent should only see one team's records, I want to narrow its
profile, so that it cannot read anything else.*

**Preconditions:** a workspace with one agent and two teams' data connected.

## Happy path

1. Open the agent's access profile. {on: Access profile page; covers: CAP-NNNN}
2. Add a narrowing to team A.
3. Ask the agent about a team B record.

**Branches (dispositioned below, not separate flows):** the narrowing names a source the agent cannot see (the page refuses it and names the source) {step: 2}.

## Acceptance criteria

1. **Narrowing applies** — after step 2, the agent's answer cites only team A records.
2. **No widening** — a narrowing that would add a source is refused with a message naming it.
```

A happy-path step may end with `{on: <place>; covers: CAP-NNNN, ...}` and a branch clause with
`{step: <n>}`; the journey page draws them as the step's place and capabilities and files the
branch under that step. Write one only when the text states it — a `covers` id must already be in
the journey's `covers:`. Leave a step or branch bare when unsure; nothing is ever inferred.

A criterion is observable from outside the code (a page, an API response, a log the platform
writes) — that is what lets a QA run drive it. Word each one to
[*Wording a promise*](#wording-a-promise--every-capability-rule-and-criterion): one plain sentence
after its bold label, saying what a person sees, with no routes, codes or identifiers in it.

## 7. Slot answers

Phase 0 replaces the stub in each mechanical slot (`knowledge/slots/<id>.md`, the file `fleet
init` wrote with a `<!-- fleet:stub -->` marker) with an `## Answers` list read off the repository
— the commands, paths and conventions a command will cite. Remove the stub marker only when the
slot is genuinely answered.

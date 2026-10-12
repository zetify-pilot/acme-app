---
type: spec
---

# Interview Protocol (how every `/:*` command asks for human input)

One contract, for every command that can reach a decision it is not entitled to make
alone. **Its short form is the interview card below, and the card is not cited — it is
inlined.** `fleet commands sync` materializes it into every command that can put a
question to a human, between `<!-- include: process/interview-card.md -->` markers, so
the text is in front of the model at the moment it asks, in every engine, with no
"read that file" step to skip. A command never restates the card in its own words: the
ten near-identical summaries this file once replaced ("options, marked recommendation,
rationale on every option") each dropped the plain-words half, and *that* short form —
not this file — is what a model follows at ask-time. The plain-words rule was then re-added
by hand four times in four weeks (, -18, -25, ) while the questions
stayed id-dense. The pointer was the failure; the card is the fix.

**The rule this exists to enforce: a decision you could have asked about is never
merely reported.** Listing an open decision back at the user is not an escalation, it
is a deferral — and a deferral that repeats every cycle is how a queue of five-second
answers becomes permanent. If a human is attached, you **interview**; you do not print
a to-do list for them.

---

## The card — what every command inlines

<!-- include: process/interview-card.md -->
### Before you ask a human anything — the interview card

**The person answering has not read the issue, the PRD, the code or any register, and
will not look anything up.** They answer many questions a day from what is in front of
them, and only that. So, every time you ask:

1. **Say what the work is first, in plain words.** One or two sentences on what somebody
   will be able to do that they cannot today. Then **one concrete example** — a named
   person doing it, and what they see. Then **one line on what is undecided**, so the
   question reads as a fork and not a quiz. This goes in the message *before* the first
   question, once per run; later questions inherit it.
2. **Ask with `AskUserQuestion`:** 2–4 options, the one you recommend first and marked
   `(Recommended)`, and on *every* option why it is right and what it costs — not only on
   the one you favour, or the human cannot pick against you.
3. **Every option says what changes for a real person**, not what changes in the code.
   *"The error would read 'this key cannot list agents'"*, not *"return a typed reason from
   the allowlist path."*
4. **No bare ids, no unexplained jargon.** ``, ``, ``, ``,
   `PRD 0242` never appear in an option label, and anywhere else only in parentheses after
   the plain name — *the goal of getting a customer live without an engineer ()*. An
   internal noun (access profile, projection compiler, cause ledger, `blockedBy`) gets half
   a sentence of ordinary English the first time it appears. `file:line` stays, as evidence,
   never as the only statement of the problem.
5. **The test, before you send:** would somebody who has never opened this repo pick the
   same option, for the same reason? If not, rewrite. Being asked to *"explain that again"*
   is a defect in the question, not a preference — re-ask in full, plainer, and hold that
   register for the rest of the run.

6. **A mockup, design or any visual reaches the person ONE way: the fleet's `ask` tool with the mockup attached** (`upload_link` the folder, then `attachments: {bundleId, entry}`). Their browser is on their own machine, not on the box you run on: **never** tell them to open a file path, run `python3 -m http.server` or visit `localhost` / `127.0.0.1`, and never carry a mockup question in the built-in `AskUserQuestion`, which has no attachment. The tool answers with a viewer link; put that link whole in what you say. One authority: `.claude/process/interview.md` → *A mockup reaches a person ONE way*.

7. **The person may not be the one who knows — every question can be answered *"I can't
   answer this"*, and you must plan for that.** The question card carries that choice itself
   (*Can't answer — carry on*); you never add it as an option, and you never invent an answer
   in its place. When it comes back: **carry on with an explicit `Assumption: <what you
   assumed and why>` line, marked unconfirmed by the owner** — or, where the right party is
   the reporter, carry the question to them as an open question — **never ask it again**, and
   list every such item under an **`Unconfirmed assumptions`** heading in what you write, so
   a human can review them later. Downstream, it is an assumption to confirm, not a fact. The
   rule, once: `.claude/process/interview.md` → *"I can't answer this"*.

**Headless — no human attached:** you write all of the above into the escalation instead,
in the same words, so whoever reads it later can answer it as filed.

Full protocol — discovery before forks, acting on the answer, where the decision is
written: `.claude/process/interview.md`.
<!-- /include -->

Everything below is the long form: when the card applies, what to do *before* you can
name options, what to do with the answer, and what a headless run writes instead.

---

## When it applies

| Command class | Behavior |
|---|---|
| **Authoring / planning** (`prd:create`, `prd:design`, `prd:plan`, `program:create`, `program:decompose`, `program:prove`, `slice:create`, `slice:edit`, `component:create`, `route`, `page:spec`, `*:create`) | Interview. These exist to turn intent into a specified artifact; an unresolved fork is the work, not an interruption. |
| **Delivery / triage** (`program:deliver`, `unblock`, `own`, `sidekick`) | Interview *and* report. Every question that unblocks work gets asked live; the written report is emitted regardless (see [Headless](#headless-the-report-is-unconditional)). |
| **Autonomous execute** (`prd:implement`, `bug:fix`, `task:implement`, `page:improve`, `push`, `audit`, `arch:reconcile`, `check`, `verify`, `prd:verify`, `intake`) | **Do not block — but an escalation is still bound to the card.** These are autonomous by default and must survive a headless fleet dispatch, so they never stop on a prompt: an open fork goes to [`autonomous-drive.md`](autonomous-drive.md) Rule G (file an issue) or Rule D (withhold the merge). **When one of them parks on a person anyway** (`needs-decision` → `Blocked · decision`), what it writes *is* the interview, asked in writing — so every one of them inlines the card and writes the [`decision` document](decision-document.md), checked by `knowledge/scripts/validate_decision.py`. Their `--manual` variants may interview at the gates their prose names. |
| **Two-mode authoring** (`route`, `slice:create`, `program:create`, `prd:create`) | Both of the above, and the variable decides which. At a terminal they are the first row. Dispatched by the fleet — `$FLEET_RESULT_FILE` set, the brief carrying an idea's dossier or its accepted proposal — **never**: `route` asks by *writing* a `questions` result and ending its turn, exactly as `intake` does, and at most one question; the three `*:create` commands ask nothing and write one row or one stub from the brief's own words. `AskUserQuestion` in that mode reaches nobody and stalls the run. |

Do **not** interview for something you can settle yourself: a convention the specs
already fix, a fact in the code, or a choice with an obvious default. Asking about
those is its own kind of noise, and it trains the user to skim.

---

## The discovery round — when the alternatives are not yours to name

**The shape below is for a *fork*: a decision between alternatives you can already name.
It is the wrong instrument for finding out what someone wants**, and using it there
inverts it — the 2–4 options become the model's guesses, the user picks the least-wrong
one, and their pick is then read downstream as a specification. A guess laundered through
a menu is indistinguishable from a requirement, which is precisely the property that makes
it dangerous.

**The entry test, before you enumerate anything:**

> Can you say, in one concrete sentence about a real person, **what somebody does today
> without this**?

If not, you have not earned the right to offer options. Ask in the open first:

- *What happens today when someone needs this, and what does it cost them?*
- *Who hits it, and how often?* — the persona is an answer, never an assumption.
- *What is this deliberately not doing?* — asked outright, because nobody volunteers a
  non-goal, and an exclusion nobody asked about is one nobody writes down.
- *What will people assume it does, that it will not?*

Open questions are asked as **plain text in the conversation**, not through
`AskUserQuestion` — the tool's contract is options, and an option list is the thing this
round exists to defer. Converge out of discovery the moment you can name real alternatives,
then switch to the shape below for each genuine fork. One discovery round is usually
enough; the answers are what make the fork questions worth asking.

**Where this is mandatory:** any command that authors a durable artifact from a request
rather than from a prior stage's output — today [`slice:create`](#)
Step 2, whose Step 3 turns these answers into permanent register rows. A command receiving
decomposition gap rows or a settled PRD has already had this conversation and skips it.

## A mockup reaches a person ONE way

**Fleet infrastructure, identical in every repo and every session type — a person's terminal, a
dispatched run, a seat. It is not a slot a repo fills:** it is stated here, once, in the `process-interview`
slot's shared text, and it binds every product built with Fleet.

A person looks at your design on **their own machine**. The box you run on has no address they can
reach, so none of these is a delivery, however they are phrased:

- *"open `knowledge/prds/…/mockups/…/index.html`"* (a path on the box);
- *"run `python3 -m http.server 8899` and open `localhost:8899`"* (a loopback on the box);
- *"I put it at `file:///…`"*, or a bare `127.0.0.1` / `0.0.0.0` URL.

The delivery is the fleet's `ask` tool **with the mockup attached**: `upload_link` the folder (it must be a
self-contained `index.html` plus its assets), then pass `attachments: [{"bundleId": "upl_…", "entry":
"index.html"}]` on the question. Fleet answers with a **viewer link** the person can click — on a
terminal it also shows on the Terminals page — and on a dispatched run it parks the question with the
mockup beside it. Show the link whole. The built-in `AskUserQuestion` carries no attachment, so a
question *about* a design is the fleet's `ask` tool; `AskUserQuestion` may take the person's answer only
once the viewer link is in the question text.

**It is enforced, not just asked.** A hook on `AskUserQuestion` refuses a question that names a mockup, a
loopback, a file URL or an `.html` path without a fleet viewer link, and says to use the fleet's `ask` tool
(`fleet_daemon.askguard`); the fleet MCP server's own instructions and the `ask` tool description say the
same. If the fleet's `ask` tool is **not in your tool list**, the session is mis-wired: say so plainly and
stop — never fall back to a path or a loopback.

## The question shape (mandatory)

Ask with the **`AskUserQuestion`** tool. (Older command prose calls this "the built-in
`question` tool" — same tool, this is the real name.)

**This shape governs a fork — a choice between alternatives you can name.** If you cannot
yet name them, you are in discovery and the section above applies first; item 1's *"never
open-ended when the alternatives are enumerable"* is that boundary, and it is a condition
to check rather than a formality to satisfy.

Every question carries:

1. **2–4 concrete options.** Never open-ended when the alternatives are enumerable.
   The tool appends an "Other" escape automatically — you do not add one.
2. **The recommendation FIRST, and marked** — suffix its label `(Recommended)`. A
   recommendation you buried in prose is not a recommendation.
3. **A rationale on EVERY option, in that option's `description` — not just the
   recommended one.** State *why* this is the right call, and what it costs: the
   mechanism ("why this works"), then the tradeoff ("Con: …"). An option with a bare
   restatement of its label is a defect — the user cannot pick against your
   recommendation if only your recommendation was argued. Where the reasoning is
   evidence-backed (a measured rate, a past failure, a line of code), cite it.
4. **One dimension per question.** Don't fold two independent forks into one.
5. **≤4 questions per round**, most-blocking first; the tool's own ceiling is 4. More
   pending → ask the blocking ones now, carry the rest to the next round.
6. **A visual question gets a visual answer.** If the fork is genuinely about layout or
   appearance, render it (browser mockup, or the tool's per-option `preview`) rather
   than describing it — and deliver a mockup only as *A mockup reaches a person ONE way* says. A question that merely *concerns* the UI is usually still
   text-shaped.
7. **Plain words, one concrete example, no bare ids — the card, above.** Not restated
   here; the card is the authority on register and it is already in the command you are
   running. The two failures it was written against, so nobody relaxes it as style:

   > **Measured.** A `prd:design` run on a composed end-to-end verification PRD opened with
   > three well-formed forks — recommendation marked, rationale on every option — built
   > entirely from ``, ``, `browser-leg-nightly`, `Arrow-IPC` and four PRD
   > numbers, with no sentence anywhere saying what the PRD does. The reply was not a
   > choice: *"I don't know what this PRD is about."* Each option was plain on its own
   > and the round still failed, because nothing in it required establishing the subject
   > before enumerating positions on it.

   > **Measured.** A `route` session asked a four-option question in which every label
   > and every rationale was built from bare ids — ``, ``, `` — and
   > the answer that came back was not a choice but *"I don't know them and I don't look
   > them up."* An option whose label is an id asks the human to go look something up
   > before they can answer — which is the deferral this protocol exists to prevent.

Shape of a good option `description`:

> Write your decision into the issue description, then move the issue from
> `Blocked · decision` to `Implement Queue`.
> **Why:** the fleet dispatches only the identifier, so the
> description is the one channel every implementer reads.
> **Con:** one more mutation class in an append-only command — so the decision write
> must be mandatory, never a silent relabel.

## Act on the answer, and persist it where the reader looks

An answer you don't act on is theater — the same failure as reporting instead of
asking, one step later. On every answer:

1. **Apply it** — make the change the answer authorizes, in the same cycle.
2. **Persist it into the artifact the downstream reader actually reads**, not into
   conversation. For the tracker-backed work that is the **issue description**, as a
   `## Decision (<date>)` section. **The shape, the length ceiling, and when you may
   revise your own section are owned by
   [`decision-write-back.md`](decision-write-back.md)** — read it before writing one;
   this spec does not restate it. **That heading is the human's answer alone:** an agent
   recording its own choice, or the questions it is parking on, never writes it — the
   agent-owned headings are `## Implementation notes (<date>)` and `## Open questions
   (<date>)` ([`decision-write-back.md`](decision-write-back.md), ).
3. **A recorded human decision is what legitimately clears a human gate.** When the
   user answers the question a `Blocked · decision` state was holding for, that state's
   condition is satisfied — by the human, live — and the item may be released. The
   prohibition on moving `Blocked · decision` → `Implement Queue` guards against a
   *model* deciding it; it was never meant to outlive the human's own answer. The
   decision write in (2) is what makes the move auditable, so it is not optional.
4. **Release it to the right place — an answer does not always mean `Implement Queue`.**
   Ask what the *answer* left behind. Nothing left but implementation →
   `Implement Queue`. Something only a human can do (mint a credential, click a console,
   merge a guarded PR) → `Blocked · action`. Something that must wait on other work → a
   `blockedBy` edge, `Implement Queue`, and no park at all. **Something that changes what
   the product promises** (a new slice, a new PRD, a reversed requirement row) → the
   unblock run **authorizes it in the same run**, while the human is attached, by
   dispatching `/fleet:slice:create` and `/fleet:prd:create`; the *PRD* is handed
   onward, never the task, because an execute run may not mint the warrant for its own
   work (Rule J). And an issue that was
   escalated **out of `Triage Queue`** goes back to **`Triage Queue`**, never straight to
   `Implement Queue` — the checker still owes the priority, project, component and
   blockers it never set. Leaving a decided issue in a park state is how a queue whose
   target is zero stops reaching it; the destinations and the reasoning are owned by
   [`triage-partition.md`](../registers/triage-partition.md).

## "I can't answer this" — the third kind of answer, and the one place its rule lives

**Why it exists (, owner decision).** A customer's idea (*"Memory & File space for a
Team"*) stopped with four questions owed to the owner — the first one *"who runs into this, and
how often?"*. The customer wrote the idea; the owner cannot know. The card offered an option or
free text and nothing else, so the whole idea sat in his queue until he invented an answer or
ignored it — and an invented answer is read downstream as a fact, while an ignored one stalls
the work. **A question put to the wrong person is not a decision they owe; it is a question
that needs another route.**

**What the surfaces do.** Every question card — the cockpit card, the idea page, the headless
channel's card — carries a plain choice, *Can't answer — carry on* (and, on an intake
interview, *Can't answer — ask the customer*). It is a **person's** action, on the same answer
route as an answer, under the same key rules; it is never offered to or taken by an agent. The
answer is recorded **on that question**: `cantAnswer: true`, optionally `forReporter: true` and
a one-line `note`, with who and when from the answer's own stamps. The interview **continues**.

**What the asking command must do on receiving one** — the same in every interview command
(interactive, `intake`, `program:shape`, `prd:fill`, `slice:refine`, `program:demonstrate`,
`prd:blueprint`), and written nowhere else:

1. **Never invent the answer, and never ask it again** — not in a later round, not reworded.
   It counts against the question budget exactly as an answer would; it is not a free retry.
2. **Proceed on a stated assumption.** Write one line, `Assumption: <what you assumed and
   why>` — what the artifact will say *instead of* the answer, and the evidence you chose it on
   (the repository, the nearest precedent, the recommended option). It is marked **unconfirmed
   by the owner**, and it is the most conservative reading that does not widen scope: an
   assumption never adds a customer-facing promise, never fills in a persona or a day an
   outcome becomes true, and never settles a fork *toward* more work. Where a part of the
   artifact cannot be written without the answer, leave it out and say so in `open` — that is
   still not a made-up answer.
3. **Or hand it to the right party.** When the note or the choice says it is for the reporter
   (`forReporter`), or the question is about the reporter's own experience, write it as an
   **open question for the reporter** — verbatim, in the filer's framing — and make no
   assumption on it at all.
4. **List every such item, under the heading `Unconfirmed assumptions`**, in what you land:
   an intake dossier's optional `unconfirmedAssumptions` field (one `Assumption: …` or
   `For the reporter: …` line each — **omit the key when there are none**, never write
   *"none"*); a PRD's `prd.md`, a slice's detail file and a program's narrative each carry a
   `## Unconfirmed assumptions` section, and a headless shaping run also repeats each in the
   landed result's `open` list, prefixed `Unconfirmed:`. A reviewer must find all of them in
   one place without reading the transcript.
5. **A command that asked nothing has nothing to carry** — `slice:refine`'s stub mode writes
   no rounds, so none of this applies to it.

**What downstream commands do.** [`check`](#), `prd:create`,
`prd:design`, `prd:plan` and the rest of the `prd:*` pipeline read an `Unconfirmed assumptions`
section as **assumptions to confirm, not facts**: they never cite one as the owner's decision,
never promote one into an acceptance criterion or a requirement row on its own authority, and
when a decision turns on one, that question is what they put to a human — *to the person who can
answer it*, the reporter included.

**What it is not.** Not a skip of the question budget, not a licence to stop interviewing, not
a way to avoid a fork the owner *can* answer, and not permission for an agent to mark its own
question can't-answer. The card is where a person says it.

## Headless: the report is unconditional

Loop, cron, and fleet dispatches have no human attached, and detecting that reliably
is not worth the fragility. So: **the written report/escalation section is emitted
every run, interview or not.** The interview is an *addition* on top of it, never a
replacement — a headless run therefore loses nothing, and no mode-detection is needed.

An escalation line written for a headless run must be **askable as filed**: state the
decision, the 2–4 options, and the recommendation. The next interactive cycle should
be able to ask it verbatim without re-deriving it.

**A fleet park asks in fields, not prose.** A run that ends `needs-decision` writes the
card as one `decision` result document — brief, quoted context, options with why, cost and
then — and checks it with `knowledge/scripts/validate_decision.py` before the sentinel
([`decision-document.md`](decision-document.md), inlined into every command that can park
there). The sentinel's summary shrinks to a headline. The service re-checks the document
with the same predicate and records every broken rule on the park as `askRefused`, so a
park that skipped the card is visible rather than merely unreadable.

## Converge

Stop interviewing when a round surfaces nothing material and the user has confirmed
the shape. Track decisions in a running summary so a later round never re-asks a
settled one.

---

## Common mistakes

- Printing "**INPUT REQUIRED:**  — needs a decision" and ending the turn, with
  a human right there.
- **Opening a round with the fork instead of the subject** — four carefully-argued
  options about a piece of work whose purpose was never stated, because the asker had
  just read the artifact and forgot the answerer had not. The card's item 1.
- **Restating the card in the command's own words.** Every summary that was ever
  written dropped the plain-words half. The card is inlined; a command cites nothing
  shorter than it.
- A recommendation with rationale and three bare alternatives.
- Asking a question whose answer is already in the specs or the code.
- Getting the answer, acting on it in-session, and never writing it down — so the next
  run, or the implementer that picks the issue up, re-derives or contradicts it.
- Recording the decision as a tracker comment and assuming the fleet reads it.
- Bolting an interview onto an autonomous execute command, breaking headless runs.
- **Offering 2–4 invented options when you do not yet know the requirements.** The shape
  above is for a *fork between alternatives you can name* — used for discovery it inverts:
  the options become the model's guesses, and the user picking one launders a guess into
  a decision the next stage reads as settled. Item 1's *"when the alternatives are
  enumerable"* is the carve-out, and nothing prompts you to check which case you are in.
  The test before you enumerate: **can you say what somebody does today without this?**
  If not, ask that first, in the open.

## Related

- [`spine.md`](spine.md) — the step vocabulary; an interview round is a
  `kind: author` or `kind: decision` step, and a human sign-off is `kind: gate` /
  `actor: user`.
- [`autonomous-drive.md`](autonomous-drive.md) — Rules D and G, the *non*-interviewing
  path autonomous commands take instead.
- [`issue-tracking.md`](issue-shape.md) — the tracker issue contract the decision
  write appends to.

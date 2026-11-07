---
description: "Turn a person's captured idea into a decision-ready dossier: read what the product already promised on that ground, interview the filer asynchronously across at most eight questions by emitting question results and being resumed with the answers, and emit one fixed-shape dossier a human can promote or decline from — or hand the filing back, told plainly, when it is not an idea at all."
---
# Intake — the front door for anything a person files

**You are the only command in the fleet that can hold a real conversation with nobody
in the room.** Every other headless command gets one shot: it reads, it decides, it
writes a verdict. You get to *ask*, end your turn, and be **resumed into the same engine
session** when the answers come back — so the reasoning that produced a question is
still in your context when you read the reply. That is the whole reason this command
exists, and it is what lets a filed sentence become something the product can actually
reason about.

Your product is **a dossier**: one fixed-shape record, nine fields (plus one optional list of unconfirmed assumptions), that a human can read
in a minute and decide from. A dossier missing a field is not a shorter dossier — it is
an unusable one, because the missing field is always the one the reader needed.

> **Version one is the IDEA path only.** Bugs and tasks do not come through here; §2
> stops on anything else. Do not shape them, do not dossier them, do not "just triage it
> while I'm here".

> **There IS an issue, and you are not the party that touches it.** Filing mints a
> `Type:idea` issue in the **`Intake Queue`** workflow state, in the same transaction as
> the `fleet_intake` row and dispatched through the outbox — so the key you were invoked
> with names *this* work, and is the id to use whenever you
> have to refer to the item. **What has not changed is that you read and write no
> tracker.** Everything you are given arrives inlined in the dispatch payload (§1), and
> everything you produce leaves as one result file plus the done-sentinel (§8, §10). Every
> move the issue makes — to `Needs answer` when you ask, to `Intake · decision` when you
> conclude — is written by **fleet**, as a projection of a decision its own database
> already made from the file you left. So reaching for the tracker — to read context, to
> park, to record an answer, to close a duplicate — still means you have left the
> contract: not because the issue is missing, but because that write belongs to the one
> party that owns it, and yours would race it.

> # ⚠️ THE FILER HAS NOT READ THIS REPO.
>
> They read your question and nothing else. Not the feature map. Not the register row
> you found. Not the component registry. **If a question cannot be answered by somebody
> who has never opened this repository, it is a defect in the question, not a gap in
> the filer.**
>
> This warning is here because the fleet has already produced the failure it names, in
> the one place it hurt most: a `route` session asked a four-option question in which
> every label and every rationale was built from bare planning ids, and the answer that
> came back was not a choice but *"I don't know them and I don't look them up."*
> Everything you learn in §3 is **evidence for the dossier**, never vocabulary for the
> question.
>
> And the mirror of it: **a question the repo could have answered is worse than
> silence.** You have a component resolver, a feature map, a requirement register and two
> planning registers. Spend them first. Every question you ask that §3 already answered
> spends the one resource this command exists to protect and teaches the filer to skim
> the next one.

> **You do not build anything, and you do not promise anything.** No branch, no commit,
> no code, no PRD, no slice row, no program row, no feature-map row, no requirement
> row. **Adding customer-facing functionality is the one call reserved for a human**
> (the repository's always-on rules), and a dossier is *evidence for that call*, never the call itself. The
> only artifacts you produce are the result file named by `$FLEET_RESULT_FILE` and the
> done-sentinel (§10) — neither of which is in the repository.
>
> **Concretely, in this session you MUST NOT:** run `git checkout -b`, `git commit`,
> `git push` or `gh pr create`; edit, create or delete any file in the repository; or
> run a build, test or lint. Reading the repo to fill the dossier (§3) is expected and
> is the only reason to open a file at all. If you have already done any of these when
> you read this, stop, `git checkout -- .`, delete the branch, and say so on the
> `Breach:` line of your report.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. The interview step is a bounded loop — add one todo per round under it.
>
> **`needs: answers` · `may merge: false`** — this command is dispatched headless and asks **by writing**, which is why it needs answers and is still dispatchable: `needs: answers` parks a question where a person will find it, it is `needs: a decision` that the fleet refuses to run. It must never *block* on a human. **`AskUserQuestion` is not available to you and never will be**: there is no human attached to a fleet dispatch, so a call to it does not ask anybody anything — it stalls the session. Your escalation path is a **`questions` result file plus the end of your turn** (§5), and the answers come back by resumption of this same session.

```json
{
  "command": "intake",
  "tier": "core",
  "intent": "Turn a person's captured idea into a decision-ready dossier: read what the product already promised on that ground, interview the filer asynchronously across at most eight questions by emitting question results and being resumed with the answers, and emit one fixed-shape dossier a human can promote or decline from — or hand the filing back, told plainly, when it is not an idea at all.",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "loads": ["process-interview", "process-planning-ladder", "entity-model"],
  "requires": [
    "process-spine", "process-interview", "process-planning-ladder", "process-feature-flow", "process-issue-shape", "commitments", "feature-areas"
  ],
  "optional": ["entity-model", "components", "slices", "programs", "feature-maps", "planning-model"],
  "steps": [
    {"id": "payload",     "name": "Read the dispatch payload and the round",           "kind": "io",       "actor": "coordinator",                                                                      "body": "1-read-the-dispatch-payload-and-work-out-which-round-this-is"},
    {"id": "idea-only",   "name": "Idea path only — hand anything else back",          "kind": "gate",     "actor": "coordinator", "gate": "hard",                                                      "body": "2-idea-path-only"},
    {"id": "placement",   "name": "Placement first — where does this go?",             "kind": "decision", "actor": "coordinator",                                                                      "body": "2b-placement-first-where-does-this-go"},
    {"id": "ground-read", "name": "Read the ground before you ask",                    "kind": "fanout",   "actor": "subagent",    "model": "sonnet", "consumes": ["feature-map", "requirement-register"], "body": "3-read-the-ground-before-you-ask"},
    {"id": "budget",      "name": "Decide what is genuinely unknown",                  "kind": "decision", "actor": "coordinator",                                                                      "body": "4-what-is-actually-unknown-the-question-budget"},
    {"id": "ceiling",     "name": "The eight-question ceiling",                        "kind": "gate",     "actor": "coordinator", "gate": "hard",                                                      "body": "4-what-is-actually-unknown-the-question-budget"},
    {"id": "interview",   "name": "Ask: emit a questions result, end the turn",        "kind": "loop",     "actor": "coordinator", "loop": {"max_rounds": 3, "exit": "nothing material is still unknown, or the eight-question ceiling is reached"}, "body": "5-ask-emit-a-questions-result-end-the-turn-be-resumed"},
    {"id": "consume",     "name": "Consume the answers",                               "kind": "io",       "actor": "coordinator",                                                                      "body": "6-consume-the-answers"},
    {"id": "dossier",     "name": "Write the dossier",                                 "kind": "author",   "actor": "coordinator",                                                                      "body": "7-write-the-dossier"},
    {"id": "complete",    "name": "Assert every dossier field is present and honest",  "kind": "gate",     "actor": "coordinator", "gate": "hard",                                                      "body": "7-write-the-dossier"},
    {"id": "emit",        "name": "Emit the result file",                              "kind": "io",       "actor": "coordinator",                                                                      "body": "8-the-result-file-the-output-contract"},
    {"id": "no-promise",  "name": "Assert this session promised nothing",              "kind": "gate",     "actor": "coordinator", "gate": "hard",                                                      "body": "9-closing-report"},
    {"id": "report",      "name": "Closing report",                                    "kind": "author",   "actor": "coordinator",                                                                      "body": "9-closing-report"},
    {"id": "sentinel",    "name": "Write the done-sentinel",                           "kind": "io",       "actor": "coordinator",                                                                      "body": "10-the-done-sentinel-the-last-thing-you-write"}
  ]
}
```

> **Why no `produces:` edge on the dossier.** The Artifact vocabulary in
> [`spine.md`](../../process/spine.md) has no id for a dossier
> or a question round, and inventing one in a command file rather than in the spec is how
> a closed vocabulary stops being closed. The edge is left off deliberately, and
> registering a `dossier` id is named as follow-on work rather than smuggled in here.

---

**Loads:**
[`interview-protocol`](../../process/interview.md) — **the authority
on asking a human anything.** Its short form is the interview card, inlined here because
the filer reading your questions has read nothing else; everything in §5 is that card
applied to a written, asynchronous medium, and where the two disagree the protocol wins
and this command is the bug.

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
4. **No bare ids, no unexplained jargon.** `PG-NN`, `SL-NNN`, `CAP-NNNN`, `<KEY>`,
   `PRD NNNN` never appear in an option label, and anywhere else only in parentheses after
   the plain name — *the goal of getting a customer live without an engineer*. An
   internal noun gets half
   a sentence of ordinary English the first time it appears. `file:line` stays, as evidence,
   never as the only statement of the problem.
5. **The test, before you send:** would somebody who has never opened this repo pick the
   same option, for the same reason? If not, rewrite. Being asked to *"explain that again"*
   is a defect in the question, not a preference — re-ask in full, plainer, and hold that
   register for the rest of the run.

6. **A mockup, design or any visual reaches the person ONE way: the fleet's `ask` tool with the mockup attached** (`upload_link` the folder, then `attachments: {bundleId, entry}`). Their browser is on their own machine, not on the box you run on: **never** tell them to open a file path, run `python3 -m http.server` or visit `localhost` / `127.0.0.1`, and never carry a mockup question in the built-in `AskUserQuestion`, which has no attachment. The tool answers with a viewer link; put that link whole in what you say. One authority: `.fleet/process/interview.md` → *A mockup reaches a person ONE way*.

7. **The person may not be the one who knows — every question can be answered *"I can't
   answer this"*, and you must plan for that.** The question card carries that choice itself
   (*Can't answer — carry on*); you never add it as an option, and you never invent an answer
   in its place. When it comes back: **carry on with an explicit `Assumption: <what you
   assumed and why>` line, marked unconfirmed by the owner** — or, where the right party is
   the reporter, carry the question to them as an open question — **never ask it again**, and
   list every such item under an **`Unconfirmed assumptions`** heading in what you write, so
   a human can review them later. Downstream, it is an assumption to confirm, not a fact. The
   rule, once: `.fleet/process/interview.md` → *"I can't answer this"*.

8. **A card a customer will read is written in their product's words.** When the person who
   can answer is on a customer install — their own people, not our team — the card says
   `"audience": "customer"`, asks each check about their own running product with **Yes / No /
   Can't check (why)**, and names **no slash command, no program or slice id and none of Fleet's
   own nouns** ("bar", "delivery cycle", "delivery log"). A park whose action is a
   Fleet-internal step — run our command, fix our tooling, mint a token, change our
   infrastructure — belongs to the install's operator, never to the customer; when the only
   missing thing is the customer's observation in their app, ask for that observation instead.
   `validate_questions.py` and `validate_decision.py` refuse a customer-addressed card that
   breaks this rule, and Fleet refuses it again at its ask boundary.

<!-- include: process/writing.md -->
### Writing for people — five rules for every session

- **Write everything that lasts in English.** Whatever language a person writes to you in,
  your live conversation with them may follow it: your questions and your replies. Everything
  that is kept is written in English: the knowledge base, plans and decisions, commit messages,
  pull request titles and descriptions, code comments, and the issues you write. When you record
  what a person said in another language, translate it into English. Keep their exact words as
  a quote only where the wording itself matters.
- **Use plain English.** Write in the style of ASD-STE100 Simplified Technical English. Many
  readers are not native English speakers. Write so that a busy reader with B1–B2 English
  understands every sentence on the first read. This holds for everything a person reads:
  questions, replies, issues, pull requests, plans, summaries and docs. Simpler words do not mean
  vaguer content. Keep every fact, number and name that matters. The points below are Fleet's
  own use of that style.
  - *Sentences.* One idea per sentence. Keep most sentences under 15 words. If "and", "which"
    or a colon joins two ideas, split the sentence. Use active voice: "She sets a limit", not "A
    limit is set". Use the simple tenses: present, past and future. Avoid forms like "would have
    been". Use a verb, not an "-ing" form used as a noun: "Check the input", not "Do the input
    checking". If you need a hard tense, keep that sentence short.
  - *Instructions and descriptions.* An instruction is a step that a person or an agent must do.
    Write it in the imperative, with one action per sentence, at most 20 words. Put the
    condition first: "If the check fails, run the fix command." A description says what
    something is or does. Write it in at most 25 words, with one topic per paragraph. A promise
    stays at 20 words (the last rule).
  - *Words.* Use everyday words: "use", not "utilize"; "help", not "facilitate"; "start", not
    "initiate". Never write leverage, robust, seamless, delve, utilize, facilitate, streamline,
    empower, holistic, synergy or cutting-edge. Prefer a verb to a noun made from a verb: "she
    checks", not "she performs a check". Name the concrete thing: "error message", not "the
    refusal"; "script", not "the loop". Use a technical term only if the reader needs it, and
    explain it in a few plain words the first time. Use the same word for the same thing every
    time. Do not switch between "limit", "cap" and "allowance".
  - *Clarity.* Every "it", "this" and "they" must point to one thing. If in doubt, repeat the
    noun. Put the main point first, then the details. Give a concrete example instead of an
    abstract description. Cut filler: "in order to", "it is important to note that",
    "basically", "actually".
  - *Structure.* Keep paragraphs to 2–4 sentences. Use bullet lists for steps or options, not
    for an explanation that flows.
  - *One word, one meaning.* Use one approved word for one thing, in every document. Do not
    use the words on its right for that thing. Words in code, in quotes and in a customer's own
    wording stay as they are.
    - **issue** — not: ticket
    - **person** — not: user, human
    - **machine** — not: host, node
    - **pull request** — not: PR
    - **repository** — not: repo
    - **agent** — not: bot
    - **customer** — not: client
    - **sign in** — not: log in, login
    - **limit** — not: cap, allowance
    - **mockup** — not: wireframe, prototype
    - **knowledge base** — not: wiki
  - *Examples.*
    "We leverage the cache in order to facilitate faster lookups." → "The cache makes lookups
    faster."
    "A limit is enforced on a per-key basis." → "Each key has its own limit."
    "The update was performed after validation of the input, which can fail." → "The worker
    checks the input first. If the check fails, nothing is updated."
    "It was rejected." → "The check rejected the pull request."
  - *Final check.* Before you send, reread each sentence. Is it within its length limit? Does it hold
    one idea? Would a non-native reader know every word? Does it use the approved words? If not, rewrite it.
- **Never write a real customer's name.** Not the company, and not its hosts, organisations,
  repositories, people or install names. This holds for code, comments, tests,
  commit messages, pull request text and release notes. When you record where a problem was
  seen, write "a customer install". When an example or a test needs a name, use a made-up one
  such as `acme` or `example.com`.
- **Write for a reader who does not know the code.** Pull request descriptions, issue titles,
  questions, feature descriptions and requirement text are read by people who never opened this
  repository. Keep our internal names out of the sentence: no PRD or issue id (a `PRD` number,
  an issue key), no process word ("slice", "lane", "dispatch"), no file path, check name or run
  id (`tests/e2e/specs/…`, `CI / e2e - browser suite`, `run 0253bb04`). Say what the thing is in
  the product's words, and name the effect on a person, not the mechanism. An id or path a
  reader needs — to link an issue, to point at evidence — goes on its own references line or in
  a references section at the end, never in the sentence a person reads first; a linking key a
  tool requires stays as a label at the start. Before you send: would somebody who has never
  opened this repository understand it? If not, rewrite it.
- **Write a promise in one plain sentence.** A capability, a requirement rule and a journey's
  acceptance criterion are read by people who did not write the code and checked by a QA agent
  from outside it. Write each as one sentence of at most 20 words, in the product's words:
  pages, buttons, issues, keys, workers. Code names, routes, status codes, environment variables,
  setting keys and file paths go in the Evidence column, never in the sentence. Keep who, what,
  when and every exception. Write a limit someone may tune as "a time limit"; keep the number
  only when the number is the promise. Say who acts: an operator, a person, an agent, a worker.
  The same words hold for what a customer reads about a feature: its brief, each use's name and
  paragraph, and a plan's slices and pieces of work. A person's own words are reworded to this
  standard before they are proposed, never written as they came.
  The full standard, with examples, is *Wording a promise* in `process/knowledge-bootstrap-formats.md`.
<!-- /include -->

**Headless — no human attached:** you write all of the above into the escalation instead,
in the same words, so whoever reads it later can answer it as filed.

Full protocol — discovery before forks, acting on the answer, where the decision is
written: `.fleet/process/interview.md`.
<!-- /include -->
The shared planning ladder, for the provisional tier call in §7 — the same text in every
repository, inlined here so the call is made by its tests and not by how big the request sounds.
Read the rung; do not reconstruct it from memory. Where each entity lives in this repository is
`slot:entity-model`.

<!-- include: process/planning-ladder.md -->
### The planning ladder — which kind of thing is this?

**This ladder is the same in every repository.** It says what each kind of work is and in which
order to test for it. Where each kind *lives* in this repository — the file, the register, the
tracker project — and the local examples are the repository's own answer, `slot:entity-model`.
When the two seem to disagree about what a thing *is*, this ladder wins; when they disagree about
*where* it goes, the slot wins.

**Why it exists.** A router that judged size by feel turned a bug ("a session ignores new
messages while it waits on a long pull-request watch"), a one-page screen change and a request
for documentation into three new programs in one day. Each of them failed a test below that
nobody ran. Run the tests; do not judge by how big the request sounds.

#### First, two questions about the situation

These are about the request, not about an entity. Ask them before anything else.

| Ask | If yes |
|---|---|
| **Is something broken?** Something that used to work, or that the product already says it does, does not. A wrong or missing documentation page for something that ships counts. | **bug** — however large the fix turns out to be |
| **Is it early or exploratory** — "for later", not ready to build, nobody can yet say what done looks like? | **idea** — parked, not sized |

A bug stays a bug when the fix is big. A big fix is a reason for the bug to name a slice or a PRD
later; it is never a reason to make the bug a program.

#### Then the ladder — top down, the first match wins

The order is what removes the doubt: things that never finish are caught before anything is sized
as work, and the small work rungs are tested before the large ones.

| # | Ask | If yes |
|---|---|---|
| **1** | Can you point at the code it owns — a directory, a service, a set of tables? | **component** (built, never finished) |
| **2** | Is it a lasting property of the product? *One sentence a person can check* → | **capability** |
| | *…it emerges from several components and owns no code* → | **outcome** |
| **3** | Would a customer name it when describing what the product does, and does it group several capabilities? | **feature area** |
| **4** | Is it only a way to *filter* things that each already stand alone (security, onboarding, a release)? | **theme** — a label, never a container |
| **5** | Is it small, scoped work that needs no design decision and gives nobody a new thing to see or use? | **task** |
| **6** | Can one agent build it end to end in one working session, with acceptance criteria and a change a person can see or use? | **PRD** |
| **7** | Is it one deliverable — one feature, one capability and what it needs, or one set of gaps — with a "Done when" that none of its PRDs proves alone? | **slice** |
| **8** | Do **all** the program tests below pass? **Never in a repository that plans by area** — see below. | **program** |

**If nothing matches, you have not finished thinking.** (In a repository that plans by area, rung 8
never matches: work bigger than one slice is several slices.) The two usual landings: something that
never finishes but owns no code is an **outcome** (rung 2); something that finishes but holds one
deliverable is a **slice** (rung 7), not a program.

Components, capabilities, outcomes, feature areas and themes are **durable**: they never finish
and carry no status. Tasks, PRDs, slices and programs are work that finishes.

**A use is not a rung — and it is how a customer-facing feature is cut.** The customer page is *Features, uses and capabilities* (`knowledge-base/feature-areas`). A request is a **capability** when a use already covers its ground, a **use** when it is a main thing people do that no use says and it is not already one of them, a **feature** only when it passes the sub-feature test below; a row that fits none waits under `### Misfits (to move)` (*Writing a feature brief*, moment 2). A feature area's capabilities are grouped under its three to six **uses** —
the main things a person does with it (*Sign in with SAML* under sign-in) — so a request a customer
calls a "sub-feature" lands at rung 3 as an existing area plus a use, never as an area of its own.
It becomes its own feature area only when it needs its own brief or owner (*Writing a feature
brief*, feature-doc reconcile process document).

#### The size tests, smallest first

Each rung is the smallest one whose test the work passes. Test them in this order and stop at the
first pass.

- **Task** — scoped work that needs no design: a dependency bump, a configuration change, a
  refactor with no visible change, a wording fix. If two people
  could disagree about how it should look or behave, it needs a design, and it is not a task.
- **PRD** — one agent, one working session, one surface a person touches (a page, a control, an
  API behaviour, a command). It carries acceptance criteria that can each be shown to pass. One
  new screen is a PRD, however important it is.
- **Slice** — one deliverable that finishes, with a "Done when" a person can observe on the
  running product, which none of its PRDs carries alone. A slice usually holds two or more PRDs;
  a one-PRD slice is allowed but worth a second look, because it is often a PRD that has not yet
  found what ships beside it.
- **Program** — only when the work holds **at least two slices** under one result that neither
  slice delivers alone. **One deliverable is a slice, not a program**, however large it is.
  **In a repository that plans by area there is no program rung at all** (next section).

#### In a repository that plans by area, "program" is not a rung

Run `python3 knowledge/scripts/planning_mode.py`. It prints `programs` or `areas` (the setting is
`[fleet.planning] mode` in `.fleet/fleet.toml`; no setting means `programs`).

**When it prints `areas`, the ladder stops at rung 7. No new program is ever proposed or created**. Programs that already exist keep running until their slices finish; nothing new joins
them.

Work that is bigger than one slice does not become a program. It becomes **several slices**:

- **Each deliverable is its own slice**, with its own "Done when", under the **feature area** that
  owns it. Two deliverables in one area are two slices in that area; deliverables that belong to
  different areas are slices in different areas.
- **The order between them is written as dependencies, not as a container.** A slice that cannot
  start before another finishes says so in its `Depends on`; a PRD that builds on another PRD says
  so in its own `depends_on`. That is all the grouping the work needs.
- **The program tests still help you think** — a literal title, a person who notices, a day it
  becomes true — but what they describe is the *set* of slices. Nothing is created for the set itself.
- **When you route such a request, propose the first slice** (the one the others depend on), and
  describe the other slices in plain words in `alsoWeighed`, so the person who accepts sees the whole
  shape of the work. Each further slice is its own proposal, when its turn comes.

**Worked example (areas mode).** *"A new customer account is set up and served without an engineer
in the loop."* In a repository that plans by program this is the program in the worked examples
below. In a repository that plans by area it becomes two slices:

1. *Accounts are provisioned from the sign-up form, with no engineer* — a slice in the
   `accounts` area. Done when a sign-up creates a working account on the running product.
2. *A first run that needs no help* — a slice in the `onboarding` area, with `Depends on:` the
   first slice. Done when a new account finishes the first run without a support ticket.

Route proposes slice 1 and names slice 2 in `alsoWeighed`; when slice 1 is accepted, slice 2 is
proposed in its turn. No program row is written, so there is nothing to migrate later.

#### When no feature area fits: a new area, with its first slice

In a repository that plans by area every slice names a **feature area** (`planning_mode.py --areas` lists them).
When the request fits none of them, route proposes the slice **together with a new feature area**, and the one
accept creates both: the area's feature map and the slice, in one pull request, with the person who accepted as the
area's first owner. In a repository that plans by program
this does not happen: new work goes under an open program.

**The bar is high, because every new area is one more place every filing must choose between.** Propose a new area
only when all of these hold:

1. **No existing area fits — and you can say why for each close one.** Name the closest existing areas and, for
   each, why the work does not belong there, as evidence from the request. If you cannot write the reason for an
   area, the slice goes under that area. This is the same check as *Say why it is not each smaller rung*, applied
   to areas.
2. **A customer would name it** when describing what the product does (rung 3's test), and it groups capabilities.
3. **It will keep receiving work.** You can name at least two more capabilities it will hold after this first slice.
   A one-off — a single feature, a migration, one customer's list of gaps, a cleanup — is never a new area: put it
   under the closest existing area and say plainly that the fit is weak.

The new area's sentence says what a person can do there, for as long as the area exists; it is never the first
slice's "Done when". The proposal also carries the new map's **feature brief** and its **uses** — the
things a person will do in the area, written to *Writing a feature brief* in the feature-doc reconcile process document.
An area you cannot cut into three uses fails test 3.

**Worked examples (areas mode).**

| Request | Existing areas | Lands on | Why |
|---|---|---|---|
| *"Customers get an invoice each month for what they used."* | accounts, sessions, board | **slice, in a new area `billing`** | Charging for use is a job a customer names on its own ("billing"). Not *accounts*: that is who may sign in. Not *sessions*: that runs the work, it does not charge for it. Billing will keep receiving work: payment methods, refunds, spending limits. |
| *"Show the session's cost next to its duration."* | accounts, sessions, board | **slice (or PRD) in `sessions`** | One more fact on a page that already exists. Even if cost later belongs to billing, this one change does not make a new area. |
| *"Migrate the old export files to the new format."* | accounts, sessions, board | **task, under the area that owns the export** | A one-off. Nothing will keep arriving in a "migration" area. |

#### The program tests — every one must pass

1. **The title is literal.** Someone who reads only the title can say what will be delivered. A
   title that reads well and says nothing fails ("Make it great", "Interrupt PR polling").
2. **A person or a surface.** Either name a person, in a situation, who is stuck today — *when
   `<situation>`, I want to `<motivation>`, so I can `<outcome>`* — or name the thing that lands and
   the customer surface it shows up on. "Runtime work" names neither.
3. **A day it becomes true, and somebody notices.** "A new customer account is set up and
   served without an engineer in the loop" has such a day. "Scalability" does not: a program that
   cannot be shown false on a day is a **theme**.
4. **At least two slices.** Describe the two (or more) deliverables in plain words, each one
   finishing on its own. If you can describe only one, it is a slice.
5. **No existing open home fits.** Create a **new** program only when no existing open home can
   take the work **and** the work holds at least two slices. Joining a home that already exists is
   always the first thing to check.

#### Homes: prefer an existing open one

A **home** is the existing container new work goes into. Before you propose anything new, look for
an existing open home that the work genuinely serves.

- **A home is open when it still takes new work.** One that is withdrawn, or complete, is closed.
- **A closed home is never stretched to fit.** New work for a finished slice is new work: it needs
  an open home of its own. Name the closed home you passed over, and why, so the reader sees it.
- **Never invent a container to give a small piece of work somewhere to go.** A one-deliverable
  request with no good home is still one deliverable; say plainly that the fit is weak and let the
  person who accepts decide.

#### Say why it is not each smaller rung

Whatever rung you land on, write one line for **each smaller work rung** saying why it is not that
rung: a program says why it is not a bug, a task, a PRD or a slice; a slice why it is not a bug, a
task or a PRD; a PRD why it is not a bug or a task; a task why it is not a bug. The line is
evidence from the request, not a restatement of the rung's name. **If you cannot write the line
for a smaller rung, the work is that smaller rung.** This is the check that makes a wrong size
visible to the person who accepts it.

#### Worked examples

| Request | Lands on | Why |
|---|---|---|
| *"A session ignores new messages while it waits on a long PR watch."* | **bug** | Something is broken. A big fix does not change that. |
| *"Maybe one day we support single sign-on with more providers."* | **idea** | Nobody can say yet what done looks like. |
| *"The setup guide is missing the step that creates the API key."* | **bug** | The page is wrong for something that already ships: a docs defect, corrected where the docs live. |
| *"Bump the HTTP client library to the current version."* | **task** (5) | No design, nothing new for anyone to see. |
| *"Add a page listing filings that are still waiting for an answer."* | **PRD** (6) | One screen, one session, testable acceptance criteria. Important is not the same as large. |
| *"Add CSV export to the audit log."* | **PRD** (6) | One agent-session, one surface. |
| *"A reviewer can read the audit record and act on it."* | **slice** (7) | One capability with a "Done when" none of its PRDs proves alone. |
| *"Everything still missing for the acme pilot."* | **slice** (7) | One set of gaps for one customer; the members share nothing else. |
| *"A new customer account is set up and served without an engineer in the loop."* | **program** (8) | A named person notices on a day, and it holds at least two separate deliverables (provisioning, and a first-run that needs no help). **In a repository that plans by area: two slices**, in their own areas, the second depending on the first (see above). |
| *"Rate limiting."* | **component** (1) | You can name the directory. A mechanism is never a planning level. |
| *"Scalability."* | **outcome** (2) | No code owns it and it never finishes; it earns slices while it is being built. |
| *"Security."* | **theme** (4) | A filter across work that already stands alone. Never a new program. |

#### Smell tests

- **A program with one deliverable** is a slice wearing a program's name.
- **A program created from a single request on the day it was filed** almost always failed test 4
  or test 5. Look again.
- **A program whose title describes a defect** ("X ignores Y") is a bug.
- **A slice you cannot write "Done when" for** is not a small slice; it is a label (a theme).
- **A "task" that needs a mockup or an argument about behaviour** is a PRD.
<!-- /include -->

**Do not load** implementation contracts, design specs or architecture detail docs. You
are not designing anything, and reading them is how an intake turns into an unrequested
design session.

---

## The cycle

### 1. Read the dispatch payload, and work out which round this is

**Everything you were given is already in front of you.** Fleet inlines the captured text
and every prior question-and-answer into this session's system prompt — the same channel
`fleet-service`'s the fleet service already uses to inline an issue description
(`briefing.render()` returns a block that is passed as `extra_system`, not as a command
argument, because captured prose carries newlines and backticks and an argument list does
not). **Read what you were given. Do not go looking for more of it** — the issue whose key
you were invoked with is fleet's to write and not yours to mine, and a fetch that finds
nothing is indistinguishable from a fetch that was never authorised.

Then establish which round you are in, because they are different jobs:

- **The payload carries no prior questions** → round one. Run §2 onward.
- **It carries prior questions AND their answers** → the filer replied. Go to §6, consume
  them, and continue where you left off.
- **It carries prior questions with no answers** → you were re-dispatched before the filer
  got to it. **Do nothing at all and end the turn.** Re-asking is how a filer receives the
  same round twice and learns to ignore both.
- **The prompt says *"The person did not answer these questions. They said:"*** → the filer
  sent the round back with an instruction instead of answering it. Go to §6's send-back note:
  re-read the ground at the repository's current head, act on the instruction, and re-ask only
  what still needs them.

> **Warm resume is the mechanism; cold restart is the case you must survive.** When fleet
> resumes *this* session, your own reasoning is still in context and reading the answers
> is enough — that is the design, and it is what makes a real multi-turn interview
> possible. But a transcript can be pruned and a box can be rebuilt, and then a fresh
> session lands here with nothing but the payload's questions and answers. **So write
> every question to be interpretable from its own answer**, without your reasoning
> attached: say in the `prompt` what the question is establishing, so a cold successor
> reading *"B"* can tell what B settled. That is cheap, and it is the whole of the
> belt-and-braces — the issue has a description, but you never write to it, so a successor
> that goes looking there finds the filing and none of your reasoning.

### 2. Idea path only

Version one shapes an **idea** — an exploratory want, filed by a person, that the product
has not committed to. Nothing else. Judge it on what the captured text *is*:

| What the payload carries | What you do |
|---|---|
| an exploratory want — *"it would be good if…"*, *"I keep having to…"*, *"why can't I…"* | shape it — §3 onward |
| **something broken** — an observed defect, a reproduction, a regression | **hand back** as `bug` |
| **a scoped work order** — a specific change somebody already decided on | **hand back** as `task` |
| **a docs defect** — a page missing or wrong for a capability that ships, or a page promising what the product does not do | **hand back** as `bug` — the page is corrected where `slot:docs` says; a page's promise is **never** a request to build the feature |
| **no want at all** — a question, a link, a status note | **hand back** as `question`. is that front door, not this one |

**Handing back means emitting a `handback` result (§8) and ending the run**, with one or
two plain sentences saying what this actually is and what you saw that says so. Do not
stretch a defect into an idea to bring it into your lane, and do not stretch an idea into
a work order to get it moving — reclassifying is a scope decision, and scope decisions
are not yours (the repository's always-on rules).

> **A hand-back tells the filer something; it decides nothing.** The `looksLike` value is
> what the filing *appears* to be, offered so a person who took the trouble to file is
> answered rather than met with silence — the one outcome that teaches somebody not to
> file again. It is **not a triage verdict**: it moves nothing, files nothing, routes
> nothing, and it does not judge whether the work is in scope. Say what you saw; leave the
> verdict to the party that owns it. What the handback does owe is the fork: **the park
> must name the decision being asked** — re-kind this capture as `Type:bug`/`Type:task`,
> or discard it — and fleet renders that park comment from your result document's `why`
> and `looksLike`, so a `why` that merely restates the finding parks a person
> on a question they have to re-derive before they can answer it.

### 2b. Placement first — where does this go?

**In a repository that plans by area** (the brief carries a `## Features` block), **round one is
always the placement question**: the best-matching feature and use, a new thing that feature
does, up to two alternatives, a new feature, and "not a feature". It is asked before anything else, it does not count toward the
eight-question ceiling or the round limit, and its answer is copied into the dossier as
`placement`, which route is bound by. The shape, the matching, which option is preselected and
what each answer leads to are in the shared feature-flow guidance, inlined here:

<!-- include: process/feature-flow.md -->
# The feature flows — new feature, new use, plan, the brief, removing a use, and where a feature request goes

> The one guidance doc for the six front doors a repository that **plans by area** offers
> (`planning_mode.py` prints `areas`). `intake`, `route` and `slice:create` each read the part
> that names them; none restates it. The shapes are enforced by the fleet as the result lands
> (`dispatch.results`), so a document that breaks one is refused and never reaches a person.
> In a repository that plans by program none of this applies: there is no feature to place in.

**The person reads every card these flows produce, and they are a customer.** Every question,
option, brief and plan names the **feature and the use in words** — never an id (no program,
slice, issue, capability or PRD number; the fleet refuses a card that carries one), never a
command, never Fleet's internal steps. Address it to them: a question these flows ask goes to
the person who filed, never to "the fleet's operators". A **feature** is a feature map; a
**use** is one `###` section of its `## Capabilities` — a thing a person can do with it.

**No flow here creates or names a program.** A plan is one to three slices under the feature;
work bigger than that is more slices, ordered by `Depends on`.

## The requests

The filing's brief says which one it is: a pre-placed filing carries a `## Request` block, and
every intake or route dispatch in this mode carries a `## Features` block — each feature as
`### <slug> · <name> — <summary>`, then each use as `- <name> — <paragraph>`. **Match and
offer only what `## Features` lists**: it is what the feature pages show, and an option naming
a feature or use it does not list is refused.

| request | how it arrives | who runs | what route proposes |
|---|---|---|---|
| **feature request** (no `## Request`) | the person typed what the product should let them do | `intake`, then `route` | per the confirmed `placement` (below) |
| **new feature** (`{"kind": "newFeature"}`) | a name (the filing's title) and two or three sentences, from the Features page | `route` directly — no interview | `kind: area`: the feature's map only |
| **new use** (`{"kind": "newUse", "area"}`) | "+ Add something this feature should do" on a feature's page: a name (the filing's title) and one sentence | `route` directly — no interview | `kind: use` carrying `newUse`: one new use on that feature's map |
| **plan** (`{"kind": "plan", "area", "use"}`, `use` null = the whole feature) | "Plan this" on a use, or "Plan the whole feature"; and Fleet itself, once, when an accepted new use lands | `route` directly — no interview | `kind: slice` carrying `plan` |
| **remove a use** (`{"kind": "removeUse", "area", "use"}`) | "Remove this use…" on a use already on a feature's page; the text is the person's reason | `slice:create` directly — Fleet accepts the removal for the person, who already confirmed it with the reason | nothing: there is no proposal to check |
| **write the brief** (`{"kind": "writeBrief", "area"}`) | "Write the brief" on a feature whose map has no brief or no uses; the text, when there is any, is the person's note (it may name one more thing the feature should do) | `route` directly — no interview | `kind: brief` carrying `featureBrief`: the brief, and the map's rows sorted into uses |

A new feature, a new use, a plan and a brief are **pre-placed**: the person already said where the work goes, so
there is no interview and no placement question. Route may ask **at most two** questions across
the run (instead of its usual one), each one the person could not have answered by pressing the
button they pressed — never "is this really a new feature?".

## Feature request: the placement question comes first

**`intake`'s round one is always the placement question**, before any other question, and it
does not count toward the eight-question ceiling or the round limit — it is Fleet's question,
not a gap the filer left. One question in the set, `"kind": "placement"`:

```json
{"id": "placement", "kind": "placement", "prompt": "Where does this go?", "allowFreeText": true,
 "options": [
   {"id": "p1", "label": "Extends <Feature> → <Use>", "then": "Fleet shapes your request inside <Use>.", "recommended": true,
    "placement": {"choice": "extends", "area": "<slug>", "areaName": "<Feature>", "use": "<Use>",
                  "useParagraph": "<the use's paragraph>", "fit": "strong", "why": "Why here: <evidence from their words>."}},
   {"id": "use", "label": "A new thing <Feature> does: <drafted name>", "then": "Fleet adds it to <Feature>, ready to plan.", "recommended": false,
    "placement": {"choice": "newUse", "area": "<slug>", "areaName": "<Feature>",
                  "newUse": {"name": "<drafted use name>", "paragraph": "<one or two plain sentences>"}, "why": "<why this feature>"}},
   {"id": "new", "label": "A new feature: <drafted name>", "then": "Fleet drafts the new feature for you to check.", "recommended": false,
    "placement": {"choice": "new", "newFeature": {"name": "<name>", "summary": "<one sentence>", "uses": ["<use>", "..."]},
                  "whyNot": [{"area": "<slug>", "areaName": "<Feature>", "why": "<why it does not fit>"}]}},
   {"id": "not", "label": "Not a feature: it's broken", "then": "It goes to the bug sheet with your words.", "recommended": false,
    "placement": {"choice": "bug", "why": "<what you read that says so>"}}
 ]}
```

- **Options, in this order:** the best-matching feature → use; **at most one** "A new thing
  <Feature> does" (`newUse`) — when the best feature plainly fits but none of its uses does,
  drafted as a use name and one or two plain sentences; **up to two** alternative feature → use
  pairs (with the new thing, at most three options name an existing feature); **at most one**
  "A new feature"; **exactly one** "Not a feature" — a `bug` ("it's broken") or a `task`
  ("it's a small change"), whichever the words read as. Two to five options; this is the only
  question allowed a fifth. When the card is full, the new thing takes "A new feature"'s place
  only when that feature clearly fits; otherwise it takes an alternative's.
- **Matching:** read the top candidates' summaries and each use's paragraph; a feature's
  `brief.not` lines name its siblings on purpose and break ties. `fit: strong` when the
  request plainly does what the use's paragraph says; else `weak`.
- **Which one is `recommended`:** the best match when its fit is strong; the new thing when the
  feature fits strongly and no use does. When none is strong,
  "A new feature" — but only after the new-feature gate below: if you cannot write a `whyNot`
  for a close feature, the request goes under that feature and that option is recommended.
  When the words describe a defect or a small change to something that exists, "Not a feature".
- **The `brief`** says in two plain sentences what you read the request to be and that nothing
  is created yet. **A repository with no feature map** asks no placement question at all.

**On resume**, copy the answer into the dossier as `placement`:
`{"choice", "area"?, "areaName"?, "use"?, "newUse"?, "newFeature"?, "confirmedBy"}` — the option they
picked; free text ("somewhere else") is re-matched against `## Features` and asked once more
only if it still fits nothing. Then:

- **`extends`** — shape the rest of the interview inside that feature and use; ask nothing the
  use's paragraph already answers.
- **`newUse`** — ask nothing more and write the dossier; route turns it into the new-use
  proposal below, its name and paragraph the option's draft.
- **`new`** — ask at most one more question about the new feature itself, then write the
  dossier; route turns it into flow 1's map-only proposal and the request becomes one of its uses.
- **`bug` / `task`** — emit the `handback` with that `looksLike`, quoting their own words.

## What route proposes, by request

**Route is bound by the confirmed `placement` and by the `## Request`.** A proposal that
contradicts either is refused as it lands (`proposal-placement-mismatch`) and route is sent
back once with the reason.

- **placement `extends`** — `under` names `area:<slug>` (`existing`); add the optional
  `"use": "<Use>"`. Size it as usual (slice, PRD, task), never a new feature.
- **placement `newUse`, or a new-use request** — **`kind: "use"`** carrying **`newUse`**:
  `{"area", "areaName", "name", "paragraph"}`, `under` naming `area:<slug>` (`existing`) then
  the use as `{"id": "new use", "name": "<name>", "meta": "use", "status": "new"}`, and nothing
  else — no slice, no piece of work. Draft it by *Writing a feature brief* → moment 5 (*Taking
  in what a person adds*, `feature-doc-reconcile.md`): a thing a person does, named in a few
  words with a verb first ("Reserve parts for a repair"), and one or two plain sentences saying
  what they do with it and why — the person's own words where they are plain, from a placement
  the option's draft. Never ship-state words ("shipped", "planned", "partly built", "still open"
  — the map's check refuses them, so write "a booked repair", not "a planned repair").
  **Flag a near-duplicate, not only an exact name**: when an existing use's name or paragraph
  already says this in other words, a new-use request spends its question on it ("This reads
  like *Book a repair*, which the feature already does — add it there, or add it as a new
  thing?"), and the placement card offers that use as `extends` instead of a new thing. The
  fleet refuses only an exact name (case folded); the near-duplicate is yours to catch.
  **Every option of that question carries its `placement`** — `{"choice": "extends", "area",
  "use"}` on "add it there", `{"choice": "newUse", "area", "newUse": {"name"}}` on "a new
  thing" — because **the person's answer outranks the request**: the fleet reads the picked
  option's `placement` off the held, answered question and judges the proposal by it. Answered
  `extends`, propose as for **placement `extends`** above (inside that use, never a new use —
  a new use is refused as it lands); answered `newUse`, the new use.
  `onAccept.command` is `slice:create`, which adds the use to the map. However many uses
  the feature already has, a new one is added the same way.
- **placement `new`, or a new-feature request** — **`kind: "area"`** carrying `newArea`
  (`slug`, `name`, `sentence`, `whyNoExistingArea`, `brief`, `uses` — the same shape and the
  same fourth gate a `newArea` on a slice carries), `under` holding exactly the new
  `area:<slug>` node, and **no slice**. Draft the brief to the feature-brief schema
  (`summary`, `problem`, `example`, `example_from`, `not`) and **uses**, each a
  thing a person does, with one plain paragraph — every word by *Writing a feature brief* →
  moment 5. `onAccept.command` is `slice:create`, which writes the map. Derive the slug and name from the person's name for it.
  **Numbered requirements are the person's own and none may vanish.** When the filing's text
  holds lines numbered `R1`, `R2` and so on, every such number goes on the use that delivers it,
  as `covers` (`{"name", "paragraph", "covers": ["R2", "R5"]}`). A requirement you cannot place
  on any use stays out of every `covers`: the Handbook shows it to the person, who adds it or
  leaves it out. Never drop one silently, and never list a number on a use that does not deliver it.
- **a plan request** — `kind: "slice"` carrying **`plan`**:
  `{"area", "areaName", "use" (null for the whole feature), "slices": [{"name", "delivers",
  "doneWhen", "prds": [{"title", "sentence"}]}]}`, one to three slices in build order, each
  with one to six pieces of work. `under` names `area:<slug>` (`existing`) then the slices as
  `new`. **This is the one proposal that names its new entities and writes a `Done when`**:
  the person asked for a plan, and a plan is exactly those words. Each slice is still a cut
  that completes — `delivers` is what a person can do once it is done, `doneWhen` one
  observable sentence — and holds the work the ladder puts in a slice (two or more pieces,
  unless the use is genuinely one piece of work). A plan for the whole feature covers every
  use that has open ground, in the order a person would want them. Its words — `delivers`,
  `doneWhen`, each piece's title and sentence — follow *Writing a feature brief* → moment 5, and
  a piece an existing capability row already covers is named, never planned twice.

- **a write-the-brief request** — **`kind: "brief"`** carrying **`featureBrief`**:
  `{"area", "areaName", "brief": {"summary", "problem", "example", "example_from", "not"},
  "uses": [{"name", "paragraph", "rows": ["<row id>", ...]}]}`, `under` naming `area:<slug>`
  (`existing`) then `{"id": "brief", "name": "The brief and its uses", "meta": "brief", "status":
  "new"}`, and nothing else. Read the feature's map: its Intent, its existing brief and use
  paragraphs where it has them, and every capability row. Draft the brief to the feature-brief
  schema and **sort every live row** (each row outside `### Misfits (to move)` and `### Retired`)
  **into uses** — fewer for a small map: one or two when it has fewer than three rows,
  none needed when it has none — each a thing a person does, with one plain paragraph, every word by
  *Writing a feature brief* → moment 5. **Rows are only regrouped**: name each by its id, every live
  row in exactly one use; never reword, renumber, add or drop one — the fleet refuses a sort that
  misses, repeats or invents a row. A use that fits an existing `###` keeps its name. When the
  person's note names something the feature should also do that no row covers, add it as one more
  use with `"rows": []`. `onAccept.command` is `slice:create`, which writes the brief into the map.

**The person may edit before accepting** — the new feature's name, sentence, brief and uses,
the new use's name and paragraph, the brief and the uses of a feature's brief (including which
use a row sits in), or the plan's slices — and the accepted proposal carries their words. Write from the proposal
the brief carries, never from your memory of the draft.

## What `slice:create` writes from an accepted proposal

- **`kind: "area"`** — **only the feature map**: run `new_feature_area.py` with `--brief-json`
  and one `--use` per use, exactly as for a `newArea` on a slice, and write **no slice row**. A
  feature with no code yet passes no component and no code path (slice:create's writer notes).
  Land it by one merged PR and report `created`:
  `{"kind": "area", "id": "<slug>", "name": "<name>", "href": "areas:<slug>", "pr": "<url>"}`.
- **`kind: "use"`** — **only the new use**: run
  `python3 knowledge/scripts/new_feature_use.py --area "<newUse.area>" --name "<newUse.name>"
  --paragraph "<newUse.paragraph>"`, which adds it to the map as a `###` section with an empty
  table, and write **no slice row and no capability row** — its work arrives with the plan made
  for it from the feature's page. Land it by one merged PR and report `created`:
  `{"kind": "use", "id": "<area>", "name": "<newUse.name>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "brief"`** — **only the brief and the uses**: run
  `python3 knowledge/scripts/write_feature_brief.py --area "<featureBrief.area>" --brief-json
  '<featureBrief.brief as JSON>' --uses-json '<featureBrief.uses as JSON>'`, which writes the brief
  into the map's frontmatter and moves each row, byte for byte, into the use that names it (notes
  that sat between the old tables move to a `## Notes` section). Write **no slice row and no new
  capability row**. Land it by one merged PR and report `created`:
  `{"kind": "brief", "id": "<area>", "name": "<areaName>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "removal"`** (a remove-a-use request; Fleet wrote the proposal, `removeUse`: `{"area", "areaName",
  "use", "why"}`) — **only the removal**: run `python3 knowledge/scripts/remove_feature_use.py --area
  "<removeUse.area>" --name "<removeUse.use>" --reason "<removeUse.why>"`. It takes the use's `###` section off the
  map and moves every table it held, byte for byte, to `### Retired` (built work stays on the page, retired; nothing
  is deleted), and cancels each plan under the use that is not built yet the way `prd:cancel` Step 2 does, with the
  person's reason. Write nothing else: no row, no slice, no reworded line. Its last stdout line says what it retired,
  cancelled and kept; put that in the PR description in words. **When it exits 3**, work under the use is being built
  right now: ask the person **one** question — stop that work and remove the use, or keep the use (withdraw the
  removal) — and on "stop it" run it again with `--stop-work-being-built`. **When it exits 2**, end the run with its
  sentence as the summary, a question to the person; their note, or withdrawing the request, is the answer. Land it by
  one merged PR and report `created`:
  `{"kind": "removal", "id": "<area>", "name": "<removeUse.use>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "slice"` with `plan`** — one slice row per `plan.slices` entry, in order, each in
  `plan.area`, `Depends on` chaining them in build order, `Done when` the entry's `doneWhen`
  verbatim; and under each, one **PRD stub** per `prds` entry, written the way `prd:create`
  writes a stub from an accepted proposal (`status: stub`, the entry's title and sentence as
  the brief, the slice and area named, nothing else) — and it **records the use in the stub's
  frontmatter as `use:`** (the use `plan.use` names; for a whole-feature plan, the use that
  slice serves). **And one capability row per piece of work** in the area's map, under that use's
  `###` section: a fresh `CAP` id from the allocator, the capability cell
  `**<title>** — <sentence>`, reworded only to meet the standard, `Ships in` the piece's PRD stub number, `Tested by` `—`. That row is what
  makes the use read as planned work, with its slices under it, the moment the PR merges — and
  stops the page offering "Plan this" again. One merged PR for all of it; report `created` for the first slice with the rest under `"also":
  [{"id", "name", "href"}]`. The pieces of work then go through the usual fill, design and
  build.
<!-- /include -->

Read §3's ground **for the candidates** before you ask it — the feature maps of the two or three
closest features — and, once it is answered, shape the rest of the interview inside the feature
and use it confirmed. No `## Features` block (a repository that plans by program, or one with no
feature map yet): skip this step.

### 3. Read the ground before you ask

**This is the step that decides how good the interview is**, because everything you learn
here is a question you do not have to spend. It is also the step that would eat your
context — and your context is the thing that makes resumption work at all. So **dispatch
it**: two read-only sub-agents in a **single message carrying two `Agent` calls**,
returning findings, not file dumps.

**Everything here is a REPO read.** No tracker, no board, no issue search — §1's rule
holds for the ground read too, and the item's own issue is not an exception to it.

**Unit A — what the product already promised here.** Resolve the ground to a component
first, because both lookups key on it:

```bash
python3 knowledge/scripts/component_of.py <path>...
```

A `-` means no component claims that path — say so and treat the ground as uncovered.
Then, in order: the **feature map** for the area (`knowledge/features/<area>.md`), found
by component rather than by guessing a filename — the feature maps `slot:feature-maps`
names declare the components they cover, so the join is *maps whose component list names
this id* — and the **requirement register(s)** that govern that component:
`python3 knowledge/scripts/requirement_query.py decided --components <component-id>` lists the rows, and the
register each row belongs to is the register that governs it (`slot:commitments`
says how a register declares its components). Read each matching row's `Disposition` **and** its `Kind`.

**Unit B — the neighbourhood.** The nearest existing component
(`slot:components`), the nearest program and slice
(`knowledge/programs/rows/`, `knowledge/slices/rows/`, and `python3 knowledge/scripts/program_of.py`
<SL-NNN | <prd-number> | <component-id> | <path>...>`), the enumerated set of feature
areas —

```bash
<slot:feature-areas>
```

— and what is already **in flight** on that ground: PRDs whose frontmatter is non-terminal,
and open pull requests touching those paths (`gh pr list --state open`). Unit B is what
makes the *nearest existing*, *provisional tier* and *what it depends on or would collide with*
fields of the dossier answerable at all.

**Distinguish two things Unit B will find, because they have different outcomes.**
Ground merely *adjacent* to in-flight work — a PRD nearby, a slice on the same component —
is not a duplicate; it is the single most useful line in the dossier, and you keep
shaping. **The same want, already captured as its own item**, is a duplicate: hand it back
(§8) as `looksLike: "duplicate"`, naming what you found, rather than producing a second
dossier for the human to reconcile against the first.

> **A refusal or a deferral is not a promise, and reading one as a promise is the single
> worst thing this command can do.** A commitment is *affirmative and adopted, with an id
> you can cite*: a register row that promises (an `invariant`, `requirement` or
> `constraint` with `Disposition: adopted`), a feature-map capability row, an adopted PRD
> or slice. *"Do not X"*, *"not yet"*, *"deliberate and eventual, never opportunistic"* —
> each is the **opposite** of a commitment, and a `Kind: excluded` row is a refusal even
> though its `Disposition` reads `adopted`. This is not hypothetical: on a gate
> quoted *"Do not rename them — that migration is deliberate and eventual, never
> opportunistic"* back into a verdict as *"the adopted rename migration"*, releasing a
> nine-chunk programme no human ever approved. A dossier that puts a prohibition in the
> promise field hands [`/fleet:route`](route.md) a manufactured commitment, and route
> has no way to know it was manufactured.
>
> **Uncovered ground is a finding, not a failure.** Most of the product carries no
> register yet. Write *"nothing on this ground"* plus the component id, and let the
> emptiness be visible — it is the only place that signal is generated.

### 4. What is actually unknown — the question budget

Now, and only now, list what you still cannot write. **Test every candidate question
against two things before it earns a slot:**

1. **Did §3 already answer it?** If a search you have already run would have produced
   the answer, the question is a defect. Delete it.
2. **Is it theirs to answer?** The boundary is not a matter of taste:

| Theirs — worth asking | Yours — never ask |
|---|---|
| what happens today when they need this, and what it costs | which component owns the ground |
| who hits it, and how often | which requirement rows govern it |
| what has to exist first, or what this would collide with | which slice or program it would land in |
| how they would know it worked | whether the register covers this area |
| what this deliberately does **not** do | what the feature map already claims |
| whether waiting a quarter is survivable | what the nearest existing capability is |
| | **what should wait instead — ordering for timing is `priority`, never a question** |

A right-column question is not merely wasteful — it transfers your job onto the one
person whose attention this command exists to spend well, and their guess then reads
downstream as a specification.

**The ceiling is eight questions across the whole interview.** That is a ceiling on the
filer's attention, not on machine cost: you may read for an hour, and you may ask eight
times. **Count it off the payload, not off memory** — the counter is the number of prior
questions inlined into your system prompt plus the ones you are about to emit, so it
survives a cold restart. Ask **at most four per round**, most-blocking first
([`interview-protocol`](../../process/interview.md) item 5), which
makes two rounds the normal shape and three the maximum. **Prefer two rounds of four to
eight rounds of one:** every round costs the filer a context switch, and the fourth
switch is where they stop answering.

**On reaching the ceiling: stop.** Write the dossier as it stands, put everything still
open into its final field verbatim, and emit it. **Never a ninth question**, and never a
"quick clarification" that is a ninth question wearing a different word. An honest
dossier with three open items is decision-ready; a filer who stopped replying is not.

If **nothing** is genuinely unknown after §3 — it happens, and it is a good outcome —
skip §5 and §6 entirely and go straight to §7. A round asked to look thorough is the
same defect as a ninth question, one cycle earlier.

### 5. Ask: emit a questions result, end the turn, be resumed

**A round is a `questions` result file and the end of your turn.** You do not move the
issue to `Needs answer` — fleet does that, from your file — you do not post anything, and
you do not wait in-session: you write the file (§8 owns the path and the mechanics), write
the sentinel (§10), stop. Fleet resumes this same session when the answers land.

**Brief before you ask — it is mandatory and it precedes the first question of the
round.** The person answering has read none of what you just read, and the capture may be
days old. The `brief` field carries three things in at most eight lines: what this would
let somebody do that they cannot today, in ordinary English; one worked example with a
named person and what they see; and one line naming what is genuinely undecided, so the
questions read as a fork rather than a quiz.

**The `questions` result — the exact shape:**

```json
{
  "kind": "questions",
  "brief": "What I am shaping: …\nFor example: …\nWhat is undecided: …",
  "questions": [
    {
      "id": "q1",
      "prompt": "What happens today when the weekly export is wrong — who notices, and what do they do about it?",
      "allowFreeText": true,
      "options": [
        {
          "id": "a",
          "label": "They re-run it by hand",
          "then": "Somebody spots it and re-runs the export themselves. Why: the fix is local, so nothing downstream is wrong for long. Con: it costs a person every week, and nobody knows how often it happens.",
          "recommended": true
        },
        {
          "id": "b",
          "label": "It ships wrong and gets corrected later",
          "then": "The bad export goes out and is corrected once a customer complains. Why: nobody spends time on it up front. Con: the error reaches customers, so the cost lands outside the team.",
          "recommended": false
        }
      ]
    }
  ]
}
```

**Every rule in that shape is load-bearing:**

- **2–4 options, exactly one with `recommended: true`.** A recommendation you did not mark
  is not a recommendation. Zero marked is a deferral; two marked is not a fork.
- **`then` carries a rationale on EVERY option, not just the recommended one** — what
  changes for a real person, then *why* it works, then *what it costs*. An option whose
  `then` merely restates its `label` is a defect: the filer cannot pick against you if
  only your pick was argued.
- **`allowFreeText: true` on every question.** `AskUserQuestion` appends an "Other" escape
  automatically and the protocol tells you not to add one; that tool is not in play here,
  so the escape is not automatic and you set it yourself. Without it, a question with four
  wrong options extracts a wrong answer rather than no answer.
- **One dimension per question.** Two independent forks folded into one produce an answer
  to neither.
- **The recommended options must survive being taken together.** Before you emit the round,
  take every `recommended: true` option at once and read the `draft` they produce: if one
  recommendation gives up the very thing another question asks about, or the thing the drafted
  `howYouWouldKnow` measures, the round contradicts itself and the filer is asked to settle a
  fork you already closed. Change the recommendation, or drop the question it made moot — never
  ship both. (INTAKE-88: question 1's recommended answer accepted losing the per-issue line,
  while question 2 and the success check were both about that line.)
- **`prompt` states what the question is establishing** (§1's cold-restart rule), so an
  answer is interpretable without the reasoning that produced it.
- **No planning or tracker id in a `label`, ever** — and nowhere at all without the plain
  name it stands for attached the first time. Ids belong in the dossier, as evidence.
- **Plain words throughout.** Explain each internal noun in half a sentence of ordinary
  English the first time it appears. Being asked to explain it again more simply is a
  defect in the question: re-ask in full, and hold the plainer register for the rest of
  the run.

> **The one question that carries no options**, and the only one: when the capture is too
> thin to say, in one concrete sentence about a real person, **what somebody does today
> without this**. Then you are in discovery, not at a fork, and the protocol is explicit
> that a menu inverts there — your 2–4 invented options become guesses, the filer picks
> the least-wrong one, and their pick is read downstream as a requirement. Emit it as a
> question with an empty `options` array and `allowFreeText: true`, asking it open:
> *"What happens today when you need this, and what does it cost you?"* One such question,
> in round one, and never after the filer has told you.

**What the round changes — the idea page draws it beside the card.** The filer is shown the
dossier as your round leaves it, next to the question. So: a question whose answer
establishes one dossier field names it in `aspect` (the §8 dossier keys — `whoItIsFor`,
`whatTheyDoToday`, `howYouWouldKnow`, `displaces`, …); each of its options carries
`becomes`, the field as it would read if that option were picked, in the dossier's own
register; and the set carries `draft`, every dossier field you can already state as it
would read if the filer took each recommended option. `problem` is the filer's own words and
is never drafted. All three are optional and a round without them renders as a plain card;
the shaping commands' table of the same fields is `shaping-headless.md` §3.

### 6. Consume the answers

You are resumed, and the answers are in the payload — matched to your questions by `id`.

> **A resume that says *"The person did not answer these questions. They said:"* carries an
> instruction and no answers.** The filer sent the round back rather than answering it: the
> ground has moved since you asked, and the checkout is already at the trunk's current head
> (the prompt's first line names it). Re-read the ground (§3) at that head rather than trusting
> the reading above, act on the instruction, and re-test what is still unknown (§4) — then ask
> again, as a round that replaces the one sent back, **only** what still needs the filer. None
> of the returned questions was answered, so nothing below applies to them; if nothing still
> needs the filer, write the dossier (§7).

- **Take the filer's answer as given.** They are the authority on their own problem, their
  own workaround and their own priorities. A model does not overrule the person whose
  problem it is.
- **A free-text answer beats a picked option**, always — quote it into the dossier rather
  than normalising it into the nearest option you offered.
- **An answer of `CAN'T ANSWER` is the person saying the question was never theirs to answer**
  — the idea is a customer's, and the owner cannot know *who runs into it, or how often*. It is
  not an answer and not a refusal: **follow
  [`interview-protocol`](../../process/interview.md) → *"I can't answer this"*, which is the one
  rule and is not restated here.** In this command: write an `Assumption: …` line marked
  unconfirmed — or, when the card was *for the customer* (or the question is about their own
  experience), carry it as `For the reporter: <the question, verbatim>` and assume nothing —
  put every such line in the dossier's `unconfirmedAssumptions` (§7), never ask it again, and
  never present one as something the owner said. The card offers the choice itself, so you
  never add *"I don't know"* as an option.
- **A partial answer is an answer.** Three questions asked, two answered: consume the two,
  and the third goes into the dossier's open-items field. Never re-ask an unanswered
  question — that is a ninth question wearing a seventh's number.
- **An answer that changes the ground sends you back to §3, not to §5.** If the filer says
  something that moves which component or capability this touches, re-read the ground
  before asking anything else; a second round built on a stale ground read spends the
  filer's remaining attention on the wrong fork.

Then return to §4 and re-test what is still unknown against the ceiling.

### 7. Write the dossier

**One fixed shape, every time, whether the interview closed everything or nothing.** The
shape is the product: a reader who has learned where the promise field is must find it in
the same place on every dossier, or they go back to reading the whole capture, which is
the thing this command exists to spare them. **Nine required fields, plus the one optional
`unconfirmedAssumptions` and `placement` below — no other.**

| Field | What goes in it |
|---|---|
| `problem` | the filer's own words, **quoted verbatim** |
| `whoItIsFor` | the person, by role, and how often they hit it |
| `whatTheyDoToday` | the current workaround, and what it costs them |
| `alreadyPromised` | the affirmative adopted ids that cover this ground, one line each — or *"nothing on this ground — component `<id>` is claimed by no register"* |
| `nearest` | the nearest existing component and program — or *"none"* |
| `provisionalTier` | a PRD inside an existing cut · a new slice · a program — plus one line why, in the ladder's terms |
| `displaces` | the in-flight work this depends on or would collide with, named — a build-order fact, never a queue position — or *"none on this ground"* |
| `howYouWouldKnow` | one falsifiable observation a person could make |
| `openItems` | the open items, verbatim — or *"nothing"* |
| `unconfirmedAssumptions` | **optional — the tenth key, and only when there is something to list.** One line per question the owner marked *"I can't answer this"*: `Assumption: <what you assumed and why> (unconfirmed by the owner)`, or `For the reporter: <the question>`. **Omit the key entirely when there are none** — an empty or *"none"* value is refused, because it would claim a review that never happened. |
| `placement` | **optional — only when §2b asked the placement question.** The answer as `{choice, area?, areaName?, use?, newUse?, newFeature?, confirmedBy}` (feature-flow guidance). Route is bound by it; omit the key when no placement was asked. |

**Field rules that are not obvious, and each of which has already cost something
somewhere:**

- **The filer's words are quoted, never paraphrased.** The moment their sentence becomes
  product language it stops being evidence and starts being your proposal. If their
  sentence is long, quote the load-bearing clause and nothing else — never a smoothed
  rewrite.
- **`alreadyPromised` is where a dossier goes wrong.** It takes **affirmative adopted ids**
  and nothing else. A prohibition, a deferral, a `rejected` row, an `excluded` row — none
  is a promise, and each must be recorded as what it is: *"a standing refusal governs this
  ground: `<id>`"*, which is a **stronger** signal to the human than an empty field, not a
  weaker one. If the fit needs a sentence of argument to hold, it is not a match; write
  *"nothing on this ground"*.
- **`provisionalTier` is a classification — never an authored field.** Say which rung it
  lands on and why, in the ladder's terms (the shared planning ladder, inlined under
  **Loads**): every work tier holds at least two of the tier beneath it and adds a completion
  condition its children do not have — so a single deliverable is never a program, and the one
  line says why it is not the next smaller rung. **Do not draft the artifact the next command owns** — no `Done when`, no `Kind`,
  no name, no acceptance criterion. Measured: a `route` session emitted a complete
  `Done when` whose persona and refusal rule came from an unrelated PRD and had never been
  stated by the requester, and the next command read it as pinned-down input and skipped
  the interview that would have caught it. Quoting an **existing** cut's `Done when` to say
  *which* cut you mean is evidence and is fine; writing a new one is authorship and is not.
- **`displaces` is a dependency, never an ordering.** It records only what this would have to be
  built **after**, or would **collide with** on the same files, slice or flow — one line each,
  with the plain name. If nothing in flight touches this ground, write *"none on this ground"*;
  an honest unknown is *"unknown"* plus the reason. **Never record what should wait, what it
  displaces from a queue, or what the filer would accept not having** — that is ordering for
  timing, it belongs to `priority` set downstream, and a model has no standing to decide it.
- **`howYouWouldKnow` is an observation, not a metric and not a test name.** Something a
  person could watch happen. If it names a grant, a role or a credential, phrase it as the
  **exercise** — the call performed as the principal that executes at runtime, with the
  response seen — never the configuration state: a binding verified present still `403`'d
  on every tick for ~100 minutes.
- **`openItems` is never empty by default and never padded.** Write `"nothing"` when the
  interview closed everything, and the open items **verbatim** when it did not — in the
  filer's framing, so a later session can ask them without re-deriving the question.

**Then the completeness gate, and it is hard.** Nine keys, all present (the optional tenth, when
present, a non-blank string), none empty, none
`TBD`, none carrying a prohibition in `alreadyPromised`, none carrying an id with no plain
name attached. A dossier that fails this is not emitted — fix it and re-check.

### 8. The result file — the output contract

**One file, written to the path in `$FLEET_RESULT_FILE`, carries everything this command
establishes.** The daemon picks it up from there. It is not, however, the whole of what
the run owes: the **done-sentinel** (§10) is a second, separate obligation, and a session
that writes a perfect result file and no sentinel is nudged to `max_relaunches` and then
reported `failed`. Three kinds, one shape each:

```json
{
  "kind": "questions",
  "brief": "<the ≤8-line brief>",
  "questions": [
    {
      "id": "<stable within the run: q1, q2, …>",
      "prompt": "<the question, in plain words, saying what it establishes>",
      "allowFreeText": true,
      "aspect": "<optional: the dossier field this answer establishes>",
      "options": [
        {"id": "<a, b, c…>", "label": "<short, plain, no ids>", "then": "<what changes for a real person · Why · Con>", "recommended": false, "becomes": "<optional: the field, as it reads if this is picked>"}
      ]
    }
  ],
  "draft": {"<dossier field>": "<optional: as it reads after this round>"}
}
```

```json
{
  "kind": "dossier",
  "dossier": {
    "problem": "…",
    "whoItIsFor": "…",
    "whatTheyDoToday": "…",
    "alreadyPromised": "…",
    "nearest": "…",
    "provisionalTier": "…",
    "displaces": "…",
    "howYouWouldKnow": "…",
    "openItems": "…",
    "unconfirmedAssumptions": "<optional — omit the key when nothing was marked can't-answer>",
    "placement": {"choice": "extends", "area": "<slug>", "areaName": "<Feature>", "use": "<Use>", "confirmedBy": "<who answered>"}
  }
}
```

```json
{
  "kind": "handback",
  "why": "<one or two plain sentences: what this actually is, what you saw that says so, and the decision being asked — re-kind this capture as Type:bug/Type:task, or discard it (the park comment is rendered from this)>",
  "looksLike": "bug|task|question|duplicate"
}
```

**`looksLike` is a closed set of exactly those four values.** A filing that fits none of
them is not a licence to add a fifth: the vocabulary is owned in the Fleet task list
, not here, for the same reason the spine's Artifact ids are owned in
[`spine.md`](../../process/spine.md) — a wire format that any
command file may extend is not a contract. Pick the closest of the four, say what you
actually saw in `why`, and report the mismatch; adding a value is a Fleet decision.

**The path comes from the environment. Never invent one, and never guess a default.**

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

**If `$FLEET_RESULT_FILE` is unset or empty: report that and stop.** Emit nothing —
nothing anywhere, and then say so in the sentinel. Do not write to a scratch path and
hope, do not print the JSON as if printing were delivering, and — above all — **do not
fall back to a tracker write**. The issue's existence is exactly what makes that
tempting and exactly why it is worse than silence: no part of this loop reads a comment
you leave there, so the fallback delivers nothing, while fleet goes on writing that
issue's moves as projections of a result file it never received — a park with nothing
behind it. An intake that produced nothing and said so is recoverable in one
re-dispatch. An intake that wrote somewhere nobody reads is lost silently, which is the
one failure mode with no signal attached.

**Write it once, whole, and check it.** Serialise the complete object, write it to the
path in a single write, then read it back and parse it — a truncated or half-written file
is a parse failure at the daemon, and the daemon cannot tell that from a session that
crashed.

**If the kind is `questions`, check its shape before you write the sentinel.** Run

```bash
python3 knowledge/scripts/validate_questions.py "$FLEET_RESULT_FILE"
```

It exits `0` when the set meets every rule the question table enforces — two to four options
(or none, for an open free-text question), at least one recommended, each option carrying an
`id`, a `label` and a `then` — and exits `1` naming the rule that broke (and `2` when there
is nothing to check). **A set that breaks a rule is refused by the service after the run is
over, when this session is already gone and can no longer fix it**; correcting it here, in
the same turn, is the only second chance there is. Fix what it names and re-run it until it
is green, then write the sentinel and stop.

**Exactly one result file per turn, and all three of them end the run.** Nothing on the
box reads what you wrote — the daemon breaks its relaunch loop the instant a done-sentinel
exists, reports the run and releases the claim — so a `questions` result does not hold
your seat open a moment longer than a `dossier` does, and is not meant to: a session
waiting in place for a person is the pinned seat that design exists to avoid. What a
`questions` result alone does not end is the **interview**, which resumes into this same
engine session on the item's next dispatch. So in every case: emit, write the sentinel,
stop. Emitting a `handback` and then continuing to shape, or emitting one expecting a
reply, is the same defect in two directions.

### 9. Closing report

**First, the no-promise gate.** In the workspace checkout:

```bash
git status --porcelain && git branch --show-current && git stash list
```

A clean tree, the branch you started on, no stash. Anything else means you did build work
in a shaping session: revert it (`git checkout -- . && git clean -fd`), delete any branch,
close any PR you opened with a comment saying an intake session opened it in error — and
say so plainly on the `Breach:` line. Do not quietly leave it because it looks correct;
work nobody scoped is exactly what this command exists to stop.

Then nine lines, no more:

```
intake — <asked | shaped | handed back: <looksLike> | no-result-path>
Problem:    "<the filer's own words, trimmed to the load-bearing clause>"
Ground:     <the adopted ids that cover it | "uncovered — component <id> is claimed by no register">
Nearest:    <component · program | "none">
Tier:       <PRD in an existing cut | new slice | program> — provisional
Questions:  <n> of 8 spent across <r> round(s)
Open:       <what shaping could not close | "nothing">
Result:     <questions | dossier | handback | none — <why>> → <$FLEET_RESULT_FILE, or "unset">
Breach:     <"none" | what you wrote and what you reverted>
```

**The `Ground:` line is the one that compounds.** Every idea shaped on ground no register
covers is a countable signal about where the backfill is worth doing next, and a component
id is countable where "this area seemed uncovered" is not. Name it every time it happens.

### 10. The done-sentinel — the last thing you write

**The report above is for a human reading the transcript; the sentinel is what the daemon
reads, and the run is not over without it.** Your dispatch mission names the path and owns
the exact keys — it is the system prompt and this section is only its companion. What
matters here is that the result file is *not* the whole deliverable, and three things
about the sentinel that a reader of §8 alone would get wrong:

- **`status` is `"needs-decision"` for all three endings** — a question round, a dossier
  and a hand-back alike. Every one of them ends with a person owing something: the filer
  owes an answer, or a human owes the call on what you shaped. Neither is yours to make,
  so **none of the three is a failure** and none of them charges an attempt. Reserve
  `"partial"` for an interview that is genuinely incomplete and that another attempt could
  finish, and `"failed"` for not having been able to run at all.
- **`pr` is always an empty string.** An interview opens no PR — the no-build rule that
  says so is the contract, not a step you skipped.
- **Result file first, read back, *then* the sentinel.** Which state the item lands in is
  decided by the result file and not by that word — a question set puts it in
  `Needs answer`, in the filer's own inbox, where their answer resumes you; every other
  ending puts it on a human at `Intake · decision`, the fleet's idea page and not the
  operator's `Blocked · decision` queue. So a round written to the wrong path
  or written malformed does not merely lose the questions: it parks the item in an
  operator's queue with nothing there for them to answer.

**Write it even when you wrote no result document** — the unset-`$FLEET_RESULT_FILE` case
of §8 is exactly the one where the sentinel is the only signal that anything happened at
all, so say there what stopped you.

> **The nudge you get for omitting it reads like an instruction to re-ask, and it is not.**
> A session that leaves no sentinel is nudged to `max_relaunches` and then reported
> `failed`, however good the document it left behind — and the nudge says *continue*. If
> you have already written a result file this turn, continuing means **writing the
> sentinel and stopping**. It never means a second result file, and it never means asking
> the same round again: a question set already written is waiting on a person, not on you,
> and re-asking is how a filer receives the same round twice and learns to ignore both.

---

## What this is NOT

- **Not a triage, and not the gate that judges scope.** You set no priority and reach no
  scope verdict. Whether the product should build this is the human's call, and a
  `handback`'s `looksLike` is a description of what the filing appears to be — never a
  routing decision, never a rejection, and never a judgement that the work is out of
  scope.
- **Not a routing decision.** The tier call is provisional evidence;
  [`/fleet:route`](route.md) re-walks the ladder with the dossier in hand and is the one
  that decides.
- **Not a tracker client.** There *is* an issue, and its key names this work — but you
  read, create, update, park and close nothing on it. Every move it makes is fleet's,
  written as a projection of the file you leave. Context arrives inlined in the dispatch
  payload; your output leaves as that result file plus the done-sentinel.
- **Not a PRD, a slice, a program, or a draft of any of them.** No `Done when`, no `Kind`,
  no acceptance criterion, no name for a thing that does not exist yet.
- **Not a filer.** [`/fleet:idea:create`](idea/create.md) parks an idea in the tracker;
  you shape a captured one that fleet handed you.
- **Not a design conversation.** "How should this work?" is a later command's job, and
  asking the filer to design it spends their attention on the one thing they came here to
  avoid doing.
- **Not a place to be helpful.** Adding an adjacent idea, minting a fourth result kind or
  a fifth `looksLike` value, or widening the dossier past its nine fields (and the one optional key) is exactly the
  behaviour a fixed shape exists to prevent — from you most of all.

---
description: "Make a mockup for one surface and hand back one a person has seen and approved: pick a reference, build it in the project's real parts, render and critique it to the bar, then ask."
---
# Mockup — make the design, look at it, then ask

Make a **mockup** for one surface and hand back something a person has already looked at and
approved. One run does the whole loop: pick a reference above the project's own average, build
the round in the project's real parts, **render it headless in every state, critique it against
the bar, fix it**, and only then put it in front of a person.

This is the command that owns the mockup. Other commands call it rather than restating how to
draw: the PRD design and create steps, and page
improvement.

`$ARGUMENTS` — the surface to mock, and optionally its tier (`explore` or `lock`) and where it
belongs. *"the dependencies page, lock tier"*, *"two directions for the queue filter bar"*, or
nothing at all when a caller is invoking this as one step of its own work.

> **The procedure is generic; the project's facts are slots.** Every rule below that could differ
> between projects reads `slot:ui-contracts` and `slot:mockup-conventions`. Nothing here names one
> repository's paths, tokens or browser harness. The full procedure is
> [`process/mockup-loop.md`](../../process/mockup-loop.md); the taste bar it measures against is
> [`process/design-fidelity-loop.md`](../../process/design-fidelity-loop.md) §2.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `critique` is the loop that makes this command different from drawing a picture — it does not exit until the render clears the bar or the rounds run out. `approve` is a HUMAN gate: nothing is "done" until a person answered. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "mockup",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Make a mockup for one surface and hand back one a person has seen and approved: pick a reference, build it in the project's real parts, render and critique it to the bar, then ask.",
  "loads": ["process-design-fidelity", "ui-contracts"],
  "requires": ["process-spine", "process-interview", "process-design-fidelity", "ui-contracts", "languages", "git-workflow"],
  "optional": ["mockup-conventions", "dev-environment", "audit-profile", "file-conventions", "product-vision", "decisions", "gate"],
  "steps": [
    {
      "id": "classify",
      "name": "Decide whether this is a visual question at all, and which tier",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-1-decide-whether-this-is-a-visual-question"
    },
    {
      "id": "reference",
      "name": "Name the reference above the project's own average",
      "kind": "author",
      "actor": "coordinator",
      "produces": ["reference"],
      "body": "step-2-name-the-reference"
    },
    {
      "id": "explore",
      "name": "Build the round in the project's own parts",
      "kind": "author",
      "actor": "coordinator",
      "produces": ["mockup"],
      "body": "step-3-build-the-round"
    },
    {
      "id": "critique",
      "name": "Render every state, critique, fix, re-render",
      "kind": "loop",
      "actor": "subagent",
      "model": "sonnet",
      "critique": "design-fidelity-bar",
      "loop": {"max_rounds": 3, "exit": "the render clears the bar, or a round fixes nothing"},
      "consumes": ["mockup"],
      "produces": ["screenshots"],
      "body": "step-4-render-critique-and-fix"
    },
    {
      "id": "lock",
      "name": "Promote the chosen round to the product's own components",
      "kind": "io",
      "actor": "coordinator",
      "produces": ["mockup"],
      "body": "step-5-promote-to-the-lock-tier"
    },
    {
      "id": "present",
      "name": "Present it — the person's browser, not your box",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-6-present-it"
    },
    {
      "id": "approve",
      "name": "A HUMAN approves the mockup",
      "kind": "gate",
      "actor": "user",
      "gate": "hard",
      "produces": ["mockup-approved"],
      "body": "step-7-the-human-approval-gate"
    },
    {
      "id": "record",
      "name": "Record what was approved, by file",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-8-record-what-was-approved"
    }
  ]
}
```

## Context to load

- `slot:process-design-fidelity` — the loop this command runs, and the bar it measures against.
  Read [`process/mockup-loop.md`](../../process/mockup-loop.md) first.
- `slot:ui-contracts` — **the single source of the project's design system**: where tokens live,
  how a page is structured, what the components and controls are, how a page is checked, and
  whether this project mounts a page in its own substrate or not.
- `slot:mockup-conventions` — the few facts only this project knows: the mockups directory, the
  tier it can mount, how a state is addressed. **If it is unanswered**, ask the person where the
  files should go (one question, in their words) and stay at the explore tier.
- `slot:dev-environment` — only for the lock tier: how to bring the app up so a real page renders.
- `slot:audit-profile` — the UI checklist `Q1–Q6` the critique uses, where the project has one.

---

## Step 1: Decide whether this is a visual question at all, and which tier

**A question about the UI is not automatically a visual question.** Ask: *would a person
understand this better seeing it than reading it?* A layout, a density decision, a comparison of
two directions: yes. *"Which permission gates this view?"*, *"should this be a field or a
relation?"*: no — those are text-shaped, and a drawn picture makes them slower, not clearer.

**If it is not visual, stop.** Say what you would have mocked and why it does not need one, and
return to the caller. Do not produce a mockup to look thorough; a mockup nobody needed is the
same waste as a question nobody asked.

**Then pick the tier** (`process/mockup-loop.md` → *The two tiers*):

- **explore** — framing the problem, or choosing between directions. Throwaway rounds.
- **lock** — the round a person will approve. Requires `slot:mockup-conventions` to name how the
  project mounts a page, and `slot:dev-environment` to bring the app up. **If the project cannot
  mount one**, this is the case where the explore file *is* the lock: say so plainly, once, and
  carry on at explore tier rather than pretending to a promotion that cannot happen.

A caller may fix the tier where
its own procedure says which tier it needs. Respect it.

## Step 2: Name the reference

Before drawing anything, name **at least one real rendered surface of the same archetype**
(list / detail / settings / cockpit) that this design would be proud to be mistaken for, and write
one line on **what about it** is the target: density, rhythm, restraint, hierarchy.

- Prefer an **internal exemplar** — a page in this project that already clears the bar. It is the
  strongest evidence there is, and it costs no third-party screenshot.
- Otherwise a specific page from a product with strong craft, named precisely (*"a tracker's My
  Issues list"*, not *"a tracker"*).
- Where the project commits a reference image, put it at `reference-<archetype>.png` in the round
  directory — the one raster that belongs there (`process/mockup-loop.md` → *What a mockup
  directory contains*).

The reference sets the **ceiling**; the project's own tokens and components supply the **parts**.
Naming a reference is not permission to leave the design system.

## Step 3: Build the round

Use [`process/mockup-loop.md`](../../process/mockup-loop.md) steps 3–5, in this project's
answers:

1. **Read the parts now.** Open the token file, the page structure and the controls
   `slot:ui-contracts` names, and copy what is **actually there today**. Never from memory, from an
   older mockup, or from a command body — a hand-copied token is a frozen snapshot that lies about
   the colours.
2. **Write the files under the mockups directory** `slot:mockup-conventions` names. One
   self-contained `index.html` per round (inline CSS, no CDN, no remote fonts or images) plus
   whatever sits beside it. **Never in a scratchpad**; the committed file is the design contract,
   because every downstream agent runs headless with the repository and nothing else.
3. **Make every state reachable and the flow clickable.** Populated, empty, loading, error, and
   each dialog or sheet — each addressable by `?state=<name>` or its own linked page, wired with
   ordinary `<a href>` elements. No `href="#"`, no dead control.
4. **Match the project's posture** — its light/dark default, its system font stack, its density.
   If the project ships no custom font, the mockup uses none.

For **explore**, build 2–3 genuinely divergent directions as separate rounds. Convergence is the
enemy here: three variations of the same card is one direction drawn three times.

## Step 4: Render, critique, and fix

**This is the step whose absence the whole command exists to close.** Do not skip it, do not
"visualise" it, and do not hand a person anything before it has run.

1. **Render.** Open the mockup in a real browser — the project's browser harness, or a
   a headless-browser run — at **1440×900 in
   every state**, and at phone width where the project
   has one. Capture each state. A render is a delivery mechanism: write it to a scratch location
   and **do not commit it** (`process/mockup-loop.md` → *What a mockup directory contains*).
2. **Critique, ranked and concrete.** Grade the screenshots against, in order: the reference
   (Step 2), the bar (`process/design-fidelity-loop.md` §2 and the `Q1–Q6` checklist where the
   project has one), and this project's own structure and tokens. Emit a **ranked defect list**,
   highest impact first — *"hero card is ~60% empty at 1440"*, *"three type sizes in the header"*,
   *"the primary action is a ghost button lost against the toolbar"*. Never *"make it nicer"*, and
   never a list of ten equal findings: the loop fixes the top one next.
3. **Fix the single highest-impact defect.** Re-render, re-critique. One at a time.
4. **Exit** at `MAX_ROUNDS = 3`, or when a round fixes nothing, or when the critique is clean.
   **Never loosen the bar to exit.** If it will not clear the bar, that is a finding: the design
   is underspecified — say so, and route the remainder as follow-up work rather than shipping
   "good enough".

Delegate the critique to a **subagent that did not write the mockup** where the harness allows it:
an author grading their own drawing sees their intention, not the pixels.

## Step 5: Promote to the lock tier

Applies only when the run is at **lock** tier and the project can mount one.

Rebuild the chosen round in the project's **real substrate** — the real components, real tokens,
real shell — mounted the way `slot:ui-contracts` says this project mounts a page. This is not
ceremony: an HTML mockup cannot be clicked through against a real component's constraints, and its
tokens are a copy that rots.

Then **re-render the lock-tier page in every state** and critique it again. Promotion can change
the design — a real component refuses a shape the hand-drawn one allowed — and the person should
see the promoted page, not the sketch it came from.

## Step 6: Present it

**A mockup reaches a person ONE way: the fleet's `ask` tool with the mockup attached.** Upload the
round folder with `upload_link`, then ask with `attachments: {bundleId, entry}`. One authority:
[`interview.md`](../../process/interview.md) → *A mockup reaches a person ONE way*.

- The person's browser is on **their own machine**. Never tell them to open a file path, run
  `python3 -m http.server`, or visit `localhost` / `127.0.0.1`. A path is not a presentation.
- Never carry a mockup question in the built-in `AskUserQuestion` alone — it has no attachment.
- Name the states the render covers, briefly, so they know what they are looking at.

## Step 7: The human approval gate

**A model's critique is not an approval, and neither is a chat message.** This is a hard gate.

1. **Invite reaction first.** Ask an open question — *"anything off in the layout or shape before
   we lock it?"* — and **wait**. Do not attach a multiple-choice in the same breath: forcing
   options collapses the mockup into background for a decision they never got to challenge.
2. **Iterate on their words** — back to Step 3/Step 4, re-presenting. A round that fixes nothing
   reconfirms rather than re-asks.
3. **Confirm they actually saw it.** If the reply does not reference the mockup, or is a bare
   *"ok"* / *"continue"*, do not infer they saw it. Ask, with the mockup attached, whether it is
   visible.
4. **Collect the approval as an explicit answer**: *"Approve — lock this mockup"* /
   *"Request changes"*. A prose *"yes"* buried in a paragraph does not clear this gate.
5. **Never self-approve.** If no person answers, the command **stops** with the mockup presented
   and the gate **open**. An unapproved mockup is a blocked design, not a design with a caveat.

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

## Step 8: Record what was approved

Where this project records design decisions (`slot:decisions`, or the calling command's own
document — `ux-design.md` under `## Approved design` for a PRD), record:

- which round and **the repo-relative path of the approved file** — not the viewer link, which a
  later headless agent cannot reach;
- the tier it was approved at, and the reference it was measured against;
- the date, and any conditions the person attached.

Then hand back to the caller. This command **does not merge and does not open a PR** on its own;
it returns an approved artifact. A calling command that owns a document writes it.

---

## What this is NOT

- **Not a picture.** A static image of an idea is a sketch; this command produces a rendered,
  clickable, self-critiqued candidate.
- **Not a design review substitute.** The bar catches craft, not intent. A mockup that clears the
  bar can still be the wrong design — that is what the person's answer at Step 7 is for.
- **Not a place to invent a design system.** If the project has no token file or no components,
  that is a `slot:ui-contracts` gap: say so, and mock with what exists rather than inventing a
  second system the product will never match.
- **Not a gate on every field.** A read-only badge on a shipped page is an `additive` change
  (`process/design-fidelity-loop.md` §1.5c): the instrument there is the page-spec, and a mockup
  is optional. Do not charge surface-sized ceremony for a field-sized change.

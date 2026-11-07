---
description: "File one well-formed Type:task tracker issue saying what the work is, and stop — the checker decides everything else."
---
# Task — Create

File a **`Type:task` tracker issue** the right way — a small, scoped engineering task
to be done later. This is the create-axis sibling of
[`/fleet:task:implement`](implement.md) (which *executes* a task to a merged PR).
This command records the task and **stops** — no plan, no branch, no repo file, and
since the check gate landed, **no triage**: [`/fleet:check`](../check.md) does that in
a fresh session and decides where the task goes.


> **Your job is to say what the work is, clearly enough that someone else can judge
> it.** Priority, area, project, component, blockers and fleet-eligibility are the
> checker's. The one judgement that is genuinely yours is *what happened / what is
> missing*, because you are the only party that saw it.

---

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

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `hands-off` is a real gate, not a note: the filer setting a priority or a Project is the defect this command exists to prevent. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "task-create",
  "tier": "core",
  "sop": "none",
  "needs": "nothing",
  "may merge": false,
  "intent": "File one well-formed Type:task tracker issue saying what the work is, and stop \u2014 the checker decides everything else.",
  "requires": [
    "process-spine", "registers-triage-partition",
    "tracker-identity"
  ],
  "optional": ["components", "feature-areas"],
  "steps": [
    {
      "id": "file",
      "name": "Say what the work is, and file it through Fleet",
      "kind": "io",
      "actor": "coordinator",
      "produces": [
        "tracker-issue"
      ],
      "body": "what-to-do"
    },
    {
      "id": "hands-off",
      "name": "Leave priority, area, project and blockers to the checker",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "what-the-checker-does-next"
    },
    {
      "id": "rule-g",
      "name": "Invoked by an execute command (Rule G)",
      "kind": "io",
      "actor": "coordinator",
      "body": "invoked-by-an-execute-command"
    }
  ]
}
```

## What to do

1. Capture a concise title + a short description of the task: what should change, and
   **why it is worth doing** — the checker judges the second half against what the
   product has already committed to, so a task body that says only *what* leaves it
   guessing. Write the title and the description to the plain-language rule in
   [`process/writing.md`](../../../process/writing.md) → *Write for a reader who does not
   know the code*: the title says what should change and the body says why it is worth
   doing, in words a person who has never opened this repository understands.
2. **File it through the Fleet tools.** Call the `file_issue` tool with `kind: "task"`,
   the title, a body that says what should change and why it is worth doing, and
   `command: "task:create"` — or, when this filing comes from another command's Rule G,
   `command: "<that command> (Rule-G deferral)"` (e.g. `bug:fix (Rule-G deferral)`); Fleet
   ends the body with the one `Filed by <origin> · <command>` line from it, so never write
   that line yourself. When this filing comes from a run under Rule G, put the originating
   issue key in the body too. Pass `repo` = the lane named by the **`tracker-identity`** slot **only when the
   work lands in another repository**; omit it otherwise. Fleet searches for prior art
   on every filing and attaches the dedupe record to the mint, so **run no search of
   your own**. Print the returned `id`, Fleet's `message`, and the `dedupe` record it
   returned. `/fleet:check` re-runs the full prior-art search before anything is
   released.
   **When the work was asked for from a feature** — the person named the feature it is for, or the
   brief's `## Request` carries its `area` — pass that slug as `feature`, and Fleet files the
   issue under it at birth, so nobody links it by hand afterwards. Never choose one yourself:
   with no feature named, omit it, and the checker places the issue.
3. **Push back if it's a feature in disguise** — PRD-worthy work goes through
   `prd:create`, not here. A task is small, single-stream work. (The checker is a
   second net for this, not the first one: a feature filed as a task comes back as a
   proposal for the human, which is slower than routing it right the first time.)
4. **No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools; create a personal key in Fleet under Settings › Connect your tools*. There is no other filing path — never fall back to a tracker script or a tracker key, which a machine outside the install's cluster does not have and must not need.

## What the checker does next, so you don't

Named here only so nobody re-adds it above: `/fleet:check` sets the priority, the
`Component` label, the tracker project (the feature area), any `blockedBy`
relations, and finally either the **`Implement Queue`** state or **`Blocked · decision`**.
It re-runs the full prior-art search against the filed report and appends its own record
before releasing, which is the safety net under Fleet's own title-only search.

**This is where the old "leave `agent-eligible` OFF by default" rule went.** No create
command writes routing labels at all any more — only the checker moves an issue to
`Implement Queue` — so the rule is structural rather than remembered.

**This command files and stops; the checker owns the park.** But if a dispatched filing run
nevertheless ends on a person's decision — a fork its brief does not settle — the park carries
the `decision` document, in the card's own fields:

<!-- include: process/decision-document.md -->
### Parking on a person — the `decision` document (headless)

**Every `needs-decision` park writes one `decision` document, and it is the interview card
in fields.** The person clearing `Blocked · decision` reads this card and nothing else —
not the issue, not the PRD, not the register, not your comment thread. The sentinel's
`summary` is its headline (the rules for it are below); everything a person needs to decide
goes here. Write it to `$FLEET_RESULT_FILE` (skip only if that is unset) before the
done-sentinel:

```json
{
  "kind": "decision",
  "brief": {
    "work":    "What somebody will be able to do that they cannot today, in plain words.",
    "example": "One named person doing it, and what they see.",
    "stopped": "What stopped this run, in plain words — the fork, not the log.",
    "stakes":  "What is at stake either way."
  },
  "context": [
    {"ref": "AC-4", "name": "automated comments never reach the customer",
     "quote": "<the criterion's own text, verbatim>", "url": "<optional https link>"}
  ],
  "question": {
    "id": "<short id>",
    "prompt": "The decision, as one question in plain words.",
    "options": [
      {"id": "<short id>", "label": "<what the person picks, no ids>",
       "why": "<why this is right>", "cost": "<what it costs>",
       "then": "<what happens next if picked>", "recommended": true},
      {"id": "…", "label": "…", "why": "…", "cost": "…", "then": "…", "recommended": false}
    ]
  }
}
```

- **Two to four options, the recommended one first** and the only one marked `true`;
  `why`, `cost` and `then` on **every** option.
- **Quote what you cite.** Every acceptance criterion, requirement, issue or PRD the question
  leans on gets a `context` entry whose `quote` is its own text — or, in prose, the plain name
  with the id in parentheses: *the automated-account rule*. A bare `AC-4`, `REQ-NNN`,
  `<KEY>`, `PRD NNNN`, `SL-NNN`, `PR #123` or a bare command name is refused.
- **Labels carry no ids at all**, and nothing says where the issue was parked — the fleet
  says that, and the person reading is already there.

**The `summary` is still the first thing a person reads**: on their request's own page, its
Cockpit row and the park list, wherever no card is drawn. So it is written to them, not to the
fleet:

- **One or two plain sentences, addressed to the person**: what Fleet found, then the choice.
- **Name things by their titles, in quotes, never by ids.** No slice, PRD, capability, issue,
  pull request or filing id, not even in parentheses, and none of Fleet's own nouns (slice, PRD
  stub, capability row): a person asked for a plan, a feature, a fix. The ids belong in the
  document's `context`, where the card quotes them.
- **Say what each answer does**: *"Withdraw this request, or send it back if you want … anyway."*

Write *"This use already has a plan, 'Bring the whole local service up with one command',
accepted earlier today. Withdraw this request, or send it back if you want a second plan
anyway."*, never *"Slice SL-NNN, its two PRD stubs and its capability rows already sit on main from the
accepted sibling filing, so this idea's plan would duplicate it"*.

**Check both before the sentinel** and fix every reason it prints, in this turn:

```bash
python3 knowledge/scripts/validate_decision.py --summary "<the summary you will write>" "$FLEET_RESULT_FILE"
```

`0` meets the card; `1` prints every rule broken; `2` means there is no `decision` document at
the path. A park with a missing or refused document still parks — the fleet does not strand a
person's decision over its shape — but the park is recorded as `askRefused` with your reasons,
and that is counted.
<!-- /include -->

## Invoked by an execute command (Rule G)

When [`autonomous-drive.md`](../../../process/autonomous-drive.md) Rule G
fires — an execute command found an **important follow-up task** out of scope — this
command files it (don't bolt it onto the in-flight branch). **Put the originating issue
key in the body**; the run's `filed_from` records it, and the checker sets any blocker.
The caller logs it in its Autonomous Decisions Log. If the step-4 refusal fires inside an
execute command, the caller records the follow-up in its own Autonomous Decisions Log and
carries on, rather than failing its run.

## What this is NOT

- Not execution — that's `task:implement`.
- Not triage — that's [`check`](../check.md).
- Not a PRD — heavier work is `prd:create`.
- Not a repo artifact — tasks live in the tracker, never in `knowledge/`.

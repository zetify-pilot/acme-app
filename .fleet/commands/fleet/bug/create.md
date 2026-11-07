---
description: "File one bug tracker issue carrying the forensic evidence only the filer can supply — reproduction, observed vs expected, the log line — and stop."
---
# Bug — Create

File a **bug tracker issue** the right way. This is the create-axis sibling of
[`/fleet:bug:fix`](fix.md) (which *executes* a bug to a merged PR). Creating a bug
does **not** fix it, and — since the check gate landed — it does not *route* it either:
it records the forensic evidence and hands the issue to
[`/fleet:check`](../check.md), which triages it in a fresh session and decides where
it goes.

> **Your job is the evidence, and nothing else.** Priority, area, project, component,
> blockers and fleet-eligibility are all set by the checker. You are the only party
> that can supply the reproduction, the observed-vs-expected, and the log line — so
> spend everything here and let the gate do the rest. Guessing a priority for a defect
> you just found is exactly the self-assessment the gate exists to replace.

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

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `evidence` is the whole job: the filer is the only party who can supply it, and the only party forbidden from triaging it. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "bug-create",
  "tier": "core",
  "sop": "none",
  "needs": "nothing",
  "may merge": false,
  "intent": "File one bug tracker issue carrying the forensic evidence only the filer can supply \u2014 reproduction, observed vs expected, the log line \u2014 and stop.",
  "loads": ["process-issue-shape"],
  "requires": [
    "process-spine", "process-issue-shape", "registers-triage-partition",
    "tracker-identity"
  ],
  "optional": ["components", "feature-areas"],
  "steps": [
    {
      "id": "evidence",
      "name": "Record the evidence \u2014 repro, observed vs expected, the log line",
      "kind": "author",
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

## Context to load

- [`../../../process/issue-shape.md`](../../../process/issue-shape.md) —
  the canonical "create a well-formed tracker issue" contract.

## What to do

1. Gather the bug context: a one-line title, and **forensic** detail in the body —
   repro steps, observed-vs-expected, stack/log excerpt, suspected `file:line`.
   A bug with no observation and no artifact is not a bug report; the checker closes
   those, so do not file one. Write the title to the plain-language rule in
   [`process/writing.md`](../../../process/writing.md) → *Write for a reader who does not
   know the code*: the title says what is broken in words a person who has never opened
   this repository understands, and the repro steps and `file:line` evidence stay in the
   body.
2. Set **severity** and **source** in the body (the typed fields the issue shape names
   for a bug). Severity is a *description of the
   harm you observed*, not a routing decision — the checker derives the tracker
   priority field from it.
3. **File it through the Fleet tools.** Call `file_issue` with `kind: "bug"`, the title,
   the body, `command: "bug:create"` (or `command: "<that command> (Rule-G deferral)"` when
   another command's Rule G sent you here), and `repo` = the lane named by the
   **`tracker-identity`** slot **only when the work lands in another repository**. The same
   call serves a bug a person reported to you and a defect you found yourself (a red CI
   lane, a broken test, a regression you hit mid-run). For a defect found during other work,
   put provenance in the body as `Found during: <KEY>`.

   **When the work was asked for from a feature** — the person named the feature it is for, or the
   brief's `## Request` carries its `area` — pass that slug as `feature`, and Fleet files the
   issue under it at birth, so nobody links it by hand afterwards. Never choose one yourself:
   with no feature named, omit it, and the checker places the issue.

   A bug filed through the tools is born in **`Triage Queue`** as a bug — no person-confirmed
   reproduce stage, whoever's key the session holds. `/fleet:check` confirms it is real and
   runs the full prior-art search before anything is released, so **run no search of your
   own**. Print the returned `id` and Fleet's `message`; the filing is done when its tracker
   key appears (`get_issue` on the `id`). Never re-file a bug as a `task` to reach Triage.

   **A defect in the fleet itself is not a bug in the repository.** When what you found is a
   defect in the fleet — the control plane, the daemon, or the command tier, rather than the
   `repo` checkout's own code — pass `subject: "fleet"`. The filing is then recorded in the
   install's operator inbox and opens **no tracker issue at all**: on a customer install the
   lane's tracker is the customer's own repository, and a fleet-internal defect opened there
   becomes a public issue in their repo and is handed to their workers. Leave `subject` out
   for a defect in the repository's own code; that one still goes to its tracker.

   **No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools; create a personal key in Fleet under Settings › Connect your tools*. There is no other filing path — never fall back to a tracker script or a tracker key, which a machine outside the install's cluster does not have and must not need.

4. Print the created issue key (and Fleet's message).

## What the checker does next, so you don't

Named here only so nobody re-adds it above: `/fleet:check` sets the priority, the
component, the feature area, any blockers, and finally either the **`Implement Queue`**
position (fleet takes it) or **`Blocked · decision`** (the human owns the call). It
re-runs the full prior-art search against the filed report and appends its own record
before releasing.

**This command files and stops; the checker owns the park.** File only;
`/fleet:check` releases it. But if a dispatched filing run
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
fires — `prd:implement` / `task:implement` / `bug:fix` found a bug **out of the
current scope** — this command files it as an agent-found defect (never fix it inline;
that's scope creep and skips reproduce-first TDD). **Link the new issue back** with
`Found during: <KEY>` in the body, and the caller records it in its Autonomous Decisions Log.

## What this is NOT

- Not a fix — that's `bug:fix`.
- Not triage — that's [`check`](../check.md). Do not set priority, area, project or
  the `Implement Queue` position here — file only; `/fleet:check` releases it.
- Not a repo artifact — bugs live in the tracker, never in `knowledge/`.

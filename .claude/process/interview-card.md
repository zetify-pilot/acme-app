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

6. **The person may not be the one who knows — every question can be answered *"I can't
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

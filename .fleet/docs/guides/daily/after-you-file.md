# After you file

When you are done your feature request will have become real work you accepted, or your bug will be confirmed and on its way to a fix. Both need a few minutes of you along the way, and this page shows where.

## A feature request: where it goes, interview, proposal, your call

A feature request lives only in Fleet until you accept what it becomes. Nothing is created in your tracker before that.

1. [fleet] **The intake interview reads it.** An agent reads your sentence, the features your product already has and what it already promised on that ground. This is the intake interview.
2. [you] **Say where it goes.** In a repository with features, its first question is always **Where does this go?** The best fit comes first, marked and already picked, then the others. See the next section.
3. [you] **Answer the rest of its questions.** It asks only what it still cannot work out, inside the feature you picked.
   They appear on the request's page and in the [Cockpit](guides/daily/cockpit). See [Answer a question](guides/daily/answer-a-question).
4. [fleet] **It writes the request up.** The request's page shows what was established: the ask in your words, who it is for, what is already promised nearby, and how you would know it worked.
5. [fleet] **It proposes what the request becomes.** The interview routes itself: it works out what kind of work this is and where it belongs. That is the route proposal. Nothing is created yet.
6. [you] **Make the call.** The card asks **Waiting on you: create this?** and shows what Fleet proposes. See below.
7. [fleet] **It is created.** The work is filed where the proposal said, and the request's page links to it.

### Where does this go?

Each answer says why it fits, and **See this feature** opens the feature it names. The send button says what your pick will do.

| You pick | What happens |
|---|---|
| **Adds to** a feature **→** one of its uses | Fleet shapes your request inside that use and proposes the work for it. |
| **A new thing** a feature **does** | Fleet drafts it as a new use of that feature for you to check and add, ready to plan. |
| **A new feature** | Fleet drafts the new feature's brief and uses for you to check, and your request becomes one of its uses. |
| **Not a feature** | It is a bug or a small change: it is handed back to file as a bug, or created as a task. |

None of them fits? Write where it goes instead. In a repository with no features yet there is no such question, and the interview goes straight on.

### The three moves on a routed request

- **Create it** accepts the proposal. The request becomes the work it proposed, filed under your name. A task or a bug it becomes is filed under the feature the proposal names, so you do not link it afterwards. For a new feature the card asks **create this feature?**, and for a plan **start this plan?** When accepting also starts the work, the button reads **Create it and start**.
- **Send back to the interview…** asks for one note on what to change. The interview runs again with that note as its answer and proposes again.
- **Park…** sets the request down until a date, the same way as [snoozing an item](guides/daily/cockpit).

**Withdraw** ends a request you no longer want.

> **Careful:** When the proposal cannot be created as proposed, **Create it** is disabled and the card says why. Send it back with a note so it proposes again. Only the case where the run never confirmed its own proposal offers **Create it anyway**. A proposal that falls outside the product's vision also offers **Create it anyway**: adding something the product never promised is a person's call to make.

### When the interview hands it back

Sometimes the interview decides your filing is not a feature request to shape:

- **"Not a feature request — this looks like a bug."** **File it as a bug** opens the bug dialog with your words in it, and withdraws the request. The bug keeps the feature the request was filed under.
- **"Not a feature request — the fleet says this is a task."** **Create it** files your words as a task.
- **Handed back for another reason.** The card gives the reason. Nothing runs until you send it back with a note, or withdraw it.

## A bug: reproduce, then confirm

A bug's page shows where it stands: **Filed › Reproducing › Confirm › Fixing › Verified**.

1. [fleet] **An agent tries to reproduce it.** This is the reproduce stage. When it can, it writes a test that fails because of the bug, and pushes it.
2. [you] **Confirm it.** The card asks **The fleet reproduced this. Is this your bug?** and names the failing test and the suspected cause. Pick a priority and a component if offered, then press **Yes, fix it**.
3. [fleet] **It goes to be fixed.** With a pushed failing test it goes straight to the fleet to fix, skipping triage; the test is the proof. Without one, it is triaged first.

If the reproduction is wrong, press **That's not it**. It asks for one line, then reproduces again.

If the agent **could not reproduce** the bug, the card says what was tried and what would settle it. **Add evidence and run again** reproduces again with what you add. **File it anyway** sends it to triage without a failing test.

> **Tip:** Ticked **If it reproduces, fix it without asking me** when you filed? Then a confirmed reproduction goes to a fix without this step.

## A task

A task skips both: it is created at once and goes to the check, which gives it a priority and a place. Its page follows it from there.

Next: Answer a question (guides/daily/answer-a-question) · Find anything (guides/daily/find-anything) · Why a second session verifies every change (concepts/verify-before-merge)

---
- **intake interview**: The agent that reads a new feature request against what the product already promised, asks where it goes, and asks its filer what it cannot work out.
- **route proposal**: The route step's answer to what kind of work a filing is and where it belongs, which a person accepts or sends back.
- **reproduce stage**: The step after a bug is filed where an agent tries to make it happen and writes a test that fails because of it.

# Build the knowledge for code you already have

Fleet's agents plan new work against a written description of your product, and the Quality desk checks the product against it. A repository that already has code starts without one. The knowledge bootstrap writes it with you: an agent reads the code and drafts, and you confirm what the product promises. You start with one part of the product and add the next part when you are ready.

When you are done with the first part, that part is described end to end: its components, what it can do, the rules it keeps, the feature area it belongs to and the journeys people take through it. Fleet's agents can plan new work against it, and the Quality desk can check its promises.

## The one idea

> **Why:** Only you can say what it promises. The code shows what the product *does*. The agent finds a rule in the code, for example "an order of more than 500 parts needs a second approver", and cannot tell whether that rule is intended, an accident or a bug. So nothing becomes a promise the Quality desk defends until you have kept it in a review.

A rule written down by mistake is worse than no rule: the Quality desk would defend the bug every time it checks. That is why the agent drafts and you confirm, in batches.

## What you will have at the end

Seven kinds of knowledge, each one explained on the **Knowledge** page: what it is, how to tell it apart from its neighbours, and an example. That page also shows what is added later, as work happens: decisions, PRDs, check results and more.

| What it answers | Kind | What it holds |
|---|---|---|
| Who it is for | Product and personas | What the product is, who uses it, and the job each person comes to do. |
| What we build | [Components](knowledge-base/capabilities-and-components) | The parts of the system, and which code each one owns. |
| What someone can do | [Capabilities](knowledge-base/capabilities-and-components) | One row per thing the product can do, with the code and test behind it. |
| The rules | [Requirements](knowledge-base/promises) | What the system always or never does. You keep or drop each one. |
| How it is grouped | [Feature areas](knowledge-base/feature-areas) | Capabilities grouped the way a customer would name them. |
| Whole jobs | [Journeys](knowledge-base/journeys) | How one kind of user gets a real job done, with criteria anyone can check. |
| Where it is checked | Test environment | Where the [Quality desk](guides/quality/quality-desk) may test the promises, and the build commands agents use. |

[Open Knowledge](#knowledge)

## Before you start

The repository needs Fleet's commands and its planning record. If it has neither, [start a knowledge base](guides/knowledge/start-a-knowledge-base) first. The bootstrap command ships with the core commands.

## What you type

You run one command in a terminal session in the repository. Each time, it does the next step, stops, and tells you in three lines what it did, what it is waiting on, and what the next run will do. So you can spread the work over days.

`knowledge:bootstrap` — Describe an existing code base into the knowledge corpus one resumable step at a time — survey, components, per-component capabilities and rules, feature areas, journeys — drafting from the code and confirming every promise with a person in batches, so new work builds on it and the QA Desk checks it out of the box.

| Add after the command | When |
|---|---|
| `start ordering` | The first time. Describe only "ordering" for now. |
| nothing | Every time after that. Does the next step. |
| `add approvals` | When you want the next part described. |
| `status` | To see where it stands. Changes nothing. |

## The steps, in order

### Once: get to know the repository

Steps 1 and 2 run once for the whole repository.

1. [fleet] **1 · Survey.** Runs alone, then asks you once. It lists every page, API route, table and command-line tool, and works out how the repository is built and tested.

   **It does:** reads your CI to find the real lint, test, build and generate commands, runs each once, and records them. It drafts a one-paragraph product statement and the kinds of users it sees evidence of: login roles, permissions, separate apps.

   **Asks you:** is the product statement right? Who uses the product, and what job does each kind of user come to do?

   **Produces:** the product statement and personas, and the repository's answers to the questions Fleet's commands ask.
2. [you] **2 · Components.** A gate. Runs alone, then it is your call where to start. It splits the whole code base into components and gives every code file an owner.

   **It does:** proposes layers and components from package boundaries, imports, tables and route groups. A page in the web app goes to the component it serves, not to "the web app".

   **Asks you:** which part to start with. It asks about a boundary only where it touches that part; the rest wait until you get to those parts.

   **Gate:** it goes on only when nearly every code file has an owner, and every file without one is listed with a reason.

### Each part: describe one part, all the way

Steps 3 to 7 run for one part at a time, and your first part goes all the way to step 7 before the second part starts.

1. [fleet] **3 · Draft.** Runs alone. It reads the part's code, tests, pages and database tables, and drafts what it can do and the rules it enforces.

   **It does:** writes capability rows, for example *"Order approval by a second reviewer"*, each with the file and line that implements it and the test that proves it. It writes rules, for example *"An order of more than 500 parts is refused until a second person approves it"*, each marked **tested**, **enforced** or only **observed**. Anything that looks like a bug is listed separately and never written down as a rule.

   **Gate:** every route and page this part owns is described, or listed with a reason why not.

   **Produces:** a draft. Nothing is final yet. The draft comes from the code alone, and tests count as the strongest evidence, because a test shows someone meant the behaviour.
2. [you] **4 · Your review.** A gate, and your call. One review per part. You mark each rule keep, drop or edit, and whatever you keep gets a permanent id.

   **You see:** rules grouped by how well they are backed. The "observed only" ones are flagged: keep them only if you would call a change there a bug. Capabilities with plain evidence are listed as "keeping these unless you object".

   **Suspected bugs:** each one becomes a filed bug, or a rule after all if you say it is intended.

   **Produces:** capabilities and requirements.
3. [you] **5 · Feature areas.** Asks you. It groups the new capabilities into features a customer would recognise, such as "Ordering" or "Approvals", and writes each one's brief and its uses with the capabilities under each. See [Features, uses and capabilities](knowledge-base/feature-areas).

   **Asks you:** the features, the uses of each and which capabilities go under which use, in one question. A capability that fits no use waits under `### Misfits (to move)` until you say where it goes. For a later part, new capabilities go into the areas you already have first; you are asked about a new area only when nothing fits.
4. [you] **6 · Journeys.** Asks you. For each kind of user, the whole jobs they come to do, written from the real screens, with numbered criteria anyone can check.

   **For example:** *"A buyer orders a part that needs approval"*, criterion 3: *"The buyer sees 'Waiting for approval' and the order cannot be shipped."*

   **Asks you:** which journeys are real, and keep, drop or edit for each criterion.
5. [you] **7 · Ready for the Quality desk.** A gate. Asks you. It checks that the part is fully described, counts the promises the Quality desk can now check, and asks where it may test them.

   **It does:** from now on, a new file in this part that no feature area claims fails the build, so the description cannot quietly fall behind the code.

   **Asks you:** which environment the Quality desk may run against, and whether it may write there. It recommends a test environment, never production.

Then the next part: steps 3 to 7 again. Areas and journeys are extended, never redrawn.

## Describe a part from the Knowledge page

You do not have to use a terminal. Each part in the readiness table on the **Knowledge** page has a **Describe** button, and anyone signed in can press it. A background run does the same work as steps 3 to 7 for that one part.

- **One run describes one part and lands one pull request.** The run reads every file the part owns, in batches, and does not write anything until every file has been read. If it cannot finish reading, it stops where it got to and says how many files are unread; it never writes up a part it only partly read.
- **It asks you in writing, at most two rounds.** The questions appear on the part's row and in the Cockpit under "Waits on me". Answer in either place and the run carries on from your answer.
- **It merges its own pull request.** The pull request holds only knowledge files. When it merges, the part counts as described.
- **One part at a time.** While another part's pull request is open, a new run is refused with "base not current": the next part starts from the merged result of the last.
- **Stop** ends the run at the next beat, and a run that ran out of time stops and waits for you; it is not counted as a failure.
- **Continue picks up where it stopped.** After a Stop, a time-out or a failure the part offers **Continue**. It starts a new run that reads only the files the earlier run had not read, and never re-reads one it recorded. If the part's files changed in between, it reads the whole part again rather than guess. **Describe** after a Stop still starts from nothing.
- **Each part's row says where it stands:** not being described, running (step 1 to 5), waiting on your answers, pull request open, failed, or stopped. The readiness counts include a part only once its pull request has merged.

### What the row shows and what you can do in it

The box at the top only says whether the knowledge base is ready to build on, and which part Fleet suggests next. It has no button: every action is on a part's own row.

| The row says | What you can do |
|---|---|
| Not described, or Partly described | **Describe** starts a run for that part. |
| Describing, step 2 of 5 | Unfold the row to see the five steps (Survey, Read files, Draft, Check with you, Write and open PR), and **Stop**. |
| Waiting on you, N questions | **Answer N questions** unfolds the row. Each question lists its options with the recommended one marked and the reason for each, and a free-text box. **Can't answer, carry on** skips one; **Send answers** is enabled once every question is answered or skipped. |
| PR open | **Open PR** opens the pull request on your git host. It counts toward readiness once it is merged. |
| Failed, Stopped, or Paused | **Retry** or **Continue** picks up from the files already read. |

A row folds and unfolds with its arrow or its name, and **Fold all / Unfold all** move every row. A row that starts waiting on you unfolds once; after that your choice stays, and a refresh never moves it. The table shows the seven parts with the most recent change; **show all** lists the rest. The page follows the runs by itself, and a refresh never takes an answer you are typing.

## When nobody is at the keyboard

If you run it where nobody can answer, or you say "later", it writes its questions into its progress file, saves what it has, and stops. It never answers a question for you. The next run reads your answers from the file and carries on.

Each step is committed with that progress file. With a remote it opens a pull request per step, so each review is small enough to read.

## When the code changes later

Each run first checks whether a described part's code has changed. If it has, the agent re-reads only what changed and shows it to you as a small review. If new code contradicts a rule you kept, it asks you: keep the rule and file the change as a bug, or replace the rule. It never edits a promise on its own.

## What it never does

- Decide on your behalf.
- Describe the whole repository in one go.
- Plan new work. It writes no programs, slices or PRDs; once your knowledge exists, you plan on top of it.

Next: Answer the questions the commands ask about your repository (guides/knowledge/fill-slots) · Keep your feature maps true to the code (guides/knowledge/keep-maps-current) · Read the Quality desk (guides/quality/quality-desk)

---
- **promise**: Anything the product committed to that a check can prove: a requirement, a shipped capability or a journey's acceptance criterion.
- **component**: A part of the product you can point at in the code, such as a directory, a service or a set of tables; it is built and never finishes.
- **capability**: One concrete thing the product lets a person do, small enough to check at any time and still true tomorrow; it sits under one use of a feature, is shipped by a PRD, and never finishes.
- **requirement**: One sentence the system must always, or must never, do, kept with a permanent id in a register.
- **journey**: How one kind of person gets a whole job done in the product, written from the real reason they open it.

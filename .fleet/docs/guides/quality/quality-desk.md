# Read the Quality desk

When you are done you will know, for the repository you are looking at, which promises are proven right now, which are failing or out of date, and what the QA agent will check tonight.

## What the desk shows

Open **Knowledge** in the sidebar and, under **What the Quality desk checks**, press **Open the Quality desk →**. The desk has three tabs: **Promises**, **Scenarios** and **Environments**.

A promise is one thing your product has committed to that a check can prove: a rule in a requirement register, a shipped capability, or a journey's acceptance criterion. A promise is green only when a check passed it against the live product, with evidence, inside its window, and the verifier did not dispute it. Anything less has its own state, so a gap never reads as green.

On the Quality page (#quality):
1. One line per feature area, with its promises counted in words.
2. A newer result waiting in an open pull request, under its promise.
3. Ask the QA agent to cover a promise nothing checks yet.

[Open the Quality desk](#quality)

## Read it, top to bottom

1. [you] **Read the head lines.** **Release** says which release production runs and how many promises got worse, got fixed, or are not yet checked on it. **Checked** counts every promise and splits the checked ones by state. **Tonight** says how many checks are left under tonight's limit and what the QA agent plans to run. Press **more** for the trend, the outcomes and the plan row by row.
2. [you] **Read the features.** The list opens on **Features, worst first in each tier**: one line per feature, worst first within its tier, saying in words how many of its promises are failing, not checked yet and passing. A promise in no feature sits last under **Not in a feature**. Open a line to see that feature's promises; **what the words mean** explains every state once.
3. [you] **Narrow it.** Press **Filter** and pick a **Feature**, a **State** (**Failing**, **Flaky**, **Disputed**, **Out of date**, …), a **Register** or a **Release**, or type in **Search id or words**.
4. [you] **Open a row.** The row unfolds into why it is in that state, the releases it passed or failed on, the commit and environment of the result that decided it, and the evidence: what was expected, what was observed, and the platform's own request and audit ids. A newer result waiting in an open pull request shows as a **waiting** line under its promise, with a link to the pull request; it never changes the promise's state or the counts.
5. [fleet] **Fleet keeps it current.** The QA agent runs its checks on its nightly plan and writes each result into the repository. The desk reads the results; nobody marks a promise by hand.

## What each state means

| State | What it means |
|---|---|
| passing | a live check passed it, with evidence, inside its window |
| failing | a check proves it failed |
| flaky | one check gave different verdicts on the same release |
| disputed | the verifier disagreed with the check's verdict |
| unfinished | it ran and passed with evidence, but cannot count yet |
| out of date | no live pass inside its window |
| can’t run | the check was blocked where it was sent |
| quarantined | counts nowhere and files no findings |
| not checked yet | nothing proves it |

A failing row also names its cause: **product**, **agent couldn’t run it**, **environment** or **inconclusive**, and the ticket it filed when there is one.

> **Why:** A result that ran only against the code, or did not finish, is never shown as green. The desk would rather say "out of date" or "unfinished" than let an old or partial check stand for a live one.

## The other two tabs

**Scenarios** lists the checks the QA agent wrote and runs. A scenario walks several parts of the product together, and each expected result in it proves one promise. Each row shows the scenario's state, the environment it runs in, the verifier's word on it, its last five runs and when it last ran. A scenario marked **weak** let a planted bug through, so its passes prove less than they look.

**Environments** lists where those checks run, and how many are marked production. Open one and the desk proves its safety instead of asserting it: the latest result of the repository's cross-tenant write check, and each login's scope and expiry. The same unfold carries **Pause all runs** — one press stops every run the QA agent would start there, and **Resume runs** lifts it. An environment that cannot run a check makes that check read **can’t run**, never green. Credentials show only as the names of their secret-store references.

> **Tip:** If the Tonight line says **QA is off for this repository**, the repository's `fleet.toml` declares no `[fleet.recurring] qa` table, so the QA agent does not run on its own. See [Recurring work](guides/team/recurring-work).

Next: Ask the QA agent to check a promise (guides/quality/ask-for-a-check) · Read a verify verdict (guides/quality/verdicts) · How Fleet knows what has been checked (concepts/quality)

---
- **promise**: Anything the product committed to that a check can prove: a requirement, a shipped capability or a journey's acceptance criterion.
- **verifier**: A fresh session that never wrote the work and checks it from the evidence before it counts, such as a fix before it merges.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.
- **scenario**: A check the QA agent writes that walks several parts of the product together, each expected result proving one promise.

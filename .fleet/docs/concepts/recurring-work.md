# Recurring work

Some work comes back on a schedule: a nightly audit, a weekly review. In Fleet you write that schedule once, in your repository. Fleet files each piece of work when it falls due, once, and nobody has to remember to.

## Two halves, two owners

| | The schedule | The nightly limit |
|---|---|---|
| Says | **What** recurs, and how often | **How much** of it may land in one night |
| Lives in | Your repository's `fleet.toml` | **System › Recurring work** |
| Changed by | A reviewed pull request | An operator, on the page |
| Applies to | Each entry | Every entry together |

The schedule is a `[fleet.recurring]` table. Each entry names the work, its kind and its cadence, and may name a target:

```toml
[fleet.recurring]
entries = [
  { name = "nightly-audit", kind = "audit", cadence = "daily" },
  { name = "weekly-feature", kind = "prd", cadence = "weekly:mon", target = "frontend" },
]
```

The kinds and cadences an entry may use are listed in the fleet.toml reference. A cron expression is refused. A mistyped entry is caught by a knowledge check when the change is reviewed, and the entries around it still file.

## What Fleet does with it

1. [fleet] **Reads the schedule.** Fleet reads `fleet.toml` at your repository's current commit, so a cadence change takes effect once it merges.
2. [fleet] **Files the due work once.** An entry that falls due files one issue for its window. Two servers, a restart or a retry never file it twice.
3. [fleet] **Keeps to the nightly limit.** Anything over the limit is shown as waiting and filed the next night, oldest first.
4. [you] **Sets the limit.** Until an operator sets one, Fleet files no recurring work at all.

From there, a filed issue moves like any other: it goes to the triage check, then to the fleet.

## Where you'll see it

**System › Recurring work** shows the limit and the schedule. Each entry has its cadence, when it last ran, when it is next due, and a state: **on schedule**, **waiting** (the nightly limit was reached) or **missed** (a window passed with nothing filed).

[Open System](#system)

> **Tip:** The schedule has no button on the page on purpose. Adding or changing an entry is a reviewed merge to `fleet.toml`.

Next: Schedule recurring work (guides/team/recurring-work) · Recurring work did not run (troubleshooting/recurring-missed)

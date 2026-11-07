---
title: "Schedule recurring work"
kind: guide
for: [admin, owner]
summary: "Write a schedule in your repository's fleet.toml, set the nightly limit on System › Recurring work, and read what is due, waiting or missed."
routes: [system:recurring]
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/checks/recurring/__init__.py
  - packages/fleet-service/src/fleet_service/dispatch/recurring.py
  - packages/fleet-service/src/fleet_service/api/recurring.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
minutes: 5
---

:::lede
When you finish this guide, Fleet files work that recurs, such as a nightly audit, without anyone filing it by hand. Each due window gets exactly one issue, within a nightly limit you set.
:::

## Two halves, two places

Recurring work is set in two places, on purpose:

- **What recurs** lives in your repository, in `.fleet/fleet.toml`. A change to it is reviewed and merged like any other change.
- **How much may land in one night** is set on **System › Recurring work**, and only there.

Until a nightly limit is set, Fleet files no recurring work at all. There is no default.

## Set it up

A schedule with two entries looks like this:

```toml
[fleet.recurring]
entries = [
  { name = "nightly-audit", kind = "audit", cadence = "daily" },
  { name = "weekly-feature", kind = "prd", cadence = "weekly:mon", target = "frontend" },
]
```

:::steps
- [you] **Write the schedule.** Add a `[fleet.recurring]` table with one entry per piece of recurring work, like the example above, and open a pull request.
- [fleet] **The merge checks it.** Fleet's `recurring` check reads the entries the same way the scheduler will, so a mistyped cadence is caught in review rather than on a silent wrong night.
- [you] **Merge it.** Once it is on the branch Fleet reads, the entries appear on System › Recurring work.
- [you] **Set the nightly limit.** Under **Issues Fleet may file each night**, type a number and click **Save**. The new limit applies from the next check.
- [fleet] **Fleet files what is due.** For each entry whose window has come, Fleet files one tracker issue. It lands in triage, where the check sorts it like any other filed work.
:::

Each entry needs a `name`, a `kind` and a `cadence`. It may also carry a `target`, a free-form pointer such as an area, a component or a repository. A cadence is a plain word, not a cron expression; the kinds and cadence words Fleet accepts are listed in the fleet.toml reference. One bad entry is reported and skipped, and the others still file.

Every issue the schedule files goes through the same gate as work a person files:

::command{name="check"}

## Read the schedule

On **System › Recurring work**, the **Schedule** table has one row per entry: **Entry**, **Cadence**, **Last ran**, **Next due** and **State**. The state is one of three:

- **on schedule**: nothing is owed.
- **waiting**: the window came, but the nightly limit was reached. Waiting work files on the next night, oldest first, before anything newly due.
- **missed**: the window passed with nothing filed, for example while Fleet was not running. A missed window is never filed later.

::action[Open Recurring work]{route="system:recurring"}

:::callout{kind="why"}
The limit is yours to set because only you know how much recurring work your team can absorb next to feature work. Fleet will not guess that number for you.
:::

The System page's **Recurring work** card shows the same reading in one line, for example how many entries are waiting.

::cards{links="concepts/recurring-work, troubleshooting/recurring-missed"}

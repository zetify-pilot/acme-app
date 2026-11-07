---
title: "Fix a problem"
kind: job
icon: fix
group: run
for: [everyone]
summary: "Something is stuck, failed or not merging. Find out why, and do the one thing that moves it."
minutes: 3
---

:::lede
Start from what you see. Something that is not moving is almost always waiting for something specific, and Fleet says what. Each page here starts from a symptom, shows where Fleet names the cause, and says what to do about it.
:::

## The big picture

:::ideas
- **Held back.** The Queue view of everything that is not running and not ranked next. Each row says what it waits for.
- **Failed.** Where an issue stops after its runs kept failing. It waits for a person to fix the cause and press **Reset & retry**.
- **System.** The page that checks each part of the fleet, such as dispatch, machines and your tracker, and marks it **OK**, **ATTENTION**, **PROBLEM** or **NOT SET UP**.
- **Drain.** A machine that finishes what it holds and takes nothing new, because someone asked or because it kept failing.
:::

Work out how wide the problem is, then look in the right place. One issue sitting still: read the reason on the issue itself. It waits on a person, on another issue, on a date, or on its attempts. One run that ended badly: the reason on the run's page says whether the problem is the work or the machine. Nothing starting anywhere: open **System** and begin with the parts marked **PROBLEM**.

Fleet notices most stalled pull requests on its own and sends the issue back to an agent with the reason. It hands you only the cases a person must settle. If no page here explains what you see, download a diagnostics file from **System** and send it to Fleet's team.

## Read these in order

::path{links="troubleshooting/why-is-this-stuck,troubleshooting/pr-not-merging,troubleshooting/run-failed,troubleshooting/fleet-paused"}

## When you need it

::pages{links="troubleshooting/machine-drained,troubleshooting/recurring-missed,troubleshooting/session-problems,troubleshooting/send-diagnostics"}

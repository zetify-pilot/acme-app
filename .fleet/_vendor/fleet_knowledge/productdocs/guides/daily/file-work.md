---
title: "File a feature request, a bug or a task"
kind: guide
for: [everyone]
summary: "Hand the fleet something new in plain words: a feature request to place and shape, a bug to reproduce, or a task to build."
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/static/app.html
  - packages/fleet-service/src/fleet_service/api/filings.py
  - packages/fleet-service/src/fleet_service/api/bugs.py
  - packages/fleet-service/src/fleet_service/api/tasks.py
  - knowledge/features/fleet-filings.md
minutes: 5
---

:::lede
When you are done you will have a :term[filing] with its own key, and the fleet will already be working on it: asking where a feature request goes, reproducing a bug, or checking a task.
:::

## Pick the kind

There are three kinds, and the one fact you need to know is which you have.

:::compare
| | Feature request | Bug | Task |
|---|---|---|---|
| Use it for | Something the product should let people do and does not yet | Something that is broken | Small, clear work you can describe now |
| What happens next | Fleet asks where it goes, interviews you, then proposes what it becomes | An agent tries to reproduce it | It is created at once and checked |
| You write | A title and a sentence | What happened, where, and any evidence | What and why |
:::

You never choose a kind of work, a component or a priority. The fleet works those out, and asks you if it needs to.

## Open the filing dialog

The foot of the sidebar has three buttons on every page: **Feature request**, **Report a bug** and **File a task**. On a phone, the **+** in the top bar opens the same dialog. The switch at the top of the dialog, **Feature request**, **Bug** and **Task**, changes the kind and keeps what you typed in each.

To add a whole new feature, or something one feature should do, start from the **Features** page instead: see [Add a feature and plan its work](guides/plan/add-and-plan-a-feature).

## File a feature request

:::steps
- [you] **Say what should exist, or what happened.** Write it in **What should exist, or what happened**, in plain words.
- [you] **Give it a title, or leave it blank.** A blank **Title** is made from your sentence.
- [you] **Say if it blocks you.** Tick **This is blocking me right now** when it does.
- [you] **Pick the repository.** The dialog offers it only when Fleet has more than one, and starts on the one you are looking at.
- [you] **Press File it.** You land on the request's own page.
- [fleet] **Fleet asks where it goes.** In a repository with features, the first question is **Where does this go?**: inside one of a feature's uses, as a new thing a feature does, as a new feature, or not a feature at all. Then it asks what else it needs, on the request and in the Cockpit. See [After you file](guides/daily/after-you-file).
:::

## Report a bug

:::steps
- [you] **Say what happened.** In **What happened**: what you did, what you expected, and what happened instead.
- [you] **Say where.** **Where** takes a URL, a page name or an issue key.
- [you] **Attach evidence.** Drop files, paste a screenshot, or choose a file. On a phone, **Camera** and **Photos** add a picture. **Paste console output or a log excerpt** opens a box for text.
- [you] **Choose whether to be asked.** With **If it reproduces, fix it without asking me** ticked, a confirmed bug goes straight to a fix. Leave it off and Fleet asks you first.
- [you] **Press File it.** You land on the bug's page.
- [fleet] **An agent tries to reproduce it.** It writes a failing test when it can.
:::

:::callout{kind="tip"}
**Report a bug** from the sidebar is about Fleet itself. It attaches a screenshot of the page you were on, the browser log, and the page, browser and Fleet version, under **Attached automatically**. When your team sends bug reports to its Fleet provider, the dialog says so.
:::

## File a task

:::steps
- [you] **Say what and why.** In **What and why**: what should exist, and why it is worth doing. No priority, no placement.
- [you] **Add a title and attachments if you have them.** Both are optional.
- [you] **Press File it.** You land on the task's page.
- [fleet] **The issue is created at once.** It goes to the check, which gives it a priority and a place, and only then can it be built.
:::

:::callout{kind="careful"}
If a send fails, the dialog stays open with your text in it, and the reason is shown under the field it concerns. Nothing is lost.
:::

::cards{links="guides/daily/after-you-file, guides/daily/find-anything, concepts/who-decides-what"}

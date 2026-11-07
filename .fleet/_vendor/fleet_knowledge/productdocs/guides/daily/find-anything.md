---
title: "Find anything"
kind: guide
for: [everyone]
summary: "Find a filing, an issue, a planning document or a page by its key or its words, and jump anywhere with the palette."
routes: [ideas, bugs]
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/static/team-items.js
  - packages/fleet-service/src/fleet_service/api/static/cockpit-palette.js
  - packages/fleet-service/src/fleet_service/api/filings.py
  - packages/fleet-knowledge/src/fleet_knowledge/templates/board.js
  - knowledge/features/fleet-filings.md
minutes: 4
---

:::lede
When you are done you will know the one place to look for each kind of thing in Fleet, and the keyboard shortcut that gets you to any page from anywhere.
:::

## Which search to use

| You are looking for | Search here |
|---|---|
| Something filed: a feature request, bug or task, or a customer's report | **Cockpit**, with the **Waiting on** chip removed |
| An issue the fleet works on, by key or title | **Queue** |
| A :term[program], :term[slice], :term[PRD] or any document in the knowledge base | **Knowledge** |
| A session, a machine or a page | The palette, :kbd[⌘K] |

## The Cockpit: everything that was filed

The [Cockpit](guides/daily/cockpit) is one list of every feature request, bug and task, and every report from your product, history included. It opens on what waits on you (the chip **Waiting on** is **Me**); remove that chip to search everything.

:::steps
- [you] **Search.** The box takes words from a title, a Fleet id such as a bug's key, or a product report id.
- [you] **Narrow it.** **Filter** adds a chip per choice: **Waiting on**, **State** (**Intake** through **Shipped**, **Closed** and **Cancelled**), **Filed by** (**Me** for what you filed), **Assignee**, **Kind**, **Customer**, **Came from** (**The product**, **By hand**, **My agents**, **CI**), **Filed** and **Changed** (**Last 24 hours**, **Last 7 days**, **Last 30 days**). Each choice shows how many it would hold.
- [you] **Keep it.** **Save view** keeps the filters under a name. **Views** opens it later, and the filter **Filed by: Me** shows what you filed.
:::

## Queue: the fleet's issues

On the **Queue** page, **Search the queue** takes an issue's key or words from its title. See [Read the Queue](guides/daily/the-queue).

## Knowledge: the plan and its documents

On the **Knowledge** page, **Search this corpus, or an id** searches every kind of planning document at once when you press :kbd[Enter]. Typing an id in full, such as `SL-12`, opens it.

## The palette: jump anywhere

Press :kbd[⌘K] (:kbd[Ctrl K] off a Mac) on any page. Type to filter, move with :kbd[↑] :kbd[↓], and press :kbd[Enter].

- **Sessions** jumps to one of your open sessions.
- **Actions** has **Open a new session**.
- **Box shell** opens a shell on a machine.
- **Go to** lists every page in the sidebar.

:::callout{kind="tip"}
Off a Mac, inside a terminal pane, :kbd[Ctrl K] stays the terminal's own key. Click outside the pane first. Press :kbd[?] for the list of keyboard shortcuts.
:::

::action[Open the Cockpit]{route="cockpit"}

::cards{links="guides/daily/the-queue, guides/daily/file-work, guides/plan/read-the-board"}

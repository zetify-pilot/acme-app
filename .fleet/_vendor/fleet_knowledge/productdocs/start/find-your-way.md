---
title: "Find your way around the app"
kind: start
for: [everyone]
summary: "A tour of the sidebar: the daily pages at the top, then Fleet, Docs, Settings and System."
routes: [settings]
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.html
  - packages/fleet-service/src/fleet_service/api/static/app.js
minutes: 5
---

:::lede
The sidebar puts the pages you open every day at the top, with no heading over them. Below them sit the pages that show what your knowledge base says right now, then Docs, which explains how Fleet works, and Settings and System at the foot.
:::

## Daily

The first group has no label. These are the pages most people open every day, in the order they reach for them.

| Page | What it is for |
|---|---|
| **Cockpit** | Everything that waits on you: questions, calls, customer items, jobs only a person can do, and repairs. Its badge counts that list. Beside **Waiting**, **All items** lists everything filed, and **Views** holds saved lists such as **Unassigned**. A view you star appears in the sidebar under Cockpit. It is also where the app opens on a phone. |
| **Features** | Each :term[feature] of your product: what it is, what people do with it, how far it has got, and what waits on you. You add a feature and plan its work here. |
| **Terminals** | The agent sessions and terminals you are working in. |
| **Queue** | What the fleet will pick up next, what is held back, and what is running. |

A program's page has no sidebar entry. It opens from the features it touches and from the items that belong to it.

## Fleet

What your knowledge base holds and how the fleet has done.

| Page | What it is for |
|---|---|
| **Stats** | How runs have gone over a window you choose. |
| **Knowledge** | Your knowledge base itself, read at the commit Fleet last synced: every capability, requirement, decision and component, and what each kind of file is. |
| **Architecture** | Your component registry, drawn as a diagram. |

The **Runs** page, which lists every :term[run] (one attempt at one issue on one machine, and how it ended), opens from the links on an issue and on the System page.

## Docs

One entry, with no heading over it: these pages. The Docs home starts from what you want to do, and the search box at the top of every docs page (press :kbd[/]) finds any page.

Two pages explain an order rather than a screen: [The Work Line](concepts/the-work-line) (what happens to a piece of work, in what order, and who has to be there for each step) and [Build the knowledge for code you already have](guides/knowledge/describe-existing-code) (the order a knowledge base gets written in, before any work is planned against it).

## Settings and System

Pinned at the foot of the sidebar, because neither is a daily page.

**System** shows what the control plane sees right now: dispatch, machines, tracker reads and writes, background jobs, safety limits and recurring work.

**Settings** has its own menu in four groups.

| Group | Panes |
|---|---|
| Access | **Set up**, **Secrets**, **Shared MCP servers**, **API keys**, **Connect your tools**, **Send reports** |
| You | **My secrets**, **My MCP config** |
| Estate | **Repositories**, **Model config**, **Agents**, **Machines** |
| Work | **Labels** |

**Send reports** appears only where the install offers it.

::action[Open Settings]{route="settings"}

## On every page

Three quiet buttons sit at the foot of the sidebar: **Feature request**, **Report a bug** and **File a task**. Each one opens a short form in plain words. Beside them, **Theme** switches the colours.

:::callout{kind="tip"}
On a phone the sidebar becomes a tab bar with **Cockpit**, **Programs**, **Terminals**, **Queue** and **More**. The **+** in the top bar opens the same form as **Feature request**, with a switch for a bug or a task.
:::

::cards{links="guides/daily/cockpit, guides/daily/the-queue, concepts/how-work-moves"}

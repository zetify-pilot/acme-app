---
title: "Arrange your sessions and use the keyboard"
kind: guide
for: [developer]
summary: "Switch the Terminals page between Grid, Focus, List and Board, jump anywhere with ⌘K, and find every shortcut behind ?."
sources:
  - packages/fleet-service/src/fleet_service/api/static/cockpit-palette.js
  - packages/fleet-service/src/fleet_service/api/static/app.js
minutes: 3
---

:::lede
When you are done you will have the Terminals page laid out the way you work, and you will reach any session, machine shell or page without the mouse.
:::

## Four layouts

The **Layout** switch sits in the bar at the top of the Terminals page. Your choice is remembered in this browser.

| Layout | What it shows |
|---|---|
| **Grid** | Every open session as a tile. Drag a tile's header to move it, its corner to resize it. |
| **Focus** | One session large, with the :term[dock] beside it. |
| **List** | Every session in a list, and the one you pick beside it, using the width. |
| **Board** | Every session as a card, in columns by what it is doing: **Working**, **Needs you**, **Idle**. |

::screen{route="terminals" pins="layouts,tile,dock"}
1. The **Layout** switch.
2. A tile. In Grid, drag its header to move it and its corner to resize it.
3. The dock, beside the focused session in Focus.

Sessions keep the order they were opened in; dragging a tile only changes where you see it. To undo your arrangement, use **Reset tile sizes and order** in the palette.

A session that has ended leaves the board. Find it in the **Closed** list (see [Take a session over, or bring one back](guides/sessions/take-over-and-restore)) or on the Workstation page.

## The palette

Press :kbd[⌘K] (:kbd[Ctrl K] off a Mac), or click *Jump to session, open a box shell…* in the bar. Type a few letters of what you want. The palette lists:

- **Sessions**, in the order the grid shows them.
- **Open a new session**.
- **Open a shell on** each machine.
- **Go to** any page in the sidebar.
- **Layout:** each of the four layouts, and in Grid, the focused tile's **wider**, **narrower**, **taller** and **shorter**.
- **Keyboard shortcuts**.

Use the arrow keys and :kbd[Enter], or :kbd[Esc] to close it.

## The shortcuts

Press :kbd[?] (outside a text field) or the **?** button in the bar for the full sheet.

| Keys on a Mac | Off a Mac | What it does |
|---|---|---|
| :kbd[⌘K] | :kbd[Ctrl K] | Open the command palette |
| :kbd[⌘1] to :kbd[⌘9] | :kbd[Ctrl 1] to :kbd[Ctrl 9] | Focus session 1 to 9, in the order the grid shows them |
| :kbd[⌘⇧S] | :kbd[Ctrl Shift S] | Open a shell on the focused session's machine |
| :kbd[⌘B] | :kbd[Ctrl B] | Hide or show the session list |
| :kbd[⌘.] | :kbd[Ctrl .] | Hide or show the dock, in Focus and full screen |
| :kbd[?] | :kbd[?] | The shortcut sheet |

:::callout{kind="careful"}
Shortcuts never fire while you type in a field. Off a Mac, a terminal keeps its own keys: inside a terminal pane :kbd[Ctrl K] and :kbd[Ctrl B] go to the terminal, not to Fleet.
:::

## Text size and alerts

The **···** button in the bar holds **Alerts** and **Terminal text** (**A−** and **A+**). The text size is remembered in this browser and applies to every terminal pane.

::cards{links="guides/sessions/drive-a-session, guides/sessions/review-a-sessions-work, guides/sessions/shell-on-a-machine"}

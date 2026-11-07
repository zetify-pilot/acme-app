# Find anything

When you are done you will know the one place to look for each kind of thing in Fleet, and the keyboard shortcut that gets you to any page from anywhere.

## Which search to use

| You are looking for | Search here |
|---|---|
| Something filed: a feature request, bug or task, or a customer's report | **Cockpit**, with the **Waiting on** chip removed |
| An issue the fleet works on, by key or title | **Queue** |
| A program, slice, PRD or any document in the knowledge base | **Knowledge** |
| A session, a machine or a page | The palette, ⌘K |

## The Cockpit: everything that was filed

The [Cockpit](guides/daily/cockpit) is one list of every feature request, bug and task, and every report from your product, history included. It opens on what waits on you (the chip **Waiting on** is **Me**); remove that chip to search everything.

1. [you] **Search.** The box takes words from a title, a Fleet id such as a bug's key, or a product report id.
2. [you] **Narrow it.** **Filter** adds a chip per choice: **Waiting on**, **State** (**Intake** through **Shipped**, **Closed** and **Cancelled**), **Filed by** (**Me** for what you filed), **Assignee**, **Kind**, **Customer**, **Came from** (**The product**, **By hand**, **My agents**, **CI**), **Filed** and **Changed** (**Last 24 hours**, **Last 7 days**, **Last 30 days**). Each choice shows how many it would hold.
3. [you] **Keep it.** **Save view** keeps the filters under a name. **Views** opens it later, and the filter **Filed by: Me** shows what you filed.

## Queue: the fleet's issues

On the **Queue** page, **Search the queue** takes an issue's key or words from its title. See [Read the Queue](guides/daily/the-queue).

## Knowledge: the plan and its documents

On the **Knowledge** page, **Search this corpus, or an id** searches every kind of planning document at once when you press Enter. Typing an id in full, such as `SL-XX`, opens it.

## The palette: jump anywhere

Press ⌘K (Ctrl K off a Mac) on any page. Type to filter, move with ↑ ↓, and press Enter.

- **Sessions** jumps to one of your open sessions.
- **Actions** has **Open a new session**.
- **Box shell** opens a shell on a machine.
- **Go to** lists every page in the sidebar.

> **Tip:** Off a Mac, inside a terminal pane, Ctrl K stays the terminal's own key. Click outside the pane first. Press ? for the list of keyboard shortcuts.

[Open the Cockpit](#cockpit)

Next: Read the Queue (guides/daily/the-queue) · File a feature request, a bug or a task (guides/daily/file-work) · Read the Programs list, and set its order (guides/plan/read-the-board)

---
- **program**: A larger result that two or more slices add up to and none delivers alone, used only by repositories that plan by programs.
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **PRD**: A piece of work one agent builds in one session, with acceptance criteria, and the only thing whose status anyone writes.

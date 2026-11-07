# Read the Queue

When you are done you will know what the fleet is about to spend its machines on and why, and you will have corrected an issue's priority, type, component or repository, or left a note on it, without opening your tracker.

## What the Queue shows

The **Queue** page lists the issues the fleet drives, grouped by their position. Rows that wait on a person lead the list in their own stage. A line above the list counts what is running, on how many machines, what waits on CI or on a merge, and how many machines are free.

The tabs split the same list four ways:

| Tab | What it holds |
|---|---|
| **Everything** | Every outstanding issue on this page |
| **Next up** | What the fleet ranked to work on next, in that order |
| **Held back** | What it did not rank and nobody needs to act on |
| **Running** | What a machine is working on now, including work that is not a tracker issue |

On the Queue page (#queue):
1. The four tabs, each with its count.
2. **Next up**: what the fleet takes next.
3. **Held back**: waiting for something, but not for you.

> **Why:** The Queue opens on work the fleet actually drives. Feature requests and work nobody has classified are left out by default, and the **Scope** filter names how many it leaves out, so nothing is hidden without saying so.

## Narrow the list

The filter row offers **Search the queue** (a key, or words from a title), and **Filter** adds **Scope**, **Kind** (the issue's type) and **Stage**, plus **Repository** when Fleet reads more than one. Every filter is part of the page's address, so a link carries your view, and the back button undoes a change.

## Open an issue's panel

Click a row. Its panel opens beside the list (over the page on a phone) and stays open while you walk the list with ↑ ↓. Escape closes it.

The panel shows why the issue is where it is and what it waits on. Its head carries **Actions** and, while a machine works on it, **Stop this run…** as well.

## Change priority, type, component or repository

1. [you] **Change the fields.** **Fields** lists **Priority**, **Type**, **Component** and **Repository**, each with a fixed list of choices. A changed field shows what it was.
2. [you] **Save.** The bar counts your unsaved changes. **Save changes** sends them; **Discard** drops them.
3. [fleet] **The tracker is updated.** The panel says **Sent** while the change waits to be written to the tracker, and the field is locked until the tracker shows it.

> **Careful:** **Priority** can only be changed on an issue that already has one. A missing priority means the issue has not passed the check, and setting one by hand would let it skip the check. Type and repository cannot be changed while a machine runs the issue; component can.

## Leave a comment

Under **Comment**, type a note the next reader of the issue should see, and press **Post comment**. It posts at once, from the Fleet account, opening with a line saying it is on your behalf.

## Move the issue

**Actions** holds the moves a person can make on the issue as a whole. Only the ones allowed in its current position are listed, and each asks before it acts.

- **Open a terminal…** starts a session about the issue.
- **Park** sets it aside: the fleet takes nothing from it until somebody moves it back. **Un-park** returns it to the queue it was parked from.
- **Take it by hand** and **Hand back**: see [Take work by hand](guides/daily/take-it-by-hand).
- **Approve** takes an issue out of the Backlog: to the Implement Queue when it was already graded, back to the check when it was not.
- **Reopen** sends a closed issue back to the check, with a reason.
- **Snooze…** appears when the issue waits on you. See [Work through the Cockpit](guides/daily/cockpit).
- **Close issue…** ends it, set apart at the foot of the menu.

[Open the Queue](#queue)

Next: Take work by hand (guides/daily/take-it-by-hand) · How work moves from filing to merge (concepts/how-work-moves) · Why is this item not moving? (troubleshooting/why-is-this-stuck)

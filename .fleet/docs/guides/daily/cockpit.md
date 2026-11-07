# Work through the Cockpit

When you are done you will have gone through everything in the Cockpit that waits on you, each item answered on its own page or snoozed until a day you chose, and you will know how to turn the same list into any other view you need.

## What the Cockpit holds

The Cockpit is the first page in the sidebar. It is one list of every item, one row per item, and it opens on what waits on you: a question an agent stopped on, a change ready for a yes, a new feature or a plan Fleet drafted for you to check (named "New feature: …" or "Plan: …"), a customer's report no agent has read, or a job only a person with access can do. The number on its sidebar entry counts those same items.

It opens with one chip on the filter bar, **Waiting on** is **Me**: the items with an open question or job that is assigned to you. An item is assigned to whoever filed it, and a question Fleet asks puts the person it is addressed to on the item it is about when nobody else is on it. A line under the bar says how many more wait on other people, such as "Showing what waits on you · 12 more wait on someone else ›"; click it to see what waits on anyone. Remove the chip with its **×** to see everything, history included: in progress, queued for Fleet, shipped, closed and cancelled.

**Waiting on** has five values:

| Value | What it holds |
|---|---|
| **Me** | An open question or job about the item is assigned to you. |
| **Someone else** | It waits on another person, or on a person nobody has been named for yet. |
| **Fleet running** | A machine is working on it now. |
| **Fleet queued** | It is the fleet's move, and no machine has started yet. |
| **Nothing** | Nobody is asked anything: it is finished, or it is set aside. |

With the chip removed, the list also shows issues that were closed in your tracker in the last 90 days, even ones nobody filed through Fleet: an issue someone marked done, cancelled or duplicate by hand shows as **Shipped**, **Cancelled** or **Closed**, and is waiting on nobody. Its **Changed** time and the time it reached that state are the tracker's own. A closed issue older than 90 days drops off the list unless it was filed through Fleet. If the issue is reopened, it shows as open work again. The 90 days is a setting your operator can change (`FLEET_ITEMS_CLOSED_WINDOW_DAYS`). Closed issues never wait on you, so they are never in the opening list or the sidebar number.

**Views**, above the filter bar, opens saved filters. One comes with Fleet: **Unassigned** (what waits on a person nobody is assigned to). To see what you filed, filter by **Filed by: Me**.

Each row shows its priority, the item and its type, the title with where it stands underneath, its feature (for a PRD or slice, the feature whose page lists it), its **State** and how long it has been there, such as "Implementing, for 2d" (an item that waits on a person says whom: "Waiting on you", or their name), links to its tracker issue and pull requests, who it is assigned to, and how long ago it reached its step.

A plan or an idea that has become PRDs reads as what those PRDs are doing, not as the day it was filed. With every PRD shipped it is shipped and waits on nobody. Otherwise it waits on whatever its pieces wait on, as the feature's own page shows them: on a person when one of its PRDs is stopped on a question (on you when it is asked of you, so the plan is in your **Waiting on: Me**), being worked on when Fleet is designing or building one of them, and in line for Fleet when a piece waits its turn. A piece that waits for another piece to ship waits on whatever that piece waits on, so a plan whose pieces all wait for one design that needs a person's answer waits on that person, not on Fleet. Its last change is the newest one among the plan and its PRDs, such as the day its last PRD shipped.

On the Cockpit page (#cockpit):
1. **Views**, your saved filters.
2. **Filter** and the chips it made, such as **Waiting on** is **Me**.
3. One item: its priority, its title, its state. Click it to open its page.

## Narrow the list

1. [you] **Filter.** **Filter** opens a list of fields. Pick one, then a value, and it becomes a chip, such as **Customer** is **acme**. Click **is** to turn it into **is not**; the **×** removes it.
2. [you] **Pick what you need.** **Waiting on**, **State**, **Assignee**, **Filed by**, **Kind**, **Customer**, **Came from** (**The product**, **By hand**, **My agents**, **CI**), **Filed**, **Changed**, **Priority**, **Label** and **Feature**. Each value shows how many items it would hold.
3. [you] **Pick a state.** **State** says where an item stands: **Intake**, **Triage**, **Planning**, **Queued**, **Implementing**, **Verifying**, **Waiting** (on a person), **Stopped**, **Held** (taken by hand), **Backlog**, **Shipped**, **Closed** or **Cancelled**. Pick **Closed** or **Cancelled** to see only what was closed or cancelled.
4. [you] **Pick a customer.** **Customer** lists every customer a `customer:` label names, such as `customer:acme`, and **No customer**.
5. [you] **Pick a time.** **Filed** and **Changed** each take **Last 24 hours**, **Last 7 days** or **Last 30 days**; click **within** to turn it into **older than**. **Changed** counts any change: a new state, a comment, a run, a question. Closed and cancelled items are in the list like any other, so **State** is **Closed** and **Changed** within **Last 7 days** finds what was closed this week. The time always counts back from now, so a view saved with **Last 7 days** shows the last seven days whenever you open it.
6. [you] **Search.** The search box matches the rows' words and keys, and offers to filter by a person whose name you type.
7. [you] **Group and sort.** **Display** holds **Group by** and **Sort by**. Group by offers **What's asked**, **Step**, **Feature**, **Assignee**, **Type**, **Priority**, **Label**, **Customer**, **State** and **None**. **What's asked** files items under **Decide**, **Approve** or **By hand**, and **Step** under the step they stand at; both put the items nobody is asked about under **Nothing asked**, last. Priority runs from **Urgent** to **No priority**, Assignee puts **Me** first and **Nobody** last, and Label and Customer put **No label** and **No customer** last. An item with several assignees, labels or customers is listed under each of them. Sort by offers **Default** (newest to reach where it stands), **Newest change**, **Newest filed** and **Priority**. Fleet remembers both choices in this browser.

For example, to follow one customer's work, remove **Waiting on**, add **Customer** is **acme** and **Changed** within **Last 7 days**, group by **State**, and press **Save view**: the view shows every item for that customer that changed in the last seven days, open or closed, each with its state.

## Save a view

**Save view** sits on the filter bar. Once the bar differs from how the Cockpit opens (**Waiting on** is **Me**, grouped by what is asked), it keeps what the bar holds under a name, with **Who sees it**: **Only me** or **Everyone**. A view saved before the Cockpit became one list opens as it was: a view of the old **Waiting** tab shows what waits on a person, and a view of the old **All items** tab shows everything. A saved view opens as its own page. Press its star to put it in the sidebar under **Cockpit**. Only the person who made a view can change, share or delete it; anyone can save a copy with **Save as a new view**. Until there is something to save, the button is greyed out, and pointing at it says why: change a filter, grouping or sort first, sign in, or your saved views could not be read just now.

## Answer an item

1. [you] **Open the row.** Click it. The item's own page opens, with its question in the first tab, **Waiting on a person**, beside its overview, its decision log and its activity.
2. [you] **Answer it.** Pick an option, type an answer, or press the button the question offers. How each kind of question works is in [Answer a question](guides/daily/answer-a-question); a by-hand job is in [Take work by hand](guides/daily/take-it-by-hand).
3. [fleet] **It leaves what waits on you.** Once your answer lands, the row's **Waiting on** moves on, and it leaves the list while **Waiting on** is **Me**. Use the page's crumb to go back to the list as you left it.

## Change many rows at once

Tick the box at the start of each row you want to change. A bar appears at the foot of the page, "*N* selected", with **Priority**, **Assignee**, **Labels** and **Feature**. The change is made on every selected row, and a message says what landed, with **Undo** (⌘Z) while it shows. The stage is Fleet's and cannot be changed here.

## Snooze an item until later

Snooze is Fleet's own hold on an item. It takes the item out of what waits on everyone, and out of the sidebar count, until its date, then brings it back by itself. The question stays open; nothing is withdrawn.

1. [you] **Press Snooze…** on the item's question card, or in the page's **⋯** menu.
2. [you] **Say why it can wait.** **Why can it wait?** is one line and required, for example "Waiting on the permissions decision".
3. [you] **Pick when it comes back.** **On a date** (any day after today), or **Until I say so**.
4. [you] **Press Snooze.** A message confirms the day it comes back.
5. [nobody] **It returns on its date.** The item waits on its person again that morning, and its page says it is back from snooze.

To see what is snoozed, add the **Show** filter with **Snoozed**: every snoozed item, with its reason, who snoozed it and when it comes back. **Bring back now** returns one early.

> **Careful:** Snooze is not the tracker's Parked position. Parking takes an issue away from the fleet with no reason or date; snoozing only takes a question out of everyone's list until its day.

[Open the Cockpit](#cockpit)

Next: Answer a question (guides/daily/answer-a-question) · Take work by hand (guides/daily/take-it-by-hand) · Screen what customers send (guides/daily/customer-reports)

---
- **Cockpit**: The first page in the sidebar: one list of everything waiting on a person, one row per item, beside everything that was filed.
- **Snooze**: Fleet's own hold on an item waiting on a person, which takes it out of everyone's Cockpit until the day you chose and then brings it back.
- **Parked**: The tracker position that takes an issue away from the fleet, with no reason or date, until someone moves it back.

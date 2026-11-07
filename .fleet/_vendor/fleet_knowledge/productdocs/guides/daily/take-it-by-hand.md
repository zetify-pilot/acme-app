---
title: "Take work by hand"
kind: guide
for: [everyone]
summary: "Do a job only a person can do and hand it back, or take an issue off the fleet and drive it yourself."
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/handmoves.py
  - packages/fleet-service/src/fleet_service/api/actionclear.py
  - knowledge/features/fleet-human-queues.md
minutes: 5
---

:::lede
When you are done the fleet will have its work back: either a job only you could do is done and handed back to it, or an issue you took off the fleet to work yourself is handed back to the queue you name.
:::

## Two ways work comes to your hands

- **The fleet asks you.** A run stopped because it needs something outside its reach: access it does not have, a setting in another system, a value only you know. The issue waits on a person, and it is listed in the [Cockpit](guides/daily/cockpit) as **By hand**.
- **You take it.** You decide to do an issue yourself. You take it by hand, and the fleet leaves it alone until you hand it back.

## Do a job the fleet asked for

:::steps
- [you] **Open the item.** In the Cockpit, filter **Asking for** to **By hand** and open the row. Its card is headed **Something only a person can do** and lists the steps the run wrote. **Why the run stopped, in its own words** opens its full text.
- [you] **Do the steps.** Do them outside Fleet, or press **Open a terminal…** to do them in an agent session about the issue.
- [you] **Fill in what it asks for.** Some jobs need values back, for example the name of a resource you created. They are written into the issue's description, so everyone can read them.
- [you] **Hand it back.** Press **Done — hand it back to the fleet**, or **Hand back and release** when the card has fields.
- [fleet] **A fresh run picks it up.** The issue goes back to where it stopped, and the next run reads what you did.
:::

:::callout{kind="careful"}
Never type a password, token or key into these fields. They are written into the issue for everyone to read. A secret belongs on the Secrets page.
:::

While a fleet agent is still working on the issue, the button is shown but disabled, with the line "A fleet agent is still working on this". Hand it back once it finishes.

## Take an issue yourself

Taking an issue by hand moves it to the :term[Human WIP] position. The fleet does not start work on an issue there, and only you can hand it back.

:::steps
- [you] **Find the issue on the Queue.** Click its row to open its panel beside the list.
- [you] **Choose Actions, then Take it by hand.** The box asks to confirm: the fleet stops working it and leaves it to you until it is moved back. Press **Take it**.
- [you] **Do the work.** **Open a terminal…** in the same **Actions** menu starts a session about the issue.
- [you] **Hand it back.** On the issue's panel, choose **Actions**, then **Hand back**. Pick **Where it goes**: **Implement Queue** to have it built, **Backlog** to set it aside, or **Verify Queue** to have your work checked (that one also asks for a priority). Add **Why** if you like, then press **Hand it back**.
- [fleet] **The fleet takes it from that queue.** From **Implement Queue** a machine picks it up and builds it; from **Verify Queue** a fresh session checks your work. **Backlog** waits until someone moves it on.
:::

:::callout{kind="why"}
Take it by hand is not offered while a machine is running the issue, or once it is closed. A running machine would overwrite the move or be stranded by it. Stop the run first, or wait for it to finish.
:::

A person's hold blocks every other move on the issue, including **Park**, so nobody else can move work out from under you. Closing the issue stays possible, but only for you. When the hold was set in the tracker and Fleet has no record of who took it, **Hand back** asks for a reason, recorded under your name.

::action[Open the Queue]{route="queue"}

::cards{links="guides/daily/the-queue, guides/daily/cockpit, concepts/how-work-moves"}

---
title: "Answer a question"
kind: guide
for: [everyone]
summary: "Answer what an agent asked you, approve a design it drew, or send the question back with instructions."
routes: [inbox]
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/inbox.py
  - packages/fleet-service/src/fleet_service/api/decisionclear.py
  - packages/fleet-service/src/fleet_service/api/mockview.py
  - knowledge/features/fleet-human-queues.md
minutes: 6
---

:::lede
When you are done the agent that stopped to ask you will have your answer and will carry on from it, whether you picked an option, wrote your own words, or approved a design it drew.
:::

## Where questions come from

An agent asks a person when it reaches something only a person can say: which of two designs, whether a bug is the bug, what an idea should cover. The question is listed in the [Cockpit](guides/daily/cockpit), and its card is the first tab of the page of the item it is about. Your answer goes back into the session that asked, which picks up from it.

A card names who asks and whose move it is. Questions come in two shapes:

- **A set of questions** from an interview or a planning step. It shows "Question 1 of 3" and walks you through them one at a time.
- **A decision** a run stopped on while working an issue, with its options. Its card is headed **Your decision**.

## Answer a set of questions

:::steps
- [you] **Read why you are asked.** **Why am I being asked this?** opens the brief the agent wrote. Each option can carry its reasons and costs; the recommended one is marked **recommended**.
- [you] **Pick an option, or write your own.** Click an option. **None of these — let me write it** opens a box headed **In your own words**.
- [you] **Move through the set.** **Next →** goes to the next question; **Back** returns to the one before. The count at the foot shows how many are answered.
- [you] **Send it.** On the last question the button is **Answer**. It is enabled once every question has an answer.
- [fleet] **The session carries on.** Your answers go back to the session that asked, and the item leaves the Cockpit's **Waiting** list.
:::

:::callout{kind="tip"}
When a draft is shown with the question **Does this say what you meant?**, the button reads **Approve and write it**. Pressing it is your go-ahead for the agent to write the document as drafted.
:::

## When you cannot answer

Under the options of an interview's question there is **Can't answer — carry on**. The agent goes on with an assumption it states and marks unconfirmed, and it is listed for you to confirm later. You can add **A line on why**. On an idea a customer filed there is also **Can't answer — ask the customer**, which sends the question to whoever filed it.

## Send it back

If the question itself is wrong, press **Send back**. **Send it back** asks for **Your instruction**: what the session should look at again, or do instead. The session that asked reads it as your answer and asks again.

## Answer a decision on an issue

:::steps
- [you] **Read the decision.** The card shows the brief and the options. **Why the run stopped, in its own words** opens the run's own text.
- [you] **Pick an option.** The recommended option is listed first.
- [you] **Press Decide.** When the run wrote no options, type into **Your answer** and press the button that hands it back.
- [fleet] **A fresh run picks it up.** Your choice is written into the issue's description, and the issue goes back to where it stopped.
:::

## Approve a design

A question can carry a :term[mockup]: clickable pages the agent drew. The card frames it under **Design**, or **Design for** when each option has its own; an option with one is marked **has a design**.

:::steps
- [you] **Look through it.** Links and buttons inside the frame work. When it has several pages, switch between them above the frame. When options carry designs, the tabs show each option's.
- [you] **Open it large if you need to.** **Open full screen ↗** opens it in its own tab.
- [you] **Answer the question.** Your answer approves the design as a whole, every page of it, not only the one showing.
:::

:::callout{kind="careful"}
A mockup link is signed for you and expires. Leave the card open and Fleet renews it. A link copied out of the frame stops working later.
:::

::action[Open the Cockpit]{route="cockpit"}

::cards{links="guides/daily/cockpit, guides/daily/after-you-file, guides/plan/fill-and-design-a-prd"}

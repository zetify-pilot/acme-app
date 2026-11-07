---
title: "Screen what customers send"
kind: guide
for: [owner, developer]
summary: "Read a customer's bug report or feature request before any agent does, then approve it, take it up, or turn it away."
routes: [customer]
sources:
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/screenclear.py
  - packages/fleet-service/src/fleet_service/api/screened.py
  - packages/fleet-service/src/fleet_service/api/product.py
  - knowledge/features/fleet-filings.md
minutes: 5
---

:::lede
When you are done every report and request a customer sent will have been read by a person first, and either handed to the fleet, linked to work that already exists, or closed with a reason.
:::

## Why a person reads it first

A customer's words come from outside your team. They can contain text that tries to instruct an agent: commands to run, files to change, links to follow. So Fleet gives no agent a customer's report until a person has read the exact text and approved it. This is :term[screening].

Customer items arrive in the **Waiting** list of the [Cockpit](guides/daily/cockpit). To see only them, filter **Type** to **Customer bug** or **Feature request**. On the **All items** tab, **Came from** is **The product** lists everything that came from your product.

## Screen a bug report

:::steps
- [you] **Open the report.** Its card asks **Approve this report for an agent to read?** **The request** tab holds the customer's words exactly as an agent will receive them, and **Evidence** their screenshot and log.
- [you] **Read it for instructions.** Approve only if it contains nothing that tries to instruct the fleet.
- [you] **Add what a reproduction needs, if you like.** **Edit** on the report's text lets you add context, such as the account or the steps, before you approve. Each save is a new version under your name; the customer's own words stay as version 1, and **edited · *N* versions** shows every version. The agent reads the latest. Saving approves nothing.
- [you] **Approve it or refuse it.** **Approve for reproduction** hands it to the fleet. **Refuse…** turns it away.
- [fleet] **It is reproduced, then confirmed.** An agent tries to reproduce it, and a person confirms the result, as for any bug. See [After you file](guides/daily/after-you-file).
:::

:::callout{kind="careful"}
When the report holds hidden characters, the card shows where and **Approve for reproduction** is disabled. Hidden characters can carry instructions you cannot see. A report that changes after you approved it is screened again as a new round; your earlier answer does not carry over.
:::

## Decide on a feature request

A feature request asks **Take this feature request up?**

- **Take it** files the request as a Fleet feature request and marks the customer's request done. It then goes through the [intake interview](guides/daily/after-you-file) like any other.
- **Same as…** links it to the feature request or issue it repeats.
- **Close** ends it as not planned, with an optional note to the person who asked.

Once taken up, the report's page says which bug or feature request it became, and links to it.

::action[Open the Cockpit]{route="cockpit"}

::cards{links="guides/daily/after-you-file, guides/team/report-keys, guides/daily/find-anything"}

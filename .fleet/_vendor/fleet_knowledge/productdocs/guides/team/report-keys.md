---
title: "Send bug reports between Fleets with a report key"
kind: guide
for: [admin]
summary: "Make a report key for a customer on Settings › API keys, and paste its connection code on Settings › Send reports in the customer's Fleet."
routes: [settings:reports]
sources:
  - packages/fleet-service/src/fleet_service/api/reportsending.py
  - packages/fleet-service/src/fleet_service/api/keys.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
minutes: 4
---

:::lede
When you finish this guide, every bug report filed in a customer's Fleet also reaches your Fleet, with its screenshot and browser log, so you can fix what broke. The reports stay in the customer's Fleet too.
:::

## Two Fleets, two pages

A report key joins two Fleets. Each side does one part:

- **The provider** (the Fleet that receives reports) makes one **report key** per customer. Fleet shows it once, as a **connection code**.
- **The customer** (the Fleet that sends reports) pastes that connection code on **Settings › Send reports** and switches sending on.

A report key can only file bug reports on the provider's Fleet, and nothing else.

:::steps
- [you] **Provider: make the key.** On **Settings › API keys**, under **Customer report keys**, click **New report key**. Type the **Customer name** and click **Create report key**.
- [you] **Provider: copy the code.** Fleet shows the connection code once. It cannot show it again. Copy it and send it to the customer's Fleet admin.
- [you] **Customer: save the code.** On **Settings › Send reports**, paste the code into **Connection code** and click **Check and save**. The page then names the provider and the address it sends to.
- [you] **Customer: switch sending on.** Tick **Send bug reports to** followed by the provider's name.
- [fleet] **Reports travel.** From then on, every bug report filed in the customer's Fleet is also sent to the provider.
:::

::action[Open Send reports]{route="settings:reports"}

## What each side sees

**Customer report keys** appears on Settings › API keys only on a Fleet that has been set up to receive customers' reports. Each key there can be revoked. **Revoke this report key?** warns that the next report filed with it is refused, and that a revoked key cannot be brought back.

On **Send reports**, the customer sees when the code expires and when the last report was sent. Before the code runs out, the page asks them to get a new one from the provider. Use **Replace code** to paste the new one. If reports cannot be sent, the page says why and how many are waiting. Waiting reports are sent once a working code is saved. A report the provider refused is listed with the provider's reason.

:::callout{kind="careful"}
The connection code holds the provider's address and the key itself. Treat it like a password: send it to the customer's admin only, and revoke the key if it leaks.
:::

If the **Send reports** entry is missing from a customer's Settings, their installation does not allow reports to leave it.

::cards{links="guides/daily/customer-reports, guides/your-tools/api-keys, guides/team/connect-github-and-tracker"}

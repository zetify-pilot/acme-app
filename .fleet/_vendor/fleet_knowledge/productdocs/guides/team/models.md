---
title: "Choose the models your fleet runs"
kind: guide
for: [admin, owner]
summary: "On Settings › Model config, choose the models the fleet may run, the weighted mix dispatch draws from, models for single steps, and what new sessions open on."
routes: [settings:models]
sources:
  - packages/fleet-service/src/fleet_service/api/modelconfig.py
  - packages/fleet-service/src/fleet_service/api/setup.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
minutes: 5
---

:::lede
When you finish this guide, Fleet has a list of models it may run and a default mix that every dispatch draws from. If you want, implementing, verifying and planning can also run on models of their own, and new sessions open on the model you chose.
:::

## Before you start

Models are paid for with the OpenRouter key saved on Settings › Set up, step 3 ([Connect your tracker, GitHub and a model provider](guides/team/connect-github-and-tracker)). Without that key, there is nothing to choose from.

Open **Settings › Model config**. The page has three cards, **Default mix**, **Models this fleet may run** and **New sessions and conversations**, and a save bar at the foot. Changes stay on the page until you click **Save changes**. They then take effect at once. **Discard** throws them away.

::action[Open Model config]{route="settings:models"}

## Choose the models

:::steps
- [you] **Add the models the fleet may run.** On **Models this fleet may run**, click **Add model**. The **Add a model** dialog lists OpenRouter's models that your key can run. Search by model ID or name, tick one or more, and click the **Add** button, which counts what you ticked (for example **Add 2 models**). A model that is already on the list shows **Already added**.
- [you] **Build the default mix.** On **Default mix**, click **Add to mix** and pick a model for each row. Each row also has a reasoning effort and a weight.
- [you] **Give a step its own model, if you want one.** Each model on the list has three tags, **implement**, **verify** and **Plan**. Ticking a tag makes that step draw from the tagged model instead of the mix. **Plan**, the step that splits a designed PRD into the work to build, also gets its own effort.
- [you] **Choose what people's new work opens on.** On **New sessions and conversations**, **Session default** is the model and **Thinking effort** a new session opens on; every allowed model stays in the session form's list. **Talk to it** is the model used when someone talks to a finished run. Left unset, a new session opens on the first allowed model, and a conversation uses your installation's own setting.
- [you] **Save.** Click **Save changes**.
- [fleet] **Every dispatch draws a model.** A step with its own model runs that model. Every other dispatch draws one model from the mix, chosen by weight.
:::

## How the mix chooses

Every dispatch draws one model from the mix, chosen by weight, whatever the task type. Weights are relative: with weights 3 and 1, the first model takes three quarters of the dispatches. A mix with one row always draws that one. The effort field is the reasoning effort the model is run with.

:::callout{kind="tip"}
Implementing and verifying are separate sessions, so each can have its own model. For example, you can keep the mix for implementing and tag one model for **verify**, so every verdict comes from the same model.
:::

## Remove a model

**Remove** on a model's row takes it off the list at once, without waiting for **Save changes**. A model that the default mix or a step still uses cannot be removed: its **Remove** is greyed out, and its tip says to **Reassign the default mix and any step first**.

Saving also changes which models the model picker offers when a person opens a session, and which one it opens on.

::cards{links="guides/team/connect-github-and-tracker, concepts/verify-before-merge, guides/team/machines-and-seats"}

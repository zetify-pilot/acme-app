---
title: "Ask the QA agent to check a promise"
kind: guide
for: [owner, developer]
summary: "Pick a promise nothing checks yet and have Fleet file one check for it, counted against tonight's limit."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/templates/quality.js
  - packages/fleet-service/src/fleet_service/api/briefing.py
  - packages/fleet-service/src/fleet_service/store/briefing.py
  - knowledge/journeys/flows/fleet-brief-a-check.md
minutes: 4
---

:::lede
When you are done, one check for a promise that had none is filed in your tracker under Fleet's own name, and the promise turns once the run writes its result.
:::

## Before you start

You ask from the Quality desk, on a :term[promise] that reads **not checked yet**. The kinds of check you can pick come from your repository's audit profile, and the areas from its feature maps; if either is missing, the dialog says there is nothing to ask for.

An asked check counts against the same nightly limit as the rest of Fleet's recurring work. With no limit set, an asked check is held until an operator sets one.

## Ask for the check

:::steps
- [you] **Find the promise.** On the **Promises** tab, press **Filter** and pick **Not checked yet**, or search for its id.
  ::screen{route="quality" pins="line,ask"}
  1. One line per feature, saying how many of its promises are not checked yet.
  2. The button that opens the dialog.
- [you] **Open it and press "Ask the QA agent to cover this".** The dialog shows the promise and how many checks are left tonight.
- [you] **Pick the kind of check.** **Kind of check** lists the kinds in your audit profile. If the promise names no area of its own, pick one under **Area** too.
- [you] **Add a note if it helps.** **Note for the QA agent** is optional, for example "try it with a second workspace". The promise itself always travels with the check.
- [you] **Press Ask.** It is at the foot of the dialog, beside **Cancel**, which closes it and files nothing.
- [fleet] **Fleet files one check.** With room left tonight, the page says the check is filed. With tonight's limit full, it says the check is **queued** and when it is held until; Fleet files it on its next pass. Nothing is dropped.
- [fleet] **The run writes its result.** When the QA agent's run finishes, the promise changes state on the desk's next read.
:::

:::callout{kind="tip"}
Pressing **Ask** twice, or a retry after a network hiccup, files no second issue. Each opening of the dialog is one request.
:::

:::callout{kind="careful"}
If the dialog refuses an area or a kind, nothing was filed. The area or kind is not one your installation defines; fix the audit profile or the feature maps rather than asking again.
:::

## Where the limit lives

The **Tonight** line on the desk says how many checks are left, and **more** names the briefs still waiting. The limit itself is set under recurring work on the System page.

::action[Open the Quality desk]{route="quality"}

::cards{links="guides/quality/quality-desk, guides/team/recurring-work, guides/knowledge/fill-slots"}

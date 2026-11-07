---
title: "Narrow Fleet to your programs"
kind: guide
for: [everyone]
summary: "Name who is responsible for each program, then see only your own programs on the Programs list."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/templates/board.js
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/owners.py
  - knowledge/features/fleet-personal-views.md
minutes: 4
---

:::lede
When you are done every :term[program] will name the people responsible for it, and you will be able to narrow the Programs list to the ones that are yours with one control.
:::

## Name who is responsible

Each program can name one or more people who are :term[responsible] for it. Anyone on your team can set it.

:::steps
- [you] **Open Programs.** The **Responsible** column shows who is responsible for each program, or a button to assign someone.
- [you] **Click it on the program's row.** A box asks **Who is responsible for** that program, and lists the people who have signed in to your Fleet. **Search by name or email** narrows it.
- [you] **Pick the people and press Save.** Tick one or more people, then press **Save**; **Cancel** leaves it as it was. Each person you picked now finds the program under **Assigned to me**.
:::

:::callout{kind="why"}
This changes what each person sees, never what they may open. A program you are not responsible for is still one click away from anyone.
:::

## Narrow the Programs list

The Programs list opens on every program. Under **Filter**, choose **Assigned** and then **Assigned to me** to see only the programs you are responsible for. It shows as a chip while it narrows; its × shows every program again. **Unassigned** shows the programs nobody is responsible for yet.

If you are responsible for nothing yet, the list says so. Ask a teammate to set it, or clear the filter.

::action[Open Programs]{route="board"}

## What the Cockpit shows you

The [Cockpit](guides/daily/cockpit) narrows by person, not by program. It opens on what waits on you: the items assigned to you, and the questions asked of you by name. Its **Assignee** filter shows **Me** while it narrows; remove the chip to see everyone's, or pick **Nobody** for what no one is assigned yet. The sidebar count counts what waits on you.

:::callout{kind="careful"}
**Assigned to me** appears only when Fleet knows who you are. On a Fleet with no sign-in, such as one run on your own machine, every program shows, and the Cockpit opens on everyone's items.
:::

::action[Open the Cockpit]{route="cockpit"}

::cards{links="guides/daily/cockpit, guides/plan/read-the-board, guides/plan/shape-a-program"}

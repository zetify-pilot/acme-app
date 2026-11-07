---
title: "Answer the questions the commands ask about your repository"
kind: guide
for: [developer, owner]
summary: "Replace the placeholder slot answers fleet init wrote, so every command can run in your repository and none runs half-blind."
routes: [slot]
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/slots.py
  - packages/fleet-knowledge/src/fleet_knowledge/slot-questions.json
  - packages/fleet-knowledge/src/fleet_knowledge/scaffold.py
  - packages/fleet-knowledge/src/fleet_knowledge/slotanswers.py
  - packages/fleet-knowledge/src/fleet_knowledge/cli.py
  - packages/fleet-knowledge/src/fleet_knowledge/templates/board.js
  - packages/fleet-knowledge/src/fleet_knowledge/templates/scaffold/knowledge/slots/gate.md
minutes: 6
---

:::lede
When you are done, every question Fleet's commands ask about your repository has a real answer in it, the Agents page shows those slots as **filled**, and no command is blocked or runs with less than it needs.
:::

## What a slot is

A command is a procedure that works in any repository. What it cannot know is how *your* repository does things: how to run its tests, how branches are named, which issue tracker it files into. Each of those questions is a :term[slot], and your repository answers it with a short document.

Every slot is one of three kinds:

| Kind | What happens while it has no answer |
|---|---|
| Ships with the agents | Nothing for you to do. It is answered under `.fleet/`, the same in every repository. |
| Required here | Every command that needs it refuses to run. |
| Optional here | Commands still run, with less to go on. Each slot says what goes missing without it. |

## See which slots need you

Open **Settings › Agents**. Under the agents, three lists cover the slots: **Slots that ship with the agents**, **Slots this repository must answer**, and **Declared by no agent**. Each row says what the slot answers, which file answers it, how many agents use it, and its state:

- **filled**: a real answer.
- **stub**: the file is there but is still the placeholder `fleet init` wrote. Write the real answer in it.
- **missing**: a required slot with no file at all.
- **not set**: an optional slot nobody has answered.

::action[Open Agents]{route="settings:agents"}

From a terminal, the same survey is:

```sh
fleet slots --repo .
```

It lists each slot as filled or not, and ends by saying which commands can run here.

## Fill one in

:::steps
- [you] **Open the file the slot points at.** `fleet init` writes required slots to `knowledge/slots/<slot>.md`, for example `knowledge/slots/gate.md` for how lint, build and tests run. Below its first line, a `<!-- fleet:stub -->` marker, it says what it is asking. Slots Fleet could answer itself, such as `git-workflow`, arrive already **filled**; read them and correct what is wrong.
- [you] **Write the answer.** In plain words, for an agent that has never seen the repository: the commands to run, what green means, where things live. Point at a document the repository already has when it already says it.
- [you] **Delete the placeholder line.** The file starts with `<!-- fleet:stub -->`. While that line is there, the slot counts as unanswered, however much you wrote under it.
- [you] **Merge it.** Open a pull request as usual.
- [fleet] **The Agents page reads it.** After the next sync the row reads **filled**, and the commands that needed it can run.
:::

:::callout{kind="tip"}
A slot is a question, not a path. If your answer already lives somewhere else, such as an existing architecture document, point the slot at that file in `knowledge/slots/README.md` instead of copying it.
:::

## Make it a gate

`fleet slots` always succeeds; it only reports. The check form is what your build runs:

```sh
fleet check --only slots
```

It fails when a command needs a required slot that has no answer file at all. A required slot that is still only a placeholder is a warning, not a failure, so a freshly set-up repository does not fail every pull request. Add `--strict` to fail on warnings too, once your answers are written.

::cards{links="knowledge-base/slots, guides/knowledge/fix-a-failing-check"}

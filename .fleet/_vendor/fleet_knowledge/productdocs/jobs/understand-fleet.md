---
title: "Understand Fleet"
kind: job
icon: understand
group: learn
for: [everyone]
summary: "What Fleet does, who decides what, and why every change is checked twice before it merges."
minutes: 3
---

:::lede
Fleet turns what your team decides into merged code. This path shows how a piece of work moves, where Fleet stops for a person, and why the agent that writes a change never approves it. Once you have read it, every other page in these docs will make sense.
:::

## The big picture

::diagram{name="fleet-map"}

Every piece of work in Fleet is an issue in your own tracker. At every moment it sits in exactly one :term[position], and the position says who has it. A queue means a machine will take it next. `Implementing` or `Verifying` means a run is working on it, and nobody else can take it. A blocked position means it waits on a person. `Done` means it merged.

Fleet settles most of what happens in between. It checks what you filed, builds it and verifies it on its own. It stops for a person in a few clear cases: to promise something new, to answer a question an agent cannot settle, or to do something no agent can, such as create a credential. Each of those lands in your :term[Cockpit]. And every change passes two separate sessions. One writes it and opens a pull request. A fresh one, which never saw the code being written, proves each claim and then merges it or sends it back.

## Read these in order

::path{links="start/what-fleet-is,concepts/how-work-moves,concepts/the-work-line,concepts/who-decides-what,concepts/verify-before-merge"}

## When you need it

::pages{links="concepts/your-tracker,concepts/commands-and-tools"}

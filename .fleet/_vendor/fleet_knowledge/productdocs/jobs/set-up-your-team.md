---
title: "Set up your team's Fleet"
kind: job
icon: team
group: run
for: [admin, owner]
summary: "Connect your tracker, GitHub and a model provider, add repositories, and decide how much work each machine takes on."
minutes: 3
---

:::lede
An admin sets Fleet up once. This path connects your tracker, GitHub and an AI provider, adds a repository, picks the models, and decides how much work each machine takes on. When you are done, **Settings › Set up** says **Fleet is ready**.
:::

## The big picture

:::ideas
- **Repository.** A codebase Fleet works on. Each one says who merges its pull requests and whether Fleet posts its verify check there.
- **Model config.** The models the fleet may run, and the mix every run draws from.
- **Machine.** A computer running Fleet's worker. It asks Fleet for work; Fleet decides everything else.
- **Seat.** One session at a time on a machine. A dispatch seat works the queue on its own; an interactive seat is where a person runs a session.
:::

**Settings › Set up** walks you through five steps: your tracker, your GitHub App, an AI provider key, a repository and one worker. Its :term[seat]s set how much it takes on, and **Drain** lets it finish what it holds and take nothing new, for maintenance.

Fleet decides which command runs and which model it uses, so changing either never means updating the machines. Each run gets a model from your mix, chosen only among the models that machine can pay for. Recurring work, such as a nightly audit, is written once in the repository's `fleet.toml` and filed within a nightly limit you set.

## Read these in order

::path{links="guides/team/connect-github-and-tracker,guides/team/repositories,guides/team/models,concepts/machines-seats-runs,guides/team/machines-and-seats"}

## When you need it

::pages{links="guides/team/verify-check,guides/team/agents-page,concepts/recurring-work,guides/team/recurring-work,guides/team/report-keys"}

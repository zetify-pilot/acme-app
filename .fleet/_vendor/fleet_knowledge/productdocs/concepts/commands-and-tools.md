---
title: "Commands and tools"
kind: concept
for: [developer]
summary: "Commands are the written procedures an agent follows. Tools are how an agent reaches Fleet. The fleet runs some commands alone; others need a person."
sources:
  - ARCHITECTURE.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandsync.py
  - packages/fleet-knowledge/src/fleet_knowledge/slots.py
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/check.md
  - packages/fleet-service/src/fleet_service/dispatch/routing.py
  - packages/fleet-service/src/fleet_service/dispatch/attendance.py
  - packages/fleet-service/src/fleet_service/api/mcptools.py
  - packages/fleet-service/src/fleet_service/api/resync.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/features/fleet-command-tier.md
  - knowledge/features/fleet-work-tracking.md
minutes: 7
---

:::lede
A command is a written procedure an agent follows, step by step, to do one kind of work: check a filing, fix a bug, verify a change. A tool is how that agent reaches Fleet: to read an issue, file one, move one or ask a person. The commands are what Fleet does; the tools are how it does it safely.
:::

## Commands

Each :term[command] is a markdown file with a name in two parts, the thing and the step, such as `bug:fix` or `slice:create`. You call it as a slash command.

::command{name="check"}

The commands ship with Fleet. `fleet commands sync` writes them into a repository's `.fleet/` folder, as a plugin. Fleet's own sessions load that folder. An engineer who wants the commands in their own Claude Code opts in the same way; nobody gets them by accident.

To bring a repository up to the release your install runs, open **Settings › Repositories** and press **Apply Fleet**. Fleet opens one pull request that changes only its own files. You review it and merge it; Fleet never merges it.

## What the fleet runs on its own

The fleet picks the command from an issue's position and type. Nobody chooses it per issue.

| Position | Command |
|---|---|
| `Intake Queue` | the interview, or the routing step, by the feature request's stage |
| `Triage Queue` | the triage check |
| `Implement Queue`, `Rework Queue` | `bug:fix`, `task:implement`, `prd:implement` or `audit`, by type |
| `Verify Queue` | `verify`, or `prd:verify` for a PRD |

A command says for itself whether it may run with nobody attached. The fleet runs a command alone only when the command says it needs no person. Some commands have a twin for each case: the fleet designs a drafted PRD on its own with `prd:blueprint`, while `prd:design` is the same step with you at the keyboard, in a session or your own terminal.

::command{name="prd:design"}

## Slots: what a repository must answer

A command often needs a fact only your repository knows: how to run its tests, where its code is generated, what its tracker calls things. Each such question is a :term[slot]. Your repository answers its slots in its own files. A command whose required slot is unanswered is reported as unable to run there, rather than guessing.

## Settings › Agents

In the app, each command is called an agent. **Settings › Agents** lists, for each repository, the agents it serves, and opens a command's full text with every document it points at.

::action[Open Agents]{route="settings:agents"}

## Tools

Agents reach Fleet through its tools, served as an MCP server. The tools cover issues (`get_issue`, `search_issues`, `file_issue`, `move_issue`, `triage`, `comment`), questions (`ask`), the board and the queue, and a few more. The full list is in the MCP tools reference.

- **A fleet session** gets a key in a private file. A dispatched run's key reaches only what its command may do, and every call is checked against it. No session ever holds a tracker credential.
- **You**, on your own machine, connect Claude Code or another AI tool with an API key in your name. **Settings › Connect your tools** walks you through it. Nothing is installed.

::action[Connect your tools]{route="settings:connect"}

::cards{links="guides/your-tools/connect-your-terminal, guides/your-tools/fleet-commands-locally"}

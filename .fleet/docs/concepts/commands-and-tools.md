# Commands and tools

A command is a written procedure an agent follows, step by step, to do one kind of work: check a filing, fix a bug, verify a change. A tool is how that agent reaches Fleet: to read an issue, file one, move one or ask a person. The commands are what Fleet does; the tools are how it does it safely.

## Commands

Each command is a markdown file with a name in two parts, the thing and the step, such as `bug:fix` or `slice:create`. You call it as a slash command.

`check` — Gatekeep every newly-filed tracker issue in a fresh session: confirm it is real and new, judge it against what the product has already committed to, triage it, then release it to the fleet, escalate a decision to the human, park operator-hands work in Blocked · action, or close it.

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

`prd:design` — Technical + UX design grounded in a PRD; produces design.md (+ optional ux-design.md).

## Slots: what a repository must answer

A command often needs a fact only your repository knows: how to run its tests, where its code is generated, what its tracker calls things. Each such question is a slot. Your repository answers its slots in its own files. A command whose required slot is unanswered is reported as unable to run there, rather than guessing.

## Settings › Agents

In the app, each command is called an agent. **Settings › Agents** lists, for each repository, the agents it serves, and opens a command's full text with every document it points at.

[Open Agents](#settings:agents)

## Tools

Agents reach Fleet through its tools, served as an MCP server. The tools cover issues (`get_issue`, `search_issues`, `file_issue`, `move_issue`, `triage`, `comment`), questions (`ask`), the board and the queue, and a few more. The full list is in the MCP tools reference.

- **A fleet session** gets a key in a private file. A dispatched run's key reaches only what its command may do, and every call is checked against it. No session ever holds a tracker credential.
- **You**, on your own machine, connect Claude Code or another AI tool with an API key in your name. **Settings › Connect your tools** walks you through it. Nothing is installed.

[Connect your tools](#settings:connect)

Next: Connect your own AI tool to Fleet (guides/your-tools/connect-your-terminal) · Use Fleet's commands in your own Claude Code (guides/your-tools/fleet-commands-locally)

---
- **command**: One step of Fleet's work, such as `bug:fix` or `slice:create`, written as a markdown file that a session runs.
- **slot**: One question a command asks about the repository it runs in, and the place where the repository answers it.

---
title: "Connect your own tools"
kind: job
icon: tools
group: use
for: [developer]
summary: "Your own MCP servers and tokens in the sessions you open, team secrets for the work, and Fleet's tools in your own terminal."
minutes: 3
---

:::lede
Bring what you already use into Fleet, and take Fleet into what you already use. This path sets up your own MCP servers in the sessions you open, stores the tokens they need, and hands a credential to a session that needs one.
:::

## The big picture

:::ideas
- **My MCP config.** Your own MCP servers, such as Confluence or Figma, added to every session you open.
- **My secrets.** Your personal tokens. Only your sessions can use them, and your MCP config names them instead of holding them.
- **Secrets.** Credentials the work needs, such as a vendor API or a test login. Your whole team sees their names, and a session gets one only when you attach it.
- **API keys.** A key that lets a tool on your own computer act as you in Fleet.
:::

There are two directions. Into Fleet: your MCP config names a token as `{secret:name}`, and Fleet puts the value in when it hands the config to your session. Runs the fleet dispatches on its own never get your servers, and a session that holds them becomes private to you. Servers every session should have, runs included, go on the team's list, **Shared MCP servers**, instead. To pick between the two kinds of :term[secret], ask one question: does the work need it, or do you?

Out of Fleet: an :term[API key] lets Claude Code or another AI tool on your own computer read, file and move issues through Fleet in your name, with no tracker key on your machine. You can also load the repository's Fleet commands into your own Claude Code.

## Read these in order

::path{links="guides/your-tools/personal-mcp,guides/your-tools/shared-mcp,guides/your-tools/my-secrets,guides/secrets/team-or-personal,guides/secrets/attach-a-secret"}

## When you need it

::pages{links="guides/your-tools/connect-your-terminal,guides/your-tools/api-keys,guides/your-tools/fleet-commands-locally,guides/services/atlassian,guides/services/figma"}

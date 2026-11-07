---
title: "Set up Figma's MCP server for your sessions"
kind: guide
for: [developer]
summary: "Connect Figma to your Fleet sessions with a personal access token and the Framelink server, and why the server stays in your own config."
sources:
  - packages/fleet-service/src/fleet_service/api/mcpconfig.py
  - packages/fleet-service/src/fleet_service/api/me.py
  - packages/fleet-daemon/src/fleet_daemon/mcplist.py
minutes: 5
---

:::lede
When you finish, a session you open can read the Figma files your token can open: frames, layout and styles. You add the server to **My MCP config**, and the token lives on **My secrets**.
:::

Figma's official remote server needs an interactive sign-in that Fleet cannot run, so Fleet uses the community Framelink server. It is a local program that Fleet starts with `npx`, and it reads through Figma's public API. It cannot write to the canvas.

## What you need

- A Figma account that can open the files you want to read.
- Node.js on the machine that runs your session. Fleet's sessions include it, so `npx` can start the server.

## Create a personal access token

1. In Figma, open the file browser, click the account menu in the top-left corner and choose **Settings**.
2. Select **Security**, then **Personal access tokens**.
3. Choose **Generate new token**, give it a name and choose its scopes.
4. Copy the token straight away. Figma shows it only once. It starts with `figd_`.

Figma's own page is [Manage personal access tokens](https://help.figma.com/hc/en-us/articles/8085703771159-Manage-personal-access-tokens).

## Store the token

On **My secrets**, press **Add a secret**, name it `figma_pat`, paste the token and press **Save secret**. Fleet stores it encrypted and shows only its last four characters.

::action[Open My secrets]{route="settings:my-secrets"}

## The config

On **My MCP config**, paste this entry and press **Save**:

```json
{
  "figma": {
    "type": "local",
    "command": ["npx", "-y", "figma-developer-mcp", "--stdio"],
    "environment": {
      "FIGMA_API_KEY": "{secret:figma_pat}"
    }
  }
}
```

The `{secret:figma_pat}` reference goes in the environment value, never in the command. A secret in a command would land on the process's command line.

## The shared list

The shared list takes remote servers only. The Framelink server is local, so **Shared MCP servers** refuses it. Figma's official remote server needs interactive sign-in, which Fleet does not support, so there is no shared Figma server today.

If your team needs Figma in every session, each person adds this entry to their own **My MCP config**. Runs Fleet dispatches on its own get no Figma. The shared list and its rules are on [Give every session the same MCP servers](guides/your-tools/shared-mcp).

## What success looks like

Open a new session. In its first lines, the server reads `loaded`. In a terminal session you can also run `opencode mcp list` and see the server listed as connected.

## Common failures

| What you see | What it means | What to do |
|---|---|---|
| `could not start` | Fleet could not run `npx figma-developer-mcp`. | Check the `command` line, and that Node.js is available in the session. |
| `refused its secret` | Figma rejected the token. | Generate a new token and replace `figma_pat`. |
| Save is refused, naming a missing secret | The name after `{secret:` must match a secret on My secrets. | Add `figma_pat`, or fix the spelling. |

::cards{links="guides/your-tools/personal-mcp, guides/your-tools/shared-mcp"}

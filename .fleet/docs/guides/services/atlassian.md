# Set up Atlassian's MCP server for Confluence and Jira

When you finish, a session you open can read the Confluence pages and Jira issues your Atlassian account can see. You can put the server in your own **My MCP config**, or, with a read-only account, on the team's **Shared MCP servers** list so every session and run gets it.

You do it in three parts: an Atlassian admin turns on API-token sign-in, you create a credential, and you paste one entry into a Fleet settings page. The entry never holds the credential itself: it names a Fleet secret as `{secret:name}`, and Fleet puts the value in when it hands the config to a session.

## Before you start

You need an Atlassian account that can see the Confluence spaces and Jira projects you want. To share the server with everyone, you also need an account the whole team may use. A read-only service account is the safer choice.

> **Careful:** Atlassian turns API-token sign-in off by default. Until an organisation admin turns on **API token** under **Connectors**, **Atlassian MCP server**, **Authentication** at [admin.atlassian.com](https://admin.atlassian.com), Atlassian refuses every token, however right it is. Atlassian's own documentation calls this *allow API token authentication*.

## Choose a credential

Atlassian's MCP server accepts two kinds of credential. Pick one.

| Credential | Who it suits | The exact header |
|---|---|---|
| Personal API token | One person's own sessions | `Authorization: Basic <base64>` |
| Service-account API key | A shared account, or unattended use | `Authorization: Bearer <key>` |

For a personal API token, build the base64 value from your Atlassian email and the token joined by a colon:

```bash
printf '%s' 'your.email@example.com:YOUR_API_TOKEN' | base64 | tr -d '\n'
```

The whole output is the value after `Basic `. Create the token at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens). Atlassian shows it once.

For a service-account API key, create the key in the Atlassian admin console and keep it as it is. The header sends it after `Bearer `.

## Store the credential

**Your own sessions.** On **My secrets**, press **Add a secret** and save the value under `atlassian_auth` for a personal token or `atlassian_key` for a service-account key. Fleet stores it encrypted and shows only its last four characters.

[Open My secrets](#settings:my-secrets)

**Every session and run.** On **Secrets**, save the same value under the same name and tick **Give it to every session**. The row then shows an **every session** chip.

> **Careful:** Tick **Give it to every session** before you save. You can change that choice later: open the secret's **⋯** menu, press **Change settings**, tick **Give it to every session** and press **Save settings**. You do not paste the value again. A secret saved without it is refused by the shared list with *you have no shared key named …*.

[Open Secrets](#settings:secrets)

> **Careful:** A key with **Give it to every session** reaches every session and every run, whoever started it. Use a read-only account for this, so the worst a session can do is read.

## The config

The entry is the same `mcp` shape that OpenCode uses. Paste it into the editor on the page you chose and press **Save**.

**My MCP config** (only the sessions you open):

```json
{
  "atlassian": {
    "type": "remote",
    "url": "https://mcp.atlassian.com/v2/mcp",
    "oauth": false,
    "headers": {
      "Authorization": "Basic {secret:atlassian_auth}"
    }
  }
}
```

With a service-account key, change the last line to `"Authorization": "Bearer {secret:atlassian_key}"`.

**Shared MCP servers** (every session and run):

```json
{
  "atlassian": {
    "type": "remote",
    "url": "https://mcp.atlassian.com/v2/mcp",
    "oauth": false,
    "headers": {
      "Authorization": "Basic {secret:atlassian_auth}"
    }
  }
}
```

On the shared list, use the secret you saved on **Secrets** with **Give it to every session**. The shared list accepts only remote servers with `"oauth": false`, which this entry is.

## What success looks like

Open a new session. In its first lines, the server reads `loaded`. In a terminal session you can also run `opencode mcp list` and see the server listed as connected.

A session that is already open keeps the config it started with, so open a new one after a save.

## Common failures

| What you see | What it means | What to do |
|---|---|---|
| `refused its secret` or a 401 | Atlassian rejected the credential. The admin switch is often still off. | Ask the admin to turn on API token authentication, then replace the secret. |
| `could not start` | The address is wrong or the server never came up. | Check that the `url` is `https://mcp.atlassian.com/v2/mcp`. |
| `skipped` | The shared list or the machine already has a server with that name. | Rename your entry, or remove the other one. |

The full list of session lines is on [Use your own MCP servers in sessions](guides/your-tools/personal-mcp), and the shared list's own rules are on [Give every session the same MCP servers](guides/your-tools/shared-mcp).

Next: Use your own MCP servers in sessions (guides/your-tools/personal-mcp) · Give every session the same MCP servers (guides/your-tools/shared-mcp)

# Use your own MCP servers in sessions

When you finish, every terminal and agent session you open starts with your own MCP servers, for example Atlassian's server for Confluence and Jira and a Figma server. They run with your access and your tokens. Nobody else's sessions get them, and neither do runs Fleet dispatches on its own.

You do it on two pages under **You** in Settings: **My secrets** holds your tokens, and **My MCP config** lists your servers. The config never holds a token. It names one as `{secret:name}`, and Fleet puts the value in when it hands the config to your session.

## Before you start

You need an account on each service, with access to what you want to read. Each service has its own page for creating a credential and writing its entry:

- [Set up Atlassian's MCP server for Confluence and Jira](guides/services/atlassian)
- [Set up Figma's MCP server for your sessions](guides/services/figma)

Follow the service's page, then come back here for how the config is saved and how to read a session's first lines.

## Set it up

1. [you] **Save your tokens on My secrets.** Press **Add a secret**, give it a name, paste the value and press **Save secret**. Use the secret name the service's page gives you, because its config entry uses that name. A name uses letters, digits, dots, dashes and underscores, and starts with a letter or a digit.

   [Open My secrets](#settings:my-secrets)
2. [fleet] **Fleet keeps the value to itself.** It stores the value encrypted and from then on shows only its last four characters. Only you can see it, and only sessions you open receive it. Fleet does not test it against the service.
3. [you] **Write your servers on My MCP config.** Paste the entry from the service's page into the editor and press **Save**.
4. [fleet] **Fleet checks the config before it saves anything.** The line above the editor reads *valid*, with how many servers and secrets it found. If anything is wrong, it lists every problem with the entry, the field, the fault and the fix, and ends *Nothing was saved.*
5. [you] **Open a new session.** Press ⌘K (Ctrl+K off a Mac) and choose **Open a new session**. Your config applies only to sessions opened after you save it; a session that is already open keeps what it started with.
6. [fleet] **The session lists your servers first.** Before the agent does any work, the session prints `fleet · your MCP servers` with one line per server. If your team has set up servers for every session on **Settings › Shared MCP servers**, they are listed above yours under `fleet · shared MCP servers` (see [Give every session the same MCP servers](guides/your-tools/shared-mcp)). *Reading the first lines* below says what each line means.

## The config

The editor holds one JSON object: each key is a server name you choose, and each value is that server's entry, in the `mcp` format of OpenCode's config. Each service page carries the exact entry to paste. Every entry uses one of these two shapes:

```json
{
  "a-remote-server": {
    "type": "remote",
    "url": "https://example.com/mcp",
    "oauth": false,
    "headers": {
      "Authorization": "Bearer {secret:my_token}"
    }
  },
  "a-local-server": {
    "type": "local",
    "command": ["npx", "-y", "some-server", "--stdio"],
    "environment": {
      "SERVICE_API_KEY": "{secret:my_token}"
    }
  }
}
```

A `remote` entry needs a `url`; a `local` entry needs a `command` list. The save check also holds you to these rules:

- **`{secret:name}` goes only in a header value or an `environment` value.** In a `url` it would be logged with every request, and in a `command` it would land on the process's command line.
- **The name must match a secret on My secrets exactly.** A missing name is refused, and the problem lists the names you do have.
- **Never paste a token into the config.** A value that looks like a token is refused, with a pointer to My secrets.
- **If a remote server sets `oauth`, it must be `false`.** Fleet cannot run an interactive sign-in, so any other value is refused.
- **`{env:…}` and `{file:…}` are refused.** They would reach the server as plain text.
- **Don't reuse the name of Fleet's own tools server.** The check names the clash if you do.

On the My MCP config page (#settings:my-mcp):
1. The editor, with a status line above it: *valid*, *unsaved changes*, or how many problems stop the save.
2. **Save**. After a save that lands, the page says *Sessions you open from now on start with them.*

[Open My MCP config](#settings:my-mcp)

## Reading the first lines

| The line says | What it means | What to do |
|---|---|---|
| `loaded` | The server is running in this session. | Nothing. |
| `refused its secret` | The service turned the token down. For Atlassian, the admin switch is often still off. | Check the admin switch on the [Atlassian page](guides/services/atlassian), then replace the secret on My secrets. |
| `could not start` | The server never came up: a wrong command or address. | Check the entry on My MCP config. |
| `still starting` | A local server has not answered yet. It may load once its package has downloaded. | Wait. |
| `skipped` | The team's shared list or the worker running your session already has a server with that name, and that one wins, so yours was not used. | Rename your entry. |
| `dropped` | Fleet could not fetch one of its secrets, or could not hand it to the session. | Check the secret on My secrets, then open a new session. |
| `failed` | The server failed for another reason, printed under the line. | Read the reason, then fix the entry or the secret. |
| `status unknown` | The server list could not be read. | Open a new session. |

A server that fails never stops the session. The session goes on without it and says so.

## Change or remove a secret

To change a value, press **Replace** on the secret and enter the new one. The name stays.

To remove one, press **Delete** and confirm **Delete secret**. Fleet refuses while your MCP config still uses it, and names the entries that do: take those out of the config first. A deleted value cannot be brought back; you add it again.

If a secret shows *Can't be read*, Fleet can no longer read the saved value and no session receives it. Enter the value again with **Replace**.

A token that everyone working a task needs belongs on **Secrets**, under Access, not on My secrets. A server every session should have belongs on the team's list: see [Give every session the same MCP servers](guides/your-tools/shared-mcp).

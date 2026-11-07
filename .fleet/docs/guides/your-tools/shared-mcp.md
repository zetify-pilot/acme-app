# Give every session the same MCP servers

When you finish, every terminal session, every agent session and every run Fleet starts on its own begins with the same MCP servers, for example Atlassian's server for Confluence and Jira. An agent reads the real page instead of a pasted copy.

This is the team's list, one for your whole Fleet. Your own servers, which only your sessions get, are on **My MCP config**: see [Use your own MCP servers in sessions](guides/your-tools/personal-mcp).

You use two pages under **Access** in Settings: **Secrets** holds the keys, and **Shared MCP servers** lists the servers. The list never holds a key. It names one as `{secret:name}`, and Fleet puts the value in when it hands the list to a session.

## Set it up

1. [you] **Save the key on Secrets.** Press **Add a secret**, give it the name the service's page says, paste the value and tick **Give it to every session**. Press **Save secret**. The row now shows an **every session** chip.
   If a key is already saved without that choice, open its **⋯** menu, press **Change settings**, tick **Give it to every session** and press **Save settings**. You do not paste the value again.

   [Open Secrets](#settings:secrets)
2. [you] **Write the servers on Shared MCP servers.** Paste a config like the one below into the editor and press **Save**.

   [Open Shared MCP servers](#settings:shared-mcp)
3. [fleet] **Fleet checks the list before it saves anything.** The line above the editor reads *valid*, with how many servers and keys it found. A URL-only entry is saved as a remote server with `"oauth": false`. If anything else is wrong, one refusal lists every missing field with the value to use, and ends *Nothing was saved.*
4. [fleet] **The next session starts with them.** A change applies to the next session or run each machine starts; one already running keeps what it started with. The page says who saved the list last, and when. It also shows each server's last start result from a session, so a broken server is visible here without opening a session.

> **Careful:** A secret saved without **Give it to every session** is refused by the shared list with *you have no shared key named …*. To fix it, open the secret's **⋯** menu, press **Change settings**, tick **Give it to every session** and press **Save settings**. You do not paste the value again.

## The config

The format is the same `mcp` section of OpenCode's config that My MCP config uses. The shared list takes remote servers only. An entry with a `url` is enough: Fleet saves it as `"type": "remote"` with `"oauth": false`. The full shape is:

```json
{
  "a-remote-server": {
    "type": "remote",
    "url": "https://example.com/mcp",
    "oauth": false,
    "headers": {
      "Authorization": "Bearer {secret:my_token}"
    }
  }
}
```

Each service page carries the entry for that service: [Set up Atlassian's MCP server for Confluence and Jira](guides/services/atlassian). Figma's working server is local, so it cannot go on this list; [Set up Figma's MCP server for your sessions](guides/services/figma) explains the alternative.

The shared list is stricter than your own:

- **Every entry is a remote server with a `url`; `"oauth": false` is the only accepted value.** A URL-only entry gets both defaults, so you do not write them by hand. The shared list never starts a program on a machine, so a `local` entry is refused.
- **A `{secret:name}` must name a secret saved on Secrets with Give it to every session.** A key on My secrets, or a team secret without that choice, is refused, and the problem lists the names you can use.
- **Never paste a key into the list.** It is refused, as on My MCP config.
- **Don't reuse the name of Fleet's own tools server.**

## Who gets what

| Server | Who gets it |
|---|---|
| On **Shared MCP servers** | Every session anyone opens, and every run Fleet starts on its own. |
| On a person's **My MCP config** | Only the sessions that person opens. Runs never get it. |

When both lists, or the machine's own config, name a server the same, the shared one wins. The session lists the shared servers first, under `fleet · shared MCP servers`, and marks the other one `skipped`. A shared server that fails never stops the session: the session names it, with the reason, and goes on without it. The Shared MCP servers page shows each server's newest start result, with that reason, so the failure is visible there too.

> **Careful:** A key with **Give it to every session** reaches every session and every run, whoever started it. Use a key with only the access the whole team should have, such as a read-only token.

Next: Use your own MCP servers in sessions (guides/your-tools/personal-mcp) · Team secret or personal secret? (guides/secrets/team-or-personal)

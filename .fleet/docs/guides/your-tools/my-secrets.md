# Keep your own tokens in My secrets

When you are done you will have a personal token stored in Fleet, ready for your MCP config to use by name, and seen by nobody else.

**My secrets** holds tokens for the tools in your own MCP config: an Atlassian API token, a Figma personal access token. They are yours: nobody else can list or use them, only sessions you open receive them, and the model provider never sees their values.

A credential a task needs for everyone who works on it belongs on the team's **Secrets** page instead. See [Team secret or personal secret?](guides/secrets/team-or-personal).

[Open My secrets](#settings:my-secrets)

## Add one

1. [you] **Open Settings › My secrets and press Add a secret.** It is under **You** in the Settings menu.
2. [you] **Name it.** For example `ATLASSIAN_TOKEN`. The form tells you as you type if a name will not do, and shows the reference your config will use: `{secret:ATLASSIAN_TOKEN}`.
3. [you] **Paste the value and press Save secret.** It is stored encrypted. From then on Fleet shows only its last four characters. Fleet does not check the value with the vendor, so paste it carefully.
4. [you] **Use it in My MCP config.** Write `{secret:ATLASSIAN_TOKEN}` where the server needs the token. See [Use your own MCP servers in sessions](guides/your-tools/personal-mcp).
5. [fleet] **Your sessions get it.** A session you open fetches the token when it needs it, and only for a server your config names it in. No other session can.

## Replace or delete one

Each secret's row shows its name, the last four characters of its value after an ellipsis (for example `…9f2a`), and the day it was saved. The value itself is never shown again.

- **Replace** takes a new value; the name stays.
- **Delete** removes it. Fleet refuses while your MCP config still uses it, and names the entries that do. Take it out of the config first.

A personal secret has no settings of its own: it is yours, and only sessions you open receive it. The **Give it to every session** setting belongs to a team secret on **Settings › Secrets**, where **Change settings** on its row turns it on or off without asking for the value again.

> **Careful:** A row that reads **Can't be read — enter it again** holds a value Fleet can no longer decrypt, so no session receives it. Press **Replace** and paste the value again.

## Your sessions become private

A session that holds your personal tools is **private**: only you can watch it or resume it. A colleague who opens it is told to open their own session.

Next: Use your own MCP servers in sessions (guides/your-tools/personal-mcp) · Team secret or personal secret? (guides/secrets/team-or-personal) · Create and revoke API keys (guides/your-tools/api-keys)

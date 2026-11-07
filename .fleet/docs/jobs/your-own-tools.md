# Connect your own tools

Bring what you already use into Fleet, and take Fleet into what you already use. This path sets up your own MCP servers in the sessions you open, stores the tokens they need, and hands a credential to a session that needs one.

## The big picture

- **My MCP config.** Your own MCP servers, such as Confluence or Figma, added to every session you open.
- **My secrets.** Your personal tokens. Only your sessions can use them, and your MCP config names them instead of holding them.
- **Secrets.** Credentials the work needs, such as a vendor API or a test login. Your whole team sees their names, and a session gets one only when you attach it.
- **API keys.** A key that lets a tool on your own computer act as you in Fleet.

There are two directions. Into Fleet: your MCP config names a token as `{secret:name}`, and Fleet puts the value in when it hands the config to your session. Runs the fleet dispatches on its own never get your servers, and a session that holds them becomes private to you. Servers every session should have, runs included, go on the team's list, **Shared MCP servers**, instead. To pick between the two kinds of secret, ask one question: does the work need it, or do you?

Out of Fleet: an API key lets Claude Code or another AI tool on your own computer read, file and move issues through Fleet in your name, with no tracker key on your machine. You can also load the repository's Fleet commands into your own Claude Code.

## Read these in order

1. **Use your own MCP servers in sessions** (guides/your-tools/personal-mcp): Give the sessions you open your own MCP servers, such as Confluence, Jira or Figma, with your tokens kept on My secrets.
2. **Give every session the same MCP servers** (guides/your-tools/shared-mcp): Save one list of MCP servers, such as Confluence, on Settings › Shared MCP servers, so every session and run gets them, with their keys on Secrets.
3. **Keep your own tokens in My secrets** (guides/your-tools/my-secrets): Store the personal tokens your own MCP servers need, such as an Atlassian or Figma token, where only your sessions can use them.
4. **Team secret or personal secret?** (guides/secrets/team-or-personal): Decide whether a credential goes on Settings › Secrets, for the work, or on Settings › My secrets, for your own tools, and store it there.
5. **Give a session a secret** (guides/secrets/attach-a-secret): Hand a stored credential to every session on a task, or to one session that is already running, and take it back when you are done.

## When you need it

- **Connect your own AI tool to Fleet** (guides/your-tools/connect-your-terminal): Let Claude Code, Cursor, VS Code or opencode on your own computer read, file and move issues through Fleet, as you, with nothing installed.
- **Create and revoke API keys** (guides/your-tools/api-keys): Make a key that lets a tool on your own computer act as you in Fleet, see when each key was last used, and revoke one you no longer trust.
- **Use Fleet's commands in your own Claude Code** (guides/your-tools/fleet-commands-locally): Load the repository's Fleet commands from .fleet/ into Claude Code on your own computer, for one session, for yourself, or for the whole team.
- **Set up Atlassian's MCP server for Confluence and Jira** (guides/services/atlassian): Connect Confluence and Jira to your Fleet sessions with an Atlassian API token or service-account key, after an admin turns on API-token sign-in.
- **Set up Figma's MCP server for your sessions** (guides/services/figma): Connect Figma to your Fleet sessions with a personal access token and the Framelink server, and why the server stays in your own config.

---
- **secret**: A password, token or key Fleet stores for you and hands only to the sessions you attach it to.
- **API key**: A key you create in Settings that lets your own tools, such as a terminal agent, call Fleet as you.

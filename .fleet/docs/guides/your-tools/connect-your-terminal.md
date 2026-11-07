# Connect your own AI tool to Fleet

When you are done, the AI tool on your own computer can ask Fleet "what's in my queue?", read and file issues, comment and ask questions, in your name, without any tracker key on your machine.

Fleet serves its tools at a web address. Your tool calls that address with an API key you create, read from a file only you can read. Nothing is installed, and the key never sits in your tool's settings or on a command line.

The place to do this is **Settings › Connect your tools**. It fills in your Fleet's real address and walks the three steps below.

[Open Connect your tools](#settings:connect)

1. [you] **Get a key.** Under **Your key**, pick one of your keys from **Use**, or press **Create a key**. Fleet shows a new key once. See [Create and revoke API keys](guides/your-tools/api-keys).
2. [you] **Save it to a file.** Copy the command under the key and run it in a terminal; on Windows, copy the one marked **On Windows, in PowerShell** and run it in PowerShell. Paste the key when it waits (nothing is shown) and press Enter. The key lands in a file named after your Fleet's address, `~/.config/fleet/<Fleet address>.headers.json`, readable only by you. Each Fleet you use gets its own file, so saving a second Fleet's key never replaces the first.
3. [you] **Pick your tool and add Fleet to it.** Choose the tab for your tool and copy its entry. Each tab says where the entry goes (see below).
4. [you] **Check it works.** Restart or reconnect your tool and ask it *what's in my Fleet queue?*. Press **Check again**.
5. [fleet] **The key turns connected.** Under **Check it works**, the key reads **connected**, when it was last used, and which tool and version connected. Until then it reads **not used yet**.

The command from the second step, for reference, for a Fleet at `fleet.example.com`. It reads the key without echoing it:

```bash
mkdir -p ~/.config/fleet && (umask 077 && read -rs k && printf '{"Authorization":"Bearer %s"}\n' "$k" > ~/.config/fleet/fleet.example.com.headers.json)
```

On Windows `~` is your user folder, the same folder Git Bash calls `$HOME`, so every tool finds the same file. The PowerShell command saves it there too, without a byte-order mark so every tool can read it.

## Where each tool's entry goes

| Tool | Where | Where the key comes from |
|---|---|---|
| **Claude Code** | A command you run once; it adds Fleet for every project. | Claude Code reads your Fleet's key file each time it connects. |
| **Cursor** | `~/.cursor/mcp.json`, or `.cursor/mcp.json` in one project. | A line in your shell profile reads the key from the saved file into `FLEET_KEY`. The tab gives you the line. |
| **VS Code** | **MCP: Open User Configuration**, or `.vscode/mcp.json` in one project. | VS Code asks for the key the first time and keeps it in its own secure storage. |
| **opencode** | `~/.config/opencode/opencode.json`, or `opencode.json` in one project. | A one-line file beside the key file, `~/.config/fleet/<Fleet address>.opencode-bearer`, written from the saved key by a command the tab gives you. |
| **Other (JSON)** | Your tool's own MCP list. | In the file itself: replace the placeholder with your key. |

The Claude Code command looks like this, with your Fleet's address filled in on the page:

```bash
claude mcp add-json --scope user fleet '{
  "type": "http",
  "url": "<your Fleet address>/api/tools/v1/mcp",
  "headersHelper": "cat \"${FLEET_HEADERS_FILE:-$HOME/.config/fleet/<Fleet address>.headers.json}\""
}'
```

> **Careful:** **Cursor** only sees `FLEET_KEY` when it is started from a terminal that has it: run `cursor` from a new terminal. Opened from the Dock or the Start menu, it will not find your key. With **Other (JSON)** the key sits in the file: keep it `chmod 600` and never commit it.

## Not supported yet

**Claude Desktop** and **claude.ai** can only connect to tools that offer a sign-in, which Fleet does not offer yet. Use Claude Code, Cursor, VS Code or opencode.

## Replace a key

Create a new key, save it with the same command (for opencode, re-run its bearer-file command too), then revoke the old key on **API keys**. Your tool picks up the new key from the file on its next call.

## When Fleet is not answering

Your tool simply has no Fleet tools until the address answers again: Claude Code marks the server failed, opencode drops it. Nothing on your computer is broken. Reconnect once Fleet is back.

Next: Create and revoke API keys (guides/your-tools/api-keys) · Use Fleet's commands in your own Claude Code (guides/your-tools/fleet-commands-locally) · Use your own MCP servers in sessions (guides/your-tools/personal-mcp)

---
- **API key**: A key you create in Settings that lets your own tools, such as a terminal agent, call Fleet as you.

# Use Fleet's commands in your own Claude Code

When you are done, typing `/` in Claude Code on your own computer lists the same Fleet commands the fleet's agents run, such as filing a task or fixing a bug.

## Where the commands live

Fleet writes its commands into your repository's `.fleet/` folder as a Claude Code plugin. They are ordinary files under version control. Claude Code does not load `.fleet/` on its own, so your everyday sessions stay as they are until you opt in. Sessions Fleet opens on its own machines get the commands without any of this.

A command's name follows its file: `.fleet/commands/<namespace>/task/create.md` is the command below, for example.

## What Fleet tells the session

`fleet commands sync` also writes `.fleet/AGENTS.md`: what Fleet is, where the knowledge base lives and where Fleet's own docs are. A Fleet session reads it from the checkout, so it knows Fleet even when your `Fleet's own value (set your own)` says nothing about Fleet. When you load the plugin, Claude Code prints that file at the start of the session too. You never edit your `Fleet's own value (set your own)` to get this, and the next sync updates what a new session is told.

`task:create` — File one well-formed Type:task tracker issue saying what the work is, and stop — the checker decides everything else.

## Opt in

| | One session | Just you, every time | The whole team |
|---|---|---|---|
| How | Start Claude Code with `claude --plugin-dir .fleet` | Add the block below to `.claude/settings.local.json` | Add the same block to `.claude/settings.json` and commit it |
| Committed? | No | No, the file stays on your computer | Yes |
| Works in `claude -p` (headless) | Yes | No, use the flag | No, use the flag |

The block for the settings files. Replace `<namespace>` with your repository's command namespace (the part after `/` and before the first `:` in a command's name):

```json
{
  "extraKnownMarketplaces": {
    "fleet": { "source": { "source": "directory", "path": "./.fleet" } }
  },
  "enabledPlugins": { "<namespace>@fleet": true }
}
```

A repository set up with `fleet init` usually has the team block already.

## Let the commands reach Fleet

Commands that file, read or move issues do it through Fleet's tools, so connect Claude Code to Fleet first. See [Connect your own AI tool to Fleet](guides/your-tools/connect-your-terminal). With that done, a task you file from your laptop appears in your Cockpit under **Filed by me**, filed through Fleet in your name, and no tracker key is needed on your computer.

## Change a command for your repository

> **Careful:** Never edit files under `.fleet/` in place: the next sync undoes the edit. Put your version at the same path under `.fleet/local/`, for example `.fleet/local/commands/<namespace>/<verb>.md`, and the sync writes it in place of Fleet's.

Next: Connect your own AI tool to Fleet (guides/your-tools/connect-your-terminal) · Commands and tools (concepts/commands-and-tools)

---
- **plugin**: A folder Claude Code can load to add commands to a session; Fleet writes its commands into `.fleet/` as one.

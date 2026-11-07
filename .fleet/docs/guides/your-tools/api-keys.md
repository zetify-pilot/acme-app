# Create and revoke API keys

When you are done you will have an API key saved where your tools can read it, and you will know how to retire it.

An API key is how Fleet knows a tool is acting as you. Fleet keeps only a fingerprint of it, so it can show you a key **once** and never again. A key you lose is a key you replace.

[Open API keys](#settings:api-keys)

## Create a key

1. [you] **Open Settings › API keys and press Create key.** The dialog is titled *Create an API key*.
2. [you] **Name it and choose its kind.** Name it after where it will live (*laptop*, *work mac*). Then choose **Your own key**, which acts as you; **CI key**, for an automated job that files through Fleet; or **Integration key**, which can only read Fleet, for another system (it also asks for the address where that system publishes its signing keys).
3. [you] **Press Create key.** The key is shown once.
4. [you] **Save it straight away.** For your own key, the dialog gives three steps, each with **Copy**: the key, a command that saves it to this Fleet's own file, `~/.config/fleet/<Fleet address>.headers.json` (it reads the key without showing it; Windows gets a PowerShell one too), and the command that adds Fleet to Claude Code.

> **Careful:** Never paste a key into a chat, a ticket or a file you commit. Save it with the command the dialog gives you, which keeps it off the screen and off the command line.

For Cursor, VS Code or opencode, go on to [Connect your own AI tool to Fleet](guides/your-tools/connect-your-terminal).

## Read the list

Each row shows the key's name and the first characters it starts with, its **Purpose**, when it was **Created**, when it was **Last used**, when it **Expires**, and its **Status**: **active**, **expired** or **revoked**. Search by name, prefix or purpose, filter by **Status** or **Purpose**, and sort. Revoked and expired keys are hidden until you ask for them.

Every key you create expires; its expiry date is on its row. A key made before scopes existed carries every scope and never expires until its owner rotates it, so rotate old keys.

## Revoke a key

Press **Revoke** on the key's row and confirm. The key stops working at once: the next call that presents it is refused, and your tool says the key is no longer valid. The row stays, marked **revoked**, so you can see which key stopped.

> **Careful:** A revoked key cannot be brought back. If a tool still uses it, create a new key, save it to the same file, and the tool picks it up on its next call. Revoke a key as soon as the computer that holds it is lost, sold or retired.

Next: Connect your own AI tool to Fleet (guides/your-tools/connect-your-terminal) · Keep your own tokens in My secrets (guides/your-tools/my-secrets) · Send bug reports between Fleets with a report key (guides/team/report-keys)

---
- **API key**: A key you create in Settings that lets your own tools, such as a terminal agent, call Fleet as you.

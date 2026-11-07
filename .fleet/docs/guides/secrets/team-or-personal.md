# Team secret or personal secret?

When you are done your credential will be stored in the right one of Fleet's two places, encrypted, and shown from then on only by its last four characters.

Fleet keeps two kinds of secret, for two different jobs. Ask one question: **does the work need it, or do you?**

| | Secrets | My secrets |
|---|---|---|
| Where | Settings › Secrets, under **Access** | Settings › My secrets, under **You** |
| What it is for | A system the work has to reach: a vendor API, a test login, a package registry | A token for a tool in your own MCP config: an Atlassian or Figma token |
| Who sees it | Everyone who signs in to your Fleet sees its name, description and last four characters | Only you |
| Which sessions get it | Those you attach it to: every session on a task, or one running session. A secret named `build-…` can also go to every build run in a repository, and one named `qa-…` to every `/qa` run. One saved with **Give it to every session** goes to every session and run, as a file in the session's secrets folder | Only sessions you open, through your MCP config |
| How a session reads it | The file `$FLEET_SECRETS_DIR/NAME`, listed in `index.json` with its description | Your MCP config names it as `{secret:NAME}` |

## Store a team secret

1. [you] **Open Settings › Secrets and press Add a secret.** A dialog opens with three fields: **Name**, **Description** and **Value**.
2. [you] **Name it.** The name becomes a file name, so the dialog tells you as you type if it will not do, and offers a fix.
3. [you] **Describe it.** **Description** is optional but worth it: agents read it to know what the secret is for. Never put the value here.
4. [you] **Paste the value and press Save secret.** Fleet stores it as you paste it; it cannot check it with the vendor.
5. [you] **Attach it where it is needed.** A stored secret reaches no session until you attach it. See [Give a session a secret](guides/secrets/attach-a-secret).

On the Secrets page (#settings:secrets):
1. **Add a secret** opens the dialog.
2. Each stored secret: its name and description, the last four characters of its value after an ellipsis (for example `…9f2a`), **Used by**, and who last changed it and when. Its **⋯** menu has **Change settings**, **Edit description**, **Replace value** and **Remove…**, which deletes it.

[Open Secrets](#settings:secrets)

**Used by** says what holds each secret: how many tasks, how many live sessions, and which repositories' runs. **Not attached** means nothing does.

## Store a personal secret

On **Settings › My secrets**, press **Add a secret**, name it, paste the value and press **Save secret**. Then use it in your MCP config. The full walk-through is [Keep your own tokens in My secrets](guides/your-tools/my-secrets).

## Change or remove one

**Change settings** on a secret's row changes who receives it, without asking for, showing or changing the value. Tick **Give it to every session** to give it to every session and every run Fleet starts, or untick it to go back to giving it only to the tasks and sessions you attach it to. The chip on the row updates. A secret that becomes shared is then accepted by a Shared MCP entry, and it stops being attached to individual tasks, sessions and repositories, because a shared key is given to every session instead. A secret that stops being shared can be attached to tasks and sessions again.

**Replace value** takes a new value: sessions started from then on get it, while one already running keeps the old one. The name and the settings stay as they were. The **Remove…** item deletes the secret.

Each settings change is recorded on the row with the person who made it and the day, the same way a save is.

> **Careful:** Fleet refuses a value that looks like a credential it already holds or issues, such as a tracker key, a model provider key, a GitHub token or a private key, and says where that credential belongs. And a row marked **Can't be read — replace it** reaches no session until you replace its value.

Next: Give a session a secret (guides/secrets/attach-a-secret) · Keep your own tokens in My secrets (guides/your-tools/my-secrets) · Use your own MCP servers in sessions (guides/your-tools/personal-mcp)

---
- **secret**: A password, token or key Fleet stores for you and hands only to the sessions you attach it to.

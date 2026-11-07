---
title: "Review what a session did"
kind: guide
for: [developer]
summary: "Read a session's branch and pull request, its changes, the ports it serves and the files in its checkout, without leaving Fleet."
sources:
  - packages/fleet-service/src/fleet_service/api/static/cockpit-branch.js
  - packages/fleet-service/src/fleet_service/api/static/cockpit-portsfiles.js
  - packages/fleet-service/src/fleet_service/api/static/cockpit-metrics.js
  - packages/fleet-service/src/fleet_service/api/portproxy.py
  - packages/fleet-service/src/fleet_service/api/sessioninspect.py
minutes: 4
---

:::lede
When you are done you will be able to tell, from the Terminals page, what a session changed, whether its pull request is green, and what it is serving, and open any of it.
:::

## The branch line

Every session works on a branch of its own. Its header shows a branch line such as `⎇ ws/1a2b3c4d · #123 ◐ CI 31/44`:

| Mark | Means |
|---|---|
| `⎇ ws/…` | The session's branch. Hover for the commit it is at. |
| `↑3` `↓2` | Commits ahead of, and behind, `origin/main`. |
| `●4` | Files changed and not committed yet. |
| `#123` | The branch's pull request. Click to open it on GitHub. |
| `◐ CI 31/44` / `✓ CI 44/44` | Checks still running, or all passed. |
| `conflict`, `draft`, `✓ merged`, `closed` | The pull request's state. |
| `no GitHub credential` | Fleet holds no GitHub access to read the pull request. Ask whoever set up Fleet. |

## The dock

In the **Focus** layout, or with a session open full screen, the :term[dock] sits beside it: the machine's figures on top, then tabs. Hide or show it with :kbd[⌘.].

::screen{route="terminals" pins="dock"}
1. The dock: the machine's figures, then the **Terminal**, **Changes**, **Ports**, **Files**, **Uploads** and **Secrets** tabs.

:::steps
- [you] **Open the pull request.** **View PR**, in the session's header (in Focus, under its **⋯** menu), opens the pull request on GitHub. It appears once the branch has one.
- [you] **Read the changes.** **View changes** opens the **Changes** tab: every file the session changed since it branched from `origin/main`, committed or not, with a diff. Fleet asks the machine for it, so it can take a moment to arrive. An edit in the conversation also offers **Show the change**, a diff of just that edit, with a link to the file in the **Changes** tab.
- [you] **Open what it serves.** The **Ports** tab lists the ports the session's machine is serving, the session's own first. **Copy** gives you a `fleet-port-forward` line that puts the port on your own computer's `localhost`, a database too; see [Reach a session's port from your computer](guides/sessions/reach-a-port). A web port also has **Open ↗**, which opens it in a new tab on its own address, signed in as you. Every opening is recorded. Only a port served on the machine itself is listed: a database inside a container network must be published to the machine first.
- [you] **Browse its files.** The **Files** tab shows the session's checkout, read-only. Open a file to read it with line numbers, or press **Insert @path** to mention it in your next message.
- [you] **Finish.** When the agent's turn is done and a pull request exists, **View PR** and **Close session** appear under the conversation.
:::

:::callout{kind="tip"}
The **Terminal** tab is a shell on the session's machine, starting in the session's folder. See [Open a shell on a machine](guides/sessions/shell-on-a-machine). The **Secrets** tab is covered in [Give a session a secret](guides/secrets/attach-a-secret).
:::

::cards{links="guides/sessions/reach-a-port, guides/sessions/take-over-and-restore, guides/secrets/attach-a-secret"}

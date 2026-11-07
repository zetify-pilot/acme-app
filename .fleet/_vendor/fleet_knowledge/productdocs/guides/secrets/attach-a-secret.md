---
title: "Give a session a secret"
kind: guide
for: [developer]
summary: "Hand a stored credential to every session on a task, or to one session that is already running, and take it back when you are done."
sources:
  - packages/fleet-service/src/fleet_service/api/secretattach.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - packages/fleet-service/src/fleet_service/api/static/cockpit-secrets.js
  - packages/fleet-daemon/src/fleet_daemon/secretsdir.py
minutes: 4
---

:::lede
When you are done the session that needs a credential will have it as a private file, for as long as the session lasts, and no other session will.
:::

A :term[secret] reaches a session only when you attach it. Store it once on **Settings › Secrets** first (see [Team secret or personal secret?](guides/secrets/team-or-personal)), then pick the way that fits the work.

## Attach it to a task

Use this when the work on one issue needs the credential, whether a fleet run does it or you do.

:::steps
- [you] **Open the issue's page.** Find the card **Attached for this task**. It lists what every session on this task is given.
- [you] **Press Attach a secret… and pick one.** The stored secrets appear as buttons, each with its last four characters.
- [fleet] **Every session on the task gets it.** A run on this issue, and a terminal you open from the issue, receive it for as long as they last.
- [you] **Detach it when you are done.** **Detach** on its row takes it back: a running session loses it shortly after, and no new session gets it.
:::

## Attach it to a session that is already running

Use this for your own session, including one that is about no issue at all.

:::steps
- [you] **Focus the session and open the dock's Secrets tab.** Use the **Focus** layout, or open the session full screen. The tab is headed *Secrets in this session*.
- [you] **Tick the secret.** The list shows what the session holds first, then *Other stored secrets*. Type in *Find a secret…* to search them.
- [fleet] **It reaches the session in seconds.** The line above the list says how many are attached. Untick to take one back.
:::

::screen{route="terminals" pins="dock"}
1. The dock beside the focused session. Its **Secrets** tab lists every stored secret, one tick from the session.

A secret the session holds through its task shows as a locked row, *detach it on the task*: take it away on the issue's page, not here.

You can also pick secrets when you open a session, in the **Secrets** field of the form. See [Open a session](guides/sessions/open-a-session).

## What the session sees

Each secret is a file, `$FLEET_SECRETS_DIR/NAME`, in a private folder that is removed when the session ends. `$FLEET_SECRETS_DIR/index.json` lists the names and descriptions, never the values. The value is never in the session's environment or on a command line. A command reads the file straight into the program that needs it, and never prints it. For example, the JFrog CLI takes its token on standard input:

```bash
jf config add fleet --url "$JF_URL" --access-token-stdin --interactive=false < "$FLEET_SECRETS_DIR/build-jfrog-token"
```

Fleet shows which secrets a run was given, by name and last four characters, never the value.

:::callout{kind="careful"}
Take a secret back the moment something looks wrong: detach it on the task, or untick it in the dock. The session's next attempt to read it is refused. Then replace the value on Settings › Secrets, because a session that already read it has seen it.
:::

::cards{links="guides/secrets/team-or-personal, guides/sessions/review-a-sessions-work, guides/team/repositories"}

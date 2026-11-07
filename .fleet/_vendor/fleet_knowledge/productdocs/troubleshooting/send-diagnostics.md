---
title: "Send Fleet's team a diagnostics bundle"
kind: troubleshooting
for: [owner, admin]
summary: "When the other pages do not explain a problem, download one diagnostics file from System and send it to Fleet's team, or report a bug straight from the app."
sources:
  - packages/fleet-service/src/fleet_service/api/diagnostics.py
  - packages/fleet-service/src/fleet_service/dispatch/diagnostics.py
  - packages/fleet-service/src/fleet_service/dispatch/reportsend.py
  - packages/fleet-service/src/fleet_service/api/static/app.js
  - knowledge/journeys/flows/report-a-fleet-problem-to-zetify.md
minutes: 4
---

:::lede
When something is wrong with Fleet itself and the other troubleshooting pages do not explain it, Fleet's team needs to see what your Fleet saw. One file from the System page carries it. You read it, and you send it.
:::

## What you see

| What you have | What to use | What happens |
|---|---|---|
| A problem with the whole fleet that the System page cannot explain | **Download diagnostics** | You get one file, and send it to Fleet's team yourself |
| One thing on one page is broken | **Report a bug** | If reports are switched on, it reaches Fleet's team by itself |
| "Reports can't be sent" on Send reports | The connection code is missing, refused or expired | An admin saves a working code |

## Download diagnostics

The last section of the System page is headed "Send Fleet's team a diagnostics bundle".

::action[Open System]{route="system"}

:::steps
- [you] **Press Download diagnostics.** At the foot of the System page.
- [you] **Choose how far back.** "How far back" offers 1h, 6h, 24h, 3d or 7d; 24h is preselected. Pick a span that covers when the problem started.
- [you] **Press Download.** The button reads "Preparing the file…" while Fleet builds it. Only one file is built at a time.
- [fleet] **The file arrives.** A file named `fleet-diagnostics-` and a time stamp, ending `.tar.gz`. Your download is recorded under your name.
- [you] **Read it before you send it.** Then send it to Fleet's team the way you normally reach them. Fleet does not send it for you.
:::

**What is in it:** the System reading; recent runs, claims, moves between positions, pending tracker writes, verdicts and stats; every machine's state and metrics; the configuration with every secret value removed; and the control plane's own warnings and recent log lines.

**What is not:** secret values and money figures are removed before the file is written. Your cluster's own state is not in it, because Fleet has no access to your cloud account. Worker machines' logs are not in it, because Fleet does not ask the machines for anything; if Fleet's team needs one, open a shell on that machine from Machines and read it there.

:::callout{kind="careful"}
The file may contain code and issue text: runs and logs quote what the agents read and wrote. Read it before you send it, and send it only to people who may see that code.
:::

## Report a bug from the app

For a problem you can point at on one page, **Report a bug** is quicker. Fleet takes a screenshot before the dialog opens; you type a title and what happened, and the screenshot, the browser's recent log, the page address, the browser, the window size and Fleet's release are attached for you. The report is kept on your Fleet, and, when sending is switched on, delivered to Fleet's team by itself, later if they cannot be reached right now.

Sending is switched on by an admin on [Settings › Send reports](app:settings:reports).

:::steps
- [you] **Get a connection code.** Fleet's team gives your admin one.
- [you] **Paste and save it.** Paste it on Send reports and press **Check and save**.
- [you] **Switch sending on.** Tick "Send bug reports to" your Fleet provider. The page then shows when the code expires and when the last report was sent.
:::

If the page reads "Reports can't be sent", reports are waiting and will be sent once a working code is saved; nothing is lost. When the code's **Expires** date shows how many days are left, ask Fleet's team for a new one before it runs out. If your Fleet's operator has turned sending off, the Send reports page is not shown at all.

::cards{links="troubleshooting/fleet-paused, guides/daily/file-work"}

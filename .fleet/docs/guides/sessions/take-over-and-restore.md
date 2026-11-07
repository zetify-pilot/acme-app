# Take a session over, or bring one back

When you are done you will be able to pick up a session from another tab or computer, give a terminal a window of its own, and bring back a session you closed by mistake.

## One view at a time

A session can be watched in one place at a time. Open it in a second tab or on another computer and the first place says *This session is open in another tab or window.* The session itself is fine and keeps running.

1. [you] **Press Take over here.** The view moves to this tab. The other tab lets go and says the session was opened elsewhere.
2. [fleet] **Nothing is lost.** The conversation is kept on the machine and replayed to the new view, and queued messages travel with the session.

On the Terminals page (#terminals):
1. A session's tile. When another tab holds the session, the line over it offers **Take over here**.

## Give a terminal its own window

A terminal pane (a plain shell, the agent on a terminal screen, or a shell on a machine) has **Pop out** in its corner. The view moves to a new browser window; where the pane was, the page says it is open in its own window. **Dock back** in that window closes it and the pane returns. For a machine shell, **Bring it back** does the same from the page.

Agent sessions shown as a conversation have no **Pop out**.

## Find a session you closed

Closing a session ends it on its machine. When you watch it close, a message offers **Resume** at once, in case the close was a mistake.

1. [you] **Open the Closed list.** On the Terminals page, under your sessions, the line **Closed · N** is folded. Press it or **Show all**.
2. [you] **Find it.** Search with *Find a closed session*. Sessions are grouped by the day they ended, newest first, with who closed each one.
3. [you] **Open it or resume it.** A row opens the session's own page: its conversation, read-only, and why it ended. **Resume** starts it again on the same machine, with the same conversation, folder and branch. The command it was opened with is not run again.

> **Careful:** Only agent sessions can be resumed. Closing a terminal ends its shell, so there is nothing to start again. A session that holds someone's personal tools can be watched and resumed only by the person who opened it.

## A session lost with its machine

If a machine goes away while it holds your session, the session is listed under **Lost with their boxes** on the **Workstation** page rather than vanishing.

Next: Open a session (guides/sessions/open-a-session) · Arrange your sessions and use the keyboard (guides/sessions/layouts-and-shortcuts) · A session will not start, or stopped responding (troubleshooting/session-problems)

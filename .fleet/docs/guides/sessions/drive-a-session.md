# Drive an agent session

When you are done you will know every move the message box under an agent session offers: sending, queueing, mentioning files, running the agent's own commands, stopping a turn and retrying one.

## The message box

Under every agent session's conversation sits one line that grows as you type: *Tell the agent something — it reads it at its next step*. Enter sends, Shift Enter starts a new line, and the small **↵** button sends too. What you have typed but not sent is kept for that session, so a reload or a sign-in brings it back.

When the session asks you something, the question appears directly above the message box, so the question and the place to answer it are together.

On the Terminals page (#terminals):
1. The message box of the focused session: type, mention files with `@`, run commands with `/`.

## Give a session your files

In the focus view of a session you opened, drag one or more files onto the session. Each file uploads to the session's own folder on its worker, and its path appears in the input line, with a space on each side. Nothing is sent: write your message around the paths and press Enter when you are ready, and the agent reads the files when your message reaches it.

The **Uploads** tab, beside Ports and Files, lists the files the session holds, with each file's name, size, who uploaded it and when. **Insert path** writes that file's path into the input line again, and **Remove** deletes the file from the worker and from the list.

A session takes up to 1000 files, 200 MB each and 1 GB in all, and refuses archives such as zip files. Drag a whole folder onto the session, or use **Upload files** or **Upload folder** in the Uploads tab: a folder keeps its structure, so `docs/a/b.md` arrives as `docs/a/b.md`, and a folder over a limit is refused whole before anything is sent. Only the person who opened the session can add or remove its files.

Files are deleted from the worker when the session closes, and after 14 days at most even if the session stays open. Deleting a file does not undo what the agent has already read: that stays in the session's transcript and has already reached the model provider.

A worker that runs its sessions in boxes, or one that has not been updated, shows no drop target.

## Every move, in order

1. [you] **Send a message.** Type and press Enter. The agent reads it at its next step.
2. [you] **Send more while it works.** A message sent during a turn is **queued** on the machine and shown as a chip above the message box: *queued — waiting for the agent to finish this turn*. Each chip has **Edit** and **×** until its turn starts. The queue lives on the machine, so another tab or another computer shows the same one.
3. [you] **Jump the queue if you must.** **Send now (interrupts)** on a chip stops the running turn and sends that message next.
4. [you] **Point it at a file.** Type `@` and the start of a name. Fleet asks the machine for matching files in the session's checkout; pick one and `@path` is written into your message. The file goes with the message when you send it. Delete the mention first and nothing is attached. The **Files** tab's **Insert @path** writes the same mention.
5. [you] **Run one of the agent's commands.** Start a message with `/`. The list shows the commands this agent offers, including your repository's own, and narrows as you type. Pick one, add what it asks for, and send.
6. [you] **Stop a turn.** While the agent works, an **Esc** chip sits at the right of the message box. Click it or press Esc in the session. The agent ends its turn and the conversation shows *Stopped by you*. The session stays open.
7. [you] **Retry a refused turn.** When the agent refuses a turn, its card says why and offers **Retry**, which sends the same message again as a new one.

> **Careful:** **Esc** asks the agent to stop, and the agent decides when its turn ends. A stuck turn can take a while to stop. The chip reads *Stopping…* until it has.

## When the agent is done

Once a turn finishes and the session's branch has a pull request, two buttons appear under the conversation: **View PR** opens it on GitHub, and **Close session** ends the session. See [Review what a session did](guides/sessions/review-a-sessions-work).

## A terminal session is different

A terminal (a plain shell, or the agent on a terminal screen) has no message box. You type straight into the screen, and Esc belongs to the terminal. Each terminal has **Find** and **Pop out** in its corner.

Next: Review what a session did (guides/sessions/review-a-sessions-work) · Arrange your sessions and use the keyboard (guides/sessions/layouts-and-shortcuts) · Take a session over, or bring one back (guides/sessions/take-over-and-restore)

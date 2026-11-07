# Sessions: runs, terminals and shells

Everything an agent does in Fleet happens in a session on a machine. Some sessions the fleet starts by itself to work an issue. Others you open from the browser and drive yourself. They share the same machines and the same rules.

## Three kinds

| | Dispatched run | Your session | Shell on a machine |
|---|---|---|---|
| Who starts it | The fleet, from a queue | You, from **Terminals** | You, from the machine's **Shell** button |
| What runs in it | The command for the issue's step | An agent, or a plain terminal, in a repository's checkout | A shell as the machine's login user, in its home folder |
| Who drives it | Nobody: it runs alone | You | You |
| Takes a seat | A dispatch seat | An interactive seat | None |
| Where to see it | **Runs**, **Queue** | **Terminals**, **Workstation** | The shell's own window |

A session you open is a workstation session. It is not a run: nothing was dispatched and nothing is being attempted on an issue. It keeps running whether or not anyone is watching.

## Open a session

On **Terminals**, press **+ New session**. Pick the repository and the model, and give it a title, a branch and a first prompt if you like. A blank branch starts a new branch from the main branch. If you would rather not run an agent, choose **Open a plain terminal instead**.

On the Terminals page (#terminals):
1. **+ New session** opens one on a machine with a free seat.
2. Each session is a tile. It says when it is waiting on you.
3. Choose how the sessions are laid out.
4. Type to the agent here.

[Open Terminals](#terminals)

## What a session gives you

- **Its own branch.** A session starts on a branch of its own. The machine reads that branch every cycle so the work is not lost, and the page shows the branch's pull request and how its checks stand.
- **A transcript that survives.** An agent session's recent output is kept on the machine and replayed to anyone who opens it later, even after the machine's worker restarts.
- **Ports and files.** The **Ports** and **Files** tabs list what the session is serving and its working tree. An HTTP port opens in a new browser tab behind Fleet's login.
- **A waiting signal.** A session that has asked you something says so on the page, and in the Cockpit.
- **Fleet's tools, with no tracker key.** A session gets a key to Fleet's tools in a private file. It files, reads and moves issues through Fleet, never with a tracker credential of its own.
- **Live pull request status.** When a pull request is named in your message or in a tool's output, the agent is shown its live state (open, blocked, conflicting, queued or merged, with its checks) so it never reasons from a stale picture. It works in Claude Code and OpenCode sessions alike, reads GitHub through the machine's own `gh` login or `GH_TOKEN`, and stays silent when there is none.

## Look in on a run

A dispatched run's thread can be opened the same way as your own session, so you can watch what it is doing. When a run has finished, its drawer offers **Talk to it**: an agent session that starts out knowing what the run concluded, for asking questions about it.

## A shell on the machine

Sometimes you need the machine itself, not a session. A machine's **Shell** button opens a shell as the machine's login user. It is not a session and takes no seat. Every shell is opened in your name and recorded against you.

**Workstation** also offers **Open a bare shell**: a plain terminal session in a repository's checkout, with no agent.

Next: Open a session (guides/sessions/open-a-session) · Drive an agent session (guides/sessions/drive-a-session) · Watch a run, and stop or retry one (guides/sessions/watch-a-run)

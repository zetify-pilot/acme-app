# Work with agent sessions

Everything an agent does in Fleet happens in a session on one of your machines. Some sessions the fleet starts on its own; others you open from the browser and drive. This path shows you how to open one, talk to it, and read what it changed.

## The big picture

- **Run.** The fleet's own attempt at one issue. Nobody drives it. You open it from the issue it works on, or from what the Queue says a machine is running.
- **Session.** An agent, or a plain terminal, that you open from **Terminals** and drive yourself, in a repository's checkout.
- **Shell.** A terminal on the machine itself, as its login user, outside any session. You open it with the machine's **Shell** button.

All three run on the same machines. A machine has seats, and each seat holds one session at a time. A run takes a dispatch seat, a session you open takes an interactive seat, and a shell takes none. That is why a new session can wait: it needs a machine with a free interactive seat.

A session starts on a branch of its own. Its page shows that branch's pull request and how its checks stand, and its transcript is kept so you can open it later. When an agent session asks you something, it says so on its tile and in the Cockpit. You can watch a run's conversation the same way, and once a run has ended, **Talk to it** opens a session that knows what the run concluded.

## Read these in order

1. **Sessions: runs, terminals and shells** (concepts/sessions): A dispatched run works an issue on its own. A session you open is yours to drive. Both run on a machine, each on a branch of its own.
2. **Open a session** (guides/sessions/open-a-session): Start an agent session or a plain terminal on a Fleet machine, in the repository and on the branch you choose.
3. **Drive an agent session** (guides/sessions/drive-a-session): Talk to an agent session: send and queue messages, point it at files, run its slash commands, stop a turn and retry a refused one.
4. **Review what a session did** (guides/sessions/review-a-sessions-work): Read a session's branch and pull request, its changes, the ports it serves and the files in its checkout, without leaving Fleet.

## When you need it

- **Arrange your sessions and use the keyboard** (guides/sessions/layouts-and-shortcuts): Switch the Terminals page between Grid, Focus, List and Board, jump anywhere with ⌘K, and find every shortcut behind ?.
- **Take a session over, or bring one back** (guides/sessions/take-over-and-restore): Move a session's one view to this tab, give a terminal its own window, and find or resume a session you closed.
- **Watch a run, and stop or retry one** (guides/sessions/watch-a-run): Find a run on the Runs page, read its conversation while it works or after, stop one that has gone wrong, and retry an issue that ran out of attempts.
- **Open a shell on a machine** (guides/sessions/shell-on-a-machine): Get a shell on one of your Fleet machines itself, as its login user, recorded in your name, without opening a session.
- **Reach a session's port from your computer** (guides/sessions/reach-a-port): Point psql, DBeaver or pgAdmin on your own Windows, Mac or Linux computer at a database a session runs, signed in as you, with nothing opened on the machine.
- **Build an app that runs behind a port link** (guides/sessions/build-an-app-behind-a-port-link): What an app receives when it is opened with Open ↗, how it learns its public address, and how to test sign-in against the same behaviour in your own CI.

---
- **seat**: One place on a machine for a session; each seat holds one session at a time.

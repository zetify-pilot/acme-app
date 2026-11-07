# Understand Fleet

Fleet turns what your team decides into merged code. This path shows how a piece of work moves, where Fleet stops for a person, and why the agent that writes a change never approves it. Once you have read it, every other page in these docs will make sense.

## The big picture

| Step | What happens | Who |
|---|---|---|
| File | You file an idea, a bug or a task, and answer Fleet's questions | you |
| Build | A machine's session builds it and opens a pull request | fleet |
| Verify | A fresh session that did not write it proves each claim, or sends it back | fleet |
| Merge | The change merges; what it promised is checked from then on | nobody |

Under all four: the knowledge base (what the product is and promised), machines and seats (where sessions run, and how many at once), and your own tools (MCP servers, secrets, API keys).

Every piece of work in Fleet is an issue in your own tracker. At every moment it sits in exactly one position, and the position says who has it. A queue means a machine will take it next. `Implementing` or `Verifying` means a run is working on it, and nobody else can take it. A blocked position means it waits on a person. `Done` means it merged.

Fleet settles most of what happens in between. It checks what you filed, builds it and verifies it on its own. It stops for a person in a few clear cases: to promise something new, to answer a question an agent cannot settle, or to do something no agent can, such as create a credential. Each of those lands in your Cockpit. And every change passes two separate sessions. One writes it and opens a pull request. A fresh one, which never saw the code being written, proves each claim and then merges it or sends it back.

## Read these in order

1. **What Fleet is** (start/what-fleet-is): You decide what to build, Fleet builds and checks it, and Fleet asks you when only a person can answer.
2. **How work moves from filing to merge** (concepts/how-work-moves): Every issue sits in exactly one position. Some positions hand it to a machine, some wait on a person, and a few end it.
3. **The Work Line** (concepts/the-work-line): Every step a piece of work takes from idea to closed program, who has to be there for each one, and what sits at each step right now.
4. **Who decides what** (concepts/who-decides-what): Fleet settles everything it can on its own. A person answers questions, makes the calls that promise something new, and does what no agent can.
5. **Why a second session verifies every change** (concepts/verify-before-merge): The agent that writes a change never approves it. A fresh session proves each claim before the change merges, or sends it back.

## When you need it

- **Your tracker and Fleet** (concepts/your-tracker): Your issues stay in Linear, GitHub Issues or Jira. Fleet reads them, keeps its own record of the work it drives, and writes every change back.
- **Commands and tools** (concepts/commands-and-tools): Commands are the written procedures an agent follows. Tools are how an agent reaches Fleet. The fleet runs some commands alone; others need a person.

---
- **Cockpit**: The first page in the sidebar: one list of everything waiting on a person, one row per item, beside everything that was filed.

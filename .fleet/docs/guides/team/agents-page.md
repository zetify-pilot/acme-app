# Read the Agents page

When you finish this guide, you can open Settings › Agents and tell which of Fleet's agents can run in a repository and what is stopping the others. You can also read exactly what any agent is told to do, and see which questions about your codebase are still unanswered.

## What the page lists

An agent is one of Fleet's commands, such as `check` or `prd:implement`. Each is a written prompt that a session follows. **Settings › Agents** lists the agents committed in a repository. If Fleet serves more than one repository, the page opens on **By repository** with the worst first. Pick a repository to see its agents.

The bar at the top counts the **agents**, how many have no spine (no declared list of steps), **broken references**, **slots filled**, how many **need nobody**, and how many **may merge**.

[Open Agents](#settings:agents)

1. [you] **Find an agent.** Type in **Search agents and what they are for**, or sort **by family** or **A–Z**.
2. [you] **Read its line.** Each agent shows **runs here**, **blocked** or **not declared**, what it is for, and how many steps it declares. A broken-reference mark means the prompt names a file this repository does not have. **needs** names the slots that block it.
3. [you] **Open it.** Click the agent's name to see its own page.
4. [you] **Answer what is missing.** Click a slot that is **missing** or a **stub** to open its page, then write the file it names.

## One agent's page

An agent's page has these parts:

- **verdict**: whether it runs in this repository and, if it does not, which slots it needs.
- **invoke**: the command to start it, ready to copy.
- **may merge**: whether it may merge its own work, or must hand off to someone else.
- **requires** and **optional**: the slots it reads.
- The documents, other agents and scripts it refers to. Each one is a link.
- **Steps**: the steps, gates and actors the agent declares, when it declares them.
- **The prompt, in full**: the whole prompt, rendered from the file in your repository.

A document an agent refers to opens on a page of its own, showing who reads it.

> **Why:** The prompt on this page is the file in your repository, not a copy kept by Fleet. What you read here is exactly what a session is told.

## Slots

A slot is a question about your codebase that no agent can guess, for example how to run lint, build and tests here (the `gate` slot). The page lists slots in up to three groups:

- **Slots that ship with the agents**: answered inside Fleet's own files and the same in every repository. If one is missing, the agent tree is incomplete. Your repository has not failed to supply anything.
- **Slots this repository must answer**: a missing required slot stops every agent that needs it. A missing optional slot makes the run worse in the way its line describes.
- **Declared by no agent**: either an agent should be asking for it, or the row is out of date.

Each slot reads **filled**, **stub** (the file exists but only holds a placeholder), **missing** or **not set**. A slot's page lists who it blocks. Under **Fix it** you will find the file to write and **Open a session to write it**. Filling slots is its own guide: [Fill a repository's slots](guides/knowledge/fill-slots).

Next: Answer the questions the commands ask about your repository (guides/knowledge/fill-slots) · Commands and tools (concepts/commands-and-tools)

---
- **slot**: One question a command asks about the repository it runs in, and the place where the repository answers it.

---
title: "Sorting something new: which kind of thing is it?"
kind: concept
for: [everyone]
summary: "Walk the planning ladder to decide whether a request is a bug, an idea, a task, a PRD, a slice or a program, in the order that removes the doubt."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/process/planning-ladder.md
  - knowledge/slots/entity-model.md
  - packages/fleet-knowledge/src/fleet_knowledge/commandtree/commands/zetify/route.md
minutes: 8
---

:::lede
Someone asks for something. Before anyone builds it, it has to be put in the right place: a bug, a small task, one buildable piece, a deliverable, or something larger. Judging by how big the request sounds gets it wrong. Run the tests below, in order, and stop at the first one that fits.
:::

## Why there is a fixed order

Fleet once turned a bug, a one-page screen change and a request for documentation into three new programs in one day. Each of them failed a test that nobody ran. The :term[planning ladder] is that list of tests, in the order that catches each mistake before it happens. It is the same in every repository, and the commands that sort work (route, intake and check) all carry it.

## Three names do most of the work

Most requests end up as one of three things: the part of the product it belongs to, what will be true when it is done, and the piece one agent builds.

::diagram{name="three-questions" slice="SL-250"}

## Walk the ladder

:::steps
- [you] **Is something broken?** Something that used to work, or that the product already says it does, does not. A wrong or missing docs page for something that ships counts. Then it is a **bug**, however large the fix turns out to be.
- [you] **Is it early?** Nobody can yet say what "done" looks like, and it is for later. Then it is an **idea**: parked, not sized.
- [you] **Can you point at the code it owns?** A directory, a service, a set of tables. Then it is a :term[component]: something you build, which never finishes.
- [you] **Is it a lasting property of the product?** If it is one sentence a person can check, it is a :term[capability]. If it comes out of several parts working together and owns no code, like "an order page loads in under a second", it is an :term[outcome].
- [you] **Would a customer name it, and does it group several capabilities?** Then it is a :term[feature]: a brief, a few uses, and the capabilities under each use. Its planning name is :term[feature area].
- [you] **Is it small work that needs no design?** A dependency bump, a configuration change, a wording fix, a refactor nobody can see. Then it is a **task**. If two people could disagree about how it should look or behave, it needs a design and is not a task.
- [you] **Can one agent build it in one working session, with criteria that each can be shown to pass?** One page, one control, one API behaviour, one command. Then it is a :term[PRD]. One new screen is a PRD, however important it is.
- [you] **Is it one deliverable with a "Done when" that none of its PRDs proves alone?** Then it is a :term[slice]. It usually holds two or more PRDs.
- [you] **Does every program test below pass?** Only then is it a :term[program].
:::

If it is only a way to group things that already stand on their own, such as "security" or "onboarding", it is none of these. Do not create a container for it; sort each piece on its own.

**If nothing matches, you have not finished thinking.** Something that never finishes but owns no code is an outcome. Something that finishes but holds one deliverable is a slice, not a program.

## The program tests

A program is the rung most often reached for and most often wrong. Every one of these must pass:

1. **The title is literal.** Someone who reads only the title can say what will be delivered.
2. **It names a person or a surface.** A person who is stuck today ("when this happens, I want that, so I can do this"), or the thing that lands and the screen it shows up on.
3. **There is a day it becomes true, and somebody notices.** "A new customer is set up without an engineer" has such a day. "Scalability" does not.
4. **It holds at least two slices**, each finishing on its own. If you can describe only one, it is a slice.
5. **No existing open home fits.** Joining something that already exists is always the first thing to check.

:::mode{areas}
Your repository plans by areas, so the existing programs take no new slices. New work goes under the feature area that owns it, and the area is the home you look for first.
:::
:::mode{programs}
Your repository plans by programs. A new slice names its feature area and may also join an open program it genuinely serves. A finished or withdrawn program is never stretched to take new work.
:::

## Say why it is not each smaller rung

Whatever you land on, write one line for each smaller rung saying why it is not that: a slice says why it is not a bug, a task or a PRD. The line is evidence from the request, not the rung's name repeated. **If you cannot write the line, the work is that smaller rung.** This is what lets the person who accepts the proposal see a wrong size.

## Worked examples

| Request | It is | Why |
|---|---|---|
| "A session ignores new messages while it waits on a long pull-request watch." | bug | Something is broken. A big fix does not change that. |
| "Maybe one day we support single sign-on with more providers." | idea | Nobody can say yet what done looks like. |
| "Bump the HTTP client library to the current version." | task | No design, nothing new for anyone to see. |
| "Add CSV export to the audit log." | PRD | One agent, one session, one surface. |
| "A reviewer can read the audit record and act on it." | slice | One capability, with a "Done when" none of its PRDs proves alone. |
| "A new customer account is set up and served without an engineer in the loop." | program | A named person notices on a day, and it holds at least two deliverables. |
| "Rate limiting." | component | You can name the directory. |
| "Scalability." | outcome | No code owns it and it never finishes. |

## Let Fleet sort it with you

You do not have to walk the ladder alone. Filing a :term[feature request] starts a short interview that asks where it goes and writes it up for a decision:

::command{name="intake"}

To have a request sorted and handed to the command that builds that kind of thing:

::command{name="route"}

Route proposes; a person accepts or sends it back. Bugs, tasks and ideas live only in your tracker and never get a file in the knowledge base.

::cards{links="knowledge-base/feature-areas, knowledge-base/slices, knowledge-base/prds"}

# Slots: your repository's answers

A Fleet command is a procedure that works in any repository: fix a bug, design a PRD, verify a change. To run in yours, it needs a few facts only your repository knows, such as which command runs the tests. Each of those facts is a slot, and your repository fills it in once.

## What a slot is

A slot is one question a command asks about the repository it runs in, and the place where your repository answers it. The Knowledge page calls them **Repository answers**.

The questions arrive with the commands, the same in every repository. Only the answers are yours. A command that needs an answer your repository has not given says so, instead of guessing.

## Three kinds of slot

| Kind | Who answers it | Example |
|---|---|---|
| **Shared** | Nobody: it ships with the commands and is the same everywhere | the planning ladder, the shape of an issue, how a person is asked a question |
| **Required** | Your repository. A command that needs it will not run without it | `gate` (how to run lint, build and tests), `git-workflow` (branch names, who merges), `feature-areas`, `commitments`, `tracker-identity`, `languages` |
| **Optional** | Your repository, when it has an answer. A command that lacks it does less, in the way the question says | `entity-model`, `journeys`, `codegen`, `ui-contracts`, `operations`, `audit-profile` |

The full list of questions, and which commands read each one, is in the Slots reference.

## Where the answers live

Each answer lives wherever your repository already keeps that fact. `knowledge/slots/README.md` holds the map: one entry per slot naming the file or files that answer it. Some answers are short files of their own under `knowledge/slots/`, such as `knowledge/slots/gate.md`. Others point at something that already exists: the `slices` slot points at the slice register, `components` at the component registry, `product-vision` at the file that says what the product is for.

A slot file ends with an **Answers** list, one fact per line, so a command lands on the fact rather than on a document to search.

## Starting empty is fine

Some slots Fleet answers for you. The setup pull request writes `git-workflow` and `tracker-identity` from this repository's settings in Fleet. It writes `planning-model`, `entity-model`, `file-conventions` and `feature-areas` from the layout it creates. Change any of them when your repository works differently.

For every other slot, `fleet init` writes a short placeholder, marked with a `<!-- fleet:stub -->` line at the top. Until you replace it, Fleet reports the commands that depend on it as waiting for an answer: a warning, never a failed build. Delete the marker when the answer is written.

To see which slots your repository has answered and which commands can run:

```bash
fleet slots --repo .
```

> **Tip:** Answer `gate` and `git-workflow` first. Almost every command that changes code reads them, and a wrong answer there shows up as red checks on every pull request.

## Where you see them

Each slot has a page in Fleet. It says whether the slot is filled, still a placeholder, or missing; which files answer it; and which commands cannot run until it is answered. When it is not filled, the page offers to open a session that writes the answer with you.

Next: Answer the questions the commands ask about your repository (guides/knowledge/fill-slots) · The knowledge folder, file by file (knowledge-base/the-folder)

---
- **slot**: One question a command asks about the repository it runs in, and the place where the repository answers it.

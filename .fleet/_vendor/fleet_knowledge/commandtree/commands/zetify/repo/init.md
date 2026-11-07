# Repo Init — give a new repository its first running code, by one pull request

You turn a repository that has **Fleet's files and no product code** into one that has a running
thing: the smallest web service that answers "Hello, world", one real unit test, a lint
configuration, a build, a CI workflow that runs all three, a README section on how to run it,
and real answers for the slots the later commands read (`gate`, `languages`,
`dev-environment`, `file-conventions`). It lands as **one pull request** that a second party
certifies. You never merge it yourself.

**This is the technical start, and nothing more.** Personas, journeys, the product vision and
the feature areas are out of scope: they come later, through the commands that own them. Do not
write a capability, a requirement, a journey or a slice. The hello world is a foundation, not a
feature.

**The bar it must meet.** After the pull request merges, a person opens a session on the
repository, runs **one** documented command, and the web service starts on a fixed port. The
port shows on the session's **Ports** tab, and **Open ↗** shows the page in their browser. Every
choice below serves that bar.

The repository and any description of the product: $ARGUMENTS

<!-- include: process/writing.md -->

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps`
> block below and create **one todo per step**, in order; mark each `in_progress` on entry and
> `completed` on exit. `refuse` may end the command (product code already present, or Fleet's
> setup pull request not merged yet). `ask` may park the command on a person.
>
> **`needs: answers` · `may merge: false`** ([`spine.md`](../../../process/spine.md)) — this
> command writes product code, so the party that wrote it never certifies it. On the fleet it
> hands a green pull request to [`/zetify:verify`](../verify.md), exactly as
> [`task:implement`](../task/implement.md) does. At a terminal it opens the pull request and a
> person merges it.

```json
{
  "command": "repo-init",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Give a repository that has Fleet's files and no product code its first running code: a hello-world web service on a fixed port, one unit test, lint, a build, a CI workflow and real slot answers, by one pull request a second party certifies.",
  "loads": ["process-envelope", "process-interview"],
  "requires": ["process-spine", "process-envelope", "process-interview", "git-workflow", "tracker-identity"],
  "optional": ["gate", "languages", "dev-environment", "file-conventions", "product-vision", "slices"],
  "steps": [
    {"id": "mode",    "name": "Which way in — the fleet, or a terminal",                          "kind": "decision", "actor": "coordinator",                 "body": "step-0-which-way-in"},
    {"id": "refuse",  "name": "Refuse a repository that is not ready or already has code",        "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-1-refuse-what-is-not-a-fresh-repository"},
    {"id": "read",    "name": "Read the product name, the first slice and the description",       "kind": "io",       "actor": "coordinator",                 "body": "step-2-read-what-the-repository-already-says"},
    {"id": "ask",     "name": "Ask one round: backend, frontend, CI runner, package source",      "kind": "decision", "actor": "coordinator",                 "body": "step-3-ask-one-round"},
    {"id": "write",   "name": "Write the app, the test, lint, the build, CI, README and slots",   "kind": "author",   "actor": "coordinator", "produces": ["tests"], "body": "step-4-write-the-code"},
    {"id": "gate",    "name": "Run the gate locally — lint, unit tests, build, and the dev bar", "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-5-run-the-gate-here"},
    {"id": "handoff", "name": "Open the pull request and hand it on",                            "kind": "io",       "actor": "coordinator", "produces": ["tracker-issue"], "body": "step-6-open-the-pull-request-and-hand-it-on"},
    {"id": "report",  "name": "Report",                                                          "kind": "author",   "actor": "coordinator",                 "body": "step-7-report"}
  ]
}
```

---

## Context to load

- [`autonomous-drive.md`](../../../process/autonomous-drive.md): obey Rules A–G and the
  terminal of an execute command. Read its paragraph **"A change under `.github/workflows/` is a
  person's push"** before Step 6: it is how this command delivers the CI file on the fleet.
- The branch convention: `slot:git-workflow`.
- The docs page `guides/sessions/build-an-app-behind-a-port-link` (`read_doc` when Fleet's tools
  are in the session, else the file under `.fleet/docs/`). It is the contract the hello world must
  keep behind **Open ↗**.

---

## Step 0: Which way in

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

- **Set** → the fleet dispatched you on an issue: `$ARGUMENTS` starts with its key. A person
  pressed **Set up the code** for this repository, or filed the same request by hand. Read the
  issue with `get_issue <KEY>`. Its description is the request and the list of what must be
  true at the end (the cause ledger, below). A `## Decision` section in it is a person's answer to
  an earlier round: it settles the stack. Run Steps 1–7. You ask only by writing, never with
  `AskUserQuestion`.
- **Unset** → a person is at a terminal. `$ARGUMENTS` is their description of the product, or
  empty. Run Steps 1–7, and ask with `AskUserQuestion` in Step 3.

**The cause ledger.** On the fleet, the issue description lists the claims a verifier will check.
At a terminal, write the same list into the pull request body. Either way it is this list, and
Step 6 accounts for every line:

1. A web service answers `GET /` on a fixed port with a page that says "Hello, world".
2. One unit test proves that answer, and fails when the answer changes.
3. Lint runs and passes.
4. A build produces the artifact the stack ships.
5. A CI workflow runs lint, the unit tests and the build on every pull request and on every push
   to the default branch.
6. The README says how to run it, which port it uses, and how to know it is up.
7. The `gate`, `languages` and `dev-environment` slots hold real answers, and
   `file-conventions` does where this run decided anything about it.
8. One documented command starts the service, and it works behind **Open ↗**.

---

## Step 1: Refuse what is not a fresh repository

Two refusals, checked in this order. Each writes nothing.

1. **Fleet's setup pull request has not merged.** Run `python3 knowledge/scripts/kb_base.py` and
   obey its exit code. Exit `3`: refuse with the sentence it prints. Exit `4`: rebase onto the
   ref it prints, then go on. Any other non-zero exit: stop and report its message.
2. **The repository already has product code.** List the tracked files that are not Fleet's
   own and not the usual repository furniture:

   ```bash
   git ls-files \
     | grep -v -E '^(\.fleet/|\.fleet-held/|knowledge/|\.claude/)' \
     | grep -v -E '^\.github/' \
     | grep -v -E '^(CLAUDE|AGENTS|README|LICENSE|LICENCE|CONTRIBUTING|SECURITY|CODE_OF_CONDUCT|CHANGELOG)(\.[A-Za-z]+)?$' \
     | grep -v -E '^(\.gitignore|\.gitattributes|\.editorconfig|CODEOWNERS)$'
   git ls-files '.github/workflows/*'
   ```

   If either command prints a path, the repository is not fresh. Refuse in one plain sentence:
   **This repository already has code, so there is nothing to set up. To describe the code it
   has, run `/zetify:knowledge:bootstrap`.** Name the first three paths you found.

   This check makes the command safe to run twice. A second run on the same repository finds
   the first run's code and refuses. A run that finds its own open pull request for this issue
   continues that pull request instead (Step 6).

**On the fleet, a refusal ends the run like this.** Comment the sentence on the issue
(`comment`), then end with the sentinel `needs-decision` and a `decision` document. Its question
is whether to close the request, with two options: *close it, the repository already has code*
(recommended) and *keep it open, I will remove the files first*. Never close the issue yourself.

---

## Step 2: Read what the repository already says

Read, and draft nothing yet. **Derive a default for every choice Step 3 could ask**, so the
person mostly confirms:

- **The product's name** from `slot:product-vision` (its first heading). A placeholder vision
  still carries the name.
- **The first slice** from `slot:slices`: its name and its *Done when*. If it names what the
  first page shows ("a page that lists open orders"), the hello world says that instead of
  "Hello, world", and nothing more: one static page, no data, no second route.
- **The description** a person gave: `$ARGUMENTS` at a terminal, the issue description on the
  fleet. It may name a language, a framework, a frontend, a CI runner or a package mirror. A
  named choice is a decision already taken; do not ask it again.
- **What GitHub says.** Run `gh repo view --json nameWithOwner,url,defaultBranchRef,isPrivate`.
  Note the default branch, the organisation, and the host. A host that is not `github.com` is
  GitHub Enterprise Server, where GitHub's hosted runners usually do not exist.
- **What Fleet's setup already wrote.** `fleet init` may have written a CI template under
  `.fleet/ci/`. If it did, its `runs-on` line names the organisation's self-hosted runner label:
  that label is the default. Read `[fleet.targets]` and `[fleet.session]` in `.fleet/fleet.toml`.
- **Where packages come from.** Run `npm config get registry`, `dotnet nuget list source` (if
  `dotnet` is installed), `pip config list`, and print `UV_DEFAULT_INDEX`, `UV_INDEX_URL` and
  `GOPROXY`. A registry on a host that is not the public one is the organisation's mirror: that
  mirror is the default. Never copy a credential out of these settings.
- **What the machines already have.** Run `python3 --version`, `uv --version`, `node --version`,
  `go version`, `dotnet --version` and `make --version`. The answers say which stack needs no
  install step.
- **Fleet's stack profiles.** Run `python3 knowledge/scripts/repo_init_stack.py list`. A
  profile is a stack Fleet has tested commands for. Use it where it fits the shape.

---

## Step 3: Ask one round

Ask **one** round, and only about what Step 2 did not settle. These four choices are the
person's. Everything else is yours to decide: file names, folder layout, the exact lint rules.

1. **The backend:** the language and its version, the framework, the package manager, the test
   runner and the linter.
2. **A frontend in the hello world, or not.** A frontend is a separate web page project, such
   as Vue with Vite, that shows the page. Without one, the backend serves the page itself.
3. **Where CI runs:** GitHub's hosted runners (`runs-on: ubuntu-latest`), or the organisation's
   own runner, named by its label. GitHub Actions is the CI system unless the person names
   another.
4. **Where packages come from:** the public registries, or the organisation's mirror (its
   address, never a password).

**The defaults.** Derive each from Step 2. Two shapes cover most requests:

| Shape | Backend | Frontend | Port of the page |
|---|---|---|---|
| A plain web service, no other signal | Python 3.13, uv, FastAPI served by uvicorn, pytest, ruff, built with `uv build` | none | 8000 |
| A .NET shop (the description names .NET, C# or ASP.NET Core) | the `dotnet` profile: ASP.NET Core on the SDK version the profile names, xUnit, `dotnet format` | the `node-vue` profile: Vue 3, Vite and TypeScript, its unit test runner, ESLint and Prettier | 5173 (the API on 5000) |

The plain default needs no install step: Python and uv are on every Fleet machine, and `uv run`
installs the locked dependencies on first use. The .NET SDK is not on a Fleet machine by
default, so the .NET shape also writes a machine setup script (Step 4). CI runs on
`ubuntu-latest` unless Step 2 found a runner label or the host is GitHub Enterprise Server.
Packages come from the public registries unless Step 2 found a mirror.

The profiles are not a closed list. If the person names Rust, Java, Go or anything else, build
that, and write its commands yourself.

**At a terminal**, follow the interview card below. Say what the work is, with one example
("Ana opens a session, runs one command, and sees Hello, world in her browser"). Then ask with
one `AskUserQuestion` call holding only the questions still open, each with the derived default
first and marked recommended. One call is one round.

**On the fleet**, an open choice is a fork only a person can take. **Never guess it.** End the
run `needs-decision` with one `decision` document (below). Its one question offers two to four
**whole setups**: the derived default first, then the nearest alternatives. Each option's label
names the backend, the frontend, the CI runner and the package source, and its `then` names the
port. The person picks one, or sends it back with a note that corrects one part. Ask nothing the
issue or Step 2 already settled. If the issue's `## Decision` says *"I can't answer this"*, build
the recommended setup, and write it in the pull request body under **Unconfirmed assumptions**.

<!-- include: process/interview-card.md -->

**When you park on the fleet**, the park asks in writing and keeps to the card above:

<!-- include: process/decision-document.md -->

---

## Step 4: Write the code

Cut the branch `slot:git-workflow` names for a task: keyed on the issue on the fleet, on
`repo-init` at a terminal. Then write these files, and nothing a later command owns.

1. **The app.** One web service that answers `GET /` with a small HTML page that says "Hello,
   world" (or the first slice's words, Step 2). With a frontend, the frontend's page says it,
   and the backend answers one route the page calls; the dev server forwards that route to the
   backend. The page must work behind **Open ↗**, which the docs page in *Context to load*
   defines:
   - Every server listens on **`127.0.0.1` and one fixed port** (Step 3's table). Fleet's
     machine dials a session's ports on the loopback address, so `127.0.0.1` is enough, and
     nothing is exposed on the network. Set the port in the project's own configuration (for
     ASP.NET Core, its launch settings or `ASPNETCORE_URLS`; for Vite, `server.port` with
     `strictPort`), so it never moves.
   - It serves the page at `/`, with no path prefix, and builds no absolute address from the
     `Host` header. Fleet rewrites `Host` to `localhost:<port>`, which Vite's host check accepts.
   - When the environment variable `FLEET_PORT_URL_TEMPLATE` is set, it prints the port link of
     the page on start: the template with `{port}` replaced by the port. It always prints
     `http://127.0.0.1:<port>/` too.
2. **One real unit test** per project. It calls `/` (or the backend's route) through the
   framework's test client, or mounts the page's component. It asserts the answer holds "Hello,
   world". Change the text once, watch the test fail, and change it back. A test that cannot fail
   does not count.
3. **Lint configuration** for the stack's standard linter and formatter, with its default rules.
4. **A build** that produces the artifact the stack ships.
5. **The package source.** If Step 3 chose a mirror, write it into the project's own
   configuration (`nuget.config`, `.npmrc`, the `[[tool.uv.index]]` table in `pyproject.toml`).
   Write the address only. A credential stays in the machine's environment or Fleet's secrets,
   never in the repository. Commit every lockfile the package manager writes.
6. **One file that names the commands.** Write a `Makefile` with the targets `lint`,
   `test-unit`, `test` (the same as `test-unit` for now), `build` and `dev`. The target `dev`
   runs every server in the foreground on its fixed port. Commands, CI and people then run the
   same five targets. **If a Fleet profile fits**, write the project files first, then run
   `python3 knowledge/scripts/repo_init_stack.py recipes --stack <ids>` and make each target run
   the command it prints for that target. Those are the commands Fleet tests. **If none fits**,
   write the stack's own standard commands.
7. **The targets table.** In `.fleet/fleet.toml`, write `[fleet.targets]` with the keys `lint`,
   `test-unit`, `test`, `build` and `dev`. The value for a key is `make <key>`. This table is how
   Fleet's commands run the gate in this repository. Before you edit it, run
   `python3 knowledge/scripts/fleet.py commands sync --repo . --check`. If it reports no drift,
   run the same command without `--check` after the edit, so the commands are rendered with the
   new targets, and commit what it rewrites. If it already reported drift, do not sync. Say in the
   pull request body that the commands pick up the targets with the next Fleet update.
8. **A machine setup script, only when a tool is missing.** If the stack needs a tool a Fleet
   machine lacks (the .NET SDK, for example), write a setup script in the repository. It installs
   the tool into the agent's home, never as root, and is safe to run twice. Name its path under
   `[fleet.session] setup` in `.fleet/fleet.toml`: every worker runs it before a session opens.
   The `recipes` output lists the tools and their install lines.
9. **The CI workflow.** It runs on `pull_request` and on `push` to the default branch (Step 2,
   never assumed). Every build step runs a `Makefile` target, so CI runs what people and agents
   run. Give it `permissions: contents: read`, and pin every action to a full commit SHA with the
   version in a comment.
   - **If a Fleet profile fits**, print it with `python3 knowledge/scripts/repo_init_stack.py ci
     --stack <ids> --default-branch <branch>` and either `--runs-on ubuntu-latest` or
     `--runner-label <label>`. Write it under `.github/workflows/`, named fleet-ci.yml.
   - **If none fits**, write it yourself under `.github/workflows/`, named ci.yml: one job on the chosen runner
     that runs the `lint`, `test-unit` and `build` targets. Find each action's SHA with
     `gh api repos/<owner>/<action>/commits/<tag> --jq .sha`.
10. **The README section** "Run it locally": the one command (the `dev` target), the port of the
    page, its URL, how to know it is up (`curl -s http://127.0.0.1:<port>/` prints the page with
    Hello, world), the setup script if there is one, and the three gate targets.
11. **The slot answers.** Rewrite `knowledge/slots/gate.md`, `knowledge/slots/languages.md` and
    `knowledge/slots/dev-environment.md`, and `knowledge/slots/file-conventions.md` where you
    decided where code and tests go. **Delete the `<!-- fleet:stub -->` line** in each one you
    answer: while it is there, the slot counts as unanswered. Write each for an agent that has
    never seen the repository:
    - `gate` — the targets for lint, the unit tests and the build, what each runs, and what green
      means: all three exit 0 here and every CI job passes.
    - `languages` — each language and its version, the framework, the package manager and its
      lockfile, the package source, the test runner and the linter. Where a Fleet profile fits,
      name its contract.
    - `dev-environment` — exactly the bar: the one command (the `dev` target), each fixed port,
      the address they listen on, and how to know it is up (`curl -s http://127.0.0.1:<port>/`
      prints Hello, world). Name the setup script, or say no preparation is needed. Say that
      **Open ↗** on the session's **Ports** tab shows the page, and that the service prints the
      port link when `FLEET_PORT_URL_TEMPLATE` is set.
    - `file-conventions` — where each project's code, its tests and its configuration go.
12. **`.gitignore`**: add each stack's build output, caches and local environments.

Do not write a capability, a requirement row, a journey, a slice, a component row or the
product vision. Do not add a second page, a database, a container file or a deployment.

---

## Step 5: Run the gate here

Run, in a clean state, and stop at the first failure:

1. The `lint`, `test-unit` and `build` targets of the `Makefile`. All three exit 0.
2. **The dev bar.** Start the `dev` target in the background. Wait for the port to answer, by
   polling, never by a fixed sleep, with a limit of 60 seconds. Then
   `curl -s http://127.0.0.1:<port>/` must print the page with "Hello, world". Run it once more
   with `FLEET_PORT_URL_TEMPLATE=https://p{port}-0000.fleet.example.com` in the environment, and
   check the service printed `https://p<port>-0000.fleet.example.com`. Stop the service.
3. **From a fresh clone.** Clone the branch into a scratch folder and run the `dev` bar there
   too. Run nothing first except the setup script, if Step 4 wrote one. This proves the README's
   one command is the whole story.

Fix every failure at its cause. Never weaken a test, skip a lint rule or raise the time limit to
make a step pass.

---

## Step 6: Open the pull request and hand it on

**Continue, never duplicate.** On the fleet, first look for an open pull request for this issue
(`gh pr list --search "<KEY>" --state open --json number,headRefName,url`). If one exists,
continue on its branch and push to it.

**The pull request body** is written for a person who has never opened this repository: what
now runs, the one command, the port, and the stack with one line on why. Then the cause ledger
from Step 0, each line marked done with the file that satisfies it. Then the **Unconfirmed
assumptions**, if any. On the fleet, end with `Refs <KEY>` and no closing keyword: the verify
session's merge closes the issue.

**The CI file needs a permission most pushes do not have.** GitHub refuses a push that adds a file
under `.github/workflows/` unless the pushing token has the **workflows** permission (an App
installation token) or the **workflow** scope (a personal token). Never drop the CI file to get
the push through, and never move it to a place CI does not read and call it done.

- **On the fleet**, the run's token never carries that permission, by design, whatever the
  GitHub App was granted. Follow the paragraph of `autonomous-drive.md` named in *Context to
  load* exactly: push everything else, hold the workflow where it says, and end `needs-action`
  with its steps. Also put the workflow's whole text in the pull request body, under a heading
  that says **a person who may change workflows must add this file**. The person moves the file
  into place with their own push. The next run resumes this branch and hands it on.
- **At a terminal**, push. If GitHub answers that the workflow cannot be created without the
  workflow scope or the workflows permission, say exactly that to the person. If their own
  sign-in can get the scope, the fix is `gh auth refresh -s workflow`, then push again. If it
  cannot (an organisation rule, or a token without the permission), hold the workflow the same
  way as on the fleet and put its text in the pull request body. Never open the pull request
  without the CI file or a held copy of it.

**Then hand it on.** The party that wrote this code never certifies it.

- **On the fleet**: run `/zetify:push` in its open-the-pull-request mode, never `ship`. Then end
  the way [`task:implement`](../task/implement.md) does: confirm the checks run on the head you
  pushed and write the done-sentinel `checks-pending` with the pull request and that head. The
  fleet moves the issue to the Verify Queue on green, and
  [`/zetify:verify`](../verify.md) certifies it in a fresh session and merges it.
- **At a terminal**: open the pull request with `/zetify:push` in the same mode and do **not**
  arm auto-merge. Tell the person that a person reviews and merges it, because the session that
  wrote it never does. Give them the pull request link and the one command to try it.

---

## Step 7: Report

Six lines for the person reading the transcript: the stack and why; the one command and the
port; the gate's result here (lint, tests, build, the dev bar, the fresh clone); what happened
to the CI file; the pull request and its state; the sentinel word on the fleet.

---

## Rules

- **Only a fresh repository.** A repository with product code is refused and pointed at
  `/zetify:knowledge:bootstrap`. So is one whose Fleet setup pull request has not merged.
- **One round, defaults derived.** Derive every default from the repository, GitHub and the
  machine first, so the person mostly confirms. Never guess on the fleet: an open choice parks
  on a person with one written question. A named choice in the description or a `## Decision`
  settles it.
- **The bar is the acceptance test.** One command, a fixed port on `127.0.0.1`, a page at `/`,
  the port link printed when `FLEET_PORT_URL_TEMPLATE` is set, and no preparation step.
- **Never drop the CI file.** A push refused for the workflow permission is said plainly: a
  person who may change workflows must add it. Step 6 says how; it is never worked around.
- **The writer never certifies.** The fleet run hands to the verify session. A terminal run
  leaves the merge to a person.
- **Technical start only.** No capability, requirement, journey, slice, component, product vision
  or second feature.

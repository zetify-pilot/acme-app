# Fleet docs

How to use Fleet, and how a repository's knowledge base is built.

Fleet's own docs, one file per page, in reading order under the job each belongs to. Live facts (this repository's slices, areas and PRDs) are filled in only by the `read_doc` tool.

## Understand Fleet

- [Understand Fleet](jobs/understand-fleet.md): What Fleet does, who decides what, and why every change is checked twice before it merges.
- [What Fleet is](start/what-fleet-is.md): You decide what to build, Fleet builds and checks it, and Fleet asks you when only a person can answer.
- [How work moves from filing to merge](concepts/how-work-moves.md): Every issue sits in exactly one position. Some positions hand it to a machine, some wait on a person, and a few end it.
- [The Work Line](concepts/the-work-line.md): Every step a piece of work takes from idea to closed program, who has to be there for each one, and what sits at each step right now.
- [Who decides what](concepts/who-decides-what.md): Fleet settles everything it can on its own. A person answers questions, makes the calls that promise something new, and does what no agent can.
- [Why a second session verifies every change](concepts/verify-before-merge.md): The agent that writes a change never approves it. A fresh session proves each claim before the change merges, or sends it back.
- [Your tracker and Fleet](concepts/your-tracker.md): Your issues stay in Linear, GitHub Issues or Jira. Fleet reads them, keeps its own record of the work it drives, and writes every change back.
- [Commands and tools](concepts/commands-and-tools.md): Commands are the written procedures an agent follows. Tools are how an agent reaches Fleet. The fleet runs some commands alone; others need a person.

## Learn the knowledge base

- [Learn the knowledge base](jobs/knowledge-base.md): The folder in your repository that holds what the product is, what it promised and what was decided.
- [The knowledge base](knowledge-base/overview.md): The knowledge folder each repository keeps: what the product does, what it promised, and what is changing. Fleet plans and checks against it.
- [The knowledge folder, file by file](knowledge-base/the-folder.md): Where each kind of knowledge lives under knowledge/, what each file holds, and who writes it.
- [Features, uses and capabilities](knowledge-base/feature-areas.md): A feature is a part of the product a customer would name: a brief says what it is, uses say what people do with it, capabilities make each use work.
- [Slices](knowledge-base/slices.md): A slice is one deliverable with one sentence that says when it is done. What makes a good one, where it lives, and how it finishes.
- [PRDs](knowledge-base/prds.md): A PRD is one piece of work one agent can build in one session, with criteria that each can be shown to pass. It is the only thing whose status is written.
- [Promises and requirements](knowledge-base/promises.md): What the product has committed to, kept as numbered requirements that are never deleted, cited by id, and checked by the Quality desk.
- [Start a knowledge base in a repository](guides/knowledge/start-a-knowledge-base.md): Give a repository its planning record and Fleet's commands, from the Set up page or with fleet init in a terminal.
- [Build the knowledge for code you already have](guides/knowledge/describe-existing-code.md): Run the knowledge bootstrap: an agent drafts your product's description from the code, one part at a time, and you confirm what it promises.
- [Answer the questions the commands ask about your repository](guides/knowledge/fill-slots.md): Replace the placeholder slot answers fleet init wrote, so every command can run in your repository and none runs half-blind.
- [Record a decision so it outlives the conversation](guides/knowledge/record-a-decision.md): Your answers to Fleet's questions are kept on the issue for you; a decision the whole product should follow goes in a dated decision record.
- [Keep your feature maps true to the code](guides/knowledge/keep-maps-current.md): When you change code a feature map describes, correct the map's facts in the same pull request, and never rewrite its intent to match the code.
- [Move a repository from programs to feature areas](guides/knowledge/move-to-areas.md): Give every live slice its feature area with fleet planning migrate, and optionally stop programs taking new slices, by one pull request you review.
- [Fix a failing knowledge check](guides/knowledge/fix-a-failing-check.md): Read what fleet check printed, find the file and the fix it names, and get your pull request green without weakening the check.
- [Run the knowledge checks in your CI](guides/knowledge/run-checks-in-your-ci.md): Add one GitHub Actions job that runs fleet check on every pull request, so a broken knowledge base fails the build before it merges.
- [Planning by areas or by programs](knowledge-base/planning-modes.md): A repository plans in one of two modes. Both put every slice under a feature area; only one also groups slices into programs.
- [Sorting something new: which kind of thing is it?](knowledge-base/what-is-it.md): Walk the planning ladder to decide whether a request is a bug, an idea, a task, a PRD, a slice or a program, in the order that removes the doubt.
- [Programs](knowledge-base/programs.md): In a repository that plans by programs, a program is a larger result that two or more slices add up to, proven by a check of its own.
- [Capabilities and components](knowledge-base/capabilities-and-components.md): A capability is something a person can do with the product. A component is a part of the system you build. They are mapped to each other, never one to one.
- [Journeys](knowledge-base/journeys.md): A journey is how one kind of person gets a whole job done with the product, written as numbered criteria anyone can check.
- [Decisions](knowledge-base/decisions.md): A decision record keeps a choice someone made, the option they turned down and why, so a later change cannot quietly reverse it.
- [Slots: your repository's answers](knowledge-base/slots.md): Fleet's commands are the same in every repository. Slots are the questions they ask about yours: how to test it, how branches work, where things live.
- [Records: check results, audits and retros](knowledge-base/records.md): What happened, kept as written: a file for every check run, a record for every audit, and the retros agents write after their runs.
- [Generated tables](knowledge-base/generated-tables.md): Some tables in the knowledge folder are rendered from one file per row and never edited by hand. Which ones, why, and what to do instead.

## Use Fleet day to day

- [Use Fleet day to day](jobs/daily-work.md): Work through the Cockpit, answer what waits on you, and file what you noticed.
- [Take one feature request to a merged change](start/your-first-change.md): File a small feature request, answer Fleet's questions, accept its proposal, and watch it become a merged pull request.
- [Find your way around the app](start/find-your-way.md): A tour of the sidebar: the daily pages at the top, then Fleet, Docs, Settings and System.
- [Work through the Cockpit](guides/daily/cockpit.md): One list, opening on what waits on you: answer each item on its own page, narrow it by state, customer or change date, save a view, or snooze an item.
- [Answer a question](guides/daily/answer-a-question.md): Answer what an agent asked you, approve a design it drew, or send the question back with instructions.
- [File a feature request, a bug or a task](guides/daily/file-work.md): Hand the fleet something new in plain words: a feature request to place and shape, a bug to reproduce, or a task to build.
- [After you file](guides/daily/after-you-file.md): Say where a feature request goes, answer the interview, accept or send back what it becomes, and confirm the bug the fleet reproduced.
- [Take work by hand](guides/daily/take-it-by-hand.md): Do a job only a person can do and hand it back, or take an issue off the fleet and drive it yourself.
- [Read the Queue](guides/daily/the-queue.md): See what the fleet will work on next, what it is holding back and what is running, and change an issue's priority, labels or comments.
- [Find anything](guides/daily/find-anything.md): Find a filing, an issue, a planning document or a page by its key or its words, and jump anywhere with the palette.
- [Screen what customers send](guides/daily/customer-reports.md): Read a customer's bug report or feature request before any agent does, then approve it, take it up, or turn it away.
- [Review a pull request Fleet opened](guides/daily/review-a-pull-request.md): Hold a Fleet pull request's merge with a review comment or a request for changes, and know how Fleet answers it.

## Plan what gets built

- [Plan what gets built](jobs/plan-the-work.md): Features, slices and PRDs: add a feature, decide where work belongs, what is true when it is done, and what one agent builds.
- [How Fleet plans: one piece of work, start to finish](concepts/how-fleet-plans.md): Follow one real piece of work from a feature request to merged code, and learn the few words Fleet uses on the way.
- [Add a feature and plan its work](guides/plan/add-and-plan-a-feature.md): Add a feature and check the brief Fleet drafts, write the brief of a feature that has none, plan one use or the whole feature, and add more later.
- [Use the Features page](guides/plan/work-by-area.md): Read what each feature is and how far it has got, find what is open and what waits on you, give every slice a feature, and start a slice no program drives.
- [Refine a slice](guides/plan/refine-a-slice.md): Sharpen a slice cut from a brief into a clear Done when, its promises and the bar it is held to, by answering one or two rounds of questions.
- [Fill and design a PRD](guides/plan/fill-and-design-a-prd.md): Turn a PRD stub into a drafted PRD, then a designed one, by answering the fleet's questions and approving its mockup.
- [Read the Programs list, and set its order](guides/plan/read-the-board.md): See where every program stands, narrow the list to what needs you, and set the priority order the fleet works in.
- [Shape a program and hand it to the fleet](guides/plan/shape-a-program.md): Turn a bare program into slices and a proof through a few rounds of questions, then start it so the fleet plans and builds the rest.
- [Do a planning step yourself](guides/plan/do-a-step-yourself.md): Fill, design or plan a PRD in your own session, and tell the fleet so it does not start the same step.
- [Narrow Fleet to your programs](guides/plan/my-programs.md): Name who is responsible for each program, then see only your own programs on the Programs list.

## Work with agent sessions

- [Work with agent sessions](jobs/agent-sessions.md): Open a session, drive it, review what it did, and look in on the fleet's own runs.
- [Sessions: runs, terminals and shells](concepts/sessions.md): A dispatched run works an issue on its own. A session you open is yours to drive. Both run on a machine, each on a branch of its own.
- [Open a session](guides/sessions/open-a-session.md): Start an agent session or a plain terminal on a Fleet machine, in the repository and on the branch you choose.
- [Drive an agent session](guides/sessions/drive-a-session.md): Talk to an agent session: send and queue messages, point it at files, run its slash commands, stop a turn and retry a refused one.
- [Review what a session did](guides/sessions/review-a-sessions-work.md): Read a session's branch and pull request, its changes, the ports it serves and the files in its checkout, without leaving Fleet.
- [Arrange your sessions and use the keyboard](guides/sessions/layouts-and-shortcuts.md): Switch the Terminals page between Grid, Focus, List and Board, jump anywhere with ⌘K, and find every shortcut behind ?.
- [Take a session over, or bring one back](guides/sessions/take-over-and-restore.md): Move a session's one view to this tab, give a terminal its own window, and find or resume a session you closed.
- [Watch a run, and stop or retry one](guides/sessions/watch-a-run.md): Find a run on the Runs page, read its conversation while it works or after, stop one that has gone wrong, and retry an issue that ran out of attempts.
- [Open a shell on a machine](guides/sessions/shell-on-a-machine.md): Get a shell on one of your Fleet machines itself, as its login user, recorded in your name, without opening a session.
- [Reach a session's port from your computer](guides/sessions/reach-a-port.md): Point psql, DBeaver or pgAdmin on your own Windows, Mac or Linux computer at a database a session runs, signed in as you, with nothing opened on the machine.
- [Build an app that runs behind a port link](guides/sessions/build-an-app-behind-a-port-link.md): What an app receives when it is opened with Open ↗, how it learns its public address, and how to test sign-in against the same behaviour in your own CI.

## Connect your own tools

- [Connect your own tools](jobs/your-own-tools.md): Your own MCP servers and tokens in the sessions you open, team secrets for the work, and Fleet's tools in your own terminal.
- [Use your own MCP servers in sessions](guides/your-tools/personal-mcp.md): Give the sessions you open your own MCP servers, such as Confluence, Jira or Figma, with your tokens kept on My secrets.
- [Give every session the same MCP servers](guides/your-tools/shared-mcp.md): Save one list of MCP servers, such as Confluence, on Settings › Shared MCP servers, so every session and run gets them, with their keys on Secrets.
- [Keep your own tokens in My secrets](guides/your-tools/my-secrets.md): Store the personal tokens your own MCP servers need, such as an Atlassian or Figma token, where only your sessions can use them.
- [Team secret or personal secret?](guides/secrets/team-or-personal.md): Decide whether a credential goes on Settings › Secrets, for the work, or on Settings › My secrets, for your own tools, and store it there.
- [Give a session a secret](guides/secrets/attach-a-secret.md): Hand a stored credential to every session on a task, or to one session that is already running, and take it back when you are done.
- [Connect your own AI tool to Fleet](guides/your-tools/connect-your-terminal.md): Let Claude Code, Cursor, VS Code or opencode on your own computer read, file and move issues through Fleet, as you, with nothing installed.
- [Create and revoke API keys](guides/your-tools/api-keys.md): Make a key that lets a tool on your own computer act as you in Fleet, see when each key was last used, and revoke one you no longer trust.
- [Use Fleet's commands in your own Claude Code](guides/your-tools/fleet-commands-locally.md): Load the repository's Fleet commands from .fleet/ into Claude Code on your own computer, for one session, for yourself, or for the whole team.
- [Set up Atlassian's MCP server for Confluence and Jira](guides/services/atlassian.md): Connect Confluence and Jira to your Fleet sessions with an Atlassian API token or service-account key, after an admin turns on API-token sign-in.
- [Set up Figma's MCP server for your sessions](guides/services/figma.md): Connect Figma to your Fleet sessions with a personal access token and the Framelink server, and why the server stays in your own config.

## Set up your team's Fleet

- [Set up your team's Fleet](jobs/set-up-your-team.md): Connect your tracker, GitHub and a model provider, add repositories, and decide how much work each machine takes on.
- [Connect your tracker, GitHub and a model provider](guides/team/connect-github-and-tracker.md): Work through Settings › Set up, its five steps from your tracker to the first worker, until the page says Fleet is ready.
- [Add and configure repositories](guides/team/repositories.md): Add a repository on Settings › Repositories, choose how Fleet uses it, and set who merges, the verify check, notes for agents and the setup command.
- [Choose the models your fleet runs](guides/team/models.md): On Settings › Model config, choose the models the fleet may run, the weighted mix dispatch draws from, models for single steps, and what new sessions open on.
- [Machines, seats and runs](concepts/machines-seats-runs.md): Machines ask Fleet for work, seats say how much each one takes on, and a run is one attempt at one issue.
- [Run machines and set their seats](guides/team/machines-and-seats.md): On Settings › Machines, add a machine, set how many dispatch and interactive seats it runs, drain it, resume it or remove it.
- [Set up the Fleet verify check in your repository](guides/team/verify-check.md): Add a repository, switch on the Fleet verify check, make it required, and see it on a test pull request.
- [Read the Agents page](guides/team/agents-page.md): Use Settings › Agents to see which agents can run in a repository, read any agent's full prompt, and find the slots a repository still has to answer.
- [Recurring work](concepts/recurring-work.md): Write a cadence once in your repository. Fleet files the due work exactly once per window, within a nightly limit, and shows what is next and what was missed.
- [Schedule recurring work](guides/team/recurring-work.md): Write a schedule in your repository's fleet.toml, set the nightly limit on System › Recurring work, and read what is due, waiting or missed.
- [Send bug reports between Fleets with a report key](guides/team/report-keys.md): Make a report key for a customer on Settings › API keys, and paste its connection code on Settings › Send reports in the customer's Fleet.

## Check quality

- [Check quality](jobs/check-quality.md): See which promises a live check has proven, ask for a check, and read the verdict on a pull request.
- [How Fleet knows what has been checked](concepts/quality.md): Every promise your product makes is checked against the live product, the result is written into the repository, and a second session re-grades the checks.
- [Read the Quality desk](guides/quality/quality-desk.md): See which of your product's promises a live check has proven, which are failing, and which nothing checks yet.
- [Ask the QA agent to check a promise](guides/quality/ask-for-a-check.md): Pick a promise nothing checks yet and have Fleet file one check for it, counted against tonight's limit.
- [Read a verify verdict](guides/quality/verdicts.md): What the Fleet verify check on a pull request says, what each verdict does to the issue, and what to do when one is sent back.

## Fix a problem

- [Fix a problem](jobs/fix-a-problem.md): Something is stuck, failed or not merging. Find out why, and do the one thing that moves it.
- [Why is this item not moving?](troubleshooting/why-is-this-stuck.md): An issue sits still. Find out whether it waits on a person, on another issue, on a date or on its attempts, and what moves it.
- [The pull request is not merging](troubleshooting/pr-not-merging.md): A verified change has a pull request that will not land. What Fleet fixes on its own, and the few cases that need you.
- [A run failed](troubleshooting/run-failed.md): An issue reads Failed, or keeps being retried. Read why its runs ended, fix the cause, then Reset & retry.
- [Nothing is being picked up](troubleshooting/fleet-paused.md): Work waits in the queues and no run starts. Read the System page part by part to find what is holding the whole fleet.
- [A machine was drained](troubleshooting/machine-drained.md): A machine takes no new work. Tell a drain someone asked for from one Fleet put on it, and clear or resume each the right way.
- [Recurring work did not run](troubleshooting/recurring-missed.md): A scheduled entry filed nothing. Read its state on System › Recurring work: no nightly limit, waiting for the next night, or missed.
- [A session will not start, or stopped responding](troubleshooting/session-problems.md): A session waits for a box forever, or its terminal stopped answering. What each message means and how to get it back.
- [Send Fleet's team a diagnostics bundle](troubleshooting/send-diagnostics.md): When the other pages do not explain a problem, download one diagnostics file from System and send it to Fleet's team, or report a bug straight from the app.

## Reference

- [Issue positions](reference/issue-positions.md): Every position an issue can be in, what it means, and what the fleet runs from it.
- [Commands](reference/commands.md): Every Fleet command, what it does, what it needs from a person and whether it merges.
- [MCP tools](reference/mcp-tools.md): Every tool Fleet's MCP address serves, what it does and the route it calls.
- [Knowledge file types](reference/knowledge-file-types.md): Every file type a knowledge base registers, where it lives and what it must carry.
- [Slots](reference/slots.md): Every question a command asks a repository, whether it is required, and who answers it.
- [Fleet checks](reference/fleet-checks.md): Every check fleet check runs over a knowledge base, and what each one holds.
- [The fleet.toml file](reference/fleet-toml.md): Every key Fleet reads from a repository's .fleet/fleet.toml, table by table, with defaults.
- [Ids](reference/ids.md): The shape of every id: programs, slices, PRDs, capabilities and requirement prefixes.
- [Glossary](reference/glossary.md): Every planning word and every word of the running loop, each in one place.

## Terms

- [Terms](terms.md): the planning words the pages mark as terms

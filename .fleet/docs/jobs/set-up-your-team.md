# Set up your team's Fleet

An admin sets Fleet up once. This path connects your tracker, GitHub and an AI provider, adds a repository, picks the models, and decides how much work each machine takes on. When you are done, **Settings › Set up** says **Fleet is ready**.

## The big picture

- **Repository.** A codebase Fleet works on. Each one says who merges its pull requests and whether Fleet posts its verify check there.
- **Model config.** The models the fleet may run, and the mix every run draws from.
- **Machine.** A computer running Fleet's worker. It asks Fleet for work; Fleet decides everything else.
- **Seat.** One session at a time on a machine. A dispatch seat works the queue on its own; an interactive seat is where a person runs a session.

**Settings › Set up** walks you through five steps: your tracker, your GitHub App, an AI provider key, a repository and one worker. Its seats set how much it takes on, and **Drain** lets it finish what it holds and take nothing new, for maintenance.

Fleet decides which command runs and which model it uses, so changing either never means updating the machines. Each run gets a model from your mix, chosen only among the models that machine can pay for. Recurring work, such as a nightly audit, is written once in the repository's `fleet.toml` and filed within a nightly limit you set.

## Read these in order

1. **Connect your tracker, GitHub and a model provider** (guides/team/connect-github-and-tracker): Work through Settings › Set up, its five steps from your tracker to the first worker, until the page says Fleet is ready.
2. **Add and configure repositories** (guides/team/repositories): Add a repository on Settings › Repositories, choose how Fleet uses it, and set who merges, the verify check, notes for agents and the setup command.
3. **Choose the models your fleet runs** (guides/team/models): On Settings › Model config, choose the models the fleet may run, the weighted mix dispatch draws from, models for single steps, and what new sessions open on.
4. **Machines, seats and runs** (concepts/machines-seats-runs): Machines ask Fleet for work, seats say how much each one takes on, and a run is one attempt at one issue.
5. **Run machines and set their seats** (guides/team/machines-and-seats): On Settings › Machines, add a machine, set how many dispatch and interactive seats it runs, drain it, resume it or remove it.

## When you need it

- **Set up the Fleet verify check in your repository** (guides/team/verify-check): Add a repository, switch on the Fleet verify check, make it required, and see it on a test pull request.
- **Read the Agents page** (guides/team/agents-page): Use Settings › Agents to see which agents can run in a repository, read any agent's full prompt, and find the slots a repository still has to answer.
- **Recurring work** (concepts/recurring-work): Write a cadence once in your repository. Fleet files the due work exactly once per window, within a nightly limit, and shows what is next and what was missed.
- **Schedule recurring work** (guides/team/recurring-work): Write a schedule in your repository's fleet.toml, set the nightly limit on System › Recurring work, and read what is due, waiting or missed.
- **Send bug reports between Fleets with a report key** (guides/team/report-keys): Make a report key for a customer on Settings › API keys, and paste its connection code on Settings › Send reports in the customer's Fleet.

---
- **seat**: One place on a machine for a session; each seat holds one session at a time.

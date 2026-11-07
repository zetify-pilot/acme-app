# Nothing is being picked up

Fleet has no single pause switch. When nothing starts, one part of the fleet is holding it: no free machine, a provider refusing its key, the tracker not being read. The System page checks each part and says which one.

## What you see

| What you see on System | Likely cause | What to do |
|---|---|---|
| Dispatch: "Work is waiting and nothing starts", and a card "Dispatch is starved" | There is work, and no machine that can take it | Read the cause beside it, then go to Machines |
| Dispatch: "Quiet —" and a reason | Nothing is waiting that a machine could start | Usually nothing. The reason says why |
| Dispatch: "Quiet —" so many "held by a person's open agent session" | People have those items open in their own sessions | Finish or close those sessions |
| A card ending "dispatch paused for" a provider | The model provider keeps refusing Fleet's key | Fix the key or limit with the provider. The pause lifts by itself |
| Machines: few or none online, or some "paused itself" | Machines are off, too old, or drained | See Machines below |
| "Reading" your tracker: "reads failed in a row", "Could not be read" | Fleet cannot read the tracker, so it sees no new work | Check the tracker connection |
| "Writing to" your tracker: "writes not delivered" | Fleet's moves are not reaching the tracker | Check the tracker connection |
| Dispatch: "Nobody is watching dispatch" | The check that watches dispatch has no reading | Send diagnostics |

## Read the System page

[Open System](#system)

The page opens with one sentence for the whole fleet ("Everything is running. Nothing needs you.", or how many things need you), then one card per part. Each part is marked **OK**, **ATTENTION**, **PROBLEM** or **NOT SET UP**. Start with the parts marked PROBLEM.

The parts that decide whether work is picked up:

- **Dispatch.** Whether anything is starting, and if not, why. "Picking up work" means it is.
- **Machines.** How many are online and how many are working.
- **Reading** your tracker (the heading names it: Linear, GitHub Issues or Jira). Whether Fleet can see the work.
- **Writing to** your tracker. Whether the moves Fleet made have reached it.
- **Safety limits.** The controls that stop work when a threshold is crossed.

The page also has Background jobs and Recurring work; for the second see [Recurring work did not run](troubleshooting/recurring-missed).

## Work is waiting and nothing starts

The Dispatch part reads "Work is waiting and nothing starts" and the page raises "Dispatch is starved". The line under it names what holds the machines, the biggest cause first, with counts.

1. [you] **Read the cause.** It names, for example, how many machines are being taken out of service or are full.
2. [you] **Open Machines.** On [System › Machines](#system:machines), the "Held back" filter shows what keeps each machine from being given work.
3. [you] **Fix what it names.** A drained machine: [A machine was drained](troubleshooting/machine-drained). A machine too far behind the control plane gets no work until it updates. A machine with no repository cloned, or none it may push to, has nowhere to run.
4. [fleet] **Work starts.** As soon as one machine is eligible and free, the next issue goes to it.

The glossary on the Docs reference pages lists every reason a machine cannot take work, with what each one means.

## A provider refused the key

A card reads like "OpenRouter key refused: daily limit — dispatch paused for" the engine and provider. The provider refused Fleet's credential several launches in a row on more than one machine: a spent key or limit, an authentication refusal, or a rate limit. Work that needs that provider is held off every machine; other providers keep working.

1. [you] **Fix it with the provider.** Top up the account, raise the limit, or replace the key.
2. [fleet] **It lifts by itself.** Every few minutes Fleet lets one run through to test the provider. When the provider accepts, the pause ends. There is no button, and none is needed.

## The tracker is not being read or written

If Fleet cannot read the tracker, it does not see new work or new positions, so nothing new is offered. If writes are not delivered, the tracker does not show the moves Fleet has made; Fleet keeps them in its outbox and delivers them when the tracker accepts again.

1. [you] **Open the part.** On its card, press the link to its details: the failing reads or writes and what the tracker answered.
2. [you] **Check the connection.** Make sure Fleet's access to the tracker still works. See [Connect GitHub and your tracker](guides/team/connect-github-and-tracker).
3. [fleet] **It catches up.** The next successful read picks up the board; queued writes are delivered.

"The board shrank on the last read" or "The board's state names changed" means the read worked but what came back looks wrong, for example a workflow state was renamed in the tracker.

## Safety limits

Each limit shows **on** (it stops work when its threshold is crossed), **off** (no threshold is set, so nothing stops on it) or **retired** (kept for history; nothing to do), and when it last fired. A limit that fired recently explains a sudden stop. Thresholds are set on your Fleet service, not on this page.

> **Careful:** If Dispatch reads "Nobody is watching dispatch", Fleet's own check is not reporting, so the page cannot tell you whether work is moving. [Send diagnostics](troubleshooting/send-diagnostics) to Fleet's team.

Next: A machine was drained (troubleshooting/machine-drained) · Why is this item not moving? (troubleshooting/why-is-this-stuck) · Send Fleet's team a diagnostics bundle (troubleshooting/send-diagnostics)

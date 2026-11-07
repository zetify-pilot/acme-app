# Fix a problem

Start from what you see. Something that is not moving is almost always waiting for something specific, and Fleet says what. Each page here starts from a symptom, shows where Fleet names the cause, and says what to do about it.

## The big picture

- **Held back.** The Queue view of everything that is not running and not ranked next. Each row says what it waits for.
- **Failed.** Where an issue stops after its runs kept failing. It waits for a person to fix the cause and press **Reset & retry**.
- **System.** The page that checks each part of the fleet, such as dispatch, machines and your tracker, and marks it **OK**, **ATTENTION**, **PROBLEM** or **NOT SET UP**.
- **Drain.** A machine that finishes what it holds and takes nothing new, because someone asked or because it kept failing.

Work out how wide the problem is, then look in the right place. One issue sitting still: read the reason on the issue itself. It waits on a person, on another issue, on a date, or on its attempts. One run that ended badly: the reason on the run's page says whether the problem is the work or the machine. Nothing starting anywhere: open **System** and begin with the parts marked **PROBLEM**.

Fleet notices most stalled pull requests on its own and sends the issue back to an agent with the reason. It hands you only the cases a person must settle. If no page here explains what you see, download a diagnostics file from **System** and send it to Fleet's team.

## Read these in order

1. **Why is this item not moving?** (troubleshooting/why-is-this-stuck): An issue sits still. Find out whether it waits on a person, on another issue, on a date or on its attempts, and what moves it.
2. **The pull request is not merging** (troubleshooting/pr-not-merging): A verified change has a pull request that will not land. What Fleet fixes on its own, and the few cases that need you.
3. **A run failed** (troubleshooting/run-failed): An issue reads Failed, or keeps being retried. Read why its runs ended, fix the cause, then Reset & retry.
4. **Nothing is being picked up** (troubleshooting/fleet-paused): Work waits in the queues and no run starts. Read the System page part by part to find what is holding the whole fleet.

## When you need it

- **A machine was drained** (troubleshooting/machine-drained): A machine takes no new work. Tell a drain someone asked for from one Fleet put on it, and clear or resume each the right way.
- **Recurring work did not run** (troubleshooting/recurring-missed): A scheduled entry filed nothing. Read its state on System › Recurring work: no nightly limit, waiting for the next night, or missed.
- **A session will not start, or stopped responding** (troubleshooting/session-problems): A session waits for a box forever, or its terminal stopped answering. What each message means and how to get it back.
- **Send Fleet's team a diagnostics bundle** (troubleshooting/send-diagnostics): When the other pages do not explain a problem, download one diagnostics file from System and send it to Fleet's team, or report a bug straight from the app.

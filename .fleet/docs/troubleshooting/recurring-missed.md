# Recurring work did not run

Recurring work is filed from the schedule in your repository's `fleet.toml`, up to a nightly limit someone sets in Fleet. When an entry filed nothing, its state on the Recurring work page says why, and only one of the reasons loses the work.

## What you see

| What you see | Likely cause | What to do |
|---|---|---|
| "Not set. Fleet files no recurring work until a limit is set." | Nobody has set the nightly limit | Set it |
| "No recurring entries." | The merged `fleet.toml` has no `[fleet.recurring]` entry | Add one to `fleet.toml` and merge it |
| An entry's State reads **waiting** — "the nightly limit was reached" | More was due than the limit allows in one night | Nothing, or raise the limit |
| An entry's State reads **missed** — a time, "nothing filed" | Fleet passed that window without filing it | File that one by hand if you need it |
| The entry you expect is not in the table | It is not in the merged `fleet.toml` | Check the schedule in the repository |

## Open Recurring work

[Open Recurring work](#system:recurring)

On the System page, the Recurring work part reads "Up to" so many "issues a night", or "No nightly limit". Its own page shows the limit and a Schedule table with one row per entry: Entry, Cadence, Last ran, Next due, State. **on schedule** means the current window was filed.

## No nightly limit

There is no default. Until someone sets a limit, Fleet files no recurring work at all.

1. [you] **Set the limit.** In "Issues Fleet may file each night", enter a whole number in the range the hint gives. It applies to every entry in the schedule.
2. [you] **Save.** The page says "Saved. The new limit applies from the next check." The change is recorded under your name.
3. [fleet] **Entries start filing.** From the next check, each entry is filed when it is due.

## Waiting

The night's limit was reached before this entry was filed. Nothing is lost: waiting entries are filed the next night, oldest first. If entries wait every night, the limit is lower than what your schedule asks for; raise it, or space the schedule out in `fleet.toml`.

## Missed

Fleet passed that window and filed nothing. A missed window is never filed later on its own; the next window is filed as usual. If the missed work matters, file it yourself with [File work](guides/daily/file-work).

> **Careful:** Changing the limit does not bring back a missed window, and changing the schedule only takes effect once it is merged to your repository. The schedule says what recurs; the limit, set on this page, says how much may land in one night.

The schedule's format is in the fleet.toml reference.

Next: Schedule recurring work (guides/team/recurring-work) · Recurring work (concepts/recurring-work) · Nothing is being picked up (troubleshooting/fleet-paused)

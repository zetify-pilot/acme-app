# Who decides what

Fleet will build whatever it is handed, so the question that matters is whether the product already committed to it. Fleet settles everything else itself. It stops for a person in a few clear cases, and every one of them lands in your Cockpit.

## The one call that is always yours

Only a person promises something new. When a feature request is routed, Fleet proposes what it is and where it goes, and creates nothing until you press **Create it**. When the triage check finds that a filed issue would add new customer-facing functionality, it does not queue it. It brings it to you as a call.

Defects, internal work and work the product already promised do not wait for you. The check releases them to the fleet itself.

> **Why:** The agent that found a piece of work is the wrong party to judge whether it should be built. The check runs in a fresh session that never saw the filing, and the one call it may not make is a new promise.

## The ways Fleet waits on you

| What you see | Position | What you do |
|---|---|---|
| A question a run stopped on | `Blocked · decision` | Answer it. The fleet is stopped on it until you do. |
| An interview question about a feature request you filed (kept by Fleet, not in your tracker) | `Needs answer` | Reply. Only your own item waits; nothing else is blocked. |
| A proposal for a feature request, a new feature or a plan, waiting for your verdict (kept by Fleet) | `Intake · decision` | Accept it, send it back, or park it, on its page. |
| Something no agent can do, such as creating a credential or clicking a console | `Blocked · action` | Do it, then mark it done. |
| A pull request a person must merge | `Awaiting merge` | Merge it. |
| Work that kept failing | `Failed` | Read why, then reset it so the fleet tries again. |

The answer to a question goes back to the session that asked. An answer to a check's escalation sends the issue back to the check, never straight to building, so the check finishes the triage it started.

## Your Cockpit

The **Cockpit** is the one list of everything that waits on a person, one row per item. Each row says what it is, the exact ask, who it is assigned to, and since when.

- **Waiting** lists what waits on a person; the sidebar count is the part assigned to you.
- **Filter** narrows it, for example to **Assignee** is **Me**, or **Asking for** is **Decide**, **Approve** or **By hand**.
- Opening a row opens the item's own page, where you answer or decide.
- **Snooze…** sets an item down until a date, or until you say so, with your reason. It leaves every count for everyone; a dated snooze comes back by itself.

See [Work through the Cockpit](guides/daily/cockpit).

[Open the Cockpit](#cockpit)

## Doing it yourself

Sometimes you want to do a piece of work yourself. Take it by hand and it moves to `Human WIP`. Every dispatcher leaves a `Human WIP` issue alone. When you are done, hand it back to a queue, or to a verifier if you opened a green pull request.

A person-owned park is left only by a person. If anything other than your answer or your act moves an issue out of `Blocked · decision` or `Blocked · action`, Fleet puts it back and shows it. One exception: a `Blocked · action` park that names a condition Fleet can check, such as a merge it waits on, is lifted by Fleet once that condition holds.

Next: Answer a question (guides/daily/answer-a-question) · Take work by hand (guides/daily/take-it-by-hand) · Work through the Cockpit (guides/daily/cockpit)

---
title: "Fix a failing knowledge check"
kind: guide
for: [developer]
summary: "Read what fleet check printed, find the file and the fix it names, and get your pull request green without weakening the check."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/cli.py
  - packages/fleet-knowledge/src/fleet_knowledge/runner.py
  - packages/fleet-knowledge/src/fleet_knowledge/checks/planning/tracking_metadata.py
  - packages/fleet-knowledge/src/fleet_knowledge/checks/structure/_journeys.py
  - packages/fleet-knowledge/src/fleet_knowledge/checks/slots/_slots.py
minutes: 5
---

:::lede
When you are done, `fleet check` passes on your branch, the problem it named is fixed at its cause, and nothing was added to a list of exceptions to make it go quiet.
:::

## Run it where you can read it

The knowledge checks run in your build, but the output is easier to read on your own machine. In your checkout:

```sh
fleet check
```

It prints one line per check, then the findings under each one that has any:

| Line starts with | Means |
|---|---|
| `ok` | Passed. |
| `FAIL` | At least one error. This is what turns a build red. |
| `note` | Warnings or advisories only. The build stays green. |
| `skip` | Does not apply to this repository, with the reason. A repository without journeys is not broken. |

It ends with a count, for example `31 check(s): 15 passed, 1 failed, 4 noted, 11 skipped, 0 disabled — 7 finding(s)`. It exits 0 when nothing fails, 1 when something does, and 2 when the command itself was wrong.

## Fix one finding

:::steps
- [you] **Find the error.** Under the `FAIL` line, each `[error]` names a file and, where it can, a line, such as `knowledge/slices/rows/SL-012.json:1:` followed by the message. Read the sentence after it; it says what is wrong in plain words.
- [you] **Read the fix it names.** A finding carries a `fix:` line saying what to change, and sometimes a `run:` line with a command that does it for you.
- [you] **Fix the cause.** Change the file it names. If the finding is about code, the fix is usually in the knowledge file that describes the code, not in the code.
- [you] **Run only that check.** Give it the name from the `FAIL` line, for example `tracking-metadata`, and repeat until it reads `ok`:

  ```sh
  fleet check --only tracking-metadata
  ```
- [you] **Run them all once more, then push.** One fix can surface the next finding in another check.
:::

## Findings you will meet often

| What it says | What to do |
|---|---|
| `SL-… names no area — every new or changed slice names the feature area it belongs to` | Add `area` to the slice, with the slug of the feature map it belongs to. On an untouched slice that names a program, the same gap is only a note (`needs an area`). |
| `… joins program …, but this repository plans by area` | Take `program` off the new slice and keep it under its area. |
| a map "has no brief", "is cut into N use(s)", or has capability rows "under no use" | A feature map needs a brief and its capability rows under a few uses. Write the brief, cut the rows into uses, and park any row that fits none under `### Misfits (to move)`. See [Features, uses and capabilities](knowledge-base/feature-areas). |
| a brief or use "states ship-state" or "names internal ids bare" | Take the word ("shipped", "planned", "partly built", "still open") or the number out. Progress is read from the plans, and the prose says what a person does, in plain words. |
| unclaimed code path `…` | A new code file no feature map claims. Add it to the `source_of_truth:` of the map that describes it. |
| `/… cannot run in this repo — unfilled required slot(s)` | Write the answer the slot points at. See [answering the slot questions](guides/knowledge/fill-slots). |

:::callout{kind="careful"}
Some checks keep a baseline file of known exceptions, and a `run:` line may offer to rewrite it. A baseline may shrink, never grow: adding your new problem to it turns a real gap into one nobody will look at again. Fix the file instead, unless a person has agreed the exception.
:::

## When the output is too long

Show errors only:

```sh
fleet check --level error
```

List every check with what it enforces:

```sh
fleet check --list
```

Print the findings as JSON, for a script:

```sh
fleet check --json
```

Print which knowledge folder the checks read, and why. Run it first when a finding names a file you do not recognise: the checks may be reading a different folder than you think.

```sh
fleet config
```

::cards{links="guides/knowledge/keep-maps-current, troubleshooting/pr-not-merging"}

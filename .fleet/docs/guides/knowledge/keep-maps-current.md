# Keep your feature maps true to the code

When you are done, the feature map for the code you changed lists what the product really does today, names the files it describes, and still says why the area exists in the words a person wrote. Your pull request passes the knowledge check.

## What a feature map holds

Each feature area has one map under `knowledge/features/`, `<area>.md`. It has two parts, and they are kept differently:

| Part | What it is | Who may change it |
|---|---|---|
| The **Intent** paragraph | Why the area exists: who it is for and what job it does. | A person, on purpose. |
| The **brief** and the uses | What the feature is, and the three to six things a person does with it. | Written with the map; changed when a use no longer describes its rows. Never its summary or problem without a person. |
| The ledger | The capability rows, each under the use it serves, the pages it surfaces on, and `source_of_truth:`, the list of code paths the map describes. | Anyone, whenever the code says it is wrong. |

> **Careful:** Code can tell you whether a capability exists and whether it is reachable. It can never tell you why the feature should exist. Correct the ledger to match the code; never rewrite the Intent to describe the code.

## When you change code

1. [you] **Find the map.** Look for the map whose `source_of_truth:` lists the file you changed. `python3 knowledge/scripts/component_of.py <path>` names the component that owns a file.
2. [you] **Correct the facts in the same pull request.** A capability you delivered gets its row marked shipped the way the map's own rows record it. A route that moved gets its new address. A renamed file gets its new path in `source_of_truth:`.
3. [you] **Put a new row under its use.** A capability you add goes under the use it serves. If it fits none, follow [When nothing fits](knowledge-base/feature-areas); a map that has no brief yet gets one in the same change.
4. [you] **Claim a new file.** A new file under the code the maps cover must be listed in some map's `source_of_truth:`. A file no map claims fails the check.
5. [fleet] **The check reads it.** The `journeys-and-features` check runs with every knowledge check, locally and in CI.

The commands that build things in Fleet do this as part of the change: an agent that delivers a capability marks its row in the same pull request. You only do it by hand for work you write yourself.

## What the check fails on

- **A file no map claims.** A code file under a folder the maps cover, which is not one of the reviewed exclusions (tests, generated code, scripts and the like). Claim it in the map that describes it.
- **A path that is not there.** A `source_of_truth:` entry naming a file that was moved or deleted. Point it at the new path.
- **A map with no paths.** Every map must list at least one; a map that names none can never be told its code changed.

Run it before you push:

```sh
fleet check --only journeys-and-features
```

The finding says which file and what to do, and the [failing-check guide](guides/knowledge/fix-a-failing-check) covers reading it.

[Open Knowledge](#knowledge)

Next: Features, uses and capabilities (knowledge-base/feature-areas) · Capabilities and components (knowledge-base/capabilities-and-components) · Fix a failing knowledge check (guides/knowledge/fix-a-failing-check)

---
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.
- **capability**: One concrete thing the product lets a person do, small enough to check at any time and still true tomorrow; it sits under one use of a feature, is shipped by a PRD, and never finishes.

---
title: "Run the knowledge checks in your CI"
kind: guide
for: [developer]
summary: "Add one GitHub Actions job that runs fleet check on every pull request, so a broken knowledge base fails the build before it merges."
sources:
  - knowledge/scripts/fleet.py
  - packages/fleet-knowledge/src/fleet_knowledge/cli.py
minutes: 4
---

:::lede
When you are done, every pull request runs `fleet check`, and a knowledge base that breaks a check turns the build red before it can merge.
:::

## Add the workflow

Create `.github/workflows/knowledge-checks.yml` in your repository and commit it:

```yaml
name: Knowledge checks

on:
  pull_request:

jobs:
  fleet-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run fleet check
        run: python3 knowledge/scripts/fleet.py check --repo .
```

The checkout brings the `fleet/` submodule with it, because that is where the checks live. The job then runs the `fleet.py` script Fleet writes into `knowledge/scripts/`. `fleet check` reads the `knowledge/` folder and exits 0 when every check passes. It exits 1 when any check fails, and the job fails with it.

:::callout{kind="tip"}
If your repository pins Fleet's source as a private submodule, the checkout needs a token that can read it. Add `token: ${{ secrets.FLEET_READ_TOKEN }}` under the checkout's `with:`, and save that token as a secret under **Settings › Secrets and variables › Actions**.
:::

## What the checks look at

`fleet check` reads the `knowledge/` folder and checks that it is well formed and connected:

- the planning record: every :term[slice], :term[PRD] and :term[program] is named and resolves.
- the :term[feature map]s, their uses and the capability rows under them.
- the requirement :term[register]s and the decisions beside them.
- the code each feature map says it describes, so a new file is claimed by a map.
- the answers a :term[slot] gives, before a command can run here.

The full list, with what each check enforces and why, is in [Fleet checks](reference/fleet-checks).

## When the build goes red

The job prints the same lines `fleet check` prints on your machine. `FAIL` marks a check that found an error, and the findings under it name the file and the fix. Fix the cause, commit, and push; the job runs again.

[Fix a failing knowledge check](guides/knowledge/fix-a-failing-check) walks through one finding, from the `FAIL` line to a green run.

::cards{links="reference/fleet-checks, guides/knowledge/fix-a-failing-check"}

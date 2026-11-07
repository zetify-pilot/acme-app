# Add and configure repositories

When you finish this guide, the repository you want Fleet to work in has a card on Settings › Repositories. You will have decided who merges its pull requests, whether Fleet posts its verify check there, and what agents should know before they start.

## The page

**Settings › Repositories** lists every repository Fleet works in under **Fleet works here**, and the repositories agents may only read under **Reference only**. Fleet reaches a repository only when your GitHub App is installed on it, so connect the App first ([Connect your tracker, GitHub and a model provider](guides/team/connect-github-and-tracker)).

On the Repositories page (#settings:repositories):
1. A repository's card: its name, how Fleet uses it, and whether it is ready. **Issues** says which issues belong to it.
2. **Merging** says who merges its pull requests. Change it under **Settings** on the card.
3. **Verify check** says whether Fleet posts its check on the repository's pull requests.
4. **Add a repository** opens the form.

The first card is the default lane: issues with no `repo:` label belong to it. Every other repository owns the issues labelled `repo:<its name in Fleet>`.

## Add a repository

1. [you] **Name it.** Click **Add a repository** and type the **Repository** as GitHub spells it, for example `acme/payments`. Fleet calls it by its own name. Open **Use a different name** only when two of your repositories share a name.
2. [you] **Choose how Fleet uses it.** Under **How Fleet uses it**, pick one of three answers. Fleet reads the repository's default branch and suggests one.
3. [you] **Add it.** Click **Add repository**. If the GitHub App is not installed on that repository yet, the form says so and links to the App's install page on GitHub.
4. [fleet] **Fleet creates its tracker label.** A repository that takes work gets the label its issues are routed by. If Fleet cannot create the label, the card says exactly what to fix.
5. [you] **Merge the setup pull request.** A **Fleet project** with no planning record gets a setup pull request from Settings › Set up, step 4. Read it and merge it yourself.

| | Fleet project | Work here, no Fleet files | Reference only |
|---|---|---|---|
| Agents work here | Yes | Yes | No |
| Fleet's commands and plan live here | Yes | No | No |
| Fleet verify check | Yes | Yes | No |
| What it is for | Fleet's files live here; Fleet runs its commands and reads the plan | Issues, terminals, pull requests and Fleet verify, with no Fleet folder | Every session and run may read it; Fleet does no work here |

You can change the answer later from the card's **⋯** menu with **Change role…** at any time. Making a repository **Reference only** stops all work there and deletes the GitHub ruleset Fleet created to require its verify check.

## Set who merges and the verify check

Click **Settings** on the card. The panel's sentence at the top describes, in words, what your current answers mean together. The **Merging & review** tab holds:

- **Who merges**: **Agents**, **A person**, or **A person, for some paths**. With **Agents**, a pull request merges only after its checks are green and Fleet's verifier has signed off. With **A person, for some paths**, list the **Paths a person merges**, one per line. **Except pull requests that change only these paths** lets a narrow change merge without a person.
- **Fleet verify check**: **Post the check on pull requests**. This check turns green when Fleet's independent verifier signs off on the change.
- **Is the check required by the repository?** Answer **Yes, a ruleset requires it** only when a GitHub ruleset on the repository really does require the check. Fleet then turns on auto-merge as soon as a bug's or task's pull request opens, and GitHub still waits for the verdict.
- **Reviewer comments**: **Send to an agent** returns each open comment from someone who can write to the repository to an agent, once. **Leave to the merger** means Fleet does not read them.

Click **Save**. A change that loosens how the repository merges (for example from **A person** to **Agents**) opens a second box, **Loosen how this repository merges?**, that lists what loosens. Nothing is saved until you click **Loosen it**.

> **Careful:** Fleet requires **Fleet verify** on every lane: it creates a ruleset on the repository's default branch, so GitHub itself refuses a merge with no independent verdict, by any path. That is the promise that the party who wrote the change never certifies it. You can still make it required at once with **Make Fleet verify required** on Settings › Set up, step 4, without waiting for Fleet's next pass.

For the steps from start to finish, see [Set up the Fleet verify check in your repository](guides/team/verify-check).

## Tell agents how to work here

The **Agents** tab:

- **Which work uses Fleet's commands** (Fleet projects only): **Every kind**, or **Only some kinds** with the kinds listed. Other kinds use Fleet's general instructions.
- **Prepare a fresh checkout**: a **Command that prepares a fresh checkout**, for example `make deps`. It runs once in each new checkout, before an agent starts.
- **Notes for agents**: conventions, CI quirks, hazards. Agents read them with every task in this repository.

A Fleet project also has a **Plan** tab: the **Branch** and **Folder** Fleet reads the plan from, and the **Name of the top level** the board uses. Under **Advanced** you list the **Other repositories verify may read**, and **Changes to this repository** shows who changed what, and when.

## Rename or remove a repository

Both are in the card's **⋯** menu. **Rename in Fleet…** changes the name Fleet uses on the board, in links and in labels. Everything filed under the old name moves with it, and Fleet will not rename a repository while work is running in it. **Remove from Fleet…** stops all filing and dispatching there, stops reading its plan and deletes the **Fleet verify** ruleset Fleet created. Issues stay in your tracker, and you can add the repository again later.

[Open Repositories](#settings:repositories)

Next: Connect your tracker, GitHub and a model provider (guides/team/connect-github-and-tracker) · Read the Agents page (guides/team/agents-page) · Why a second session verifies every change (concepts/verify-before-merge)

# Connect your tracker, GitHub and a model provider

When you finish this guide, Settings › Set up says **Fleet is ready**. Your issue tracker, your GitHub App, an AI provider key, a repository and one worker are connected, so an issue your team files can become a pull request that Fleet wrote and checked.

## The checklist

Open **Settings › Set up**. The page is called **Get Fleet ready**. It lists five steps, and each step shows one state: **To do**, **In progress**, **Needs you** or **Ready**. The band above the list counts what is left, for example "2 steps before Fleet can work." Click a step's title to open it. The first unfinished step is already open.

[Open Set up](#settings:set-up)

1. [you] **Connect your issue tracker.** Choose Linear, GitHub Issues or Jira, then let Fleet add the states or labels it reads.
2. [you] **Connect your GitHub App.** Fleet works on your repositories as a GitHub App that belongs to you. You can create a new App or connect one you already have.
3. [you] **Add your AI provider key.** Save an OpenRouter key and tick the models your agents may run on.
4. [you] **Add a repository.** Name the repository Fleet works in. A new one gets a setup pull request, which you review and merge.
5. [you] **Add a worker.** Run one command on a Linux machine you own. The step turns Ready when the machine's seats report.
6. [fleet] **Fleet says it is ready.** Once all five steps are Ready, the band turns green and offers **File a task** and **Report a bug**.

## 1. Connect your issue tracker

At the top of the step, choose **Linear**, **GitHub Issues** or **Jira**. If your installation has already chosen the tracker, the choice is locked and the step says so.

Whichever tracker you pick, Fleet moves an issue by where it sits on the board, so it needs its own states or labels there. Setup only adds what is missing and never renames or deletes anything you already have.

**Linear.** Paste a **Linear API key** and click **Check and save**. Fleet makes sure the key can see your teams before it keeps it. Then click **Choose your team**, pick the **Team Fleet works from**, and click **Set up this team**. Fleet adds the workflow states and labels the team lacks and shows you exactly what it added. Running it again adds nothing.

**GitHub Issues.** Connect the GitHub App first (step 2). Then click **Choose the issue repository**, pick the **Issue repository**, and click **Set up labels**. Fleet creates its lifecycle, kind and lane labels there. It never deletes, renames or recolours a label you have. If you add labels later, **Run setup again** adds only the missing `fleet:` labels. The issue repository must be one of the repositories Fleet works in, or Fleet never dispatches work for it. The step warns you when it is not.

**Jira.** Fleet connects to Jira Cloud only. Enter the **Jira site address** and choose how Fleet signs in:

- **API token**: an **Account email** and an **API token** made by that account. Everything Fleet writes in Jira appears under this account's name, so a dedicated account reads best.
- **OAuth service account**: a **Client ID** and a **Client secret**. The step includes the instructions for creating the service account in Atlassian's admin pages. Click **Test connection** to try the credentials before you save them.

Click **Check and save**. Then pick the **Jira project** and click **Check this project**. Fleet picks up only the issues in that project that carry a `fleet:` label.

If the project requires a field Fleet does not fill itself, such as a custom "Release Notes Required" field, the check lists it under **Required fields** with a box for the value Fleet should write. That covers fields Jira asks for when an issue is **created** and fields it asks for when an issue is **moved** (a status screen or a workflow rule). A field Jira refused a move over, and that the check could not see beforehand, appears in the same list as soon as the refused write is parked, and the write goes through on its next check once you save a value. Fleet sets a field that only a workflow rule asks for with an ordinary edit of the issue before the move; if Jira shows that field on neither the move screen nor the edit screen, Fleet cannot set it and the refusal says a Jira admin has to add it to one of them. Until a field has a value, Fleet says which field is missing, not that a status or label does not exist.

## 2. Connect your GitHub App

Choose one of the two options:

- **Create a GitHub App.** Say **Who owns the App** (**An organisation** or **My personal account**), and fill in the **Organisation** and **App name** fields. Click **Create App on GitHub →**, confirm on GitHub and come back. You never copy a key. To see what the App will be allowed to do, open **What the App may do**.
- **Connect an existing GitHub App.** Enter the **GitHub host**, the **App ID** and the **Private key (.pem)**. You can upload the file or choose **Paste the key instead**. Click **Check App**. Fleet asks GitHub about the App and lists any permission it lacks, and nothing is saved yet. Then click **Connect App**.

Next, install the App on the repositories Fleet may work in: click **Install on repositories ↗** and choose them on GitHub. They appear on the step on their own shortly afterwards. If the App is missing a permission Fleet needs, the step names it by GitHub's own label. An owner of the organisation must then accept the change on GitHub.

The step also shows a **GitHub App permissions** panel: every permission Fleet needs, the level it needs, the level the installation actually has, and a marker — **Missing**, **Too low** or **OK** — with the gaps first. When anything is missing, a line above the table says how many and where to grant them (a link opens the App's settings page on GitHub). If Fleet could not read what the installation grants, or the App is not installed anywhere yet, the panel says that instead of showing a tick. The panel only reads; you change permissions on GitHub.

**Pull requests: Read and write** is also what lets Fleet hold a merge when a reviewer asks for changes: it turns off auto-merge or takes the pull request out of the merge queue. On an App created before this was needed, grant it once: GitHub → Settings → GitHub Apps → your Fleet app → Permissions & events → Pull requests → Read and write, save, then open the installation (Settings → Applications, or the organisation's Installed GitHub Apps) and accept the update. Until you do, the held pull request's wait says Fleet's GitHub App needs 'Pull requests: write' to hold a merge.

## 3. Add your AI provider key

Paste an **OpenRouter API key** and click **Check and save**. Fleet checks the key with OpenRouter and then lists only the models that key may use. Under **Model your agents run on**, tick one or more models and click **Save choice**. Fleet ships no default model: a run uses only the models you tick. To weight the models or give a step its own model, see [Choose the models your fleet runs](guides/team/models).

## 4. Add a repository

Repositories are added and removed on **Settings › Repositories** ([Add and configure repositories](guides/team/repositories)). This step shows how each one is doing.

A repository that is a Fleet project and has no planning record yet shows two fields: **Product name** and **First outcome**. The first outcome is one sentence describing what you want the fleet to work towards first. Click **Open setup pull request**. Fleet opens one pull request that adds the planning record and the core commands. Read it and merge it on GitHub. The step turns Ready once it has merged.

> **Why:** Fleet never merges the setup pull request itself. It is the first change Fleet makes to your repository, so a person reads it first.

Fleet makes **Fleet verify** required on every repository it serves: it creates a ruleset on the default branch, so GitHub refuses a merge with no independent verdict by any path. If the step offers **Make Fleet verify required**, clicking it does that at once instead of waiting for Fleet's next pass. You can switch that ruleset off on GitHub later.

## 5. Add a worker

A worker is a Linux machine you own. It takes work from the queue and hosts live terminals. Click **Add worker**. The panel that opens is the same one Settings › Machines uses, described in [Run machines and set their seats](guides/team/machines-and-seats). The step turns Ready once the machine's dispatch seat and terminal seat both report.

## Customer reports

Under the checklist, **Customer reports** decides whether a report a customer filed waits for a person on your team before any agent reads it. Choose **Hold customer reports for a person** and name the **Label that marks a customer report**, or choose **Off**. Turning it off asks you to confirm first. Click **Save**. The section shows who changed it last, and when.

Next: Add and configure repositories (guides/team/repositories) · Choose the models your fleet runs (guides/team/models) · Run machines and set their seats (guides/team/machines-and-seats)

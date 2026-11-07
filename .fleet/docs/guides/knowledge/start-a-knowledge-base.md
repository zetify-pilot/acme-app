# Start a knowledge base in a repository

When you are done, your repository holds a small knowledge base Fleet can read: the product's name, the first thing your team wants done, a folder for PRDs, an empty requirement register, and the commands your agents run. Fleet's board shows the repository from the next sync on.

## Two ways to do the same thing

Both ways write the same files. Pick the one that fits how you work.

- **From Fleet**, if the repository is already added under **Settings › Set up**. Fleet opens one pull request; you review it and merge it.
- **From a terminal**, with the `fleet` command, if you would rather see the files on disk first and commit them yourself.

Neither ever overwrites a file your repository already has. A file that exists is kept and reported, and running either a second time writes nothing.

## From Fleet: the setup pull request

1. [you] **Open Set up.** Go to **Settings › Set up** and open step 4, **Add a repository**. A repository that has no planning record yet shows a short form.

   [Open Set up](#settings:set-up)
2. [you] **Name the product.** In **Product name**, write what the board should call the product this repository builds.
3. [you] **Say what you want first.** In **First outcome**, write one sentence: the first outcome you want the fleet to work towards. In a new repository it becomes the first slice, in the **product** feature area.
4. [you] **Press Open setup pull request.** Fleet opens one pull request in the repository with the planning record and the core commands.
5. [you] **Review it and merge it.** The step reads *setup pull request #… is open — review and merge it* until you do.
6. [fleet] **The board picks it up.** After the next sync the step is ticked and the board shows the repository's first slice.

## Get the `fleet` command

`fleet init` comes from Fleet's `fleet-knowledge` package. Install that package before you run `fleet init`.

On your own machine, and in a Fleet terminal session, run:

```sh
uv tool install git+https://github.com/ZetifyAI/fleet#subdirectory=packages/fleet-knowledge
```

`uv` puts `fleet` on your PATH. In a Fleet terminal session, `uv` is already installed. If you have a Fleet checkout, use `uv tool install -e ./packages/fleet-knowledge` so the command follows that checkout.

Some machines already have a different program named `fleet`, for example a Linux package. Run `fleet --help` to check. The right command lists `config`, `check`, `board` and `planning`. If it does not, the install above did not reach your PATH. Run `~/.local/bin/fleet --help`, or add `~/.local/bin` to your PATH.

## From a terminal: `fleet init`

Run it at the root of your checkout:

```sh
fleet init
```

It asks three things when you run it in a terminal, and refuses to guess when you run it from a script (then pass them as flags):

| It asks | Flag | What to give |
|---|---|---|
| The product's name | `--product` | e.g. `Payments` |
| The first thing the team wants done | `--slice` | One sentence. It becomes the first slice, in the `product` area. |
| The command namespace | `--namespace` | The prefix your commands are typed with. Press Enter for the default. |

Two more flags are worth knowing. `--detect` looks at the files in the repository and fills in how it is linted, tested and built; `--stack` names those stacks yourself. `fleet init` then prints every file it wrote, every file it kept, and anything it could not finish, with the lines to add.

Commit what it wrote and open a pull request the way your repository usually does.

## What you get

| Where | What it is |
|---|---|
| `knowledge/slices.md` | Your first slice. |
| `knowledge/programs.md` | An empty program register. |
| `knowledge/prds/` | Where PRDs go. |
| `knowledge/requirements/product.md` | The register for what the product promises. |
| `knowledge/strategy/product-vision.md` | What the product is for. |
| `knowledge/slots/` | Your answers to the questions the commands ask about this repository, starting as placeholders. |
| `.fleet/` | The commands, and `.fleet/fleet.toml`, Fleet's settings for this repository. |
| `knowledge/scripts/` | The scripts the commands run. |

A new repository plans by feature area: `.fleet/fleet.toml` says `mode = "areas"` and `require_area = true`, so every slice must name the area it belongs to.

> **Careful:** The files under `.fleet/` and `knowledge/scripts/` belong to Fleet. Don't edit them by hand: `fleet commands sync` writes them again when Fleet updates, lists every file changed since it last wrote it under **HAND-EDITED**, and replaces it. To keep your own version of a command, put the whole file under `.fleet/local/` at the path the sync names.

## Next: set up the code

A new repository has Fleet's files and no code yet. The `repo:init` command gives it the smallest running thing: a web page that says *Hello, world* on a fixed port, one unit test, lint, a build and a CI workflow, in one pull request. It asks you one short round of questions first, such as the language, whether you want a separate frontend, where CI runs and where packages come from. Each question comes with a default it read from the repository. Personas, journeys and the product vision come later, through their own commands.

1. [you] **Start it.** In a Fleet terminal session on the repository, type `/<namespace>:repo:init` and a sentence about the product. Or let the fleet do it: on **Settings › Set up**, once every step is done, press **Set up the code**. It opens the task dialog, filled in. Choose the repository, add a sentence about the product, and press **File it**. A task you file yourself with the title **Set up the code** does the same.
2. [you] **Answer its questions.** In a session it asks you there. On the fleet the question waits for you on **Needs you**.
3. [fleet] **It builds and checks the code.** It runs lint, the tests and the build, starts the page, and checks that it answers.
4. [you] **Add the CI file if it asks you to.** Fleet's runs can never push to `.github/workflows/`. The run says so plainly, and shows you the commands that move the workflow file into place.
5. [fleet] **A second session checks the pull request.** The session that wrote the code never merges it. On the fleet, the verify gate merges it. In your own session, you review it and merge it.

After it merges, open a session on the repository and run the command the README names. The page appears on the session's **Ports** tab, and **Open ↗** shows it in your browser. If the repository already has code, `repo:init` stops and points you to describing that code instead.

## Next

If your repository already has code but nothing describes it yet, describe it before you plan new work. Then answer the placeholder questions.

Next: Build the knowledge for code you already have (guides/knowledge/describe-existing-code) · Answer the questions the commands ask about your repository (guides/knowledge/fill-slots) · The knowledge folder, file by file (knowledge-base/the-folder)

---
- **slice**: One deliverable with a one-sentence "Done when", which finishes by itself once its PRDs are done and its proof has shipped.
- **feature area**: The planning name for a feature: every slice, PRD, task and bug is filed under one.

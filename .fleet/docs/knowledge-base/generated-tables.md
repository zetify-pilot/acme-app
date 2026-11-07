# Generated tables

When many people and agents plan at once, two pull requests that each add a different row to the same table still collide. So a busy knowledge base keeps every row in its own file and renders the table from them. The rendered table is something you read, never something you edit.

## Why rows live in their own files

A register used to be one shared table. Every branch that added a slice or a requirement edited the same file, so two unrelated pull requests conflicted, and someone had to merge them by hand. With one file per row, a branch touches only its own row, and nothing collides.

A small repository may never need this. `fleet init` writes each register as one ordinary table, with a "next id" line at the top, and the commands add rows to it.

## Which tables are generated

| The table you read | Rendered from | Kept in git? |
|---|---|---|
| `knowledge/slices.md` | `knowledge/slices/rows/`, one file per slice, plus the shell `slices.md.tmpl` | no, rendered when needed |
| `knowledge/programs.md` | `knowledge/programs/rows/`, one file per program, plus `programs.md.tmpl` | no, rendered when needed |
| `knowledge/requirements/` registers | `knowledge/requirements/rows/`, one file per requirement, plus each register's `.md.tmpl` shell | no, rendered when needed |
| a feature map's capability table, when it keeps rows | `knowledge/features/rows/`, one file per capability, plus the map's `.md.tmpl` shell | no, rendered when needed |
| a feature map's `source_of_truth:` list | `knowledge/features/source_of_truth/`, one file per code path | written into the map's front matter |

The **shell** (the `.md.tmpl` file) is the part you do edit: the prose around the table, the headers, and a marker saying where the rows go. The rows are JSON files named by their id, for example `knowledge/slices/rows/SL-XXX.json`.

There are also indexes worked out from the rest, generated when someone asks for them and never committed: an index of every decision record, a list of which requirements are decided but not yet built, and a roadmap from the program and slice registers.

## What to do instead of editing a table

- **Use the command.** The slice, program, PRD and bootstrap commands write the row file, then render the table.
- **Or edit the row file** and render again. The generators ship with the commands under `knowledge/scripts/`; the register's own header names the one to run.
- **Never fix a conflict in a generated table by hand.** Take either side whole and render it again from the rows.

> **Careful:** A rendered table that disagrees with its rows fails the knowledge check, and so does a row typed straight into the table: nothing that reads the rows would ever see it.

## Ids are claimed, not counted

With one file per row, a shared "next id" counter would be the one line everybody edits. So a repository that keeps rows in files can turn on id claims (`id_claims = true` under `[fleet.planning]` in `.fleet/fleet.toml`): each new id is reserved on your repository's GitHub when it is allocated, and two branches cannot both take `SL-YYY`. The commands allocate ids for you. See the Ids reference.

## The other generated folder

`knowledge/scripts/` itself is written by `fleet commands sync` from the version of Fleet your repository uses. A change made there by hand is lost on the next sync. To change a script, change it in Fleet.

Next: The knowledge folder, file by file (knowledge-base/the-folder) · Fix a failing knowledge check (guides/knowledge/fix-a-failing-check)

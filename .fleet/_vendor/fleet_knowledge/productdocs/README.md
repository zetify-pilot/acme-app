# Fleet product docs: how a page is written

This folder holds Fleet's in-product documentation: how to use Fleet, and how a repository's
knowledge base is built. Every page is one markdown file here. The Fleet web app renders it as a
designed page (Docs, in the sidebar), and agents read the same page as plain markdown, rendered by
the last column of the block table below: through the `read_doc` MCP tool with the repository's live
facts filled in, and on a box as files at `.fleet/docs/` that `fleet commands sync` writes with no
live facts, in reading order (`index.md`). Either way an agent never sees a directive, front matter
or this file.

**Out of scope here:** installing, upgrading, network and security. Those stay in `docs/guides/`.

**This file is the contract.** The parser (`fleet_knowledge/docsmd.py`), the web renderer
(`templates/docs.js`), the agent renderer and the tests that run every page through both
(`fleet-knowledge/tests/test_docsmd.py`, `fleet-service/tests/api/test_docs.py` and
`test_js_render_docs.py`) all implement exactly what is written below. A block, an attribute or a front-matter key that is not in
this file is an error.

## Layout

```
productdocs/
  index.md                 the contents: section order and page order (see "The index")
  jobs/                    kind: job — one page per job the Docs home offers (see "Jobs")
  start/                   kind: start
  concepts/                kind: concept
  knowledge-base/          kind: concept
  guides/<group>/          kind: guide
  troubleshooting/         kind: troubleshooting
  reference/               kind: reference — GENERATED, never hand-edited
  README.md                this file (not a page)
```

A page's **id** is its path without `.md`, e.g. `guides/your-tools/personal-mcp`. Ids are what
`::cards`, `routes` lookups and `read_doc` use. File names are lowercase, hyphenated.

## Front matter

Every page starts with YAML front matter. All keys below; no others.

```yaml
---
title: "Use your own MCP servers in sessions"   # required, sentence case
kind: guide          # required: start | concept | guide | troubleshooting | reference | job
for: [developer]     # required: any of owner | developer | admin | everyone
summary: "One sentence shown on cards and in search."   # required, ≤ 160 chars
routes: [settings:my-mcp]   # optional: app route keys whose "?" opens this page
sources:                   # optional: repo paths this page describes (freshness contract)
  - packages/fleet-service/src/fleet_service/api/me.py
mode: any            # optional, default any: programs | areas | any
minutes: 6           # optional: reading time shown in the header
generated: true      # reference pages only; set by the generator
icon: knowledge      # job pages only, and required there: understand | daily | plan | knowledge | sessions | tools | team | quality | fix
group: learn         # job pages only, and required there: learn | use | run — where the Docs home draws it
---
```

- `routes` values are the app's addresses as they appear after `#` (`cockpit`, `terminals`). A route
  with a parameter is written as its kind only (`program`, not `program:PG-40`). Settings panes are
  `settings:<pane id>`: `set-up`, `secrets`, `shared-mcp`, `api-keys`, `connect`, `reports`,
  `my-secrets`, `my-mcp`, `repositories`, `models`, `agents`, `machines`, `labels`. A page of the System view is `system:<part>`
  (`system:machines`, `system:recurring`). Each route belongs to at most one page.
- `mode` limits a whole page to repositories that plan by programs or by areas. To vary a *part* of
  a page, use `:::mode` blocks instead.

## Plain markdown

Headings `##` and `###` (the page title comes from front matter; never write `#`), paragraphs,
`**bold**`, `*italic*`, `` `code` ``, links `[text](target)`, bullet and numbered lists, tables,
blockquotes, fenced code blocks. A link to another page uses its id: `[Slices](knowledge-base/slices)`.
A link to an app page uses `app:` and the route key: `[Areas](app:areas)`.

No raw HTML. Any `<tag>` outside a code span or fence is an error.

## Blocks

Directive syntax. Attributes are `key="value"`, `key=value` or a bare `flag`. Containers open with
`:::name{attrs}` on their own line and close with `:::` on its own line; containers do not nest,
except that leaf blocks may appear inside `:::steps` items and `:::mode`/`:::callout`/`:::compare`
bodies. Leaf blocks stand alone on their own line.

| Block | Attributes | In the product | What an agent reads |
|---|---|---|---|
| `:::lede` | — | The large intro in the page header. At most one, before the first `##`. | The paragraph, after the title. |
| `:::steps` | — | A timeline. Body is a list: `- [you\|fleet\|nobody] **Title.** text`; item continuation lines are indented two spaces and may hold leaf blocks. | `1. [you] **Title.** text` |
| `:::callout{kind}` | `kind`: `why` \| `tip` \| `careful` (required); `figure`: short text shown large | A tinted panel. | `> **Why:** figure text` |
| `:::mode{programs}` / `:::mode{areas}` | exactly one of `programs`, `areas` | Adjacent mode blocks become tabs, opened on the reader's repository mode. | Only the reader's mode, prefixed `(This repository plans by programs.)`; where the mode is unknown (the `.fleet/docs/` copy), every mode, each prefixed `(If this repository plans by programs.)` |
| `:::compare` | — | Body is a markdown table; drawn as side-by-side option cards (one per column after the first). | The table. |
| `::diagram{name}` | `name` (required): `work-line` \| `three-questions` \| `knowledge-folder` \| `knowledge-map` \| `fleet-map`; plus `slice="SL-…"` for `three-questions` | A drawn diagram filled with real names from the reader's knowledge. | A table with the same facts. |
| `::live{…}` | exactly one of `slice="SL-…"`, `area="<area-slug>"`, `prd="NNNN"`, `program="PG-…"`; `title` (required) and `quote`: what the example says | A card read live from the reader's knowledge, stamped with the commit it was read from. When the reader's repository does not hold the item, the card shows `title` and `quote`, marked as an example from Fleet's own planning — never an error. | The same facts as a blockquote, read at that moment, with the commit; or the written example. |
| `::screen{route}` | `route` (required): an app route key; `focus`: an item id on that page; `pins`: comma-separated anchor names | A framed crop of that app page with numbered pins. The numbered list directly under the block is the legend (one item per pin, same order). | `On the <Page> page (<url>):` then the numbered list. |
| `::action[Label]{route}` | `route` (required): an app route key | A button that opens that app page. | `[Label](<url>)` |
| `::cards{links}` | `links` (required): comma-separated page ids | Next-step cards using each page's title and summary. | `Next: <title> (<id>) · …` |
| `::command{name}` | `name` (required): a command id, e.g. `slice:create` | The slash command with a copy button and its one-line purpose, read from the repository's command tree, or from the tree Fleet ships when that cannot be read. | `` `slice:create` — purpose ``: the bare id, never a namespace before it |
| `::figure{name}` | `name` (required): a figure registered in `templates/docs-figures.js`; `alt` (required): the text an agent reads | A one-off designed visual. | The `alt` text. |
| `::embed{name}` | `name` (required): `work-line` | A live part of the app drawn inside the page, by the app itself (see "Embeds"). | A table with the same facts, without the live counts. |
| `:::ideas` | — | Job pages: 2 to 4 idea cards. Body is a list: `- **Name.** text`. | The list. |
| `::path{links}` | `links` (required): comma-separated page ids | Job pages: the numbered reading path, each page with its summary and reading time. | `1. **Title** (id): summary` |
| `::pages{links}` | `links` (required): comma-separated page ids | Job pages: the rest of the job's pages, as a two-column list. | `- **Title** (id): summary` |
| `:term[word]` | inline | A definition that opens on click/Enter, closes on Escape. | The word; the page ends with a `---` list of the definitions used. |
| `:kbd[keys]` | inline | Keyboard keys. | The keys. |

**Screens and their anchors.** `::screen` accepts only these routes, and `pins` only these anchor
names (registered in `templates/docs-screens.js`; adding one is a change to this table and that file):

| route | anchors |
|---|---|
| `areas` | `area`, `slices`, `prds`, `next` |
| `cockpit` | `tabs`, `views`, `filter`, `row` |
| `terminals` | `new`, `tile`, `layouts`, `composer`, `dock` |
| `program` | `slices`, `proof`, `levers` |
| `slice` | `done-when`, `prds`, `levers` |
| `issue` | `position`, `actions`, `blockers` |
| `queue` | `views`, `next`, `held` |
| `quality` | `line`, `waiting`, `ask` |
| `settings:my-mcp` | `editor`, `save` |
| `settings:secrets` | `add`, `list` |
| `settings:machines` | `machine`, `seats`, `drain`, `add` |
| `settings:repositories` | `repo`, `merge`, `verify`, `add` |

**Figures.** No figures are registered yet, so `::figure` is reserved: using it is an error until
`templates/docs-figures.js` registers one.

**Embeds.** `::embed` draws a part of the app that reads live and keeps itself current while the
page is open. The renderer asks the host for it (`ctx.embed(name)`, answering a DOM node or an HTML
string) and keeps no copy of its own; a host that cannot draw it shows an error in its place. The
names are closed, and adding one is a change to this table, `docsmd.EMBEDS` and its agent table,
`templates/docs.js` and the app's `docsCtx` at once:

| name | In the product | What an agent reads |
|---|---|---|
| `work-line` | The Work Line: every step in order with who attends it, the live counts under each step, a **Right now** / **Just the order** switch, one real issue followed through, and how many issues sit at each tracker position. | The bands and steps, who has to be there for each, and the commands that run them (`docsmd.WORK_LINE`). |

## Terms

`:term[word]` looks the word up, case-insensitively, first in `terms.md` in this folder (the
planning and product words: slice, feature area, PRD, program, promise, …), then in the app's
glossary of loop words (`fleet_service/api/glossary.py`: draining, lease, claim, lane, box, run, …). A term found in
neither is an error. `terms.md` is a list of `- **word**: one-sentence definition.` lines under a
`---`-free front matter with `title: Terms` and `kind: reference`; it is not listed in the index.

## The index

`index.md` has front matter `title` and `kind: start`, then these sections, each a list of page ids:

- `## Start here`: the one page a newcomer reads first.
- `## Jobs`: the job pages, in the order the Docs home shows them.
- `## Common tasks`: `- page/id: Label`, the tasks people come for most, one click each from the home.
- `## Reference`: the generated reference pages.

An id listed that has no file is an error.

## Jobs

The Docs home offers jobs, not a list of pages. A **job page** (`jobs/<slug>.md`, `kind: job`, an
`icon`) has a `:::lede`, `## The big picture` (a `::diagram` or a `:::ideas`), `## Read these in
order` with a `::path`, and the rest of its pages in `::pages` lists. **The job page owns its
pages**: every page other than the job pages, the reference pages and `terms` is led to by exactly
one job's `::path` or `::pages`. That job is the page's breadcrumb, and Previous and Next walk a job
from its page through its path and then its lists. A page no job reaches, or that two jobs claim,
is an error.

## Writing rules

- Write for the person using Fleet, in plain words. Name things as the app names them on screen.
- Explain a Fleet term the first time a page uses it, or mark it `:term[…]`.
- Never restate a number, limit or rule the code owns. Cite it by linking the reference page.
- A page describes what is built today. A feature that is not built is not documented.
- Each guide does one job. Its first paragraph says what you will have when you are done.

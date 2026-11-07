<!-- fleet:stub -->
# mockup-conventions

Where mockups are written in this repository, and which of the two tiers it can mount.

Fill this in as the web surface takes shape. It is optional: without it the `mockup` command
still runs every generic rule — it picks a reference, copies the real tokens, renders and
critiques the result, and puts it in front of a person — but it has to ask where the files go,
and it cannot promote an approved round to this product's own components.

- **directory** — where a mockup round is written here, repository-relative. Nothing here is
  ever left in a scratchpad: the committed file is the design contract, because the agents that
  plan, implement and verify run headless with the repository and nothing else.
- **tiers** — `explore` always; `lock` only if this repository can mount a page in its own
  substrate (a dev-only route, a fixture harness, a component library). Say which, and where.
- **states** — how a mockup addresses its states here, so every one is reachable: `?state=<name>`
  on one file, one linked page per state, or another convention. The rule is that a person can
  click through the flow without the author narrating it.
- **guidelines** — the design rules a mockup here must follow beyond the shared ones, in plain
  words, with a link to each document that owns them.

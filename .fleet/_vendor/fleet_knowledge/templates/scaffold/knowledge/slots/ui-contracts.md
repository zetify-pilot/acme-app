<!-- fleet:stub -->
# ui-contracts

Where this repository's design system lives: the page structure it follows, the tokens and
components it is built from, and how a page is checked.

Fill this in as the product's web surface takes shape. It is one of the slots the shipped
commands read to run here; `fleet slots --repo .` reports which command is blocked while it is
empty. The `mockup` command reads it before drawing anything, so name the real files:

- **tokens** — the file that holds colour, type scale and spacing. A mockup copies what is
  there at authoring time, never from memory.
- **pages** — how a page is structured and how one is reached.
- **catalog** — the shared components and controls a page is composed from.
- **checks** — how a page is verified (the browser harness, the lint rules, the screenshot run).

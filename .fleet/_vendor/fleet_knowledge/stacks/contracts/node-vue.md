---
type: spec
---

# Vue + TypeScript implementation contract — read before writing any frontend code

The coding and lint contract for the **Vue / TypeScript lane**. The `languages` slot points
here; an implementing agent reads it in full before touching a `.vue` or `.ts` file. Code that
breaks it fails `make lint`, `make typecheck` or review.

Written by `fleet init` from the `node-vue` stack profile. It is this repository's file: change
a rule here when the team changes its mind.

---

## The gate: strict types, clean lint, nothing baselined

- `make lint` runs ESLint (flat config, `eslint-plugin-vue` + `typescript-eslint`) and
  `prettier --check`; `make typecheck` runs `vue-tsc --build`. Both run in `make preflight`,
  before every push, and in CI.
- `tsconfig` is `strict: true` with `noUncheckedIndexedAccess`. Formatting is Prettier's, not a
  matter of taste: run `make lint-fix` rather than hand-formatting.
- **Never suppress to get green.** No `// @ts-ignore`, no `// @ts-expect-error` without a
  reason, no `eslint-disable` line added to silence a rule, no `as any` / `as unknown as T`.
  Fix the type. A justified exception carries a one-line reason a reviewer can check.
- Dependencies are exact in `package-lock.json` (committed, installed with `npm ci`). A new
  dependency is a decision: check its licence, size and maintenance first.

## Coding conventions

- **Components.** Single-file components with `<script setup lang="ts">` and the Composition
  API. One component per file, `PascalCase.vue`, multi-word names (`FaultList`, never `List`).
  Props typed with `defineProps<{…}>()` and defaults through `withDefaults`; emits typed with
  `defineEmits<{…}>()`. Never mutate a prop.
- **Logic lives in composables** (`useFaults.ts`, `use` prefix, returning refs and functions),
  not in components. A component composes; it does not fetch, parse and cache by itself.
- **State.** Local state in the component; shared state in a Pinia store (setup-store syntax),
  one store per domain concept. No global mutable module state.
- **Types.** `type`/`interface` for every shape crossing a boundary; no `any`. Parse data
  arriving from the network at the boundary (a schema validator or a generated client) instead
  of casting it. Prefer union types and `as const` over enums.
- **Names.** `camelCase` for variables and functions, `PascalCase` for types and components,
  `SCREAMING_SNAKE_CASE` only for true constants. Files: `PascalCase.vue`, `camelCase.ts`.
- **Templates.** No complex expressions in templates — move them to a `computed`. `v-for`
  always has a stable `:key` (an id, never the index). Never `v-if` and `v-for` on one element.
- **Security.** No `v-html` with anything but sanitised, trusted content. No secret in frontend
  code or in a `VITE_*` variable: everything the bundle holds is public.
- **Accessibility.** Semantic elements first (`button`, `label`, headings in order); every
  interactive element is reachable and operable by keyboard and has an accessible name.
- **User-visible text** goes through the project's i18n mechanism when it has one; never
  concatenate translated fragments.
- Keep a component small enough to read on one screen; split it before it grows a second job.

## Error handling

- **Every async call handles failure.** No floating promise (`@typescript-eslint/no-floating-promises`);
  every `await` that can fail is inside a `try`/`catch` at the layer that can do something
  about it, or the error propagates to one that can.
- **Show the user what happened** in words they can act on — an empty state, an inline error,
  a retry — never a blank screen or a console-only failure. Loading, empty and error are three
  states every data view renders.
- **Never swallow.** An empty `catch` is a defect. Log with context through the project's
  logger, then surface or rethrow.
- **Type errors as values where the caller must branch** (a result union), not as thrown
  strings. Throw only `Error` (or a subclass), never a string or plain object.
- One global handler (`app.config.errorHandler`) reports what no one else caught; it is the
  last line, not the strategy.

## Tests — levels and naming

| Level | Tool | Runs in | What it covers |
|---|---|---|---|
| unit | Vitest | `make test-unit` | composables, stores, pure functions — no network, no real timers |
| component | Vitest + Vue Test Utils | `make test-unit` | one component, mounted, through its props, events and rendered output |
| end-to-end | Playwright | `make test-e2e` | the built app in a real browser, against the real or a recorded backend |

- **Files.** Unit and component tests sit beside the code as `<name>.spec.ts`
  (`FaultList.spec.ts`); end-to-end tests live in `e2e/<journey>.spec.ts`.
- **Names.** `describe('<Unit>')` with `it('<does what> when <condition>')`, e.g.
  `it('shows the retry button when the fault list fails to load')`. The name reads as a sentence.
- **Query like a user.** Find elements by role, label or text; `data-testid` only when nothing
  accessible identifies the element. Never assert on CSS classes or component internals.
- **Determinism.** Mock the network at the boundary (MSW or the generated client's seam), use
  fake timers (`vi.useFakeTimers()`) instead of waiting, and await the condition
  (`await flushPromises()`, Playwright's auto-waiting `expect`), never a fixed sleep. A flaky
  test is a bug, fixed at its cause.
- One behaviour per test; arrange / act / assert; no logic in the test body.
- **A bug fix starts with a failing test** that reproduces it, then the fix.

## Generated code stays separate

- Generated sources (API clients from OpenAPI or protobuf — e.g. `@bufbuild/protobuf` /
  Connect stubs) are produced by `make generate` into their own folder (`src/gen/` or a
  package of their own) and are **never edited by hand** — change the source and regenerate.
- Generated folders are excluded from ESLint and Prettier (`ignores` in `eslint.config`,
  `.prettierignore`) and imported, never copied from.
- Hand-written code never lives in a generated file. Wrap a generated client in a small
  hand-written module when it needs adapting, so a regeneration cannot erase the adaptation.

## Verification you run yourself (FAST only — never the slow gates)

- `npx vue-tsc --build` (or the editor's type check) over what you changed.
- One targeted test: `make test-one T=<test name>`.
- `npx eslint <files you changed>`.

Do **not** run `make test`, `make test-e2e`, `make build` or `make generate` from an
implementation task: the coordinator runs those once per wave. A UI change is also checked in a
real browser before it is called done.

# Conventional targets — what the fleet's commands mean when they say `make <target>`.
#
# Written by `fleet init`. Each target below is named by at least one shipped command; a
# repository replaces the recipe with its own and keeps the name. A target this repository
# genuinely has no use for (no database, no UI) stays as it is: the refusal is loud, which
# is what a command that needs it should meet — never a silent no-op.
#
# The list is `fleet_knowledge.checks.slots._portability.MAKE_TARGETS`; `fleet init` on an
# existing Makefile reports which of them it lacks.

.PHONY: agent-loop agent-loop-install build coverage dev dev-headless dev-services dev-stop generate generate-page-specs lint lint-ci lint-fix pre-commit-dry preflight reseed seed test test-db test-e2e test-one test-unit typecheck validate-knowledge

# run a named agent loop: `make agent-loop LOOP=<name>`
agent-loop:
	@echo "make agent-loop: not configured for this repository — see the Makefile header" >&2; exit 2

# install a loop's prompt: `make agent-loop-install LOOP=<name> PROMPT=<file>`
agent-loop-install:
	@echo "make agent-loop-install: not configured for this repository — see the Makefile header" >&2; exit 2

# compile or bundle every artifact
build:
	@echo "make build: not configured for this repository — see the Makefile header" >&2; exit 2

# the unit lane with the coverage gate
coverage:
	@echo "make coverage: not configured for this repository — see the Makefile header" >&2; exit 2

# the full stack with hot reload, in the foreground
dev:
	@echo "make dev: not configured for this repository — see the Makefile header" >&2; exit 2

# the full stack, backgrounded, for a browser pass
dev-headless:
	@echo "make dev-headless: not configured for this repository — see the Makefile header" >&2; exit 2

# only the backing services (a database, a queue)
dev-services:
	@echo "make dev-services: not configured for this repository — see the Makefile header" >&2; exit 2

# stop whatever `dev` started
dev-stop:
	@echo "make dev-stop: not configured for this repository — see the Makefile header" >&2; exit 2

# regenerate everything derived from a source of truth
generate:
	@echo "make generate: not configured for this repository — see the Makefile header" >&2; exit 2

# regenerate the surface specs' derived sections
generate-page-specs:
	@echo "make generate-page-specs: not configured for this repository — see the Makefile header" >&2; exit 2

# the static checks a commit must pass
lint:
	python3 -m compileall -q app tests

# the static checks CI runs, where they exceed `lint`
lint-ci:
	@echo "make lint-ci: not configured for this repository — see the Makefile header" >&2; exit 2

# the mechanical auto-fixes, run before hand-fixing lints
lint-fix:
	@echo "make lint-fix: not configured for this repository — see the Makefile header" >&2; exit 2

# the commit hooks over the working tree, writing nothing
pre-commit-dry:
	@echo "make pre-commit-dry: not configured for this repository — see the Makefile header" >&2; exit 2

# the lane's fast mechanical guards, run before the first push — the same checks CI runs
preflight:
	$(MAKE) lint test

# reset and seed the running stack
reseed:
	@echo "make reseed: not configured for this repository — see the Makefile header" >&2; exit 2

# seed the running stack
seed:
	@echo "make seed: not configured for this repository — see the Makefile header" >&2; exit 2

# every suite, the CI equivalent
test:
	python3 -m pytest -q

# the lane that needs a database up
test-db:
	@echo "make test-db: not configured for this repository — see the Makefile header" >&2; exit 2

# the full-stack lane
test-e2e:
	@echo "make test-e2e: not configured for this repository — see the Makefile header" >&2; exit 2

# one test by name: `make test-one T=<name>`
test-one:
	@echo "make test-one: not configured for this repository — see the Makefile header" >&2; exit 2

# the fast unit lane, no services
test-unit:
	python3 -m pytest -q

# the type checker over the whole tree
typecheck:
	@echo "make typecheck: not configured for this repository — see the Makefile header" >&2; exit 2

# the corpus validators (`knowledge/scripts/validate_*.py`, `fleet check`)
validate-knowledge:
	@echo "make validate-knowledge: not configured for this repository — see the Makefile header" >&2; exit 2


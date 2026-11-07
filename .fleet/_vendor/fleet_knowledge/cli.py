"""`fleet` — the command line over a knowledge base.

Three subcommands, written for someone who has never seen this tool:

    fleet config     what corpus am I looking at, and why that one?
    fleet check      run the validators
    fleet board      programs, their slices, and what needs a decision

**There was a fourth — `fleet browser`, the whole graph as a second clickable page — and it
is gone rather than migrated.** `ui.py` states the rule both generators lived by: they inline
or link THE SAME `fleet.css` and THE SAME `board.js`, and the moment keeping both honest
required forking the renderer, the standalone one stopped being worth its price. The knowledge
browser WAS that fork — its own template, its own palette, its own payload builder. The
knowledge it read is now `fleet_knowledge.knowledge`, an entity model the board serves as a tab
of its own; only the second renderer was thrown away.

`config` comes first on purpose. Every other command's output is only as trustworthy as the
root it read, so the tool can always be asked which root it picked and which layer picked it —
flag, environment, `.env`, TOML or discovery.

Conventions this file keeps, because a CLI teaches by behaving consistently:

  * `-k/--knowledge-dir` works on every subcommand and always wins.
  * A failure prints what went wrong AND what to do about it. Exit 2 means "you and I
    disagree about the invocation or the configuration"; exit 1 means "the corpus has a
    problem". Nothing exits 1 for a usage mistake.
  * `--json` is available wherever a machine might read the output, and is exactly the data,
    with no human framing mixed in.
  * Nothing here prints a date, a duration, a rate or an estimate. Counts and dependency
    order only.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from dataclasses import replace
from pathlib import Path
from typing import Any

from . import board as board_mod
from . import commandsync, paths, runner, slotanswers
from . import slots as slots_mod
from .checks import slots as slots_check
from .config import ConfigError, GitContext, KnowledgeBase, Origin, resolve

PROG = "fleet"


def _add_root_flag(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "-k",
        "--knowledge-dir",
        metavar="PATH",
        default=None,
        help="the knowledge/ directory to read (beats every other source; see `fleet config`)",
    )


def _resolve_or_exit(args: argparse.Namespace) -> KnowledgeBase:
    """The corpus this invocation is about, resolved from `--repo` when one was given.

    `--repo` moves the ANCHOR of the resolution, not the corpus: everything downstream of
    it — the `.env`, the `fleet.toml`, upward discovery — is then searched from that
    checkout instead of from the process's cwd. `-k` still beats it, because `-k` names the
    corpus outright while `--repo` only says where to look for whatever names it.

    Read with `getattr` so the flag stays opt-in per subcommand: a parser that does not
    offer it resolves from the cwd exactly as it always did.
    """
    repo = getattr(args, "repo", None)
    try:
        return resolve(args.knowledge_dir, cwd=Path(repo).resolve() if repo is not None else None)
    except ConfigError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


# ─────────────────────────── config ───────────────────────────


def cmd_config(args: argparse.Namespace) -> int:
    kb = _resolve_or_exit(args)
    cfg = kb.config
    if args.json:
        payload: dict[str, Any] = {
            "root": str(kb.root),
            "knowledge": str(kb.knowledge),
            "knowledge_origin": {"kind": kb.origin.kind, "detail": kb.origin.detail},
            "options": {
                name: {
                    "value": list(v) if isinstance(v := getattr(cfg, name), tuple) else v,
                    "origin": {"kind": cfg.origin(name).kind, "detail": cfg.origin(name).detail},
                }
                for name in cfg.field_names()
            },
            # The per-family tables, verbatim. Not folded into `options`: a section is a
            # table with its own vocabulary and one origin, not a value with a type this
            # command knows — and flattening it would invent key names nobody wrote.
            "sections": {name: dict(cfg.section(name)) for name in cfg.section_names()},
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"knowledge  {kb.knowledge}")
    print(f"           ^ chosen by {kb.origin}")
    print(f"root       {kb.root}")
    print()
    width = max(len(n) for n in cfg.field_names())
    print("option".ljust(width), " value".ljust(42), " came from")
    print("-" * (width + 46 + 24))
    for name in cfg.field_names():
        value = getattr(cfg, name)
        shown = ", ".join(value) if isinstance(value, tuple) else str(value)
        shown = shown if shown != "" else "(unset — this corpus does not have it)"
        marker = " " if cfg.origin(name).kind == "default" else "*"
        print(f"{name.ljust(width)} {marker}{shown[:41].ljust(42)} {cfg.origin(name)}")
    print()
    print("* = set by this project; everything else is the built-in default.")
    print(
        "Set options in `.fleet/fleet.toml`, or a `[tool.fleet]` table in a "
        "pyproject.toml, found by walking up from the current directory."
    )
    # Only when a project actually set one. A permanent block of three empty headings would
    # be noise on every run for the majority of corpora, which set none of them.
    for name in cfg.section_names():
        table = cfg.section(name)
        if not table:
            continue
        print()
        print(f"[{name}]   {cfg.origin(name)}")
        for key in sorted(table):
            print(f"  {key} = {table[key]!r}")
    return 0


# ─────────────────────────── check ───────────────────────────


def _with_git_context(kb: KnowledgeBase, args: argparse.Namespace) -> KnowledgeBase:
    """`kb`, told which revisions the history-dependent checks compare against.

    Nothing given, nothing changed: every one of those checks falls back to what it did
    before, which is what a working checkout wants.
    """
    ctx = GitContext(base=args.base or "", head=args.head or "", tip=args.tip or "")
    return replace(kb, git=ctx) if ctx else kb


def cmd_check(args: argparse.Namespace) -> int:
    checks = runner.discover()
    if args.list:
        if not checks:
            print("No checks are installed. A check is a module under fleet_knowledge/checks/")
            print("exposing `CHECKS: list[Check]` — see that package's docstring.")
            return 0
        if args.json:
            print(
                json.dumps(
                    [{"name": c.name, "title": c.title, "description": c.description} for c in checks],
                    indent=2,
                )
            )
            return 0
        width = max(len(c.name) for c in checks)
        for c in checks:
            print(f"{c.name.ljust(width)}  {c.title}")
        return 0

    kb = _with_git_context(_resolve_or_exit(args), args)
    try:
        results = runner.run_checks(kb, checks, only=args.only, min_level=args.level, strict=args.strict)
    except (runner.UnknownCheckError, runner.DisabledCheckError) as exc:
        print(f"{PROG} check: {exc}", file=sys.stderr)
        print("Run `fleet check --list` to see every check.", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([r.as_dict(kb.root) for r in results], indent=2))
    else:
        if not results:
            print("No checks are installed — nothing was validated.")
            print("Add a module under fleet_knowledge/checks/ exposing `CHECKS: list[Check]`.")
            return 0
        print(f"Checking {kb.knowledge}")
        print(runner.format_results(results, relative_to=kb.root, verbose=args.verbose))
    return runner.exit_code(results, strict=args.strict)


def cmd_commands(args: argparse.Namespace) -> int:
    """Put the shared command tier where a repository's agent will find it, or check it.

    The reporting/​writing twin of `slots`: that command answers "what does this repo supply
    to the commands", this one supplies the commands themselves.

    `--check` exits 1 on drift so CI can gate it, and writes nothing. A materialized tree
    nobody compares is a hand-copy again by the next commit, which is the failure the tier
    was packaged to end.
    """
    repo = (args.repo or Path.cwd()).resolve()
    take = frozenset(args.replace or ())
    if args.check:
        report = commandsync.verify(repo, replace=take)
    else:
        report = commandsync.sync(repo, prune=args.prune, replace=take)
    if args.json:
        print(json.dumps({"inSync": report.in_sync, **report.drift_json()}, indent=2))
    else:
        print("\n".join(report.lines(diffs=args.check or args.diff)))
    if args.check and not report.in_sync:
        print(
            f"\n{PROG}: the command tier in {repo} does not match this fleet-knowledge. "
            f"Run `{PROG} commands sync --repo {repo}` to update it.",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Write the planning record and the command tier into a repository, offline.

    Two questions only the owner can answer — the product's name and the first thing the team wants
    done — plus the namespace the commands are typed under (default `commandsync.CUSTOMER_NAMESPACE`).
    On a TTY a missing answer is asked for; with no TTY (a script, a CI job) both answers must be
    supplied up front, because a prompt that reads EOF is a scaffold that writes a register row named "".
    The namespace is never asked for: it has a default, so a run whose flags supply the two answers
    never prompts for it.

    **The first thing the team wants done is a slice or a program by the planning mode** (FLT-1281,
    `scaffold.planning_mode`): a fresh repository plans by area, so it is the first slice (`--slice`,
    under the area `product`) and no program is asked for; a repository whose kept `.fleet/fleet.toml`
    plans by program is asked for its first program (`--program`), exactly as before. `--program` still
    names the first slice in `areas` mode, so a script written before the mode keeps working.
    """
    from fleet_knowledge import planningmode, scaffold  # noqa: PLC0415 — one subcommand's dependency

    repo = (args.repo or Path.cwd()).resolve()
    if not repo.is_dir():
        print(f"{PROG} init: {repo} is not a directory", file=sys.stderr)
        return 2

    mode = scaffold.planning_mode_for(repo)
    answers = _ask_answers(args, areas=mode == planningmode.AREAS)
    if answers is None:
        return 2
    product, program, namespace = answers
    problems = scaffold.validate_answers(product, program, namespace, mode=mode)
    if problems:
        for field, problem in problems:
            print(f"{PROG} init: --{field}: {problem}", file=sys.stderr)
        return 2

    chosen = _stacks_of(args, repo)
    if chosen is None:
        return 2
    facts = _facts_of(args)
    if facts is None:
        return 2

    report = scaffold.init(
        repo,
        {"productName": product, "firstSlice" if mode == planningmode.AREAS else "firstProgram": program},
        namespace,
        args.set if args.set is not None else "core",
        stacks=chosen,
        ci_runner=args.ci_runner or "",
        facts=facts,
    )
    print("\n".join(report.lines()))
    return 0


def _facts_of(args: argparse.Namespace) -> slotanswers.RepoFacts | None:
    """The install facts the flags name (`slotanswers.RepoFacts`), or `None` after a refusal.

    A tracker whose keys carry a prefix (Linear, Jira) is refused without a readable `--key-prefix`: the
    shipped scripts compose issue ids from it, so a guessed one is worse than the placeholder.
    """
    tracker = (getattr(args, "tracker", None) or "").strip()
    prefix = (getattr(args, "key_prefix", None) or "").strip().rstrip("-")
    if prefix and not slotanswers.valid_key_prefix(prefix):
        print(
            f"{PROG} init: --key-prefix: {prefix!r} is not a key prefix (a letter, then letters or digits)",
            file=sys.stderr,
        )
        return None
    if tracker in ("linear", "jira") and not prefix:
        print(f"{PROG} init: --tracker {tracker} needs --key-prefix, the prefix its issue keys carry", file=sys.stderr)
        return None
    lane = getattr(args, "lane_label", None)
    lane_label = None if lane is None else ("" if lane.strip().lower() == "none" else lane.strip())
    if lane_label and not lane_label.startswith("repo:"):
        print(f"{PROG} init: --lane-label: {lane_label!r} is not a `repo:<name>` label (or `none`)", file=sys.stderr)
        return None
    check = getattr(args, "verify_check", None)
    merge = getattr(args, "merge", None) or ""
    return slotanswers.RepoFacts(
        tracker=tracker,
        tracker_home=(getattr(args, "tracker_home", None) or "").strip(),
        key_prefix=prefix,
        lane_label=lane_label,
        merge=slotanswers.AGENTS if merge == "agents" else slotanswers.PERSON if merge == "person" else "",
        verify_check=None if check is None else ("" if check.strip().lower() == "none" else check.strip()),
    )


def _stacks_of(args: argparse.Namespace, repo: Path) -> list[Any] | None:
    """The stacks `--stack` names plus those `--detect` finds, or `None` after a refusal."""
    from fleet_knowledge import stacks  # noqa: PLC0415 — one subcommand's dependency

    named = [s for given in (args.stack or []) for s in given.split(",") if s.strip()]
    try:
        chosen = {c.id: c for c in stacks.resolve_repo(repo, named)} if named else {}
    except stacks.UnknownStackError as exc:
        print(f"{PROG} init: --stack: {exc}", file=sys.stderr)
        return None
    if args.detect:
        found = stacks.detect_repo(repo)
        print(f"{PROG} init: detected {', '.join(c.id for c in found) or 'no stack'}")
        for choice in found:
            chosen.setdefault(choice.id, choice)
    return [chosen[sid] for sid in stacks.profiles() if sid in chosen]


def _ask_answers(args: argparse.Namespace, *, areas: bool = False) -> tuple[str, str, str] | None:
    """`(product, first, namespace)` from flags and prompts, or `None` after a refusal.

    A missing value on a TTY is asked for; off a TTY it is refused and named. `namespace` is never
    asked for: it has a documented default, `commandsync.CUSTOMER_NAMESPACE` (the tree's own
    namespace, owner decision 2026-10-15), so a run whose flags supply the other answers never
    prompts and never stalls. `--namespace` still names another prefix. A declared namespace is
    always a customer render, so the default carries the prefix and none of the home project's text.

    `first` is the first thing the team wants done. With `areas` it is the first SLICE: asked for as
    one, refused as `--slice`, and given by `--slice` or — its old name — `--program`. Without, it is
    the first program, exactly as before (`--program`; `--slice` is read as its new name).
    """
    interactive = sys.stdin.isatty()
    values: dict[str, str] = {}
    first = "slice" if areas else "program"
    prompts = {
        "product": "The product's name (e.g. Payments): ",
        "program": "The first thing the team wants done (a sentence): ",
        "slice": "The first thing the team wants done (a sentence; it becomes the first slice, in the product area): ",
    }
    for field in ("product", first):
        given = getattr(args, field)
        if field == first and given is None:
            # The other name for the same answer: `--program` from a script written before the mode, or `--slice`.
            given = getattr(args, "program" if field == "slice" else "slice")
        if given:
            values[field] = given
            continue
        if not interactive:
            print(
                f"{PROG} init: --{field} is required — no TTY to ask on, so supply every answer on the command line",
                file=sys.stderr,
            )
            return None
        try:
            values[field] = input(prompts[field])
        except EOFError:
            print(f"{PROG} init: no answer for --{field}", file=sys.stderr)
            return None
    values["namespace"] = getattr(args, "namespace", None) or commandsync.CUSTOMER_NAMESPACE
    return values["product"], values[first], values["namespace"]


def _config_of(root: Path) -> KnowledgeBase | None:
    """The surveyed repo's OWN resolved config, or None when it has none.

    Resolved from `root` rather than the process's cwd, because `--repo` means the question
    is about THAT checkout and its config is the only one entitled to answer it.
    """
    try:
        return resolve(None, cwd=root)
    except ConfigError:
        return None


def _knowledge_of(root: Path, kb: KnowledgeBase | None) -> Path:
    """Where this repo keeps the corpus the slot registry is resolved against.

    `knowledge_dir` is the OTHER half of the same defect `_commands_dir_of` fixes, and it
    bites harder: a repository whose answers are its own top-level documents sets
    `knowledge_dir = "."`, and a reader that ignores it looks for the registry under a
    `knowledge/` directory that does not exist — then reports `registry: NONE` and every
    command blocked, which reads as "this repo answers nothing" rather than "this reader
    looked in the wrong place". The two failures are indistinguishable in the output, and
    the wrong one is the one a person acts on.
    """
    return (kb.knowledge if kb is not None else root / paths.DEFAULT_DIR_NAME).resolve()


def _commands_dir_of(kb: KnowledgeBase | None, root: Path) -> str:
    """The surveyed repo's OWN `[fleet.slots] commands_dir`, or the default.

    ══ WHY THE CLI HAS TO READ IT AT ALL ═══════════════════════════════════════
    The `slots` CHECK has honoured this option since it existed; this command did not, and
    hardcoded the default. Two readers of one repo, disagreeing about which directory holds
    its commands — and the disagreement is invisible, because both then report confidently
    about whatever they found. The option decides the NAMESPACE a command is addressed by
    (`namespace_of` takes the directory's basename), so a repo whose commands live one level
    down had every cross-reference between them silently unresolved on one path and resolved
    on the other.

    A repo with no corpus, or a config that cannot be read, is not an error here: this
    command exists to answer questions about repos that have declared little or nothing, so
    it falls back rather than exiting.
    """
    if kb is None:
        return slots_mod.default_commands_dir(root)
    return str(slots_check.option(kb, "commands_dir", slots_mod.default_commands_dir(kb.root)))


def cmd_slots(args: argparse.Namespace) -> int:
    """What this repo supplies to the command tree, and which commands can therefore run.

    The reporting twin of the `slots` check. `fleet check --only slots` is the GATE — it
    exits non-zero on an unfilled mandatory slot. This is the ANSWER TO A QUESTION, and it
    exits 0 whatever it finds, because "what is missing" is the thing you run it to learn.

    `--reference` is what makes it useful against a repo that has declared nothing: such a
    repo has no slot list of its own, so the honest comparison is against one that does.

    `--emit` is the mechanical half of the two-file split, and it exists because the
    alternative is the copy step the split removes. `--emit answers` renders a repo's
    legacy registry as the thin `fill`-only block that replaces it, so migrating is one
    command and a paste rather than 35 hand-edited rows. `--emit questions` refreshes the
    shipped questionnaire FROM a repo's registry, which is how the packaged file is
    updated when a command gains a `requires:` — a MERGE over the shipped rows, never a
    replacement of them, because the source repo is entitled to decline a question and a
    decline must not read as a deletion. `slots.Refresh` carries that argument in full.
    """
    root = (args.repo or Path.cwd()).resolve()
    kb = _config_of(root)
    knowledge = args.knowledge_dir.resolve() if args.knowledge_dir else _knowledge_of(root, kb)
    commands_rel = args.commands_dir or _commands_dir_of(kb, root)

    if args.emit:
        registry = slots_mod.read_registry(root, knowledge, args.registry)
        if not registry.present:
            # ══ THE QUESTIONS DO NOT COME FROM THE ANSWERS ═════════════════════
            # Both modes used to read the repo's registry and exit 2 without it, which put
            # the questionnaire behind the very file it is asked in order to write:
            # `fleet slots --repo <new repo> --emit questions` printed "no slot registry at
            # slots/README.md" and nothing else, on exactly the repo that needed to read it.
            # The questionnaire SHIPS in this package, so it is readable here and now:
            #   * `--emit questions` renders it verbatim — the vocabulary, unconditionally.
            #   * `--emit answers` renders every repo-tier id with an empty list, because
            #     the questionnaire carries no repo fills: a blank answer sheet, which is
            #     the file an onboarder is being asked to produce.
            # A registry that EXISTS but is broken still exits 2 below — that is a repo
            # saying something unreadable, not a repo that has said nothing yet.
            registry = slots_mod.read_questions()
        if not registry.slots:
            for err in registry.errors:
                print(f"{PROG} slots: {err}", file=sys.stderr)
            return 2
        if args.emit == "questions":
            refresh = slots_mod.refresh_questions(registry)
            # ══ THE ACCOUNT GOES TO STDERR BECAUSE STDOUT IS THE FILE ══════════
            # The documented invocation is a redirect into `slot-questions.json`, so a line
            # of report on stdout corrupts the very file this writes. It has to be printed
            # somewhere, though: the deletion bug this merge fixes survived because the
            # output went straight into the packaged file and the 13 dropped rows were
            # never rendered anywhere a person reads.
            source = registry.path or "the shipped questionnaire"
            print(f"{PROG} slots: questionnaire refreshed from {source}", file=sys.stderr)
            for line in refresh.report():
                print(f"  {line}", file=sys.stderr)
            print(refresh.block(), end="")
        else:
            print(slots_mod.answers_block(registry), end="")
        return 0

    ref_root: Path | None = None
    ref_knowledge: Path | None = None
    if args.reference:
        ref_root = args.reference.resolve()
        ref_knowledge = ref_root / paths.DEFAULT_DIR_NAME

    if args.json:
        reference = None
        if ref_root is not None and ref_knowledge is not None:
            reference = slots_mod.read_registry(ref_root, ref_knowledge, args.registry)
        s = slots_mod.survey(
            root, knowledge, registry_rel=args.registry, commands_dir=commands_rel, reference=reference
        )
        print(
            json.dumps(
                {
                    "repo": str(root),
                    "commands_dir": commands_rel,
                    "registry": str(s.registry.path) if s.registry.present else None,
                    "registry_errors": list(s.registry.errors),
                    "slots": [
                        {
                            "id": f.slot.id,
                            "tier": f.slot.tier,
                            "requirement": f.slot.requirement,
                            "filled": f.filled,
                            # `filled` / `stub` / `unfilled`: a placeholder is there and unfilled.
                            "state": f.state,
                            "stub": f.stub,
                            "matched": [str(m.relative_to(root)) for m in f.matched],
                            "missing": list(f.missing),
                            "degrade": f.slot.degrade,
                        }
                        for f in s.fills
                    ],
                    "blocked_commands": [{"command": n.command, "blocked_by": b} for n, b in s.blocked_commands()],
                },
                indent=2,
            )
        )
        return 0

    print(
        "\n".join(
            slots_check.summary_lines(
                root,
                knowledge,
                reference_root=ref_root,
                reference_knowledge=ref_knowledge,
                registry_rel=args.registry,
                commands_dir=commands_rel,
            )
        )
    )
    return 0


# ─────────────────────────── generators ───────────────────────────


def _write(out: Path, html: str, *, quiet: bool, open_it: bool) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    if not quiet:
        print(out)
    if open_it:
        webbrowser.open(out.resolve().as_uri())
    return 0


def cmd_digest(args: argparse.Namespace) -> int:
    """The binding digest of one planning row's completion cell — `fleet digest`, as the commands cite it.

    A command used to reach this through a `python3 -c "import sys; sys.path.insert(0,'scripts');
    import _fleet_knowledge_shim; …"` heredoc, which is one repository's shell history: five of
    the six lane repos have no `scripts/` and no shim. The register now names the capability
    and this subcommand is what a repo binds it to.
    """
    from fleet_knowledge.checks.planning import _digest as d

    kb = _resolve_or_exit(args)
    register = kb.knowledge / args.register
    try:
        cell = d.extract_done_cell(register, args.row)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"planning-digest: {exc}", file=sys.stderr)
        return 2
    print(d.digest_of(cell))
    return 0


def cmd_planning_migrate(args: argparse.Namespace) -> int:
    """`fleet planning migrate` (FLT-1283): a dry run by default; `--write` edits this tree; `--pr` opens one PR."""
    from . import planningmigrate as pm  # noqa: PLC0415

    if args.close_programs:
        args.drop_programs = True
    if args.flip and not args.drop_programs:
        print("fleet planning migrate: --flip needs --drop-programs (programs close to new slices)", file=sys.stderr)
        return 2
    if args.write and args.pr:
        print("fleet planning migrate: --write and --pr are two ways to write; pick one", file=sys.stderr)
        return 2
    kb = _resolve_or_exit(args)
    repo = Path(kb.root)
    if args.pr:
        import tempfile  # noqa: PLC0415

        try:
            with tempfile.TemporaryDirectory(prefix="fleet-migrate-") as tmp:
                the_plan, url = pm.open_pr(
                    repo,
                    base=args.base,
                    branch=args.branch,
                    drop_programs=args.drop_programs,
                    flip=args.flip,
                    workdir=Path(tmp),
                    close_programs=args.close_programs,
                    require_area=args.require_area,
                )
        except RuntimeError as exc:
            print(f"fleet planning migrate: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({**the_plan.as_json(), "pr": url}, indent=2) if args.json else (url or "nothing to migrate"))
        return the_plan.exit_code()
    the_plan = pm.plan(
        kb.knowledge,
        kb.config,
        drop_programs=args.drop_programs,
        flip=args.flip,
        close_programs=args.close_programs,
        require_area=args.require_area,
    )
    if args.write:
        new_ids = pm.slice_allocator(kb) if any(p.creates for p in the_plan.proofs) else None
        try:
            written = pm.apply(kb.knowledge, repo, the_plan, new_ids=new_ids, **pm.registers_of(kb.config))
        except Exception as exc:  # noqa: BLE001 — an allocator that cannot reach its claims is a repo error
            print(f"fleet planning migrate: {exc}", file=sys.stderr)
            return 2
        for path in written:
            print(f"wrote {path}", file=sys.stderr)
    print(
        json.dumps(the_plan.as_json(), indent=2) if args.json else pm.table(the_plan), end="" if not args.json else "\n"
    )
    return the_plan.exit_code()


def cmd_board(args: argparse.Namespace) -> int:
    kb = _resolve_or_exit(args)
    out = args.out or kb.knowledge / board_mod.DEFAULT_OUT_NAME
    html = board_mod.render(
        kb.knowledge,
        config=kb.config,
        template=args.template,
        title=args.title,
        guidance=board_mod.load_guidance(args.guidance),
        intent_title=args.intent_title,
    )
    return _write(out, html, quiet=args.quiet, open_it=args.open)


# ─────────────────────────── argv ───────────────────────────


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Read, validate and render a file-based knowledge base — programs, slices, PRDs, "
            "feature maps, requirement registers and journeys.\n\n"
            "Start with `fleet config` to see which corpus is being read and why."
        ),
        epilog=(
            "The knowledge directory is resolved in this order, first hit wins:\n"
            "  1. --knowledge-dir / -k\n"
            "  2. $KNOWLEDGE_DIR\n"
            "  3. $FLEET_ROOT (knowledge/ beneath it)\n"
            "  4. a .env found by walking up (process env wins over .env)\n"
            "  5. .fleet/fleet.toml, or [tool.fleet] in a pyproject.toml\n"
            "  6. the nearest ancestor holding knowledge/programs.md\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="command", metavar="COMMAND")

    p_config = sub.add_parser(
        "config",
        help="print the resolved knowledge base and where every value came from",
        description=(
            "Print the corpus this tool would read, the layer that chose it, and every option "
            "with its source. Run this first when a command reports something surprising: an "
            "unexpected answer is usually an unexpected root."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_root_flag(p_config)
    p_config.add_argument("--json", action="store_true", help="machine-readable output")
    p_config.set_defaults(func=cmd_config)

    p_check = sub.add_parser(
        "check",
        help="run the validators over the knowledge base",
        description=(
            "Run every installed check. A check that does not apply to this corpus is SKIPPED "
            "with a reason, never failed — a project without journeys is not a broken project.\n"
            "\n"
            "Exit codes: 0 nothing gates, 1 the corpus has an error-level finding, 2 the "
            "invocation or the configuration is wrong."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_root_flag(p_check)
    # ══ WHY `check` NEEDS ITS OWN `--repo` ═════════════════════════════════════
    # `fleet slots` has had one since it existed, so gating a checkout and reporting on it
    # were reached by two different invocations — and for a repo whose corpus IS its root,
    # the only spelling `check` offered was `-k <repo-root>`, which names the corpus and
    # says nothing about which checkout it belongs to. Same question, two commands, one of
    # them unable to ask it: the way that failed was `fleet check --only slots -k <repo>`
    # answering confidently about the wrong tree.
    p_check.add_argument(
        "--repo",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "the checkout to check (default: cwd). Its own .env / fleet.toml / discovery answer "
            "where the corpus is, exactly as `fleet slots --repo` already resolves it."
        ),
    )
    p_check.add_argument("--list", action="store_true", help="list the installed checks and exit")
    p_check.add_argument(
        "--only",
        metavar="NAME",
        action="append",
        help="run only this check (repeatable). An unknown name is an error, never a silent skip.",
    )
    p_check.add_argument(
        "--level",
        choices=runner.LEVELS,
        default="advisory",
        help="the least severe finding to report (default: advisory, i.e. everything)",
    )
    p_check.add_argument("--strict", action="store_true", help="also exit non-zero on warnings")
    # The three revisions the history-dependent checks need. Separate flags rather than one
    # `--base`, because they answer three different questions and a CI run has three different
    # answers: on a merge-ref checkout the working tree is none of them.
    p_check.add_argument(
        "--base",
        metavar="REF",
        default=None,
        help=(
            "the commit this change is measured against (a PR's base sha). Scopes the PRD process gates "
            "to what this change touched, and gives the statement lock its comparison point."
        ),
    )
    p_check.add_argument(
        "--head",
        metavar="REF",
        default=None,
        help="the branch head, when the working tree is not it (a CI merge-ref checkout)",
    )
    p_check.add_argument(
        "--tip",
        metavar="REF",
        default=None,
        help="the trunk tip — it can see ids minted after this branch diverged; a merge base cannot",
    )
    p_check.add_argument("-v", "--verbose", action="store_true", help="show passing and skipped checks in full")
    p_check.add_argument("--json", action="store_true", help="machine-readable output")
    p_check.set_defaults(func=cmd_check)

    p_slots = sub.add_parser(
        "slots",
        help="what this repo supplies to the command tree, and which commands can run here",
        description=(
            "A slash command is a portable procedure; a repo is a set of filled-in slots. "
            "This prints which slots this checkout fills, which it does not, how each unfilled "
            "optional one degrades, and every command whose `requires:` is unmet. It always "
            "exits 0 \u2014 to GATE on the same data, run `fleet check --only slots`."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_slots.add_argument("--repo", type=Path, default=None, help="the checkout to survey (default: cwd)")
    p_slots.add_argument("-k", "--knowledge-dir", type=Path, default=None, help="its knowledge directory")
    p_slots.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="another repo whose registry defines the slot list, for a checkout that declares none",
    )
    p_slots.add_argument(
        "--registry",
        default=slots_mod.DEFAULT_REGISTRY,
        help=f"registry path relative to the knowledge dir (default: {slots_mod.DEFAULT_REGISTRY})",
    )
    p_slots.add_argument(
        "--commands-dir",
        default=None,
        help=(
            "the command tree, relative to the repo root. Default: the repo's own "
            f"`[fleet.slots] commands_dir`, else {slots_mod.COMMANDS_DIR}"
        ),
    )
    p_slots.add_argument(
        "--emit",
        choices=("questions", "answers"),
        default=None,
        help=(
            "render one half of the split from this repo's registry and exit: `answers` the thin "
            "`fill`-only block that replaces a legacy registry, `questions` the shipped questionnaire "
            "with this repo's rows merged over it (it can add or amend a row, never drop one; what "
            "changed is reported on stderr so stdout stays the file). Retire a row by hand instead."
        ),
    )
    p_slots.add_argument("--json", action="store_true", help="machine-readable output")
    p_slots.set_defaults(func=cmd_slots)

    p_commands = sub.add_parser(
        "commands",
        help="write the shared command tier into a repo's .claude/, or check it is current",
        description=(
            "A slash command is a portable procedure, and this is what makes it portable: the "
            "process documents, registers, rubrics and commands ship WITH this package, and "
            "this writes them into a repository's `.claude/` directory.\n"
            "\n"
            "The version of the procedure a repo is on is then its `fleet-knowledge` version, "
            "rather than whenever somebody last copied a directory.\n"
            "\n"
            "Exit codes: 0 nothing to do (or the sync succeeded), 1 `--check` found drift."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_commands.add_argument("mode", choices=("sync",), nargs="?", default="sync", help=argparse.SUPPRESS)
    p_commands.add_argument("--repo", type=Path, default=None, help="the checkout to write into (default: cwd)")
    p_commands.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit non-zero instead of writing — the CI form",
    )
    p_commands.add_argument(
        "--replace",
        action="append",
        metavar="PATH",
        help=(
            "a setup file (CLAUDE.md, the CI template, an edited fleet.mk, …) whose Fleet part somebody "
            "edited: replace it with "
            "this release's anyway. Repeatable. Without it an edited Fleet part is reported and kept"
        ),
    )
    p_commands.add_argument(
        "--diff",
        action="store_true",
        help="print the diff of every hand-edited file and every setup file the sync changes (`--check` always does)",
    )
    p_commands.add_argument(
        "--json",
        action="store_true",
        help="print the setup files, hand-edited files and overrides as JSON instead of the report",
    )
    p_commands.add_argument(
        "--prune",
        action="store_true",
        help=(
            "also delete tier files this package does not carry. Off by default: a file the "
            "package lacks is usually the repo's own, and `.claude/` is not exclusively ours."
        ),
    )
    p_commands.set_defaults(func=cmd_commands)

    p_init = sub.add_parser(
        "init",
        help="write a repository's planning record and core command tier into it",
        description=(
            "A repository's first contact with Fleet, as files it can commit. Writes the planning "
            "record the board reads — the first slice named from your answer (a fresh repository plans "
            "by feature area, so it sits in the `product` area and no program is written; where a kept "
            "`.fleet/fleet.toml` plans by program, a program and its first slice, as before), the PRD "
            "folder, the requirement register, the product vision, the slot answers — and the core "
            "command set, rendered under the namespace you give, with the shipped scripts. "
            "Idempotent: a file that already exists is kept and reported, and a second run writes "
            "nothing.\n"
            "\n"
            "`--product` and `--slice` (`--program` where the repository plans by program; either name "
            "works) are asked for on a TTY; with no TTY both must be given. `--namespace` is never "
            f"asked for: it defaults to `{commandsync.CUSTOMER_NAMESPACE}`, so "
            f"the commands are typed `/{commandsync.CUSTOMER_NAMESPACE}:check` and so on. `--set` is "
            "`core` (the generic work loop) by default.\n"
            "\n"
            "Fleet's configuration is written to `.fleet/fleet.toml`; nothing is written at the "
            "repository root but the always-on rules file. Its `[fleet.targets]` table says what each "
            "conventional target the commands name runs here: a target an existing Makefile defines "
            "runs as `make <target>`, and `--stack dotnet,node-vue` / `--detect` fill the rest with the "
            "stack profiles' commands. The worker toolchain those commands need is printed.\n"
            "\n"
            "Exit codes: 0 the record is in place, 2 the invocation is wrong."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_init.add_argument("--repo", type=Path, default=None, help="the checkout to initialise (default: cwd)")
    p_init.add_argument("--product", default=None, metavar="NAME", help="the product's name")
    p_init.add_argument(
        "--slice",
        default=None,
        metavar="SENTENCE",
        help="the first slice, as a sentence (a repository planning by area: every fresh one)",
    )
    p_init.add_argument(
        "--program",
        default=None,
        metavar="SENTENCE",
        help="the first program, as a sentence (a repository whose .fleet/fleet.toml plans by program); "
        "in a repository planning by area, the first slice",
    )
    p_init.add_argument(
        "--namespace",
        default=None,
        metavar="NS",
        help=(
            f"the command prefix (`[a-z][a-z0-9-]{{1,30}}`, default `{commandsync.CUSTOMER_NAMESPACE}`); "
            "the commands are typed `/<NS>:…`"
        ),
    )
    p_init.add_argument(
        "--set",
        choices=("core", "all"),
        default=None,
        help="which command set to write: `core` (default) or `all`",
    )
    p_init.add_argument(
        "--stack",
        action="append",
        metavar="IDS",
        help=(
            "the stacks this repository builds in, comma-separated (e.g. `dotnet,node-vue`): their "
            "commands are written to `[fleet.targets]` in `.fleet/fleet.toml`, and the worker "
            "toolchain they need is printed"
        ),
    )
    p_init.add_argument(
        "--detect",
        action="store_true",
        help="detect the stacks from the files present (adds to any `--stack`)",
    )
    p_init.add_argument(
        "--ci-runner",
        default=None,
        metavar="LABEL",
        help="the self-hosted runner label the CI template (`.fleet/ci/fleet-ci.yml`) runs on",
    )
    # What the install already knows, so the slots it determines are written as answers, not placeholders
    # (`slotanswers`). Each is optional: an unknown fact leaves `tracker-identity` a placeholder and makes
    # `git-workflow` name the setting instead of a value. The setup pull request fills them from the install.
    p_init.add_argument(
        "--tracker",
        choices=tuple(slotanswers.TRACKERS),
        default=None,
        help="the tracker the install drives; with --key-prefix (Linear, Jira) it answers `tracker-identity`",
    )
    p_init.add_argument(
        "--tracker-home",
        default=None,
        metavar="WHERE",
        help="where its issues live: the Linear team key, the Jira project key, or the GitHub `owner/name`",
    )
    p_init.add_argument("--key-prefix", default=None, metavar="KEY", help="the issue-key prefix, e.g. `ENG`")
    p_init.add_argument(
        "--lane-label",
        default=None,
        metavar="LABEL",
        help="the `repo:<name>` label that routes an issue here, or `none` for the install's default lane",
    )
    p_init.add_argument(
        "--merge",
        choices=("agents", "person"),
        default=None,
        help="who merges here, as the repository's Merging setting in Fleet says",
    )
    p_init.add_argument(
        "--verify-check",
        default=None,
        metavar="NAME",
        help="the check Fleet posts and requires on this repository (`Fleet verify`), or `none`",
    )
    p_init.set_defaults(func=cmd_init)

    p_board = sub.add_parser(
        "board",
        help="render the program board — what to pick up, what is stuck, what is not yours",
        description=(
            "Five views — what to do next, programs, dependencies, health, commands — plus a page "
            "per program, slice and PRD. Every entity renders UNRANKED here: the authored order is "
            "a fleet-service table a human writes on the Priorities page, and a tree on a disk has "
            "no access to it. Counts and order only: no date, no rate, no capacity."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_root_flag(p_board)
    p_board.add_argument("--template", type=Path, default=None, help="an alternative page template")
    p_board.add_argument("--guidance", type=Path, default=None, help="JSON file of this project's command vocabulary")
    p_board.add_argument(
        "--title", default=board_mod.DEFAULT_TITLE, help=f"masthead title (default: {board_mod.DEFAULT_TITLE!r})"
    )
    p_board.add_argument("--intent-title", default=board_mod.DEFAULT_INTENT_TITLE, help="what to call the first view")
    p_board.add_argument("--out", type=Path, default=None, help="output file (default: <knowledge>/program-board.html)")
    p_board.add_argument("--open", action="store_true", help="open the result in a browser")
    p_board.add_argument("--quiet", action="store_true", help="do not print the output path")
    p_board.set_defaults(func=cmd_board)

    p_planning = sub.add_parser(
        "planning",
        help="where new slices go — `migrate` gives every live slice its feature area, by one reviewed PR",
    )
    planning_sub = p_planning.add_subparsers(dest="planning_command", metavar="SUBCOMMAND", required=True)
    p_migrate = planning_sub.add_parser(
        "migrate",
        help="give every live slice a feature area; optionally take the repository off programs",
        description=(
            "Three jobs. (1) Area backfill, always: every live slice with no `area` gets one — from the area its\n"
            "PRDs agree on, else from the one feature map holding all its components; anything else is listed\n"
            "as CANNOT PLACE and left alone. (2) Off programs, only with --drop-programs: each live slice\n"
            'leaves its program (kept as `from_program`); --flip also sets [fleet.planning] mode = "areas".\n'
            "(3) Close the programs, only with --close-programs (implies --drop-programs): every open program\n"
            "is marked `superseded by areas` after its live slices left it, and each open PRD its Verified by\n"
            "names becomes one area slice of its own; a program holding a slice it cannot place stays open.\n\n"
            "A DRY RUN BY DEFAULT: prints what it would change and writes nothing. Finished and withdrawn\n"
            "slices, and finished, waived and withdrawn programs, are never touched, so every PG-NN keeps\n"
            "resolving.\n\n"
            "Exit: 0 nothing left or all placed; 1 at least one slice could not be placed (or a program stays\n"
            "open because of one); 2 usage or repo error."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_root_flag(p_migrate)
    p_migrate.add_argument("--repo", type=Path, default=None, help="the repository to migrate (default: this one)")
    p_migrate.add_argument("--drop-programs", action="store_true", help="also take every live slice off its program")
    p_migrate.add_argument("--flip", action="store_true", help='with --drop-programs: set mode = "areas"')
    p_migrate.add_argument(
        "--close-programs",
        action="store_true",
        help="also close every open program into feature areas, its open proof PRDs becoming area slices",
    )
    p_migrate.add_argument("--require-area", action="store_true", help="also set [fleet.planning] require_area = true")
    p_migrate.add_argument("--write", action="store_true", help="write the change into this working tree")
    p_migrate.add_argument(
        "--pr", action="store_true", help="write it on a new branch in a temporary worktree and open one PR"
    )
    p_migrate.add_argument("--base", default="origin/main", help="what --pr branches from (default: origin/main)")
    p_migrate.add_argument("--branch", default="knowledge/slices-to-areas", help="the branch --pr opens")
    p_migrate.add_argument("--json", action="store_true", help="print the plan as JSON")
    p_migrate.set_defaults(func=cmd_planning_migrate)

    p_digest = sub.add_parser(
        "digest",
        help="the binding digest of one planning row's completion cell",
        description=(
            "Prints the 64-hex digest the `bars` check binds a bar to: the SHA-256 of the exact "
            "authored bytes of the row's `Done when` cell. Compute it from the register AFTER the "
            "row is written; a hand-rolled hash over what you think the cell says is the defect "
            "the digest exists to catch."
        ),
    )
    _add_root_flag(p_digest)
    p_digest.add_argument("register", help="the planning register, relative to the knowledge dir (e.g. slices.md)")
    p_digest.add_argument("row", help="the row id (e.g. SL-165)")
    p_digest.set_defaults(func=cmd_digest)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "command", None):
        ap.print_help()
        return 2
    result: int = args.func(args)
    return result


__all__ = ["Origin", "build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

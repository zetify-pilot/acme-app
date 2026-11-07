"""The four commitment checks, as the runner sees them.

Each one wraps a validator that used to be a standalone script in `scripts/`. The wrapping
is thin on purpose: the rules, the messages and the severities live in the modules beside
this one, and this file only decides **when a check applies** and **how a violation is
handed to a board**.

`applies()` is the half that is new, and it is what makes these usable outside the corpus
they were written for. A knowledge base with no `requirements/` directory has no register
to validate, no statements to guard and no coverage to be exhaustive over — it is not
FAILING those checks, it does not have them. The old scripts had no way to say that: with
no register they printed `requirements OK — 0 register(s)` and exited 0, which reads as a
pass and is really an absence. Here it is a skip with a reason.

`Finding.hint` and `Finding.command` are load-bearing, not decoration: a board renders the
command as something a reader can run. Every message that has a knowable fix carries one,
and the command is spelled from configuration, so a project whose entry points are named
differently gets its own spelling rather than this repo's.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ...config import KnowledgeBase, git_context
from ...runner import Finding
from . import coverage as _coverage
from . import registers as _registers
from . import statements as _statements
from . import todos as _todos
from .context import Context, context_for

# `<path>: <message>` — how every ported validator names the file a violation is in. The
# prefix is turned back into a real `Finding.path` so a board can link it; a message with
# no resolvable prefix keeps the whole string, which is the safe direction.
_PREFIXED_RE = re.compile(r"^([\w./@+-]+\.(?:md|lock|baseline|py|yaml|yml|json)):\s+(.*)$", re.S)
_LINE_RE = re.compile(r"\bline (\d+)\b")


def _split(ctx: Context, raw: str) -> tuple[Path | None, int | None, str]:
    """`(path, line, message)` out of one accumulated violation string.

    The prefix is stripped ONLY when it resolves to a real file. A note that happens to
    open with a filename-shaped word (`UNCLAIMED.baseline: 193 documents…`) keeps its whole
    sentence — dropping the half a message needs to make sense, in exchange for a link that
    would not have worked, is the wrong trade.
    """
    m = _PREFIXED_RE.match(raw)
    if not m:
        return None, None, raw
    candidate = ctx.root / m.group(1)
    if not candidate.exists():
        return None, None, raw
    message = m.group(2)
    lm = _LINE_RE.search(message)
    return candidate, int(lm.group(1)) if lm else None, message


@dataclass(frozen=True)
class _Hint:
    """One `(pattern -> hint, command)` rule. First match wins."""

    pattern: str
    hint: str
    command_attr: str | None = None
    command_args: str = ""


class _Check:
    """Shared plumbing: build a context, run the ported checks, shape the findings."""

    name = ""
    title = ""
    description = ""
    hints: tuple[_Hint, ...] = ()

    def applies(self, kb: KnowledgeBase) -> bool:
        raise NotImplementedError

    def reason_not_applicable(self, kb: KnowledgeBase) -> str:
        raise NotImplementedError

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        raise NotImplementedError

    # ── helpers ──────────────────────────────────────────────────────────────
    def _context(self, kb: KnowledgeBase) -> Context:
        return context_for(kb)

    def _hint_for(self, ctx: Context, message: str) -> tuple[str | None, str | None]:
        for h in self.hints:
            if re.search(h.pattern, message):
                cmd = None
                if h.command_attr:
                    base = getattr(ctx.cfg, h.command_attr, "")
                    cmd = f"{base} {h.command_args}".strip() if base else None
                return h.hint, cmd
        return None, None

    def _findings(self, ctx: Context, errors: list[str], notes: list[str]) -> list[Finding]:
        out: list[Finding] = []
        for level, raws in (("error", errors), ("advisory", notes)):
            for raw in raws:
                path, line, message = _split(ctx, raw)
                hint, command = self._hint_for(ctx, message)
                out.append(
                    Finding(
                        level=level,
                        message=message,
                        path=path,
                        line=line,
                        hint=hint,
                        command=command,
                    )
                )
        return out


class RequirementRegisters(_Check):
    """The register itself, plus the PRD `implements:` edge."""

    name = "requirement-registers"
    title = "Requirement registers"
    description = (
        "Every commitment a corpus makes is one numbered row in a per-domain register, and the "
        "load-bearing rule is that an ID is PERMANENT and never reused — because everything "
        "downstream (a PRD's `implements:`, a spec citing the id instead of restating the rule, the "
        "derived backlog) is a string match on it. This validates the register's structure (id shape, "
        "uniqueness within and across files, the Kind/Disposition/Cut vocabularies and their legality, "
        "the supersession and Needs graphs being acyclic and residue-free, the append-at-end rule that "
        "makes two concurrent allocations conflict instead of merging into a duplicate, and that every "
        "`Source` anchor still lands where it says), and it validates the realisation edge from PRDs: a "
        "claim must resolve, be covered by an acceptance criterion from `planned` onward, and not point "
        "at a row the register has refused or replaced. It also reads the edge backwards — a requirement "
        "statement reappearing verbatim in prose without that row cited is a failed citation."
    )
    hints = (
        _Hint(
            r"duplicate requirement id",
            "Two rows carry one permanent id. Renumber the row YOUR branch added — never the one that "
            "was already on the base — with an id from `validate_id_collisions.py --allocate`.",
        ),
        _Hint(
            r"no acceptance criterion cites it",
            "Add the bracketed id to the acceptance criterion that would fail if the requirement were "
            "not met — one direction only, an AC citing nothing stays legal.",
            "cmd_validate_requirements",
        ),
        _Hint(
            r"does not resolve to a requirement row",
            "Ids are permanent, so this is a typo or a row someone deleted. Fix the reference, or "
            "restore the row and supersede it in place.",
        ),
        _Hint(
            r"is placed above lower-numbered rows",
            "Move the row to the END of its register. A mid-file insert merges cleanly with another "
            "author's mid-file insert and lands one id twice; two appends conflict instead.",
        ),
        _Hint(
            r"quoted verbatim without citing the row",
            "Prose may not restate a commitment, it cites one — add the bracketed id at (or next to) "
            "the restatement so a reader can follow it back.",
        ),
        _Hint(
            r"is `superseded|still carries Needs|which is `rejected",
            "Clearing the edge is part of the supersession, not a follow-up: re-point it at the "
            "successor row, or drop it.",
        ),
        _Hint(
            r"baseline entr\(y/ies\).*are no longer violations",
            "Delete those lines from the ratchet file — the baseline only ever shrinks, and a stale "
            "entry pre-grandfathers a future regression of that same row.",
        ),
        _Hint(r".", "Run the register validator for the full context.", "cmd_validate_requirements"),
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return bool(self._context(kb).registers())

    def reason_not_applicable(self, kb: KnowledgeBase) -> str:
        ctx = self._context(kb)
        return f"no requirement register found under {ctx.rel(ctx.register_dir)}/ — this corpus has no constraint axis"

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        ctx = self._context(kb)
        _registers.run_all(ctx)
        return self._findings(ctx, ctx.errors, ctx.notes)


class RequirementStatementGuard(_Check):
    """The statement guard — a permanent id must guarantee the MEANING, not the string."""

    name = "requirement-statement-guard"
    title = "Requirement statement guard"
    description = (
        "A permanent id protects the NUMBER; on its own it does not protect what the number means. So "
        "every row that existed at the comparison base (the pull request's base commit, or the merge "
        "base with the trunk) is compared with the tree: appended to is fine and expected; rewritten is "
        "allowed only while superseding into a newly minted id or while no PRD claims the row; deleted "
        "is never allowed, since ids are permanent; and an id REBOUND onto someone else's statement is "
        "never allowed. Stateless — there is no lock file for concurrent changes to collide on — and "
        "fail-closed: with no resolvable base the check fails rather than passing a comparison it never "
        "made."
    )
    hints = (
        _Hint(
            r"no comparison base|is not a commit in this repository",
            "Fetch the base branch (in CI: check out with full history) or pass `--base <commit>`, then "
            "re-run — the guard refuses to report a pass it did not compute.",
            "cmd_validate_statements",
        ),
        _Hint(
            r"no longer present in any register",
            "Ids are PERMANENT: restore the row and mark it `superseded` or `rejected` in place rather "
            "than deleting it.",
        ),
        _Hint(
            r"ID cell was REWRITTEN",
            "Renumber only rows YOUR branch added. If a meaning must move, mint a new row and supersede "
            "this one into it.",
        ),
        _Hint(
            r"statement was REWRITTEN",
            "Mint a new row and set this one `superseded by <new id>` — or, if the wording never carried "
            "the old meaning, say so in the commit and drop the claim first.",
        ),
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return bool(self._context(kb).registers())

    def reason_not_applicable(self, kb: KnowledgeBase) -> str:
        ctx = self._context(kb)
        return f"no requirement register found under {ctx.rel(ctx.register_dir)}/ — there are no statements to guard"

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        import argparse

        ctx = self._context(kb)
        # An explicit base beats `resolve_base`'s merge-base-with-the-trunk fallback. The two
        # agree on a normal branch checkout and diverge on a CI merge ref, where the caller is
        # the only party that still knows which commit this change is measured against.
        base = git_context(kb).base or None
        rows, errors, notes, _base_ref, _base_rows = _statements._check(ctx, argparse.Namespace(base=base))
        del rows
        return self._findings(ctx, errors, notes)


class CommitmentCoverage(_Check):
    """Exhaustive coverage: prose that can carry a commitment must be claimed."""

    name = "commitment-coverage"
    title = "Commitment coverage"
    description = (
        "A register declares which prose it is the constraint axis for. This checks that the declaration "
        "is EXHAUSTIVE over the corpus that can carry a *the system shall / never* — every spec and every "
        "decision record must be claimed by some register's `source_of_truth:`, excluded by a reviewed "
        "TYPE carve-out (an index, a template, a dated worked example, a review checklist), or named in "
        "the unclaimed baseline as acknowledged debt. The baseline may SHRINK, never grow: an addition "
        "needs a matching burn-down in the same change or an explicit `# ack:` line, because regenerating "
        "the file to absorb new debt would launder exactly the signal it exists to keep. Second leg: a "
        "declared `source_of_truth:` path must resolve, since a dangling claim covers nothing while "
        "reading as coverage."
    )
    hints = (
        _Hint(
            r"unclaimed prose",
            "Claim the document from the register that owns its domain, or add it to the baseline as "
            "acknowledged debt.",
            "cmd_validate_coverage",
            "--write-baseline",
        ),
        _Hint(
            r"baseline grew",
            "Claim the document from a register, burn down an entry in the same change, or record "
            "`# ack: <path> <reason>` above it — the baseline may shrink, never grow.",
        ),
        _Hint(
            r"does not exist — a dangling claim",
            "Fix the path or drop the entry: a claim that resolves to nothing covers nothing while "
            "reading as coverage.",
        ),
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        ctx = self._context(kb)
        if not ctx.registers():
            return False
        return any((ctx.root / root.rstrip("/")).is_dir() for root in _coverage.coverage_roots(ctx))

    def reason_not_applicable(self, kb: KnowledgeBase) -> str:
        ctx = self._context(kb)
        if not ctx.registers():
            return (
                f"no requirement register found under {ctx.rel(ctx.register_dir)}/ — nothing declares "
                "which prose it is the constraint axis for"
            )
        roots = ", ".join(_coverage.coverage_roots(ctx))
        return f"none of the coverage roots exist ({roots}) — this corpus has no commitment-bearing prose"

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        ctx = self._context(kb)
        _coverage.check_claims_resolve(ctx)
        _coverage.check_coverage(ctx)
        _coverage.check_baseline_ratchet(ctx)
        return self._findings(ctx, ctx.errors, ctx.notes)


class TodoRegister(_Check):
    """The todo register and every citation of it."""

    name = "todo-register"
    title = "Todo register"
    description = (
        "The register of things noticed and not yet settled — not decisions (those are requirement rows) "
        "and not dispatchable work (those are tracker issues), but the questions raised in passing that "
        "otherwise die with the session. A file you can open is complete by construction; a marker "
        "convention is only as complete as its least careful author. This enforces that ids are a "
        "contiguous append-only run with a correct counter (so an id is permanent and safe to cite), that "
        "a row which fails to parse is a hard error rather than a silent skip, that a closed row says how "
        "it was settled and a `filed` one names a real issue key, and that every citation of the register "
        "anywhere in the tree resolves to a real row — a pointer to nothing reads as tracked when it is not."
    )
    hints = (
        _Hint(
            r"append-only violated|out of sequence",
            "Rows are closed, never deleted: restore the missing row and mark it `done` or `dropped` "
            "with a note saying why.",
        ),
        _Hint(
            r"but the highest row is",
            "Set the `APPEND ONLY. Next id:` counter to one past the highest row in the same change that takes the id.",
        ),
        _Hint(
            r"is `filed` but `Refs` names no well-formed issue",
            "Put the real issue key in `Refs` — 'filed' without one is where work goes to disappear.",
        ),
        _Hint(
            r"which is not a row in",
            "A citation that resolves to nothing reads as tracked when it is not: fix the id, or add the row it meant.",
        ),
        _Hint(r".", "Run the todo validator for the full list.", "cmd_validate_todos"),
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return self._context(kb).todo_register_path.is_file()

    def reason_not_applicable(self, kb: KnowledgeBase) -> str:
        ctx = self._context(kb)
        return f"no todo register at {ctx.rel(ctx.todo_register_path)} — this corpus keeps no open-question list"

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        ctx = self._context(kb)
        try:
            rows = _todos.rows(ctx)
        except _todos.TodoParseError as exc:
            return [
                Finding(
                    level="error",
                    message=str(exc),
                    path=ctx.todo_register_path,
                    line=_first_line(str(exc)),
                    hint="A row that fails to parse must be fixed, never silently dropped — the register "
                    "exists so an open question does not die with the session.",
                    command=ctx.cfg.cmd_validate_todos,
                )
            ]
        errs = _todos.validate(ctx, rows, _todos.citations(ctx))
        return self._findings(ctx, errs, [])


def _first_line(message: str) -> int | None:
    m = re.match(r"^[^:]+:(\d+):", message)
    return int(m.group(1)) if m else None


# NOT named `CHECKS`, deliberately. The runner may walk this package with `iter_modules`
# (which yields the SUBPACKAGE) or recurse with `walk_packages` (which yields this module
# too). Exporting `CHECKS` from both the subpackage's `__init__` and from here would
# register four checks twice under the recursive walk. One export point, on the package —
# see `__init__.py`.
ALL_CHECKS = [RequirementRegisters(), RequirementStatementGuard(), CommitmentCoverage(), TodoRegister()]

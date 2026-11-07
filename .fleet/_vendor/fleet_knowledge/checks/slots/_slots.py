"""Is this repo's slot registry honest, and which commands can actually run here?

The `slots` check answers both halves of the question a person could not previously ask
of a checkout: *is what the registry claims true*, and *what is missing*.

WHAT IT GATES, and what it deliberately does not:

  * A **mandatory** slot whose `fill` resolves to nothing is an **error**. A command that
    declares it in `requires:` cannot run here, and a repo that ships the command tree
    while silently lacking the answer is the failure this whole layer exists to prevent.
  * An **optional** slot is an **advisory** naming its own `degrade`. An unfilled optional
    slot is a smaller run, never a broken one — failing on one would teach people to turn
    the check off, and the runner's whole contract is that a corpus without some ground
    SKIPS honestly rather than reddening a build.
  * A **shared** slot (one that ships under `.claude/`) that is missing is an error with a
    DIFFERENT hint: nothing is wrong with the repo's answers, the command tree it was
    given is incomplete. Conflating the two sends a reader to fix the wrong file.
  * A spine naming a slot id **no questionnaire asks** is an **error** — that is a typo,
    and a typo in a `requires:` gates nothing while looking exactly like a gate. Measured
    against the RESOLVED slot set instead, as it was, this fired on every optional question
    a repo had legitimately declined: `slots/README.md` tells a repo that a question it has
    not taken on "is simply absent", and doing that produced 62 errors here for ids the
    shipped questionnaire defines — while `fleet slots`, reading the same tree, listed them
    under `not answered` and blocked nothing. Two readers of one repo, contradicting each
    other, and the gate was the one that was wrong. A declined question is already reported
    twice: as `unanswered` below, and per-command through the blocked-command line when the
    spine had it in `requires:`.
  * A `consumed_by` entry naming a command with no spine here is a **warning**, not an
    error: command trees legitimately differ between repos, and a slot may be consumed by
    a command this checkout does not carry.

`applies()` is the honest predicate the runner requires: a repo with neither a command
tree nor a slot registry has no commands to run and nothing to validate, so it SKIPS with
a line saying so.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fleet_knowledge import rulesfile
from fleet_knowledge import slots as slotmod
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.runner import Finding

# `[fleet.slots]` vocabulary. A key outside this set is refused rather than ignored, the
# same way the top-level table is — a silently-ignored option is a setting someone
# believes is in force.
KNOWN_OPTIONS = frozenset({"registry", "commands_dir"})

_SENTINEL = object()


def _probe(holder: object, key: str) -> object:
    """`holder.key` or `holder["key"]`, whichever the holder actually offers."""
    if isinstance(holder, dict):
        return holder.get(key, _SENTINEL)
    return getattr(holder, key, _SENTINEL)


def option(kb: KnowledgeBase, key: str, default: object) -> object:
    """This family's value for `key`, or `default`.

    Reads the `[fleet.slots]` table FIRST, then the spine's `Config` — the same order every
    other family uses, and for the same reason: a project writing both is saying "this family
    reads a different one", and the general value winning would make the specific one
    unwritable. Never raises on a config that predates the key; absent means the default.
    """
    config = getattr(kb, "config", None)
    if config is None:
        return default
    for holder in (_probe(config, "slots"), config):
        if holder is _SENTINEL or holder is None:
            continue
        value = _probe(holder, key)
        if value is not _SENTINEL and value is not None:
            return value
    return default


@dataclass
class SlotsCheck:
    """The command↔repo interface, verified against the tree it describes."""

    name: str = "slots"
    title: str = "slot registry — what this repo answers, and which commands can run"
    description: str = (
        "A slash command is a portable procedure and a repo is a set of filled-in slots. "
        "This check reads the repo's slot registry, probes every declared `fill` against the "
        "working tree, and joins the result to the command spines: a mandatory slot with no "
        "answer fails, an optional one degrades in the way it names, and every command whose "
        "`requires:` is unmet is reported by name so nobody has to discover it mid-run."
    )

    def _registry_rel(self, kb: KnowledgeBase) -> str:
        return str(option(kb, "registry", slotmod.DEFAULT_REGISTRY))

    def _commands_rel(self, kb: KnowledgeBase) -> str:
        return str(option(kb, "commands_dir", slotmod.default_commands_dir(kb.root)))

    def applies(self, kb: KnowledgeBase) -> bool:
        has_commands = (kb.root / self._commands_rel(kb)).is_dir()
        has_registry = (kb.knowledge / self._registry_rel(kb)).is_file()
        return has_commands or has_registry

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        registry_rel = self._registry_rel(kb)
        commands_rel = self._commands_rel(kb)
        survey = slotmod.survey(kb.root, kb.knowledge, registry_rel=registry_rel, commands_dir=commands_rel)
        out: list[Finding] = []

        # --- the registry itself -------------------------------------------------
        if not survey.registry.present:
            # A repo with commands but no registry is not broken — it has simply never
            # declared what it supplies. Say exactly that, and say how to find out.
            return [
                Finding(
                    level="warning",
                    message=(
                        f"no slot registry at {registry_rel} — this repo ships a command tree but has "
                        "never declared what it supplies to it, so nothing can say which commands can run here"
                    ),
                    path=kb.knowledge / registry_rel,
                    hint="Declare one, or compare against a repo that has one to see what is missing.",
                    command=f"fleet slots --repo {kb.root} --reference <path/to/repo/with/a/registry>",
                )
            ]

        for err in survey.registry.errors:
            out.append(
                Finding(
                    level="error",
                    message=f"slot registry: {err}",
                    path=survey.registry.path,
                    hint="The registry is the file that decides what gates a command; a malformed row gates nothing.",
                )
            )
        # Three severities because three different people fix them, and flattening them
        # would make the loudest one the only one anybody reads. A repo still on the legacy
        # shape is not broken — reporting it as an error would only get the check switched
        # off before the migration it is asking for.
        for warn in survey.registry.warnings:
            out.append(
                Finding(
                    level="warning",
                    message=f"slot registry: {warn}",
                    path=survey.registry.path,
                    hint="The questionnaire is the shared vocabulary; a slot outside it is one repo's private word.",
                )
            )
        for note in survey.registry.notes:
            out.append(
                Finding(
                    level="advisory",
                    message=f"slot registry: {note}",
                    path=survey.registry.path,
                )
            )
        if survey.registry.unanswered:
            ids = ", ".join(survey.registry.unanswered)
            out.append(
                Finding(
                    level="advisory",
                    message=(
                        f"{len(survey.registry.unanswered)} question(s) in the shipped questionnaire that this "
                        f"repo takes no position on at all, so nothing above speaks for them: {ids}"
                    ),
                    path=survey.registry.path,
                    hint="Answer one with a `fill`, or leave it — an unasked optional question costs its `degrade`.",
                )
            )

        # --- every slot, probed against the tree ---------------------------------
        for fill in survey.fills:
            slot = fill.slot
            if fill.filled:
                # A partly-resolved fill is worth one advisory: the slot is answered, but
                # a pattern in it names nothing, which is usually a path that moved.
                if fill.missing:
                    out.append(
                        Finding(
                            level="advisory",
                            message=(
                                f"slot `{slot.id}` is filled, but {len(fill.missing)} of its `fill` "
                                f"pattern(s) match nothing: {', '.join(fill.missing)}"
                            ),
                            path=survey.registry.path,
                            hint="Remove the stale pattern or restore the path it names.",
                        )
                    )
                continue

            where = ", ".join(slot.fill) or "(no fill declared)"
            if fill.stub:
                # A PLACEHOLDER, honestly marked: the slot is unfilled and `fleet slots` and the
                # board say so, but the corpus is well-formed. This check is what `make
                # validate-knowledge` runs on every change, and failing every pull request of a
                # freshly scaffolded repository until somebody writes its answers would gate the
                # wrong thing — so a stub is a warning here, never an error.
                stub_paths = ", ".join(str(p.relative_to(kb.root)) for p in fill.stubs)
                out.append(
                    Finding(
                        level="warning" if slot.mandatory else "advisory",
                        message=(
                            f"{'mandatory' if slot.mandatory else 'optional'} slot `{slot.id}` is only a "
                            f"placeholder ({stub_paths}): {slot.answers}"
                            + (
                                f" Commands that cannot run until it is answered: "
                                f"{', '.join(sorted(slot.consumed_by)) or 'no command yet'}."
                                if slot.mandatory
                                else f" Degrades to: {slot.degrade or 'unspecified'}"
                            )
                        ),
                        path=fill.stubs[0],
                        hint=(
                            "Replace the placeholder with the real answer "
                            f"(and delete any `{slotmod.STUB_MARKER}` line)."
                        ),
                    )
                )
                continue
            if slot.shared:
                out.append(
                    Finding(
                        level="error",
                        message=(
                            f"shared slot `{slot.id}` is missing: {where}. This ships WITH the command "
                            "tree, so the tree in this checkout is incomplete — it is not a repo answer."
                        ),
                        path=survey.registry.path,
                        hint="Sync the command tree; a shared slot is never a repo's to supply.",
                    )
                )
            elif slot.mandatory:
                users = ", ".join(sorted(slot.consumed_by)) or "no command yet"
                out.append(
                    Finding(
                        level="error",
                        message=(
                            f"mandatory slot `{slot.id}` is unfilled: {where}. "
                            f"{slot.answers} Commands that cannot run without it: {users}."
                        ),
                        path=survey.registry.path,
                        hint=f"Create {slot.fill[0] if slot.fill else 'the fill path'} and answer the question in it.",
                    )
                )
            else:
                out.append(
                    Finding(
                        level="advisory",
                        message=(
                            f"optional slot `{slot.id}` is unfilled: {where}. "
                            f"Degrades to: {slot.degrade or 'unspecified'}"
                        ),
                        path=survey.registry.path,
                    )
                )

        # --- the registry ↔ command-spine join -----------------------------------
        for command, sid in survey.unknown_slot_refs:
            out.append(
                Finding(
                    level="error",
                    message=(
                        f"command `{command}` declares slot `{sid}`, which no questionnaire asks and no "
                        "registry defines — a declared need nothing anywhere defines gates nothing"
                    ),
                    hint=(
                        "Almost always a typo in the spine. Check it against "
                        f"`fleet slots --repo {kb.root} --emit questions`, which needs no registry."
                    ),
                )
            )
        for sid, command in survey.unknown_command_refs:
            out.append(
                Finding(
                    level="warning",
                    message=(f"slot `{sid}` lists `consumed_by: {command}`, which has no spine in this checkout"),
                    path=survey.registry.path,
                    hint="Command trees differ between repos; drop the entry if that command never runs here.",
                )
            )

        # --- the answer people actually want -------------------------------------
        fills_by_id = survey.fill_of()
        for need, blockers in survey.blocked_commands():
            # Blocked only by placeholders: reported, at the stub's own severity (above).
            only_stubs = all(sid in fills_by_id and fills_by_id[sid].stub for sid in blockers)
            out.append(
                Finding(
                    level="warning" if only_stubs else "error",
                    message=(
                        f"`/{need.command}` cannot run in this repo — unfilled required slot(s): {', '.join(blockers)}"
                        + (" (each only a placeholder)" if only_stubs else "")
                    ),
                    path=need.path,
                    hint="Fill the slot, or remove it from the command's `requires:` if it is genuinely not needed.",
                )
            )

        return out


def summary_lines(
    root: Path,
    knowledge: Path,
    *,
    reference_root: Path | None = None,
    reference_knowledge: Path | None = None,
    registry_rel: str = slotmod.DEFAULT_REGISTRY,
    commands_dir: str | None = None,
) -> list[str]:
    """The human report behind `fleet slots` — the same survey, rendered for reading.

    `reference_*` is what makes the tool answer the question for a repo that has declared
    nothing: probe it against another repo's registry, so "0 of 5 mandatory filled" is a
    sentence someone can actually say.
    """
    commands_dir = commands_dir or slotmod.default_commands_dir(root)
    reference = None
    if reference_root is not None:
        reference = slotmod.read_registry(
            reference_root, reference_knowledge or (reference_root / "knowledge"), registry_rel
        )
    s = slotmod.survey(root, knowledge, registry_rel=registry_rel, commands_dir=commands_dir, reference=reference)

    lines: list[str] = [f"repo: {root}"]
    found_rules = rulesfile.rules_file(root)
    lines.append(
        f"rules: {found_rules.name} — the always-on rules an agent session starts from"
        if found_rules is not None
        else (
            "rules: MISS — not ready: this repository has no always-on rules file "
            f"({rulesfile.RULES_FILES[0]}), so every agent session here starts with no standing "
            "project instructions"
        )
    )
    if s.registry.present and s.registry.slots:
        lines.append(f"registry: {s.registry.path}")
    elif reference is not None:
        lines.append(f"registry: NONE — compared against {reference.path}")
    else:
        # NOT "and therefore nothing is known". The shared tier ships with the commands and
        # is surveyed regardless, so this report is already true about most of the tree —
        # saying only "NONE" here is what made a reader take the blocked lines below for a
        # broken sync rather than for the answers this repo simply has not written yet.
        lines.append(
            f"registry: NONE at {registry_rel} — measured against the shipped questionnaire "
            "(shared tier ships with the commands; repo-tier answers are yours to write)"
        )
        lines.append(f"          `fleet slots --repo {root} --emit answers` prints the blank answer sheet")
    if s.registry.present:
        for e in s.registry.errors:
            lines.append(f"  ! {e}")
        for w in s.registry.warnings:
            lines.append(f"  ! {w}")
        for n in s.registry.notes:
            lines.append(f"  - {n}")

    groups = (
        ("shared  ", [f for f in s.fills if f.slot.shared]),
        ("required", [f for f in s.fills if not f.slot.shared and f.slot.mandatory]),
        ("optional", [f for f in s.fills if not f.slot.shared and not f.slot.mandatory]),
    )
    for label, fills in groups:
        if not fills:
            continue
        ok = sum(1 for f in fills if f.filled)
        stubs = sum(1 for f in fills if f.stub)
        lines.append("")
        lines.append(f"{label}  {ok}/{len(fills)} filled" + (f", {stubs} only a placeholder (stub)" if stubs else ""))
        for f in sorted(fills, key=lambda x: (x.filled, x.slot.id)):
            # THREE STATES, not two: a placeholder file is there and answers nothing, and saying
            # `MISS` would send a reader looking for a file that exists (see `slots.STUB_MARKER`).
            mark = "ok  " if f.filled else "STUB" if f.stub else "MISS"
            detail = ""
            if f.stub:
                where = ", ".join(str(p.relative_to(root)) for p in f.stubs)
                detail = f"  <- {where}: a placeholder — replace it with the real answer"
                if not f.slot.mandatory and f.slot.degrade:
                    detail += f"   [degrades: {f.slot.degrade}]"
            elif not f.filled:
                detail = f"  <- {', '.join(f.slot.fill) or 'no fill declared'}"
                if not f.slot.mandatory and f.slot.degrade:
                    detail += f"   [degrades: {f.slot.degrade}]"
            lines.append(f"  {mark} {f.slot.id}{detail}")

    # NOT COUNTED ANYWHERE ABOVE, and that is why it has to be printed. A tier line reads
    # "optional 3/9 filled" over the questions this repo took on; a question it never named
    # is in neither half of that fraction and would otherwise be invisible in the one report
    # a person runs to find out what is missing.
    if s.registry.unanswered:
        lines.append("")
        lines.append(f"not answered  {len(s.registry.unanswered)} shipped question(s) this repo does not name")
        lines.append(f"  {', '.join(s.registry.unanswered)}")

    blocked = s.blocked_commands()
    lines.append("")
    if not s.needs:
        lines.append("commands: no spine declares slots in this checkout")
    elif not blocked:
        lines.append(f"commands: all {len(s.needs)} spined command(s) can run here")
    else:
        lines.append(f"commands: {len(s.needs) - len(blocked)}/{len(s.needs)} can run here")
        for need, blockers in blocked:
            lines.append(f"  BLOCKED /{need.command}  <- {', '.join(blockers)}")

    # WHAT THE LINE ABOVE DID NOT SPEAK FOR. Every count here is over SPINED commands —
    # `read_command_needs` can only see a command that declared something — so a tree
    # where two thirds carry no spine printed "all 16 spined command(s) can run here"
    # and never mentioned the other 18. The word "spined" was carrying the whole caveat,
    # and a reader scanning for a verdict reads that line as an all-clear.
    undeclared = _undeclared(root, commands_dir, {n.path for n in s.needs})
    if undeclared:
        lines.append(
            f"  {len(undeclared)} command(s) declare no slots at all and are not covered "
            f"by the line above: {', '.join(undeclared[:8])}"
            + (f", +{len(undeclared) - 8} more" if len(undeclared) > 8 else "")
        )
    return lines


def _undeclared(root: Path, commands_dir: str, spined: set[Path]) -> list[str]:
    """Command files in the tree that no spine speaks for, by the name a person types.

    Read off the filesystem rather than from the survey, because the survey is built FROM
    the spines: a command with none contributes nothing to it and is invisible there by
    construction. That is exactly why it has to be counted somewhere else.

    Matched BY PATH, which `CommandNeed` already carries. The obvious alternative — compare
    the spine's `command` id against the file name with `:` swapped for `-` — is a guess
    that a spine id mirrors its path, and it holds for every command here today. A command
    that names itself something else would be reported as undeclared while carrying a
    perfectly good spine, and the report would be wrong in the direction nobody checks.
    """
    base = root / commands_dir
    if not base.is_dir():
        return []
    return [
        ":".join(path.relative_to(base).with_suffix("").parts)
        for path in sorted(base.rglob("*.md"))
        if path not in spined
    ]

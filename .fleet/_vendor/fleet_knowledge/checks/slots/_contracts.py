"""Does every reference in the tree resolve to something the tree actually defines?

`_portability.py` asks whether a command names something the fixed layout does not provide.
This asks the question one level up: when a command names something the tree itself
defines, does it exist?

Three references, three resolutions:

  * **A slot citation's ID.** `slot:git-workflow` names a question; a slot id the
    questionnaire does not ask is answered by no repository, so a citation of one is an
    instruction that resolves to nothing while looking exactly like one that resolves.
  * **A spine's `sop`.** Seven of thirty-four named a SOP file the repository does not have;
    two named a register slug in a field meant for SOPs. The field now resolves: `none`, or
    the `slug:` of a document the tier itself carries.
  * **A critique rubric's `spec`.** Two registered rubrics pointed at sections of a shared
    document that did not exist, and four hard gates graded against them. A gate that can
    only be faked is worse than no gate — spine.md's own words. The spec now has to resolve
    to a file the tier carries, and to a heading in it when one is named.

And one structural rule with the same shape: every file under the shared tier's directories
must be the `fill` of exactly one shared slot. One process document shipped to six
repositories with no slot row and no reference from any file in the tree — loaded by nothing,
gradeable by nothing.

The first version of this check also held every tool citation's argv to a register's grammar
and every slot citation's key to a declared list. Both are gone with the register: a script
named by its path has its own `--help`, and a slot is cited whole.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fleet_knowledge import commands as commandmod
from fleet_knowledge import slots as slotmod
from fleet_knowledge.checks.slots._portability import _shared_docs, _tier_root
from fleet_knowledge.checks.slots._slots import option
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.runner import Finding

_SLUG = re.compile(r"^slug:\s*([a-z0-9][a-z0-9-]*)\s*$", re.MULTILINE)
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_SPEC = re.compile(r"^(?P<path>[^§#]+?)(?:\s*(?:§|#)\s*(?P<heading>.+))?$")
#: `slot:<id>` in a code span or a fence placeholder — how a command names a repository's
#: answer. The id is the whole citation; the reader opens the repository's fill for it.
_SLOT_CITE = re.compile(r"[`<]slot:(?P<id>[a-z][a-z0-9-]*)(?P<tail>:[a-z][a-z0-9:-]*)?[`>]")


def slot_citations(text: str) -> list[tuple[str, str, int]]:
    """`(slot id, tail, line)` for every slot citation; a tail is a key the form no longer has."""
    out: list[tuple[str, str, int]] = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in _SLOT_CITE.finditer(line):
            out.append((m.group("id"), m.group("tail") or "", i))
    return out


def _shared_slugs(tier: Path | None) -> dict[str, Path]:
    """`slug → document` for every shared-tier file that declares one."""
    out: dict[str, Path] = {}
    for _, doc in _shared_docs(tier):
        m = _SLUG.search(doc.read_text(encoding="utf-8", errors="ignore")[:2000])
        if m:
            out[m.group(1)] = doc
    return out


def _rubric_specs(tier: Path | None) -> dict[str, str]:
    """`rubric id → spec` from spine.md's `critique_rubrics` block."""
    if tier is None:
        return {}
    spine = tier / "process" / "spine.md"
    if not spine.is_file():
        return {}
    import json

    for block in re.findall(r"```json\s*\n(.*?)\n```", spine.read_text(encoding="utf-8"), re.DOTALL):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        rubrics = data.get("critique_rubrics") if isinstance(data, dict) else None
        if isinstance(rubrics, dict):
            return {k: str(v.get("spec", "")) if isinstance(v, dict) else str(v) for k, v in rubrics.items()}
    return {}


def _heading_present(doc: Path, heading: str) -> bool:
    text = doc.read_text(encoding="utf-8", errors="ignore")
    want = heading.strip().lower()
    return any(want in h.lower() for h in _HEADING.findall(text))


def _resolve_spec(tier: Path, spec: str) -> str | None:
    """Why a rubric spec does not resolve, or None when it does.

    A spec is `<tier-relative path>[ §<heading>]`. The path may be written with or without
    the `.claude/` or `.fleet/` prefix the materialized tree carries (by layout), because the same string has to be
    true in the authoring tree and in every repo that receives it.
    """
    m = _SPEC.match(spec.strip())
    if not m:
        return "spec is empty"
    rel = m.group("path").strip()
    for prefix in (".claude/", ".fleet/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix) :]
            break
    doc = tier / rel
    if not doc.is_file():
        return f"`{rel}` is not a file the tier carries"
    heading = m.group("heading")
    if heading and not _heading_present(doc, heading):
        return f"`{rel}` has no heading matching `{heading.strip()}`"
    return None


@dataclass
class CommandContracts:
    """Every reference the tree makes, resolved against what the tree defines."""

    name: str = "command-contracts"
    title: str = "every slot, slug and spec a command names resolves"
    description: str = (
        "Requires every slot citation to name a question the questionnaire asks; resolves "
        "each spine's `sop` to a shared-tier slug and each critique rubric's `spec` to a file "
        "and heading the tier carries; and requires every shared-tier document to be the fill "
        "of exactly one shared slot."
    )

    def _commands_rel(self, kb: KnowledgeBase) -> str:
        return str(option(kb, "commands_dir", slotmod.default_commands_dir(kb.root)))

    def applies(self, kb: KnowledgeBase) -> bool:
        return (kb.root / self._commands_rel(kb)).is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:  # noqa: C901 — one rule per branch, flat by design
        commands_rel = self._commands_rel(kb)
        base = kb.root / commands_rel
        cmds = commandmod.read_commands(kb.root, commands_rel)
        tier = _tier_root(base, kb.root)
        out: list[Finding] = []
        if tier is None:
            return out

        questions = slotmod.read_questions()
        known = {s.id for s in questions.slots}
        slugs = _shared_slugs(tier)
        rubrics = _rubric_specs(tier)

        # Every document in the tier is read the same way: commands and shared docs alike.
        docs: list[tuple[str, Path]] = [(c.name, kb.root / c.path) for c in cmds]
        docs += [(f"{d}/{doc.name}", doc) for d, doc in _shared_docs(tier)]

        for label, path in docs:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for sid, tail, line in slot_citations(text):
                if sid not in known:
                    out.append(
                        Finding(
                            level="error",
                            message=f"`{label}` line {line}: cites `slot:{sid}`, which the questionnaire does not ask",
                            path=path,
                            hint="A slot id the questionnaire lacks is answered by no repository.",
                        )
                    )
                elif tail:
                    out.append(
                        Finding(
                            level="error",
                            message=f"`{label}` line {line}: cites `slot:{sid}{tail}` — a slot is cited whole",
                            path=path,
                            hint=(
                                "Drop the key: the reader opens the repository's fill for the slot. What a repo "
                                "RUNS is a `make` target, not a slot key."
                            ),
                        )
                    )

        # --- spine-level references -----------------------------------------------
        for c in cmds:
            if not c.has_spine:
                continue
            path = kb.root / c.path
            if c.sop != "none" and c.sop not in slugs:
                out.append(
                    Finding(
                        level="error",
                        message=f"`{c.name}`: spine `sop: {c.sop}` names no document the tier carries",
                        path=path,
                        hint=(
                            "`sop` is `none`, or the `slug:` of a shared-tier document. A repository's own SOP "
                            "is not the tier's to name."
                        ),
                    )
                )
            for step in c.steps:
                if step.critique and step.critique not in rubrics:
                    out.append(
                        Finding(
                            level="error",
                            message=(
                                f"`{c.name}` step `{step.id}`: critique `{step.critique}` is not a registered rubric"
                            ),
                            path=path,
                            hint="Register it in spine.md's `critique_rubrics` with a spec the tier carries.",
                        )
                    )

        for rid, spec in rubrics.items():
            why = _resolve_spec(tier, spec)
            if why:
                out.append(
                    Finding(
                        level="error",
                        message=f"critique rubric `{rid}`: spec `{spec}` — {why}",
                        path=tier / "process" / "spine.md",
                        hint="A rubric with no text is a gate that can only be faked. Write the spec or re-point it.",
                    )
                )

        # --- every shared document is the fill of exactly one shared slot ----------
        filled: dict[str, list[str]] = {}
        for s in questions.slots:
            if s.shared:
                for f in s.fill:
                    filled.setdefault(f.split("/", 1)[-1] if f.startswith(".claude/") else f, []).append(s.id)
        for d, doc in _shared_docs(tier):
            rel = f"{d}/{doc.relative_to(tier / d)}"
            owners = filled.get(rel, [])
            if len(owners) != 1:
                out.append(
                    Finding(
                        level="error",
                        message=(
                            f"shared tier `{rel}` is the fill of {len(owners)} shared slot(s) "
                            f"({', '.join(owners) or 'none'}) — it must be exactly one"
                        ),
                        path=doc,
                        hint=(
                            "A shared document with no slot row is loaded by nothing and graded by nothing; "
                            "add a `shared` row for it, or delete the file."
                        ),
                    )
                )
        return out


CHECKS = [CommandContracts()]

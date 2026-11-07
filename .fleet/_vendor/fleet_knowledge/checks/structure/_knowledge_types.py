"""Verify the knowledge-base file-type system.

A knowledge base's own type registry — `knowledge/FILE-TYPES.md` by default — is the
single source of truth: a JSON registry mapping each file type to a `home` glob set
(relative to the knowledge root), optional `exclude` globs, a `lifecycle`, and `required`
frontmatter fields. This verifier enforces:

  Coverage      — every file under the knowledge root matches EXACTLY ONE type. Zero
                  matches is a hard error (an untyped file must be typed or deleted);
                  two-or-more is a glob-ambiguity bug in the registry.
  Header ↔ home — every markdown file declares `type:` equal to the type its location
                  implies, and carries that type's `required` fields.
  Registry sane — the JSON parses; every type used on disk is defined.

`README.md` and `_TEMPLATE.md` are universal (always `readme` / `template`) and are
auto-excluded from every other type. Non-text assets (png/tsx/pdf/html) are typed by
folder and carry no header.

**The registry is DATA, not code — that is what makes this check portable.** Another
project defines its own vocabulary by editing its own `FILE-TYPES.md`; nothing here
knows a single type name. The file it reads must contain one fenced ```json block whose
object carries a `types` array, each entry shaped:

    {
      "type":      "spec",              # the id written as `type:` in frontmatter
      "home":      ["specs/*.md"],      # globs, relative to the knowledge root
      "exclude":   ["specs/draft/*"],   # optional globs subtracted from `home`
      "lifecycle": "durable",           # free-form; recorded, not enforced here
      "required":  ["type", "status"]   # frontmatter fields every such file carries
    }

Everything else about the file — prose, tables, the frontmatter it carries itself — is
ignored, so a project can explain its taxonomy around the block.

Stdlib only. Exit 1 on any violation.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from fleet_knowledge import authoring

from ._kit import Finding, KnowledgeBase, Reporter, local_kb, option, option_list

# Defaults — the values this repository already had. Every one is a config key.
DEFAULT_REGISTRY = "FILE-TYPES.md"
DEFAULT_HEADER_EXTS = (".md",)  # only markdown docs carry a type header; assets type by folder
DEFAULT_UNIVERSAL = {"readme": "**/README.md", "template": "**/_TEMPLATE.md"}


def read_hint(type_id: str) -> str:
    """Where to read what a file of `type_id` must be, so an agent that got it wrong is told."""
    page = authoring.page_for_type(type_id)
    return f" Read `{authoring.docs_path(page)}` (`read_doc {page}`) for what a `{type_id}` file holds."


class RegistryError(Exception):
    """The type registry is unreadable — a violation of the check, not a crash."""


def glob_files(knowledge: Path, pattern: str) -> set[Path]:
    """Glob `pattern` under the knowledge root, portably across Python versions.

    `Path.glob()` changed semantics in 3.13: a pattern ending in a bare `**` used
    to match directories ONLY, and now matches files too. Six homes in this repo's
    FILE-TYPES.md end that way (`work/reviews/**`, `artifacts/**`, `demos/*/**`,
    `specs/architecture/diagrams/**`, `work/drafts/**`, `**/mockups/**`), so on
    <=3.12 every file under them matched no type at all while the same tree
    passed on a 3.13+ dev machine — 522 phantom "matches NO file type" errors in
    CI against a locally-green checkout.

    Normalising a trailing `**` to `**/*` is equivalent on 3.13+ (the only thing
    dropped is the directory itself, and callers filter to files anyway) and
    restores the intended recursive-file meaning on older interpreters.
    """
    if pattern == "**" or pattern.endswith("/**"):
        pattern += "/*"
    return set(knowledge.glob(pattern))


def frontmatter_fields(path: Path) -> dict[str, str] | None:
    """Top-level scalar fields from a .md frontmatter block or a .yaml file. None if a
    .md has no frontmatter at all."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        if not text.startswith("---"):
            return None
        parts = text.split("---", 2)
        if len(parts) < 3:
            return None
        body = parts[1]
    else:  # .yaml / .yml — whole file is the mapping
        body = text
    out: dict[str, str] = {}
    for line in body.splitlines():
        m = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


class KnowledgeTypesValidator:
    """The ported `validate_knowledge_types` run, bound to one knowledge base."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb
        self.repo: Path = kb.root
        self.k: Path = kb.knowledge
        self.registry_name: str = option(kb, "file_types_registry", DEFAULT_REGISTRY)
        self.registry = self.k / self.registry_name
        self.header_exts = set(option_list(kb, "file_types_header_exts", DEFAULT_HEADER_EXTS))
        self.universal: dict[str, str] = dict(option(kb, "file_types_universal", DEFAULT_UNIVERSAL))
        self.report = Reporter(base=self.k)
        self.types_count = 0
        self.files_count = 0

    # -- registry -----------------------------------------------------------------
    def load_registry(self) -> list[dict[str, Any]]:
        text = self.registry.read_text(encoding="utf-8")
        m = re.search(r"```json\s*(.*?)```", text, re.S)
        if not m:
            raise RegistryError(f"{self.registry_name}: no ```json registry block found")
        types: list[dict[str, Any]] = json.loads(m.group(1))["types"]
        return types

    def gitignored(self, paths: list[Path]) -> set[Path]:
        """Return the subset of paths that .gitignore would exclude."""
        if not paths:
            return set()
        r = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            input="\n".join(str(p) for p in paths),
            capture_output=True,
            text=True,
            cwd=self.repo,
        )
        return {Path(line) for line in r.stdout.splitlines() if line}

    # -- the run ------------------------------------------------------------------
    def run(self) -> Reporter:
        types = self.load_registry()
        type_ids = {t["type"] for t in types}
        err = self.report.err

        # file -> set of matching type ids
        matches: dict[Path, set[str]] = {}
        empty_homes: list[str] = []
        for t in types:
            tid = t["type"]
            hit: set[Path] = set()
            for pat in t["home"]:
                hit |= glob_files(self.k, pat)
            for pat in t.get("exclude", []):
                hit -= glob_files(self.k, pat)
            # README/_TEMPLATE belong only to their universal types
            if tid not in self.universal:
                for pat in self.universal.values():
                    hit -= glob_files(self.k, pat)
            hit = {p for p in hit if p.is_file()}
            if not hit:
                empty_homes.append(tid)
            for p in hit:
                matches.setdefault(p, set()).add(tid)

        by_id = {t["type"]: t for t in types}
        all_files = sorted(p for p in self.k.rglob("*") if p.is_file())
        ignored = self.gitignored(all_files)
        for path in all_files:
            if path in ignored:
                continue
            ts = matches.get(path, set())
            if not ts:
                err(
                    path,
                    "matches NO file type — add a type to "
                    f"{self.registry_name} whose home covers it, or delete the file."
                    f" Every type and where it lives: `{authoring.docs_path(authoring.FALLBACK_PAGE)}`",
                    hint=f"Give the file a home: add or widen a `home` glob in {self.registry_name}.",
                )
                continue
            if len(ts) > 1:
                err(
                    path,
                    f"matches MULTIPLE types {sorted(ts)} — fix the overlapping "
                    f"home/exclude globs in {self.registry_name}",
                    hint=f"Narrow one type's `home`, or add an `exclude` in {self.registry_name}.",
                )
                continue
            tid = next(iter(ts))
            spec = by_id[tid]
            if path.suffix in self.header_exts:
                fields = frontmatter_fields(path)
                if fields is None:
                    err(
                        path,
                        f"missing frontmatter `type: {tid}` header.{read_hint(tid)}",
                        hint=f"Add a YAML frontmatter block opening with `type: {tid}`.",
                    )
                    continue
                declared = fields.get("type")
                if not declared:
                    err(
                        path,
                        f"missing `type:` header (location implies `{tid}`).{read_hint(tid)}",
                        hint=f"Add `type: {tid}` to the frontmatter.",
                    )
                elif declared not in type_ids:
                    err(
                        path,
                        f"`type: {declared}` is not a registered type",
                        hint=f"Use a type defined in {self.registry_name}, or register `{declared}` there.",
                    )
                elif declared != tid:
                    err(
                        path,
                        f"`type: {declared}` but location implies `{tid}` — header and placement disagree."
                        f"{read_hint(tid)}",
                        hint=f"Either set `type: {tid}` or move the file into `{declared}`'s home.",
                    )
                for req in spec.get("required", []):
                    if req == "type":
                        continue
                    if req not in fields:
                        err(
                            path,
                            f"type `{tid}` requires frontmatter field `{req}`.{read_hint(tid)}",
                            hint=f"Add `{req}:` to the frontmatter.",
                        )

        for tid in sorted(set(empty_homes)):
            self.report.raw_note(f"type `{tid}` currently matches no files (home reserved for future use)")

        self.types_count = len(types)
        self.files_count = len(all_files) - len(ignored)
        return self.report


# --------------------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------------------
class KnowledgeTypesCheck:
    name = "knowledge-types"
    title = "File types"
    description = (
        "Every file in the knowledge base matches exactly one type from the project's own type "
        "registry (FILE-TYPES.md by default), declares that type in its frontmatter, and carries the "
        "fields that type requires. Coverage is what makes the taxonomy real: an untyped file is one "
        "nothing indexes, nothing validates and no reader can place, and a file matching two types is "
        "a glob bug that silently changes which rules apply to it."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        name = str(option(kb, "file_types_registry", DEFAULT_REGISTRY))
        knowledge: Path = kb.knowledge
        return (knowledge / name).is_file()

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        validator = KnowledgeTypesValidator(kb)
        try:
            return validator.run().findings
        except RegistryError as exc:
            return [
                Finding(
                    level="error",
                    message=str(exc),
                    path=validator.registry,
                    hint="The registry needs one fenced ```json block holding a `types` array.",
                )
            ]


CHECK = KnowledgeTypesCheck()


# --------------------------------------------------------------------------------------
# Legacy entry point — byte-identical stdout and exit codes
# --------------------------------------------------------------------------------------
def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    kb = local_kb(root if root is not None else Path.cwd())
    validator = KnowledgeTypesValidator(kb)
    try:
        report = validator.run()
    except RegistryError as exc:
        raise SystemExit(str(exc)) from exc
    if report.notices:
        print("knowledge-types notes:")
        for n in report.notices:
            print(f"- {n}")
    if report.errors:
        print("knowledge file-type validation failed:")
        for e in report.errors:
            print(f"- {e}")
        return 1
    print(
        f"knowledge file-types OK — {validator.files_count} files, "
        f"all match exactly one of {validator.types_count} registered types"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))

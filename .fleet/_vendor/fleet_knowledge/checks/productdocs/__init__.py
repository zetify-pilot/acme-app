"""Fleet's own product docs follow their contract (`fleet check --only product-docs`).

The pages under `fleet_knowledge/productdocs/` are rendered by the web app as designed pages and
read by agents as markdown; `productdocs/README.md` is the contract both readers rely on, and
`docsmd.validate` is its teeth. This is where that validation GATES — in the `fleet check` the
repository's CI already runs (`make validate-knowledge`), not a job or step of its own — with the
three inputs only the docs' home repository can supply:

  * **the app's real route table**, so a `routes:` key, an `app:` link or a `::screen`/`::action`
    route names a page the app actually draws. Read off the shipped script
    (`fleet_service/api/static/app.js`): every kind `WORLD_OF` lights (the table four service tests
    already read as the app's complete route list), `settings:<id>` for each `SETTINGS_PANES` row and
    `system:<key>` for each `SYS_PARTS` row. The service enumerates its routes nowhere else; reading
    the script is reading the source of truth, and an empty parse is a FAILURE rather than a skip,
    because a route table that silently reads as empty would let every route through;
  * **the repository root**, so every `sources:` path a page claims to describe exists;
  * **the loop glossary's words** (`fleet_service/api/glossary.py`), so a `:term[…]` that is not in
    `terms.md` must be a word the app's own glossary defines. `fleet-knowledge` may not import the
    service (and runs under a bare `python3`), so the rows are read off the module's SOURCE: the
    first two arguments of every `_term(...)` call, expanded exactly as `api/docs._glossary_words`
    expands them. `tests/api/test_tools_docs.py` holds the two readings equal, so neither can drift.

**Applies only where the docs live** — a checkout carrying `productdocs/` in the package source,
which is Fleet's own repository. A customer's repository receives the pages as files under
`.fleet/docs/` (`commandsync`) and has none of the app source the route and source checks read,
so there the check SKIPS with that reason rather than failing over ground it does not have.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

from fleet_knowledge import docsmd
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.runner import Finding

__all__ = ["CHECKS", "ProductDocsCheck", "glossary_words", "route_keys"]

#: Where each input lives, relative to the repository root.
HOME: Final = "packages/fleet-knowledge/src/fleet_knowledge/productdocs"
APP_JS: Final = "packages/fleet-service/src/fleet_service/api/static/app.js"
GLOSSARY_PY: Final = "packages/fleet-service/src/fleet_service/api/glossary.py"

_WORLD_OF: Final = re.compile(r"const WORLD_OF = \{(.*?)\n\};", re.S)
_WORLD_ROW: Final = re.compile(r'([A-Za-z_]\w*):\s*"\w+"')
_SETTINGS: Final = re.compile(r"const SETTINGS_PANES = \[(.*?)\n\];", re.S)
_SYS_PARTS: Final = re.compile(r"const SYS_PARTS = \[(.*?)\n\];", re.S)
_ID_FIELD: Final = re.compile(r'\bid:\s*"([^"]+)"')
_KEY_FIELD: Final = re.compile(r'\bkey:\s*"([^"]+)"')
_COMMENT: Final = re.compile(r"/\*.*?\*/", re.S)
#: `path:line: message` or `path: message`, the shape `docsmd.validate` reports in.
_ERROR: Final = re.compile(r"^(?P<path>[^:\s]+\.md)(?::(?P<line>\d+))?: (?P<message>.*)$", re.S)


def route_keys(app_js: str) -> frozenset[str]:
    """Every route key a docs page may name, read off the app's script. Empty when nothing parsed."""
    keys: set[str] = set()
    table = _WORLD_OF.search(app_js)
    if table:
        keys |= set(_WORLD_ROW.findall(_COMMENT.sub("", table.group(1))))
    panes = _SETTINGS.search(app_js)
    if panes:
        keys |= {f"settings:{pane}" for pane in _ID_FIELD.findall(_COMMENT.sub("", panes.group(1)))}
    parts = _SYS_PARTS.search(app_js)
    if parts:
        keys |= {f"system:{part}" for part in _KEY_FIELD.findall(_COMMENT.sub("", parts.group(1)))}
    return frozenset(keys)


def glossary_words(source: str) -> frozenset[str]:
    """Every spelling of every loop-glossary row, lowercased — `api/docs._glossary_words`, read off source.

    A row's key, its key with spaces for hyphens, its on-screen name, and that name with and without
    its parenthesis (`Machine (box)` gives `machine (box)`, `machine` and `box`).
    """
    words: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_term"):
            continue
        named = [a.value.lower() for a in node.args[:2] if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if len(named) != 2:  # noqa: PLR2004 — a key and a name
            continue
        key, name = named
        spellings = {key, key.replace("-", " "), name}
        if "(" in name:
            spellings |= {name.split("(", 1)[0].strip(), name.split("(", 1)[1].rstrip(")").strip()}
        words |= {w for w in spellings if w}
    return frozenset(words)


class ProductDocsCheck:
    name = "product-docs"
    title = "Fleet's product docs follow their contract"
    description = (
        "Every page under fleet_knowledge/productdocs/ passes productdocs/README.md: its front matter, "
        "its blocks and their attributes, no raw HTML, the index against the files, every route against "
        "the app's real route table, every `sources:` path present, and every term defined."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return (kb.root / HOME).is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        home = kb.root / HOME
        inputs: list[Finding] = []
        keys = route_keys(_read(kb.root / APP_JS))
        if not keys:
            inputs.append(
                Finding(
                    level="error",
                    message=f"no route was read out of {APP_JS} (`WORLD_OF`, `SETTINGS_PANES`, `SYS_PARTS`)",
                    path=kb.root / APP_JS,
                    hint="the app's route table moved or changed shape; update `route_keys` in "
                    "fleet_knowledge/checks/productdocs to read it where it is now",
                )
            )
        words = glossary_words(_read(kb.root / GLOSSARY_PY))
        if not words:
            inputs.append(
                Finding(
                    level="error",
                    message=f"no loop-glossary row was read out of {GLOSSARY_PY} (`_term(key, name, …)`)",
                    path=kb.root / GLOSSARY_PY,
                    hint="the glossary moved or changed shape; update `glossary_words` in "
                    "fleet_knowledge/checks/productdocs to read it where it is now",
                )
            )
        if inputs:
            # FAIL CLOSED: validating against an empty route table or word list would report every
            # route and term as unknown, and burying the real cause under that noise helps nobody.
            return inputs
        errors = docsmd.validate(docsmd.load(home), words, route_keys=keys, repo_root=kb.root)
        return [_finding(home, error) for error in errors]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _finding(home: Path, error: str) -> Finding:
    m = _ERROR.match(error)
    hint = "the contract is productdocs/README.md; fix the page, or change the contract and its parser together"
    if m is None:
        return Finding(level="error", message=error, path=home, hint=hint)
    return Finding(
        level="error",
        message=m.group("message"),
        path=home / m.group("path"),
        line=int(m.group("line")) if m.group("line") else None,
        hint=hint,
    )


CHECKS = [ProductDocsCheck()]

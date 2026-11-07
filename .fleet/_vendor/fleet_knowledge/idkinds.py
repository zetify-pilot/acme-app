"""The id kinds a knowledge base writes: one place both the customer-render scanner and the docs read.

An id is a prefix of capitals, a dash and a number (`SL-250`, `REQ-004`), or a PRD number
(`PRD 0502`). Which prefixes are ids is product vocabulary, gathered here from where the product
already defines each kind, never retyped by a reader:

  * the id namespaces `Config` defaults to (`program_prefix`, `slice_prefix`,
    `capability_prefix`, `todo_prefix`) and the prefixes no register may claim
    (`reserved_prefixes`);
  * the prefix every requirement register the scaffold ships declares in its front matter
    (`prefix: REQ`);
  * `HOME_PREFIXES`, the program, slice, capability and register prefixes of Fleet's own
    planning, which the customer-render scanner (`checks/slots/_render`) refuses in anything
    synced into a customer's repository. Fleet's own registers are not shipped, so they cannot
    be discovered from a customer's install. This tuple is the one copy.

STDLIB ONLY, LIKE `docsmd`, which reads it.
"""

from __future__ import annotations

import dataclasses
import re
from functools import cache
from pathlib import Path
from typing import Final

from fleet_knowledge.config import Config

__all__ = ["HOME_PREFIXES", "prefixes"]

#: Fleet's own planning and register prefixes (`_render._INTERNAL_ID` is built from these).
HOME_PREFIXES: Final = ("PG", "RUN", "SL", "CAP", "GOV", "FLT", "CRD", "BTR")

_ID_FIELDS: Final = ("program_prefix", "slice_prefix", "capability_prefix", "todo_prefix", "reserved_prefixes")
_SCAFFOLD_REGISTERS: Final = Path(__file__).resolve().parent / "templates" / "scaffold" / "knowledge" / "requirements"
_PREFIX_LINE: Final = re.compile(r"^prefix:\s*([A-Z]{2,5})\s*$", re.MULTILINE)


@cache
def prefixes() -> frozenset[str]:
    """Every prefix the product defines as an id kind: config defaults, scaffold registers, Fleet's own."""
    out: set[str] = set(HOME_PREFIXES)
    defaults = {f.name: f.default for f in dataclasses.fields(Config)}
    for name in _ID_FIELDS:
        value = defaults.get(name)
        out.update(value if isinstance(value, tuple) else (value,) if isinstance(value, str) else ())
    if _SCAFFOLD_REGISTERS.is_dir():
        for register in sorted(_SCAFFOLD_REGISTERS.glob("*.md")):
            out.update(_PREFIX_LINE.findall(register.read_text(encoding="utf-8")))
    return frozenset(p for p in out if p)

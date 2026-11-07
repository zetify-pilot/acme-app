"""Bind a slice's clause decomposition to the exact text of its `Done when` cell.

A slice's completion condition is one prose sentence in the slice register. When a PRD
decomposes that sentence into numbered clauses — the checkable parts a proof run has to
drive — the decomposition lives in the slice's detail file and carries a SHA-256 digest of
that cell's exact UTF-8 text. Editing the cell without re-blessing the digest fails here, so
the decomposition cannot silently drift from the completion condition it decomposes.

Format (documented for the next author):

  ## Clause decomposition (PRD 0123)
  ...
  <!-- done-cell-digest: sha256:<64 lowercase hex> -->
  | ID | Clause | Day-one state | Owner |
  |---|---|---|---|
  | SL123-C1 | ... | ... | ... |

**Every** slice detail file that carries that comment is bound, not only the one a project
happened to name in `clause_digest_slice`. The comment is a claim that the table below it is
pinned to the cell it decomposes; a comment nothing checks is worse than no comment, because
the next author trusts it. So the set this gate enforces is discovered from the corpus — each
detail file whose clause-decomposition section carries a digest — and `clause_digest_slice`
names only the one slice whose clause ids a project additionally holds to a required minimum.
A slice with no decomposition section at all is silent here (as a bar is in the `bars` check):
absence withholds nothing, and only a decomposition that EXISTS is held to its binding.

The configured clause ids are the required minimum. Extra rows are allowed; missing a
required id is a failure.

Ported from `scripts/validate_slice_clause_digest.py`. The failure wording and exit code are
unchanged; the OK line now counts the decompositions bound rather than naming the one slice.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import _registers
from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._digest import digest_of, extract_done_cell

NAME = "slice-clause-digest"

#: `digest_of` and `extract_done_cell` moved to `_digest` when the `## Bar` check began
#: binding to the same cell with the same digest — one implementation, or the two gates
#: would eventually disagree about which bytes were blessed. They stay reachable through
#: this module, which is where callers already name them, and `__all__` is what makes that
#: a re-export rather than an accident of the import (`--no-implicit-reexport`).
__all__ = [
    "NAME",
    "SliceClauseDigestCheck",
    "analyse",
    "cli",
    "digest_of",
    "extract_done_cell",
    "parse_decomposition",
    "validate",
]

#: Next H2 ends the section; H3 is allowed inside.
NEXT_H2_RE = re.compile(r"^##\s+", re.M)

#: The clause-decomposition heading, however its parenthetical is spelled. The configured
#: `clause_digest_heading` pins one project's exact heading; this matches any sibling so a
#: corpus that names the PRD per slice is not silently exempt. The section still ends at the
#: next H2, so a `## Bar` below is never read as part of the decomposition.
CLAUSE_HEADING_FALLBACK_RE = re.compile(r"^##\s+Clause decomposition\b.*$", re.M)


def _row_re(prefix: str) -> re.Pattern[str]:
    p = re.escape(prefix)
    return re.compile(rf"^\|\s*({p}\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|?\s*$")


def _row_prefix(cfg: PlanningConfig, slice_id: str) -> str:
    """The clause-id prefix for `slice_id`.

    The convention is the slice id with its dash removed, then `-C` (`SL-199` -> `SL199-C`),
    which is what the slice commands author and what a bar's criterion ids use. A project may
    name one slice explicitly and give it a different prefix; that override is honored rather
    than silently replaced by the derived form.
    """
    if slice_id == cfg.clause_digest_slice and cfg.clause_row_prefix:
        return cfg.clause_row_prefix
    return f"{slice_id.replace('-', '')}-C"


def _clause_section(detail_md: Path, cfg: PlanningConfig) -> str | None:
    """The clause-decomposition section's text, or None when the file carries no such section.

    The configured heading is tried first; a heading with a different parenthetical is a
    fallback so a corpus that names the PRD per slice is read rather than skipped. The next
    H2 ends the section, which is what keeps a `## Bar` (or any later section) out of it.
    """
    if not detail_md.is_file():
        return None
    text = detail_md.read_text(encoding="utf-8")
    m = re.search(cfg.clause_digest_heading, text, re.M) or CLAUSE_HEADING_FALLBACK_RE.search(text)
    if not m:
        return None
    rest = text[m.end() :]
    next_h2 = NEXT_H2_RE.search(rest)
    return rest[: next_h2.start()] if next_h2 else rest


def _has_digest(detail_md: Path, cfg: PlanningConfig) -> bool:
    """True when the file's clause-decomposition section carries a `done-cell-digest`."""
    section = _clause_section(detail_md, cfg)
    return section is not None and re.search(cfg.clause_digest_marker, section, re.IGNORECASE) is not None


def _bound_slice_ids(regs: _registers.Registers) -> list[str]:
    """Every slice detail file that carries a digest comment, by id, in a stable order.

    Keyed on the marker rather than on the register, because the marker is the claim being
    checked: a detail file for a slice the register does not know still asserts a binding and
    is still read (its missing row is then the finding). Files whose stem is not a well-formed
    slice id are skipped — a README or a baseline beside the details is not a slice.
    """
    directory = regs.slice_detail_dir
    if not directory.is_dir():
        return []
    id_re = regs.cfg.re_slice_id()
    out: list[str] = []
    for path in sorted(directory.glob("*.md")):
        if not id_re.match(path.stem):
            continue
        if path.stem == regs.cfg.clause_digest_slice:
            continue
        if _has_digest(path, regs.cfg):
            out.append(path.stem)
    return out


def _targets(regs: _registers.Registers) -> list[tuple[str, bool]]:
    """`(slice id, required-ids-enforced)` for every decomposition this gate binds.

    The configured slice comes first and is always checked — that is what lets a corpus whose
    one garden decomposition lost its section still fail. Then every other slice whose detail
    file carries a digest. Only the configured slice has a required-clause-id list; the rest
    are bound by the digest alone, which is the invariant the comment asserts.
    """
    cfg = regs.cfg
    out: list[tuple[str, bool]] = []
    seen: set[str] = set()
    if cfg.clause_digest_slice:
        out.append((cfg.clause_digest_slice, True))
        seen.add(cfg.clause_digest_slice)
    for slice_id in _bound_slice_ids(regs):
        if slice_id in seen:
            continue
        out.append((slice_id, False))
        seen.add(slice_id)
    return out


def parse_decomposition(
    detail_md: Path, cfg: PlanningConfig, row_prefix: str | None = None
) -> tuple[str | None, list[dict[str, str]]]:
    """Parse the clause-decomposition section.

    Returns `(stored_digest_hex_or_None, [{id, clause, day_one, owner}, ...])`. `row_prefix`
    defaults to the configured one, then to the prefix derived from the detail file's own slice
    id — the package names no slice, so a caller reading an iterated detail file gets that
    file's convention rather than another corpus's.
    """
    if not detail_md.is_file():
        raise FileNotFoundError(f"{detail_md} not found")
    section = _clause_section(detail_md, cfg)
    if section is None:
        raise ValueError(f"{detail_md}: missing `{cfg.clause_digest_heading_label}` section")

    dm = re.search(cfg.clause_digest_marker, section, re.IGNORECASE)
    stored = dm.group(1).lower() if dm else None

    prefix = row_prefix or cfg.clause_row_prefix or f"{detail_md.stem.replace('-', '')}-C"
    row_re = _row_re(prefix)
    clauses: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in section.splitlines():
        rm = row_re.match(line.strip())
        if not rm:
            continue
        cid = rm.group(1)
        if cid in seen:
            raise ValueError(f"{detail_md}: duplicate clause id {cid}")
        seen.add(cid)
        clauses.append(
            {
                "id": cid,
                "clause": rm.group(2).strip(),
                "day_one": rm.group(3).strip(),
                "owner": rm.group(4).strip(),
            }
        )
    return stored, clauses


def _slice_violations(regs: _registers.Registers, slice_id: str, *, require_ids: bool) -> list[str]:
    """Violations for one slice's clause decomposition, in the original wording."""
    cfg = regs.cfg
    slices_md = regs.slice_register
    detail_md = regs.slice_detail(slice_id)

    try:
        done = extract_done_cell(slices_md, slice_id, regs.slice_rows_dir)
    except (FileNotFoundError, ValueError) as e:
        return [str(e)]
    expected = digest_of(done)

    try:
        stored, clauses = parse_decomposition(detail_md, cfg, _row_prefix(cfg, slice_id))
    except (FileNotFoundError, ValueError) as e:
        return [str(e)]

    errors: list[str] = []
    if stored is None:
        errors.append(f"{detail_md}: no `<!-- done-cell-digest: sha256:... -->` in the clause decomposition section")
    elif stored != expected:
        errors.append(
            f"{detail_md}: done-cell digest mismatch — cell digest is sha256:{expected}, "
            f"stored is sha256:{stored}. Re-read the Done when cell in {slices_md} and "
            "re-bless the digest after updating the clause table."
        )

    if require_ids and cfg.clause_required_ids:
        present = {c["id"] for c in clauses}
        missing = [cid for cid in cfg.clause_required_ids if cid not in present]
        if missing:
            errors.append(
                f"{detail_md}: clause list missing required id(s): {', '.join(missing)} "
                f"(need at least {', '.join(cfg.clause_required_ids)})"
            )
        if not clauses and not missing:
            errors.append(f"{detail_md}: clause decomposition table has no data rows")
    elif not clauses:
        errors.append(f"{detail_md}: clause decomposition table has no data rows")

    return errors


def validate(kb: Any) -> list[str]:
    """Human-readable violations (empty == pass), in the original wording."""
    regs = _registers.of(kb)
    errors: list[str] = []
    for slice_id, require_ids in _targets(regs):
        errors.extend(_slice_violations(regs, slice_id, require_ids=require_ids))
    return errors


def analyse(kb: Any) -> Report:
    regs = _registers.of(kb)
    report = Report()
    for slice_id, require_ids in _targets(regs):
        detail_md = regs.slice_detail(slice_id)
        for message in _slice_violations(regs, slice_id, require_ids=require_ids):
            report.findings.append(
                finding(
                    ERROR,
                    message,
                    path=detail_md,
                    hint=_hint(message),
                )
            )
    return report


def _hint(message: str) -> str | None:
    if "digest mismatch" in message:
        return "Re-read the `Done when` cell, re-work the clause table against it, then re-bless the digest."
    if "no `<!-- done-cell-digest" in message:
        return "Add the digest comment inside the section so the decomposition is bound to the cell it decomposes."
    if "missing required id" in message:
        return "Every required clause is a part of the completion condition a proof run has to drive — add it."
    if "no data rows" in message:
        return "Decompose the completion condition into numbered clauses before claiming the section exists."
    return None


class SliceClauseDigestCheck:
    """Every clause decomposition carrying a digest stays bound to the `Done when` text it decomposes."""

    name = NAME
    title = "Slice clause digest"
    description = (
        "A slice's completion condition is one prose sentence, and when a proof PRD decomposes it into "
        "numbered clauses the two can drift apart silently — the sentence gets edited, the clause table does "
        "not, and the proof now checks a condition nobody agreed to. This check binds them with a SHA-256 "
        "digest of the cell's exact bytes: change the sentence without re-blessing the digest and the commit "
        "fails. It binds EVERY slice detail file that carries a digest comment rather than one configured "
        "slice, because a comment asserts a binding and one nothing checks is a comment the next author "
        "trusts. It also asserts every required clause id is present for the configured slice, so that "
        "decomposition cannot quietly shed the parts that are hardest to prove."
    )

    def applies(self, kb: Any) -> bool:
        cfg = PlanningConfig.of(kb)
        regs = _registers.of(kb)
        if cfg.clause_digest_slice and regs.slice_detail(cfg.clause_digest_slice).is_file():
            return True
        return bool(_bound_slice_ids(regs))

    def run(self, kb: Any) -> list[Any]:
        return analyse(kb).findings


CHECK = SliceClauseDigestCheck()


def cli(kb: Any) -> int:
    """Print the ported validator's failure wording and exit code; count what was bound."""
    cfg = PlanningConfig.of(kb)
    regs = _registers.of(kb)
    errors = validate(kb)
    if errors:
        print("validate_slice_clause_digest: FAILED")
        for e in errors:
            print(f"- {e}")
        return 1
    targets = _targets(regs)
    required = ""
    if cfg.clause_digest_slice and cfg.clause_required_ids:
        required = f", and all {len(cfg.clause_required_ids)} required clauses are present in {cfg.clause_digest_slice}"
    print(f"validate_slice_clause_digest: OK — done-cell digest matches in {len(targets)} decomposition(s){required}")
    return 0

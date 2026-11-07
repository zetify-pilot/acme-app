"""Cross-subtree knowledge-base hygiene — the checks no single register owns.

Each one guards a way a corpus rots without any file becoming individually wrong:

- **Audit lifecycle** — at most one record per (audit type, scope). A recurring audit
  programme keeps the latest run only; superseded runs must be deleted, or "when was
  this last swept" has several answers.
- **Audit coverage honesty** — a `status: complete` record whose own coverage matrix
  sums to fewer units than its headline claim is asserting a reconciliation instead of
  deriving one, which silently removes un-read ground from the next run's seed.
- **Transient self-destruct docs** — a doc declaring `delete_when_shipped: <prd>` must
  be deleted once that trigger fires, or "delete once X" handoff docs rot in place
  after their trigger has fired.
- **Spec-index completeness** — every spec is referenced from the specs index, so no
  spec is undiscoverable.
- **Single-source drift** — a fact with one defining home must be CITED elsewhere, never
  restated. Each pattern below is a known-drifted restatement found in two or more files
  saying different things.
- **Feature-coverage ledger** — every feature area has exactly one tiered, familied row,
  so the audit rotation can select it and a grouped scope cannot quietly run short.
- **Doc parity** — named invariants asserted against named documents. A target that goes
  missing is a LOUD error, never a silent skip: two such guards once ran permanently
  dead behind an `is_file()` test while the invariant drifted unnoticed.

Everything repo-specific here — which directories, which vocabularies, which documents
carry which invariant — is a config key. The doc-parity rules have NO default: they name one
project's documents, so a project declares its own.

Stdlib only. Exit 1 on any violation.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._kit import Finding, KnowledgeBase, Reporter, frontmatter, local_kb, option, option_list

# --------------------------------------------------------------------------------------
# Defaults — the values this repository already had. Every one is a config key.
# --------------------------------------------------------------------------------------
DEFAULT_AUDITS_DIR = "audits"
DEFAULT_ARCH_AUDITS_DIR = "audits/architecture"
DEFAULT_PRDS_DIR = "prds"
DEFAULT_SPECS_DIR = "specs"
DEFAULT_FEATURES_DIR = "features"
DEFAULT_SPECS_INDEX = "specs/README.md"
DEFAULT_COVERAGE_LEDGER = "audits/feature-coverage-ledger.md"
DEFAULT_TRANSIENT_FIELDS = ("delete_when_shipped", "delete_when")

# `YYYY-MM-DD-`, and also the rarer `YYYY-MM-` form. The day group is optional
# because a record named `2026-05-agent-quality-benchmark.md` otherwise parsed as
# "no date prefix" and was dropped from the uniqueness check entirely — a silent
# skip, not a reported one, so a duplicate scope on such a file would never fail.
# The day group is greedy-first, so `2026-08-15-observers` still yields the scope
# `observers` rather than `15-observers`.
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}(?:-\d{2})?[a-z]?-")

# A `status: complete` coverage-matrix row that sums to fewer packages than the
# record's own `Packages reviewed` claim is a **false-full-coverage** failure:
# the reconciliation is asserted independently instead of derived from the unit
# table, silently removing un-read ground from the next run's seed.
REVIEWED_ROW_RE = re.compile(r"\|?\s*Packages reviewed\s*\|\s*\*+\s*(\d+)\s*/\s*(\d+)")
AUDITED_ROW_RE = re.compile(r"audited\s*\(\s*(\d+)/")

# Single-source ratchet. Each fact below has exactly ONE defining home; every other file
# may cite the home but must not restate the value. These patterns are the known-drifted
# restatements — each was found in 2+ files saying different things (one consistency
# review counted 7 files carrying 3 variants of the branch convention). Deleting a
# pattern requires deleting the fact's owner too.
DEFAULT_DRIFT_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"<user>/(prd|fix|task)-",
        "old branch-name form — defined ONCE in tracking-and-execution.md → 'Git workflow'",
    ),
    (
        r"til-MMM",
        "stale 'til-' Linear key (now 'eng-') — cite tracking-and-execution.md, don't restate",
    ),
    (
        r"kind:\s*outcome\s*\|\s*area|`outcome \| area`",
        "retired kind enum — defined ONCE in tracking-and-execution.md → 'Two kinds of project'",
    ),
    (
        r"Connect / Assess / Prioritize",
        "retired core-loop labels — defined ONCE in product-vision.md → Core Loop",
    ),
)
# Scope: the always-on + normative docs where a stale restatement misleads an agent.
# Records (prds/NNNN, audits, retros, decisions) are history and exempt. Repo-relative.
DEFAULT_DRIFT_SCOPE = (
    "CLAUDE.md",
    ".claude/commands",
    ".fleet/commands",
    "knowledge/specs",
    "knowledge/features/README.md",
    "knowledge/slices/README.md",
    "knowledge/prds/README.md",
    "knowledge/programs/README.md",
    "knowledge/journeys/README.md",
)

# The closed `Tier` vocabulary of the feature-audit rotation. Kept as a closed set (not
# derived from the ledger's own prose) so a typo'd tier fails rather than silently
# becoming an unselectable area — the failure mode is invisible by construction: an area
# that is never picked produces no run, no record, and no complaint.
DEFAULT_FEATURE_TIERS = ("core", "rotation", "parked")
# The closed `Family` vocabulary — the PRODUCT grouping the ledger's own "Family" section
# defines. Kept closed for the same reason: a typo'd family is invisible by construction.
# It does not fail a scope — it silently DROPS the area from the family the owner meant,
# so the grouped run reports clean coverage of a smaller set.
DEFAULT_FEATURE_FAMILIES = (
    "agents",
    "connectors",
    "governance",
    "knowledge",
    "experience",
    "tenancy",
    "operations",
    "automation",
)
DEFAULT_FEATURE_FAMILY_MIN_MEMBERS = 2  # a family of one is a rename, not a grouping

# The ledger's data rows carry six cells (Area · Family · Tier · Last audited · Depth ·
# Notes). Matching on the first three PLUS the shape is what keeps the file's other
# tables — Tier vocabulary, Family vocabulary, Size, "Who writes what", all three-column —
# out of the parse: they have four pipes, a data row has six or more.
LEDGER_ROW_RE = re.compile(r"^\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|[^|\n]*\|[^|\n]*\|", re.M)
LEDGER_AREA_RE = re.compile(r"^`([a-z0-9-]+)`$")


@dataclass(frozen=True)
class DocParityRule:
    """One named invariant asserted against one named document.

    A hardcoded invariant target must never be a silent skip: two such guards were
    deleted along with their targets and both ran permanently dead behind an
    `if <path>.is_file()` test, so the invariant drifted unnoticed. A missing target is
    an error that forces the next reader to re-point or retire the invariant on the
    record.
    """

    path: str  # knowledge-relative
    fact: str  # named in the "target no longer exists" error
    message: str  # the violation text; `{line}` is filled for a `forbid_line` rule
    forbid: str | None = None  # a substring whose PRESENCE is the violation
    require: str | None = None  # a substring whose ABSENCE is the violation (case-insensitive)
    forbid_line: str | None = None  # a substring; the first offending line is reported, then stop
    allow_tokens: tuple[str, ...] = ()  # a line carrying one of these is not an offence
    skip_frontmatter: bool = False


# The doc-parity invariants a project asserts are its OWN facts about its OWN documents, so the
# package ships none: a corpus declares them as `[[fleet.structure.hygiene_doc_parity]]` tables
# in its `fleet.toml` (one per rule; the keys are `DocParityRule`'s fields), e.g.
#
#     [[fleet.structure.hygiene_doc_parity]]
#     path = "specs/architecture/components/access-profiles.md"
#     fact = "credential classes"
#     require = "credential classes"
#     message = "must contain 'credential classes'"
#
# Until 2026-10 three such rules — about three of one product corpus's documents — were the
# default here, and every other corpus failed them for files it never had.
DEFAULT_DOC_PARITY: tuple[DocParityRule, ...] = ()

#: A doc-parity rule as a TOML table needs its keys checked here, not at the point of use: a
#: misspelled `forbidd` would otherwise produce a rule that matches nothing and passes, which
#: is the shape of a guard that silently stopped guarding.
_DOC_PARITY_KEYS = frozenset(
    {"path", "fact", "message", "forbid", "require", "forbid_line", "allow_tokens", "skip_frontmatter"}
)
_DOC_PARITY_REQUIRED = ("path", "fact", "message")


def doc_parity_rules(value: Any) -> list[DocParityRule]:
    """`hygiene_doc_parity` as rules, whether it arrived as objects or as TOML tables.

    THE named blocker for a second corpus: these three rules are one repository's invariants,
    and a bare knowledge base failed three errors it had no way to switch off. Written as
    `hygiene_doc_parity = []` a project asserts none; written as a list of tables it asserts
    its own.
    """
    out: list[DocParityRule] = []
    for i, item in enumerate(value):
        if isinstance(item, DocParityRule):
            out.append(item)
            continue
        if not isinstance(item, Mapping):
            raise ValueError(f"hygiene_doc_parity[{i}] must be a table of rule fields, got {item!r}")
        unknown = sorted(set(item) - _DOC_PARITY_KEYS)
        if unknown:
            raise ValueError(
                f"hygiene_doc_parity[{i}]: unknown field(s) {', '.join(unknown)} — "
                f"known fields are {', '.join(sorted(_DOC_PARITY_KEYS))}"
            )
        missing = [k for k in _DOC_PARITY_REQUIRED if not item.get(k)]
        if missing:
            raise ValueError(
                f"hygiene_doc_parity[{i}]: missing required field(s) {', '.join(missing)} — "
                "a rule with no target, no name or no message cannot report anything"
            )
        spec = dict(item)
        spec["allow_tokens"] = tuple(str(t) for t in spec.get("allow_tokens", ()))
        spec["skip_frontmatter"] = bool(spec.get("skip_frontmatter", False))
        out.append(DocParityRule(**spec))
    return out


def scalar(fm: str, name: str) -> str | None:
    m = re.search(rf"^{name}:\s*(.+)$", fm, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else None


def _extract_prd_numbers(trig: str) -> list[str]:
    """All PRD numbers a trigger references, expanding an en-dash/hyphen range
    (`0286–0289` → 0286, 0287, 0288, 0289) so an "all shipped" condition spanning
    several PRDs is checked against every one of them, not just the first number
    the string happens to contain. A `YYYY-MM-DD` date embedded in the same
    trigger (e.g. `..., or 2027-06-30`) is stripped first so its year isn't
    mistaken for a bare PRD number."""
    without_dates = re.sub(r"\d{4}-\d{2}-\d{2}", "", trig)
    numbers: list[str] = []
    for a, b in re.findall(r"(\d{3,4})\s*[-–]\s*(\d{3,4})", without_dates):
        numbers.extend(str(n).zfill(4) for n in range(int(a), int(b) + 1))
    without_ranges = re.sub(r"\d{3,4}\s*[-–]\s*\d{3,4}", "", without_dates)
    numbers.extend(m.zfill(4) for m in re.findall(r"\d{3,4}", without_ranges))
    seen: set[str] = set()
    out: list[str] = []
    for n in numbers:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


class KnowledgeHygieneValidator:
    """The ported `validate_knowledge_hygiene` run, bound to one knowledge base."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb
        self.repo: Path = kb.root
        self.k: Path = kb.knowledge
        self.report = Reporter(base=self.repo)
        self.audits_dir: str = option(kb, "hygiene_audits_dir", DEFAULT_AUDITS_DIR)
        self.arch_audits_dir: str = option(kb, "hygiene_arch_audits_dir", DEFAULT_ARCH_AUDITS_DIR)
        self.prds_dir: str = option(kb, "prds_dir", DEFAULT_PRDS_DIR)
        self.specs_dir: str = option(kb, "specs_dir", DEFAULT_SPECS_DIR)
        self.features_dir: str = option(kb, "features_dir", DEFAULT_FEATURES_DIR)
        self.specs_index: str = option(kb, "hygiene_specs_index", DEFAULT_SPECS_INDEX)
        self.coverage_ledger: str = option(kb, "coverage_ledger", DEFAULT_COVERAGE_LEDGER)
        self.transient_fields = tuple(option_list(kb, "hygiene_transient_fields", DEFAULT_TRANSIENT_FIELDS))
        # A `delete_when: YYYY-MM-DD` trigger is the ONE place a ported check compares
        # against today's date. It emits no schedule of its own — it observes that a
        # date a human authored has passed — but it is switchable for a project that
        # wants no wall-clock read at all.
        self.date_triggers: bool = bool(option(kb, "hygiene_date_triggers", True))
        self.drift_patterns: list[tuple[str, str]] = [
            (str(rx), str(msg)) for rx, msg in option(kb, "hygiene_drift_patterns", DEFAULT_DRIFT_PATTERNS)
        ]
        self.drift_scope = option_list(kb, "hygiene_drift_scope", DEFAULT_DRIFT_SCOPE)
        self.feature_tiers = set(option_list(kb, "feature_tiers", DEFAULT_FEATURE_TIERS))
        self.feature_families = set(option_list(kb, "feature_families", DEFAULT_FEATURE_FAMILIES))
        self.family_min_members = int(option(kb, "feature_family_min_members", DEFAULT_FEATURE_FAMILY_MIN_MEMBERS))
        self.doc_parity: list[DocParityRule] = doc_parity_rules(option(kb, "hygiene_doc_parity", DEFAULT_DOC_PARITY))

    # -- helpers ------------------------------------------------------------------
    def err(self, path: Path, msg: str, **kw: Any) -> None:
        self.report.err(path, msg, **kw)

    def warn(self, path: Path, msg: str, **kw: Any) -> None:
        self.report.warn(path, msg, **kw)

    # -- audit lifecycle ----------------------------------------------------------
    def check_audit_scopes(self) -> None:
        base = self.k / self.audits_dir
        if not base.is_dir():
            return
        for typedir in sorted(p for p in base.iterdir() if p.is_dir()):
            by_scope: dict[str, list[Path]] = {}
            for f in sorted(typedir.glob("*.md")):
                if f.stem.startswith("_") or f.stem == "README":
                    continue
                scope = DATE_PREFIX_RE.sub("", f.stem)
                if scope == f.stem:  # no date prefix → not a dated run record
                    continue
                by_scope.setdefault(scope, []).append(f)
            for scope, files in by_scope.items():
                if len(files) > 1:
                    names = ", ".join(f.name for f in files)
                    self.err(
                        typedir,
                        f"{len(files)} records for scope `{scope}` ({names}) — the recurring "
                        "audit program keeps the latest run only; delete superseded records",
                        hint="Delete every superseded record for this scope, keeping the latest run only.",
                    )

    def check_audit_coverage(self) -> None:
        """Architecture audit records must derive their coverage reconciliation from
        the unit table, never assert it independently.

        A `status: complete` record whose coverage-matrix rows sum to fewer packages
        than its `Packages reviewed` claim is a false-full-coverage claim — the exact
        failure that silently removes un-audited ground from the next run's seed.
        `partial` records are honest residuals and are not flagged.

        A `status: complete` record must also claim its own full scope: a `Packages
        reviewed` row whose numerator is less than its own denominator (`19 / 21`) is
        a record admitting an unreviewed remainder in its own words — that is
        `status: partial` by definition, not `complete`. And when the matrix doesn't use
        the `audited (n/n)` count format at all, the claim can't be mechanically
        cross-checked against the unit table; that format is optional, so an unparseable
        matrix on a `status: complete` record is surfaced as a non-blocking warning
        rather than silently passing with no output at all.
        """
        base = self.k / self.arch_audits_dir
        if not base.is_dir():
            return
        for f in sorted(base.glob("*.md")):
            if f.stem == "README":
                continue
            text = f.read_text(encoding="utf-8")
            fm = frontmatter(text)
            if not fm or scalar(fm, "status") != "complete":
                continue
            m = REVIEWED_ROW_RE.search(text)
            if not m:
                continue
            claimed, total = int(m.group(1)), int(m.group(2))
            if claimed < total:
                self.err(
                    f,
                    f"status: complete but claims only {claimed}/{total} packages reviewed in its "
                    "own Part 1 count — a complete record cannot admit an unreviewed remainder "
                    "(use status: partial instead, or finish the scope) (ENG-6198)",
                    hint="Set `status: partial`, or finish the remaining units and update the count.",
                )
                continue
            counts = [int(n) for n in AUDITED_ROW_RE.findall(text)]
            if not counts:
                self.warn(
                    f,
                    f"status: complete claims {claimed}/{total} packages reviewed but its coverage "
                    "matrix doesn't use the `audited (n/n)` count format, so the claim can't be "
                    "mechanically reconciled against the unit table — see knowledge/audits/README.md "
                    "(ENG-6198)",
                    hint="Write each matrix row's verdict as `audited (n/n)` so the total is derivable.",
                )
                continue
            summed = sum(counts)
            if summed < claimed:
                self.err(
                    f,
                    f"claims {claimed} packages reviewed (status: complete) but its coverage "
                    f"matrix rows sum to {summed} — the reconciliation must be derived from the "
                    "unit table, not asserted independently (ENG-6168)",
                    hint="Derive the headline count from the matrix rows, or audit the missing units.",
                )

    # -- transient docs -----------------------------------------------------------
    def prd_status_map(self) -> dict[str, str]:
        out: dict[str, str] = {}
        base = self.k / self.prds_dir
        if not base.is_dir():
            return out
        for d in base.iterdir():
            f = d / "prd.md"
            if not f.is_file():
                continue
            fm = frontmatter(f.read_text(encoding="utf-8"))
            if fm and (num := scalar(fm, "prd")):
                out[re.sub(r"\D", "", num).zfill(4)] = scalar(fm, "status") or ""
        return out

    def _trigger_fired(self, trig: str, statuses: dict[str, str]) -> str | None:
        """Whether an expiry trigger has fired. Supports `shipped:NNNN` / bare `NNNN`
        (fires when that PRD is shipped — or, for a trigger listing several PRDs via a
        range like `0286–0289`, once ALL of them are shipped) and `YYYY-MM-DD` (fires
        once the author's own date has passed). `superseded`/other values are manual and
        never auto-fire."""
        if "shipped" in trig or re.fullmatch(r"\d{3,4}", trig.strip()):
            nums = _extract_prd_numbers(trig)
            if nums and all(statuses.get(n) == "shipped" for n in nums):
                label = nums[0] if len(nums) == 1 else "/".join(nums)
                verb = "is" if len(nums) == 1 else "are all"
                return f"PRD {label} {verb} shipped"
            return None
        dm = re.fullmatch(r"\s*(\d{4})-(\d{2})-(\d{2})\s*", trig)
        if dm and self.date_triggers:
            import datetime

            y, mo, d = (int(x) for x in dm.groups())
            if datetime.date(y, mo, d) < datetime.date.today():
                return f"date {dm.group(0).strip()} has passed"
        return None

    def check_transient_docs(self) -> None:
        statuses = self.prd_status_map()
        for f in sorted(self.k.rglob("*.md")):
            fm = frontmatter(f.read_text(encoding="utf-8"))
            if not fm:
                continue
            for fieldname in self.transient_fields:
                trig = scalar(fm, fieldname)
                if trig and (why := self._trigger_fired(trig, statuses)):
                    self.err(
                        f,
                        f"`{fieldname}: {trig}` has fired ({why}) — delete this transient doc",
                        hint="Delete the doc; its trigger has fired, which is what the field promised.",
                    )

    # -- spec index ---------------------------------------------------------------
    def check_specs_index(self) -> None:
        readme = self.k / self.specs_index
        if not readme.is_file():
            return
        text = readme.read_text(encoding="utf-8")
        for f in sorted((self.k / self.specs_dir).glob("*.md")):
            if f.name == readme.name and f.parent == readme.parent:
                continue
            if f.name not in text:
                self.err(
                    readme,
                    f"spec `{f.name}` is not referenced in {self.specs_index} — index is incomplete",
                    hint=f"Add a line linking `{f.name}` to the spec index.",
                )

    # -- doc parity ---------------------------------------------------------------
    def _doc_parity_target(self, path: Path, fact: str) -> str | None:
        if not path.is_file():
            self.err(
                path,
                f"doc-parity target no longer exists — re-point or retire this invariant ({fact})",
                hint="Point the rule at the document's new home, or retire the invariant on the record.",
            )
            return None
        return path.read_text(encoding="utf-8")

    def check_doc_parity(self) -> None:
        for rule in self.doc_parity:
            target = self.k / rule.path
            text = self._doc_parity_target(target, rule.fact)
            if text is None:
                continue
            if rule.forbid is not None and rule.forbid in text:
                self.err(target, rule.message)
                continue
            if rule.require is not None and rule.require.lower() not in text.lower():
                self.err(target, rule.message)
                continue
            if rule.forbid_line is not None:
                body = text.split("---", 2)[-1] if rule.skip_frontmatter else text
                for line in body.splitlines():
                    if rule.forbid_line in line and not any(x in line for x in rule.allow_tokens):
                        self.err(target, rule.message.format(line=line.strip()[:60]))
                        break

    # -- single source ------------------------------------------------------------
    def check_single_source(self) -> None:
        pats = [(re.compile(rx), msg) for rx, msg in self.drift_patterns]
        roots = [self.repo / s for s in self.drift_scope]
        files: list[Path] = []
        for r in roots:
            if r.is_file():
                files.append(r)
            elif r.is_dir():
                files.extend(sorted(r.rglob("*.md")))
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.splitlines(), 1):
                for rx, msg in pats:
                    if rx.search(line):
                        self.err(
                            f,
                            f"line {i}: {msg}",
                            line=i,
                            hint="Cite the fact's defining home instead of restating its value here.",
                        )

    # -- feature coverage ledger --------------------------------------------------
    def check_feature_coverage_ledger(self) -> None:
        """Every feature area has exactly one tiered, familied row in the coverage ledger.

        The rotation picks its next area from that ledger, so a map with no row is an area
        the rotation can never select and no coverage report will ever mention — it drops
        out of the audit program silently, which is precisely how 11 maps came to have
        never appeared in any coverage ledger at all. A row naming no map is the mirror
        failure: it reports coverage of ground that does not exist.

        `Tier` is authored by a human and never by a run, so an unknown value is an error
        (a run must not be able to invent a tier), while a blank one is a warning — a new
        area awaiting a human's ruling is a legitimate transient state, and it stays
        unselectable until someone rules on it.

        `Family` is the same authored column on the product axis, and it is stricter: a
        blank one is an ERROR, not a warning. An untiered area is merely never
        auto-selected — loud by omission, and reported every run. An unfamilied area is
        *silent*: it still sits in the table looking covered while every `family:<name>`
        scope that should have swept it quietly runs one area short and reports clean.
        Same reason the family sizes are enforced — a family holding one area is a rename,
        and grouping by it buys nothing the area's own name did not already.
        """
        ledger = self.k / self.coverage_ledger
        maps_dir = self.k / self.features_dir
        if not ledger.is_file() or not maps_dir.is_dir():
            return
        areas = {p.stem for p in maps_dir.glob("*.md") if p.stem != "README"}
        rows: dict[str, tuple[str, str]] = {}
        for c_area, c_family, c_tier in LEDGER_ROW_RE.findall(ledger.read_text(encoding="utf-8")):
            m = LEDGER_AREA_RE.match(c_area.strip())
            if not m:
                continue
            area = m.group(1)
            if area in rows:
                self.err(ledger, f"`{area}` has more than one row — one line per area, never a dated pile")
            rows[area] = (c_family.strip(), c_tier.strip())
        for area in sorted(areas - rows.keys()):
            self.err(
                ledger,
                f"feature area `{area}` has no row — the rotation can never select it, and it "
                "would vanish from coverage without anyone noticing; add a row, tier it, family it",
                hint=f"Add a `| `{area}` | <family> | <tier> | … |` row to the ledger.",
            )
        for area in sorted(rows.keys() - areas):
            self.err(
                ledger,
                f"row `{area}` names no {self.features_dir}/{area}.md — stale row, delete it",
                hint="Delete the row, or restore the feature map it names.",
            )
        members: dict[str, list[str]] = {}
        for area in sorted(rows.keys() & areas):
            family_cell, tier = rows[area]
            if not tier:
                self.warn(ledger, f"`{area}` is untiered — it will never be auto-selected until it is")
            elif tier not in self.feature_tiers:
                self.err(
                    ledger,
                    f"`{area}` has Tier `{tier}` — not in the closed vocabulary {sorted(self.feature_tiers)}",
                )
            fams = [x.strip() for x in family_cell.split(",") if x.strip()]
            if not fams:
                self.err(
                    ledger,
                    f"`{area}` names no Family — it drops silently out of every `family:<name>` scope "
                    f"while still looking covered here; pick from {sorted(self.feature_families)}",
                )
            for fam in fams:
                if fam not in self.feature_families:
                    self.err(
                        ledger,
                        f"`{area}` has Family `{fam}` — not in the closed vocabulary {sorted(self.feature_families)}",
                    )
                else:
                    members.setdefault(fam, []).append(area)
        for fam, held in sorted(members.items()):
            if len(held) < self.family_min_members:
                self.err(
                    ledger,
                    f"family `{fam}` holds {len(held)} area ({', '.join(held)}) — a family of fewer "
                    f"than {self.family_min_members} is a rename, not a grouping; either place "
                    "more areas in it or drop the word",
                )
        # A vocabulary word nothing uses is dead, not broken: it misleads a reader of the
        # closed set and answers `family:<name>` with an empty sweep, but it cannot shrink a
        # run that was actually dispatched. Visible, not blocking.
        for fam in sorted(self.feature_families - members.keys()):
            self.warn(ledger, f"family `{fam}` is in the closed vocabulary but holds no area — dead word")

    # -- the run ------------------------------------------------------------------
    def run(self) -> Reporter:
        self.check_single_source()
        self.check_audit_scopes()
        self.check_audit_coverage()
        self.check_feature_coverage_ledger()
        self.check_transient_docs()
        self.check_specs_index()
        self.check_doc_parity()
        return self.report


# --------------------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------------------
class KnowledgeHygieneCheck:
    name = "knowledge-hygiene"
    title = "Corpus hygiene"
    description = (
        "The cross-subtree rules no single register owns: one audit record per scope, an audit's "
        "coverage claim derived from its own unit table rather than asserted, a transient doc deleted "
        "once its trigger fires, a complete spec index, no restatement of a fact that has one defining "
        "home, and one tiered, familied ledger row per feature area. Each guards a way the corpus rots "
        "while every file in it stays individually valid."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        knowledge: Path = kb.knowledge
        return knowledge.is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        return KnowledgeHygieneValidator(kb).run().findings


CHECK = KnowledgeHygieneCheck()


# --------------------------------------------------------------------------------------
# Legacy entry point — byte-identical stdout and exit codes
# --------------------------------------------------------------------------------------
def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    report = KnowledgeHygieneValidator(local_kb(root if root is not None else Path.cwd())).run()
    if report.warnings:
        print("knowledge hygiene warnings (non-blocking — review before the next audit run):")
        for w in report.warnings:
            print(f"- {w}")
    if report.errors:
        print("knowledge hygiene validation failed:")
        for e in report.errors:
            print(f"- {e}")
        return 1
    print(
        "knowledge hygiene OK — audit scopes unique, no fired transient docs, "
        "specs index complete, doc-parity invariants hold"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))

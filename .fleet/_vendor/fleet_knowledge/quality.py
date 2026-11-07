"""Read the check-result files and the audit-profile slot's kinds (design D1, D4, D5, D6).

PRD 0774 makes every check leave one append-only JSON result per run under
``knowledge/audits/results/<kind>/<YYYY-MM-DD>-<scope-slug>-<HHMMSS>Z.json``. This module is
the ONE reader of that home — design D1 reads it **at sync, at the commit**, never in a
request path — and the slot-kinds reader design D6 names as 0775's own gap. It is pure and
stdlib-only: no YAML dependency, no clock, and no exception escapes a malformed file.

- ``read_results`` — the typed run rows and verdict rows the roll-up composes (D1, D5).
- ``read_kinds`` — the ``audit-profile`` slot's ``kinds:`` entries, including the optional
  ``areas:`` list that places a non-journey check (D4).
- ``read_scenarios`` — PRD 0887's scenario records (``knowledge/scenarios/<slug>.md``): the typed
  checks that span several things-under-test, which the desk draws as their own things and walks
  as the trace.

Defensive by construction: a file that fails to parse or is missing a required key is skipped
with no error (E12); ``verdicts: []`` is tolerated (E13); a kind with no slot entry still
yields rows (E14); and a path that escapes the results home is refused, never read (E27).

The pure roll-up appended below — ``quality_map`` and ``quality_drill`` (design D2-D5) — composes
the ``GET /api/quality`` payload from these rows and the served typed rows. It is pure and
stdlib-only: no I/O and no clock, so the two ``ran_at`` instants are carried as stated and the
age is derived at render. Its inputs and the exact shapes B4 must build are documented at the
definitions.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

from . import markdown as md
from . import quality_reviews
from .checks.commitments.options import CommitmentsConfig
from .checks.commitments.registers import line_is_cut

RESULTS_SUBDIR = "knowledge/audits/results"


def results_prefix(corpus_dir: str) -> str:
    """The repository-relative results folder a pull request's files must sit under.

    ``<corpus_dir>/audits/results/`` when the corpus dir is named, else the served home with a
    trailing slash so a path prefix test never matches a sibling folder (PRD 0994).
    """
    base = corpus_dir.strip().strip("/")
    if not base:
        return RESULTS_SUBDIR + "/"
    return f"{base}/audits/results/"


#: Where PRD 0887's scenario records live in the repository — one `scenario` file per named check
#: that spans several things-under-test. Read at sync beside the result files (see
#: :func:`read_scenarios`), never in a request path.
SCENARIOS_SUBDIR = "knowledge/scenarios"

# The eight keys 0774's commit-time shape check refuses a file for dropping. A file missing any
# of them is skipped rather than raised over: a bad file is a fact held against the commit, not
# a reason to fail the sync (design D1, edge E12).
_REQUIRED_RESULT_KEYS = (
    "schema_version",
    "kind",
    "target",
    "commit",
    "environment",
    "finished",
    "ran_at",
    "verdicts",
)

# The slot's `kinds:` block is a fenced `yaml` block; a line-by-line read (below) is both
# sufficient and unbreakable, matching `scripts/validate_check_results.py`'s parser.
_YAML_FENCE_RE = re.compile(r"^```ya?ml[ \t]*\n(.*?)^```", re.M | re.S)

# The scalar fields a kind entry carries, beside the optional `areas:` list.
_KIND_FIELDS = ("claim", "covers", "limit")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_safe_result_path(path: Path, root: Path, home: Path) -> bool:
    """True only for a regular file whose real path stays under the results home.

    The walk already found the path under the home, so what this refuses is the substitute
    that passes a lexical check: a symlink (or a path that resolves) out of the home, and any
    ``.``/``..``/empty segment in the repo-relative path (edge E27).
    """
    if path.is_symlink():
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    if not _is_under(resolved, home):
        return False
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    return not any(part in ("", ".", "..") for part in rel.parts)


def parse_result(text: str) -> dict[str, Any] | None:
    """The parsed eight-key result from its text, or None when it is unparseable or malformed.

    None is the one defensive answer: design D1's reader skips a bad file with no exception
    (E12). ``verdicts`` must be a list of objects so the caller can read each entry's fields
    without a second guard. One copy of the shape rules, shared by the file reader and the
    open-pull-request reader (PRD 0994).
    """
    try:
        raw = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    if not all(key in raw for key in _REQUIRED_RESULT_KEYS):
        return None
    verdicts = raw["verdicts"]
    if not isinstance(verdicts, list) or not all(isinstance(item, dict) for item in verdicts):
        return None
    return raw


def _read_result(path: Path) -> dict[str, Any] | None:
    """The parsed eight-key result at ``path``, or None when the file is unreadable or malformed."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return parse_result(text)


def result_rows(data: dict[str, Any], file: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The run row and verdict rows one parsed result file yields.

    ``file`` is the repo-relative POSIX path the rows carry. The shape rules live here once, so
    the file reader and the open-pull-request reader cannot disagree about them (PRD 0994).
    """
    base: dict[str, Any] = {
        "kind": data["kind"],
        "target": data["target"],
        "commit": data["commit"],
        "environment": data["environment"],
        "finished": data["finished"],
        "ran_at": data["ran_at"],
        "file": file,
    }
    base.update(_run_v2_fields(data))
    verdicts: list[dict[str, Any]] = []
    for item in data["verdicts"]:
        verdict = dict(base)
        verdict["id"] = item.get("id", "")
        verdict["verdict"] = item.get("verdict", "")
        verdict["reason"] = item.get("reason", "")
        verdict.update(_verdict_v2_fields(item))
        verdicts.append(verdict)
    return base, verdicts


def read_results(
    root: Path, review_authority: quality_reviews.Authority | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The result files under ``<root>/knowledge/audits/results`` as typed rows.

    Returns ``(runs, verdicts)``: one **run** row per readable file — ``kind``, ``target``,
    ``commit``, ``environment``, ``finished``, ``ran_at`` and ``file`` (the repo-relative POSIX
    path) — and one **verdict** row per ``verdicts[]`` entry, being the run fields plus ``id``,
    ``verdict`` and ``reason`` (absent reason → ``""``), plus the verifier's ``review`` (and
    ``oracle`` / ``not_counted`` where they apply) laid over by ``quality_reviews.overlay``.
    Rows are in sorted-file order.

    An absent home is ``([], [])``. A file that fails to parse, is not an object, is missing a
    required key, or carries a malformed ``verdicts`` list is skipped with no exception (E12);
    ``verdicts: []`` yields a run row and no verdict rows (E13); the kind is never resolved
    against a slot, so an unknown kind still yields rows (E14); and a path escaping the home is
    refused before it is read (E27).
    """
    runs: list[dict[str, Any]] = []
    verdicts: list[dict[str, Any]] = []
    home_dir = root / RESULTS_SUBDIR
    if not home_dir.is_dir():
        return runs, verdicts
    home = home_dir.resolve()
    for path in sorted(home_dir.rglob("*.json")):
        if not _is_safe_result_path(path, root, home):
            continue
        data = _read_result(path)
        if data is None:
            continue
        base, file_verdicts = result_rows(data, path.relative_to(root).as_posix())
        runs.append(base)
        verdicts.extend(file_verdicts)
    # THE VERIFIER'S READING (FLT-1213/1214): reviews are their own append-only records, never an
    # edit of the result file, so they are laid over the rows here — every row leaves with its
    # `review` and, for a scenario version with no approved oracle, its `not_counted`.
    # `review_authority` is what a signed record is checked against (BUG-1144): the server-side
    # secret and the run table. None — every caller that is not the desk's sync — verifies nothing.
    return runs, quality_reviews.overlay(root, verdicts, authority=review_authority)


def verifier_reading(root: Path, review_authority: quality_reviews.Authority | None = None) -> dict[str, Any]:
    """Everything the verifier recorded that the desk shows beside the verdict rows —
    `quality_reviews.reading(root)`, unchanged: ``disputed`` (the standing disputes), ``weak``
    (`{scenario: outcome}` — a planted bug that did not turn it red), ``planted`` (every latest
    planted outcome) and ``oracles`` (`[{scenario, version, state}]`). Empty lists and maps for a
    corpus with no review records."""
    return dict(quality_reviews.reading(root, authority=review_authority))


def _weak_set(inputs: dict[str, Any]) -> dict[str, Any]:
    weak = (inputs.get("verifier") or {}).get("weak")
    return weak if isinstance(weak, dict) else {}


# ─────────────────────── the schema-2 fields, read when present ───────────────────────
#
# A schema-2 result file names WHERE it ran (`environment_id`), WHICH RELEASE it ran against
# (`release`) and which version of a scenario it ran (`scenario_version`), and each verdict may
# carry the promise it proves, what was expected and observed, the platform evidence ids, the
# attempts, a failure cause, the tracker ticket a fail filed, the verifier's review and a `new`
# flag. The writer and its validator are a separate change; this reader takes the fields when they
# are there and never requires them,
# so a schema-1 file reads exactly as it did — and a schema-1 row carries NONE of these keys, so a
# corpus of schema-1 files keys its reading exactly as before.

#: The run-level fields a schema-2 file may carry, all scalar strings.
_RUN_V2_KEYS = ("environment_id", "release", "scenario_version")
#: The verdict-level scalar string fields.
_VERDICT_V2_TEXT = ("promise", "expected", "observed", "attempts", "cause", "ticket")
#: The closed vocabularies: an unknown word is dropped, never guessed at.
CAUSES = frozenset({"product", "agent", "environment", "inconclusive"})
REVIEW_STATES = frozenset({"verified", "unverified", "disputed"})


def _text_or_none(value: Any) -> str | None:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = str(value).strip()
        return text or None
    return None


def _run_v2_fields(data: dict[str, Any]) -> dict[str, Any]:
    """The schema-2 run fields this file carries, and `schema_version` when it is not 1."""
    out: dict[str, Any] = {}
    version = data.get("schema_version")
    if isinstance(version, int) and not isinstance(version, bool) and version != 1:
        out["schema_version"] = version
    for key in _RUN_V2_KEYS:
        text = _text_or_none(data.get(key))
        if text is not None:
            out[key] = text
    return out


def _verdict_v2_fields(item: dict[str, Any]) -> dict[str, Any]:
    """The schema-2 verdict fields this entry carries, each typed or dropped — never raised on."""
    out: dict[str, Any] = {}
    for key in _VERDICT_V2_TEXT:
        text = _text_or_none(item.get(key))
        if text is not None:
            out[key] = text
    if out.get("cause") not in CAUSES:
        out.pop("cause", None)
    evidence = item.get("evidence")
    if isinstance(evidence, dict):
        shaped: dict[str, Any] = {}
        for key in ("request_ids", "audit_ids"):
            raw = evidence.get(key)
            if isinstance(raw, list):
                ids = [t for t in (_text_or_none(x) for x in raw) if t is not None]
                if ids:
                    shaped[key] = ids
        snapshot = _text_or_none(evidence.get("snapshot"))
        if snapshot is not None:
            shaped["snapshot"] = snapshot
        out["evidence"] = shaped
    review = item.get("review")
    if isinstance(review, dict):
        state = _text_or_none(review.get("state"))
        if state in REVIEW_STATES:
            out["review"] = {"state": state, "at": _text_or_none(review.get("at")) or ""}
    if isinstance(item.get("new"), bool):
        out["new"] = item["new"]
    return out


def _parse_flow_list(value: str) -> list[str]:
    """A kind field value as a list: an inline ``[a, b]`` flow list, else one scalar item.

    ``areas:`` is the only list field, and an empty value is the block-list form (its items
    arrive on the 6-space lines that follow), so an empty value is an empty list.
    """
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [_unquote(part.strip()) for part in inner.split(",") if part.strip()]
    return [_unquote(value)]


def read_kinds(slot_text: str) -> dict[str, dict[str, Any]]:
    """The ``audit-profile`` slot's ``kinds:`` entries, parsed without a YAML dependency.

    Returns ``{kind_id: {"claim": str, "covers": str, "limit": str, "areas": list[str]}}``. The
    block's shape is fixed: the fence's first line is ``kinds:`` at indent 0, each kind key is a
    bare mapping at 2-space indent, and its fields sit at 4-space indent as ``key: scalar`` (or,
    for ``areas:``, an inline flow list or a 6-space ``- item`` block list). An absent ``areas:``
    is ``[]`` (E15). Values may carry a ``:``; only the first separates the name from the scalar.

    No fence, or no ``kinds:`` line in one, yields ``{}``. An unknown field is ignored, never
    raised on, so a slot authored for a newer reader degrades to the fields this one knows.
    """
    entries: dict[str, dict[str, Any]] = {}
    block: str | None = None
    for candidate in _YAML_FENCE_RE.findall(slot_text):
        if any(line.strip() == "kinds:" for line in candidate.splitlines()):
            block = candidate
            break
    if block is None:
        return entries

    current: dict[str, Any] | None = None
    in_areas = False
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.rstrip() == "kinds:":
            continue
        if raw.startswith("  ") and not raw.startswith("    "):
            key = raw.strip()
            if key.endswith(":"):
                key = key[:-1]
            current = {"claim": "", "covers": "", "limit": "", "areas": []}
            entries[key.strip()] = current
            in_areas = False
        elif raw.startswith("    ") and not raw.startswith("      "):
            name, sep, value = raw.strip().partition(":")
            if not sep or current is None:
                continue
            name = name.strip()
            if name == "areas":
                current["areas"] = _parse_flow_list(value.strip())
                in_areas = True
            else:
                in_areas = False
                if name in _KIND_FIELDS:
                    current[name] = _unquote(value.strip())
        elif raw.startswith("      ") and in_areas and current is not None:
            stripped = raw.strip()
            if stripped.startswith("- "):
                current["areas"].append(_unquote(stripped[2:].strip()))
            elif stripped == "-":
                current["areas"].append("")
    return entries


# ─────────────────────────── the scenario records (PRD 0887) ───────────────────────────
#
# A scenario is a first-class, named check that exercises several things-under-test together and
# asserts verdicts over the combination (PRD 0887, `knowledge/scenarios/<slug>.md`). It is a typed
# record whose `references:` names the things it exercises, whose `proves:` names the promises it
# proves, and whose body carries the assertions the run records as `<slug>#<n>` — the same
# criterion-id shape a journey uses. This reader is the Fleet side of the trace: it turns the
# records into served rows the Quality desk draws as their own things (not squares) and walks.

#: A scenario's own body row: a numbered list item (`1. …`) or a pipe-table row whose first cell
#: is the ordinal. Both spell the assertion the run names `<slug>#<n>`.
_SCENARIO_LIST_ROW_RE = re.compile(r"^(\d+)\.\s+(.*)$")
#: An assertion row's first cell: a bare ordinal (`1`) or the assertion's own name
#: (`procurement-flow#1`) — the scenario template writes the second, so both count.
_INT_CELL_RE = re.compile(r"^(?:[^\s|#]+#)?\d+$")
#: The H2 that holds a scenario's assertions; when a record has one, only its rows are assertions,
#: so a `## Steps` numbered list beside it is never read as one.
_ASSERTIONS_HEADING_RE = re.compile(r"^##\s+[^\n]*(?:[Aa]cceptance criteria|[Ee]xpected|[Aa]ssertions)\b[^\n]*$", re.M)
_H2_RE = re.compile(r"^##\s+([^\n]+)$", re.M)


def _section(body: str, name: str) -> str:
    """The text under the first H2 whose title starts with `name` (case-insensitive), or `""`."""
    for heading in _H2_RE.finditer(body):
        if heading.group(1).strip().lower().startswith(name):
            rest = body[heading.end() :]
            end = _H2_RE.search(rest)
            return rest[: end.start()] if end else rest
    return ""


def _assertion_bodies(body: str) -> list[str]:
    """The sections that hold assertions — every assertions H2's text, or the whole body."""
    found = list(_ASSERTIONS_HEADING_RE.finditer(body))
    if not found:
        return [body]
    out: list[str] = []
    for heading in found:
        rest = body[heading.end() :]
        end = _H2_RE.search(rest)
        out.append(rest[: end.start()] if end else rest)
    return out


def _scenario_assertions(slug: str, body: str) -> list[dict[str, str]]:
    """The assertions a scenario's body names, as ``[{"id": "<slug>#<n>", "text": …}]``.

    The ordinal is the assertion's position in the file, never a literal row number, exactly as
    PRD 0774 derives a journey criterion's name — so a result file's `<slug>#<n>` id resolves here
    as it was written. A table row whose first cell is an ordinal (`1` or `<slug>#1`) and a
    numbered list row both count, in file order; a file that names none yields ``[]``.

    A table whose header names a ``Promise`` column gives each assertion the one promise it
    proves (``promise``), and an ``Expected`` column its expected result (``expected``) — both
    optional, and absent keys when the table has no such column. When the record has an
    acceptance-criteria (or expected-results) H2, only its rows are assertions.
    """
    out: list[dict[str, str]] = []
    ordinal = 0
    for section in _assertion_bodies(body):
        columns: dict[str, int] = {}
        for raw in section.splitlines():
            line = raw.strip()
            if line.startswith("|"):
                cells = md.cells(line)
                if len(cells) >= 2 and _INT_CELL_RE.match(cells[0]):
                    ordinal += 1
                    text_at = columns.get("assertion", 1)
                    row = {
                        "id": f"{slug}#{ordinal}",
                        "text": md.plain(cells[text_at]) if text_at < len(cells) else "",
                    }
                    for key in ("promise", "expected"):
                        at = columns.get(key)
                        if at is not None and at < len(cells) and md.plain(cells[at]):
                            row[key] = md.plain(cells[at]).strip("`")
                    out.append(row)
                elif cells and not columns and not set(cells[0]) <= set("-: "):
                    columns = {md.plain(c).strip().lower(): i for i, c in enumerate(cells)}
                continue
            columns = {} if not line else columns
            listed = _SCENARIO_LIST_ROW_RE.match(line)
            if listed:
                ordinal += 1
                out.append({"id": f"{slug}#{ordinal}", "text": md.plain(listed.group(2))})
    return out


def _setup_pairs(body: str) -> list[list[str]]:
    """A `## Setup` section's `- key: value` bullets, as `[[key, value], …]` in file order."""
    out: list[list[str]] = []
    for raw in _section(body, "setup").splitlines():
        line = raw.strip()
        if not line.startswith(("- ", "* ")):
            continue
        key, sep, value = line[2:].partition(":")
        if sep and key.strip():
            out.append([md.plain(key.strip()), md.plain(value.strip()).strip("`")])
        elif line[2:].strip():
            out.append(["", md.plain(line[2:].strip())])
    return out


def _steps(body: str) -> list[str]:
    """A `## Steps` section's numbered list, in file order."""
    out: list[str] = []
    for raw in _section(body, "steps").splitlines():
        listed = _SCENARIO_LIST_ROW_RE.match(raw.strip())
        if listed:
            out.append(md.plain(listed.group(2)))
    return out


def _lede(body: str) -> str:
    """The first paragraph under the H1 — what the scenario exercises, in one breath."""
    after = re.split(r"^#\s+[^\n]+$", body, maxsplit=1, flags=re.M)
    text = after[1] if len(after) > 1 else body
    for para in re.split(r"\n\s*\n", text):
        stripped = para.strip()
        if stripped and not stripped.startswith(("#", "|", "-", "*", "`")):
            return md.plain(" ".join(stripped.split()))
    return ""


def read_scenarios(root: Path) -> list[dict[str, Any]]:
    """The scenario records under ``<root>/knowledge/scenarios`` as served rows.

    One row per readable `type: scenario` file — ``id`` (its frontmatter id, falling back to the
    filename stem), ``name`` (its H1, falling back to the id), ``references`` (the things-under-test
    it exercises), ``proves`` (the promises it proves), ``owning_prd``, the ``assertions`` its body
    names, and ``file`` (the repo-relative POSIX path). Rows are in sorted-file order.

    An absent home is ``[]``. `README.md` and `_`-prefixed drafts are not records (the same
    exclusion `feature maps` and journeys make); a file that is not a scenario, names no id, or
    escapes the home is skipped with no exception.
    """
    home_dir = root / SCENARIOS_SUBDIR
    if not home_dir.is_dir():
        return []
    home = home_dir.resolve()
    out: list[dict[str, Any]] = []
    for path in sorted(home_dir.rglob("*.md")):
        name = path.name
        if name.startswith("_") or name.lower() == "readme.md":
            continue
        if not _is_safe_result_path(path, root, home):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = md.frontmatter(text)
        if md.field(fm, "type") != "scenario":
            continue
        slug = md.field(fm, "id") or path.stem
        if not slug:
            continue
        body = md.strip_frontmatter(text)
        h1 = re.search(r"^#\s+([^\n]+)$", body, re.M)
        row: dict[str, Any] = {
            "id": slug,
            "name": (h1.group(1).strip() if h1 else slug),
            "references": md.listfield(fm, "references"),
            "proves": md.listfield(fm, "proves"),
            "owning_prd": md.field(fm, "owning_prd"),
            "assertions": _scenario_assertions(slug, body),
            "file": path.relative_to(root).as_posix(),
        }
        # The record's own prose, optional: what it exercises, its setup and its steps. Keys are
        # present only when the record writes them, so a record that writes none keys its
        # reading exactly as it did before.
        for key, value in (("summary", _lede(body)), ("setup", _setup_pairs(body)), ("steps", _steps(body))):
            if value:
                row[key] = value
        # A QUARANTINE IS AUTHORED ON THE RECORD (`quarantine_until:` + `quarantine_reason:`):
        # the one small store the desk reads it from. While it holds, the scenario's verdicts
        # count nowhere; the page shows the state and never writes it. A record that writes
        # EITHER field is a quarantine, kept here even when it is incomplete — the page can then
        # show what was written, and `checks/quality` refuses the record at merge time. An
        # incomplete quarantine is not silently dropped: only `quarantine_until` being readable
        # decides whether it holds (`quarantine_active`).
        until = md.field(fm, "quarantine_until")
        reason = md.field(fm, "quarantine_reason")
        if until or reason:
            row["quarantine"] = {"until": until, "reason": reason}
        # WHERE IT RUNS AND AS WHOM, as the record itself states it (FLT-1204, FLT-1209): the QA
        # plan reads `environment` to run the guard before a run starts and `roles` to refuse a
        # scenario needing a role the environment's logins lack. Present only when written.
        if md.field(fm, "environment"):
            row["environment"] = md.field(fm, "environment")
        # `version:` is an integer everywhere else — the result's `scenario_version`, the oracle
        # record's `version` — so the row carries it as one, or a comparison against either reads
        # `"2" != 2` and never matches. A value that is not a positive integer is kept as written,
        # so a malformed record shows what it says rather than losing the field.
        raw_version = md.field(fm, "version")
        if raw_version:
            row["version"] = int(raw_version) if raw_version.isdigit() and int(raw_version) > 0 else raw_version
        if md.listfield(fm, "roles"):
            row["roles"] = md.listfield(fm, "roles")
        out.append(row)
    return out


# ─────────────────────────── the environment records ───────────────────────────
#
# An environment record (`knowledge/environments/<id>.json`) says where the QA agent's checks run:
# what kind of place it is, which principals sign in there and with which grants, what a run may
# write and how it is cleaned up. It is read at sync beside the result files and SERVED, so the
# reader is also the redaction: a credential is only ever a secret-store reference (`sm://…`, or
# `fleet-secret://<label>` for a secret held in Fleet's own Secrets store), the
# served row carries that reference's NAME and nothing else, and a field that holds anything other
# than a reference where a credential belongs is withheld and flagged, never passed through.

ENVIRONMENTS_SUBDIR = "knowledge/environments"

#: The record's top-level fields the desk serves, in the order the page reads them.
_ENV_FIELDS = (
    "id",
    "kind",
    "harness",
    "base_url",
    "org",
    "production",
    "principals",
    "writes",
    "cleanup",
    "version_probe",
    "fixtures",
    "steps",
    # The two guard facts the QA plan reads before a run starts (FLT-1205): the desk's "pause all
    # runs here", and how many objects an earlier run left in a customer environment.
    "paused",
    "leftovers",
)
#: The words that make a key credential-bearing, matched on the key's OWN words rather than as a
#: substring: `secret_note` and `apiKey` split into `secret`/`note` and `api`/`key`, while `author`
#: and `keyboard` stay ordinary fields. `pwd`, `pass`, `auth`, `cookie`, `bearer` and `key` are the
#: common names the short list of long ones missed (ENG-21072).
_CREDENTIAL_WORDS = frozenset(
    {
        "apikey",
        "auth",
        "authentication",
        "authorization",
        "bearer",
        "cookie",
        "cookies",
        "credential",
        "credentials",
        "key",
        "keys",
        "login",
        "logins",
        "pass",
        "passphrase",
        "passwd",
        "password",
        "passwords",
        "private",
        "pwd",
        "secret",
        "secrets",
        "token",
        "tokens",
    }
)
_REF_PREFIX = "sm://"
#: A secret held in Fleet's own Secrets store, by its label (`fleet-secret://<label>`). The form a
#: Fleet customer writes, who has no external secret manager: the label is a repository secret
#: (`api/secrets` repository scope) that the QA run reads with the `fleet-secret` box tool.
FLEET_SECRET_PREFIX = "fleet-secret://"
_REF_PREFIXES = (_REF_PREFIX, FLEET_SECRET_PREFIX)


def _key_words(key: str) -> list[str]:
    """A key's own words: snake_case, kebab-case, dots and camelCase all split."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key)
    return [word.lower() for word in re.split(r"[^A-Za-z0-9]+", spaced) if word]


def is_credential_key(key: str) -> bool:
    """Whether a record key names a credential, at any depth (see `_CREDENTIAL_WORDS`)."""
    return any(word in _CREDENTIAL_WORDS for word in _key_words(key))


def _is_ref(value: str) -> bool:
    return value.startswith(_REF_PREFIXES)


def _ref_name(value: str) -> str:
    """`sm://store/name` or `fleet-secret://name` → `name`: the reference's own name, the one
    thing a page may show."""
    if value.startswith(FLEET_SECRET_PREFIX):
        return value[len(FLEET_SECRET_PREFIX) :]
    return value[len(_REF_PREFIX) :].rstrip("/").rsplit("/", 1)[-1]


def _env_value(key: str, value: Any, depth: int = 0) -> Any:
    """One record value, typed for the wire and redacted (see the section comment).

    A credential-shaped key (`password`, `login`, `token`, `pwd`, `key`, …) yields `{"ref": name}`
    for a `sm://` or `fleet-secret://` reference and `{"withheld": true}` for anything else; every
    other `sm://` string is also reduced to its name. Scalars pass as strings (booleans stay
    booleans), lists and objects recurse four levels deep, and anything deeper or stranger is
    dropped.
    """
    if depth > 4:
        return None
    if is_credential_key(key) and not isinstance(value, (dict, list)):
        if isinstance(value, str) and _is_ref(value):
            return {"ref": _ref_name(value)}
        return {"withheld": True}
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return {"ref": _ref_name(value)} if _is_ref(value) else value
    if isinstance(value, list):
        items = [_env_value(key, item, depth + 1) for item in value]
        return [item for item in items if item is not None]
    if isinstance(value, dict):
        shaped = {str(k): _env_value(str(k), v, depth + 1) for k, v in value.items()}
        return {k: v for k, v in shaped.items() if v is not None}
    return None


#: The credential-bearing shapes a step's `run` argv may not carry as a literal value. A step
#: names a `fleet-secret://` reference in `env`; a password written into an argument is a secret
#: in the corpus, where every reader would see it.
_URL_CREDENTIAL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://[^/\s@:]+:[^/\s@]+@")
_AUTHORIZATION_BEARER_RE = re.compile(r"\bauthorization\s*:\s*bearer\s+\S+", re.IGNORECASE)
_STEP_KEYS = frozenset({"run", "env"})


def _credential_in_token(token: str) -> str | None:
    """The credential a single argv token carries, or `None` when it carries none.

    Catches the two shapes that put a value inside one token: a URL with `user:pass@`, and a
    credential-shaped key followed by `=` and a non-empty value (`password=x`, `--api-key=x`).
    A bare flag (`--password`) carries no value, so it is not a credential here; the caller
    checks the token after it.
    """
    if _URL_CREDENTIAL_RE.search(token):
        return "url"
    if "=" in token:
        key, _, value = token.partition("=")
        if value.strip() and is_credential_key(key.strip().lstrip("-")):
            return key.strip().lstrip("-")
    return None


def _run_credentials(run: Sequence[str]) -> list[tuple[int, str]]:
    """Every credential value in a step's argv, as `(token index, credential name)`.

    Scanned token by token, never as one joined string: a credential flag is a flag only when a
    value follows it, and an ordinary path or word is never one. The `-H "Authorization: Bearer
    x"` shape is the header flag and its value, which is why the value token is not judged on its
    own.
    """
    found: list[tuple[int, str]] = []
    for index, token in enumerate(run):
        if _is_ref(token):
            continue
        key = _credential_in_token(token)
        if key is not None:
            found.append((index, key))
            continue
        if (
            token.startswith("-")
            and is_credential_key(token.lstrip("-"))
            and index + 1 < len(run)
            and (value := run[index + 1].strip())
            and not value.startswith("-")
            and not _is_ref(value)
        ):
            found.append((index + 1, token.lstrip("-")))
            continue
        if token in ("-H", "--header") and index + 1 < len(run) and _AUTHORIZATION_BEARER_RE.search(run[index + 1]):
            found.append((index + 1, token))
    return found


def _served_steps(value: Any) -> Any:
    """A record's `steps` object, redacted but whole.

    `_env_value` stops at depth three, which would drop the run and env of every step. This keeps
    the list and index shape: `steps` is an object of `start`, `seed` and `stop` lists, and a step
    is an object of `run` (a list of strings) and optional `env`. A reference in `env` is served as
    `{"ref": name}`; every other env value is served as written, because a step's env is not a
    credential by key (the record check catches a literal secret by the key's own name).
    """
    if not isinstance(value, dict):
        return _env_value("steps", value)
    served: dict[str, Any] = {}
    for list_name, steps in value.items():
        if not isinstance(steps, list):
            shaped = _env_value(str(list_name), steps)
            if shaped is not None:
                served[str(list_name)] = shaped
            continue
        served_steps: list[Any] = []
        for step in steps:
            if not isinstance(step, dict):
                shaped_step = _env_value("step", step)
                if shaped_step is not None:
                    served_steps.append(shaped_step)
                continue
            shaped_step = {}
            for key, item in step.items():
                if key == "run" and isinstance(item, list):
                    shaped_step["run"] = [
                        token if isinstance(token, str) else _env_value("run", token) for token in item
                    ]
                elif key == "env" and isinstance(item, dict):
                    shaped_step["env"] = {
                        str(env_key): (
                            {"ref": _ref_name(env_value)}
                            if isinstance(env_value, str) and _is_ref(env_value)
                            else env_value
                        )
                        for env_key, env_value in item.items()
                    }
                else:
                    shaped = _env_value(str(key), item)
                    if shaped is not None:
                        shaped_step[str(key)] = shaped
            served_steps.append(shaped_step)
        served[list_name] = served_steps
    return served


def _step_findings(record: Mapping[str, Any]) -> list[tuple[str, bool]]:
    """Every problem with a record's `steps`, and whether it is a credential problem.

    The bool is what :func:`read_environments` needs: a `steps` object with a credential in a
    `run` is withheld whole, while a structural problem is still served redacted so the desk can
    show the record and its finding together.
    """
    if "steps" not in record:
        return []
    steps = record["steps"]
    if not isinstance(steps, Mapping):
        return [("`steps` must be an object with `start`, `seed` and `stop` lists", False)]
    findings: list[tuple[str, bool]] = []
    for name in ("start", "stop"):
        if name not in steps:
            findings.append((f"`steps.{name}` is missing; a copy needs at least one {name} step", False))
            continue
        value = steps[name]
        if not isinstance(value, list):
            findings.append((f"`steps.{name}` must be a list of steps", False))
        elif not value:
            findings.append((f"`steps.{name}` is empty; a copy needs at least one {name} step", False))
    if "seed" in steps and not isinstance(steps["seed"], list):
        findings.append(("`steps.seed` must be a list of steps", False))
    for list_name in ("start", "seed", "stop"):
        items = steps.get(list_name)
        if not isinstance(items, list):
            continue
        for index, step in enumerate(items):
            where = f"steps.{list_name}[{index}]"
            if not isinstance(step, Mapping):
                findings.append((f"{where} is not an object; a step holds `run` and optional `env`", False))
                continue
            unknown = sorted(str(key) for key in step if key not in _STEP_KEYS)
            if unknown:
                findings.append(
                    (f"{where} names unknown key(s) {', '.join(unknown)}; a step holds only `run` and `env`", False)
                )
            if "run" not in step:
                findings.append((f"{where} has no `run`", False))
            else:
                run = step["run"]
                if not isinstance(run, list) or not run or not all(isinstance(token, str) and token for token in run):
                    findings.append((f"{where}.run must be a non-empty list of strings", False))
                else:
                    for token_index, _name in _run_credentials(run):
                        findings.append(
                            (
                                f"{where}.run[{token_index}] holds a credential value; a step names a "
                                "`fleet-secret://` reference instead",
                                True,
                            )
                        )
            if "env" in step:
                env = step["env"]
                if not isinstance(env, Mapping):
                    findings.append((f"{where}.env must be an object of names to values", False))
                else:
                    for env_key, env_value in env.items():
                        if isinstance(env_value, str) and env_value.startswith(_REF_PREFIX):
                            findings.append(
                                (
                                    f"{where}.env.{env_key} uses an `sm://` reference; a step's env takes "
                                    "`fleet-secret://` only",
                                    False,
                                )
                            )
    if not _text_or_none(record.get("version_probe")):
        findings.append(("a record with `steps` must name a `version_probe`", False))
    return findings


def step_problems(record: Mapping[str, Any]) -> list[str]:
    """One sentence per problem with a record's `steps` object, or `[]` when it has none.

    A record with no `steps` key has no problem (AC-7). A record with steps must name `start` and
    `stop` (at least one step each; `seed` may be empty or absent), every step must be an object
    with a non-empty list of string `run` tokens and only the optional `env` beside it, an env
    value may be a `fleet-secret://` reference but never an `sm://` one (the daemon has no `sm://`
    resolver), no `run` token may carry a credential value, and the record must name a
    `version_probe` (without one no result there can count).
    """
    return [sentence for sentence, _credential in _step_findings(record)]


def read_environments(root: Path) -> list[dict[str, Any]]:
    """The environment records under ``<root>/knowledge/environments``, redacted for serving.

    One row per readable ``*.json`` object that names an ``id`` — the fields in ``_ENV_FIELDS``
    that it writes, through :func:`_env_value`, plus ``file``. An absent home is ``[]``; a file
    that fails to parse, is not an object, names no id or escapes the home is skipped with no
    exception. Rows are in sorted-file order.
    """
    home_dir = root / ENVIRONMENTS_SUBDIR
    if not home_dir.is_dir():
        return []
    home = home_dir.resolve()
    out: list[dict[str, Any]] = []
    for path in sorted(home_dir.rglob("*.json")):
        if not _is_safe_result_path(path, root, home):
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(raw, dict) or not _text_or_none(raw.get("id")):
            continue
        row: dict[str, Any] = {}
        for key in _ENV_FIELDS:
            if key not in raw:
                continue
            if key == "steps":
                # A credential in a step's argv is not served at all; every other problem is
                # still served redacted, so the desk can show the record and its finding together.
                if any(credential for _sentence, credential in _step_findings(raw)):
                    continue
                value = _served_steps(raw[key])
            else:
                value = _env_value(key, raw[key])
            if value is not None:
                row[key] = value
        row["id"] = str(raw["id"]).strip()
        row["file"] = path.relative_to(root).as_posix()
        out.append(row)
    return out


def read_environment_records(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    """The environment records as written, as `(path, object)`, for the record check.

    The same home and the same path safety as :func:`read_environments`, but no serving redaction:
    the check needs the record's own `steps`, `production` and `version_probe`. A file that fails
    to parse, is not an object or escapes the home is skipped with no exception.
    """
    home_dir = root / ENVIRONMENTS_SUBDIR
    if not home_dir.is_dir():
        return []
    home = home_dir.resolve()
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(home_dir.rglob("*.json")):
        if not _is_safe_result_path(path, root, home):
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(raw, dict):
            out.append((path, raw))
    return out


def _step_run_secrets(steps: Mapping[str, Any], where: str) -> list[tuple[str, str]]:
    """Every credential value written in a step's `run`, as `(step token path, credential name)`."""
    found: list[tuple[str, str]] = []
    for list_name, items in steps.items():
        if not isinstance(items, list):
            continue
        for index, step in enumerate(items):
            if not isinstance(step, Mapping):
                continue
            run = step.get("run")
            if not isinstance(run, list) or not all(isinstance(token, str) for token in run):
                continue
            for token_index, name in _run_credentials(run):
                found.append((f"{where}.{list_name}[{index}].run[{token_index}]", name))
    return found


def _literal_secrets(key: str, value: Any, where: str, depth: int = 0) -> list[tuple[str, str]]:
    """Every literal credential in `value`, as `(key path, key name)`.

    A container is walked rather than judged: a `login` object's `pwd` is a credential and its
    `username` is not. A scalar under a credential-shaped key is a literal secret unless it is an
    `sm://` or `fleet-secret://` reference.
    """
    if depth > 8:
        return []
    if isinstance(value, dict):
        found: list[tuple[str, str]] = _step_run_secrets(value, where) if key == "steps" else []
        for child_key, child_value in value.items():
            child_where = f"{where}.{child_key}" if where else str(child_key)
            found.extend(_literal_secrets(str(child_key), child_value, child_where, depth + 1))
        return found
    if isinstance(value, list):
        found = []
        for index, item in enumerate(value):
            found.extend(_literal_secrets(key, item, f"{where}[{index}]", depth + 1))
        return found
    if value is None or not is_credential_key(key):
        return []
    if isinstance(value, str) and _is_ref(value):
        return []
    return [(where, key)]


def environment_secret_violations(root: Path) -> list[tuple[Path, str]]:
    """Every literal credential in an environment record, as `(file, key path)`.

    Walks the same home that :func:`read_environments` serves, over the record as written. The reader
    withholds such a value at serve time; this is the commit-time gate that refuses the record
    holding it. A file that fails to parse or is not an object is skipped exactly as the reader
    skips it.
    """
    home_dir = root / ENVIRONMENTS_SUBDIR
    if not home_dir.is_dir():
        return []
    home = home_dir.resolve()
    out: list[tuple[Path, str]] = []
    for path in sorted(home_dir.rglob("*.json")):
        if not _is_safe_result_path(path, root, home):
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            out.extend((path, where) for where, _name in _literal_secrets(str(key), value, str(key)))
    return out


# ─────────────────────── the environment's cross-tenant write check ───────────────────────
#
# FLT-1277: the desk shows each environment's safety as PROVEN, not asserted. One half is the
# repository's cross-tenant write check — the nightly run that tries to write into another org
# and must fail (DLV-036's half, reported here). It arrives through the one result channel the
# desk already reads: a check result of kind `cross-tenant` whose schema-2 `environment_id`
# names the environment it drove. The latest such run per environment is the proof the page
# shows; no run means the check has never been reported, which is its own honest state.

#: The result kind the cross-tenant write check writes. A kind is a free string in the result
#: channel (`read_results` never resolves it against a slot), so this is the one convention the
#: two halves share — and the page says "never run" rather than green until it is reported.
CROSS_TENANT_KIND = "cross-tenant"


def cross_tenant_checks(
    runs: Iterable[dict[str, Any]], verdicts: Iterable[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """The latest cross-tenant write check per environment, keyed by the environment id.

    `runs` and `verdicts` are `read_results`'s two returns. A run of kind `cross-tenant` that
    names an `environment_id` is that environment's check; the newest `ran_at` wins, and the
    verdicts are the ones written by that same run (`file` is the run's identity). The state is:

    * ``pass`` — the run finished and every verdict passed;
    * ``fail`` — the run finished and any verdict failed;
    * ``blocked`` — the run finished and any verdict was blocked (none failed);
    * ``unfinished`` — the run did not finish, or carries no verdict to prove anything.

    The row also carries the run's `at`, `file` and, for a fail or block, the first such
    verdict's `reason` as `detail`, so the page can say why in the check's own words. An
    environment with no such run is absent — the caller renders "never run", never a pass.
    """
    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for verdict in verdicts:
        by_file[str(verdict.get("file") or "")].append(verdict)

    latest: dict[str, dict[str, Any]] = {}
    for run in runs:
        if str(run.get("kind") or "") != CROSS_TENANT_KIND:
            continue
        environment_id = str(run.get("environment_id") or "").strip()
        if not environment_id:
            continue
        current = latest.get(environment_id)
        if current is None or str(run.get("ran_at") or "") > str(current.get("ran_at") or ""):
            latest[environment_id] = run

    out: dict[str, dict[str, Any]] = {}
    for environment_id, run in latest.items():
        rows = by_file.get(str(run.get("file") or ""), [])
        words = [str(row.get("verdict") or "") for row in rows]
        if run.get("finished") is not True:
            state = "unfinished"
        elif "fail" in words:
            state = "fail"
        elif "blocked" in words:
            state = "blocked"
        elif words and all(word == "pass" for word in words):
            state = "pass"
        else:
            state = "unfinished"
        detail = ""
        if state in ("fail", "blocked"):
            first = next(
                (row for row in rows if str(row.get("verdict") or "") == state),
                None,
            )
            if first is not None:
                detail = str(first.get("reason") or first.get("observed") or "")
        out[environment_id] = {
            "state": state,
            "at": str(run.get("ran_at") or ""),
            "file": str(run.get("file") or ""),
            "detail": detail,
        }
    return out


# ─────────────────────────── the pure roll-up (design D2, D3, D4, D5) ───────────────────────────
#
# Everything below is pure: no I/O, no clock, and no mutation of its inputs. The two exported
# entry points are what `fleet-service`'s read routes (B4) call after composing the stored result
# reading with the served typed rows and the slot kinds. The input shapes B4 must build are:
#
# runs:     list of run rows, exactly `read_results`'s first return:
#           {"kind": str, "target": str, "commit": str, "environment": "live" | "code-only",
#            "finished": bool, "ran_at": str (RFC3339 UTC, so lexical order is time order),
#            "file": str (repo-relative POSIX path)}.
# verdicts: list of verdict rows, `read_results`'s second return — the run fields plus
#           {"id": str, "verdict": str, "reason": str}. `id` is a journey criterion
#           ("<journey>#<n>") or a checklist item ("<kind>/<item>").
# areas:    [{"id": str, "name": str, "position": int, "kind": str,
#            "capabilities": [{"id": str, "name": str}]}], in render order; every capability id
#            is unique across areas. `kind` is the typed thing kind (PRD 0885): a feature area
#            reads `area`, and the derived component/connector/customer-system rows read their
#            own kind and carry an empty `capabilities` list.
# kinds:    {kind_id: {"claim": str, "covers": str, "limit": str, "areas": list[str]}},
#           `read_kinds`'s return plus the optional `areas:` list. Output columns are these keys.
#           An `areas:` entry is a thing id or a bare typed selector (`area`, `component`,
#           `connector`, `customer-system`); a KIND WITH NO `areas:` applies to every thing.
# coverage: {"criterion_capability": {criterion_id: capability_id},
#            "known_criteria": set[str]}. `criterion_capability` maps every criterion that cites
#           a capability; a RETIRED criterion may stay mapped so the drill can place it.
#           `known_criteria` is every criterion id the served journeys still carry, so a mapped
#           id absent from it is `retired`.
#
# The unit of depth on the map is the item: for an (area, kind) square a feature area's item set
# is its capabilities, while a typed thing with no capabilities is its own single item. A verdict
# is attributed by its criterion (journey kinds) or, for a checklist kind, by its `target` naming
# a capability (placed on that capability's area) or a typed thing (placed on the thing itself);
# the kind's `areas:` must name it, else the square is `not-applicable` (PRD 0885). A later shallow
# run never hides an older counted verdict: for each item the latest counted verdict is taken, so
# an item the later run did not reach keeps its older age. Only a finished, live run's verdicts
# count; a code-only or unfinished run never counts.

_GREEN = "green"
_FAILED = "failed"
_NOT_COVERED = "not-covered"
_CODE_ONLY = "code-only"
_UNFINISHED = "unfinished"
_NEVER_CHECKED = "never-checked"
_NOT_APPLICABLE = "not-applicable"

# The seven-value coverage vocabulary, in `quality_map`'s `state` field. The last two are the
# honest pair design D3's six never distinguished: `never-checked` is a square that COULD be
# checked and was not; `not-applicable` is a square the kind's `areas:` does not name at all
# (PRD 0885), so it never reads as untested work.
QUALITY_STATES = (_GREEN, _FAILED, _NOT_COVERED, _CODE_ONLY, _UNFINISHED, _NEVER_CHECKED, _NOT_APPLICABLE)

#: The typed selectors a kind's `areas:` list may name (PRD 0885). A bare selector means every
#: thing of that kind; the served rows carry their typed kind under `kind`, with a feature area
#: (product/substrate, or absent) reading as `area`.
_TYPED_KINDS = ("area", "component", "connector", "customer-system")

# The outcome counter's keys, and the verdict strings that map onto them.
_OUTCOME_KEYS = ("pass", "fail", "blocked", "not_applicable")
_OUTCOME_VERDICTS = {"pass": "pass", "fail": "fail", "blocked": "blocked", "not-applicable": "not_applicable"}


class _Placement(NamedTuple):
    """Where one verdict lands: its area/capability, or the `not_placed` bucket it falls into."""

    area: str | None
    capability: str | None
    bucket: str
    retired: bool


class _Index(NamedTuple):
    """The normalized lookup the roll-up reads — built once from the served typed rows."""

    cap_area: dict[str, str]
    cap_name: dict[str, str]
    area_caps: dict[str, list[str]]
    area_name: dict[str, str]
    area_pos: dict[str, int]
    crit_cap: dict[str, str]
    known: frozenset[str]
    kind_map: dict[str, dict[str, Any]]
    thing_kind: dict[str, str]


def _ran_key(row: dict[str, Any]) -> tuple[str, str, str]:
    """The deterministic recency key: `ran_at`, then the file path, then the item id.

    `ran_at` is RFC3339 UTC, so a string compare is a time compare; the extra components make
    two runs at one timestamp (or a re-run's rows) order the same way on every read.
    """
    return (str(row.get("ran_at") or ""), str(row.get("file") or ""), str(row.get("id") or ""))


def _is_counted(row: dict[str, Any]) -> bool:
    """True only for a verdict a finished, live run produced (design D3) that the verifier has
    not disputed and whose expected results are not awaiting approval (FLT-1213, FLT-1214)."""
    return (
        row.get("finished") is True and str(row.get("environment") or "") != "code-only" and quality_reviews.counts(row)
    )


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for row in rows:
        if best is None or _ran_key(row) > _ran_key(best):
            best = row
    return best


def _outcome_of(verdict_rows: list[dict[str, Any]]) -> tuple[dict[str, int], int]:
    """The four outcome counts over the given verdicts, plus the N/A-without-reason count."""
    outcome = dict.fromkeys(_OUTCOME_KEYS, 0)
    na_without_reason = 0
    for row in verdict_rows:
        verdict = str(row.get("verdict") or "")
        key = _OUTCOME_VERDICTS.get(verdict)
        if key is None:
            continue
        outcome[key] += 1
        if key == "not_applicable" and not str(row.get("reason") or "").strip():
            na_without_reason += 1
    return outcome, na_without_reason


def _state(
    latest_run: dict[str, Any] | None,
    counted: int,
    in_scope: int,
    outcome: dict[str, int],
    na_without_reason: int,
    applicable: bool = True,
) -> str:
    """The square's state: a coverage word, never an outcome word folded into it (D3).

    `not-applicable` comes first and outranks everything: a square the kind's `areas:` does not
    name is not untested work, so no run can move it (PRD 0885). Otherwise `code-only` and
    `unfinished` read off the LATEST associated run; `green` needs a finished live run, full depth
    and every in-scope item a pass or a not-applicable with a reason. A fail is `failed`; a depth
    gap, a blocked verdict or an N/A without a reason is `not-covered`.
    """
    if not applicable:
        return _NOT_APPLICABLE
    if latest_run is None:
        return _NEVER_CHECKED
    if str(latest_run.get("environment") or "") == "code-only" and counted == 0:
        return _CODE_ONLY
    if latest_run.get("finished") is not True:
        return _UNFINISHED
    if counted > 0:
        if outcome["fail"] > 0:
            return _FAILED
        if counted < in_scope or outcome["blocked"] > 0 or na_without_reason > 0:
            return _NOT_COVERED
        return _GREEN
    return _NOT_COVERED


def _build_index(
    areas: list[dict[str, Any]],
    kinds: dict[str, Any],
    coverage: dict[str, Any],
) -> _Index:
    cap_area: dict[str, str] = {}
    cap_name: dict[str, str] = {}
    area_caps: dict[str, list[str]] = {}
    area_name: dict[str, str] = {}
    area_pos: dict[str, int] = {}
    thing_kind: dict[str, str] = {}
    for area in areas:
        aid = str(area.get("id") or "")
        area_name[aid] = str(area.get("name") or "")
        position = area.get("position")
        area_pos[aid] = position if isinstance(position, int) else 0
        # The typed thing kind (PRD 0885). A served row that names one of the four typed selectors
        # keeps it; a feature area's own `kind` is `product`/`substrate` (or absent), which is not
        # a selector — its typed kind is `area`.
        raw_kind = str(area.get("kind") or "")
        thing_kind[aid] = raw_kind if raw_kind in _TYPED_KINDS else "area"
        caps: list[str] = []
        for cap in area.get("capabilities") or []:
            cid = str(cap.get("id") or "")
            caps.append(cid)
            cap_area[cid] = aid
            cap_name[cid] = str(cap.get("name") or "")
        area_caps[aid] = caps
    raw_crit = coverage.get("criterion_capability") or {}
    crit_cap = {str(cid): str(cap) for cid, cap in raw_crit.items()}
    raw_known = coverage.get("known_criteria") or ()
    known = frozenset(str(cid) for cid in raw_known)
    kind_map = {str(kind): entry for kind, entry in kinds.items()}
    return _Index(cap_area, cap_name, area_caps, area_name, area_pos, crit_cap, known, kind_map, thing_kind)


def _applies(entry: dict[str, Any], thing_id: str, idx: _Index) -> bool:
    """Whether a kind's `areas:` names a thing — by its id or by a bare typed selector (D4, 0885).

    **A change, not compatibility:** a kind that declares no `areas:` applies to EVERY thing
    (design *Configuration — the kinds declare their targets*; red-team finding #11) — before the
    typed set a kind with no `areas:` placed nothing, because every checklist target was a miss.
    """
    selectors = [str(x) for x in (entry.get("areas") or [])]
    if not selectors:
        return True
    if thing_id in selectors:
        return True
    return idx.thing_kind.get(thing_id, "") in selectors


def _target_tokens(target: str) -> list[str]:
    """The ids a run's ``target`` names: comma-separated, trimmed, empty parts dropped.

    PRD 0774 froze ``target`` as a scalar; a run that covers several things lists their ids in it
    (``"CAP-0001,CAP-0002"``), and a single id is the one-element case. A free-text scope (a legacy
    target, or a run that wrote prose the writer now refuses at the source) is one token that names
    no id and places nothing — the comma is the only separator, so such a target stays one miss and
    is never split into a pile of phantom ones.
    """
    return [part.strip() for part in target.split(",") if part.strip()]


def _place(verdict: dict[str, Any], idx: _Index) -> list[_Placement]:
    """Resolve one verdict to the (area, capability) placements it lands on, or a `not_placed` miss.

    A criterion mapped in `criterion_capability` places on its capability (and reads `retired`
    when absent from `known_criteria`); a criterion in `known_criteria` with no capability cites
    no capability and is a `criteria` miss. Anything else is a checklist item: its `target` lists
    the capability and/or typed-thing ids the run covered (comma-separated), and each id the kind's
    `areas:` names places — a capability on its area, a typed thing on the thing itself (design D4;
    PRD 0885's typed set). An id the kind does not cover is dropped, and a verdict that resolves to
    no id at all is a single `targets` miss. A kind with no slot entry can place no checklist target
    (E14).
    """
    vid = str(verdict.get("id") or "")
    mapped = idx.crit_cap.get(vid)
    if mapped is not None:
        retired = vid not in idx.known
        area = idx.cap_area.get(mapped)
        if area is None:
            return [_Placement(None, None, "criteria", retired)]
        return [_Placement(area, mapped, "", retired)]
    if vid in idx.known:
        return [_Placement(None, None, "criteria", False)]
    kind = str(verdict.get("kind") or "")
    entry = idx.kind_map.get(kind)
    if entry is None:
        return [_Placement(None, None, "targets", False)]
    placements: list[_Placement] = []
    seen: set[tuple[str, str]] = set()
    for token in _target_tokens(str(verdict.get("target") or "")):
        area = idx.cap_area.get(token)
        if area is not None:
            if _applies(entry, area, idx) and (area, token) not in seen:
                seen.add((area, token))
                placements.append(_Placement(area, token, "", False))
            continue
        if token in idx.thing_kind and _applies(entry, token, idx) and (token, token) not in seen:
            seen.add((token, token))
            placements.append(_Placement(token, token, "", False))
    if placements:
        return placements
    return [_Placement(None, None, "targets", False)]


def _kind_target_areas(run: dict[str, Any], idx: _Index) -> set[str]:
    """The things a verdict-less run's checklist `target` lands on, as a set of area ids.

    A run that wrote `verdicts: []` still associates with the squares it ran against when its
    target lists a capability the kind covers or a typed thing the kind's `areas:` names; a
    journey target (not a capability or a thing id) contributes nothing.
    """
    entry = idx.kind_map.get(str(run.get("kind") or ""))
    if entry is None:
        return set()
    out: set[str] = set()
    for token in _target_tokens(str(run.get("target") or "")):
        area = idx.cap_area.get(token)
        thing = area if area is not None else (token if token in idx.thing_kind else None)
        if thing is not None and _applies(entry, thing, idx):
            out.add(thing)
    return out


def quality_map(
    runs: list[dict[str, Any]],
    verdicts: list[dict[str, Any]],
    areas: list[dict[str, Any]],
    kinds: dict[str, Any],
    coverage: dict[str, Any],
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The ``GET /api/quality`` payload **minus** ``commit`` (the route adds that).

    One square per (area, kind), plus the columns, the ``not_placed`` counts and the totals. The
    payload is O(areas x kinds): it never grows with the number of runs (FLT-1050, AC-7). Depth,
    outcome and the two ``ran_at`` instants are carried apart, and the instants are returned as
    stated — no age string is rendered here (design D2, E20).

    `scenarios` is PRD 0887's typed records (``read_scenarios``'s return): each is drawn as its
    OWN thing on the desk, never a square, so a check that spans several parts reads as itself.
    Each scenario row carries its ``references`` (the things-under-test it exercises), its
    ``proves`` (the promises it proves) and its own depth/state over its assertions, computed from
    the scenario-kind result files exactly as a square is. Absent or empty, the list is ``[]``.

    See the module comment above for the exact input shapes. `squares` are ordered by area
    (position, then id) and then by kind id.
    """
    idx = _build_index(areas, kinds, coverage)
    not_placed = {"criteria": 0, "targets": 0}
    file_areas: dict[str, set[str]] = defaultdict(set)
    verdict_files: set[str] = set()
    latest_counted: dict[tuple[str, str], dict[str, Any]] = {}
    for verdict in verdicts:
        placements = _place(verdict, idx)
        file_key = str(verdict.get("file") or "")
        verdict_files.add(file_key)
        placed = False
        for placement in placements:
            if placement.area is None or placement.capability is None:
                continue
            placed = True
            file_areas[file_key].add(placement.area)
            if not placement.retired and _is_counted(verdict):
                item_key = (str(verdict.get("kind") or ""), placement.capability)
                current = latest_counted.get(item_key)
                if current is None or _ran_key(verdict) > _ran_key(current):
                    latest_counted[item_key] = verdict
        if not placed:
            bucket = next((p.bucket for p in placements if p.bucket), "")
            if bucket:
                not_placed[bucket] += 1

    area_order = sorted(idx.area_caps, key=lambda aid: (idx.area_pos.get(aid, 0), aid))
    kind_order = sorted(idx.kind_map)
    squares: list[dict[str, Any]] = []
    for area in area_order:
        caps = idx.area_caps[area]
        # A typed thing that is not a feature area has no capability rows; its single item is the
        # thing itself (PRD 0885), so a check whose target IS the thing reaches full depth.
        if not caps and idx.thing_kind.get(area) != "area":
            caps = [area]
        in_scope = len(caps)
        for kind in kind_order:
            applicable = _applies(idx.kind_map[kind], area, idx)
            counted_rows = [latest_counted[(kind, cap)] for cap in caps if (kind, cap) in latest_counted]
            counted = len(counted_rows)
            outcome, na_without_reason = _outcome_of(counted_rows)
            associated = [
                run
                for run in runs
                if str(run.get("kind") or "") == kind
                and (
                    area in file_areas.get(str(run.get("file") or ""), set())
                    or (str(run.get("file") or "") not in verdict_files and area in _kind_target_areas(run, idx))
                )
            ]
            latest_run = _latest(associated)
            ages = [str(row.get("ran_at") or "") for row in counted_rows]
            squares.append(
                {
                    "area": area,
                    "kind": kind,
                    "depth": {"counted": counted, "in_scope": in_scope},
                    "outcome": outcome,
                    "latest_run": str(latest_run.get("ran_at") or "") if latest_run else None,
                    "oldest_counted": min(ages) if ages else None,
                    "state": _state(latest_run, counted, in_scope, outcome, na_without_reason, applicable),
                }
            )

    to_look_at = sum(1 for square in squares if square["state"] not in (_GREEN, _NOT_APPLICABLE))
    never_checked = sum(1 for square in squares if square["state"] == _NEVER_CHECKED)
    full_checks = [
        str(square["latest_run"])
        for square in squares
        if square["depth"]["in_scope"] > 0
        and square["depth"]["counted"] == square["depth"]["in_scope"]
        and square["latest_run"] is not None
    ]
    return {
        "areas": [
            {
                "id": aid,
                "name": idx.area_name.get(aid, ""),
                "position": idx.area_pos.get(aid, 0),
                "kind": idx.thing_kind.get(aid, "area"),
            }
            for aid in area_order
        ],
        "kinds": [
            {
                "id": kind,
                "claim": str(idx.kind_map[kind].get("claim") or ""),
                "covers": str(idx.kind_map[kind].get("covers") or ""),
                "limit": str(idx.kind_map[kind].get("limit") or ""),
            }
            for kind in kind_order
        ],
        "squares": squares,
        "scenarios": _scenario_rows(runs, verdicts, scenarios or []),
        "not_placed": not_placed,
        "totals": {
            "areas": len(area_order),
            "kinds": len(kind_order),
            "to_look_at": to_look_at,
            "never_checked": never_checked,
            "oldest_full_check": min(full_checks) if full_checks else None,
        },
    }


def quality_drill(rows: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """The ``GET /api/quality/{level}/{id}`` payload **minus** ``commit``.

    ``rows`` carries the same inputs as :func:`quality_map`: ``runs``, ``verdicts``, ``areas``,
    ``kinds`` and ``coverage`` under those keys. ``node`` is ``{"level": "area" | "capability",
    "id": str}``.

    At ``level: area`` each row is a capability of that area — the same square shape as the map,
    over the capability's own live criteria (retired criteria are left out of depth, design D5):
    ``id``, ``name``, ``no_criteria``, ``depth``, ``outcome``, ``latest_run``, ``oldest_counted``,
    ``state``. A capability with no criterion at all reads ``no_criteria`` true (AC-6).

    At ``level: capability`` each row is a criterion that has a verdict: ``criterion``,
    ``verdict``, ``reason``, ``kind``, ``run`` (its ``ran_at``), ``commit``, ``file`` and
    ``retired`` (true when the id is no longer in ``known_criteria``). An unknown level, area or
    capability answers empty rows, never a raise.

    At ``level: scenario`` the payload is the TRACE's served walk for one scenario (PRD 0887,
    companion): ``promises`` (its ``proves:``), ``things`` (its ``references:``), ``results`` (its
    scenario-kind result files, each with its assertions) and ``findings`` (the FAIL assertions the
    run filed as tracker tickets, with the stable ``audit_key``) — so a reader follows a promise
    through the things a scenario exercises to its result and the finding it left. ``rows`` carries
    the scenario records under ``scenarios``.
    """
    runs: list[dict[str, Any]] = rows.get("runs") or []
    verdicts: list[dict[str, Any]] = rows.get("verdicts") or []
    scenarios: list[dict[str, Any]] = rows.get("scenarios") or []
    idx = _build_index(rows.get("areas") or [], rows.get("kinds") or {}, rows.get("coverage") or {})
    level = str(node.get("level") or "")
    node_id = str(node.get("id") or "")
    if level == "area" and node_id in idx.area_caps:
        return {
            "level": level,
            "id": node_id,
            "name": idx.area_name.get(node_id, ""),
            "rows": _area_rows(runs, verdicts, node_id, idx),
        }
    if level == "capability":
        return {
            "level": level,
            "id": node_id,
            "name": idx.cap_name.get(node_id, ""),
            "rows": _capability_rows(verdicts, node_id, idx),
        }
    if level == "scenario":
        return _scenario_trace(runs, verdicts, scenarios, node_id)
    return {"level": level, "id": node_id, "name": "", "rows": []}


#: `CAP-NNNN` is a capability promise; any other `PREFIX-NNN` is a register requirement; anything
#: else is a journey id (a flow/map slug). The two shapes the trace's promise node family has.
_CAP_ID_RE = re.compile(r"^CAP-\d+$")
#: A journey criterion's or a scenario assertion's id, `<slug>#<n>` — a row so named claims a
#: promise by its own name, so one that resolves to nothing is unplaced, never silently dropped.
_ROW_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*#[1-9]\d*$")
_REQUIREMENT_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")


def _promise_kind(promise_id: str) -> str:
    """The node family a `proves:` entry names: ``capability``, ``requirement`` or ``journey``."""
    if _CAP_ID_RE.match(promise_id):
        return "capability"
    if _REQUIREMENT_ID_RE.match(promise_id):
        return "requirement"
    return "journey"


def _thing_of(reference: str) -> dict[str, str]:
    """A `references:` entry as its ``{kind, id}`` — `connector:sap` splits at the first colon.

    A reference that names no kind reads ``thing`` and keeps the whole string as its id, so an
    entry in a form this reader does not know is still shown, never dropped.
    """
    kind, sep, rest = reference.partition(":")
    if sep and kind and rest:
        return {"kind": kind, "id": rest}
    return {"kind": "thing", "id": reference}


def _scenario_files(
    runs: list[dict[str, Any]], verdicts: list[dict[str, Any]], scenario_id: str
) -> list[dict[str, Any]]:
    """The scenario-kind runs whose ``target`` is `scenario_id`, newest first.

    The result-file contract names the scenario in ``target``; its verdict ids are the scenario's
    own assertions. A run that wrote no verdicts still appears (an unfinished run is a fact about
    the scenario).
    """
    by_file: dict[str, dict[str, Any]] = {}
    for run in runs:
        if str(run.get("kind") or "") != "scenario" or str(run.get("target") or "") != scenario_id:
            continue
        by_file[str(run.get("file") or "")] = {
            "file": str(run.get("file") or ""),
            "commit": str(run.get("commit") or ""),
            "ran_at": str(run.get("ran_at") or ""),
            "environment": str(run.get("environment") or ""),
            "finished": run.get("finished") is True,
            "verdicts": [],
        }
    for verdict in verdicts:
        if str(verdict.get("kind") or "") != "scenario" or str(verdict.get("target") or "") != scenario_id:
            continue
        entry = by_file.get(str(verdict.get("file") or ""))
        if entry is None:
            continue
        entry["verdicts"].append(
            {
                "id": str(verdict.get("id") or ""),
                "verdict": str(verdict.get("verdict") or ""),
                "reason": str(verdict.get("reason") or ""),
            }
        )
    return sorted(by_file.values(), key=lambda row: str(row.get("ran_at") or ""), reverse=True)


def _scenario_rows(
    runs: list[dict[str, Any]],
    verdicts: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One row per scenario record — its own thing on the desk, never a square.

    Depth is over the scenario's OWN assertions (counted verdicts of a finished, live scenario
    run out of the assertions the record names), the outcome counts are its own, and the state
    word is the same coverage vocabulary an (area, kind) square uses. A scenario's `proves` and
    `references` ride the row so the desk can show what it is and link its trace.
    """
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        sid = str(scenario.get("id") or "")
        assertions = scenario.get("assertions") or []
        assertion_ids = [str(a.get("id") or "") for a in assertions]
        files = _scenario_files(runs, verdicts, sid)
        latest_by_assertion: dict[str, dict[str, Any]] = {}
        for file_row in files:
            for item in file_row["verdicts"]:
                if not _is_counted({**file_row, "verdict": item["verdict"]}):
                    continue
                current = latest_by_assertion.get(item["id"])
                if current is None or str(file_row.get("ran_at") or "") > str(current.get("ran_at") or ""):
                    latest_by_assertion[item["id"]] = {**item, "ran_at": file_row.get("ran_at")}
        counted_items = [latest_by_assertion[aid] for aid in assertion_ids if aid in latest_by_assertion]
        outcome, na_without_reason = _outcome_of(counted_items)
        in_scope = len(assertion_ids)
        counted = len(counted_items)
        latest_run = files[0] if files else None
        ages = [str(row.get("ran_at") or "") for row in counted_items]
        rows.append(
            {
                "id": sid,
                "name": str(scenario.get("name") or sid),
                "references": [str(r) for r in scenario.get("references") or ()],
                "proves": [str(p) for p in scenario.get("proves") or ()],
                "owning_prd": str(scenario.get("owning_prd") or ""),
                "depth": {"counted": counted, "in_scope": in_scope},
                "outcome": outcome,
                "latest_run": str(latest_run.get("ran_at") or "") if latest_run else None,
                "oldest_counted": min(ages) if ages else None,
                "state": _state(latest_run, counted, in_scope, outcome, na_without_reason),
            }
        )
    return rows


def _scenario_trace(
    runs: list[dict[str, Any]],
    verdicts: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    scenario_id: str,
) -> dict[str, Any]:
    """The served walk for one scenario: promise <-> things-under-test <-> scenario <-> result.

    The in-repo edges end at the result file; the finding hop crosses into the tracker, so each
    FAIL assertion is carried with the stable ``audit_key`` the run filed it under, and the page
    shows it as the finding the corpus cannot hold. An unknown scenario id answers the empty trace
    shape, never a raise.
    """
    scenario = next((s for s in scenarios if str(s.get("id")) == scenario_id), None)
    if scenario is None:
        return {
            "level": "scenario",
            "id": scenario_id,
            "name": "",
            "promises": [],
            "things": [],
            "results": [],
            "findings": [],
        }
    results = _scenario_files(runs, verdicts, scenario_id)
    findings: list[dict[str, str]] = []
    for result in results:
        for item in result["verdicts"]:
            if item["verdict"] == "fail":
                findings.append(
                    {
                        "kind": "fail",
                        "assertion": item["id"],
                        "reason": item["reason"],
                        "audit_key": f"{item['id']}",
                    }
                )
    return {
        "level": "scenario",
        "id": scenario_id,
        "name": str(scenario.get("name") or scenario_id),
        "promises": [{"id": str(p), "kind": _promise_kind(str(p))} for p in scenario.get("proves") or ()],
        "things": [_thing_of(str(r)) for r in scenario.get("references") or ()],
        "results": results,
        "findings": findings,
    }


def _area_rows(
    runs: list[dict[str, Any]],
    verdicts: list[dict[str, Any]],
    area: str,
    idx: _Index,
) -> list[dict[str, Any]]:
    """One row per capability of `area`, over its live criteria (design D5)."""
    latest_criterion: dict[str, dict[str, Any]] = {}
    file_caps: dict[str, set[str]] = defaultdict(set)
    for verdict in verdicts:
        placements = _place(verdict, idx)
        file_key = str(verdict.get("file") or "")
        for placement in placements:
            if placement.capability is None:
                continue
            file_caps[file_key].add(placement.capability)
            if placement.retired or not _is_counted(verdict):
                continue
            cid = str(verdict.get("id") or "")
            current = latest_criterion.get(cid)
            if current is None or _ran_key(verdict) > _ran_key(current):
                latest_criterion[cid] = verdict

    rows: list[dict[str, Any]] = []
    for cap in idx.area_caps.get(area, []):
        criteria = [cid for cid, mapped in idx.crit_cap.items() if mapped == cap]
        live_criteria = [cid for cid in criteria if cid in idx.known]
        counted_rows = [latest_criterion[cid] for cid in live_criteria if cid in latest_criterion]
        in_scope = len(live_criteria)
        counted = len(counted_rows)
        outcome, na_without_reason = _outcome_of(counted_rows)
        associated = [run for run in runs if cap in file_caps.get(str(run.get("file") or ""), set())]
        latest_run = _latest(associated)
        ages = [str(row.get("ran_at") or "") for row in counted_rows]
        rows.append(
            {
                "id": cap,
                "name": idx.cap_name.get(cap, ""),
                "no_criteria": not criteria,
                "depth": {"counted": counted, "in_scope": in_scope},
                "outcome": outcome,
                "latest_run": str(latest_run.get("ran_at") or "") if latest_run else None,
                "oldest_counted": min(ages) if ages else None,
                "state": _state(latest_run, counted, in_scope, outcome, na_without_reason),
            }
        )
    return rows


def _capability_rows(
    verdicts: list[dict[str, Any]],
    capability: str,
    idx: _Index,
) -> list[dict[str, Any]]:
    """One row per criterion of `capability` that has a verdict, retired ones marked (D5)."""
    criteria = sorted(cid for cid, mapped in idx.crit_cap.items() if mapped == capability)
    latest_verdict: dict[str, dict[str, Any]] = {}
    for row in verdicts:
        cid = str(row.get("id") or "")
        if cid not in criteria:
            continue
        current = latest_verdict.get(cid)
        if current is None or _ran_key(row) > _ran_key(current):
            latest_verdict[cid] = row
    rows: list[dict[str, Any]] = []
    for cid in criteria:
        verdict = latest_verdict.get(cid)
        if verdict is None:
            continue
        rows.append(
            {
                "criterion": cid,
                "verdict": str(verdict.get("verdict") or ""),
                "reason": str(verdict.get("reason") or ""),
                "kind": str(verdict.get("kind") or ""),
                "run": str(verdict.get("ran_at") or ""),
                "commit": str(verdict.get("commit") or ""),
                "file": str(verdict.get("file") or ""),
                "retired": cid not in idx.known,
            }
        )
    return rows


# ─────────────────────── the gaps roll-up (PRD 0776, design D3-D5) ───────────────────────
#
# The second view on the Quality desk: what CANNOT be checked yet. Pure like the map above —
# no I/O, no clock, no mutation — and fed the same served rows plus the two authored facts the
# sync folded into the `quality_gaps` reading. Its inputs:
#
# capabilities: list of capability rows —
#           {"id": str, "area": str, "name": str, "ships": list[str], "mark": str,
#            "tested": list[str]}. `tested` already folds a journey's `covers:` in, so an empty
#           list is "no declared tester".
# areas:    [{"id": str, "name": str, "position": int, "components": list[str],
#            "capabilities": [{"id": str, "name": str}]}], in corpus order.
# requirements: list of register rows — {"id", "kind", "disposition", "statement",
#            "register_file"}.
# coverage: {"criterion_capability": {criterion: capability},
#            "known_criteria": set[str],
#            "criterion_commitment": set[str]  (every commitment id a criterion cites)}.
# facts:    {"area_tiers": {area: tier}, "register_components": {register: [components]},
#            "shipped_prds": set[str]}  — the authored ledger `Tier`, each register's
#            `components:`, and every PRD whose status is `shipped`.
#
# A capability is SHIPPED when its `Ships in` carries `(shipped)`/`(core)` or when any PRD it
# cites is shipped (design D3). It is UNCHECKABLE when no tester names it AND no criterion maps
# to it (design D4). A promise is an adopted invariant, requirement or constraint that no
# criterion cites (design D5); it is filed under the area its register shares the most components
# with, or `not_placed` when no area shares one. Both lists order their areas by the authored
# tier — `core` before `rotation` before `parked`, untiered last — then by corpus order.

#: The closed tier vocabulary's ordering. An unknown or blank tier sorts last and is named, never
#: dropped (design D2, red-team R1).
TIER_RANK = {"core": 0, "rotation": 1, "parked": 2, "": 3}

#: A promise is one of these adopted kinds; a refusal or an accepted cost is not a promise a check
#: could prove (design D5).
PROMISE_KINDS = frozenset({"invariant", "requirement", "constraint"})


def _rank(tier: str) -> int:
    return TIER_RANK.get(tier, 3)


def _best_area(comps: set[str], area_comps: dict[str, set[str]], ordered: list[str]) -> str | None:
    """The area sharing the most components with `comps`, first in `ordered` on a tie, or None
    when no area shares one (design D5) — the one placement rule a register promise has."""
    best: str | None = None
    best_score = 0
    for aid in ordered:
        shared = len(comps & area_comps.get(aid, set()))
        if shared > best_score:
            best_score = shared
            best = aid
    return best


def current_line_of(facts: dict[str, Any] | None) -> str:
    """The release line being built, as the corpus's own config names it.

    The sync reads it off the commit's ``[fleet.commitments] current_line`` and carries it in the
    gaps reading; a reading written without one is the commitments checks' own default — the
    same answer the checker gives a corpus that never set it.
    """
    line = str((facts or {}).get("current_line") or "").strip()
    return line or CommitmentsConfig().current_line


def is_testable_promise(row: dict[str, Any], current_line: str | None = None) -> bool:
    """A register row a check could prove: an adopted invariant, requirement or constraint that is
    not cut from the release line being built.

    ``Cut`` names the release line a row lands in. Blank, or the line being built, is a live
    promise; a LATER line is cut, so the product being checked today does not promise it yet and
    counting it would grow the "no check yet" pile with promises nobody is making on this line.
    The comparison is the commitments checks' own (`line_is_cut`), so the desk and the checker
    cannot disagree about which rows are live.
    """
    if str(row.get("kind") or "") not in PROMISE_KINDS:
        return False
    if str(row.get("disposition") or "") != "adopted":
        return False
    line = current_line or CommitmentsConfig().current_line
    return not line_is_cut(line, str(row.get("cut") or "").strip())


def _register_of(row: dict[str, Any]) -> str:
    """The register a requirement row belongs to — its `register_file` stem, never the row id."""
    return Path(str(row.get("register_file") or row.get("file") or "")).stem


def _is_shipped(cap: dict[str, Any], shipped_prds: set[str]) -> bool:
    """A capability the product has built (design D3): a mark, or a cited shipped PRD."""
    if str(cap.get("mark") or "") in ("shipped", "core"):
        return True
    return any(str(n) in shipped_prds for n in cap.get("ships") or ())


def quality_gaps(
    capabilities: list[dict[str, Any]],
    areas: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    coverage: dict[str, Any],
    facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The ``GET /api/quality/gaps`` payload **minus** ``commit`` (the route adds that).

    Two ordered lists — ``uncheckable`` (shipped capabilities nothing can check) and ``unproven``
    (promises no criterion cites) — each grouped by area, most important first, with a ``totals``
    strip. Read-only: it returns rows and counts and writes nothing. An absent or partial input
    degrades to empty lists, never a raise.
    """
    facts = facts or {}
    line = current_line_of(facts)
    area_tiers = {str(k): str(v or "") for k, v in (facts.get("area_tiers") or {}).items()}
    register_components = {
        str(k): [str(x) for x in (v or [])] for k, v in (facts.get("register_components") or {}).items()
    }
    shipped_prds = {str(x) for x in (facts.get("shipped_prds") or ())}

    order: dict[str, int] = {}
    area_name: dict[str, str] = {}
    area_comps: dict[str, set[str]] = {}
    for i, area in enumerate(areas):
        aid = str(area.get("id") or "")
        order[aid] = i
        area_name[aid] = str(area.get("name") or "")
        area_comps[aid] = {str(c) for c in area.get("components") or ()}
    cap_meta = {str(c.get("id") or ""): c for c in capabilities}
    cited_caps = {str(v) for v in (coverage.get("criterion_capability") or {}).values()}
    cited_commitments = {str(x) for x in (coverage.get("criterion_commitment") or ())}

    def area_sort(aid: str) -> tuple[int, int, str]:
        return (_rank(area_tiers.get(aid, "")), order.get(aid, len(order)), aid)

    # ── the first list: shipped capabilities with no test path ──────────────
    uncheckable: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for area in areas:
        aid = str(area.get("id") or "")
        for cap in area.get("capabilities") or []:
            cid = str(cap.get("id") or "")
            meta = cap_meta.get(cid, cap)
            if not _is_shipped(meta, shipped_prds):
                continue
            if meta.get("tested"):
                continue
            if cid in cited_caps:
                continue
            uncheckable[aid].append({"id": cid, "name": str(cap.get("name") or meta.get("name") or "")})

    uncheckable_groups: list[dict[str, Any]] = [
        {
            "area": aid,
            "name": area_name.get(aid, ""),
            "tier": area_tiers.get(aid, ""),
            "rows": uncheckable[aid],
            "count": len(uncheckable[aid]),
        }
        for aid in sorted(uncheckable, key=area_sort)
    ]

    # ── the second list: adopted promises no criterion cites ────────────────
    promises: dict[str, list[dict[str, Any]]] = defaultdict(list)
    not_placed: list[dict[str, Any]] = []
    for row in requirements:
        if not is_testable_promise(row, line):
            continue
        rid = str(row.get("id") or "")
        if rid in cited_commitments:
            continue
        register = _register_of(row)
        comps = set(register_components.get(register, []))
        best = _best_area(comps, area_comps, sorted(order, key=area_sort))
        entry = {"id": rid, "statement": str(row.get("statement") or ""), "register": register}
        if best is None:
            not_placed.append(entry)
        else:
            promises[best].append(entry)

    unproven_groups: list[dict[str, Any]] = [
        {
            "area": aid,
            "name": area_name.get(aid, ""),
            "tier": area_tiers.get(aid, ""),
            "rows": promises[aid],
            "count": len(promises[aid]),
        }
        for aid in sorted(promises, key=area_sort)
    ]

    gap_areas = set(uncheckable) | set(promises)
    uncheckable_total = sum(g["count"] for g in uncheckable_groups)
    unproven_total = sum(g["count"] for g in unproven_groups) + len(not_placed)
    return {
        "uncheckable": {"groups": uncheckable_groups, "total": uncheckable_total},
        "unproven": {"groups": unproven_groups, "not_placed": not_placed, "total": unproven_total},
        "totals": {
            "uncheckable": uncheckable_total,
            "unproven": unproven_total,
            "areas_with_gap": len(gap_areas),
            "core_areas": sum(1 for aid in gap_areas if area_tiers.get(aid, "") == "core"),
            "not_placed": len(not_placed),
        },
    }


# ─────────────────────── the promises reading (the Quality desk's Promises view) ───────────────────────
#
# One row per TESTABLE PROMISE — an adopted, uncut invariant/requirement/constraint register row
# (`is_testable_promise`), a capability the product has shipped (`_is_shipped`), and a journey
# whose acceptance criteria a check can walk — with ONE STATE each, computed here and never stored:
#
#   passing      every check that proves it passed, live and finished, within its tier's window
#   failing      a check that proves it failed (a finished run's fail, live or a code reading)
#   flaky        one check gave different verdicts for it on the same release
#   disputed     the verifier disagreed with the check's verdict — never green, and not a failure
#   unfinished   its newest live run passed with platform evidence, but cannot count yet: the
#                run names no release (no version endpoint answers, FLT-1220), it did not finish,
#                or its expected results await the verifier's approval (FLT-1214)
#   out-of-date  it has a check, but no live pass inside the window (or none ever)
#   cant-run     the check that proves it was blocked: it could not run where it was sent
#   quarantined  every check that proves it is quarantined — it counts nowhere
#   no-check     nothing proves it
#
# EVIDENCE is any verdict that cites the promise: a journey criterion through the criterion ->
# capability and criterion -> commitment maps (and its journey itself), a scenario assertion
# through its own `promise` (the result's or the record's) or else every promise the scenario
# `proves:`, and a checklist item or lint whose result names the promise (`promise`, or an id
# whose last segment IS the promise id). Per check, the latest decisive verdict speaks; across a
# promise's checks that HAVE one, the STRICTEST state wins (a check never yet run is a check, not
# a result, so it never outranks a verdict).
#
# Pure like everything above: no I/O, and the clock is a parameter (`now`, RFC3339), because "out
# of date" is an age and an age needs a now.

PASSING = "passing"
FAILING = "failing"
FLAKY = "flaky"
DISPUTED = "disputed"
UNFINISHED = "unfinished"
OUT_OF_DATE = "out-of-date"
CANT_RUN = "cant-run"
QUARANTINED = "quarantined"
NO_CHECK = "no-check"

#: Every promise state, in the order the page lists a group's rows: the worst first.
PROMISE_STATES = (FAILING, FLAKY, DISPUTED, QUARANTINED, UNFINISHED, OUT_OF_DATE, CANT_RUN, NO_CHECK, PASSING)
_STATE_ORDER = {state: i for i, state in enumerate(PROMISE_STATES)}
#: Which of two CHECK states is stricter, when one promise has several checks.
#: `unfinished` sits between out of date and passing: a pass that cannot count yet is more than no
#: live pass at all, and less than one that counts.
_STRICT = {FAILING: 0, FLAKY: 1, DISPUTED: 2, CANT_RUN: 3, OUT_OF_DATE: 4, UNFINISHED: 5, PASSING: 6}

#: How long a pass stays current, by the area's authored tier — the part rotation's own cadence
#: (`commandtree/scripts/audit.py`'s `TIER_MAX_AGE_DAYS`, pinned equal by a test, because that
#: shipped script runs as a top-level module this package cannot import).
TIER_WINDOW_DAYS: dict[str, int] = {"core": 3, "rotation": 14}
#: A parked or untiered area is never auto-checked, so it has no cadence of its own; its passes
#: age out at the longest cadence there is rather than never.
DEFAULT_WINDOW_DAYS = 14

#: The group a promise with no area lands in.
UNPLACED = ""
#: How a filter names that group on the wire: an empty value means "no filter", so it needs a word.
UNPLACED_PARAM = "-"


def _criterion_order(pid: str) -> tuple[str, int, str]:
    """`slug#10` after `slug#9`: a journey's criteria in the order the journey states them."""
    head, sep, tail = pid.rpartition("#")
    return (head, int(tail), "") if sep and tail.isdigit() else (pid, 0, pid)


def _instant(text: Any) -> datetime | None:
    """An RFC3339 string as an aware `datetime`, or None — never a raise."""
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        parsed = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _days_between(earlier: str, later: str) -> float | None:
    a, b = _instant(earlier), _instant(later)
    if a is None or b is None:
        return None
    return float((b - a).total_seconds()) / 86400.0


def quarantine_end(until: Any) -> datetime | None:
    """The instant a quarantine's `until` names, or None when it is not a readable date.

    One reader of the field, so `quarantine_active` and the merge-time check cannot disagree
    about what a readable until-date is. A bare date means the end of that day.
    """
    text = str(until or "").strip()
    if not text:
        return None
    return _instant(text + "T23:59:59Z") if len(text) == 10 else _instant(text)


def quarantine_active(quarantine: Any, now: str) -> bool:
    """Whether a record's `quarantine` holds at `now`: its `until` date is today or later.

    An unreadable date does not quarantine: a typo must not hide a check for ever.
    """
    if not isinstance(quarantine, dict):
        return False
    stamp = quarantine_end(quarantine.get("until"))
    current = _instant(now)
    return stamp is not None and current is not None and stamp >= current


def _has_evidence(row: dict[str, Any]) -> bool:
    """A schema-2 pass needs an evidence object with something in it; schema 1 never had one."""
    version = row.get("schema_version")
    if not isinstance(version, int) or version < 2:
        return True
    evidence = row.get("evidence")
    return isinstance(evidence, dict) and any(evidence.values())


def _names_its_release(row: dict[str, Any]) -> bool:
    """A schema-2 result must say which release it ran against (FLT-1220): until a version probe
    answers, a run that names none reads unfinished. Schema 1 never carried one."""
    version = row.get("schema_version")
    return not isinstance(version, int) or version < 2 or bool(str(row.get("release") or "").strip())


def _counts_as_pass(row: dict[str, Any]) -> bool:
    """A pass that counts: a finished run against the live product, naming its release, with its
    evidence, that the verifier lets stand — `quality_reviews.counts`: not disputed, and not set
    aside (`not_counted`: its expected results are not approved, or the run names no version)."""
    return (
        str(row.get("verdict") or "") == "pass"
        and row.get("finished") is True
        and str(row.get("environment") or "") == "live"
        and _names_its_release(row)
        and _has_evidence(row)
        and quality_reviews.counts(row)
    )


def _counts_as_fail(row: dict[str, Any]) -> bool:
    """A fail that counts: any finished run's — a code reading that finds a promise broken has
    found it broken. (Only PASSING needs the live product.)"""
    return str(row.get("verdict") or "") == "fail" and row.get("finished") is True


def _is_blocked(row: dict[str, Any]) -> bool:
    return str(row.get("verdict") or "") == "blocked" and row.get("finished") is True


def _review(row: dict[str, Any]) -> str:
    review = row.get("review")
    return str(review.get("state") or "") if isinstance(review, dict) else ""


def _decisive(row: dict[str, Any]) -> bool:
    """A verdict that can decide a check's state (a not-applicable, a code-only pass, an
    unfinished run's verdict, a schema-2 pass with no evidence and a pass the verifier set aside
    never can; a disputed one always can — it decides "disputed")."""
    return _counts_as_pass(row) or _counts_as_fail(row) or _is_blocked(row) or _review(row) == "disputed"


#: The words for a pass whose run names no release (FLT-1220). Why it names none — the
#: environment's version probe — is the environment record's to say (`_release_missing`).
RELEASE_UNKNOWN = "release unknown: the run names no release"
DID_NOT_FINISH = "the run did not finish"

#: WHAT AN UNFINISHED PASS WAITS FOR — the only reasons that make a pass "unfinished" rather than
#: out of date. Each is a thing that arrives (a release the probe names, a finished run, the
#: verifier's first approval); a rejected or changed oracle, or a run naming no scenario version,
#: is a verdict on the check itself and stays out of date.
WAIT_RELEASE = "release"
WAIT_FINISH = "finish"
WAIT_APPROVAL = "approval"


def _awaits_first_approval(row: dict[str, Any]) -> bool:
    """The pass's `not_counted` is only the oracle awaiting its first approval (FLT-1214)."""
    return str(row.get("oracle") or "") == quality_reviews.PENDING and bool(str(row.get("scenario_version") or ""))


def _waiting_for(row: dict[str, Any]) -> list[str] | None:
    """What a pass waits for before it can count (`WAIT_*`), or None when it is not WAITING — not a
    live, evidenced, undisputed pass, or held back by something a wait will not fix."""
    if (
        str(row.get("verdict") or "") != "pass"
        or str(row.get("environment") or "") != "live"
        or not _has_evidence(row)
        or _review(row) == "disputed"
        or _counts_as_pass(row)
    ):
        return None
    if row.get("not_counted") and not _awaits_first_approval(row):
        return None
    waits: list[str] = []
    if not _names_its_release(row):
        waits.append(WAIT_RELEASE)
    if row.get("finished") is not True:
        waits.append(WAIT_FINISH)
    if row.get("not_counted"):
        waits.append(WAIT_APPROVAL)
    return waits or None


def _is_unfinished_pass(row: dict[str, Any]) -> bool:
    """A pass that RAN — live, with platform evidence, not disputed — and only WAITS to count: its
    run names no release, did not finish, or its expected results await their first approval
    (FLT-1220/1214). It is not "not run" (FLT-1212 is for a verdict with no evidence), and it is
    never green."""
    return _waiting_for(row) is not None


def _is_uncounted_fail(row: dict[str, Any]) -> bool:
    """A fail or block on the record that does not count (an unfinished run's): it still says the
    check did not pass, so it forbids reading a pass beside it as merely unfinished."""
    return str(row.get("verdict") or "") in ("fail", "blocked") and not _decisive(row)


def _not_counted_reasons(row: dict[str, Any]) -> list[str]:
    """Every reason a verdict on the record does not count, in the page's words — each one, not the first."""
    verdict = str(row.get("verdict") or "")
    if verdict == "not-applicable":
        return ["not applicable"]
    reasons: list[str] = []
    if verdict == "pass" and not _names_its_release(row):
        reasons.append(RELEASE_UNKNOWN)
    if row.get("finished") is not True:
        reasons.append(DID_NOT_FINISH)
    if row.get("not_counted"):
        reasons.append(str(row["not_counted"]))
    if verdict == "pass" and str(row.get("environment") or "") != "live":
        reasons.append("read the code only")
    if verdict == "pass" and not _has_evidence(row):
        reasons.append("not run (no evidence)")
    return reasons


def _not_counted_why(row: dict[str, Any]) -> str:
    """Why a verdict on the record does not count — one line, every reason."""
    return " · ".join(_not_counted_reasons(row))


def _unfinished_of(
    rows: list[dict[str, Any]], window_days: int, now: str, tainted: frozenset[str], failed_at: str = ""
) -> dict[str, Any] | None:
    """The pass that makes a check `unfinished`, or None.

    The newest waiting pass (`_is_unfinished_pass`) qualifies only when nothing says the check did
    NOT pass beside it — no uncounted fail or block on this check at or after it, none on any of the
    promise's checks at or after it (`failed_at`: the newest such fail's `ran_at` across them), and
    none on the same run (`tainted`: the run files that recorded one, on any of the promise's
    checks) — and only inside the same freshness window an out-of-date pass has: an unfinished
    reading that outlives it falls back to out of date and back into the QA agent's queue.
    """
    pending = sorted((r for r in rows if _is_unfinished_pass(r)), key=_ran_key)
    if not pending:
        return None
    newest = pending[-1]
    at, run = str(newest.get("ran_at") or ""), str(newest.get("file") or "")
    if run in tainted or (failed_at and failed_at >= at):
        return None
    for row in rows:
        if _is_uncounted_fail(row) and (str(row.get("ran_at") or "") >= at or str(row.get("file") or "") == run):
            return None
    age = _days_between(at, now)
    if age is None or age > window_days:
        return None
    return newest


def _tainted_runs(rows: Iterable[dict[str, Any]]) -> frozenset[str]:
    """The run files that recorded an uncounted fail or block."""
    return frozenset(str(r.get("file") or "") for r in rows if _is_uncounted_fail(r))


def _newest_uncounted_fail(rows: Iterable[dict[str, Any]]) -> str:
    """The `ran_at` of the newest uncounted fail or block among `rows`, or "" when there is none."""
    return max((str(r.get("ran_at") or "") for r in rows if _is_uncounted_fail(r)), default="")


def check_state(
    rows: list[dict[str, Any]],
    window_days: int,
    now: str,
    current: dict[str, str] | None = None,
    tainted: frozenset[str] = frozenset(),
    failed_at: str = "",
) -> tuple[str, dict[str, Any] | None]:
    """One check's state for one promise, from every verdict it recorded, and the row that
    decided it (None when nothing decisive exists).

    The latest decisive verdict speaks: disputed by the verifier -> `disputed`; on a release where
    this check's verdicts disagree -> `flaky`; a fail -> `failing`; a block -> `cant-run`; a pass
    inside the window -> `passing`, outside it -> `out-of-date`. A pass on a release older than its
    own environment's current one (`current`: `{environment: release}`, from counted runs only) is
    `out-of-date` too: it proved an earlier build, not this one. Where a check would read out of
    date but its newest run passed live with evidence and only waits to count (`_unfinished_of`)
    it reads `unfinished`, decided by that run. A check with nothing decisive and no such pass is
    `out-of-date` — it exists and has never been proven live.
    """
    decisive = sorted((r for r in rows if _decisive(r)), key=_ran_key)
    waiting = _unfinished_of(rows, window_days, now, tainted, failed_at)
    if not decisive:
        return (UNFINISHED, waiting) if waiting else (OUT_OF_DATE, None)
    latest = decisive[-1]
    # A NEWER PASS THAT ONLY WAITS TO COUNT says more than a stale one that did: the check ran and
    # passed, and only its release, its finish or its first approval is missing.
    newer = waiting if waiting is not None and _ran_key(waiting) > _ran_key(latest) else None
    if _review(latest) == "disputed":
        return DISPUTED, latest
    release = str(latest.get("release") or "")
    if release:
        seen = {
            str(r.get("verdict") or "")
            for r in decisive
            if str(r.get("release") or "") == release and (_counts_as_pass(r) or _counts_as_fail(r))
        }
        if {"pass", "fail"} <= seen:
            return FLAKY, latest
    if _counts_as_fail(latest):
        return FAILING, latest
    if _is_blocked(latest):
        return CANT_RUN, latest
    now_on = (current or {}).get(_env_of(latest), "")
    if now_on and release and release != now_on:
        return (UNFINISHED, newer) if newer else (OUT_OF_DATE, latest)
    age = _days_between(str(latest.get("ran_at") or ""), now)
    if age is not None and age > window_days:
        return (UNFINISHED, newer) if newer else (OUT_OF_DATE, latest)
    return PASSING, latest


def _evidence_of(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """The fields of a verdict the page shows as its evidence line, and nothing else."""
    if row is None:
        return None
    out: dict[str, Any] = {
        "id": str(row.get("id") or ""),
        "kind": str(row.get("kind") or ""),
        "target": str(row.get("target") or ""),
        "verdict": str(row.get("verdict") or ""),
        "reason": str(row.get("reason") or ""),
        "ran_at": str(row.get("ran_at") or ""),
        "environment": str(row.get("environment") or ""),
        "file": str(row.get("file") or ""),
        # The commit the result read — the drill-down's "which build" line (FLT-1211).
        "commit": str(row.get("commit") or ""),
    }
    for key in (
        "release",
        "environment_id",
        "scenario_version",
        "expected",
        "observed",
        "attempts",
        "cause",
        "ticket",
        "oracle",
    ):
        if row.get(key):
            out[key] = str(row[key])
    for key in ("evidence", "review"):
        if isinstance(row.get(key), dict):
            out[key] = dict(row[key])
    if isinstance(row.get("new"), bool):
        out["new"] = row["new"]
    why = _not_counted_why(row)
    if why and not _decisive(row):
        out["not_counted"] = why
    waits = _waiting_for(row)
    if waits:
        # What it waits for, as codes the QA plan reads (`WAIT_*`): whether a re-run can help.
        out["waiting"] = waits
    return out


def _version_number(value: Any) -> int | None:
    """A result's `scenario_version` as a positive integer (`5`, `"5"`), or None when it is not one."""
    if isinstance(value, bool):
        return None
    text = str(value).strip() if isinstance(value, (int, str)) else ""
    return int(text) if text.isdigit() and int(text) > 0 else None


def _is_superseded(row: dict[str, Any], current: Any) -> bool:
    """True when `row` ran an older version of its scenario than the record's `version:` today.

    A row naming no version is read as current — there is nothing to say it is older."""
    ran = _version_number(row.get("scenario_version"))
    return isinstance(current, int) and not isinstance(current, bool) and ran is not None and ran < current


def _assertion_index(scenarios: list[dict[str, Any]]) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    """`{assertion id: (scenario, assertion)}` across every scenario record."""
    out: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for scenario in scenarios:
        for assertion in scenario.get("assertions") or ():
            out[str(assertion.get("id") or "")] = (scenario, assertion)
    return out


def _programs_of(ids: list[str], prd_program: dict[str, str]) -> list[str]:
    seen: list[str] = []
    for n in ids:
        program = prd_program.get(str(n).split("-", 1)[0])
        if program and program not in seen:
            seen.append(program)
    return seen


def _catalog(inputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every testable promise, keyed by id: its kind, words, area, register and programs."""
    facts = inputs.get("facts") or {}
    line = current_line_of(facts)
    shipped_prds = {str(x) for x in (facts.get("shipped_prds") or ())}
    register_components = {
        str(k): {str(x) for x in (v or ())} for k, v in (facts.get("register_components") or {}).items()
    }
    prd_program = {str(k): str(v) for k, v in (facts.get("prd_program") or {}).items()}
    claims: dict[str, list[str]] = defaultdict(list)
    for n, ids in (facts.get("prd_claims") or {}).items():
        for rid in ids or ():
            claims[str(rid)].append(str(n))
    areas = list(inputs.get("areas") or [])
    area_ids = [str(a.get("id") or "") for a in areas]
    area_comps = {str(a.get("id") or ""): {str(c) for c in a.get("components") or ()} for a in areas}
    cap_area: dict[str, str] = {}
    for area in areas:
        for cap in area.get("capabilities") or ():
            cap_area[str(cap.get("id") or "")] = str(area.get("id") or "")
    coverage = inputs.get("coverage") or {}
    crit_cap = {str(k): str(v) for k, v in (coverage.get("criterion_capability") or {}).items()}
    citing: dict[str, list[str]] = defaultdict(list)
    for crit, ids in (coverage.get("criterion_commitments") or {}).items():
        for rid in ids or ():
            citing[str(rid)].append(str(crit))
    prd_caps: dict[str, list[str]] = defaultdict(list)
    for cap in inputs.get("capabilities") or ():
        for n in cap.get("ships") or ():
            prd_caps[str(n)].append(str(cap.get("id") or ""))

    def voted(cap_ids: list[str]) -> str:
        """The area most of these capabilities sit in, first in corpus order on a tie."""
        votes: dict[str, int] = defaultdict(int)
        for cap_id in cap_ids:
            if cap_area.get(cap_id):
                votes[cap_area[cap_id]] += 1
        if not votes:
            return UNPLACED
        return max(area_ids, key=lambda a: (votes.get(a, 0), -area_ids.index(a)))

    catalog: dict[str, dict[str, Any]] = {}
    for row in inputs.get("requirements") or ():
        if not is_testable_promise(row, line):
            continue
        rid = str(row.get("id") or "")
        register = _register_of(row)
        # WHERE A REGISTER PROMISE IS FILED, most specific first: the area its register shares the
        # most components with (the gaps view's rule, design D5); else where the journey criteria
        # that cite it point; else where the capabilities of the PRDs that claim it live.
        area = (
            _best_area(register_components.get(register, set()), area_comps, area_ids)
            or voted([crit_cap.get(c, "") for c in citing.get(rid, [])])
            or voted([cap for n in claims.get(rid, []) for cap in prd_caps.get(n, [])])
        )
        catalog[rid] = {
            "id": rid,
            "kind": "requirement",
            "statement": md.plain(str(row.get("statement") or "")),
            "area": area or UNPLACED,
            "register": str(row.get("prefix") or "") or register,
            "programs": _programs_of(claims.get(rid, []), prd_program),
        }
    for cap in inputs.get("capabilities") or ():
        cid = str(cap.get("id") or "")
        if not cid or str(cap.get("mark") or "") == "retired" or not _is_shipped(cap, shipped_prds):
            continue
        catalog[cid] = {
            "id": cid,
            "kind": "capability",
            "statement": md.plain(str(cap.get("name") or "")),
            "area": str(cap.get("area") or "") or cap_area.get(cid, UNPLACED),
            "register": "CAP",
            "programs": _programs_of([str(n) for n in cap.get("ships") or ()], prd_program),
        }
    # EVERY CRITERION OF A LIVE JOURNEY IS A PROMISE OF ITS OWN (FLT-1202): the journey is how a
    # person gets a job done, and each acceptance criterion is one thing it promises along the way.
    # `journey_criteria` holds only live journeys (a `status: retired` journey is dropped where the
    # file is read), and a criterion sits in its capability's area, else its journey's.
    journey_criteria = coverage.get("journey_criteria") or {}
    criterion_text = {str(k): str(v) for k, v in (coverage.get("criterion_text") or {}).items()}
    for journey in inputs.get("journeys") or ():
        slug = str(journey.get("slug") or "")
        criteria = [str(c) for c in journey_criteria.get(slug, ())]
        if not slug or not criteria:
            continue
        title = md.plain(str(journey.get("title") or slug))
        home = voted([*(str(c) for c in journey.get("covers") or ()), *(crit_cap.get(c, "") for c in criteria)])
        programs = _programs_of([str(journey.get("owning_prd") or "")], prd_program)
        for crit in criteria:
            catalog[crit] = {
                "id": crit,
                "kind": "criterion",
                "statement": md.plain(criterion_text.get(crit, "")) or f"{title}, criterion {crit.rsplit('#', 1)[-1]}",
                "area": cap_area.get(crit_cap.get(crit, ""), "") or home,
                "register": "journey",
                "programs": programs,
                "journey": slug,
                "journey_title": title,
            }
    return catalog


class _Attribution(NamedTuple):
    """Which verdicts are evidence for which promise, and which checks each promise has.

    `evidence[promise][check]` is that check's verdict rows; `checks[promise]` names every check
    that proves it, run or not (a scenario assertion, a journey criterion, a cited result);
    `held[promise]` the ones a live quarantine holds. `unplaced` is every result row that NAMES a
    promise id the catalog does not hold (BUG-1151) — a criterion past its journey's end, a retired
    journey's criterion, a register id that is unknown or no longer a live promise, a scenario-row
    id given as a promise — as ``{file, row, promise}``: that row counts toward nothing, so the
    desk says so rather than dropping it in silence.
    """

    evidence: dict[str, dict[str, list[dict[str, Any]]]]
    checks: dict[str, set[str]]
    held: dict[str, set[str]]
    unplaced: list[dict[str, Any]]


def _attribution(inputs: dict[str, Any], catalog: dict[str, dict[str, Any]], now: str) -> _Attribution:
    coverage = inputs.get("coverage") or {}
    crit_cap = {str(k): str(v) for k, v in (coverage.get("criterion_capability") or {}).items()}
    crit_commit = {str(k): [str(x) for x in v or ()] for k, v in (coverage.get("criterion_commitments") or {}).items()}
    crit_journey: dict[str, str] = {}
    for slug, criteria in (coverage.get("journey_criteria") or {}).items():
        for crit in criteria or ():
            crit_journey[str(crit)] = str(slug)
    scenarios = list(inputs.get("scenarios") or [])
    assertions = _assertion_index(scenarios)
    held_scenarios = {str(s.get("id") or "") for s in scenarios if quarantine_active(s.get("quarantine"), now)}

    def cited(check: str, explicit: str = "") -> set[str]:
        found: set[str] = {explicit} if explicit else set()
        hit = assertions.get(check)
        if hit is not None:
            scenario, assertion = hit
            own = str(assertion.get("promise") or "")
            if not explicit:
                found |= {own} if own else {str(p) for p in scenario.get("proves") or ()}
        elif check in crit_journey or check in crit_cap or check in crit_commit:
            found |= {check, crit_cap.get(check, ""), *crit_commit.get(check, [])}
        else:
            found.add(check.rsplit("/", 1)[-1])
        return {p for p in found if p in catalog}

    def unresolved(check: str, explicit: str, placed: set[str]) -> list[str]:
        """The ids a PROMISE-BEARING row could not be placed by, or [] when nothing is amiss.

        A row that names a promise (`promise`) the catalog lacks is reported even when it also
        counts elsewhere — the claim itself is wrong. A row that counts toward NOTHING is reported
        with what it resolved to: its assertion's `Promise` cell, else every id its scenario
        `proves:` (``""`` when that is empty too), else — a criterion- or assertion-shaped id that
        no journey or scenario holds — the row id itself. A checklist item with no `promise`
        (`ux/I1`) never claimed one: its tail is a guess, and it counts on the map instead.
        """
        if explicit:
            return [] if explicit in catalog else [explicit]
        if placed:
            return []
        hit = assertions.get(check)
        if hit is not None:
            own = str(hit[1].get("promise") or "")
            if own:
                return [own]
            return [str(p) for p in hit[0].get("proves") or ()] or [""]
        return [check] if _ROW_ID_RE.match(check) else []

    def is_held(check: str) -> bool:
        hit = assertions.get(check)
        return hit is not None and str(hit[0].get("id") or "") in held_scenarios

    # THE SCENARIO'S CURRENT VERSION DECLARES ITS CHECKS (BUG-1185), and only its own runs speak
    # for them. A row from a SUPERSEDED version (`_is_superseded`) is history: it adds no check,
    # counts as no evidence and sets no state — not on a row the current version dropped, nor on
    # one it kept or moved, because an approval covers its own version's passes only (FLT-1214)
    # and a reused ordinal is not the same expected result. It stays on the scenario's run list.
    scenario_at = {str(s.get("id") or ""): s.get("version") for s in scenarios}

    def retired(check: str) -> bool:
        """An assertion-shaped id of a scenario on record that its current version does not declare."""
        return "#" in check and check not in assertions and check.split("#", 1)[0] in scenario_at

    evidence: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    checks: dict[str, set[str]] = defaultdict(set)
    held: dict[str, set[str]] = defaultdict(set)
    # The checks that exist whether or not they ever ran: every scenario assertion and every
    # journey criterion.
    for check in [*assertions, *crit_journey]:
        for promise in cited(check):
            checks[promise].add(check)
            if is_held(check):
                held[promise].add(check)
    # ONE ENTRY PER (row, unknown id), however many runs repeated it: the newest file that did and
    # how many rows in all — 5000 nightly runs of one bad row are one finding, not 5000.
    unplaced: dict[tuple[str, str], dict[str, Any]] = {}
    for row in inputs.get("verdicts") or ():
        check = str(row.get("id") or "")
        if not check:
            continue
        if _is_superseded(row, scenario_at.get(check.split("#", 1)[0]) if "#" in check else None):
            continue
        if retired(check):
            # A row the current version does not declare, claiming the current version (or none):
            # misfiled, counted toward nothing, and reported as BUG-1151 reports any
            # assertion-shaped id no scenario holds.
            placed, unknowns = set(), [check]
        else:
            # THE CURRENT PROMISE CELL WINS over the row's own `promise` (BUG-1185): the record
            # says what its row proves today; a row's field narrows only a `proves:` list.
            hit = assertions.get(check)
            explicit = "" if hit is not None and hit[1].get("promise") else str(row.get("promise") or "")
            placed = cited(check, explicit)
            unknowns = unresolved(check, explicit, placed)
        for unknown in unknowns:
            file = str(row.get("file") or "")
            entry = unplaced.setdefault((check, unknown), {"file": file, "row": check, "promise": unknown, "rows": 0})
            entry["rows"] += 1
            entry["file"] = max(entry["file"], file)
        for promise in placed:
            checks[promise].add(check)
            if is_held(check):
                held[promise].add(check)
                continue
            evidence[promise][check].append(row)
    listed = sorted(unplaced.values(), key=lambda u: (u["row"], u["promise"]))
    return _Attribution(evidence, checks, held, listed)


def _env_of(row: dict[str, Any]) -> str:
    """The environment a verdict ran in — its schema-2 `environment_id`, or "" when it names none."""
    return str(row.get("environment_id") or "")


def _moves_the_release(row: dict[str, Any]) -> bool:
    """A verdict that may say which release an environment is on: a live, finished pass or fail
    the verifier lets stand. A blocked run, a disputed or not-counted verdict, a pass without
    evidence and a code reading say nothing about what is deployed."""
    if str(row.get("environment") or "") != "live" or not str(row.get("release") or ""):
        return False
    return _counts_as_pass(row) or (_counts_as_fail(row) and quality_reviews.counts(row))


def _release_lines(verdicts: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Each environment's releases, oldest first by the first counted run that named each.

    PER ENVIRONMENT, because environments do not move together: a staging box on tomorrow's build
    or a lagging customer install must not decide what is "current" anywhere else. And from
    counted runs only (`_moves_the_release`), so one blocked or disputed run on a local build
    cannot make every newer pass read out of date.
    """
    first: dict[str, dict[str, str]] = defaultdict(dict)
    for row in verdicts:
        # A row that names no environment cannot say what any environment runs; it is judged
        # against production's line instead (`_current_by_env`).
        if not _moves_the_release(row) or not _env_of(row):
            continue
        release, ran = str(row["release"]), str(row.get("ran_at") or "")
        seen = first[_env_of(row)]
        if release not in seen or ran < seen[release]:
            seen[release] = ran
    return {env: sorted(seen, key=lambda r: (seen[r], r)) for env, seen in first.items()}


def _production_environment(environments: list[dict[str, Any]]) -> str | None:
    """The one environment whose record says `production: true`, or None when there is none or
    more than one — the head's release line speaks for production and never guesses which."""
    found = [str(e.get("id") or "") for e in environments if isinstance(e, dict) and e.get("production") is True]
    return found[0] if len(found) == 1 and found[0] else None


def _release_missing(environments: list[dict[str, Any]], production: str | None) -> str:
    """Which condition of the release line fails: no production environment, several, or no
    counted run on production that names its release — with its version probe, from the record."""
    marked = [e for e in environments if isinstance(e, dict) and e.get("production") is True]
    if not marked:
        return "no environment is marked production"
    if production is None:
        return f"{len(marked)} environments are marked production; exactly one may be"
    record = next((e for e in marked if str(e.get("id") or "") == production), {})
    probe = record.get("version_probe")
    base = f"{production} is production, but no counted run there names its release"
    if not probe:
        return f"{base}: its version_probe is null, so no run there can name one"
    return f"{base}; its version probe is {probe}"


def _current_by_env(lines: dict[str, list[str]], production: str | None) -> dict[str, str]:
    """Each environment's current release; a row naming no environment reads production's."""
    current = {env: order[-1] for env, order in lines.items() if order}
    if production is not None and production in current:
        current[""] = current[production]
    return current


def _change_on(rows: list[dict[str, Any]], line: list[str]) -> tuple[str, bool]:
    """A promise's change on ONE environment's release line — `worse`, `fixed` or "" — and whether
    it has rows there but none on that line's current release."""
    if not line:
        return "", False
    current, previous = line[-1], (line[-2] if len(line) > 1 else "")
    on_current = _on_release(rows, current)
    on_previous = _on_release(rows, previous) if previous else ""
    change = ""
    if on_current == "fail" and (on_previous == "pass" or any(r.get("new") is True for r in rows)):
        change = "worse"
    elif on_current == "pass" and on_previous == "fail":
        change = "fixed"
    return change, bool(rows) and not on_current


def _on_release(rows: list[dict[str, Any]], release: str) -> str:
    """A promise's reading on one release across its checks: `fail`, `pass` or `""` (unread)."""
    seen = [r for r in rows if str(r.get("release") or "") == release]
    if any(_counts_as_fail(r) for r in seen):
        return "fail"
    if any(_counts_as_pass(r) for r in seen):
        return "pass"
    return ""


def _since(rows: list[dict[str, Any]]) -> str:
    """Where a failing promise's current run of fails began: the release, else the instant."""
    ordered = sorted((r for r in rows if _counts_as_pass(r) or _counts_as_fail(r)), key=_ran_key)
    start: dict[str, Any] | None = None
    for row in ordered:
        start = (start or row) if _counts_as_fail(row) else None
    if start is None:
        return ""
    return str(start.get("release") or start.get("ran_at") or "")


def _promise_state(
    checks: set[str],
    held: set[str],
    by_check: dict[str, list[dict[str, Any]]],
    window: int,
    now: str,
    current: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """A promise's one state over its checks — the strictest VERDICT — and the verdict that decided it.

    Strictness is taken over the checks that have a decisive verdict: a check that exists and has
    never produced one (a journey criterion nobody has walked yet, or one whose only pass still
    waits to count) does not outrank a verdict on another check — it is a check, not a result.
    Only when NO check has a decisive verdict does a waiting pass speak (`unfinished`); with none
    of those either the promise is `out-of-date` (it has a check; nothing has proven it live).
    """
    if not checks:
        return NO_CHECK, None
    live = checks - held
    if not live:
        return QUARANTINED, None
    # WHAT SAYS "DID NOT PASS" ANYWHERE ON THE PROMISE: a waiting pass on one check is not the
    # promise's newest word when another check failed — even uncounted — at or after it.
    live_rows = [row for check in live for row in by_check.get(check, [])]
    tainted = _tainted_runs(live_rows)
    failed_at = _newest_uncounted_fail(live_rows)
    decided_checks: list[tuple[str, dict[str, Any] | None]] = []
    waiting_only: list[tuple[str, dict[str, Any] | None]] = []
    for check in sorted(live):
        rows = by_check.get(check, [])
        one, row = check_state(rows, window, now, current, tainted, failed_at)
        if row is None:
            continue
        (decided_checks if any(_decisive(r) for r in rows) else waiting_only).append((one, row))
    readings = decided_checks or waiting_only
    if not readings:
        return OUT_OF_DATE, None
    state = PASSING
    decided: dict[str, Any] | None = None
    for one, row in readings:
        if _STRICT[one] < _STRICT[state]:
            state, decided = one, row
        elif one == state and row is not None and (decided is None or _ran_key(row) > _ran_key(decided)):
            decided = row
    return state, decided


# ─────────────────────── the outcome, trend and risk-weighted readings ───────────────────────
#
# FLT-1224: a desk measures OUTCOMES, not activity. Every figure below is counted from the rows the
# desk already holds — the verdicts and the computed promise states — so a reader gets the trend and
# the outcome with no second pipeline. FLT-1222: coverage is weighted by authored risk, not counted
# row by row. Nothing here reads a clock beyond the `now` the caller passed.

#: THE RISK WEIGHT of an area's authored tier (FLT-1222): one promise in a core-tier area is worth
#: three in a rotation area, because the core part rotates fastest and costs most to leave
#: unchecked. A parked or untiered part has no rotation of its own, so it weighs the baseline one —
#: counted, never dropped.
RISK_WEIGHT: dict[str, int] = {"core": 3}
_RISK_BASELINE = 1


def _risk_weighted(promises: list[dict[str, Any]]) -> dict[str, Any]:
    """The coverage figure weighted by each promise's authored risk (FLT-1222).

    Coverage is *has a check at all* — the same reading the Checked head line counts — weighted so
    a core-tier promise counts `RISK_WEIGHT["core"]` times a rotation one. `percent` is ``None``
    for a desk with no promises, never a division by zero.
    """
    covered = 0
    total = 0
    for row in promises:
        weight = RISK_WEIGHT.get(str(row.get("tier") or ""), _RISK_BASELINE)
        total += weight
        if row["state"] != NO_CHECK:
            covered += weight
    return {
        "covered": covered,
        "total": total,
        "percent": round(100 * covered / total) if total else None,
        "core_weight": RISK_WEIGHT["core"],
    }


def _median_fail_to_pass(by_promise: dict[str, list[dict[str, Any]]]) -> float | None:
    """The median days a promise took from a counted fail to its next counted pass.

    One interval per promise that recovered — its NEWEST fail that a later pass answered — in days,
    so a promise that failed and passed ten times counts once, on its latest recovery. A desk where
    nothing recovered has no median (``None``), never a zero.
    """
    gaps: list[float] = []
    for rows in by_promise.values():
        fail_at: str | None = None
        last: float | None = None
        for row in sorted(rows, key=_ran_key):
            if _counts_as_fail(row):
                fail_at = str(row.get("ran_at") or "")
            elif fail_at and _counts_as_pass(row):
                gap = _days_between(fail_at, str(row.get("ran_at") or ""))
                if gap is not None:
                    last = gap
                fail_at = None
        if last is not None:
            gaps.append(last)
    if not gaps:
        return None
    gaps.sort()
    middle = len(gaps) // 2
    return gaps[middle] if len(gaps) % 2 else (gaps[middle - 1] + gaps[middle]) / 2.0


def _trend(by_promise: dict[str, list[dict[str, Any]]], now: str) -> dict[str, int]:
    """The promises that recorded a counted fail this week, against the week before (FLT-1224).

    Counted by promise, not by run: five failing runs of one broken promise are one broken promise
    this week. A disputed fail is not a defect and is left out, exactly as it is on the desk.
    """
    current = _instant(now)
    if current is None:
        return {"this": 0, "prev": 0}
    this_cutoff = current - timedelta(days=7)
    prev_cutoff = current - timedelta(days=14)
    this_ids: set[str] = set()
    prev_ids: set[str] = set()
    for pid, rows in by_promise.items():
        for row in rows:
            if not _counts_as_fail(row) or _review(row) == quality_reviews.DISPUTED:
                continue
            at = _instant(str(row.get("ran_at") or ""))
            if at is None:
                continue
            if at > this_cutoff:
                this_ids.add(pid)
            elif at > prev_cutoff:
                prev_ids.add(pid)
    return {"this": len(this_ids), "prev": len(prev_ids)}


def _outcomes(
    verdicts: list[dict[str, Any]],
    by_promise: dict[str, list[dict[str, Any]]],
    promises: list[dict[str, Any]],
    counts: dict[str, int],
    now: str,
) -> dict[str, Any]:
    """The outcome line's figures (FLT-1224), each counted from the rows on the desk.

    * **flake** — checked promises in the `flaky` state (one check gave different verdicts on one
      release), over every checked promise.
    * **escaped** — promises that got worse on their release line: a defect that shipped.
    * **findings** — every counted fail the verifier has not disputed, and how many the verifier
      confirmed real (`review: verified`).
    * **median_fail_to_pass_days** — see :func:`_median_fail_to_pass`.
    * **week** — see :func:`_trend`.
    """
    checked = sum(1 for row in promises if row["state"] != NO_CHECK)
    findings = [row for row in verdicts if _counts_as_fail(row) and _review(row) != quality_reviews.DISPUTED]
    confirmed = sum(1 for row in findings if _review(row) == "verified")
    return {
        "flaky": {"count": counts.get(FLAKY, 0), "checked": checked},
        "escaped": sum(1 for row in promises if row["change"] == "worse"),
        "findings": {"total": len(findings), "confirmed": confirmed},
        "median_fail_to_pass_days": _median_fail_to_pass(by_promise),
        "week": _trend(by_promise, now),
    }


def quality_promises(inputs: dict[str, Any], now: str) -> dict[str, Any]:
    """The ``GET /api/quality/promises`` payload **minus** ``commit`` (the route adds that).

    ``inputs`` carries ``verdicts`` and ``runs`` (``read_results``), ``scenarios``
    (``read_scenarios``), ``areas`` (as ``quality_map`` takes them, with ``components``),
    ``capabilities``, ``requirements``, ``journeys`` (the served typed rows), ``coverage``
    (``criterion_capability``, ``criterion_commitments`` — `{criterion: [ids]}` — and
    ``journey_criteria`` — `{slug: [criterion ids]}`) and ``facts`` (``area_tiers``,
    ``register_components``, ``shipped_prds``, ``prd_program`` — `{prd n: program}` — and
    ``prd_claims`` — `{prd n: [requirement ids]}`). Every input may be absent; an empty corpus
    is an empty reading, never a raise. ``verifier`` is `verifier_reading`'s answer. The verifier's
    reviews arrive already laid over the verdict rows (`read_results`), so a disputed or
    not-counted verdict is settled before any state is computed.

    Returns ``promises`` (one row each, see the section comment), ``groups`` (one per feature
    area, worst first: most failing, then most flaky, then the largest share with no check),
    ``counts`` over every state, ``release`` (the release line, or None when no live result
    names one), ``release_missing`` (the one condition that fails when there is none), ``outcomes``
    (flake rate, escaped defects, confirmed-real share, median fail→pass and the week-over-week
    trend, FLT-1224), ``risk_weighted`` (the coverage figure weighted by tier, FLT-1222),
    ``facets`` (registers and programs), ``scenarios`` (one summary row each) and
    ``unplaced`` (every result row naming a promise id the catalog does not hold, BUG-1151).
    """
    catalog = _catalog(inputs)
    facts = inputs.get("facts") or {}
    tiers = {str(k): str(v or "") for k, v in (facts.get("area_tiers") or {}).items()}
    attribution = _attribution(inputs, catalog, now)
    assertions = _assertion_index(list(inputs.get("scenarios") or []))
    verdicts = list(inputs.get("verdicts") or [])
    lines = _release_lines(verdicts)
    production = _production_environment(list(inputs.get("environments") or []))
    current_by_env = _current_by_env(lines, production)
    # THE HEAD'S RELEASE LINE SPEAKS FOR PRODUCTION — the one environment record marked
    # `production: true` — and for nothing when there is none or several. A promise's own
    # worse / fixed / unchecked is read per environment against that environment's line.
    releases = lines.get(production, []) if production is not None else []
    current = releases[-1] if releases else ""
    previous = releases[-2] if len(releases) > 1 else ""

    promises: list[dict[str, Any]] = []
    for pid, meta in catalog.items():
        tier = tiers.get(str(meta["area"]), "")
        window = TIER_WINDOW_DAYS.get(tier, DEFAULT_WINDOW_DAYS)
        by_check = attribution.evidence.get(pid, {})
        all_rows = [row for rows in by_check.values() for row in rows]
        state, decided = _promise_state(
            attribution.checks.get(pid, set()), attribution.held.get(pid, set()), by_check, window, now, current_by_env
        )
        passes = [str(r.get("ran_at") or "") for r in all_rows if _counts_as_pass(r)]
        # WORSE IN ANY ENVIRONMENT IS WORSE: each environment's rows against its own line, the
        # environment named so the row can say where. Fixed only where nothing got worse.
        # A row naming no environment is read as production's, against production's line.
        judged = [(_env_of(r) or production or "", r) for r in all_rows]
        change, change_env, unchecked = "", "", False
        for env in sorted(lines):
            env_rows = [r for e, r in judged if e == env]
            one, missing = _change_on(env_rows, lines[env])
            unchecked = unchecked or (missing and env == production)
            if (one == "worse" or (one == "fixed" and change != "worse")) and change != one:
                change, change_env = one, env
        shown_env = change_env or production or ""
        shown_line = lines.get(shown_env, [])
        shown_rows = [r for e, r in judged if e == shown_env]
        readings = [{"release": r, "reading": _on_release(shown_rows, r)} for r in reversed(shown_line)]
        promises.append(
            {
                **meta,
                "state": state,
                "tier": tier,
                "window_days": window,
                "last_pass": max(passes) if passes else None,
                # The checks that prove it, a few by name and all by count, and the scenarios among
                # them — the page links each of those to its own page.
                "checks": sorted(attribution.checks.get(pid, ()))[:6],
                "check_count": len(attribution.checks.get(pid, ())),
                "scenarios": sorted(
                    {
                        str(assertions[check][0].get("id") or "")
                        for check in attribution.checks.get(pid, ())
                        if check in assertions
                    }
                ),
                "evidence": _evidence_of(decided),
                "since": _since(all_rows) if state == FAILING else "",
                "change": change,
                "change_env": change_env,
                "unchecked_on_release": unchecked,
                "releases": [r for r in readings if r["reading"]][:3],
            }
        )

    areas = list(inputs.get("areas") or [])
    order = {str(a.get("id") or ""): i for i, a in enumerate(areas)}
    names = {str(a.get("id") or ""): str(a.get("name") or "") for a in areas}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in promises:
        grouped[str(row["area"])].append(row)
    groups: list[dict[str, Any]] = []
    for aid, rows in grouped.items():
        # Register rules and capabilities first, worst first; then each journey's criteria together
        # under their journey (the page draws the journey once above them), worst first within it.
        rows.sort(
            key=lambda r: (
                r["kind"] == "criterion",
                str(r.get("journey") or ""),
                _STATE_ORDER[r["state"]],
                _criterion_order(str(r["id"])),
            )
        )
        counts = {state: sum(1 for r in rows if r["state"] == state) for state in PROMISE_STATES}
        groups.append(
            {
                "area": aid,
                "name": names.get(aid, ""),
                "tier": tiers.get(aid, ""),
                "total": len(rows),
                "checked": len(rows) - counts[NO_CHECK],
                "counts": counts,
                "ids": [r["id"] for r in rows],
            }
        )
    groups.sort(
        key=lambda g: (
            -g["counts"][FAILING],
            -g["counts"][FLAKY],
            -(g["counts"][NO_CHECK] / g["total"] if g["total"] else 0.0),
            g["area"] == UNPLACED,
            order.get(g["area"], len(order)),
            g["area"],
        )
    )
    by_id = {r["id"]: r for r in promises}
    promises = [by_id[pid] for g in groups for pid in g["ids"]]
    counts = {state: sum(1 for r in promises if r["state"] == state) for state in PROMISE_STATES}
    release_line = None
    release_missing = "" if current else _release_missing(list(inputs.get("environments") or []), production)
    if current:
        release_line = {
            "environment": production,
            "current": current,
            "previous": previous,
            "worse": sum(1 for r in promises if r["change"] == "worse"),
            "fixed": sum(1 for r in promises if r["change"] == "fixed"),
            "unchecked": sum(1 for r in promises if r["unchecked_on_release"]),
        }
    return {
        "now": now,
        "promises": promises,
        "groups": groups,
        "counts": counts,
        "total": len(promises),
        "checked": len(promises) - counts[NO_CHECK],
        "release": release_line,
        # When there is no release line, the ONE condition that is missing, in the page's words.
        "release_missing": release_missing,
        # The outcome and trend figures (FLT-1224) and the risk-weighted coverage (FLT-1222): the
        # lines behind the head's "more", counted here so a trimmed view still says them. The
        # per-promise rows come from the same attribution the states were computed from, so a
        # verdict whose promise is inferred from its assertion is still counted here.
        "outcomes": _outcomes(
            verdicts,
            {pid: [row for rows in attribution.evidence.get(pid, {}).values() for row in rows] for pid in catalog},
            promises,
            counts,
            now,
        ),
        "risk_weighted": _risk_weighted(promises),
        "facets": {
            "registers": sorted({str(r["register"]) for r in promises}),
            "programs": sorted({p for r in promises for p in r["programs"]}),
        },
        "scenarios": scenario_summaries(inputs, now),
        # Every result row the catalog cannot place (BUG-1151): it counts toward nothing, so the
        # first `UNPLACED_SHOWN` (row, unknown id) pairs are listed and the total is counted in
        # `summary.unplaced` — the page's "more" says the total, never the length of this list.
        "unplaced": attribution.unplaced[:UNPLACED_SHOWN],
        # The whole list, for the scenario page to filter (`scenario_detail(unplaced=…)`) without
        # rebuilding the attribution; `promises_view` keeps it off the wire.
        "unplaced_all": attribution.unplaced,
        # The verifier's standing word, counted for the Scenarios tab's head line.
        "verifier": {
            "disputed": len((inputs.get("verifier") or {}).get("disputed") or ()),
            "weak": len(_weak_set(inputs)),
        },
        # The two lines behind the head's "more": the core-tier areas' reading and how the
        # promises split by kind — counted here so a trimmed view (`promises_view`) still says them.
        "summary": {
            "core": {
                "total": sum(1 for r in promises if r["tier"] == "core"),
                "passing": sum(1 for r in promises if r["tier"] == "core" and r["state"] == PASSING),
            },
            "kinds": {
                kind: sum(1 for r in promises if r["kind"] == kind)
                for kind in ("requirement", "capability", "criterion")
            },
            "journeys": len({r["journey"] for r in promises if r["kind"] == "criterion"}),
            "current_line": current_line_of(inputs.get("facts")),
            "unplaced": len(attribution.unplaced),
        },
    }


#: How many unplaced (row, unknown id) pairs a reading lists; `summary.unplaced` counts them all.
UNPLACED_SHOWN = 20

#: How many rows of each long-tail state an area shows on the plain view; the rest are counted.
VIEW_TASTE: dict[str, int] = {UNFINISHED: 3, OUT_OF_DATE: 3, NO_CHECK: 2}
#: The most promise rows one view carries. A filter that matches more says how many it held back.
VIEW_LIMIT = 300


def promises_view(
    reading: dict[str, Any],
    *,
    state: str = "",
    area: str = "",
    register: str = "",
    program: str = "",
    text: str = "",
    mode: str = "",
    offset: int = 0,
    features: bool = False,
) -> dict[str, Any]:
    """The slice of a `quality_promises` reading one screen of the desk needs.

    The whole reading is thousands of rows, most of them out of date or unchecked, and the plain
    view shows only what needs a person: every failing, flaky, disputed, can't-run and quarantined
    promise, plus a taste of each area's long tail (`VIEW_TASTE`) with the rest COUNTED in the
    group's ``hidden``. A filter — one state, one area, a register, a program, words, or the
    release mode — answers every match instead, `VIEW_LIMIT` rows a page from ``offset``. Passing
    rows appear only when asked for by state, by mode, or by area: "show all" on a group is all of
    it, the passing promises too. The head (counts, release line, facets, summary, scenarios)
    is the whole reading's either way, so the numbers never shrink with the list.

    ``features=True`` answers the feature desk (PRD 0994) instead: every group comes back in tier
    order with the unplaced group last, ``ids`` only for what the query matches, no passing-row
    clause and no ``VIEW_TASTE``. A plain query matches nothing, so each group is a feature line
    and ``promises`` is empty.

    ``view`` says what was asked, how many rows matched and how many are carried.
    """
    rows: list[dict[str, Any]] = list(reading.get("promises") or [])
    by_id = {str(r["id"]): r for r in rows}
    needle = text.strip().lower()
    plain = not (state or area or register or program or needle or mode)

    def keep(p: dict[str, Any]) -> bool:
        if mode == "release" and not (p.get("change") or p.get("unchecked_on_release")):
            return False
        if state and p["state"] != state:
            return False
        if area and str(p["area"]) != (UNPLACED if area == UNPLACED_PARAM else area):
            return False
        if register and str(p["register"]) != register:
            return False
        if program and program not in (p.get("programs") or ()):
            return False
        return not needle or needle in f"{p['id']} {p['statement']}".lower()

    def keep_default(p: dict[str, Any]) -> bool:
        if not keep(p):
            return False
        return bool(state or mode or area or p["state"] != PASSING)

    keep_row = keep if features else keep_default

    groups: list[dict[str, Any]] = []
    carried: list[dict[str, Any]] = []
    matched = 0
    skip = max(0, int(offset)) if not plain else 0
    capped = False
    source_groups = reading.get("groups") or ()
    if features:
        source_groups = sorted(source_groups, key=lambda g: (g["area"] == UNPLACED, _rank(str(g["tier"]))))
    for group in source_groups:
        ids = [pid for pid in group.get("ids") or () if pid in by_id and keep_row(by_id[pid])]
        if features and plain:
            ids = []
        matched += len(ids)
        if skip:
            dropped = min(skip, len(ids))
            ids, skip = ids[dropped:], skip - dropped
        hidden: dict[str, int] = {}
        if plain and not features:
            used: dict[str, int] = defaultdict(int)
            tasted: list[str] = []
            for pid in ids:
                one = str(by_id[pid]["state"])
                cap = VIEW_TASTE.get(one)
                if cap is not None:
                    used[one] += 1
                    if used[one] > cap:
                        hidden[one] = hidden.get(one, 0) + 1
                        continue
                tasted.append(pid)
            ids = tasted
        room = max(0, VIEW_LIMIT - len(carried))
        capped = capped or len(ids) > room
        ids = ids[:room]
        if not ids and not hidden and not features:
            continue
        carried.extend(by_id[pid] for pid in ids)
        groups.append({**group, "ids": ids, "hidden": hidden})
    return {
        # The full unplaced list stays home: the screen carries the capped `unplaced` and its total.
        **{key: value for key, value in reading.items() if key != "unplaced_all"},
        "promises": carried,
        "groups": groups,
        "view": {
            "state": state,
            "area": area,
            "register": register,
            "program": program,
            "text": text.strip(),
            "mode": mode,
            "plain": plain,
            "features": features,
            "matched": matched,
            "carried": len(carried),
            "offset": max(0, int(offset)) if not plain else 0,
            # The limit cut rows off this view (on the plain view, the only way to know).
            "capped": capped,
            "limit": VIEW_LIMIT,
        },
    }


#: The four verdict words a result may carry, worst first. One run's verdicts fold to the worst.
_RESULT_VERDICTS = ("fail", "blocked", "pass", "not-applicable")
_RESULT_RANK = {word: i for i, word in enumerate(_RESULT_VERDICTS)}
#: The RFC 3339 UTC form a waiting result's `ran_at` must match before it may show.
_RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$")


def _waiting_instant(value: Any) -> datetime | None:
    """The instant a waiting result's `ran_at` names, or None unless it is RFC 3339 UTC."""
    text = value if isinstance(value, str) else ""
    if not _RFC3339_UTC_RE.match(text):
        return None
    return _instant(text)


def waiting_files(nodes: Iterable[dict[str, Any]], prefix: str, limit: int) -> tuple[list[dict[str, Any]], bool]:
    """The result files an open pull request list adds or changes, newest first.

    Keeps a `.json` path under ``prefix`` that is not deleted, on a pull request that is not a
    cross-repository fork. ``cut`` is true when a file list was cut or ``limit`` was reached.
    Pure: it reads the GraphQL nodes and writes nothing (PRD 0994).
    """
    files: list[dict[str, Any]] = []
    cut = False
    for node in nodes:
        if node.get("isCrossRepository") is True:
            continue
        payload = node.get("files") or {}
        page_info = payload.get("pageInfo") or {}
        if page_info.get("hasNextPage") is True:
            cut = True
        for item in payload.get("nodes") or ():
            path = str(item.get("path") or "")
            if not path.startswith(prefix) or not path.endswith(".json"):
                continue
            if str(item.get("changeType") or "") == "DELETED":
                continue
            if len(files) >= limit:
                cut = True
                continue
            files.append(
                {
                    "number": node.get("number"),
                    "url": str(node.get("url") or ""),
                    "head": str(node.get("headRefOid") or ""),
                    "path": path,
                }
            )
            if len(files) >= limit:
                cut = True
    return files, cut


def _newer_than_decided(ran_at: datetime, promise: dict[str, Any]) -> bool:
    """A waiting run shows only when it ran later than the result that decided the promise.

    The deciding instants are the promise's ``evidence.ran_at`` and its ``last_pass``; a promise
    with neither has no deciding result, so any run shows (PRD 0994, fork 9).
    """
    evidence = promise.get("evidence")
    decided = _instant(evidence.get("ran_at")) if isinstance(evidence, dict) else None
    last_pass = _instant(promise.get("last_pass"))
    return all(ran_at > one for one in (decided, last_pass) if one is not None)


def _waiting_qualifier(row: dict[str, Any]) -> str:
    """Why a waiting verdict cannot count yet: ``code-only``, ``unfinished``, ``no-evidence`` or
    empty when nothing holds it back (PRD 0994)."""
    if str(row.get("environment") or "") == "code-only":
        return "code-only"
    if row.get("finished") is not True:
        return "unfinished"
    if not _has_evidence(row):
        return "no-evidence"
    return ""


def waiting_results(promises: Iterable[dict[str, Any]], pulled: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The newer results waiting in open pull requests, one verdict per promise.

    ``promises`` is the reading's rows; ``pulled`` is ``[{number, url, path, text}]``. For each
    file it runs :func:`parse_result` and :func:`result_rows`. A row places on its ``promise``
    when the reading holds that id, otherwise on its ``id`` when the reading holds that id,
    otherwise on nothing. A run's verdicts for one promise fold to the worst; a run shows only
    when it ran later than the promise's ``evidence.ran_at`` and ``last_pass``; among runs the
    newest wins. It answers ``{promise: {verdict, qualifier, ranAt, pr, url}}`` and changes
    neither argument (PRD 0994).
    """
    rows = {str(row.get("id") or ""): row for row in promises}
    waiting: dict[str, dict[str, Any]] = {}
    for file in pulled:
        data = parse_result(str(file.get("text") or ""))
        if data is None:
            continue
        _run, verdicts = result_rows(data, str(file.get("path") or ""))
        folded: dict[str, tuple[str, dict[str, Any], datetime]] = {}
        for row in verdicts:
            verdict = str(row.get("verdict") or "")
            ran_at = _waiting_instant(row.get("ran_at"))
            if verdict not in _RESULT_RANK or ran_at is None:
                continue
            named = str(row.get("promise") or "")
            target = ""
            if named and named in rows:
                target = named
            elif str(row.get("id") or "") in rows:
                target = str(row.get("id") or "")
            if not target:
                continue
            seen = folded.get(target)
            if seen is None or _RESULT_RANK[verdict] < _RESULT_RANK[seen[0]]:
                folded[target] = (verdict, row, ran_at)
        for target, (verdict, row, ran_at) in folded.items():
            if not _newer_than_decided(ran_at, rows[target]):
                continue
            current = waiting.get(target)
            current_at = _instant(str(current["ranAt"])) if current is not None else None
            if current_at is not None and current_at >= ran_at:
                continue
            waiting[target] = {
                "verdict": verdict,
                "qualifier": _waiting_qualifier(row),
                "ranAt": str(row.get("ran_at") or ""),
                "pr": file.get("number"),
                "url": str(file.get("url") or ""),
            }
    return waiting


def _run_reading(verdicts: list[dict[str, Any]]) -> str:
    """One run's reading over its verdicts: `failing`, `passing`, `unfinished` (it ran and passed
    with evidence, but nothing it said counts yet) or `not-run` (nothing on the record counts)."""
    if any(_counts_as_fail(v) for v in verdicts):
        return FAILING
    if any(_counts_as_pass(v) for v in verdicts):
        return PASSING
    if any(_is_unfinished_pass(v) for v in verdicts) and not any(_is_uncounted_fail(v) for v in verdicts):
        return UNFINISHED
    return "not-run"


def _run_not_counted(verdicts: list[dict[str, Any]]) -> str:
    """Why a run whose verdicts all fail to count does not count: its reasons, once each."""
    if any(_counts_as_pass(v) or _counts_as_fail(v) for v in verdicts):
        return ""
    seen: list[str] = []
    for row in verdicts:
        for reason in _not_counted_reasons(row):
            if reason not in seen:
                seen.append(reason)
    return " · ".join(seen)


def _scenario_runs(inputs: dict[str, Any], scenario_id: str) -> list[dict[str, Any]]:
    """A scenario's result files, newest first, each with its verdict rows and a reading."""
    files: dict[str, dict[str, Any]] = {}
    for run in inputs.get("runs") or ():
        if str(run.get("kind") or "") != "scenario" or str(run.get("target") or "") != scenario_id:
            continue
        files[str(run.get("file") or "")] = {"run": run, "verdicts": []}
    for row in inputs.get("verdicts") or ():
        entry = files.get(str(row.get("file") or ""))
        if entry is not None and str(row.get("target") or "") == scenario_id:
            entry["verdicts"].append(row)
    out: list[dict[str, Any]] = []
    for path, entry in files.items():
        run, rows = entry["run"], entry["verdicts"]
        tally = {key: sum(1 for r in rows if str(r.get("verdict") or "") == key) for key in ("pass", "fail", "blocked")}
        causes = sorted({str(r.get("cause")) for r in rows if r.get("cause") and str(r.get("verdict")) == "fail"})
        out.append(
            {
                "file": path,
                "ran_at": str(run.get("ran_at") or ""),
                "commit": str(run.get("commit") or ""),
                "environment": str(run.get("environment") or ""),
                "environment_id": str(run.get("environment_id") or ""),
                "release": str(run.get("release") or ""),
                "scenario_version": str(run.get("scenario_version") or ""),
                "finished": run.get("finished") is True,
                "tally": tally,
                "causes": causes,
                "reading": _run_reading(rows),
                # Why nothing this run said counts, when that is so — the run dot's own words.
                "not_counted": _run_not_counted(rows),
                "verdicts": rows,
            }
        )
    out.sort(key=lambda r: (r["ran_at"], r["file"]), reverse=True)
    return out


@dataclass(frozen=True, slots=True)
class ApprovedVersion:
    """A scenario version the verifier approved whose latest run passed every assertion.

    `promises` are the promises its assertions name, unique, in file order (or the scenario's
    `proves` when no assertion names one). It is the candidate a QA-written test is filed for.
    """

    scenario: str
    version: int
    promises: tuple[str, ...]


def _review_is_disputed(row: Mapping[str, Any]) -> bool:
    return row.get("review") == "disputed" or _review(dict(row)) == "disputed"


def _oracle_approved(verifier: Mapping[str, Any] | None, scenario: str, version: int) -> bool:
    for entry in (verifier or {}).get("oracles") or ():
        if not isinstance(entry, Mapping):
            continue
        if str(entry.get("scenario") or "") != scenario:
            continue
        if _version_number(entry.get("version")) != version:
            continue
        if str(entry.get("state") or "") == "approved":
            return True
    return False


def _proved_promises(scenario: Mapping[str, Any]) -> tuple[str, ...]:
    found: list[str] = []
    for assertion in scenario.get("assertions") or ():
        if not isinstance(assertion, Mapping):
            continue
        promise = str(assertion.get("promise") or "").strip()
        if promise and promise not in found:
            found.append(promise)
    if found:
        return tuple(found)
    for promise in scenario.get("proves") or ():
        text = str(promise).strip()
        if text and text not in found:
            found.append(text)
    return tuple(found)


def approved_versions(
    runs: Iterable[Mapping[str, Any]],
    verdicts: Iterable[Mapping[str, Any]],
    scenarios: Iterable[Mapping[str, Any]],
    verifier: Mapping[str, Any] | None,
    now: str,
) -> list[ApprovedVersion]:
    """Every scenario version a QA-written test may be filed for, sorted by scenario id.

    A version qualifies only when its record names a whole positive `version`, the verifier's
    oracles approve that exact version, its latest run names the same version and finished, and
    every assertion has a `pass` row there that is neither disputed nor set aside. A quarantined
    scenario never qualifies. Pure and total: a malformed row is skipped, never raised on.
    """
    inputs = {"runs": list(runs), "verdicts": list(verdicts)}
    out: list[ApprovedVersion] = []
    for scenario in scenarios:
        if not isinstance(scenario, Mapping):
            continue
        sid = str(scenario.get("id") or "")
        version = scenario.get("version")
        if not sid or isinstance(version, bool) or not isinstance(version, int) or version <= 0:
            continue
        if quarantine_active(scenario.get("quarantine"), now):
            continue
        if not _oracle_approved(verifier, sid, version):
            continue
        scenario_runs = _scenario_runs(inputs, sid)
        if not scenario_runs:
            continue
        latest = scenario_runs[0]
        if latest.get("finished") is not True:
            continue
        if _version_number(latest.get("scenario_version")) != version:
            continue
        qualified = True
        for assertion in scenario.get("assertions") or ():
            aid = str(assertion.get("id") or "") if isinstance(assertion, Mapping) else ""
            passes = [
                row
                for row in latest["verdicts"]
                if str(row.get("id") or "") == aid and str(row.get("verdict") or "") == "pass"
            ]
            if not passes or any(_review_is_disputed(row) or row.get("not_counted") for row in passes):
                qualified = False
                break
        if qualified:
            out.append(ApprovedVersion(sid, version, _proved_promises(scenario)))
    out.sort(key=lambda candidate: candidate.scenario)
    return out


def _scenario_state(
    scenario: dict[str, Any], runs: list[dict[str, Any]], now: str
) -> tuple[str, dict[str, tuple[str, dict[str, Any] | None]]]:
    """A scenario's own state over its assertions, and each assertion's `(state, deciding row)`."""
    per: dict[str, tuple[str, dict[str, Any] | None]] = {}
    rows_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        for row in run["verdicts"]:
            # A superseded version's row is the scenario's history, never its state (BUG-1185).
            if not _is_superseded(row, scenario.get("version")):
                rows_by[str(row.get("id") or "")].append(row)
    every = [row for rows in rows_by.values() for row in rows]
    tainted = _tainted_runs(every)
    failed_at = _newest_uncounted_fail(every)
    for assertion in scenario.get("assertions") or ():
        aid = str(assertion.get("id") or "")
        per[aid] = check_state(rows_by.get(aid, []), DEFAULT_WINDOW_DAYS, now, None, tainted, failed_at)
    if quarantine_active(scenario.get("quarantine"), now):
        return QUARANTINED, per
    decided = [one for one, row in per.values() if row is not None]
    if not runs or not decided:
        return OUT_OF_DATE, per
    state = PASSING
    for one in decided:
        if _STRICT[one] < _STRICT[state]:
            state = one
    return state, per


def scenario_summaries(inputs: dict[str, Any], now: str) -> list[dict[str, Any]]:
    """One row per scenario record for the Scenarios list: its state, where and which version it
    last ran, the verifier's marks on its latest verdicts and its last five runs' readings."""
    weak = _weak_set(inputs)
    out: list[dict[str, Any]] = []
    for scenario in inputs.get("scenarios") or ():
        sid = str(scenario.get("id") or "")
        runs = _scenario_runs(inputs, sid)
        state, per = _scenario_state(scenario, runs, now)
        latest = runs[0] if runs else None
        reviews: dict[str, int] = defaultdict(int)
        for _one, row in per.values():
            mark = _review(row) if row is not None else ""
            if mark:
                reviews[mark] += 1
        held = quarantine_active(scenario.get("quarantine"), now)
        out.append(
            {
                "id": sid,
                "name": str(scenario.get("name") or sid),
                "summary": str(scenario.get("summary") or ""),
                "state": state,
                "proves": [str(p) for p in scenario.get("proves") or ()],
                "references": [str(r) for r in scenario.get("references") or ()],
                "assertions": len(scenario.get("assertions") or ()),
                "version": latest["scenario_version"] if latest else "",
                "environment_id": latest["environment_id"] if latest else "",
                "release": latest["release"] if latest else "",
                "latest_run": latest["ran_at"] if latest else None,
                "reviews": dict(reviews),
                "history": [r["reading"] for r in reversed(runs[:5])],
                "history_why": [r["not_counted"] for r in reversed(runs[:5])],
                "quarantine": dict(scenario["quarantine"]) if held else None,
                "weak": _weak_of(weak, sid),
            }
        )
    out.sort(key=lambda r: (_STATE_ORDER.get(r["state"], 99), r["id"]))
    return out


def scenario_detail(
    inputs: dict[str, Any], scenario_id: str, now: str, *, unplaced: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """One scenario's page: what it exercises, its setup and steps, each expected result with the
    promise it proves and its latest evidence, and its runs, newest first.

    ``findings`` holds this scenario's UNPLACED rows (BUG-1151): each result row that names a
    promise the desk's catalog does not hold, as ``{kind: "unplaced", assertion, promise, file,
    reason, audit_key: ""}``. They file no ticket, so they carry no audit key; the route appends
    them to the trace's own FAIL findings. ``unplaced`` is a promises reading's ``unplaced_all``,
    passed by a caller that already holds one so the attribution is not rebuilt per page; omitted,
    it is computed here.

    An unknown id answers ``{"id": …, "found": False}``, never a raise.
    """
    scenario = next((s for s in inputs.get("scenarios") or () if str(s.get("id")) == scenario_id), None)
    if scenario is None:
        return {"id": scenario_id, "found": False}
    runs = _scenario_runs(inputs, scenario_id)
    state, per = _scenario_state(scenario, runs, now)
    proves = [str(p) for p in scenario.get("proves") or ()]
    assertions: list[dict[str, Any]] = []
    for n, assertion in enumerate(scenario.get("assertions") or (), start=1):
        aid = str(assertion.get("id") or "")
        one, row = per.get(aid, (OUT_OF_DATE, None))
        # The current version's own rows only, and its Promise cell first (BUG-1185): a superseded
        # run is on the run list as history, never this assertion's evidence or its promise.
        latest_any = max(
            (
                v
                for run in runs
                for v in run["verdicts"]
                if str(v.get("id") or "") == aid and not _is_superseded(v, scenario.get("version"))
            ),
            key=_ran_key,
            default=None,
        )
        promise = str(assertion.get("promise") or (row or latest_any or {}).get("promise") or "")
        assertions.append(
            {
                "id": aid,
                "n": n,
                "text": str(assertion.get("text") or ""),
                "promise": promise,
                "promises": [promise] if promise else proves,
                "expected": str(assertion.get("expected") or ""),
                "state": one,
                "evidence": _evidence_of(row if row is not None else latest_any),
            }
        )
    held = quarantine_active(scenario.get("quarantine"), now)
    return {
        "id": scenario_id,
        "found": True,
        "name": str(scenario.get("name") or scenario_id),
        "summary": str(scenario.get("summary") or ""),
        "state": state,
        "file": str(scenario.get("file") or ""),
        "owning_prd": str(scenario.get("owning_prd") or ""),
        "proves": proves,
        "references": [str(r) for r in scenario.get("references") or ()],
        "setup": [list(p) for p in scenario.get("setup") or ()],
        "steps": [str(s) for s in scenario.get("steps") or ()],
        "quarantine": dict(scenario["quarantine"]) if held else None,
        "weak": _weak_of(_weak_set(inputs), scenario_id),
        "oracle": _oracle_of(runs),
        "assertions": assertions,
        "runs": [{k: v for k, v in run.items() if k != "verdicts"} for run in runs],
        "findings": _unplaced_findings(
            _attribution(inputs, _catalog(inputs), now).unplaced if unplaced is None else unplaced, scenario_id
        ),
    }


def _unplaced_findings(unplaced: list[dict[str, Any]], scenario_id: str) -> list[dict[str, Any]]:
    """This scenario's unplaced (row, id) pairs, as desk findings."""
    own = f"{scenario_id}#"
    return [
        {
            "kind": "unplaced",
            "assertion": u["row"],
            "promise": u["promise"],
            "file": u["file"],
            "rows": u["rows"],
            "reason": (
                f"names `{u['promise']}`, which is no promise the desk holds, so this row counts toward nothing"
                if u["promise"]
                else "names no promise and its scenario proves none, so this row counts toward nothing"
            ),
            "audit_key": "",
        }
        for u in unplaced
        if u["row"].startswith(own)
    ]


def _weak_of(weak: dict[str, Any], scenario_id: str) -> dict[str, Any] | None:
    """The planted bug this scenario let through, or None (FLT-1215)."""
    outcome = weak.get(scenario_id)
    if not isinstance(outcome, dict):
        return None
    return {"at": str(outcome.get("at") or ""), "mutation": str(outcome.get("mutation") or "")}


def _oracle_of(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Whether the verifier approved the expected results the latest run was graded against:
    `{version, state}` with state `approved` / `pending` / `rejected` / `changed`, or None when
    the latest run carries no verifier word (FLT-1214)."""
    for run in runs:
        for row in run["verdicts"]:
            if row.get("oracle"):
                return {"version": str(row.get("scenario_version") or ""), "state": str(row["oracle"])}
        if run["verdicts"]:
            return None
    return None


# ─────────────────────── the corpus's promise ids, read from disk (BUG-1151) ───────────────────────
#
# The acceptance-criteria grammar a journey criterion's id is derived under: a `1. …` flow row or a
# `- **A1** …` map row, under ANY H2 naming "Acceptance criteria", numbered by position across every
# such section — `<journey>#<n>`, PRD 0774 design D4. ONE copy: the served reading
# (`fleet_service.qualityreading.ac_criteria`) and the writer's warning both read it from here.
AC_HEADING_RE = re.compile(r"^##\s+[^\n]*[Aa]cceptance criteria\b[^\n]*$", re.M)
AC_ROW_RE = re.compile(r"^(?:\d+\.\s|-\s+\*\*[A-Z]?\d)")
NEXT_H2_RE = re.compile(r"^##\s", re.M)
#: A journey's frontmatter saying it was retired: it is history, and promises nothing today.
JOURNEY_RETIRED_RE = re.compile(r"^status:\s*retired\s*$", re.M)


def journey_criterion_ids(slug: str, text: str) -> list[str]:
    """Every criterion id a journey file carries, in file order — retired journey or not."""
    count = 0
    for heading in AC_HEADING_RE.finditer(text):
        section = text[heading.end() :]
        end = NEXT_H2_RE.search(section)
        body = section[: end.start()] if end else section
        count += sum(1 for line in body.splitlines() if AC_ROW_RE.match(line))
    return [f"{slug}#{n}" for n in range(1, count + 1)]


def scenario_citation_problems(
    scenario: Mapping[str, Any],
    journey_ids: Collection[str],
    required: Collection[str] = (),
) -> list[str]:
    """The citation problems of one scenario row, in the shape `read_scenarios` serves.

    A scenario proves a journey by naming a STEP of it (`<journey>#<n>`), never the journey
    itself: the desk counts each criterion on its own row, and a bare journey id places nowhere.
    Every entry in ``proves`` or in an assertion's ``promise`` that equals a journey id is
    reported once per (scenario, id). Every id in ``required`` — the promise and riders a run
    records — must have an assertion row of its own; ``proves`` does not stand in for one.

    Pure: it reads the mapping it is given, calls nothing, and writes nothing.
    """
    journeys = {str(jid) for jid in journey_ids}
    assertions = [a for a in scenario.get("assertions") or () if isinstance(a, Mapping)]
    cited = [str(entry) for entry in scenario.get("proves") or ()]
    cited += [str(a["promise"]) for a in assertions if a.get("promise")]
    problems: list[str] = []
    seen: set[str] = set()
    for cid in cited:
        if cid in journeys and cid not in seen:
            seen.add(cid)
            problems.append(f"cites journey {cid!r} with no step number, and only a step counts on the Quality desk")
    promised = {str(a["promise"]) for a in assertions if a.get("promise")}
    missing: set[str] = set()
    for rid in required:
        rid = str(rid)
        if rid not in promised and rid not in missing:
            missing.add(rid)
            problems.append(f"has no assertion row for {rid!r}")
    return problems


def corpus_promise_ids(
    knowledge: Path,
    *,
    requirements_dir: str = "requirements",
    features_dir: str = "features",
    journeys_dir: str = "journeys",
    capability_prefix: str = "CAP",
    aliases_file: str = "capability-aliases.md",
) -> set[str]:
    """Every id a result's `promise` may name and be placed by, read from a corpus on disk: each
    register row id, each capability id in the feature maps, and each criterion of a journey that
    is not retired. A SUPERSET of the desk's catalog — a deferred row or an unshipped capability is
    here and not there, because only the served reading knows what has shipped — so a writer that
    warns on an id outside it never cries wolf; the desk's own `unplaced` list says the rest."""
    from . import (
        corpus,  # noqa: PLC0415 — the corpus readers are heavy and only this needs them
        requirements,  # noqa: PLC0415
    )

    rows, _findings = requirements.load_registers(knowledge, dir_name=requirements_dir)
    ids = set(rows)
    for area in corpus.features(
        knowledge, features_dir=features_dir, aliases_file=aliases_file, capability_prefix=capability_prefix
    ):
        ids |= {str(cap.get("id") or "") for cap in area.get("caps") or ()}
    for path, _tier in corpus.journey_files(knowledge, journeys_dir):
        text = path.read_text(encoding="utf-8")
        if not JOURNEY_RETIRED_RE.search(md.frontmatter(text)):
            ids |= set(journey_criterion_ids(path.stem, text))
    ids.discard("")
    return ids

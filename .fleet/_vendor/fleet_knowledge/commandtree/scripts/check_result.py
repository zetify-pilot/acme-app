#!/usr/bin/env python3
"""Write the one check-result file an audit run leaves behind (PRD 0774, Gap G3).

Every audit run ends by writing **one append-only JSON file per run** under
`knowledge/audits/results/<kind>/<YYYY-MM-DD>-<scope-slug>-<HHMMSS>Z.json`, recording one
verdict per journey acceptance criterion, per checklist item or per scenario assertion. That
file is the fact the Quality desk's map is composed from: `fleet_knowledge.quality.read_results`
reads this home, and neither it nor the consuming repository's own commit-time result gate
invents the shape — this writer produces the one both consume. Before it, every run left a
record and no result, so a briefed check could not change its map square (PRD 0771 AC-3).

## Schema version 1 — the eight keys

  * `schema_version` — integer, `1` (or `2`, below).
  * `kind` — the check's kind; equals the file's parent directory (a slot `kinds:` entry).
  * `target` — the thing or capability ids the run looked at, comma-separated when it covered
    several (`CAP-0001,CAP-0002`, `sync`). The Quality desk places a checklist verdict on exactly
    these ids, so a free-text scope (`"full REST surface"`) can never place and is refused here.
  * `commit` — the code commit the run was against.
  * `environment` — `live` (the running product) or `code-only` (a source read only).
  * `finished` — boolean; whether the run completed.
  * `ran_at` — RFC3339 UTC instant the run started driving the product (`--at`; the write time
    when the run names none), so the evidence says when the product was observed. Refused when it
    is unparseable, later than now by more than `AT_SKEW`, or earlier than now by more than
    `AT_MAX_AGE` (a backdated result would otherwise reorder which run reads as the latest).
  * `verdicts` — a list of `{id, verdict, reason?}`, `verdict` one of `pass`, `fail`,
    `blocked`, `not-applicable`; `reason` required (non-empty) on `blocked` and
    `not-applicable`; an `id` at most once per file.

`id` is the engine's stable name: a journey criterion `<journey-id>#<n>` (the 1-based
ordinal in the journey's `## Acceptance criteria` list), a checklist item `<kind>/<item-id>`
(e.g. `security/SEC3`, `ui/V0`, `ux/IA1`) or a scenario assertion `<scenario-id>#<n>`.

## Schema version 2 — evidence, release, review

A v1 file stays valid forever (results are append-only). The writer emits `schema_version: 2`
the moment **any** v2 field is given, and v1 otherwise. v2 adds, at the top level:

  * `environment_id` — the environment record the run drove (`knowledge/environments/<id>.json`);
    it must resolve, and it implies `environment: live`.
  * `release` — the deployed version the run observed; required with `environment_id`. When
    the environment's version probe is unknown (the record's `version_probe` is null, or the
    run passes `--release unknown`), the run is written `finished: false`: a verdict against a
    build nobody can name is recorded, never counted. **A run need not remember it:** when
    `--release` is absent and the run names an environment, the writer takes the release from
    `FLEET_RELEASE` (`RELEASE_ENV`), which the daemon exports into every dispatched run from
    the release its environment is deployed from (ENG-19900). An explicit `--release` always
    wins, and the run is still refused when the environment is named and neither names a build.
  * `scenario_version` — the scenario record's integer `version:` the run walked (kind
    `scenario` only; required on a scenario run against an environment).
  * `scenario_sha256` — written with `scenario_version`: the sha256 of the scenario file's bytes
    (`knowledge/scenarios/<target>.md`) as the run walked it. `commit` names the code the run was
    against, which need not contain the scenario — a new scenario lands in the same PR as its first
    result — so the hash is what ties a result to the exact text it walked. The writer refuses when
    that file is absent or not at `--scenario-version`.
  * `runner` — the run id of the session that ran the check; **required with
    `environment_id`**. The verifier refuses to review a result whose `runner` is its own run
    id, so the party that ran a check never certifies it. `runner` is also allowed on a v1 file
    (it does not by itself make the file v2), because who ran a check is a fact of any run.

and, per verdict — optional on a run with no environment, but **required against one**: when
`environment_id` is set every verdict carries `promise` and `attempts`, and every `fail` /
`blocked` carries `cause` (results are append-only, so an optional field now would be a v3
later):

  * `promise` — the ONE promise id the assertion proves: a requirement row id (`FLT-1157`), a
    `CAP-NNNN`, a journey id, or one criterion of a journey (`run-agent#3`, FLT-1202) — cite
    the criterion, which the desk counts on its own row, rather than the whole journey.
  * `expected`, `observed` — short structured one-line strings (`refused 403 ceiling_exceeded`);
    **required on every v2 verdict**, environment or not (FLT-1211).
  * `evidence` — `{request_ids: [..], audit_ids: [..], snapshot: <hash>}`: the platform's own
    request ids, the audit-log row ids of a governed action or refusal, and/or a snapshot hash.
  * `attempts` — `"n/m"`: the attempt that produced the verdict out of the attempts made.
  * `cause` — `product` | `agent` | `environment` | `inconclusive`; only on `fail`/`blocked`.
  * `ticket` — the tracker key of the finding a `fail`/`blocked` filed (`BUG-1178`, `ENG-12345`),
    so the Quality desk's promise unfold can name the ticket beside the failure's cause. It is the
    stable reference the desk prints; whether that ticket is still open is the tracker's fact, not
    one a result file stores (FLT-1221).
  * `review` — `{state: verified|unverified|disputed, at: RFC3339}`; `state` defaults to
    `unverified` and a `verified`/`disputed` state needs its `at`.
  * `new` — boolean; the verdict is a regression/finding not seen on the previous run.

The rule that makes v2 worth having: **a `pass` with no evidence is not a pass.** In a v2 file
a `pass` that carries no request id, no audit id and no snapshot is written as `blocked` with
the reason `no evidence` and `cause: inconclusive` (the writer says so on stderr) — a run
that says it saw something must show what it saw. `cause` on a `pass` is refused.

Usage:

    python3 knowledge/scripts/check_result.py write --kind security --target agents \\
        --environment live --finished \\
        --verdict 'connections#3=pass' --verdict 'security/SEC3=fail' \\
        --reason 'security/SEC3=customer token echoed in the response'

    python3 knowledge/scripts/check_result.py write --kind scenario --target procurement-flow \\
        --environment live --environment-id e2e-prod --release 0.7.153 --scenario-version 2 \\
        --runner {this-session-run-id} \\
        --verdict 'procurement-flow#1=pass' --promise 'procurement-flow#1=FLT-1157' \\
        --expected 'procurement-flow#1=mail delivered' --observed 'procurement-flow#1=mail delivered' \\
        --request-id 'procurement-flow#1=req_01J...' --audit-id 'procurement-flow#1=01a0...' \\
        --attempts 'procurement-flow#1=1/1'

`--verdict ID=VERDICT` adds one verdict; `--reason ID=TEXT` attaches a reason, and every other
per-verdict flag (`--promise`, `--expected`, `--observed`, `--request-id`, `--audit-id`,
`--snapshot`, `--attempts`, `--cause`, `--ticket`, `--review`, `--reviewed-at`, `--new`) attaches
its field
the same way — each refused when it names an id no `--verdict` or `--verdict-file` declared.
Pass `--verdict-file PATH` for a JSON list of verdict objects carrying any of those keys.
`--commit` defaults to this checkout's `HEAD`; `--scope` defaults to `--target`; `--root` and
`--at` exist so tests can run the writer against a fixture. The file is written only after the
whole shape validates: a refusal prints `check_result: …` to stderr, writes nothing, and exits 1.

`--blocked-environment '<sentence>'` is for a QA run whose fresh copy never came up: every
declared row is written `blocked`, cause `environment`, reason the sentence, with no `attempts`
(the run made no attempt), and the run `finished: false`. The rest of the shape is validated as
usual, and a refusal writes nothing.

Stdlib only, like every sibling: it runs under a bare `python3` from a checkout that has
only this directory synced into it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

UTC = timezone.utc

RESULTS_SUBDIR = "knowledge/audits/results"
SCENARIOS_SUBDIR = "knowledge/scenarios"
ENVIRONMENTS_SUBDIR = "knowledge/environments"
SCHEMA_VERSION = 1
SCHEMA_VERSION_V2 = 2
ENVIRONMENTS = ("live", "code-only")
VERDICTS = ("pass", "fail", "blocked", "not-applicable")
REASON_REQUIRED = ("blocked", "not-applicable")
CAUSES = ("product", "agent", "environment", "inconclusive")
CAUSE_ALLOWED = ("fail", "blocked")
#: The cause the writer stamps on a pass it records as blocked for want of evidence.
CAUSE_NO_EVIDENCE = "inconclusive"
#: The cause every row of a run whose fresh copy never came up records: the environment, not the
#: product, and no attempt was made (`--blocked-environment`).
CAUSE_BLOCKED_ENVIRONMENT = "environment"
#: A `ticket` is the tracker key of the finding a fail (or a blocked run) filed, so the desk can
#: name it beside the cause (FLT-1221). Only a failing/blocked verdict files a finding.
TICKET_ALLOWED = ("fail", "blocked")
REVIEW_STATES = ("verified", "unverified", "disputed")
REVIEW_DEFAULT = "unverified"
#: The `release` a run writes when the environment's version probe could not name the build.
RELEASE_UNKNOWN = "unknown"
#: The environment variable the daemon exports into a dispatched run naming the release its
#: environment is deployed from. `--release` absent on a run that names an environment takes this
#: value, so a QA or audit run records the build the system knows instead of one the agent
#: remembered to pass (ENG-19900). The daemon sets it; a plain hand run leaves it unset.
RELEASE_ENV = "FLEET_RELEASE"
#: How far past now a stated `--at` may sit before it is refused as the future: room for clock
#: skew between the box that drove the product and the one writing, nothing more.
AT_SKEW = timedelta(minutes=2)
#: How far before now a stated `--at` may sit: a run writes its result the same day it drives the
#: product. Older is refused, because `ran_at` orders the desk's "latest" verdict and a backdated
#: result could slide under — or over — the run that really came last.
AT_MAX_AGE = timedelta(hours=24)
#: The reason a `pass` with no evidence is recorded under, as `blocked`.
NO_EVIDENCE_REASON = "no evidence"

#: The top-level keys that make a file v2, and the per-verdict ones.
V2_TOP_KEYS = ("environment_id", "release", "scenario_version")
V2_VERDICT_KEYS = ("promise", "expected", "observed", "evidence", "attempts", "cause", "ticket", "review", "new")

#: A kind is a slot entry name: lowercase, hyphenated, no separator that could carry a path.
_KIND_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
#: An environment record id — the filename stem under `knowledge/environments/`.
_ENV_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
#: A release as the version probe names it: a semver, a tag, an image digest, a commit.
_RELEASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+:/@-]*$")
#: One promise id: a requirement row / capability id (`FLT-1157`, `CAP-0001`), a journey slug, or
#: one criterion of a journey, `<journey>#<n>` with n >= 1 — the id the desk derives for a journey's
#: n-th acceptance criterion (`fleet_service/qualityreading.py`, `ac_criteria`) and counts as a promise of its
#: own (FLT-1202, FLT-1210). Without it a run could only cite the whole journey, which the desk
#: rolls up to no row at all.
_PROMISE_RE = re.compile(r"^(?:[A-Z][A-Z0-9]*-\d+|[a-z0-9][a-z0-9-]*(?:#[1-9]\d*)?)$")
#: One evidence id (a request id, an audit-log row id) or a snapshot hash: a single token.
_EVIDENCE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+=-]*$")
#: A run id: one token (the fleet's run ids are UUIDs or slugs), never prose.
_RUNNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
_ATTEMPTS_RE = re.compile(r"^([1-9]\d*)/([1-9]\d*)$")
#: One tracker key — the finding a fail filed (`BUG-1178`, `ENG-12345`): a team prefix and a
#: number. A result records the key, never free text or a URL, so the desk prints what the tracker
#: filed (FLT-1221).
_TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
#: `expected` / `observed` are short structured strings, not narrative.
_SHORT_TEXT_MAX = 200

#: A placeable `target`: one thing/capability id (a `CAP-NNNN`, an area/component/connector/
#: customer-system id, a journey slug) — never free text. The Quality desk's `_place` matches a
#: checklist verdict's target against the served capability and typed-thing ids, so a target of
#: prose (`"full REST surface (802 ops)"`) can never place. The writer refuses one here, at the
#: source, because a silent unplaceable target is how the desk read "no progress" over 18 results.
_TARGET_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


class CheckResultError(Exception):
    """A malformed result the writer refuses to put on disk."""


def slugify(text: str) -> str:
    """A filename-safe scope slug: lowercase, non-alphanumeric runs collapsed to `-`."""
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-")


#: An RFC3339 instant, checked by an explicit pattern BEFORE `datetime.fromisoformat` sees it, so
#: the verdict cannot depend on the interpreter: Python 3.14's `fromisoformat` accepts `T24:00` and
#: rolls it into the next day, 3.12's refuses it (BUG-1118). Hour 00-23, minute and second 00-59.
_RFC3339_RE = re.compile(
    r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,9})?"
    r"(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)


def parse_utc(instant: str) -> datetime:
    """An RFC3339 instant (trailing `Z` accepted) as an aware UTC datetime.

    Raises `ValueError` on anything the explicit pattern refuses (`T24:00:00Z` among them),
    whatever this interpreter's `fromisoformat` would have accepted.
    """
    text = instant.strip()
    if not _RFC3339_RE.match(text):
        raise ValueError(f"not an RFC3339 instant (YYYY-MM-DDTHH:MM:SSZ, hour 00-23): {instant!r}")
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def rfc3339(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def result_path(root: Path, kind: str, scope_slug: str, at: datetime) -> Path:
    """The D1 home and filename: `<kind>/<YYYY-MM-DD>-<scope-slug>-<HHMMSS>Z.json`."""
    utc = at.astimezone(UTC)
    return root / RESULTS_SUBDIR / kind / f"{utc.strftime('%Y-%m-%d')}-{scope_slug}-{utc.strftime('%H%M%S')}Z.json"


def head_commit(root: Path) -> str:
    """`HEAD` of the checkout, or a refusal — a result with no commit is untrustworthy."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise CheckResultError(f"cannot read HEAD in {root} — pass --commit: {exc}") from exc
    if not out:
        raise CheckResultError(f"cannot read HEAD in {root} — pass --commit")
    return out


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _frontmatter_version(text: str) -> int | None:
    """The scenario record's frontmatter `version:` as a positive integer, or None."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "version":
            raw = value.strip().strip("'\"")
            return int(raw) if raw.isdigit() and int(raw) > 0 else None
    return None


def scenario_digest(root: Path, scenario: str, version: int) -> str:
    """sha256 of `knowledge/scenarios/<scenario>.md` as walked, or a refusal.

    Refused when the file is absent or its `version:` is not the one the run says it walked: a
    result naming a version whose text nobody can produce is evidence of nothing.
    """
    if not _KIND_RE.match(scenario):
        raise CheckResultError(f"a scenario run's --target must be one scenario id, got {scenario!r}")
    rel = f"{SCENARIOS_SUBDIR}/{scenario}.md"
    try:
        raw = (root / rel).read_bytes()
    except FileNotFoundError as exc:
        raise CheckResultError(f"{rel} does not exist — a scenario result records the scenario it walked") from exc
    found = _frontmatter_version(raw.decode("utf-8", errors="replace"))
    if found != version:
        raise CheckResultError(
            f"{rel} is at version {found}, not --scenario-version {version} — write the result for the "
            "version the run walked"
        )
    return hashlib.sha256(raw).hexdigest()


def load_environment(root: Path, environment_id: str) -> dict[str, Any]:
    """The environment record `<root>/knowledge/environments/<id>.json`, or a refusal.

    The writer reads only what it needs from the record — that it exists (so `environment_id`
    names a real environment) and its `version_probe` (so an environment nobody can version
    leaves an unfinished run). The record's own shape is the consuming repository's
    environment validator's contract, not re-checked here.
    """
    if not _ENV_ID_RE.match(environment_id):
        raise CheckResultError(f"environment_id {environment_id!r} must be lowercase alphanumeric/hyphen")
    path = root / ENVIRONMENTS_SUBDIR / f"{environment_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        where = f"{ENVIRONMENTS_SUBDIR}/{environment_id}.json"
        raise CheckResultError(f"environment_id {environment_id!r} names no environment record ({where})") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CheckResultError(f"environment record {environment_id!r} cannot be read: {exc}") from exc
    if not isinstance(data, dict):
        raise CheckResultError(f"environment record {environment_id!r} is not a JSON object")
    return data


def _has_evidence(evidence: dict[str, Any] | None) -> bool:
    if not evidence:
        return False
    return bool(evidence.get("request_ids") or evidence.get("audit_ids") or evidence.get("snapshot"))


def _short_text(vid: str, key: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CheckResultError(f"`{key}` for {vid!r} must be a non-empty string")
    text = value.strip()
    if "\n" in text or len(text) > _SHORT_TEXT_MAX:
        raise CheckResultError(
            f"`{key}` for {vid!r} must be one short structured line (≤{_SHORT_TEXT_MAX} chars, "
            "e.g. `refused 403 ceiling_exceeded`) — narrative belongs in the record"
        )
    return text


def _clean_evidence(vid: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CheckResultError(f"`evidence` for {vid!r} must be an object {{request_ids, audit_ids, snapshot}}")
    unknown = sorted(set(raw) - {"request_ids", "audit_ids", "snapshot"})
    if unknown:
        raise CheckResultError(f"`evidence` for {vid!r} carries unknown keys {unknown}")
    out: dict[str, Any] = {}
    for key in ("request_ids", "audit_ids"):
        if key not in raw:
            continue
        ids = raw[key]
        if not isinstance(ids, list):
            raise CheckResultError(f"`evidence.{key}` for {vid!r} must be a list of ids")
        clean: list[str] = []
        for item in ids:
            if not isinstance(item, str) or not _EVIDENCE_TOKEN_RE.match(item.strip()):
                raise CheckResultError(f"`evidence.{key}` for {vid!r} holds {item!r}, which is not one id")
            if item.strip() not in clean:
                clean.append(item.strip())
        if clean:
            out[key] = clean
    if "snapshot" in raw and raw["snapshot"] not in (None, ""):
        snap = raw["snapshot"]
        if not isinstance(snap, str) or not _EVIDENCE_TOKEN_RE.match(snap.strip()):
            raise CheckResultError(f"`evidence.snapshot` for {vid!r} must be one hash token")
        out["snapshot"] = snap.strip()
    return out


def _clean_review(vid: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CheckResultError(f"`review` for {vid!r} must be an object {{state, at}}")
    state = str(raw.get("state") or REVIEW_DEFAULT).strip()
    if state not in REVIEW_STATES:
        raise CheckResultError(f"`review.state` for {vid!r} is {state!r}; must be one of {REVIEW_STATES}")
    out: dict[str, Any] = {"state": state}
    at = raw.get("at")
    if at not in (None, ""):
        if not isinstance(at, str):
            raise CheckResultError(f"`review.at` for {vid!r} must be an RFC3339 instant")
        try:
            out["at"] = rfc3339(parse_utc(at))
        except ValueError as exc:
            raise CheckResultError(f"`review.at` for {vid!r} is not an RFC3339 instant: {at!r}") from exc
    elif state != REVIEW_DEFAULT:
        raise CheckResultError(f"`review.state` {state!r} for {vid!r} needs the instant it was reviewed (`at`)")
    return out


def _clean_v2_fields(vid: str, verdict: str, item: dict[str, Any]) -> dict[str, Any]:
    """The validated optional v2 fields of one verdict (empty when it carries none)."""
    out: dict[str, Any] = {}
    if item.get("promise") not in (None, ""):
        promise = str(item["promise"]).strip()
        if not _PROMISE_RE.match(promise):
            raise CheckResultError(
                f"`promise` for {vid!r} is {promise!r}; it names ONE promise — a requirement row id "
                "(FLT-1157), a CAP-NNNN, a journey id or one journey criterion (`run-agent#3`)"
            )
        out["promise"] = promise
    for key in ("expected", "observed"):
        if item.get(key) not in (None, ""):
            out[key] = _short_text(vid, key, item[key])
    if item.get("evidence") not in (None, {}):
        evidence = _clean_evidence(vid, item["evidence"])
        if evidence:
            out["evidence"] = evidence
    if item.get("attempts") not in (None, ""):
        attempts = str(item["attempts"]).strip()
        match = _ATTEMPTS_RE.match(attempts)
        if not match or int(match.group(1)) > int(match.group(2)):
            raise CheckResultError(f'`attempts` for {vid!r} is {attempts!r}; must be "n/m" with 1 ≤ n ≤ m')
        out["attempts"] = attempts
    if item.get("cause") not in (None, ""):
        cause = str(item["cause"]).strip()
        if cause not in CAUSES:
            raise CheckResultError(f"`cause` for {vid!r} is {cause!r}; must be one of {CAUSES}")
        if verdict not in CAUSE_ALLOWED:
            raise CheckResultError(f"`cause` for {vid!r} is only recorded on fail/blocked, not on {verdict!r}")
        out["cause"] = cause
    if item.get("ticket") not in (None, ""):
        ticket = str(item["ticket"]).strip()
        if not _TICKET_RE.match(ticket):
            raise CheckResultError(
                f"`ticket` for {vid!r} is {ticket!r}; it is the tracker key of the finding this "
                "verdict filed (e.g. BUG-1178, ENG-12345)"
            )
        if verdict not in TICKET_ALLOWED:
            raise CheckResultError(f"`ticket` for {vid!r} is only recorded on fail/blocked, not on {verdict!r}")
        out["ticket"] = ticket
    if item.get("review") not in (None, {}):
        out["review"] = _clean_review(vid, item["review"])
    if "new" in item and item["new"] is not None:
        if not isinstance(item["new"], bool):
            raise CheckResultError(f"`new` for {vid!r} must be a boolean")
        out["new"] = item["new"]
    return out


def build_result(
    *,
    kind: str,
    target: str,
    commit: str,
    environment: str,
    finished: bool,
    at: datetime,
    verdicts: list[dict[str, Any]],
    environment_id: str = "",
    release: str = "",
    scenario_version: int | None = None,
    environment_record: dict[str, Any] | None = None,
    notes: list[str] | None = None,
    runner: str = "",
    scenario_sha256: str = "",
    blocked_environment: str = "",
) -> dict[str, Any]:
    """The validated result object (v1, or v2 when any v2 field is given), or a `CheckResultError`.

    Every refusal names the field, so a run that mis-shaped a verdict fixes it here rather
    than in a red commit validator in the consuming repository. `environment_record` is the
    loaded record `environment_id` names (the caller resolves it against the checkout);
    `notes` collects the corrections the writer made on the run's behalf (a pass with no
    evidence written as blocked, a run against an unversioned build written unfinished).
    """
    notes = notes if notes is not None else []
    blocked_environment = blocked_environment.strip()
    if blocked_environment and "\n" in blocked_environment:
        raise CheckResultError("--blocked-environment takes one sentence, not multi-line text")
    kind = kind.strip()
    if not _KIND_RE.match(kind):
        raise CheckResultError(f"kind {kind!r} must be lowercase alphanumeric/hyphen (a slot kinds: entry)")
    target = target.strip()
    if not target:
        raise CheckResultError("target must be non-empty (the thing or capability ids the run looked at)")
    for token in (part.strip() for part in target.split(",")):
        if not token:
            raise CheckResultError(f"target {target!r} lists an empty id — comma-separated ids only")
        if not _TARGET_TOKEN_RE.match(token):
            raise CheckResultError(
                f"target {target!r} names no thing or capability id the Quality desk can place — "
                "pass the ids the run covered (comma-separated, e.g. CAP-0001,CAP-0002 or sync); "
                "a free-text scope belongs in --scope"
            )
    commit = commit.strip()
    if not commit:
        raise CheckResultError("commit must be non-empty")
    if environment not in ENVIRONMENTS:
        raise CheckResultError(f"environment {environment!r} must be one of {ENVIRONMENTS}")
    if not isinstance(finished, bool):
        raise CheckResultError("finished must be a boolean")

    environment_id = environment_id.strip()
    release = release.strip()
    runner = runner.strip()
    if runner and not _RUNNER_RE.match(runner):
        raise CheckResultError(f"runner {runner!r} must be one run id token (the session that ran the check)")
    if environment_id and not runner:
        raise CheckResultError(
            "runner is required with environment_id — pass --runner with this session's run id, so the "
            "verifier can refuse to review a result its own run wrote"
        )
    if release and not environment_id:
        raise CheckResultError("release names the build an environment served — pass it with --environment-id")
    if environment_id:
        if not _ENV_ID_RE.match(environment_id):
            raise CheckResultError(f"environment_id {environment_id!r} must be lowercase alphanumeric/hyphen")
        if environment != "live":
            raise CheckResultError("environment_id names an environment the run drove — it implies --environment live")
        if not release:
            raise CheckResultError(
                "release is required with environment_id — pass the version the environment's probe "
                f"answered, or {RELEASE_UNKNOWN!r} when it could not name the build"
            )
        if not _RELEASE_RE.match(release):
            raise CheckResultError(f"release {release!r} must be one version token (a semver, tag, digest or commit)")
        probe = (environment_record or {}).get("version_probe", "") if environment_record is not None else ""
        unversioned = release == RELEASE_UNKNOWN or (environment_record is not None and not probe)
        if unversioned and finished:
            finished = False
            notes.append(
                f"environment {environment_id!r} has no version the run could name — written finished: false "
                "(a verdict against an unnamed build is recorded, never counted)"
            )
    if scenario_version is not None:
        if isinstance(scenario_version, bool) or not isinstance(scenario_version, int) or scenario_version < 1:
            raise CheckResultError("scenario_version must be a positive integer (the scenario record's `version:`)")
        if kind != "scenario":
            raise CheckResultError(f"scenario_version is recorded on kind `scenario` only, not {kind!r}")
    if kind == "scenario" and environment_id and scenario_version is None:
        # Without the version a scenario run walked, the Quality desk's overlay can never match
        # the file's verdicts to a scenario table, so its passes would silently never count.
        raise CheckResultError(
            "scenario_version is required on a scenario run against an environment — pass "
            "--scenario-version with the scenario record's `version:`"
        )

    v2 = bool(environment_id or release or scenario_version is not None or blocked_environment) or any(
        isinstance(item, dict) and any(key in item and item[key] not in (None, "", {}) for key in V2_VERDICT_KEYS)
        for item in verdicts
    )

    clean: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in verdicts:
        if not isinstance(item, dict):
            raise CheckResultError(f"each verdict must be an object, got {item!r}")
        vid = str(item.get("id", "")).strip()
        verdict = str(item.get("verdict", "")).strip()
        reason = str(item.get("reason", "") or "").strip()
        if not vid:
            raise CheckResultError("every verdict needs a non-empty id")
        if vid in seen:
            raise CheckResultError(f"verdict id {vid!r} appears more than once")
        seen.add(vid)
        if verdict not in VERDICTS:
            raise CheckResultError(f"verdict for {vid!r} is {verdict!r}; must be one of {VERDICTS}")
        if blocked_environment:
            # The fresh copy never came up, so every row is the environment's and no attempt was
            # made: the run-level sentence wins over whatever the row declared, and a row cannot
            # carry attempts (there were none) or a ticket (nothing was filed).
            verdict = "blocked"
            reason = blocked_environment
            item = {key: value for key, value in item.items() if key not in ("attempts", "ticket", "cause")}
        extra = _clean_v2_fields(vid, verdict, item) if v2 else {}
        if blocked_environment:
            extra["cause"] = CAUSE_BLOCKED_ENVIRONMENT
        if v2 and verdict == "pass" and not _has_evidence(extra.get("evidence")):
            verdict = "blocked"
            reason = NO_EVIDENCE_REASON
            extra["cause"] = CAUSE_NO_EVIDENCE
            notes.append(
                f"{vid}: a pass with no request id, audit id or snapshot is written as blocked "
                f"({NO_EVIDENCE_REASON!r}, cause {CAUSE_NO_EVIDENCE!r})"
            )
        if v2 and not blocked_environment:
            # FLT-1211: every v2 verdict states what was expected and what was observed — files
            # are append-only, so a field made required later would be a v3. A run whose copy never
            # came up observed nothing, so its rows carry the fact file's sentence instead.
            absent = [key for key in ("expected", "observed") if key not in extra]
            if absent:
                raise CheckResultError(
                    f"verdict {vid!r} needs {' and '.join(absent)} — every v2 verdict states what was "
                    "expected and what was observed (one short structured line each)"
                )
        if environment_id:
            # A result against an environment is the Quality desk's evidence row, and files are
            # append-only: a field optional today is a v3 tomorrow. So every verdict names the
            # promise it proves and its attempts, and every fail/blocked names its cause. A run
            # whose copy never came up made no attempt, so its rows carry no `attempts` at all.
            required = ("promise",) if blocked_environment else ("promise", "attempts")
            missing = [key for key in required if key not in extra]
            if verdict in CAUSE_ALLOWED and "cause" not in extra:
                missing.append("cause")
            if missing:
                raise CheckResultError(
                    f"verdict {vid!r} against environment {environment_id!r} needs {', '.join(missing)} — "
                    "every verdict names its promise and attempts, every fail/blocked its cause"
                )
        if verdict in REASON_REQUIRED and not reason:
            raise CheckResultError(f"verdict {verdict!r} for {vid!r} needs a non-empty reason")
        entry: dict[str, Any] = {"id": vid, "verdict": verdict}
        if reason:
            entry["reason"] = reason
        entry.update(extra)
        clean.append(entry)

    if blocked_environment:
        # A run whose copy never came up drove nothing, so it is never finished — whatever the
        # release says — and every row above already records that no attempt was made.
        finished = False
        notes.append(
            "the fresh copy never came up — every row written blocked, cause environment, "
            "unfinished (no attempt was made)"
        )

    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION_V2 if v2 else SCHEMA_VERSION,
        "kind": kind,
        "target": target,
        "commit": commit,
        "environment": environment,
    }
    if runner:
        data["runner"] = runner
    if environment_id:
        data["environment_id"] = environment_id
        data["release"] = release
    if scenario_version is not None:
        data["scenario_version"] = scenario_version
        if scenario_sha256:
            data["scenario_sha256"] = scenario_sha256
    data.update({"finished": finished, "ran_at": rfc3339(at), "verdicts": clean})
    return data


def _split_pair(raw: str, flag: str) -> tuple[str, str]:
    key, sep, value = raw.partition("=")
    if not sep or not key.strip():
        raise CheckResultError(f"{flag} expects ID=VALUE, got {raw!r}")
    return key.strip(), value


#: Per-verdict flags whose value is one scalar field: `(flag, dest, field)`.
_SCALAR_FLAGS = (
    ("--reason", "reason", "reason"),
    ("--promise", "promise", "promise"),
    ("--expected", "expected", "expected"),
    ("--observed", "observed", "observed"),
    ("--attempts", "attempts", "attempts"),
    ("--cause", "cause", "cause"),
    ("--ticket", "ticket", "ticket"),
)


def collect_verdicts(
    specs: list[str],
    reasons: list[str],
    verdict_file: str,
    fields: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Merge `--verdict-file`, repeated `--verdict`, and the per-verdict field flags into one list.

    `fields` maps a per-verdict flag's dest (`promise`, `expected`, `observed`, `attempts`,
    `cause`, `ticket`, `request_id`, `audit_id`, `snapshot`, `review`, `reviewed_at`, `new`) to its
    raw `ID=VALUE` values (`new` takes a bare ID). Every one must name a declared id.
    """
    fields = dict(fields or {})
    fields["reason"] = reasons
    if verdict_file:
        try:
            loaded = json.loads(Path(verdict_file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckResultError(f"cannot read --verdict-file {verdict_file!r}: {exc}") from exc
        if not isinstance(loaded, list):
            raise CheckResultError("--verdict-file must hold a JSON list of verdict objects")
    else:
        loaded = []

    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    declared: set[str] = set()
    for item in loaded:
        if not isinstance(item, dict):
            raise CheckResultError(f"--verdict-file entry must be an object, got {item!r}")
        vid = str(item.get("id", "")).strip()
        if not vid:
            raise CheckResultError("--verdict-file entry has no id")
        if vid in merged:
            raise CheckResultError(f"--verdict-file declares id {vid!r} more than once")
        order.append(vid)
        merged[vid] = dict(item)
    for raw in specs:
        vid, verdict = _split_pair(raw, "--verdict")
        if vid in declared:
            raise CheckResultError(f"--verdict declares id {vid!r} more than once")
        declared.add(vid)
        if vid not in merged:
            order.append(vid)
        existing = merged.get(vid, {"id": vid})
        existing["id"] = vid
        existing["verdict"] = verdict
        merged[vid] = existing

    def target(flag: str, vid: str) -> dict[str, Any]:
        if vid not in merged:
            raise CheckResultError(f"{flag} names {vid!r}, which no --verdict or --verdict-file declared")
        return merged[vid]

    for flag, dest, key in _SCALAR_FLAGS:
        for raw in fields.get(dest, []):
            vid, value = _split_pair(raw, flag)
            target(flag, vid)[key] = value
    for flag, dest, key in (("--request-id", "request_id", "request_ids"), ("--audit-id", "audit_id", "audit_ids")):
        for raw in fields.get(dest, []):
            vid, value = _split_pair(raw, flag)
            evidence = target(flag, vid).setdefault("evidence", {})
            evidence.setdefault(key, []).append(value.strip())
    for raw in fields.get("snapshot", []):
        vid, value = _split_pair(raw, "--snapshot")
        target("--snapshot", vid).setdefault("evidence", {})["snapshot"] = value.strip()
    for raw in fields.get("review", []):
        vid, value = _split_pair(raw, "--review")
        target("--review", vid).setdefault("review", {})["state"] = value.strip()
    for raw in fields.get("reviewed_at", []):
        vid, value = _split_pair(raw, "--reviewed-at")
        target("--reviewed-at", vid).setdefault("review", {})["at"] = value.strip()
    for raw in fields.get("new", []):
        target("--new", raw.strip())["new"] = True
    return [merged[vid] for vid in order]


def write_result(
    *,
    root: Path,
    kind: str,
    scope: str,
    target: str,
    commit: str,
    environment: str,
    finished: bool,
    verdicts: list[dict[str, Any]],
    at: datetime,
    environment_id: str = "",
    release: str = "",
    scenario_version: int | None = None,
    notes: list[str] | None = None,
    runner: str = "",
    blocked_environment: str = "",
) -> Path:
    """Validate everything, then write the file under the results home. Refuses otherwise."""
    slug = slugify(scope or target)
    if not slug:
        raise CheckResultError("scope/target yields an empty slug — pass a --scope with a letter or digit")
    record = load_environment(root, environment_id.strip()) if environment_id.strip() else None
    digest = ""
    if kind == "scenario" and isinstance(scenario_version, int) and not isinstance(scenario_version, bool):
        digest = scenario_digest(root, target.strip(), scenario_version)
    data = build_result(
        kind=kind,
        target=target,
        commit=commit,
        environment=environment,
        finished=finished,
        at=at,
        verdicts=verdicts,
        environment_id=environment_id,
        release=release,
        scenario_version=scenario_version,
        environment_record=record,
        notes=notes,
        runner=runner,
        scenario_sha256=digest,
        blocked_environment=blocked_environment,
    )
    path = result_path(root, data["kind"], slug, at)
    home = (root / RESULTS_SUBDIR).resolve()
    try:
        path.resolve().relative_to(home)
    except ValueError as exc:  # a scope or kind that escaped the home — never write it
        raise CheckResultError(f"result path {path} escapes the results home {home}") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def corpus_promise_ids(root: Path) -> set[str] | None:
    """Every promise id this checkout's corpus carries (register rows, capabilities, live journey
    criteria), or None when it cannot be read here — no `fleet_knowledge`, no corpus, nothing in
    it. Read for a WARNING only (BUG-1151): the corpus can change after a result is written, so an
    id it does not carry today is said, never refused."""
    try:
        _repo.fleet_knowledge()
        from fleet_knowledge.config import resolve  # noqa: PLC0415 — after the path insert
        from fleet_knowledge.quality import corpus_promise_ids as read  # noqa: PLC0415
    except (SystemExit, ImportError):
        return None
    try:
        # The checkout's own resolution (its `fleet.toml`, else `<root>/knowledge`), never the
        # caller's environment: the corpus a result is checked against is the one it is written to.
        kb = resolve(cwd=root, env={})
        cfg = kb.config
        ids: set[str] = read(
            kb.knowledge,
            requirements_dir=cfg.requirements_dir,
            features_dir=cfg.features_dir,
            journeys_dir=cfg.journeys_dir,
            capability_prefix=cfg.capability_prefix,
            aliases_file=cfg.capability_aliases,
        )
    except Exception:  # noqa: BLE001 — the read only feeds a WARNING, and it runs after the write
        # A corpus this writer cannot read — missing, unconfigured, or malformed in any way a reader
        # can raise on — is no reason to fail a result already on disk: exiting 1 there printed no
        # path, and a caller that retried wrote the same run twice. It only loses the warning.
        return None
    return ids or None


def _names_a_promise(data: dict[str, Any]) -> bool:
    """Whether any verdict names a promise — the corpus is read only when there is one to check."""
    return any(item.get("promise") for item in data.get("verdicts") or ())


def unplaced_warnings(data: dict[str, Any], known: set[str] | None) -> list[str]:
    """One warning per verdict whose `promise` the corpus does not carry: the desk will list that
    row as unplaced and count it toward nothing (BUG-1151). Empty when the corpus is unreadable."""
    if known is None:
        return []
    return [
        f"`promise` for {item['id']!r} is {item['promise']!r}, which names no register row, "
        "capability or live journey criterion in this checkout — the result is written as given, "
        "and the desk will list the row as unplaced until the corpus carries that promise"
        for item in data.get("verdicts") or ()
        if item.get("promise") and item["promise"] not in known
    ]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write one audit run's check-result file.")
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="validate and write one result file")
    write.add_argument("--kind", required=True, help="the audit type / kind (the file's parent dir)")
    write.add_argument("--target", required=True, help="the thing/capability ids the run looked at (comma-separated)")
    write.add_argument("--scope", default="", help="the filename slug (defaults to --target)")
    write.add_argument("--commit", default="", help="the code commit (defaults to HEAD)")
    write.add_argument("--environment", required=True, help="live or code-only (validated in the writer)")
    write.add_argument("--finished", dest="finished", action="store_true", default=True, help="the run completed")
    write.add_argument("--unfinished", dest="finished", action="store_false", help="the run did not complete")
    write.add_argument("--environment-id", default="", help="v2: the environment record the run drove")
    write.add_argument(
        "--release",
        default="",
        help="v2: the deployed version observed, or "
        f"{RELEASE_UNKNOWN!r}; defaults to the run's {RELEASE_ENV} when omitted",
    )
    write.add_argument("--scenario-version", type=int, default=None, help="v2: the scenario's `version:` walked")
    write.add_argument(
        "--runner", default=None, help="the run id of the session that ran the check (required with --environment-id)"
    )
    write.add_argument(
        "--blocked-environment",
        default="",
        metavar="SENTENCE",
        help="the fresh copy never came up: write every row blocked, cause environment, no attempts, unfinished",
    )
    write.add_argument("--verdict", action="append", default=[], metavar="ID=VERDICT", help="one verdict")
    write.add_argument("--reason", action="append", default=[], metavar="ID=TEXT", help="a verdict's reason")
    for flag, help_text in (
        ("--promise", "v2: the ONE promise id the assertion proves"),
        ("--expected", "v2: the expected outcome, one short structured line"),
        ("--observed", "v2: the observed outcome, one short structured line"),
        ("--request-id", "v2: a platform request id behind the verdict (repeatable)"),
        ("--audit-id", "v2: an audit-log row id behind the verdict (repeatable)"),
        ("--snapshot", "v2: a snapshot hash behind the verdict"),
        ("--attempts", "v2: n/m — the attempt that produced the verdict, of the attempts made"),
        ("--cause", "v2: product|agent|environment|inconclusive (fail/blocked only)"),
        ("--ticket", "v2: the tracker key of the finding a fail filed (fail/blocked only)"),
        ("--review", "v2: verified|unverified|disputed"),
        ("--reviewed-at", "v2: RFC3339 instant of the review"),
    ):
        write.add_argument(flag, action="append", default=[], metavar="ID=VALUE", help=help_text)
    write.add_argument("--new", action="append", default=[], metavar="ID", help="v2: the verdict is new this run")
    write.add_argument("--verdict-file", default="", help="a JSON list of verdict objects")
    write.add_argument("--root", default="", help="the checkout to write under (default: this repo)")
    write.add_argument(
        "--at",
        default="",
        help="RFC3339 UTC instant (YYYY-MM-DDTHH:MM:SSZ) the run started driving the product — the "
        "result's ran_at and its filename; default now; refused in the future or over 24h old",
    )
    return parser


def _now() -> datetime:
    """The writer's clock — one seam, so a test can hold it still."""
    return datetime.now(UTC)


def observed_at(value: str, now: datetime) -> datetime:
    """`--at`: when the run started driving the product, or a refusal naming the flag.

    Refused when the pattern refuses it (`parse_utc`, BUG-1118), when it is later than `now` by
    more than `AT_SKEW` (evidence cannot have been observed in the future), and when it is earlier
    than `now` by more than `AT_MAX_AGE` (a backdated result reorders the desk's latest).
    """
    try:
        at = parse_utc(value)
    except ValueError as exc:
        raise CheckResultError(f"--at {value!r} is not an RFC3339 UTC instant (YYYY-MM-DDTHH:MM:SSZ)") from exc
    if at > now.astimezone(UTC) + AT_SKEW:
        raise CheckResultError(
            f"--at {rfc3339(at)} is in the future (now {rfc3339(now)}) — it is when this run drove the "
            "product, which has already happened"
        )
    if at < now.astimezone(UTC) - AT_MAX_AGE:
        raise CheckResultError(
            f"--at {rfc3339(at)} is more than {int(AT_MAX_AGE.total_seconds() // 3600)}h before now "
            f"({rfc3339(now)}) — write the result when the run drives, never backdated"
        )
    return at


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "write":  # pragma: no cover - argparse enforces the set
        return 2
    notes: list[str] = []
    try:
        if args.runner is not None and not args.runner.strip():
            raise CheckResultError("--runner must be non-empty (this session's run id)")
        root = Path(args.root).resolve() if args.root else _repo.repo_root()
        # THE RELEASE THE SYSTEM KNOWS, not one the agent remembered (ENG-19900). A QA or audit
        # run names its environment but often omits `--release`; the daemon exports the deployed
        # release as `FLEET_RELEASE` into every dispatched run, which fills the gap here. An
        # explicit `--release` always wins, and the reading is only consulted for a run that
        # names an environment — a release with no environment is still refused (below).
        release = args.release
        if not release.strip() and args.environment_id.strip():
            release = os.environ.get(RELEASE_ENV, "")
        now = _now()
        at = observed_at(args.at, now) if args.at else now
        fields = {
            dest: getattr(args, dest)
            for dest in (
                "promise",
                "expected",
                "observed",
                "request_id",
                "audit_id",
                "snapshot",
                "attempts",
                "cause",
                "ticket",
                "review",
                "reviewed_at",
                "new",
            )
        }
        verdicts = collect_verdicts(args.verdict, args.reason, args.verdict_file, fields)
        commit = args.commit or head_commit(root)
        path = write_result(
            root=root,
            kind=args.kind,
            scope=args.scope,
            target=args.target,
            commit=commit,
            environment=args.environment,
            finished=args.finished,
            verdicts=verdicts,
            at=at,
            environment_id=args.environment_id,
            release=release,
            scenario_version=args.scenario_version,
            notes=notes,
            runner=args.runner or "",
            blocked_environment=args.blocked_environment,
        )
    except CheckResultError as exc:
        print(f"check_result: {exc}", file=sys.stderr)
        return 1
    for note in notes:
        print(f"check_result: note: {note}", file=sys.stderr)
    written = json.loads(path.read_text(encoding="utf-8"))
    for warning in unplaced_warnings(written, corpus_promise_ids(root) if _names_a_promise(written) else None):
        print(f"check_result: warning: {warning}", file=sys.stderr)
    try:
        shown = path.relative_to(root).as_posix()
    except ValueError:  # pragma: no cover - write_result refused escapes before writing
        shown = str(path)
    print(shown)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Lay the verifier's records over the check results (FLT-1213, FLT-1214, FLT-1215, FLT-1229).

A check-result file is append-only, so the second party's word on a verdict cannot live inside
it. The `qa:verify` command writes its own records instead (`commandtree/scripts/qa_review.py`):

    knowledge/audits/reviews/<kind>/<result-stem>--<YYYY-MM-DD>-<HHMMSS>Z.json   reviews
    knowledge/audits/reviews/oracles/<scenario>-v<N>.json                          oracle decisions
    knowledge/audits/reviews/planted/<scenario>-<YYYY-MM-DD>.json                  planted outcomes

This module is the reader half. :func:`overlay` takes the verdict rows `quality.read_results`
built and returns them with the verifier's reading on each:

* **A review record overrides whatever the result file says; the latest one wins.** Reviews of
  one `(result file, verdict id)` are ordered by their parsed `reviewed_at` instant, then by
  record path, so the answer is the same on every read.
* **No review reads `unverified`** — and an unverified pass still counts toward green: the
  verifier samples, and green is "passed on this release, with platform evidence, and not
  disputed". Unverified is a reading the desk shows, not a demotion.
* **The result file's own `review` is the runner's word.** An in-file `verified` reads
  `unverified`; an in-file `disputed` is kept until a review record speaks.
* **A review is ignored when the result names no `runner`, or when its reviewer is that runner**
  — without a runner nobody can show the reviewer was a second party.
* **Anything that makes a pass count needs provenance (BUG-1144).** A record is plain JSON in the
  repository, so everything in it is only what the file says. When Fleet dispatches
  `qa:verify` it hands the session a per-run key over its run id — env only, never argv —
  and the writer signs each record with it: `provenance` = HMAC over the canonical hash of the
  WHOLE record (:func:`record_token`). The desk recomputes it under an explicit
  :class:`Authority` — the server-side secret plus the control plane's attestations: the run
  must have attested the record's digest through `attest_qa_review` while its `qa-verify` claim was
  live, at the server's time, never the record's. A `verified` review, an `approved`
  oracle and a `caught` planted outcome without that are ignored. Disputes, rejections and missed
  catches only make things stricter and stand unsigned. No Authority verifies nothing.
* **The scenario-version oracle (FLT-1214).** A pass of kind `scenario` counts only on a
  `scenario_version` whose oracle is `approved` and still pinned: when the scenario file is at that
  version today and its expected-results section hashes differently from the approval's
  `expected_sha256`, the approval is `changed` and the pass is not counted. A scenario pass naming
  no version is not counted either.
* **Disputed is never green.** :func:`counts` answers False for a disputed or not-counted row.

:func:`reading` is the one call the desk needs for everything that is not a verdict row: the
disputed verdicts, the weak scenarios, the latest planted outcomes and the oracle states.

Pure, stdlib-only and defensive like its caller: a malformed record is skipped, never raised. The
records' integrity is the gate's job — `qa_review.py validate` and `append-only`, run by the
`qa-review-records` check — because a reader cannot see a record that was deleted.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REVIEWS_SUBDIR = "knowledge/audits/reviews"
SCENARIOS_SUBDIR = "knowledge/scenarios"
ORACLES = "oracles"
PLANTED = "planted"
REVIEW_STATES = frozenset({"verified", "unverified", "disputed"})
UNVERIFIED = "unverified"
DISPUTED = "disputed"
APPROVED = "approved"
REJECTED = "rejected"
PENDING = "pending"
#: An approval whose pinned expected results no longer match the scenario file at that version.
CHANGED = "changed"
SCENARIO_KIND = "scenario"
_RUNNER_KEYS = ("runner", "run_id")
#: The session environment variable a `qa:verify` dispatch's per-run review key rides in.
QA_REVIEW_KEY_ENV = "FLEET_QA_REVIEW_KEY"
#: The record field carrying the token :func:`record_token` computes.
PROVENANCE_FIELD = "provenance"
_RUN_KEY_PREFIX = "qa-verify:v1:"
_TOKEN_PREFIX = "qa-record:v2:"
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_EXPECTED_H2_RE = re.compile(r"^##\s+[^\n]*\b(?:expected|acceptance criteria|assertions)\b", re.I)

__all__ = [
    "APPROVED",
    "CHANGED",
    "PROVENANCE_FIELD",
    "QA_REVIEW_KEY_ENV",
    "DISPUTED",
    "PENDING",
    "REJECTED",
    "UNVERIFIED",
    "counts",
    "expected_digest",
    "overlay",
    "read_oracles",
    "read_planted",
    "read_reviews",
    "reading",
    "Authority",
    "record_digest",
    "record_signed",
    "record_token",
    "review_run_key",
    "scenario_version",
    "weak_scenarios",
]


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _instant(text: Any) -> datetime | None:
    if not isinstance(text, str) or not text.strip():
        return None
    raw = text.strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(UTC)


def _records(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    home = root / REVIEWS_SUBDIR
    if not home.is_dir():
        return []
    real = home.resolve()
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(home.rglob("*.json")):
        if path.is_symlink():
            continue
        try:
            path.resolve().relative_to(real)
        except (OSError, ValueError):
            continue
        data = _load(path)
        if isinstance(data, dict):
            out.append((path, data))
    return out


def _runner(result: dict[str, Any]) -> str:
    for key in _RUNNER_KEYS:
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


# ───────────────────────────── scenario text (mirrors qa_review.py) ─────────────────────────────


def scenario_version(text: str) -> int | None:
    """The scenario record's frontmatter `version:` as an integer, or None."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "version":
            raw = value.strip().strip("'\"")
            return int(raw) if raw.isdigit() and int(raw) > 0 else None
    return None


def expected_digest(text: str) -> str:
    """sha256 of the scenario's expected-results sections (whole body when it has none)."""
    body = _FRONTMATTER_RE.sub("", text, count=1)
    lines = body.splitlines()
    picked: list[str] = []
    inside = False
    found = False
    for line in lines:
        if line.startswith("## "):
            inside = bool(_EXPECTED_H2_RE.match(line))
            found = found or inside
        if inside:
            picked.append(line)
    chosen = picked if found else lines
    norm = "\n".join(line.rstrip() for line in chosen)
    norm = re.sub(r"\n{2,}", "\n", norm).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


# ───────────────────────────── readers ─────────────────────────────


def review_run_key(secret: str, run_id: str) -> str:
    """The per-run key a `qa:verify` dispatch is handed: HMAC(secret, run id).

    Minted by Fleet at lease from its server-side secret and delivered in the session's environment
    (`QA_REVIEW_KEY_ENV`) only. Domain-separated from every other token the secret signs.
    """
    return hmac.new(secret.encode("utf-8"), f"{_RUN_KEY_PREFIX}{run_id}".encode(), hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class Authority:
    """What the desk needs to accept a signed record — and it must be handed in explicitly.

    `secret` is the deployment's verify-dispatch secret the per-run key derives from. `attested`
    is the control plane's word: whether `run id` attested exactly `digest` (:func:`record_digest`)
    through the `attest_qa_review` tool, which only a `qa:verify` run can call, and only
    while its claim is live; the server stamps its own time. No instant the record carries is in
    the trust path, so a record backdated into a run's lifetime, or written after it ended with a
    leaked key, proves nothing. A reader holding no Authority (``None``) or an empty secret
    verifies NOTHING: there is no shape-only path on the desk side. The repository-side
    validator's shape check lives in `qa_review.py`, named as such.
    """

    secret: str
    attested: Callable[[str, str], bool]


def record_digest(data: Mapping[str, Any]) -> str:
    """sha256 of the canonical JSON of everything the record asserts — all of it but `provenance`.

    Canonical: keys sorted, no insignificant whitespace, UTF-8. A record whose verdict list, states,
    reasons, instant, reviewer kind, decision or outcome is edited after signing hashes differently,
    so a signed dispute cannot be flipped to `verified`. Mirrored in `qa_review.py`.
    """
    body = {k: v for k, v in data.items() if k != PROVENANCE_FIELD}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_token(run_key: str, data: Mapping[str, Any], *, bound: str = "") -> str:
    """A record's `provenance`: HMAC(run key, record kind · reviewer · bound · `record_digest`).

    `bound` is a fact the record leans on but does not carry — a review's result's
    `scenario_version` — so the token cannot be moved onto another version either.
    """
    payload = f"{_TOKEN_PREFIX}{data.get('record')}:{data.get('reviewer')}:{bound}:{record_digest(data)}"
    return hmac.new(run_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def record_signed(authority: Authority | None, data: Mapping[str, Any], *, bound: str = "") -> bool:
    """Whether a dispatched verifier run signed exactly this record AND attested it while live."""
    if authority is None or not authority.secret:
        return False
    token, reviewer = data.get(PROVENANCE_FIELD), data.get("reviewer")
    if not isinstance(token, str) or not isinstance(reviewer, str) or not re.fullmatch(r"[0-9a-f]{64}", token):
        return False
    expected = record_token(review_run_key(authority.secret, reviewer), data, bound=bound)
    if not hmac.compare_digest(expected, token):
        return False
    return bool(authority.attested(reviewer, record_digest(data)))


def _bound_version(version: object) -> str:
    return "" if version is None or isinstance(version, bool) else str(version)


def read_reviews(root: Path, *, authority: Authority | None) -> dict[tuple[str, str], dict[str, Any]]:
    """`{(result_file, verdict id): latest review}` — `{state, at, reviewer, reason, ticket, record}`.

    Ordered by the parsed `reviewed_at` instant, then by record path. A record whose instant does
    not parse is skipped. A `verified` entry counts only from a fleet-run record `record_signed`
    accepts under `authority` (BUG-1144); otherwise it is ignored, so the verdict reads as its
    previous review or `unverified`. ``authority=None`` verifies nothing.
    """
    best: dict[tuple[str, str], tuple[tuple[datetime, str], dict[str, Any]]] = {}
    versions: dict[str, object] = {}
    for path, data in _records(root):
        if path.parent.name in (ORACLES, PLANTED) or data.get("record") != "review":
            continue
        result_file, reviewer = data.get("result_file"), data.get("reviewer")
        when = _instant(data.get("reviewed_at"))
        if not isinstance(result_file, str) or not isinstance(reviewer, str) or when is None:
            continue
        rel = path.relative_to(root).as_posix()
        manual = data.get("reviewer_kind") == "manual"
        if result_file not in versions:
            loaded = _load(root / result_file)
            versions[result_file] = loaded.get("scenario_version") if isinstance(loaded, dict) else None
        proven = not manual and record_signed(authority, data, bound=_bound_version(versions[result_file]))
        for item in data.get("verdicts") or []:
            if not isinstance(item, dict) or item.get("state") not in REVIEW_STATES:
                continue
            # A MANUAL REVIEW ONLY EVER MAKES THINGS STRICTER (FLT-1213, FLT-1216): the re-grader is
            # the verifier agent, so a self-named person's `verified` is ignored here even if it was
            # hand-written past the writer's refusal. Its dispute still stands.
            if manual and item["state"] == "verified":
                continue
            # AND A FLEET-RUN `verified` WITHOUT PROVENANCE IS NOT ONE (BUG-1144): nothing but the
            # dispatched verifier's per-run key can sign it, so a hand-written record claiming
            # `fleet-run` — or claiming nothing — cannot move a pass to verified.
            if item["state"] == "verified" and not proven:
                continue
            key = (result_file, str(item.get("id") or ""))
            order = (when, rel)
            current = best.get(key)
            if current is not None and current[0] >= order:
                continue
            best[key] = (
                order,
                {
                    "state": str(item["state"]),
                    "at": str(data.get("reviewed_at")),
                    "reviewer": reviewer,
                    # `fleet-run` | `manual`; "" on a record from before the field (unstated).
                    "reviewer_kind": str(data.get("reviewer_kind") or ""),
                    "reason": str(item.get("reason") or ""),
                    "ticket": str(item.get("ticket") or ""),
                    "record": rel,
                },
            )
    return {key: value for key, (_order, value) in best.items()}


def read_oracles(root: Path, *, authority: Authority | None) -> dict[tuple[str, int], str]:
    """`{(scenario, version): approved|rejected|changed}` from the oracle records.

    An approval lets passes count, so it counts only when `record_signed` accepts it (BUG-1144):
    an unsigned or forged approval is ignored and the version reads pending. A rejection only makes
    things stricter and stands unsigned.

    An approval whose `expected_sha256` disagrees with the scenario file — when that file is at the
    approved version today — reads `changed`: the expected results moved without a version bump.
    """
    current: dict[str, tuple[int | None, str]] = {}
    out: dict[tuple[str, int], str] = {}
    for path, data in _records(root):
        if path.parent.name != ORACLES or data.get("record") != "oracle":
            continue
        scenario, version, decision = data.get("scenario"), data.get("version"), data.get("decision")
        if (
            not isinstance(scenario, str)
            or not isinstance(version, int)
            or isinstance(version, bool)
            or decision not in (APPROVED, REJECTED)
        ):
            continue
        if decision == APPROVED and not record_signed(authority, data):
            continue
        if decision == APPROVED:
            if scenario not in current:
                scenario_file = root / SCENARIOS_SUBDIR / f"{scenario}.md"
                try:
                    text = scenario_file.read_text(encoding="utf-8")
                    current[scenario] = (scenario_version(text), expected_digest(text))
                except (OSError, UnicodeDecodeError):
                    current[scenario] = (None, "")
            at_version, digest = current[scenario]
            pinned = data.get("expected_sha256")
            if not isinstance(pinned, str) or (at_version == version and pinned != digest):
                out[(scenario, version)] = CHANGED
                continue
        out[(scenario, version)] = str(decision)
    return out


def read_planted(root: Path, *, authority: Authority | None) -> dict[str, dict[str, Any]]:
    """`{scenario: latest planted outcome}` — `{caught, at, mutation, record}`.

    A `caught` outcome clears a scenario of being weak, so it counts only when `record_signed`
    accepts it (BUG-1144); a missed catch only makes things stricter and stands unsigned.
    """
    out: dict[str, tuple[datetime, dict[str, Any]]] = {}
    for path, data in _records(root):
        if path.parent.name != PLANTED or data.get("record") != "planted":
            continue
        scenario, caught, when = data.get("scenario"), data.get("caught"), _instant(data.get("at"))
        if not isinstance(scenario, str) or not isinstance(caught, bool) or when is None:
            continue
        if caught and not record_signed(authority, data):
            continue
        current = out.get(scenario)
        if current is not None and current[0] >= when:
            continue
        out[scenario] = (
            when,
            {
                "caught": caught,
                "at": str(data.get("at")),
                "mutation": str(data.get("mutation") or ""),
                "record": path.relative_to(root).as_posix(),
            },
        )
    return {scenario: outcome for scenario, (_when, outcome) in out.items()}


def weak_scenarios(root: Path, *, authority: Authority | None) -> dict[str, dict[str, Any]]:
    """The scenarios whose latest planted bug did not turn them red (FLT-1215)."""
    return {
        scenario: outcome
        for scenario, outcome in read_planted(root, authority=authority).items()
        if not outcome["caught"]
    }


def _scenario_of(verdict_id: str, result: dict[str, Any]) -> str:
    if "#" in verdict_id:
        return verdict_id.split("#", 1)[0]
    return str(result.get("target") or "")


def overlay(root: Path, rows: list[dict[str, Any]], *, authority: Authority | None) -> list[dict[str, Any]]:
    """The verdict rows with the verifier's reading laid over each (rules in the module doc).

    Every returned row carries `review` (`{state, at}` plus `reviewer`/`reason`/`ticket`/`record`
    when a record supplied it). A row of a `scenario` run carries `oracle`, and a pass that may not
    count carries `not_counted`. The input rows are not mutated.
    """
    reviews = read_reviews(root, authority=authority)
    oracles = read_oracles(root, authority=authority)
    files: dict[str, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []
    for row in rows:
        new = dict(row)
        rel = str(row.get("file") or "")
        if rel not in files:
            loaded = _load(root / rel) if rel else None
            files[rel] = loaded if isinstance(loaded, dict) else {}
        result = files[rel]
        vid = str(row.get("id") or "")
        in_file: dict[str, Any] = {}
        for item in result.get("verdicts") or []:
            if isinstance(item, dict) and item.get("id") == vid:
                in_file = item
                break

        review: dict[str, Any] = {"state": UNVERIFIED, "at": ""}
        own = in_file.get("review")
        if isinstance(own, dict) and own.get("state") == DISPUTED:
            review = {"state": DISPUTED, "at": str(own.get("at") or "")}
        runner = _runner(result)
        record = reviews.get((rel, vid))
        if record is not None and runner and record["reviewer"] != runner:
            review = {key: value for key, value in record.items() if value}
            review.setdefault("at", "")
        new["review"] = review

        is_pass = str(row.get("verdict") or "") == "pass"
        version = result.get("scenario_version")
        if isinstance(version, int) and not isinstance(version, bool):
            decision = oracles.get((_scenario_of(vid, result), version), PENDING)
            new["oracle"] = decision
            if is_pass and decision != APPROVED:
                new["not_counted"] = {
                    REJECTED: f"expected results v{version} were rejected by the verifier",
                    CHANGED: f"expected results v{version} changed since the verifier approved them",
                }.get(decision, f"expected results v{version} await the verifier's approval")
        elif str(row.get("kind") or result.get("kind") or "") == SCENARIO_KIND:
            new["oracle"] = PENDING
            if is_pass:
                new["not_counted"] = "the scenario run names no version, so no approved expected result covers it"
        out.append(new)
    return out


def counts(row: dict[str, Any]) -> bool:
    """False for a verdict the verifier disputed or whose expected results are not approved."""
    review = row.get("review")
    if isinstance(review, dict) and review.get("state") == DISPUTED:
        return False
    return not row.get("not_counted")


def reading(root: Path, *, authority: Authority | None) -> dict[str, Any]:
    """Everything the verifier recorded that the desk shows beside the verdict rows — one call.

    `{"disputed": [{result_file, id, ticket, reason, at, reviewer}], "weak": {scenario: outcome},
    "planted": {scenario: outcome}, "oracles": [{scenario, version, state}]}`. A dispute is listed
    only when it is the latest review of its verdict and its result names a runner other than the
    reviewer — the same rule :func:`overlay` applies.
    """
    disputed: list[dict[str, Any]] = []
    for (result_file, vid), review in sorted(read_reviews(root, authority=authority).items()):
        if review["state"] != DISPUTED:
            continue
        result = _load(root / result_file)
        runner = _runner(result) if isinstance(result, dict) else ""
        if not runner or runner == review["reviewer"]:
            continue
        disputed.append(
            {
                "result_file": result_file,
                "id": vid,
                "ticket": review["ticket"],
                "reason": review["reason"],
                "at": review["at"],
                "reviewer": review["reviewer"],
            }
        )
    planted = read_planted(root, authority=authority)
    return {
        "disputed": disputed,
        "weak": {scenario: outcome for scenario, outcome in planted.items() if not outcome["caught"]},
        "planted": planted,
        "oracles": [
            {"scenario": scenario, "version": version, "state": state}
            for (scenario, version), state in sorted(read_oracles(root, authority=authority).items())
        ],
    }

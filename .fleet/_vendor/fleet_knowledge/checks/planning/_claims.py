"""Id claims — an atomic, server-side reservation of every contended id, as a git ref.

**Why a ref.** Every earlier allocator was a SNAPSHOT: read the highest id on the trunk tip,
on every open peer PR and in the local tree, and hand out the next one. Two sessions that
allocate before either pushes still pick the same number, because an id being authored is
invisible to every peer until its PR exists — and authoring takes hours. Measured on the
consuming corpus, 2026-09-28: six PRs landed FLT rows inside seven hours, two of them renumbered
after the fact, and eight ids were burned by skip-reservations — all with the peer scan in
force.

The one primitive that closes that window is a compare-and-swap on a server every author
already depends on. GitHub's `POST /repos/{owner}/{repo}/git/refs` is exactly that: creating
`refs/ids/<ID>` succeeds once, and every later create returns **HTTP 422 "Reference already
exists"**. So allocation becomes: start at the floor, try to create the ref, and on 422 try the
next number. The ids keep their shape (`FLT-051`), nothing is rewritten at merge, and no
committed file is edited by a mint.

`refs/ids/*` is outside the default fetch refspec, so no clone carries the namespace; it is read
with one `git ls-remote`. An abandoned claim is a gap, which the corpus already treats as free.

**Transport.** Reading uses `git ls-remote` against the configured remote, so it authenticates
exactly the way the checkout already does (a CI job's persisted checkout credential, a
workstation's credential helper). Creating one claim uses `gh api`, which reads its token from
`GH_TOKEN` / `GITHUB_TOKEN` or its own keyring — **never from argv**. The bulk back-fill pushes
the refs over git in batches, because the REST create is a content-creating call GitHub
rate-limits to a few hundred an hour and a back-fill is thousands.

Every GitHub call sits behind the `ClaimStore` protocol so the check and the allocator are
tested against fakes, and a failure to reach GitHub is a distinct answer (`ClaimsUnavailableError`)
— never an empty claim set, which would read every id as unclaimed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Protocol

#: Bounds every network call so a wedged connection cannot hang a hook. A hang detector, not a
#: performance budget: a healthy `ls-remote` over a few thousand refs is well under a second.
NETWORK_TIMEOUT_S = 60

#: Refs per `git push` in the back-fill. GitHub refuses pushes that update too many refs at once;
#: a few hundred per push is far under that and still turns thousands of claims into a handful
#: of round trips.
PUSH_BATCH = 500

_GITHUB_REMOTE_RE = re.compile(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


class ClaimsUnavailableError(Exception):
    """GitHub could not be asked — offline, unauthenticated, or a non-CAS error.

    Distinct from "nothing is claimed": a caller that reads this as an empty set would report
    every id as unclaimed (the check) or hand out an unreserved id (the allocator).
    """


class ClaimStore(Protocol):
    """Where claims live. `GitHubClaims` in production; a fake in tests."""

    def claimed(self) -> set[str]:
        """Every claimed id (the ref name after the namespace). Raises `ClaimsUnavailableError`."""
        ...

    def claim(self, cid: str, sha: str) -> bool:
        """Create the claim for `cid` pointing at `sha`.

        True when this call created it, False when it already existed (HTTP 422 "Reference
        already exists" — someone holds it). Raises `ClaimsUnavailableError` on anything else.
        """
        ...

    def claim_many(self, targets: Mapping[str, str]) -> int:
        """Create every `{cid: sha}` claim not already present; return how many were created."""
        ...

    def claim_batch(self, targets: Mapping[str, str]) -> set[str]:
        """Create every `{cid: sha}` claim in one push; return the names actually created.

        The allocator's block reservation, and distinct from `claim_many` in ONE way: a
        per-ref rejection is a LOST RACE, not an error. GitHub's atomic create refuses a
        ref another session took (HTTP 422 / a `!` porcelain line), and the allocator must
        walk past it to the next free number — aborting instead would hand back nothing
        because a peer happened to be allocating at the same moment. A push that reached
        no ref at all (an unreachable remote, a wedged network) still raises
        `ClaimsUnavailableError`: an unavailable store must never read as "nothing held".
        """
        ...


def claim_name(space: str, cid: str) -> str:
    """The claim name for an id in one of the id spaces.

    A PRD number is a bare four-digit id in its frontmatter; the claim namespace is flat, so it
    is claimed as `PRD-NNNN` — the shape `format_id` already reserves for it in messages.
    Every other space's id is already prefixed and is claimed as itself.
    """
    return f"PRD-{cid}" if space == "PRD" else cid


def github_slug(url: str) -> str | None:
    """`owner/repo` from a GitHub remote URL (https or ssh), or None."""
    m = _GITHUB_REMOTE_RE.search(url.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


class GitHubClaims:
    """Claims as `refs/ids/<ID>` on the repository behind `remote`."""

    def __init__(self, root: Path, *, remote: str = "origin", namespace: str = "refs/ids/", repo: str = "") -> None:
        self.root = root
        self.remote = remote
        self.namespace = namespace if namespace.endswith("/") else namespace + "/"
        self._repo = repo

    # -- reading ---------------------------------------------------------------------------

    def claimed(self) -> set[str]:
        try:
            proc = subprocess.run(
                ["git", "ls-remote", "--refs", self.remote, f"{self.namespace}*"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=NETWORK_TIMEOUT_S,
                env=os.environ.copy(),
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ClaimsUnavailableError(f"`git ls-remote {self.remote}` failed: {e}") from e
        if proc.returncode != 0:
            detail = proc.stderr.strip()
            raise ClaimsUnavailableError(f"`git ls-remote {self.remote}` exited {proc.returncode}: {detail}")
        out: set[str] = set()
        for line in proc.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2 and parts[1].startswith(self.namespace):
                out.add(parts[1][len(self.namespace) :])
        return out

    # -- one atomic claim -------------------------------------------------------------------

    def repo(self) -> str:
        """`owner/repo` — configured, or derived from the remote's URL."""
        if self._repo:
            return self._repo
        try:
            url = subprocess.run(
                ["git", "remote", "get-url", self.remote],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=NETWORK_TIMEOUT_S,
            ).stdout
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ClaimsUnavailableError(f"cannot read remote `{self.remote}`: {e}") from e
        slug = github_slug(url)
        if not slug:
            shown = url.strip() or "unset"
            raise ClaimsUnavailableError(f"remote `{self.remote}` ({shown}) is not a GitHub repository")
        self._repo = slug
        return slug

    def claim(self, cid: str, sha: str) -> bool:
        # `gh api` authenticates from GH_TOKEN / GITHUB_TOKEN or its keyring; the token never
        # appears on this argv. `-f` fields are the ref name and a commit sha — not secrets.
        try:
            proc = subprocess.run(
                [
                    "gh",
                    "api",
                    "--method",
                    "POST",
                    f"repos/{self.repo()}/git/refs",
                    "-f",
                    f"ref={self.namespace}{cid}",
                    "-f",
                    f"sha={sha}",
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=NETWORK_TIMEOUT_S,
                env=os.environ.copy(),
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ClaimsUnavailableError(f"`gh api` could not run: {e}") from e
        return parse_create_response(proc.returncode, proc.stdout, proc.stderr)

    # -- the back-fill ----------------------------------------------------------------------

    def _push(self, specs: list[str]) -> tuple[set[str], list[str], subprocess.CompletedProcess[str]]:
        """One `git push --porcelain` of claim refspecs.

        Returns `(created names, rejected names, process)`. Git prints one porcelain line
        per ref: `*` created, `!` rejected (a taken ref, or an update hook refusing one),
        `=` already at the target. The caller decides whether a rejection is a hard error
        (`claim_many`, which back-fills and must not exit 0 leaving ids unclaimed) or a
        lost race (`claim_batch`, which walks past it).
        """
        try:
            proc = subprocess.run(
                ["git", "push", "--porcelain", self.remote, *specs],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=NETWORK_TIMEOUT_S * 10,
                env=os.environ.copy(),
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ClaimsUnavailableError(f"`git push` of {len(specs)} claim(s) failed: {e}") from e
        created: set[str] = set()
        rejected: list[str] = []
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            flag, refspec = parts[0], parts[1]
            name = refspec.rsplit(":", 1)[-1]
            name = name[len(self.namespace) :] if name.startswith(self.namespace) else name
            if flag == "*":
                created.add(name)
            elif flag == "!":
                rejected.append(name)
        return created, rejected, proc

    def claim_many(self, targets: Mapping[str, str]) -> int:
        held = self.claimed()
        todo = {cid: sha for cid, sha in targets.items() if cid not in held}
        created = 0
        items = sorted(todo.items())
        for i in range(0, len(items), PUSH_BATCH):
            batch = items[i : i + PUSH_BATCH]
            specs = [f"{sha}:{self.namespace}{cid}" for cid, sha in batch]
            got, rejected, proc = self._push(specs)
            # Porcelain `!` is a rejected/failed ref — still non-empty stdout, so a returncode-only
            # check would swallow it as "0 created" (ENG-13191).
            if rejected or (proc.returncode != 0 and not proc.stdout.strip()):
                detail = "\n".join(rejected) if rejected else proc.stderr.strip()
                raise ClaimsUnavailableError(f"`git push` of claims exited {proc.returncode}: {detail or 'no output'}")
            created += len(got)
        return created

    def claim_batch(self, targets: Mapping[str, str]) -> set[str]:
        created: set[str] = set()
        items = sorted(targets.items())
        for i in range(0, len(items), PUSH_BATCH):
            batch = items[i : i + PUSH_BATCH]
            specs = [f"{sha}:{self.namespace}{cid}" for cid, sha in batch]
            got, _rejected, proc = self._push(specs)
            # A rejection (`!`) is a lost race and is returned as "not created" — but a push
            # that reached NOTHING (no porcelain line, non-zero) is an unavailable store.
            if proc.returncode != 0 and not proc.stdout.strip():
                raise ClaimsUnavailableError(
                    f"`git push` of claims exited {proc.returncode}: {proc.stderr.strip() or 'no output'}"
                )
            created |= got
        return created


def parse_create_response(returncode: int, stdout: str, stderr: str) -> bool:
    """Read a `gh api POST git/refs` result: created, already claimed, or unavailable.

    Only a 422 whose message is "Reference already exists" is a lost race. A 422 for any other
    reason — an object GitHub does not have, a malformed ref name — is not "someone holds it",
    and treating it as one would walk the allocator up the number line forever.
    """
    if returncode == 0:
        return True
    text = f"{stdout}\n{stderr}"
    message = ""
    try:
        body = json.loads(stdout) if stdout.strip().startswith("{") else {}
        message = str(body.get("message", "")) if isinstance(body, dict) else ""
    except json.JSONDecodeError:
        message = ""
    if "Reference already exists" in (message or text):
        return False
    raise ClaimsUnavailableError(f"claim refused (exit {returncode}): {(message or stderr or stdout).strip()[:300]}")


def claim_mode(enabled: bool, environ: Mapping[str, str] | None = None) -> str:
    """`off`, `warn` or `require` — how the collision check treats an unclaimed new id.

    `FLEET_ID_CLAIMS` overrides. Otherwise a corpus that has not configured claims is `off`, and
    one that has is `require` in CI (a `CI` variable set truthy, as every CI provider does) and
    `warn` everywhere else: a pre-commit hook must never block an offline commit, and CI must
    never pass a change it could not check.
    """
    env = os.environ if environ is None else environ
    forced = env.get("FLEET_ID_CLAIMS", "").strip().lower()
    if forced in {"off", "warn", "require"}:
        return forced
    if not enabled:
        return "off"
    return "require" if env.get("CI", "").strip().lower() in {"1", "true", "yes"} else "warn"


def highest(claimed: Iterable[str], prefix: str) -> int:
    """The highest claimed number under `prefix`, or 0."""
    pat = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    best = 0
    for cid in claimed:
        m = pat.match(cid)
        if m:
            best = max(best, int(m.group(1)))
    return best

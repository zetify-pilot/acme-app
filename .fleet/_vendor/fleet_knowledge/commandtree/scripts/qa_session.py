#!/usr/bin/env python3
"""Sign a browser in from an environment record, or clear its saved session.

This is a shipped helper (it lives in `commandtree/scripts/` and is materialized into a
repository as `knowledge/scripts/qa_session.py`). A QA run uses it to obtain a signed-in
session **outside** the browser: the helper reads the environment record, sends the one sign-in
request it describes, and writes only the answer's cookies into the Playwright storage-state
file the browser tool already reads. The login and password never leave this process, are never
printed and are never passed on a command line.

Two verbs:

    qa_session.py sign-in --environment <id> --role <role>
    qa_session.py clear

`sign-in` reads `<root>/knowledge/environments/<id>.json` as raw JSON (never the redacted
reader). A principal entry may carry:

    "session": {"sign_in": "/api/auth/login", "format": "json" | "form",
                "fields": ["<login field>", "<password field>"]}

`sign_in` is a path on the record's `base_url`; the request is a POST. `fields` names the
login's field first and the password's second. Both the login and the password are
`fleet-secret://<name>` references read from `$FLEET_SECRETS_DIR/<name>`.

**The record is compared against the environment the fleet approved.** The daemon exports
`FLEET_QA_ENVIRONMENT` and `FLEET_QA_BASE_URL` from the lease, which read them from the served
environment record and the page pause. `sign-in` refuses when either is absent, when
`--environment` names a different environment, when the record's `base_url` differs, or when
the record says `paused: true`. The checkout's record is data a run can write, so it is never
believed on its own.

**The destination comes from trusted state, never from the record alone.** The record is data a
QA run may write, so it cannot be the authority on where its login goes. The host in `base_url`
must be on the `hosts` list under `[fleet.recurring] qa` in the repository's `.fleet/fleet.toml`
(an absent or empty list approves nothing). A plain `http://` URL is allowed only for a loopback
host; every other host needs `https://`. A mismatch is refused with `state: blocked`, exit 3,
before any request is sent.

`clear` writes the empty state, for a step that signs in as nobody.

Output is exactly one JSON line on stdout and never a value, a response body or a header:

    {"state": "signed-in", "role": "<role>"}                        exit 0
    {"state": "cleared"}                                            exit 0
    {"state": "blocked", "cause": "environment", "reason": "<why>"} exit 3

The response body is read and dropped; only cookies are kept. Each `Set-Cookie` becomes one
Playwright storage-state cookie. The state file is replaced in one atomic rename, mode 0600.

`--root <path>` exists so a test can run the helper against a fixture (default: this checkout).

`QA_SESSION_TIMEOUT` sets the request's time limit in seconds (default 30); it exists so a test
can prove the timeout path without waiting half a minute. Stdlib only, permanently.
"""

from __future__ import annotations

import argparse
import contextlib
import http.client
import ipaddress
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

# `tomllib` is 3.11. Refuse in one plain sentence on an older interpreter, before the import
# (`gen_program_plan.py` does the same), rather than escape as a raw traceback.
_repo.require_python()
import tomllib  # noqa: E402

ENVIRONMENTS_SUBDIR = "knowledge/environments"
CONFIG_SUBDIR = ".fleet"
CONFIG_NAME = "fleet.toml"
HOSTS_KEY = "hosts"
SECRET_PREFIX = "fleet-secret://"
STATE_ENV = "PLAYWRIGHT_MCP_STORAGE_STATE"
SECRETS_ENV = "FLEET_SECRETS_DIR"
TIMEOUT_ENV = "QA_SESSION_TIMEOUT"
APPROVED_ENVIRONMENT_ENV = "FLEET_QA_ENVIRONMENT"
APPROVED_BASE_URL_ENV = "FLEET_QA_BASE_URL"
DEFAULT_TIMEOUT = 30.0
#: The same rule as the daemon's `secretsdir.NAME_RULE`: a letter or digit first, then letters,
#: digits, `.`, `_` and `-`. This script is stdlib-only and ships into every repository, so the
#: rule is repeated here rather than imported. `index.json` is the directory's own list, never a
#: secret.
SECRET_NAME_RULE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SECRET_INDEX_FILE = "index.json"
#: An environment record id — the filename stem under `knowledge/environments/` — as
#: `check_result.py` validates it: lowercase letters, digits and hyphens, starting alphanumeric.
ENVIRONMENT_ID_RULE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
NO_STATE_REASON = (
    "this run has no private place for a browser session; its login must be a Fleet secret scoped to this repository"
)
NO_APPROVAL_REASON = (
    "this run has no approved QA environment; the sign-in helper runs only for the environment the fleet approved"
)


class BlockedError(Exception):
    """A condition that leaves the step blocked, carrying the reason a person reads."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _read_below(path: Path, home: Path) -> str:
    """The text of a regular file whose real path stays under `home`, refusing a symlink.

    `path` is built from a value an agent can supply, so a lexical check is not enough: a `..`
    segment, an absolute path, or a symlink at the last component could name a file outside the
    one home the helper may read. The real path must stay under `home`, a symlink is refused
    outright, and the last component is opened `O_NOFOLLOW`. Raises `OSError` for every refusal,
    so each caller turns it into its own blocked reason.
    """
    if path.is_symlink():
        raise OSError(f"{path} is a symlink")
    if not path.resolve().is_relative_to(home):
        raise OSError(f"{path} leaves {home}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
        return handle.read()


def _secret_filename(name: str) -> str:
    """The filename a secret is read under, or `""` when it names no file.

    The daemon refuses any name outside `NAME_RULE` and reserves `index.json`
    (`secretsdir.secret_filename`). A name this helper cannot map to exactly one file is not
    available to the run.
    """
    return name if SECRET_NAME_RULE.fullmatch(name) and name != SECRET_INDEX_FILE else ""


def _load_record(root: Path, environment_id: str) -> dict[str, Any]:
    """The environment record as written, or a plain blocked reason.

    `--environment` arrives on the command line, so only a safe slug reads a record. The record
    must name its own id and must be a real file under `knowledge/environments/`; a `..`
    segment, an absolute path, or a symlink reads nothing.
    """
    reason = f"the environment record {environment_id} could not be read"
    if not ENVIRONMENT_ID_RULE.fullmatch(environment_id):
        raise BlockedError(reason)
    home = (root / ENVIRONMENTS_SUBDIR).resolve()
    try:
        raw = json.loads(_read_below(home / f"{environment_id}.json", home))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        raise BlockedError(reason) from None
    if not isinstance(raw, dict) or raw.get("id") != environment_id:
        raise BlockedError(reason)
    return raw


def _approval(environment_id: str) -> tuple[str, str]:
    """The environment and address the fleet approved for this run, from its environment.

    The daemon exports both from the lease, which the service took from the served environment
    record and the page pause. A record in the checkout is data a run can write, so it is compared
    against this trusted pair rather than believed.
    """
    approved = os.environ.get(APPROVED_ENVIRONMENT_ENV, "").strip()
    base_url = os.environ.get(APPROVED_BASE_URL_ENV, "").strip()
    if not approved or not base_url:
        raise BlockedError(NO_APPROVAL_REASON)
    if environment_id != approved:
        raise BlockedError(f"the environment {environment_id} is not the one this run was approved for ({approved})")
    return approved, base_url


def _principal(record: dict[str, Any], role: str) -> dict[str, Any]:
    """The principal entry holding `role`, or the first blocked reason."""
    principals = record.get("principals")
    if isinstance(principals, list):
        for item in principals:
            if isinstance(item, dict) and item.get("role") == role:
                return item
    raise BlockedError(f"the environment record lists no principal with the role {role}")


def _session(principal: dict[str, Any], role: str) -> tuple[str, str, list[str]]:
    """`(sign_in, format, fields)` from the principal's `session`, or a blocked reason."""
    reason = f"the environment record does not say how {role} signs in; add session to that principal"
    session = principal.get("session")
    if not isinstance(session, dict):
        raise BlockedError(reason)
    sign_in = session.get("sign_in")
    format_name = session.get("format")
    fields = session.get("fields")
    if not isinstance(sign_in, str) or not sign_in:
        raise BlockedError(reason)
    if format_name not in ("json", "form"):
        raise BlockedError(reason)
    if not isinstance(fields, list) or len(fields) != 2:
        raise BlockedError(reason)
    first, second = fields
    if not isinstance(first, str) or not first or not isinstance(second, str) or not second:
        raise BlockedError(reason)
    return sign_in, str(format_name), [first, second]


def _scheme(reference: Any) -> str:
    """The text before `://` in a reference (`sm://…` → `sm`), or empty."""
    if isinstance(reference, str) and "://" in reference:
        return reference.split("://", 1)[0]
    return ""


def _references(principal: dict[str, Any], role: str) -> tuple[str, str]:
    """The login and password `fleet-secret://` references, login checked first."""
    reason = f"the login of {role} must be a Fleet secret for a browser step, not "
    login = principal.get("login")
    if not isinstance(login, str) or not login.startswith(SECRET_PREFIX):
        raise BlockedError(reason + _scheme(login))
    password = principal.get("password")
    if not isinstance(password, str) or not password.startswith(SECRET_PREFIX):
        raise BlockedError(reason + _scheme(password))
    return login, password


def _state_path() -> Path:
    """The storage-state file this run may write, or the blocked reason when it has none."""
    value = os.environ.get(STATE_ENV, "")
    if not value:
        raise BlockedError(NO_STATE_REASON)
    path = Path(value)
    if not path.exists():
        raise BlockedError(NO_STATE_REASON)
    return path


def _secret_value(reference: str, role: str) -> str:
    """The secret file's text for one reference, or a blocked reason naming the reference.

    The name comes from the environment record, so only a name the daemon would store as a file
    is read. A `..` segment, an absolute path, `personal/…`, `shared/…` or `index.json` reads
    nothing, and neither does a symlink out of the secrets directory.
    """
    name = reference[len(SECRET_PREFIX) :]
    reason = f"the login of {role} is not available to this run: {name}"
    base = os.environ.get(SECRETS_ENV, "")
    if not base:
        raise BlockedError(reason)
    filename = _secret_filename(name)
    if not filename:
        raise BlockedError(reason)
    home = Path(base).resolve()
    try:
        text = _read_below(home / filename, home)
    except (OSError, UnicodeDecodeError):
        raise BlockedError(reason) from None
    if text.endswith("\r\n"):
        return text[:-2]
    if text.endswith("\n"):
        return text[:-1]
    return text


def _timeout() -> float:
    """`QA_SESSION_TIMEOUT` in seconds, defaulting to 30 when unset or not a positive number."""
    raw = os.environ.get(TIMEOUT_ENV, "")
    if not raw:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT
    return value if value > 0 else DEFAULT_TIMEOUT


def _normalise_host(value: str) -> str:
    """A host name compared without case or a trailing root dot."""
    return value.strip().lower().rstrip(".")


def _approved_hosts(root: Path) -> tuple[str, ...]:
    """The hosts this repository approves for a QA sign-in, from `[fleet.recurring] qa.hosts`.

    Read from the repository's own config, never from the environment record: the record is data
    a QA run may write, so it cannot say where its own login goes. An absent, empty or malformed
    list approves nothing, which is the safe direction.
    """
    path = root / CONFIG_SUBDIR / CONFIG_NAME
    if not path.is_file():
        path = root / CONFIG_NAME
    if not path.is_file():
        return ()
    try:
        data: Any = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return ()
    for key in ("fleet", "recurring", "qa"):
        if not isinstance(data, dict):
            return ()
        data = data.get(key, {})
    raw = data.get(HOSTS_KEY, []) if isinstance(data, dict) else []
    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        return ()
    return tuple(_normalise_host(item) for item in raw)


def _loopback(host: str) -> bool:
    """Whether `host` names this machine's loopback interface, where plain `http` stays local."""
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _destination_refusal(root: Path, environment_id: str, split: SplitResult) -> str | None:
    """Why this sign-in may not go to `split`, or `None` when the destination is approved.

    Two rules, both from trusted state: a plain `http` URL is allowed only for a loopback host,
    and the host must be on the repository's `qa.hosts` list. The record's `base_url` supplies
    the host; it never supplies the authority.
    """
    host = _normalise_host(split.hostname or "")
    if split.scheme == "http" and not _loopback(host):
        return (
            f"the environment record {environment_id} names a plain http URL for a host that is not loopback; use https"
        )
    if host not in _approved_hosts(root):
        return (
            f"the environment record {environment_id} names a host this repository does not "
            "approve for QA sign-in; add that host to qa.hosts"
        )
    return None


def _post(
    base_url: str, sign_in: str, format_name: str, fields: list[str], login: str, password: str
) -> tuple[int, list[str]]:
    """Send the one POST without following a redirect; answer `(status, Set-Cookie headers)`."""
    split = urlsplit(base_url)
    path = split.path.rstrip("/") + "/" + sign_in.lstrip("/")
    values = {fields[0]: login, fields[1]: password}
    if format_name == "json":
        body = json.dumps(values).encode("utf-8")
        content_type = "application/json"
    else:
        body = urlencode(values).encode("utf-8")
        content_type = "application/x-www-form-urlencoded"
    connection_class = http.client.HTTPSConnection if split.scheme == "https" else http.client.HTTPConnection
    connection = connection_class(split.hostname or "", split.port, timeout=_timeout())
    try:
        connection.request("POST", path, body=body, headers={"Content-Type": content_type})
        response = connection.getresponse()
        response.read()
        status = response.status
        cookies = response.headers.get_all("Set-Cookie") or []
    finally:
        connection.close()
    return status, cookies


def _same_site(value: str) -> str:
    """A cookie's `SameSite` in the browser-state spelling, defaulting to `Lax`."""
    lowered = value.lower()
    if lowered == "strict":
        return "Strict"
    if lowered == "none":
        return "None"
    return "Lax"


def _cookie_expiry(morsel: Any, now: int) -> int:
    """Epoch seconds for a cookie: Max-Age wins, else Expires, else -1 for a session cookie."""
    max_age = morsel["max-age"]
    if max_age:
        try:
            return now + int(max_age)
        except ValueError:
            return -1
    expires = morsel["expires"]
    if expires:
        parsed: datetime | None
        try:
            parsed = parsedate_to_datetime(expires)
        except (TypeError, ValueError):
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp())
    return -1


def _cookies(headers: list[str], host: str) -> list[dict[str, Any]]:
    """Every `Set-Cookie` header as one Playwright storage-state cookie."""
    now = int(time.time())
    cookies: list[dict[str, Any]] = []
    for header in headers:
        jar: SimpleCookie = SimpleCookie()
        try:
            jar.load(header)
        except CookieError:
            continue
        for morsel in jar.values():
            cookies.append(
                {
                    "name": morsel.key,
                    "value": morsel.value,
                    "domain": morsel["domain"] or host,
                    "path": morsel["path"] or "/",
                    "expires": _cookie_expiry(morsel, now),
                    "httpOnly": bool(morsel["httponly"]),
                    "secure": bool(morsel["secure"]),
                    "sameSite": _same_site(morsel["samesite"]),
                }
            )
    return cookies


def _write_state(path: Path, cookies: list[dict[str, Any]]) -> None:
    """Write `{"cookies": ..., "origins": []}` through a same-folder temp file, mode 0600."""
    data = {"cookies": cookies, "origins": []}
    fd, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temp_name)
        raise


def _sign_in(root: Path, environment_id: str, role: str) -> dict[str, Any]:
    """Sign in as `role` and write its cookies; refuse in the design's order."""
    _approved_environment, approved_base_url = _approval(environment_id)
    record = _load_record(root, environment_id)
    record_base_url = record.get("base_url")
    if not isinstance(record_base_url, str) or record_base_url.rstrip("/") != approved_base_url.rstrip("/"):
        raise BlockedError(f"the environment record {environment_id} does not match the address the fleet approved")
    if record.get("paused") is True:
        raise BlockedError(f"the environment {environment_id} is paused")
    principal = _principal(record, role)
    sign_in, format_name, fields = _session(principal, role)
    login_ref, password_ref = _references(principal, role)
    state = _state_path()
    login = _secret_value(login_ref, role)
    password = _secret_value(password_ref, role)
    base_url = record.get("base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise BlockedError(f"the environment record {environment_id} has no base_url")
    try:
        split = urlsplit(base_url)
        if split.scheme not in ("http", "https") or not split.hostname:
            raise BlockedError(f"the environment record {environment_id} has no base_url")
        refusal = _destination_refusal(root, environment_id, split)
        if refusal is not None:
            raise BlockedError(refusal)
        status, headers = _post(base_url, sign_in, format_name, fields, login, password)
    except (OSError, http.client.HTTPException, TimeoutError, ValueError):
        raise BlockedError(f"the sign-in of {role} did not answer") from None
    if not 200 <= status < 400:
        raise BlockedError(f"the sign-in of {role} answered {status}")
    cookies = _cookies(headers, split.hostname)
    if not cookies:
        raise BlockedError(f"the sign-in of {role} set no cookie; Fleet hands a browser cookies only")
    _write_state(state, cookies)
    return {"state": "signed-in", "role": role}


def _clear() -> dict[str, Any]:
    """Write the empty browser state."""
    _write_state(_state_path(), [])
    return {"state": "cleared"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sign a browser in from an environment record, or clear its state.")
    sub = parser.add_subparsers(dest="command", required=True)
    sign_in = sub.add_parser("sign-in", help="sign in as one principal and write its cookies")
    sign_in.add_argument("--environment", required=True, help="the environment record id")
    sign_in.add_argument("--role", required=True, help="the principal role to sign in as")
    sign_in.add_argument("--root", default="", help="the checkout to read (default: this repo)")
    clear = sub.add_parser("clear", help="write the empty browser state")
    clear.add_argument("--root", default="", help="the checkout to read (default: this repo)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else _repo.repo_root()
    try:
        result = _sign_in(root, args.environment, args.role) if args.command == "sign-in" else _clear()
    except BlockedError as exc:
        print(json.dumps({"state": "blocked", "cause": "environment", "reason": exc.reason}))
        return 3
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

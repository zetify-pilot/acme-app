"""`fleet check`'s `environment-records`: a QA environment holds references, never secrets.

`knowledge/environments/<id>.json` says where a QA run may drive and which principals sign in.
Its credentials are secret-store references (`sm://…`, or `fleet-secret://<label>` for a secret
held in Fleet's own Secrets store). A literal value under a credential-shaped key is a secret
written into the corpus, and the Quality desk would serve it to every signed-in reader.

The reader withholds such a value at serve time (`fleet_knowledge.quality.read_environments`),
which is the second line of defence. This check is the first: it refuses the record at commit
time, so a literal secret never reaches the corpus at all (FLT-1275, ENG-21072).

Applies only to a checkout that has an environments home, so a repository without the Quality
desk skips it with a line saying so.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.quality import (
    ENVIRONMENTS_SUBDIR,
    environment_secret_violations,
    read_environment_records,
    step_problems,
)
from fleet_knowledge.runner import Finding


class EnvironmentRecords:
    name = "environment-records"
    title = "Environment records hold secret references, never secret values"
    description = (
        "Every credential in a record under knowledge/environments/ is a secret-store reference "
        "(sm://… or fleet-secret://…); a literal value under a password, token, login or other "
        "credential key fails the build, because the desk would serve it to every signed-in reader."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return (kb.root / ENVIRONMENTS_SUBDIR).is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        findings = [
            Finding(
                level="error",
                message=f"{where} holds a literal secret — a credential is a secret-store reference only",
                path=path,
                hint=(
                    "replace the value with `sm://<project>/<name>` or `fleet-secret://<label>` "
                    "and store the value in the secret store"
                ),
            )
            for path, where in environment_secret_violations(kb.root)
        ]
        for path, record in read_environment_records(kb.root):
            findings.extend(
                Finding(
                    level="error",
                    message=problem,
                    path=path,
                    hint=(
                        'a step is `{"run": ["program", "arg"], "env": {"NAME": '
                        '"fleet-secret://label"}}`; `start` and `stop` need at least one step, and a '
                        "record with steps names a `version_probe`"
                    ),
                )
                for problem in step_problems(record)
            )
            if "steps" in record and _says_production(record):
                findings.append(
                    Finding(
                        level="error",
                        message=(
                            "`steps` gives start steps and says production: a copy Fleet starts is never production"
                        ),
                        path=path,
                        hint=(
                            "remove `steps` from a production record, or run the copy on a record "
                            "that is not production"
                        ),
                    )
                )
        return findings


def _says_production(record: Mapping[str, Any]) -> bool:
    """Whether a record's `production` says true, in the shapes the guard's `_truthy` accepts."""
    value = record.get("production")
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.strip().lower() in ("true", "yes", "1")


CHECKS = [EnvironmentRecords()]

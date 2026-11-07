"""What a card addressed to a customer may never say (ENG-20785).

A customer install's people do not know Fleet's vocabulary. Measured on a customer install
(2026-10-27): two tasks sat in `Blocked · action` for four days asking the customer's own PRD
owners to run one of our commands with a program and a slice argument, write a `## Delivery log`,
and re-run another command — a task, a slice, a bar and a delivery cycle none of them had ever
heard of, for work that was theirs to give, not ours to hand them. Both were withdrawn.

The rule the issue records: acceptance in a customer's running app is the customer's to give,
asked as plain checks; a park whose action is a Fleet-internal step routes to the
install's operator, not to the customer. This module is the machine-checkable half: a card or
park document that declares `"audience": "customer"` may not name a slash command, a program id
(`PG-NN`), a slice id (`SL-NNN` or a criterion's `SLNNN-Cn`) or Fleet's own nouns ("bar",
"delivery cycle", "delivery log"). Plain product words only.

Dependency-free, like every module in this package. Imported by `questions` and `decisions` for
the box-side validators (`knowledge/scripts/validate_questions.py`,
`knowledge/scripts/validate_decision.py`) and by the service at the ask boundary, so the rule a
session is told in its own turn is the rule a later reader re-checks.
"""

from __future__ import annotations

import re
from typing import Any, Final

__all__ = [
    "CUSTOMER",
    "customer_addressed",
    "customer_document_refusals",
    "customer_words_in",
]

#: The one audience word this build knows. An absent `audience` means the card is Fleet's own
#: (a team member, an operator, a PRD owner inside the fleet) and the guard does not apply.
CUSTOMER: Final = "customer"

#: WHAT A CUSTOMER CARD MAY NOT NAME, and what each shape is called in the refusal. Ordered;
#: the first match in a piece of prose is the one reported.
_UNSAFE: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    # A slash command in any namespace — `/some-namespace:some-verb` — and the bare namespace
    # prefix (`/some-namespace:`) the issue names, which a customer may see before any verb
    # follows. One pattern covers both: the prefix alone is already our vocabulary, and this
    # module must not carry the product name the package's repo-independence test bans.
    (re.compile(r"(?<![\w/])/[a-z][a-z0-9-]*:"), "a Fleet command"),
    # A program id, a slice id, and a criterion id (`SL165-C1`, spelled without the slice dash).
    (re.compile(r"\bPG-\d+\b"), "a program id"),
    (re.compile(r"\bSL-\d+\b"), "a slice id"),
    (re.compile(r"\bSL\d+-C\d+\b"), "a criterion id"),
    # Fleet's own nouns. The issue names these three explicitly: they mean nothing to a
    # customer, and a card that uses them is asking in our vocabulary rather than theirs.
    (re.compile(r"\bdelivery[\s_-]*cycles?\b", re.IGNORECASE), 'the words "delivery cycle"'),
    (re.compile(r"\bdelivery[\s_-]*logs?\b", re.IGNORECASE), 'the words "delivery log"'),
    (re.compile(r"\bbars?\b", re.IGNORECASE), 'the word "bar"'),
)

#: Keys whose values are identifiers, links or machine flags rather than prose read by a person.
#: Their contents are not scanned: an option id (`run-it`) or a context ref (`AC-4`) is not a
#: sentence, and refusing one would be refusing the card's plumbing rather than its words.
_NOT_PROSE: Final[frozenset[str]] = frozenset(
    {
        "id",
        "ref",
        "audience",
        "kind",
        "format",
        "url",
        "condition",
        "settles",
        "bundleId",
        "entry",
        "recommended",
        "allowFreeText",
        "required",
    }
)

_RULE: Final = "customer-card-speaks-in-our-own-words"


def customer_addressed(document: object) -> bool:
    """Whether this result document says it is addressed to a customer."""
    return isinstance(document, dict) and str(document.get("audience") or "").strip().lower() == CUSTOMER


def customer_words_in(text: str) -> str | None:
    """The Fleet-internal phrase in `text`, with what the phrase is, or `None` when it is plain.

    Public because the command tier and its tests name the same shapes the document walk catches.
    """
    for pattern, what in _UNSAFE:
        found = pattern.search(text)
        if found is not None:
            return f'"{found.group(0)}" is {what}'
    return None


def _prose(value: Any, key: str = "") -> list[str]:
    if isinstance(value, str):
        return [] if key in _NOT_PROSE else [value]
    if isinstance(value, dict):
        return [text for name, item in value.items() for text in _prose(item, name)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _prose(item, key)]
    return []


def customer_document_refusals(document: object) -> list[str]:
    """Every place a customer-addressed card speaks in Fleet's own words, or `[]`.

    `document` is a whole result document — `questions`, `decision` or `action` — as the session
    wrote it to `$FLEET_RESULT_FILE`. A document that does not declare `"audience": "customer"`
    is Fleet's own and is not checked here. Each reason names the offending phrase and ends with
    the rule's code in backticks, so the session that wrote it can fix it in the same turn.
    """
    if not customer_addressed(document):
        return []
    reasons: list[str] = []
    seen: set[str] = set()
    for text in _prose(document):
        named = customer_words_in(text)
        if named is None or named in seen:
            continue
        seen.add(named)
        reasons.append(
            f"a card addressed to a customer says {named}. They do not use our commands or know "
            f"our ids and names: ask each check in the words of their own product "
            f"(`{_RULE}`)."
        )
    return reasons

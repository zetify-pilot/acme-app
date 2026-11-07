"""The interview card's rules for a `decision` result document, in one dependency-free place.

A fleet session that cannot continue without a person's ruling ends `needs-decision`, and the
issue parks at `Blocked · decision`. Until this module existed, what the person clearing that
park read was the session's end-of-run `summary` — written as "one sentence", read by somebody
who has never opened the issue, the PRD or any register. Measured on 79 implement/verify parks
in production (2026-09-27): **85% opened with a bare id**, 24% listed options, 16% named a
recommendation, median length 560 characters. The canonical example, ENG-11946:

    PRD 0676 AC-4 is not met as written: a marked comment by the fleet's own automated tracker
    account … while the register row BTR-012 records an owner-accepted fail-open … (a hardcoded
    tracker identity is forbidden by BTR-015). Please decide: (1) accept BTR-012's … Issue
    parked at Blocked · decision.

Every rule the interview card (`commandtree/process/interview-card.md`) states — what the work
is first, one concrete example, no bare ids, why and cost on every option, the recommendation
first — was already written down, and none of it was checked. The card's own Headless paragraph
binds an escalation to it; the commands that escalate most (`verify`, `prd:verify`, `check`)
did not even include it.

**This is the check.** One predicate, stdlib only (this package's rule), over the EXTENDED
`decision` document — the same `kind` the decision desk already reads, so an old document stays
readable and a new one carries what the card asks for:

    {"kind": "decision",
     "brief":    {"work": …, "example": …, "stopped": …, "stakes": …},
     "context":  [{"ref": "AC-4", "name": …, "quote": …, "url": …}, …],
     "question": {"id": …, "prompt": …,
                  "options": [{"id", "label", "why", "cost", "then", "recommended"}, …]}}

It returns a LIST of human-readable reasons (empty when the document meets the card), each
ending with the rule's code in backticks, because the reader is the session that wrote the
document — told every rule it broke, in its own turn, it can fix them all at once; told the
first one, it fixes that and meets the next on its second try. It is imported by:

  * the **service**, at the outcome edge (`fleet_service.api.agent`), handed to
    `dispatch.results.parse` as its `decision_judge` — the logic layer may not import this
    package (`tests/dispatch/test_purity.py`), so the predicate travels in as a parameter. A
    refused document still parks (the fail-safe direction: a person who reads a bad question
    can still answer it; one who is never asked cannot), and the reasons are recorded on the
    run as `askRefused`, where the Queue and `/metrics` read them;
  * the **box**, through the shipped `knowledge/scripts/validate_decision.py`, so the session
    checks its own draft before it writes the done-sentinel and can fix a refusal in its turn.

`find_ids` is exported beside it because the service's enrichment of LEGACY free-text asks
(`refs[]` on the backlog) has to recognise the same ids this predicate refuses bare — one
vocabulary, so the page cannot resolve an id the card does not know about or miss one it does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from .customerwords import customer_document_refusals

__all__ = [
    "BRIEF_FIELDS",
    "CONTEXT_MAX",
    "OPTIONS_MAX",
    "OPTIONS_MIN",
    "OPTION_FIELDS",
    "TEXT_MAX",
    "IdMention",
    "decision_refusals",
    "find_ids",
    "missing_document_reason",
    "summary_refusals",
]

#: The four things the card says come BEFORE the question, as the fields that carry them:
#: what the work is (`work`), one concrete example of a person doing it (`example`), what
#: stopped the run (`stopped`), and what is at stake either way (`stakes`).
BRIEF_FIELDS: Final[tuple[str, ...]] = ("work", "example", "stopped", "stakes")
#: Every option says why it is right, what it costs, and what happens if it is picked — on
#: EVERY option, or the person cannot pick against the recommendation.
OPTION_FIELDS: Final[tuple[str, ...]] = ("id", "label", "why", "cost", "then")
#: Two to four options — the decision desk's and 0071's bound, for 0071's reason.
OPTIONS_MIN: Final = 2
OPTIONS_MAX: Final = 4
#: Every text is read on a card, not a page. Mirrors `dispatch.results.DECISION_TEXT_MAX`.
TEXT_MAX: Final = 2000
#: A card that needs more than a dozen quoted sources is a document, not a question.
CONTEXT_MAX: Final = 12
#: The fewest words a brief field may be. A brief of "n/a" or "see PR" is the bare-id failure
#: arriving by another route.
BRIEF_WORDS_MIN: Final = 3

# ── the id vocabulary ────────────────────────────────────────────────────────
#
# ORDERED: on overlapping spans the earlier kind wins, so `ENG-11946` is an issue before it is a
# register-shaped id, and `SL-173` a slice before either.

_NUM_LIST: Final = r"(?:\s*(?:,|/|&|\band\b|\bor\b)\s*(?:ACs?[\s-]?)?\d+)*"

_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    # A slash command in any namespace — `/<namespace>:<verb>[:<verb>]` — so the tier ships no
    # product name (`test_no_module_hardcodes_a_repository_or_a_product_name`).
    ("command", re.compile(r"(?<![\w/])/[a-z][a-z-]*:[a-z][a-z:-]*[a-z]")),
    ("pr", re.compile(r"\bPR\s*#\s*\d+\b")),
    ("prd", re.compile(r"\bPRDs?\s*#?\s*\d{4}\b")),
    ("criterion", re.compile(r"\bACs?[\s-]?\d+\b" + _NUM_LIST)),
    ("slice", re.compile(r"\bSL-\d+\b")),
    ("program", re.compile(r"\bPG-\d+\b")),
    ("capability", re.compile(r"\bCAP-\d+\b")),
    ("issue", re.compile(r"\bENG-\d+\b")),
    ("requirement", re.compile(r"\b[A-Z]{2,4}-\d{3,}\b")),
)

#: Register-shaped strings that are not register ids. A false positive costs a session one
#: parenthetical; this list is the handful measured often enough to be worth not asking for.
_NOT_REGISTER: Final[frozenset[str]] = frozenset({"SHA", "ISO", "RFC", "UTF", "CVE", "TLS", "HTTP", "GH"})


@dataclass(frozen=True, slots=True)
class IdMention:
    """One id-shaped token in a text, as written, and the ids it names.

    `keys` is normalised — `AC-4`, `PRD 0676`, `PR #12478`, `ENG-11946` — and a list because one
    mention can name several: `ACs 1,2,3` is three criteria written once.
    """

    kind: str
    token: str
    start: int
    end: int
    keys: tuple[str, ...]


def _keys(kind: str, token: str) -> tuple[str, ...]:
    digits = re.findall(r"\d+", token)
    if kind == "criterion":
        return tuple(dict.fromkeys(f"AC-{int(d)}" for d in digits))
    if kind == "prd":
        return (f"PRD {digits[0]}",)
    if kind == "pr":
        return (f"PR #{digits[0]}",)
    return (token,)


def find_ids(text: str) -> list[IdMention]:
    """Every id-shaped token in `text`, left to right, overlaps resolved by kind order."""
    taken: list[IdMention] = []
    for kind, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            token = m.group(0)
            if kind == "requirement" and token.split("-", 1)[0] in _NOT_REGISTER:
                continue
            if any(m.start() < other.end and other.start < m.end() for other in taken):
                continue
            taken.append(IdMention(kind, token, m.start(), m.end(), _keys(kind, token)))
    return sorted(taken, key=lambda one: one.start)


# ── what counts as "named" ───────────────────────────────────────────────────

_WORD: Final = re.compile(r"[A-Za-z][A-Za-z'’-]+")


def _plain_words(text: str) -> int:
    """How many ordinary words `text` holds once every id is taken out of it."""
    stripped = text
    for mention in reversed(find_ids(text)):
        stripped = stripped[: mention.start] + " " + stripped[mention.end :]
    return len(_WORD.findall(stripped))


def _named_in_place(text: str, mention: IdMention) -> bool:
    """Whether the id is written the way the card allows: `plain name (ID)`, `ID (plain name)`,
    or `ID — plain name`.

    The parenthetical may hold several ids at once — `(PRD 0676, AC-4)` — as long as the words
    before it name the thing.
    """
    after = text[mention.end :]
    gloss = re.match(r"\s*\(([^()]*)\)", after)
    if gloss is not None and _plain_words(gloss.group(1)) >= 2:
        return True
    if re.match(r"\s*[—–]\s*\S", after) and _plain_words(after.split("\n", 1)[0][:120]) >= 2:
        return True
    opened = text.rfind("(", 0, mention.start)
    if opened != -1 and ")" not in text[opened : mention.start]:
        closing = text.find(")", mention.end)
        if closing != -1 and "(" not in text[mention.end : closing]:
            inner = text[opened + 1 : closing]
            before = text[:opened].rstrip()
            last_words = _WORD.findall(before[-80:])
            if _plain_words(inner) == 0 and len(last_words) >= 2:
                return True
    return False


def _normal(ref: str) -> tuple[str, ...]:
    """A context entry's `ref`, normalised the way `find_ids` normalises a mention's keys."""
    found = find_ids(ref)
    if found:
        return tuple(key for mention in found for key in mention.keys)
    return (ref.strip(),)


# ── the predicate ────────────────────────────────────────────────────────────

_BOILERPLATE: Final = re.compile(r"issue parked at|parked at\s+`?blocked|parked on\s+`?blocked", re.I)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def missing_document_reason() -> str:
    """The one reason a `needs-decision` park with no `decision` document at all carries."""
    return (
        "the run parked on a person (`needs-decision`) and wrote no `decision` document to "
        "$FLEET_RESULT_FILE, so the person clearing the park reads only a one-line summary with "
        "nothing to pick. Write the document the interview card describes — brief, context, and "
        "two to four options — and check it with `python3 knowledge/scripts/validate_decision.py` "
        "(`decision-document-missing`)."
    )


def decision_refusals(document: object) -> list[str]:
    """Every rule of the interview card this `decision` document breaks, or `[]`.

    `document` is the whole result document (`{"kind": "decision", …}`), as the session wrote it
    to `$FLEET_RESULT_FILE`. Total: a non-object, a wrong kind and every missing field has an
    answer. The reasons are for the session that wrote it, so each names the field and ends with
    its rule's code in backticks.
    """
    if not isinstance(document, dict):
        return [f"a decision is one JSON object and this is a {type(document).__name__} (`decision-not-an-object`)."]
    if document.get("kind") != "decision":
        return ['a decision document says `"kind": "decision"` (`decision-wrong-kind`).']
    reasons: list[str] = []
    texts: list[tuple[str, str]] = []

    brief = document.get("brief")
    if not isinstance(brief, dict):
        reasons.append(
            "the document carries no `brief`. The person answering has not read the issue, the PRD or "
            "any register: say what the work is (`work`), give one concrete example of a person "
            "doing it (`example`), what stopped the run (`stopped`) and what is at stake either way "
            "(`stakes`) — before the question (`decision-brief-missing`)."
        )
    else:
        for name in BRIEF_FIELDS:
            value = brief.get(name)
            if not _text(value) or len(str(value)) > TEXT_MAX:
                reasons.append(
                    f"`brief.{name}` must be a non-blank sentence of at most {TEXT_MAX} characters "
                    f"(`decision-brief-{name}`)."
                )
            elif _plain_words(str(value)) < BRIEF_WORDS_MIN:
                reasons.append(
                    f"`brief.{name}` is ids and fragments, not a sentence — write it in plain words "
                    f"(`decision-brief-{name}`)."
                )
            else:
                texts.append((f"brief.{name}", str(value)))

    quoted: set[str] = set()
    context = document.get("context", [])
    if not isinstance(context, list) or len(context) > CONTEXT_MAX:
        reasons.append(
            f"`context` is a list of at most {CONTEXT_MAX} entries, one per acceptance criterion, "
            f"requirement or issue the question leans on (`decision-context-shape`)."
        )
    else:
        for number, entry in enumerate(context, start=1):
            if not isinstance(entry, dict) or not _text(entry.get("ref")) or not _text(entry.get("name")):
                reasons.append(
                    f"context entry {number} needs a `ref` (the id, e.g. `AC-4`) and a `name` (what it "
                    f"is, in plain words) (`decision-context-shape`)."
                )
                continue
            if _plain_words(str(entry["name"])) < 2:
                reasons.append(
                    f"context entry {number}'s `name` is an id, not a name — say what "
                    f"`{entry['ref']}` is in plain words (`decision-context-name`)."
                )
            quote, url = entry.get("quote", ""), entry.get("url", "")
            if not isinstance(quote, str) or len(quote) > TEXT_MAX:
                reasons.append(
                    f"context entry {number}'s `quote` is the text the id stands for, at most "
                    f"{TEXT_MAX} characters (`decision-context-shape`)."
                )
                continue
            if url not in ("", None) and (not isinstance(url, str) or not re.match(r"https?://", url)):
                reasons.append(f"context entry {number}'s `url` must be an http(s) link (`decision-context-url`).")
            if quote.strip():
                quoted.update(_normal(str(entry["ref"])))

    question = document.get("question")
    if not isinstance(question, dict):
        reasons.append(
            "the document carries no `question` object: an id, a prompt, and two to four options "
            "(`decision-without-a-question`)."
        )
    else:
        if not _text(question.get("id")):
            reasons.append("the question needs an `id` (`decision-question-id`).")
        prompt = question.get("prompt")
        if not _text(prompt) or len(str(prompt)) > TEXT_MAX:
            reasons.append(
                f"the question needs a `prompt` of at most {TEXT_MAX} characters — the decision, in "
                f"plain words (`decision-question-prompt`)."
            )
        else:
            texts.append(("question.prompt", str(prompt)))
        options = question.get("options")
        if not isinstance(options, list) or not OPTIONS_MIN <= len(options) <= OPTIONS_MAX:
            reasons.append(
                f"a decision offers {OPTIONS_MIN} to {OPTIONS_MAX} options. One is a notification with "
                f"a button; past {OPTIONS_MAX} is a form (`decision-two-to-four-options`)."
            )
        else:
            seen: set[str] = set()
            for position, option in enumerate(options, start=1):
                if not isinstance(option, dict):
                    reasons.append(f"option {position} is not an object (`decision-option-shape`).")
                    continue
                missing = [name for name in OPTION_FIELDS if not _text(option.get(name))]
                if missing:
                    reasons.append(
                        f"option {position} is missing {', '.join(f'`{m}`' for m in missing)}. Every "
                        f"option says why it is right, what it costs and what happens if it is picked — "
                        f"not only the one you favour, or the person cannot pick against you "
                        f"(`decision-option-fields`)."
                    )
                if not isinstance(option.get("recommended"), bool):
                    reasons.append(
                        f"option {position} states `recommended` as true or false (`decision-option-shape`)."
                    )
                oid = option.get("id")
                if isinstance(oid, str) and oid in seen:
                    reasons.append(f"option {position}'s id `{oid}` repeats another's (`decision-option-id`).")
                if isinstance(oid, str):
                    seen.add(oid)
                label = option.get("label")
                if _text(label):
                    ids = find_ids(str(label))
                    if ids:
                        reasons.append(
                            f"option {position}'s label names {', '.join(f'`{m.token}`' for m in ids)}. A "
                            f"label is what a person picks, in plain words — ids belong in `why` or "
                            f"`context` (`decision-label-carries-an-id`)."
                        )
                for name in ("label", "why", "cost", "then"):
                    if _text(option.get(name)):
                        texts.append((f"option {position}.{name}", str(option[name])))
            flags = [isinstance(o, dict) and o.get("recommended") is True for o in options]
            if not flags or not flags[0]:
                reasons.append(
                    "the recommended option comes FIRST and is marked `recommended: true` "
                    "(`decision-recommendation-first`)."
                )
            elif sum(flags) > 1:
                reasons.append(
                    "exactly one option is recommended. Two recommendations are no recommendation "
                    "(`decision-recommendation-first`)."
                )

    bare: dict[str, list[str]] = {}
    for where, text in texts:
        if _BOILERPLATE.search(text):
            reasons.append(
                f"`{where}` says where the issue was parked. The park is the fleet's to say, and the "
                f"person reading it is already there — spend the words on the decision "
                f"(`decision-park-boilerplate`)."
            )
        if where.endswith(".label"):
            continue  # a label's ids are refused outright above; naming them does not help
        for mention in find_ids(text):
            if all(key in quoted for key in mention.keys):
                continue
            if _named_in_place(text, mention):
                continue
            bare.setdefault(mention.token, []).append(where)
    if bare:
        spots = sorted({place for places in bare.values() for place in places})
        reasons.append(
            f"{', '.join(f'`{token}`' for token in bare)} appear{'s' if len(bare) == 1 else ''} bare in "
            f"{', '.join(f'`{p}`' for p in spots)}. The person answering will not look anything up: "
            f"write the plain name with the id in parentheses — *the rule that automated accounts "
            f"never reach a customer (BTR-012)* — or add a `context` entry for the id that quotes "
            f"what it says (`decision-bare-id`)."
        )
    # AND A CUSTOMER-ADDRESSED PARK IN OUR OWN WORDS IS NOT A CARD THEY CAN ACT ON (ENG-20785).
    # The bare-id rule above allows an id when a `context` entry quotes it; a customer has no way
    # to use one even then, so a park that declares `"audience": "customer"` may name none at all
    # — no command, no program/slice/criterion id, and none of Fleet's own nouns.
    reasons.extend(customer_document_refusals(document))
    return reasons


# ── the done-sentinel's summary ──────────────────────────────────────────────────────────────────────────────

#: AT MOST THIS MANY SENTENCES, and this many characters: the summary is what a person reads first, on the
#: request's own page and on the Cockpit (a customer install, 2026-11-02: 330 characters of ids under "Fleet is
#: writing the plan"). Two sentences say what Fleet found and what each answer does.
SUMMARY_SENTENCES_MAX: Final = 2
SUMMARY_CHARS_MAX: Final = 320

#: A FILING'S OWN KEY (`INTAKE-8`, `BUG-12`, `TASK-3`), which `find_ids` does not know: the person has their
#: request open already, and a sibling filing is named by its title.
_FILING_KEY: Final = re.compile(r"\b(?:INTAKE|BUG|TASK)-\d+\b")

#: FLEET'S OWN NOUNS FOR WHAT A PLAN IS MADE OF: a person asked for a plan, not for slices, PRD stubs or
#: capability rows. Ordered; each is reported once.
_FLEET_WORDS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"\bslices?\b", re.IGNORECASE), '"slice"'),
    (re.compile(r"\bPRDs?\b"), '"PRD"'),
    (re.compile(r"\bPRD\s+stubs?\b|\bstubs?\b", re.IGNORECASE), '"PRD stubs"'),
    (re.compile(r"\bcapability\s+rows?\b", re.IGNORECASE), '"capability rows"'),
    (re.compile(r"\bdossiers?\b", re.IGNORECASE), '"dossier"'),
    (re.compile(r"\bsentinel\b", re.IGNORECASE), '"sentinel"'),
)

_SENTENCE_END: Final = re.compile(r"[.!?](?=\s|$)")


def summary_refusals(summary: str) -> list[str]:
    """Every rule the done-sentinel's `summary` breaks when a run parks on a person, or `[]`.

    The summary is the person's question wherever no card is drawn (a request's own page, the Cockpit row,
    the park list), and it is read by somebody who has never seen an id. So: one or two plain sentences
    addressed to that person, things named by their titles and never by ids (not even in parentheses, which
    the card's fields allow), and what each answer does. Advisory at the box (`validate_decision.py
    --summary`), like the card itself.
    """
    text = str(summary or "").strip()
    if not text:
        return [
            "the summary is blank: say in one or two plain sentences what Fleet found and what each answer "
            "does (`summary-blank`)."
        ]
    reasons: list[str] = []
    named = [m.token for m in find_ids(text)] + _FILING_KEY.findall(text)
    if named:
        reasons.append(
            f"the summary names {', '.join(dict.fromkeys(named))}. The person has never seen an id: name each "
            "thing by its title, in quotes, and drop the id (`summary-names-an-id`)."
        )
    words = [said for pattern, said in _FLEET_WORDS if pattern.search(text)]
    if words:
        reasons.append(
            f"the summary uses Fleet's own words ({', '.join(words)}). Say what the person asked for in their "
            "words: a plan, its pieces of work, the feature (`summary-fleet-words`)."
        )
    sentences = len(_SENTENCE_END.findall(text)) or 1
    if sentences > SUMMARY_SENTENCES_MAX or len(text) > SUMMARY_CHARS_MAX:
        reasons.append(
            f"the summary is {sentences} sentences and {len(text)} characters; keep it to "
            f"{SUMMARY_SENTENCES_MAX} sentences and {SUMMARY_CHARS_MAX} characters: what Fleet found, then what "
            "each answer does. The detail belongs in the `decision` document (`summary-too-long`)."
        )
    return reasons

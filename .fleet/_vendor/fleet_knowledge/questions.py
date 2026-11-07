"""0071's rules for a `questions` result document, in one dependency-free place.

A command in the shipped command tree that needs a person writes a `questions` result document
to `$FLEET_RESULT_FILE` and ends its turn (FL-29). The daemon moves those bytes and parses
nothing; the *service* is where the document gains meaning (`fleet_service.dispatch.results`),
and Postgres is where the inside of the array is finally constrained — 0071's five CHECKs, two
of them amended by 0107. That layout has one famous failure, and this module exists to close
it: the rules lived only in SQL, so a session could emit a set (five options, no
recommendation, an unshaped option) that every layer upstream accepted and only the database
refused — after the run was over and the session that wrote it was gone. The agent could not
be told, in its own turn, that its question set was malformed, because nothing on the box or
in the parser knew the rules.

**This is that one place.** A single predicate, stdlib only (like every module in this
package, `pyproject.toml`'s rule), that mirrors the LIVE constraint expressions **exactly** —
same thresholds, same field names, same direction, 0107's discovery widening included — and
returns either `None` or a sentence naming the rule that broke. It is imported by:

  * the **service**, at its ask boundary (`fleet_service.api.agent._ask_or_refuse`), so a bad
    set is refused as a value before it can reach the row;
  * the **box**, through the shipped `knowledge/scripts/validate_questions.py`, so a command
    can check its own draft before it writes `$FLEET_RESULT_FILE` and end its turn having
    asked a person nothing.

`results._questions`'s envelope check and the database's CHECKs stay where they are, as the
fail-closed backstop: this moves the SAME rules earlier, it does not replace the database's
enforcement of them.

The messages name the constraint (`fleet_question_offers_two_to_four_options`, …) rather than
inventing a second vocabulary, because the database's own refusal and this one must read as
one rule — a session told its set breaks `fleet_question_marks_a_recommendation` can fix that
rule; one told "invalid options" cannot.
"""

from __future__ import annotations

import re
from typing import Final

from .customerwords import customer_document_refusals

__all__ = [
    "OPTIONS_MAX",
    "OPTIONS_MIN",
    "PLACEMENT_KIND",
    "PLACEMENT_OPTIONS_MAX",
    "operator_work_in",
    "validate_questions_shape",
]

#: Two to four options — `fleet_question_offers_two_to_four_options`. One option is a
#: notification with a button, and a list past four is a form, which is the thing an interview
#: is supposed to be instead of. **Zero is the exception 0107 carved for discovery**, and only
#: when `allowFreeText` is true: an open question ("what happens today?") is inverted by a menu,
#: so it may carry no options at all. `OPTIONS_MIN` is the floor for a *fork*; the zero case is
#: checked separately because its condition is `allowFreeText`, not a count.
OPTIONS_MIN: Final = 2
OPTIONS_MAX: Final = 4
#: THE ONE QUESTION ALLOWED A FIFTH OPTION (owner, 2026-11-01): a feature request's placement question, `"kind":
#: "placement"` — the best-matching feature, up to two alternatives, a new feature and "not a feature". The service's
#: CHECK widens for this kind alone (migration 20261102004330); its option shapes are `dispatch.results`'.
PLACEMENT_KIND: Final = "placement"
PLACEMENT_OPTIONS_MAX: Final = 5


def _nonempty(value: object) -> bool:
    """A present, non-blank string — the `type() == "string" && @x != ""` half of a CHECK."""
    return isinstance(value, str) and bool(value.strip())


def validate_questions_shape(document: object) -> str | None:
    """Why this `questions` result document breaks one of the question rules, or `None` if it does not.

    `document` is the result document — the object with a `questions` key that `results.parse`
    reads and that `knowledge/scripts/validate_questions.py` loads from `$FLEET_RESULT_FILE` —
    not the bare array. A non-object, a missing or empty `questions` array, a question that is
    not shaped, a question whose options are not an array or are one/past four, zero options
    without the free-text escape, a question that marks no recommendation, and an option that
    is not shaped are each a sentence naming the constraint they break.

    **Mirrors the LIVE constraints, not 0071's original text.** 0107 replaced
    `fleet_question_offers_two_to_four_options` and `fleet_question_marks_a_recommendation`:
    zero options are admitted IFF `allowFreeText` is true, and the recommendation rule skips an
    empty option list (there is nothing to recommend). A predicate that still demanded two to
    four would refuse the discovery ask and the ENG-12646 salvage — so the zero case is here,
    and its condition is the free-text flag exactly as the CHECK spells it.
    """
    if not isinstance(document, dict):
        return (
            "a question set is one JSON object with a `questions` array, and this is a "
            f"{type(document).__name__} (`fleet_question_asks_something`)."
        )
    asked = document.get("questions")
    if not isinstance(asked, list) or not asked:
        return (
            "a question set must carry a non-empty `questions` array. An empty one is a park "
            "with nothing for anybody to answer (`fleet_question_asks_something`)."
        )
    for number, question in enumerate(asked, start=1):
        if not isinstance(question, dict):
            return (
                f"question {number} is not an object. Every question carries an id, a prompt, an "
                f"explicit `allowFreeText` and options (`fleet_question_every_question_is_shaped`)."
            )
        if not _nonempty(question.get("id")) or not _nonempty(question.get("prompt")):
            return (
                f"question {number} needs a non-empty `id` (to answer it by) and `prompt` (to read) "
                f"(`fleet_question_every_question_is_shaped`)."
            )
        if not isinstance(question.get("allowFreeText"), bool):
            return (
                f"question {number} needs `allowFreeText` present and boolean. An omitting writer "
                f"gets a question whose escape hatch silently does not exist "
                f"(`fleet_question_every_question_is_shaped`)."
            )
        options = question.get("options")
        if not isinstance(options, list):
            return (
                f"question {number}'s `options` must be an array. A question the schema cannot read "
                f"is one it refuses (`fleet_question_offers_two_to_four_options`)."
            )
        count = len(options)
        if count == 0 and question.get("allowFreeText") is not True:
            return (
                f"question {number} offers no options and does not allow free text. A question "
                f"nobody can answer is the one refusal with no way through "
                f"(`fleet_question_offers_two_to_four_options`)."
            )
        ceiling = PLACEMENT_OPTIONS_MAX if question.get("kind") == PLACEMENT_KIND else OPTIONS_MAX
        if count == 1 or count > ceiling:
            return (
                f"question {number} offers {count} options. A fork offers {OPTIONS_MIN} to "
                f"{ceiling}; zero is allowed only as an open, free-text question. One option is a "
                f"notification with a button and past {OPTIONS_MAX} is a form "
                f"(`fleet_question_offers_two_to_four_options`)."
            )
        for position, option in enumerate(options, start=1):
            if not isinstance(option, dict):
                return (
                    f"option {position} of question {number} is not an object "
                    f"(`fleet_question_every_option_is_shaped`)."
                )
            if not (_nonempty(option.get("id")) and _nonempty(option.get("label")) and _nonempty(option.get("then"))):
                return (
                    f"option {position} of question {number} needs a non-empty `id`, `label` and "
                    f"`then` — the consequence of picking it (`fleet_question_every_option_is_shaped`)."
                )
            if not isinstance(option.get("recommended"), bool):
                return (
                    f"option {position} of question {number} needs `recommended` present and boolean "
                    f"(`fleet_question_every_option_is_shaped`)."
                )
        if count > 0 and not any(isinstance(one, dict) and one.get("recommended") is True for one in options):
            return (
                f"question {number} marks no option recommended. An agent that asks without "
                f"recommending has handed the judgement back to the person it was meant to save the "
                f"judgement from (`fleet_question_marks_a_recommendation`)."
            )
    # A CUSTOMER CARD IN OUR WORDS IS NOT AN ASK THEY CAN ANSWER (ENG-20785). The shape can be
    # perfect and the set still unusable: one that names a slash command, a program/slice id or
    # Fleet's own nouns asks a customer to translate our vocabulary before they can answer. The
    # check is skipped unless the document says `"audience": "customer"`.
    addressed = customer_document_refusals(document)
    if addressed:
        return addressed[0]
    return None


#: A PERSON SENT TO A TERMINAL, not the bare noun (ENG-16820). The guard exists for PROD PG-047's "At a
#: terminal on the checkout, run the cycle once": the person was told to go somewhere and run something. A
#: bare `\bterminal\b` also matched a *proof description* — PG-40's "a live terminal can fetch one on
#: demand" names what the product does, and refusing it auto-filed a bug over an entirely proper question
#: (ENG-16820). The cue that separates the two is direction at the person: an imperative that opens one
#: ("open a terminal"), or a locative preposition carrying an article straight onto the noun ("at a
#: terminal"). An intervening adjective ("a live terminal") is exactly the descriptive shape the article
#: gate refuses, so it no longer reads as work.
_TERMINAL_WORK: Final = re.compile(
    r"\b(?:open|use|launch|start|attach|enter|ssh|log|sign|go|get)\b"
    r"(?:\s+(?:in\s+)?to)?\s+(?:a|an|the|your|my|its)\s+terminal\b"
    r"|\b(?:at|in|into|from|on|via|through|inside|within)\s+(?:a|an|the|your|my|its)\s+terminal\b"
    r"|\b(?:your|my)\s+terminal\b",
    re.IGNORECASE,
)

#: WHAT A DELIVERY CYCLE MAY NEVER HAND A PERSON (PROD PG-047): an option that tells them to run a slash
#: command (`/<ns>:<verb>`), to open a terminal, or to judge whether something is a fleet fault. Each is the
#: fleet's own work dressed as a decision — the session runs the command, or files the fault as a bug.
OPERATOR_WORK: Final = (
    (re.compile(r"(?<![\w/.])/[a-z][a-z0-9-]*:[a-z][a-z0-9:-]*"), "run a command"),
    (_TERMINAL_WORK, "open a terminal"),
    (re.compile(r"\bfleet(?:'s)? (?:fault|defect|bug|problem)\b", re.IGNORECASE), "judge a fleet fault"),
)


def operator_work_in(document: object) -> str | None:
    """Why this question set hands a person the fleet's own work, or `None` when every option is a decision.

    **A delivery cycle asks only for what is genuinely the person's** — scope, priority, a trade-off, to
    accept or to waive. PROD's PG-047 (question `28b43d22`) offered "run the attended cycle at a terminal",
    "run the design and create commands by hand", "treat it as a fleet fault" and "leave it": three of the
    four asked a person to do or diagnose what the fleet owns. A command the cycle names is one it runs (or
    hands to the fleet by filing); a lane that does not dispatch is a fleet defect, filed as a bug and
    reported. Read over every option's `label` and `then`; the first that matches is named.
    """
    if not isinstance(document, dict) or not isinstance(document.get("questions"), list):
        return None
    for number, question in enumerate(document["questions"], start=1):
        if not isinstance(question, dict) or not isinstance(question.get("options"), list):
            continue
        for option in question["options"]:
            if not isinstance(option, dict):
                continue
            text = f"{option.get('label') or ''}\n{option.get('then') or ''}"
            for pattern, what in OPERATOR_WORK:
                if pattern.search(text):
                    return (
                        f'option "{option.get("label") or option.get("id")}" of question {number} asks the person '
                        f"to {what}. A delivery cycle asks only for the person's decisions (scope, priority, a "
                        "trade-off, accept or waive): a command it needs is one it runs, and a stall the fleet "
                        "causes is filed as a bug and reported, never asked."
                    )
    return None

"""Filling a page template, and the two different ways a corpus's own text can wreck the page.

Both generators here do the same two things to a template: they SUBSTITUTE a handful of
`__TOKEN__` placeholders, and they ESCAPE a JSON payload on its way into one of them. Each has
a failure mode the other cannot cover, and the standalone board hit both at once.

**Substitution — prose that names a placeholder is documentation, never a site.** A template
documents itself, and the shipped board template documents all five of its placeholders in its
opening HTML comment (`Placeholders: __DATA__ (the payload), __TITLE__ …`). A blanket
`str.replace` fills those mentions too, so the stylesheet, the renderer and the whole payload
were inlined a SECOND time inside that comment — where the first `-->` the corpus happened to
carry closed the comment early and the rest of the file parsed as body text: zero scripts, zero
buttons, and the corpus rendered as visible prose down a 16,000-pixel page.

The fix is this module and not a reworded comment. Wording around the tokens fixes one file
once; a `--template` replacement is somebody else's file, this package cannot word THEIR
comments, and the next person to document a placeholder — there or here — must not be able to
break the page by doing it. So `fill` substitutes only outside comments, and `require` looks
for a placeholder only where one could actually be filled: a template that merely MENTIONS
`__DATA__` in a comment is missing it, and says so, rather than rendering a page with no data.

**Escaping — `payload` may not carry a tokenizer state change into the page.** See `ESCAPES`.

**One pass, not one `str.replace` per token.** The old sequence substituted `__STYLE__` and
`__SCRIPT__` first and then re-scanned their contents for `__TITLE__`, `__INTENT_TAB__` and
`__DATA__` — a token inside `board.js` was a live placeholder, and the ordering comment that
made that safe was a rule somebody had to keep remembering. `fill` walks the template once, so
what it substitutes is never itself scanned, and the order of `values` cannot matter.

Stdlib only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

__all__ = ["ESCAPES", "fill", "payload", "require", "sites"]


#: What a payload may never carry verbatim into a page, and what it carries instead.
#:
#: THE SET IS "EVERY STATE CHANGE", NOT "THE ONES THAT HAVE BITTEN US". Inlined JSON is text
#: the HTML tokenizer is walking, and it only stops being data at a transition: `</` opens an
#: end tag (which is every spelling of `</script>`, `</SCRIPT `, `</script foo=`), `<!--` opens
#: a comment, and `-->` closes one. Those three are the whole exit vocabulary — so this is a
#: closed set with a reason, and the reason is what makes it maintainable. The temptation is to
#: carry only the two that can escape a `<script>`, since that is where the payload is meant to
#: sit; `-->` is then the one that does nothing at all — right up until a substitution bug puts
#: the payload somewhere else, which is exactly what happened. A payload that is safe only in
#: the element it was aimed at is safe by luck.
#:
#: Every replacement is a JSON escape of one character in the sequence, so `json.loads` returns
#: the identical string and nothing on the page can tell the difference. That is what makes
#: this safe to apply unconditionally instead of somebody deciding, per corpus, whether it is
#: needed. `>` and `!` are structural nowhere in JSON — they occur only inside string literals
#: — so replacing these three over the serialized text can never touch the grammar.
ESCAPES: dict[str, str] = {
    "</": "<\\/",
    "<!--": "<\\u0021--",
    "-->": "--\\u003e",
}

#: A placeholder, as every template in this package spells one.
_TOKEN = re.compile(r"__[A-Z][A-Z0-9_]*__")

#: The two kinds of run `fill` must recognise before it substitutes anything.
#:
#: `comment` is where a placeholder is being TALKED ABOUT rather than asked for. The second
#: branch (`<!--.*` with no close) is deliberate: per the HTML parser an unterminated comment
#: swallows the rest of the document, so a template with one has no substitution sites after
#: it — and `require` then fails loudly by name instead of writing out a page whose data
#: element is empty.
#:
#: `raw` is a raw-text or RCDATA element. Its contents are still substituted — `<title>` and
#: `<script id="boarddata">` are two of the sites that matter most — but they are NOT scanned
#: for comments, because a browser does not parse comments in there either. Without this a
#: `<!--` inside an inline script would silently swallow every later placeholder.
_SPAN = re.compile(
    r"(?P<comment><!--(?:.*?-->|.*))"
    r"|(?P<raw><(?P<tag>script|style|title|textarea)\b[^>]*>.*?</(?P=tag)\s*>)",
    re.DOTALL | re.IGNORECASE,
)


def payload(data: dict[str, Any]) -> str:
    """The JSON, safe to inline in a page — see `ESCAPES` for what that means and why."""
    raw = json.dumps(data, separators=(",", ":"))
    for hostile, safe in ESCAPES.items():
        raw = raw.replace(hostile, safe)
    return raw


def fill(html: str, values: Mapping[str, str]) -> str:
    """`html` with each placeholder in `values` substituted, outside comments, in one pass.

    A token `values` does not name is left alone: a replacement template may carry placeholders
    this package has never heard of, and eating them would be worse than passing them through.
    """

    def one(match: re.Match[str]) -> str:
        return values.get(match.group(0), match.group(0))

    return "".join(_TOKEN.sub(one, run) if fillable else run for run, fillable in _runs(html))


def sites(html: str) -> set[str]:
    """Every placeholder `html` actually asks to have filled — mentions in comments excluded."""
    return {m.group(0) for run, fillable in _runs(html) if fillable for m in _TOKEN.finditer(run)}


def require(html: str, tokens: Iterable[str], template: Path) -> None:
    """Fail, naming the file and the token, unless `html` has a real site for each of `tokens`."""
    present = sites(html)
    for token in tokens:
        if token not in present:
            raise SystemExit(f"error: {template} is missing its {token} placeholder")


def _runs(html: str) -> Iterator[tuple[str, bool]]:
    """`html` cut into runs, each flagged with whether a placeholder in it is a site."""
    pos = 0
    for match in _SPAN.finditer(html):
        if match.start() > pos:
            yield html[pos : match.start()], True
        yield match.group(0), match.group("comment") is None
        pos = match.end()
    if pos < len(html):
        yield html[pos:], True

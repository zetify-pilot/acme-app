/* The board's renderer — ONE copy, read by two pages.
 *
 * `program-board.html` inlines it into a standalone file that works with no server at all
 * (that is what `fleet-knowledge` is for: a submodule in a repository with no Fleet
 * deployment). fleet-service serves these exact bytes at `/ui/board.js` for the deployed app,
 * where the same views render a payload fetched from `/api/board`.
 *
 * THE ONLY DIFFERENCE BETWEEN THE TWO IS WHERE THE PAYLOAD COMES FROM. That is the whole
 * seam, and it is `start({load})` — a function returning a promise of the payload. Baked on
 * one side, fetched on the other; every view below is identical and there is no second copy
 * to drift. A fork of this file would be the third rendering bug of the day.
 *
 * What that costs the views: the payload arrives LATER than the script. So `D` and the four
 * indexes derived from it are `let`, assigned by `boot()`, and `render()` knows the state
 * where there is no payload yet — which is also where the loading and failure states live.
 * A page that renders nothing while a fetch is in flight looks exactly like a page whose
 * fetch failed, and telling those apart is the same discipline as the sync's four silences.
 *
 * `register()`/`start({views})` let a HOST add route kinds this package knows nothing about.
 * The deployed app adds `fleet` that way. `fleet-knowledge` is the record and must not learn
 * about the loop; an extension point costs three lines and keeps that boundary intact.
 *
 * What this page may never show, by construction and not by omission: a date, a duration, a
 * rate, a projection, a velocity or a "what fits" estimate. Progress is COUNTS.
 */
window.Board = (function(){
"use strict";

/* The payload and its indexes. `let`, because they arrive from `boot()` — see the header. */
let D = null;
let PG = {};
let SL = {};
let PRD = {};
/* THE PRDs NO SLICE CLAIMS, by number (ENG-10704): their page reads the slice their file names from
   here, never off the row — a PRD row on the wire carries no such field. */
let OFF_BOARD = {};
/* Who runs the automated half, and what a row of theirs says instead of a command. */
let FLEET = { wait: "", actor: "the automation", Actor: "The automation", note: "" };

/* ── the glossary ─────────────────────────────────────────────────────────── */
/*
 * WHAT EVERY WORD ON THIS BOARD MEANS, and not one of those definitions is written here.
 *
 * The corpus authors them — `specs/glossary.md`, seven columns, read by
 * `fleet_knowledge.corpus.glossary` and carried in the payload as `D.glossary`. That is the
 * same discipline the requirement registers impose on prose: a term is defined in one row,
 * and everything else cites it. A page that carried its own copy would be the second text,
 * and the second text is the one that is quietly wrong.
 *
 * `GLOSS` is the id index behind `term()` and `defined()`, whose hover text it supplies; there
 * is no glossary PAGE any more (the Knowledge page explains the corpus's kinds, and every other
 * word is explained where it stands). A corpus with no glossary leaves both empty, and a
 * word neither `KGUIDE` nor `GLOSS` knows degrades to plain text — an honest "this corpus
 * defines no such term" rather than a definition this file invented to fill the hole.
 *
 * A HOST MAY ADD SECTIONS OF ITS OWN, through `terms()`. `fleet-knowledge` is the record and
 * knows nothing about boxes, leases or dispatch positions; the deployed app does, and its
 * vocabulary is minted by the API from the very constants that enforce it. Same three-line
 * seam as `register` and `runAction`, and the same reason for it.
 */
let TERMS = [];
let GLOSS = {};
/* Sections a host contributes, as a function called at index time so it can answer late. */
let TERMS_EXTRA = null;
/* THE HOST'S WORDS FOR A VALUE, when it has some. A term's vocabulary is a closed set of the
   record's own keys (`no-lane`, `wallclock-ceiling`), and the host's pages print a person's
   words for those keys on every chip and bar — so a reader who taps "NO REPOSITORY TO WORK IN"
   has to find a row that leads with those words, not one headed by the key alone. Called with
   the value; answers the words, or the value itself when it has none, and the row then shows
   the key on its own exactly as before. Nothing here invents a word: the corpus's own terms
   carry none, and a standalone board has no host to ask. */
let SAYS = null;

function indexTerms(){
  const corpusTerms = (D && D.glossary) || [];
  const hostTerms = TERMS_EXTRA ? (TERMS_EXTRA() || []) : [];
  TERMS = corpusTerms.concat(hostTerms);
  GLOSS = {};
  TERMS.forEach(t => { if (t && t.k) GLOSS[t.k] = t; });
}

/* Where the corpus payload has got to. `loading` is not `failed` is not `ready`, and the
   three render differently — that is the entire reason this variable exists. */
let CORPUS = { state: "loading", detail: "", body: "" };
/* The view a route falls back to, remembered from `start` so a late answer can re-enter the hash
   against it — see the knowledge index's own arrival. */
let HOME = "board";

/* Route kinds contributed by the host page: kind -> function(arg) -> html. */
const EXTRA = {};
/* Called after every render with the route, so a host can drive a live view. */
const ROUTED = [];

/* FIVE CHARACTERS, AND THE FIFTH IS THE ONE THAT WAS MISSING. `'` was not escaped: every
   attribute either page writes is double-quoted, so nothing was exploitable through it today —
   latent, not live. It is here now because "today" is doing all the work in that sentence. One
   single-quoted attribute, written by somebody who had no reason to know this list was short,
   turns a corpus row into markup; and this function is about to become the ONLY thing standing
   between a corpus's prose and an inline renderer that inserts tags. A guarantee that holds
   only while nobody writes `id='...'` is not a guarantee. */
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ── prose the corpus authored, which is Markdown ─────────────────────────── */
/*
 * THE TEXT ON THIS PAGE IS NOT PLAIN TEXT AND NEVER WAS. `specs/glossary.md` is a markdown
 * file, the vocabularies the API mints from are docstrings, and both are written the way
 * everything else in these repositories is written — a path in backticks, an emphasis in
 * asterisks. Escaped and printed, that arrives on screen as `api/fleet.py` with the punctuation
 * showing and **Draining alone does not produce this state** reading as six stray asterisks. A
 * reader has to decode the page, which is the opposite of what the marks are for.
 *
 * A WHITELIST, INLINE ONLY, AND THAT IS A DECISION RATHER THAN A STAGE. Three constructs —
 * `` `code` ``, `**bold**`, `*em*` — because they are what this corpus's sentences use.
 * Headings, lists, links and images are block structure, and a sentence inside a table cell or
 * a chip has nowhere to put them; a link would let a corpus row put a destination on the page,
 * which is a different decision from reading its emphasis and is not being made here. **There
 * is no raw-HTML passthrough and there is no library.** A markdown library over raw text, its
 * output handed to `innerHTML`, is the shape this refuses: `fleet-knowledge` declares NO
 * runtime dependency on purpose and CI holds it to that, so the alternative was never a
 * hardened parser — it was an unhardened one, vendored.
 *
 * **ESCAPED FIRST, ALWAYS, AND THE ORDER IS THE WHOLE SAFETY PROPERTY.** `esc` runs over the
 * raw text before a single mark is interpreted, so by the time any tag is inserted there is no
 * `<`, `>`, `"` or `'` left in the string that came from the corpus. Formatting after escaping
 * can only ever introduce the tags THIS function wrote. Doing it the other way round — insert
 * `<code>`, then escape — would destroy the tags; doing it in one pass over unescaped text
 * would let a term containing `<script>` reach the page as markup. The tests drive the
 * injection case through the real renderer rather than asserting the shape of this comment.
 *
 * THE ESCAPE IS INSIDE THIS FUNCTION AND NOT AT THE CALL SITE, which displaces the composed
 * form `mdown(esc(t.what))` the review that prompted this asked for. Both satisfy the rule;
 * they fail differently, and that is the whole argument. Composed, the failure mode of a call
 * site written next year is `mdown(t.what)` — raw corpus text reaching a tag inserter, which is
 * the vulnerability. Enclosed, the failure mode is `mdown(esc(t.what))` — a double escape, so
 * a reader sees `&amp;lt;` and files a cosmetic bug. One of those two mistakes is recoverable
 * and one is not, and there are six call sites today and no reason to think that is the last of
 * them. `esc` remains exported and unchanged for every site that renders a name rather than a
 * sentence.
 *
 * A code span wins over bold INSIDE it: `` `a **b** c` `` is a literal, because that is what a
 * code span means. Hence the walk below rather than two `.replace` calls, which would format
 * the contents of every code span on the page.
 */
/* A LINK IS LEFT EXACTLY AS THE AUTHOR WROTE IT, and that is the decision above rather than an
   omission below. Flattening one to its label was tried here and taken back out: it puts no
   destination on a page, but `fleet-service`'s `tests/api/test_js_render_glossary.py` pins the
   SOURCE as what a reader sees — *"a link was consumed rather than left alone"* — and a whitelist
   that grows by one construct because a different page wanted it is a decision for whoever owns
   the whitelist, not a side effect of the page that wanted it.
   Measured before withdrawing it: 1 of the 79 `Done when` cells in the corpus this fleet drives
   carries a link, and it renders as `[`SL-172`](slices/SL-172.md)` — the label's own code span
   read, the brackets printed. That is the cost, and it is one cell.

   A DOCUMENT IS THE OTHER CASE, and `mdBlock` is the one caller that opts in (`links`). A command,
   a knowledge page, an issue's own text, an agent's message on the Terminals page — those are
   documents a person reads end to end, and an agent citing its source as `[tokei](https://…)`
   printed the brackets at the operator. So inside a block document a link is an `<a>`, bounded by
   `mdHref`: `http(s)://`, `mailto:`, an in-page `#…` or a site-relative `/…`, and nothing else —
   `javascript:`, `data:`, a relative `slices/SL-172.md` that would resolve against the app's own
   path, all stay the characters the author typed. A row, a chip, a glossary term — every inline
   caller — still prints the source, exactly as above. A bare `http(s)://` URL in a document is a
   link too, by GitHub's autolink rules (`MD_BARE`, below); in a row it stays the characters. */
const MD_CODE = /`([^`\n]+)`/g;
const MD_BOLD = /\*\*(?!\s)([^*\n]+)\*\*/g;
const MD_EM = /\*(?!\s)([^*\n]+)\*/g;
/* BOLD BEFORE EMPHASIS, and that order is not a preference. `**x**` matches the emphasis
   pattern too — run em first and every bold on the page becomes an italic wrapped in stray
   asterisks. Bold consumes both pairs, so what reaches the second pass is only ever a single
   `*`, which is the one thing it should be looking at. */
/* `_emphasis_` FOLLOWS COMMONMARK'S FLANKING RULE: the opening `_` is not preceded by a letter, digit, `_` or a path
   slash and is followed by a non-space; the closing one is preceded by a non-space and not followed by a letter or
   digit. So `snake_case_names`, `a_b_c` and `src/_x_/y` stay literal, and `_soft_` or `(_soft_)` is italic. */
const MD_EM_U = /(?<![A-Za-z0-9_\\/])_(?![\s_])([^_\n]*[^_\s])_(?![A-Za-z0-9_])/g;
function mdInline(t){
  return t.replace(MD_BOLD, (_, inner) => `<b>${inner}</b>`)
          .replace(MD_EM, (_, inner) => `<em>${inner}</em>`)
          .replace(MD_EM_U, (_, inner) => `<em>${inner}</em>`);
}
/* AN ID IN A SENTENCE IS THE SAME DESTINATION IT IS IN A LIST, and until this pass it was the one
   place on the page where it was not. `badge` has always resolved an id through `routeOf`; a
   `Done when` that reads *"after SL-172 lands"*, an agent's question naming `GOV-001`, a
   register row citing `CAP-0967` — every one of those was plain text beside a chip that linked,
   on the same screen.

   **BOUNDED BY THE INDEX, NOT BY THE SHAPE.** The pattern below is the cheap half: it decides
   what is worth ASKING about. `routeOf` decides what is worth LINKING, and it answers `""` for
   every id no register on this board holds — so it is impossible for this to mint a destination
   the corpus does not have. A link to a page that says "no such thing" is worse than the plain
   text it replaced, which is the whole reason the bound is the index rather than the regex.

   The shape is deliberately narrow: two to six capitals, a hyphen, one to four digits. That is
   `GOV-001`, `CAP-0967`, `RUN-1020`, `PG-31`, `SL-185`. It is NOT a bare PRD number — `0599` in
   a sentence is a number far more often than it is a PRD, and `routeOf` would happily resolve it.
   A cheap pattern in front of an authoritative bound is how a false positive stays a lookup miss
   rather than a wrong link.

   UP TO SIX DIGITS, not four. A tracker key is `ENG-14950` — five digits — and a
   host that resolves tracker keys (`setHostRefs`) never saw one through a four-digit shape. The
   widening adds no link on its own: every match still goes to `routeOf` or the host, and both
   answer `""` for anything nobody holds.

   **THE LEFT BOUNDARY IS NOT A WORD BOUNDARY (ENG-22468).** A QA output names a repository
   record id as `ACME-BUG-3`, a file under `knowledge/bugs/`. A plain `\b` before the shape
   accepts the `BUG-3` after the first hyphen — a hyphen is a word boundary — so the id pass
   linked the unrelated Fleet filing `BUG-3` and the reader could not reach the record the agent
   meant. The lookbehind refuses a match whose first character follows a word character or a
   hyphen, so the whole `<PREFIX>-<KIND>-<n>` token stays the text the author wrote. It is the
   same refusal `routeOf` makes for an id nobody holds: the safer answer is no link, never a
   link to the wrong thing. A standalone `CAP-0967` beside a compound `x-CAP-0967` shows the
   line — the second is part of a larger token and is not a citation of its own.

   `.term` IS THE AFFORDANCE, and it is the one this file already has for exactly this: a word
   inside a sentence that is also a destination, dotted-underlined, inheriting the prose's own
   font so the line does not break around it. A `.chip` — uppercase, bordered, boxed — is the
   list treatment and reads as an interruption mid-sentence. No new class and no new token. */
const MD_ID = /(?<![\w-])([A-Z][A-Z0-9_]{1,9}-\d{1,7})\b/g;
/* A PRD IS NAMED BY A MARKER AND ITS NUMBER, NEVER BY THE NUMBER ALONE (ENG-10643). The refusal
   above is right and it left the one id the fleet's own findings name most often as the one id
   on the page that did not link: "Blocked on PRD 0379" sat beside a `CAP-0967` that did. The
   MARKER is what the bare number lacks — it says what the author meant, so the shape can be
   read without asking a register. Two markers, and the list is closed:

   * the word `PRD`, any case, then an optional space or hyphen, then EXACTLY four digits —
     `PRD 0379`, `PRD-0379` (the register form, which `MD_ID` would otherwise match and
     `routeOf` refuse), `PRD0379`, `prd 0379`. The whole mention is the link's text.
   * the bracketed title prefix a Linear issue carries — `[0599] …`, `[0609 companion ·
     ops-k8s] …` — read the way `dispatch.issues.prd_number` reads it: `[`, four digits, then
     `]` or a space. ONLY THE NUMBER LINKS; the bracket and the rest of the title stay the
     characters they were, because a title is quoted on this page, not rewritten.

   Four digits and no other count, so `2026`, a run count, `[12345]` and a sha stay text; a URL
   or a sha has no marker in front of its digits; a code span is held aside before this runs.

   **THE BOUND IS THE MARKER, NOT THE INDEX — the one place this file links what the board does
   not hold, and on purpose.** `PG-99` links only when `PG` holds it, because without the index a
   dash-and-digits pattern cannot tell an id from a part number. `PRD 9999` is unambiguous as
   written, and the page behind the link is `viewMissing`'s: "There is no PRD 9999 in this
   repository" — the honest answer, and a truer one than the plain text it replaces. */
const MD_PRD = /\b[Pp][Rr][Dd][ -]?(\d{4})\b|\[(\d{4})(?=[\]\s])/g;
/* ONE PASS, THE PRD SHAPES FIRST. A single `replace` never rescans what it inserted — the
   `href` and `data-go` it writes carry `prd:` and a query string, and a second pass over them
   would be a second chance to match something inside a tag. Composed from the two patterns'
   sources rather than typed a third time, and the PRD alternatives come first because
   `PRD-0379` satisfies `MD_ID` too, and alternation takes the first branch that matches at a
   position: were `MD_ID` first, the register form would go to `routeOf`, which answers `""` for
   it, and the one spelling the registers themselves use would be the one that stayed plain. */
const MD_REF = new RegExp(`${MD_PRD.source}|${MD_ID.source}`, "g");
/* `soft` IS FOR A NESTED SURFACE: a parent that is already a `<button>` (an option, a map
   jump, a navigating row) cannot hold another button, and the HTML parser would close the
   outer one at the inner one. A `<span class="term" data-go>` keeps the same affordance and
   the same click path (`closest("[data-go]")`) without nesting interactive content. The
   default stays a real button so a term in free prose is keyboard-activable on its own. */
/* A HOST'S OWN REGISTERS, AND WHAT A LINK IS CALLED. Two families of id are in no
   register this file holds: a TRACKER ISSUE (`ENG-14950`) and a host FILING (`BUG-12`). The deployed
   app holds both server-side and resolves them through `setHostRefs(fn)`: `fn(id)` answers
   `{ go, name }` for an id it HOLDS, `{ go: "", name }` for one it can only NAME (a requirement's
   statement — the route stays the index's), or `null`. It is asked only by a caller that opts in
   (`opts.host`), because the deployed answer is a lookup that lands later, and only a caller that
   re-renders on `onRefs` ever shows what it found. Unknown stays text — the host's bound is what it
   holds, exactly as `routeOf`'s is the index.

   `opts.tab` OPENS THE LINK IN A NEW TAB — for a surface a person must not be navigated away from:
   an agent's thread on the Terminals page, where the in-page route would take the session off the
   glass mid-turn. The anchor keeps its `data-go` (every render test reads it) and the delegated
   click leaves a `target="_blank"` anchor to the browser. `opts.title` is the same opt-in for the
   hover name: the id's kind and, where this page or the host holds it, its name. */
let HOST_REF = null;
const REF_LISTENERS = [];
function setHostRefs(fn){ HOST_REF = typeof fn === "function" ? fn : null; }
function onRefs(fn){ if (typeof fn === "function") REF_LISTENERS.push(fn); }
/* SOMETHING AN ID CAN RESOLVE AGAINST CHANGED — the index arrived, a payload was installed, the
   host's lookup landed. A listener that throws is its own fault and never stops the next one. */
function refsChanged(){
  REF_LISTENERS.slice().forEach(fn => { try { fn(); } catch (_e){ /* the listener's own fault */ } });
}
const K_ONE = { journey: "Journey", area: "Feature", capability: "Capability", component: "Component",
                requirement: "Requirement", decision: "Decision" };
function refTitle(go, id, named){
  const [kind, rest] = [go.split(":")[0], go.slice(go.indexOf(":") + 1)];
  const pg = kind === "program" ? PG[rest] : null;
  const sl = kind === "slice" ? SL[rest] : null;
  const prd = kind === "prd" ? PRD[rest] : null;
  const k = kind === "knowledge" ? rest.split(":")[0] : "";
  const what = kind === "program" ? `Program ${rest}` : kind === "slice" ? `Slice ${rest}` : kind === "prd" ? `PRD ${rest}`
    : k ? `${K_ONE[k] || k} ${id}` : kind === "issue" ? `Issue ${id}` : kind === "bug" ? `Bug ${id}`
    : kind === "idea" ? `Idea ${id}` : kind === "task" ? `Task ${id}` : id;
  const name = named || (pg && pg.name) || (sl && sl.name) || (prd && prd.title) || "";
  return name ? `${what} — ${name}` : what;
}
/* A KEY THE FLEET DOES NOT HOLD BUT THE TRACKER DOES is a link out: a new tab, the arrow, and the
   words a screen reader needs ("opens in Jira") that the arrow cannot say. ONLY http(s) ADDRESSES
   ARE LINKED — the address is the server's, but an `href` is never built from a string that
   `new URL` does not parse to one of those two schemes. Soft (inside a button) stays text. */
function externalRef(id, url){
  let at;
  try { at = new URL(String(url)); } catch (_) { return ""; }
  if (at.protocol !== "http:" && at.protocol !== "https:") return "";
  return `<a class="term" href="${esc(at.href)}" target="_blank" rel="noopener noreferrer" title="${esc(id + " on " + at.host)}">${esc(id)}<span class="mk-ext" aria-hidden="true">&#8599;</span><span class="mk-sr"> (opens in Jira)</span></a>`;
}
function mdIds(t, soft, repo, opts){
  const o = opts || {};
  /* PROSE ON A RECORD THAT CARRIES ITS OWN REPOSITORY (ENG-10706). `routeOf` reads the SELECTED
     repository's payload, so "A cut under PG-01" on a fleet idea read under the primary linked the primary's
     PG-01. With another repository named, an id is linked there by the register's own prefix — a
     program, a slice or a PRD — and anything else (a capability, a requirement: another
     repository's index this page does not hold) stays text rather than point into the wrong one. */
  const elsewhere = !!repo && repo !== REPO && manyRepos();
  return t.replace(MD_REF, (m, prd, titled, id) => {
    const n = prd || titled;
    const host = id && o.host && HOST_REF && !elsewhere ? HOST_REF(id) : null;
    const go = n ? "prd:" + n
      : !elsewhere ? routeOf(id) || (host && host.go) || ""
      : /^PG-\d+$/.test(id) ? "program:" + id : /^SL-\d+$/.test(id) ? "slice:" + id : "";
    if (!go && host && host.url && !soft){
      const out = externalRef(id, host.url);
      if (out) return out;
    }
    if (!go) return m;
    /* The title form matched `[0599` — the bracket is put back in front of the link, so the
       reader sees the title as it was written with the number inside it a destination. */
    const text = titled ? n : m;
    const other = elsewhere ? ` data-go-repo="${esc(repo)}"` : "";
    const tip = o.title ? ` title="${esc(refTitle(go, n ? "PRD " + n : id, host && host.name))}"` : "";
    const tab = o.tab ? ` target="_blank" rel="noopener noreferrer"` : "";
    const tagged = soft
      ? `<span class="term" data-go="${esc(go)}"${other} tabindex="0"${tip}>${text}</span>`
      : link(go, "term", text, tab + tip, elsewhere ? repo : undefined);
    return titled ? "[" + tagged : tagged;
  });
}

/* A DESTINATION IS AN `<a href>`, AND THAT IS WHAT MAKES IT A LINK (ENG-10590). Every navigation on
   this board used to be a `<button data-go>`: the delegated click reached the router, and nothing
   else did — no middle-click, no Cmd-click, no long-press "open in new tab", no hover URL, no
   "copy link". The whole app was a page nobody could hand a link out of. Measured on the
   production board during the QA sweep that filed ENG-10590: not one `<a>` on any page.

   `href` IS `urlFor(go)`, the same string `go()` pushes — so the address a new tab opens on is
   byte-for-byte the one this tab would have pushed, repository query included. `data-go` stays,
   because the click path (`closest("[data-go]")`) and every render test read it; a plain click
   still routes in-page through the listener below, and a modified click (Cmd, Ctrl, Shift,
   middle) is left to the browser, which is what a link is for.

   `soft` (a `<span class="term">` inside a control that is itself a button) is the one shape
   that stays what it was: an anchor inside a button is the nesting the HTML parser refuses, and
   the parser's answer to it is to close the outer element early (#553). A navigating ROW is an
   anchor now, so its inner destinations are spans for the same reason. */
function link(go, cls, inner, attrs, repo){
  /* A RECORD'S OWN REPOSITORY (ENG-10706). A link on a page about a record that carries its own
     repository — an idea, a question card — addresses THAT repository, not the selection: every
     corpus mints its own PG-01, so the selection's PG-25 is a different program. `data-go-repo`
     is what the click reads to move the selection first; absent, the link is the page's. */
  const other = repo && manyRepos() && repo !== REPO ? ` data-go-repo="${esc(repo)}"` : "";
  return `<a class="${cls}" href="${esc(urlFor(go, repo))}" data-go="${esc(go)}"${other}${attrs || ""}>${inner}</a>`;
}
/* A CODE SPAN IS HELD ASIDE, NOT SPLIT ON — and that distinction is the whole of this function.

   IT USED TO CUT THE STRING AT EVERY CODE SPAN and run the inline pass over the pieces between,
   which is correct for a bold run that sits beside a code span and silently wrong for one that
   CONTAINS it: `**`+code+`**` puts the opening mark at the end of one piece and the closing mark
   at the start of the next, so neither can find its partner and both render as the literal
   asterisks a reader should never see. `MD_BOLD`'s own `[^*\n]+` cannot span the boundary either,
   so nothing downstream could have recovered it.

   Measured on the corpus this page was built to render: **301 occurrences** across the command
   tree, and the very first bullet of the very first agent anybody opens is one of them. It is the
   flagship surface's most common formatting idiom, and it was the one shape that did not work.

   So the spans are masked to a sentinel, the inline pass runs over the WHOLE line, and the spans
   come back. A NUL (`\u0000`) is the sentinel because it cannot reach here from corpus text and
   matches neither `MD_BOLD` nor `MD_EM` (both refuse `*` and a newline inside, and this has
   neither) — so a mask can be neither forged by the input nor eaten by the pass that runs over
   it. The held text is already escaped: it is a capture from `esc(s)`, not from `s`. */
/* THE ID PASS RUNS INSIDE THE MASK AND AFTER THE MARKS, and both halves of that are load-bearing.

   INSIDE THE MASK: a code span is a literal, which is what a code span MEANS, so a backticked
   `GOV-001` stays the characters an author typed rather than becoming a control inside a
   `<code>`. The spans are already held aside for the inline pass, so running over the masked
   string is free — and it is the only spelling that cannot link one.

   AFTER THE MARKS: `**RUN-008**` is this corpus's own idiom for citing a requirement, and the
   bold pass has to have consumed both asterisk pairs before anything looks for an id, or the id
   and its emphasis compete for the same characters. It is also safe in the only way that
   matters: everything this pass inserts is a tag, the mask sentinel is a NUL no tag contains,
   and the id it matched came out of `esc`'s own output. */
/* A LINK IS HELD ASIDE TOO, for the same reason a code span is and one more. Its TEXT is read
   on its own (`mdInline`, then the code spans come back with everyone else's), so `[**b**](u)` and
   `` [`x`](u) `` keep their marks; and its HREF is out of reach of every pass after it, so an
   `ENG-123` in a URL is never turned into a `.term` anchor inside the attribute, an `*` in one
   never pairs with an `*` in the sentence, and the id pass never nests an anchor inside this one.
   `\u0001` is the sentinel because, like the code mask's NUL, corpus text cannot carry it and no
   pass matches it. Runs AFTER `esc`, so the destination it reads is already attribute-safe: it is
   checked, never re-escaped. */
const MD_LINK = /\[([^\[\]\n]+)\]\((&lt;[^\s]*?&gt;|(?:[^()\s]|\([^()\s]*\))+)\)/g;
function mdHref(dest){
  const d = /^&lt;.*&gt;$/.test(dest) ? dest.slice(4, -4) : dest; /* `[x](<mailto:x>)`, Linear's form */
  if (!d || /[\u0000\u0001\s]/.test(d)) return "";
  return /^(?:https?:\/\/|mailto:)/i.test(d) || /^#/.test(d) || /^\/(?!\/)/.test(d) ? d : "";
}
/* A BARE URL IN A DOCUMENT IS A LINK, the way GitHub draws one. An agent in a Terminals thread
   printed `https://fleet.example.test/?repo=core#issue:ENG-15360` and the operator could not click
   it: only `[text](url)` was an anchor. GFM's autolink rules, over the same escaped string:

   * `<https://…>` and a bare `http(s)://…` — those two schemes and NO OTHER: a bare `javascript:`
     or `data:` has no shape here to match, and `mailto:` stays inside `[text](url)`.
   * THE URL ENDS where GitHub's does: whitespace or `<`/`>`/`"` ends the run, then trailing
     `.,;:!?*_~'` comes off, and a `)` comes off while the URL holds more `)` than `(` — so
     "(see https://x/y)." links `https://x/y`, and `https://en.wikipedia.org/wiki/F_(x)` keeps its
     own pair. The trim reads the RAW characters (`mdRaw`) and escapes again, so `&amp;` is never
     cut to `&amp` by the `;` rule.
   * NEVER INSIDE CODE: a span is masked before this runs, a fence never reaches `mdown`. NEVER
     INSIDE A LINK: the `[text](url)` pass runs first and holds its anchor behind `\u0001`, so the
     URL in its destination and a URL as its text are both out of this pass's reach.
   * Held behind `\u0001` like any other anchor, so the id pass never links the `ENG-15360` in the
     fragment and the emphasis pass never pairs an `*` inside it. */
const MD_AUTO = /&lt;(https?:\/\/(?:(?!&lt;|&gt;)[^\s\u0000\u0001])+)&gt;/gi;
const MD_BARE = /(^|[^A-Za-z0-9])(https?:\/\/(?:(?!&lt;|&gt;|&quot;)[^\s\u0000\u0001])+)/gi;
const mdRaw = s => s.replace(/&(amp|lt|gt|quot|#39);/g, (_, e) => ({ amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'" }[e]));
/* The URL GitHub would link out of a run, on raw characters; "" when nothing past the scheme is left. */
function mdUrlEnd(raw){
  let u = raw;
  for (;;){
    if (/[.,;:!?*_~']$/.test(u)){ u = u.slice(0, -1); continue; }
    if (u.endsWith(")") && (u.match(/\)/g) || []).length > (u.match(/\(/g) || []).length){ u = u.slice(0, -1); continue; }
    break;
  }
  return /^https?:\/\/[^/?#]/i.test(u) ? u : "";
}
const MD_OUT = ` target="_blank" rel="noopener noreferrer"`;
function mdUrlA(url, inner){ return `<a class="md-a" href="${esc(url)}"${MD_OUT}>${inner}</a>`; }
/* A RELATIVE LINK, FOR A CALLER THAT KNOWS WHERE ITS DOCUMENT LIVES (`opts.rel`). `[x](differentiators.md)` in a
   repository document names the file beside it, and only the caller knows which directory "beside" is — so the
   caller answers: `opts.rel(dest)` is given the raw relative destination and returns an in-app route for it, or "".
   A route this page can show (`valid`) is a link built by `link`, like any other destination here; anything else is
   the link's words alone, because the brackets are markdown and the path names a file no browser opens as a page.
   Only a RELATIVE destination is asked: one with a scheme (`javascript:`), or a `/…` or `#…` one, is not the
   caller's to answer, and `null` leaves it exactly as `mdHref` left it. No `opts.rel`, and nothing here runs. */
function mdRel(text, dest, opts){
  const d = mdRaw(/^&lt;.*&gt;$/.test(dest) ? dest.slice(4, -4) : dest);
  if (!d || /^[A-Za-z][A-Za-z0-9+.-]*:|^[/#]|[\s\u0000\u0001]/.test(d)) return null;
  const go = String(opts.rel(d) || "");
  return go && valid(go) ? link(go, "md-a", mdInline(text)) : "";
}
/* Over the ESCAPED, code-masked string only: `mdown` is the one caller. */
function mdLinks(masked, anchors, opts){
  const hold = a => `\u0001${anchors.push(a) - 1}\u0001`;
  return masked.replace(MD_LINK, (m, text, dest) => {
    const href = mdHref(dest);
    if (!href){
      const rel = opts && typeof opts.rel === "function" ? mdRel(text, dest, opts) : null;
      return rel === null ? m : rel ? hold(rel) : text;
    }
    const out = href[0] === "#" ? "" : MD_OUT;
    return hold(`<a class="md-a" href="${href}"${out}>${mdInline(text)}</a>`);
  }).replace(MD_AUTO, (m, url) => {
    const raw = mdRaw(url);
    return mdUrlEnd(raw) === raw ? hold(mdUrlA(raw, url)) : m;
  }).replace(MD_BARE, (m, pre, run) => {
    const url = mdUrlEnd(mdRaw(run));
    if (!url) return m;
    const shown = esc(url);
    return pre + hold(mdUrlA(url, shown)) + run.slice(shown.length);
  });
}
/* A CODE SPAN THAT IS ONE URL AND NOTHING ELSE is still code, and a link: agents wrap the address
   they want clicked in backticks as often as not. Exactly one URL — the whole span, nothing GitHub
   would trim off its end — or it stays the literal every other span is. */
function mdSpan(tag, code, links){
  const raw = mdRaw(code);
  const one = links && /^https?:\/\/\S+$/i.test(raw) && !/[<>"]/.test(raw) && mdUrlEnd(raw) === raw;
  return one ? mdUrlA(raw, tag) : tag;
}
/* A BARE URL IS HELD ASIDE TOO, as the characters it is — not a link, a literal. An
   agent pastes `https://linear.app/x/issue/ENG-123/fix_the_*thing*` without brackets far more often
   than with them, and the id pass then made a `.term` anchor of the `ENG-123` mid-URL while the
   emphasis pass italicised `*thing*`. Same sentinel discipline as the code mask: `\u0002` cannot
   arrive from corpus text and no pass matches it. Run over the escaped string, so the URL can carry
   no `<`, `>` or `"` — the run stops at whitespace, and what comes back is exactly what was held. */
const MD_BARE_URL = /\bhttps?:\/\/[^\s\u0000\u0001\u0002]+/g;
function mdUrls(t, urls){ return t.replace(MD_BARE_URL, url => `\u0002${urls.push(url) - 1}\u0002`); }
/* The links and the URLs back, before the code spans: a link's own text can hold a masked span. */
function mdHeld(t, anchors, urls){
  return t.replace(/([\u0001\u0002])(\d+)\1/g, (_, k, i) => (k === "\u0001" ? anchors : urls)[Number(i)]);
}
function mdown(s, soft, repo, links, opts){
  const held = [];
  const anchors = [];
  const masked = esc(s).replace(MD_CODE, (_, code) => `\u0000${held.push(code) - 1}\u0000`);
  const urls = [];
  const linked = mdUrls(links ? mdLinks(masked, anchors, opts) : masked, urls);
  return mdHeld(mdIds(mdInline(linked), soft, repo, opts), anchors, urls)
    .replace(/\u0000(\d+)\u0000/g, (_, i) => mdSpan(`<code>${held[Number(i)]}</code>`, held[Number(i)], links));
}
/* THE SAME TEXT WITH THE MARKS TAKEN OFF AND NO TAG PUT ON — for an ATTRIBUTE, which is the one
   place on this page a tag cannot go. `data-tip` carries the full sentence a row clipped, and a
   `<code>` inside an attribute value is four literal characters and an angle bracket, not markup.
   So the attribute gets the prose and the line beside it gets the rendering, rather than one of
   them getting backticks because the other could not have them.

   ESCAPED INSIDE, exactly like `mdown` and for the same argument: the failure mode of a call site
   written next year has to be a double escape somebody files as cosmetic, never raw corpus text
   reaching a document. It only ever REMOVES characters, so there is nothing here that could
   introduce a tag even if the order were wrong. */
function mdText(s){
  return esc(s).replace(MD_CODE, "$1").replace(MD_BOLD, "$1").replace(MD_EM, "$1");
}

/* A CLIP CAN CUT A MARK IN HALF, AND HALF A MARK IS THE PUNCTUATION THIS CHANGE EXISTS TO REMOVE.
   `firstSentence` shortens the RAW text on a word boundary, so a code span or a bold run is free
   to straddle the cut: what reaches the renderer is `…all three surfaces that run it today (` with
   its partner 40 characters past the end. An unpaired mark is not a hazard — every pattern above
   needs both halves, so it renders as the literal character — but the literal character is
   exactly what a reader should never have to see. Measured on the 79 `Done when` cells this fleet
   drives: 2 of them clip that way.

   THE UNPAIRED MARK IS DELETED AND THE SENTENCE IS KEPT. The other repair is to cut the string
   back to before the orphan, and it costs far more than it saves: on the longer of those two
   cells it would throw away 90 of 120 characters to avoid one backtick. The word simply loses its
   code styling, which the clip had already half-taken anyway.

   WHICH MARKS ARE UNPAIRED IS COMPUTED, NOT GUESSED. Every construct the renderer will consume is
   blanked out with a run of spaces OF THE SAME LENGTH, so indices still line up with the original;
   whatever ` or * is still standing in that shadow copy has no partner in this string. A count of
   backticks would be wrong the moment one of them sits inside a bold run. */
function mdTrim(s){
  const src = String(s == null ? "" : s);
  const blank = m => " ".repeat(m.length);
  const shadow = src.replace(MD_CODE, blank).replace(MD_BOLD, blank).replace(MD_EM, blank);
  if (shadow.search(/[`*]/) < 0) return src;
  let out = "";
  for (let i = 0; i < src.length; i++) if (shadow[i] !== "`" && shadow[i] !== "*") out += src[i];
  return out;
}

/* ── a description the corpus did not have to write ───────────────────────── */
/*
 * THREE ANSWERS, AND A PAGE THAT RENDERS TWO OF THEM ALIKE IS LYING ABOUT A FILE. A slice's
 * description is `Done when`, a register column, so it is always there. A program has no such
 * column — `programs.md` is `ID | Name | Kind | Verified by | Requires | Disposition` — and what it has instead
 * is an OPTIONAL detail file whose opening paragraph is the description. That makes an absence
 * ORDINARY here rather than exceptional, and it makes the two kinds of absence worth telling
 * apart: `null` is a file nobody wrote, `""` is a file that was read and opens with no prose.
 *
 * Rendered as the same empty line, they are not merely indistinguishable from each other — they
 * are indistinguishable from a description somebody wrote and left blank, which is a fact about
 * the corpus that is not true. So each says which it is, in the words of the thing a reader would
 * have to go and do about it.
 */
const NO_DESC_FILE = "No description — this program has no detail file.";
const NO_DESC_PROSE = "No description — its detail file opens with no prose.";

/* "" when there IS a description, and otherwise the sentence naming which absence this is. */
function descNote(desc){
  if (desc == null) return NO_DESC_FILE;
  return String(desc).trim() ? "" : NO_DESC_PROSE;
}
/* The description as markup, or the absence as a muted note that cannot be mistaken for one.
   `soft` is `mdown`'s own, passed through for the reason `rankChip` gives: the one caller is
   `rowHtml`, and a program row is a `<button>` that a `<button class="term">` in a description
   naming `PG-31` would close early. */
function descHtml(desc, soft){
  const note = descNote(desc);
  return note ? `<i class="nodesc">${esc(note)}</i>` : mdown(desc, soft);
}

/* THE LEGEND, BOTH TIERS — `rollup.BOARD_SLICE_STATES`'s words, in the reader's language.
   `unproven` and `awaiting-proof` were ONE word here ("awaiting proof") until the roll-up split
   them: a named, unshipped proof is outstanding WORK and a blank cell is a missing LINE, and a
   page that drew both the same taught the reader to skip the one it could actually fix.
   `waived` and `withdrawn` are the two PARKED states — a decision somebody wrote down — and
   every list on this page draws them collapsed, at the foot, out of the counts. */
/* `complete` IS THE ROLL-UP'S KEY AND `proven` IS THE READER'S WORD (ENG-10589). The model's
   terminal reading is "finished when PROVEN, not when its parts exist", and a chip reading
   "complete" beside "1 to do" was read on the production board as a contradiction — a customer
   reads complete as done, where the one thing left on a proven program is a person's judgement
   that the proof drove the whole thread. The key stays: it is the wire's word, the store's CHECK
   constraint and every consumer's; only what a reader sees changes, and it changes in one place. */
const STATE = { complete: "proven", flight: "in flight", "awaiting-proof": "awaiting proof",
                unproven: "no proof named", waived: "proof waived", withdrawn: "withdrawn",
                empty: "no PRDs", abandoned: "all cancelled" };
/* THE BOARD'S WORD FOR A STATE, for a host page that names a program or a slice outside this file
   (ENG-10693): the idea page's proposal tree said "in execution" beside a program because it
   printed the words route typed on the day it proposed, and the board's own reading was one map
   away. Exported so there is one vocabulary, and a token with no word reads as itself. */
function stateWord(state){
  return STATE[state] || String(state || "");
}
/* WHOSE PROOF, when the word alone misleads (ENG-10599). `proof waived` on SL-099 sat beside a
   proof card naming 0358 as a PRD of SL-099, and a reader took the two as one story told two
   ways. They are two facts: the SLICE's own proof — "does this cut do what it said?" — is
   waived by decision, and the PROGRAM's composed proof is a PRD that happens to live in the
   cut. The chip says which, so the card beside it can say the other. */
const STATE_TIP = {
  waived: "This slice names no proof of its OWN — waived by decision in the slices baseline. A program's proof may still sit in it; that PRD proves the program, not this slice.",
};
/* ONE CHIP FOR A WITHDRAWN CUT, and the record in its tip (ENG-10599, NEW-9): the state chip
   said "withdrawn" and a second chip said `WITHDRAWN · DECISIONS/<date>-….MD` — the
   decision's file path through the chip's uppercase. The chip is the word; the tip names the
   record — the cut's own, or its program's when the cut is withdrawn with the program. The
   entity's own page prints the path in code style (`dispositionFact`). */
function sliceStateChip(s){
  const state = s.state;
  if (state === "withdrawn"){
    const own = s.disposition && s.disposition.kind === "withdrawn" ? s.disposition.ref : "";
    const p = PG[s.program];
    const parent = !own && p && p.disposition && p.disposition.kind === "withdrawn" ? p.disposition.ref : "";
    const why = own ? `Withdrawn by decision — the record is the reason: ${own}`
              : parent ? `Withdrawn with its program ${s.program} — the record is the reason: ${parent}`
              : "Withdrawn by decision.";
    return badge(STATE.withdrawn, "withdrawn", "", why);
  }
  /* A DEFERRED WAIVER owes its proof: the chip reads "awaiting proof" and its tip says what is
     owed, so the cut is never drawn as a decision nobody has to act on. */
  if (s.owed) return badge(STATE[state] || state, state, "", `Proof owed: ${s.owed}. Its waiver defers the proof rather than excusing it, so this slice and its program stay open until the proof lands.`);
  return badge(STATE[state] || state, state, "", STATE_TIP[state] || "");
}
/* WHAT A PROGRAM WAITS ON, BY A DEFERRED WAIVER: its own proof's, then each open cut's —
   "waiting on SL-188's proof: live measurement on a deployed plane", the sentence `rollup.waiting_on`
   writes into the program's flags. Read off the rows, so a payload rebuilt from stored rows says the same. */
function waitingOn(p){
  if (!p || p.state === "withdrawn") return [];
  const own = p.owed && !(p.proof || []).length ? [`waiting on ${p.id}'s proof: ${p.owed}`] : [];
  return own.concat((p.sl || []).filter(s => s.owed && s.state === "awaiting-proof")
    .map(s => `waiting on ${s.id}'s proof: ${s.owed}`));
}
function waitingChip(p){
  const w = waitingOn(p);
  if (!w.length || p.complete) return "";
  const first = w[0].replace(/:.*$/, "");
  return badge(w.length === 1 ? first : `${first} +${w.length - 1}`, "unproven", "", w.join(" · "));
}
const PARKED = ["waived", "withdrawn"];
const TERMINAL = ["shipped", "cancelled"];

/* A program is parked when the roll-up says so. `p.state` is 0093's word; a payload rebuilt
   from before it was stored carries `null`, and `null` is not parked — nobody looked, so the
   row stays in the list it always sat in rather than dropping out of it on a missing field. */
const isParked = p => PARKED.includes(p.state);

/* ── the two kinds of proof ───────────────────────────────────────────────── */
/* A `Verified by` entry is a PRD number or `drill:<stem>` — the record of an observation the
   harness measured. The second kind resolves against `D.drills` (stem -> {verdict, daemonSha})
   rather than `PRD`, and its verdict is printed beside it: a bare tick on a drill would hide
   the one fact that makes it a proof, and a `not in the corpus` on it would call a record a
   missing PRD. */
const DRILL = "drill:";
const isDrill = n => String(n).startsWith(DRILL);
const drillStem = n => String(n).slice(DRILL.length);
/* A DRILL IN A PERSON'S WORDS: its stem without the date it was written on or the "composed proof" it names, the program id in capitals
   ("0900-pg30-composed-proof" plus its date reads "0900-PG30"). The record's own id stays in the tooltip and the lookups. */
const drillShort = n => drillStem(n).replace(/-\d{4}-\d{2}-\d{2}$/, "").replace(/-composed-proof$/i, "").replace(/\bpg(\d+)/gi, (_m, n) => "PG" + n);
function drillOf(n){ return (D && D.drills && D.drills[drillStem(n)]) || null; }
/* One proof entry as a chip: a PRD links to its page; a drill names its stem and its verdict,
   green only on `passed` — the one word `rollup.proof_shipped` reads as shipped. */
function proofBadge(n, cls){
  if (!isDrill(n)){
    return badge(n, cls === undefined ? (PRD[n] ? "" : "attn") : cls, n);
  }
  const rec = drillOf(n);
  const verdict = rec ? rec.verdict : "no record";
  return `<span class="chip ${verdict === "passed" ? "complete" : rec ? "unproven" : "attn"}"
    data-tip="A drill record, not a PRD: ${esc(drillStem(n))}${rec && rec.daemonSha ? " proves " + esc(rec.daemonSha.slice(0, 12)) : ""}">${esc(n)} &middot; ${esc(verdict)}</span>`;
}
/* THE PROGRAM PROOFS THAT LIVE IN THIS CUT, for a waived slice's own proof line: "0358 proves
   PG-09" — the fact the program page's proof card states from the other side. */
function housedProofs(s){
  const p = PG[s.program];
  if (!p) return "";
  const here = (p.proof || []).filter(n => !isDrill(n) && PRD[n] && PRD[n].slice === s.id);
  if (!here.length) return "";
  return "; " + here.map(n => `${proofBadge(n, "")} proves ${badge(p.id, "", p.id)}`).join(", ") + " &mdash; the program, not this slice";
}
/* The proof cell as prose, for a row that has no room for chips. */
function proofText(proof){
  return proof.map(n => isDrill(n)
    ? `${n} (${(drillOf(n) || { verdict: "no record" }).verdict})`
    : n).join(", ");
}

/* ── the decision axis ────────────────────────────────────────────────────── */
/* `Disposition`, verbatim from the register: WHICH decision record, or WHICH successor. A
   parked state is the one state a page has to explain in the register's own words, because
   the state alone says "out of the plan" and not why. `adopted` — the norm — says nothing. */
function dispositionFact(d){
  if (!d || d.kind === "adopted") return "";
  if (d.kind === "withdrawn") return `withdrawn &mdash; <code>${esc(d.ref || "")}</code>`;
  /* A PROGRAM CLOSED INTO FEATURES (FLT-1283) names no successor row to link to; the UI says Feature, never Area. */
  if (d.kind === "superseded" && d.ref === "areas") return "superseded by features";
  if (d.kind === "superseded") return `superseded by ${badge(d.ref || "", "", d.ref)}`;
  return esc(d.kind);
}
/* A CUT'S DISPOSITION, ITS OWN OR ITS PROGRAM'S: a cut under a withdrawn program is withdrawn
   with it whatever its own cell says (the register's rule), and its page names the program's
   record in code style — never as a chip (ENG-10599, NEW-9). */
function sliceDispositionFact(s){
  const own = dispositionFact(s.disposition);
  if (own) return own;
  const p = PG[s.program];
  if (s.state === "withdrawn" && p && p.disposition && p.disposition.kind === "withdrawn"){
    return `withdrawn with its program ${badge(p.id, "", p.id)} &mdash; <code>${esc(p.disposition.ref || "")}</code>`;
  }
  return "";
}
/* The same reading on a program row, in the row's own flag line. */
function dispositionLine(d){
  const fact = dispositionFact(d);
  return fact ? `<span class="rflags"><i class="flag">${fact}</i></span>` : "";
}
/* And as ONE chip, for a badge list — where a `superseded by` link would be a chip inside a
   chip, so the successor is named in text and the row's own id chip is what navigates. */
function dispositionChip(d){
  if (!d || d.kind === "adopted") return "";
  /* A WITHDRAWN CUT IS ITS STATE CHIP (`sliceStateChip`), which carries the record in its tip
     (ENG-10599, NEW-9): a second chip with the decision's file path went through the chip's
     uppercase and read as `WITHDRAWN · DECISIONS/<date>-PROGRAM-REGISTER-CLOSE-OUT.MD`. */
  if (d.kind === "withdrawn") return "";
  const words = d.kind === "superseded"
    ? (d.ref === "areas" ? "superseded by features" : `superseded by ${esc(d.ref || "")}`)
    : esc(d.kind);
  return `<span class="chip ${esc(d.kind)}">${words}</span>`;
}

/* ── the readings only a person can act on ────────────────────────────────── */
/*
 * FOUR FIELDS THAT WERE ON THE WIRE AND ON NO PAGE. `flags`, `bar`, `requires` and the
 * per-slice `blockedBy` were all computed, carried through the store and never rendered — a
 * board that had worked out what only a human could settle and then declined to say it.
 *
 * They are read here rather than restated: every sentence below either comes out of the
 * payload verbatim (`flags`) or is a count of what the payload holds. Nothing in this section
 * decides anything the corpus has not already decided.
 */

/* A program's flags used to be drawn here, verbatim, as lines on its row. The program lifecycle
   took them off: each one is a to-do with a command (`board.py::actions`), counted on the row and
   listed on the program page, or it is not shown at all. `flags` stays on the wire for the
   generators that read it. */

/* A `## Bar` as the three numbers it is, or the fact that there is none.
   ABSENCE IS THE READING THAT MATTERS and it is stated in words: on the deployed corpus 20 of
   21 programs and 77 of 79 slices author no bar, so a blank cell here would be the ordinary
   case rendered as nothing at all. `digestOk` is a claim about the tier's own contract — a
   slice bar binds to bytes in another file and a program bar binds to nothing — so a false
   reading says which way it is wrong rather than asserting a digest went missing. */
function barFact(b){
  if (!b) return `<i class="nodesc">none written &mdash; nothing says what would have to be seen.</i>`;
  const bits = [`${b.n} criteri${b.n === 1 ? "on" : "a"}`,
                b.unprobed ? `${b.unprobed} unprobed` : "all probed"];
  if (!b.digestOk) bits.push("digest not as its tier requires");
  /* `<i>` AND NOT `<span>`. These sit inside `.kv b`, and `.kv span` is a descendant rule that
     paints every span in that block as a .61rem uppercase faint LABEL — so a span here would
     have been silently restyled into the key it sits beside. */
  return `<i class="barfact${b.unprobed || !b.digestOk ? " attn" : ""}">${esc(bits.join(" · "))}</i>`;
}

/* `requiresFact` STOOD HERE and the operator asked the reading off the page. It drew a
   program's decomposition roots — the capability ids `gen_program_plan` closes its build order
   over — and kept two absences apart that look alike: `null` for a payload rebuilt from before
   the field was carried, `[]` for a program that names none. Both readings were correct and
   neither was wanted: a reader on a program page is asking what to do about it, and a list of
   the ids a generator consumes answers a question nobody on this page had.

   WHAT IT WAS GUARDING IS NOT LOST, and that is why this went rather than being hidden. The
   `[]` case is the `undecomposed` FINDING (`board.py`), which still fires, still carries its
   own sentence and still hands over `program_decompose` in "To do here" — where a thing
   somebody must act on belongs. What retires is the passive restatement beside it. `requires`
   stays on the wire for `gen_program_plan`, which is its only reader. */

/* IS THIS CUT OPEN — `board.py`'s `open_slice`, in this file's words (ENG-10589). Not proven,
   and not parked by a decision: a withdrawn or waived cut "sits outside every open count"
   (tracking-and-execution, "Durable vs versioned"), and every reading below that filtered on
   `complete` alone counted them in — PG-09's proof chain listed two cuts of the withdrawn PG-14
   as open work, and the Dependencies page drew them in wave 0. One predicate, so the header's
   figure, the chain's cards and the graph's cards cannot disagree about what is still standing. */
function openSlice(s){ return s.state !== "complete" && !PARKED.includes(s.state); }

/* The stricter reading, and the one a state chip may use: EVERY open cut is waiting, so there
   is nowhere in this program anybody could start. Derived from `blockedBy`, which the payload
   already carries per slice — no new field, and none needed. `[]` when even one cut is free,
   because "some of it is blocked" is not a state, it is a detail of two rows. */
function blockedSlices(p){
  const open = (p.sl || []).filter(openSlice);
  return open.length && open.every(s => s.blockedBy.length) ? open : [];
}

/* ── the build steps: one graph over PRDs, slices and programs ─────────────
 *
 * THE STEPS COME FROM THE PRDs' OWN `depends_on`, and `board.py`'s `prd_waves` computes them — a
 * PRD's `wave`, a slice's, a program's. The slice register's `Depends on` used to decide them, and
 * it is far coarser than the chains the fleet actually works through: production drew nearly every
 * open cut in step 0 while its open PRDs ran eight deep behind one another. A cut's `Depends on`
 * is still on every slice (`dep`, `blocks`, `blockedBy`) as authored ORDER, and still drawn as
 * such; it no longer places anything in a step.
 *
 * THREE KINDS OF NODE AND ONE RULE PER KIND, and each waits on the tier beneath it:
 *   a PRD      waits on the open PRDs it `depends_on`;
 *   a slice    waits on its own open PRDs (and an open PRD its proof names);
 *   a program  waits on its open slices and its open composed-proof PRDs.
 * A settled thing reads no step (`wave` is `null`) and is not a node: a shipped prerequisite is
 * met, and drawing it would put an arrow pointing backwards on the page.
 *
 * `up` is what a node waits on, `down` what waits on it — both over nodes that are in play, so a
 * chain lit on hover walks exactly what the payload placed. Built once per payload, lazily: the
 * chain highlight is bound at the document and asks for it on the first hover. */
let WAVE_G = null;
function inStep(x){ return !!x && typeof x.wave === "number"; }
/* A slice or program the payload places, AND still open by its own state — the same `openSlice`
   every other count on the board reads, so a cut whose state says it is finished is never drawn
   as waiting, whatever step it was last handed. */
function inPlay(x, kind){
  if (!inStep(x)) return false;
  if (kind === "slice") return openSlice(x);
  if (kind === "program") return !x.complete && x.state !== "complete" && !PARKED.includes(x.state);
  return true;
}
function waveGraph(){
  const nodes = {}, up = {}, down = {};
  const add = (id, kind, x, prog) => { nodes[id] = { id, kind, x, prog: prog || "" }; up[id] = new Set(); down[id] = new Set(); };
  /* `from` waits on `to`. An edge to something not in play is met, dangling or parked: no node. */
  const edge = (from, to) => { if (nodes[from] && nodes[to] && from !== to){ up[from].add(to); down[to].add(from); } };
  Object.values(PRD).forEach(r => { if (inStep(r)) add(r.n, "prd", r, r.program); });
  Object.values(SL).forEach(s => { if (inPlay(s, "slice")) add(s.id, "slice", s, s.program); });
  D.programs.forEach(p => { if (inPlay(p, "program")) add(p.id, "program", p, p.id); });
  Object.values(PRD).forEach(r => (r.dep || []).forEach(d => edge(r.n, d)));
  Object.values(SL).forEach(s => { (s.prds || []).forEach(r => edge(s.id, r.n)); (s.proof || []).forEach(n => edge(s.id, n)); });
  D.programs.forEach(p => { (p.sl || []).forEach(s => edge(p.id, s.id)); (p.proof || []).forEach(n => edge(p.id, n)); });
  return { nodes, up, down };
}
function waveG(){ return WAVE_G || (WAVE_G = waveGraph()); }

/* EVERYTHING STANDING BETWEEN THIS PROGRAM AND ITS PROOF, HOWEVER FAR OUT — the program's upward
   closure through the build-step graph: its open slices, their open PRDs, its open proof PRDs and
   every open PRD those wait on, transitively. That last set is where somebody else's work shows up:
   a PRD of this program that `depends_on` another program's open PRD cannot start before it, and a
   page listing only this program's own slices would report it nearly done while the work left is
   elsewhere. The program's own node is not in the set — its proof column closes the chain.

   SETTLED WORK IS NOT IN IT, and not merely to shorten the list: a step counts UNMET prerequisites,
   so a shipped PRD beside the open one that waited on it would draw an arrow pointing backwards.
   `viewDeps` drops the same set for the same reason, so the two pages cannot disagree. */
function programChain(p){
  const g = waveG();
  if (!g.nodes[p.id]){
    /* A program not in play has nothing standing before its proof. */
    return [];
  }
  const seen = new Set(), stack = [...g.up[p.id]];
  while (stack.length){
    const id = stack.pop();
    if (seen.has(id) || !g.nodes[id]) continue;
    seen.add(id);
    g.up[id].forEach(d => stack.push(d));
  }
  return [...seen].map(id => g.nodes[id]);
}

/* ── the knowledge corpus, indexed ────────────────────────────────────────────
 *
 * THE BOARD HELD THREE REGISTERS AND THE CORPUS HAS NINE. Programs, slices and PRDs are the
 * DELIVERY half — what is happening now. The other half is what the delivery is FOR: a
 * requirement, a capability, a decision, a component, a journey, a feature area. Those ids are
 * all over this board already — in a `Done when`, in a PRD's `implements:`, in an agent's
 * question — and until this index existed every one of them was a dead `<span>`.
 *
 * WHAT THE INDEX IS, and the whole of it:
 *
 *   { kinds: [{ kind, title, blurb, section, count, chips: [{text, cls}] }, ...],
 *     ids:   { <kind>: ["GOV-001", ...], ... } }
 *
 * IT IS ITS OWN READ AND NOT A FIELD ON THE BOARD PAYLOAD, and that is a decision rather than a
 * detail. The board payload is a reading of one commit's PLAN — programs, cuts, PRDs — and this
 * is a reading of the corpus that plan is FOR; they are two questions, they change on different
 * days, and hanging the second off the first would make every board request carry three thousand
 * ids whether or not anybody opened the tab. It is asked ONCE, at boot, through the host's own
 * seam, beside `/api/corpora` and for the same reason: every page can contain an id, so the
 * answer has to be in hand before any of them renders rather than when one of them is opened.
 *
 * `ids` IS THE ONLY PART `routeOf` NEEDS, and it is grouped by kind rather than spelled as a flat
 * `id -> kind` map for one measured reason: three thousand entries carrying their kind's name
 * each is the same fact written three thousand times. It is inverted once, on arrival.
 *
 * `kinds` IS A DESCRIPTION OF THE CORPUS AND NOT A TABLE IN THIS FILE. Which kinds exist, what
 * each is called, which of the tab's sections it belongs under and how many rows it holds are
 * facts about a repository's knowledge base, so the repository answers them. That is what makes
 * `architecture` — the next kind — cost nothing here: one more row in `kinds`, one more key in
 * `ids`, and it appears under System with a list and a detail page, with no new route, no new
 * endpoint and no new page type. A kind hard-coded into this file would have cost all three.
 *
 * NOTHING HERE IS REQUIRED. With no host seam there is no index, `routeOf` answers `""` for every
 * id it does not hold, and the board is exactly what it was — which is what the standalone page
 * IS. THREE STATES, NEVER ONE, for the reason `corpusPlaceholder` gives: "no server to ask",
 * "still coming" and "the ask failed" render the same empty page otherwise, and an operator
 * debugging the third debugs the first.
 */
/* The corpus's own answer, or `null` while nobody has asked and nothing has arrived. */
let KINDEX = null;
let KINDEX_ERR = "";
let KIND_OF = {};
/* `kind -> Set(id)`: validity is per (kind, id), because the server resolves by the pair. */
let KIND_IDS = {};
let KKINDS = [];

/* Where the index has got to, in the four answers a reader can be given about it. */
function kIndexState(){
  if (!KNOWLEDGE_LOADER) return "absent";
  if (KINDEX_ERR) return "failed";
  return KINDEX === null ? "loading" : "ready";
}
/* The index, inverted and completed. A kind with ids and no description is still a kind: it
   stays indexed (so its ids link) and appears under its own name, rather than vanishing off the
   one page whose job is to list everything there is. A duplicate id across two kinds keeps the
   FIRST that claimed it in `KIND_OF`, which answers only for an id met ALONE (prose, a search box).
   A feature area and a component may legitimately share an id; a ROUTE names its kind, so whether it
   is valid is read from `KIND_IDS` — the pair — and never from the first claimant. */
function kIndexed(payload){
  KINDEX = (payload && typeof payload === "object") ? payload : {};
  KINDEX_ERR = "";
  KKINDS = (KINDEX.kinds || []).slice();
  KIND_OF = {};
  KIND_IDS = {};
  const ids = KINDEX.ids || {};
  Object.keys(ids).forEach(k => { KIND_IDS[k] = new Set(ids[k] || []); });
  Object.keys(ids).forEach(k => (ids[k] || []).forEach(id => { if (!KIND_OF[id]) KIND_OF[id] = k; }));
  Object.keys(ids).forEach(k => { if (!kKind(k)) KKINDS.push({ kind: k, count: (ids[k] || []).length }); });
  refsChanged();
}

/* READING THE INDEX, WHICH IS A THING THAT HAPPENS ONCE PER REPOSITORY AND NOT ONCE PER PAGE.
 *
 * Called at boot and again the moment a reader picks another repository — and the second call is
 * the one this function exists for. `KNOWLEDGE_CACHE` and `PROSE_CACHE` are keyed through
 * `textKey`, so a second repository's `GOV-001` is already a different entry; the INDEX was not,
 * because it is module state set once. So a switch left the previous repository's kinds, counts
 * and ids in place: the Knowledge tab counted rows out of a corpus nobody was looking at, and
 * `routeOf` went on linking ids the new repository may not hold — a link that can only ever land
 * on "this generation has no such entity", which is the one outcome the index bound exists to
 * make impossible.
 *
 * CLEARED BEFORE THE READ, never after it. The tab draws "reading the corpus index…" for a null
 * index and the old repository's numbers for a stale one, and of the two only the first is true
 * while the request is in flight. */
function kBoot(after){
  if (!KNOWLEDGE_LOADER) return;
  KINDEX = null;
  KINDEX_ERR = "";
  KKINDS = [];
  KIND_OF = {};
  KIND_IDS = {};
  K_AREAS = null;
  K_AREAS_ERR = false;
  K_AREAS_DONE = false;
  K_READY = null;
  K_READY_ERR = "";
  krPartReset();
  KNOWLEDGE_LOADER("").then(
    payload => { kIndexed(payload); if (after) after(); },
    err => { KINDEX_ERR = "The corpus index could not be read: "
               + ((err && err.message) ? String(err.message) : String(err));
             if (routeParts(openRoute())[0] === "knowledge") render(openRoute()); });
}

/* CAN THIS PAGE ACTUALLY SHOW AN ENTITY? — asked before any id is turned into a link, and it is
   the honest half of the widening. The index alone says an id EXISTS; the detail behind it is a
   separate read, and `fleet-knowledge`'s standalone page has no server to make it. A board
   holding the index with nothing behind it must leave those ids as text: a link to a page that
   can only say "not here" is worse than the plain word it replaced. */
function kServed(){ return !!KNOWLEDGE_LOADER && KKINDS.length > 0; }

/* Where an id lives, so any badge can navigate. */
function routeOf(id){
  if (PG[id]) return "program:" + id;
  if (SL[id]) return "slice:" + id;
  if (PRD[id]) return "prd:" + id;
  /* ONE ROUTE KIND FOR THE WHOLE CORPUS — `knowledge:<kind>:<id>`, and the kind is a VALUE in it
     rather than a route of its own. `routeParts` splits on the first colon only, so the argument
     arrives whole and the view splits it once more. That is the same discipline the API is under:
     a new kind is a new value, never a new endpoint. */
  const k = KIND_OF[id];
  return k && kServed() ? "knowledge:" + k + ":" + id : "";
}

/* WHICH REGISTER HOLDS THIS ID, AS THE KIND A HOST'S SESSION RECORDS — the same question
   `routeOf` answers, read one level down.

   A register id routes as `program:…`, `slice:…` or `prd:…`, and those first segments ARE the
   kind. A corpus id routes as `knowledge:<kind>:<id>`: the first segment names the ROUTE, not
   the register. Sending it as the entity kind asked the workstation API for a subject it has
   never heard of, so a requirement page's Start was refused with "unknown entity kind
   'knowledge'" (ENG-22469). `""` for an id no register holds, which the host sends as no entity
   at all. */
function entityKindOf(id){
  const route = routeOf(id);
  if (!route) return "";
  const parts = route.split(":");
  return parts[0] === "knowledge" ? (parts[1] || "") : parts[0];
}

function badge(text, cls, id, tip){
  const go = id ? routeOf(id) : "";
  const tipAttr = tip ? ` tabindex="0" data-tip="${esc(tip)}"` : "";
  return go ? link(go, `chip ${cls || ""} link`, esc(text), tipAttr)
            : `<span class="chip ${cls || ""}"${tipAttr}>${esc(text)}</span>`;
}
/* The first sentence, capped on a word boundary. Semantic truncation first; the CSS
   ellipsis then handles whatever still does not fit the column. */
function firstSentence(text, cap = 120){
  const t = String(text || "").trim();
  if (!t) return "";
  const m = t.match(/^[\s\S]*?[.!?](?=\s+[A-Z(`"']|$)/);
  let s = (m ? m[0] : t).trim();
  if (s.length > cap){
    s = s.slice(0, cap);
    s = s.slice(0, Math.max(s.lastIndexOf(" "), 40)).trim();
    return s + "…";
  }
  return s;
}

const store = {
  get(k, d){ try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v){ try { localStorage.setItem(k, v); } catch { /* private window */ } },
};

/* ── WHICH REPOSITORY THIS PAGE IS READING ─────────────────────────────────
 *
 * ONE FILE, SEVERAL REPOSITORIES. `fleet-service` serves a board per configured corpus and a
 * request says which one it means (`?repo=<lane>`); this file has to hold the answer, because
 * every page below is about ONE repository and a reader who cannot see which is a reader who
 * will eventually read the wrong one. It is declared HERE, above the Programs list, for a
 * concrete reason rather than for tidiness: the reader's sort and filter are keyed by it, and
 * a `let` read before its declaration is a TDZ throw rather than a stale value.
 *
 * THE KEY IS THE LANE NAME, and the primary has one too. `/api/corpora` says which lane each
 * corpus ANSWERS FOR (`answersLane`) — the primary answers for the deployment's default lane
 * even when it was configured without one — and that name is what `?repo=` takes, what a
 * `repo:*` label already carries, what the page URL carries and what the reader sees in the
 * selector. Never a URL, never an index: a lane name is the one spelling that fits in a query
 * string without being escaped into one, and the one an issue is already joined on.
 *
 * `""` IS STILL A REAL VALUE AND NOT AN ABSENCE, in exactly one place: BEFORE the list has been
 * read, and wherever there is nothing to choose between. The primary is addressed by asking for
 * nothing — which is what every request meant while there was only one corpus — so `""` means
 * the primary at boot without waiting for `/api/corpora` to land, and it goes on meaning the
 * primary for the whole life of a page that serves one corpus, where a name would be a label on
 * a choice nobody can make. Once a second corpus is listed the primary's key becomes its lane
 * name (`keyOf`), `REPO` is re-keyed to it in place, and `""` is thereafter only the spelling a
 * server predating `answersLane` leaves the primary with. A route of `repo:` with an empty
 * argument is the primary under either spelling, which is why nothing here treats an empty key
 * as "unset".
 *
 * THE STANDALONE FILE HAS NO LANE, NO SELECTOR AND NO SECOND CORPUS. It is generated against
 * one checkout, so `CORPORA` stays null there for the life of the page and every branch below
 * that asks for it falls to the single-repository answer, which is the honest one. It writes no
 * `?repo=` into its URL and nothing into `zb.repo`, and neither does a deployment serving one
 * corpus: both are byte-for-byte what they were before a second repository existed.
 */
let REPO = "";
/* A NAME THE PAGE WAS ASKED FOR AND COULD NOT HONOUR — `?repo=` in the URL or a stored `zb.repo`
   naming a corpus this deployment does not serve, or one it serves and has never synced. The
   page falls to the primary, which is the only honest landing, and holds the refused name here so
   the host can SAY it was refused: a reader who followed a link to `?repo=ops` and landed on
   another repository's board without a word would take the board for `ops`. Cleared by the next
   successful switch, and by the reload the corrected URL invites. `{ name, why }`, or null. */
let REPO_REFUSED = null;
/* WHO WANTS TO KNOW WHEN THE REPOSITORY MOVES. The host paints a selector in its own masthead
   off this file's state — the list, the current key, a switch in flight, the last refusal — and
   that state changes on events no render carries: the list landing at boot, a switch beginning.
   So it is told, through one seam, rather than left to poll `repo()` on every route hook. */
const REPO_HOOKS = [];
/* What `GET /api/corpora` said, or null when nobody has asked or the ask failed. NEVER a
   fabricated one-row list standing in for a deployment that could not answer: an index built
   over a guess is an index that would report five repositories as one. */
let CORPORA = null;
let CORPORA_ERR = null;
/* One command tree per repository, for the INDEX only — `{ state, tree, err }` keyed by repo
   key. The index compares repositories, and a comparison needs every side of it; the reader's
   own repository is already in `D` and is never re-fetched for this. */
const REPO_TREES = {};
/* The switch in flight, and what went wrong with the last one. A switch replaces the whole
   payload, so the page says it is doing that rather than going blank and coming back. */
let SWITCH_BUSY = null;
let SWITCH_ERR = null;
/* WHICH REPOSITORY THE LAST REFUSAL WAS ABOUT, and it is load-bearing rather than diagnostic:
   `render` is what starts a read for a repository the page is not holding, so without a record of
   the one that just failed it would start it again on the render that reports the failure, and
   again on the one after that, forever. */
let SWITCH_FAILED = null;

/* THREE MORE HOST SEAMS, ALL OF THEM OPTIONAL AND ALL OF THEM DEGRADING TO ONE REPOSITORY.
   This package is the RECORD and may not learn that somewhere there is a service serving several
   corpora — the same rule `runbox`, `reorder` and `badges` already keep. `corpora` asks what is
   configured, `repoBoard` reads one repository's board WITHOUT installing it (the index compares,
   it does not navigate), and `switchRepo` is the one that replaces the payload under the reader.
   Registered together or not at all: a selector that could list repositories and not open one
   would be a control that does nothing when pressed. */
let CORPORA_LOADER = null;
let REPO_BOARD_LOADER = null;
let SWITCH_REPO = null;

/* THE READER'S SORT AND FILTER ARE A PROPERTY OF A REPOSITORY'S BOARD, so the key they are
   stored under carries the repository. Unprefixed they leak: switch from a four-program lane
   with `stalled only` set to a lane with two programs and neither of them stalled, and the
   Programs list is empty with a filter the reader set somewhere else.

   THE PRIMARY KEEPS THE UNPREFIXED KEY IT HAS ALWAYS WRITTEN, AND THAT IS DECIDED BY IDENTITY
   RATHER THAN BY SPELLING. The primary's key used to be `""` and is now its lane name where a
   second corpus exists, so a rule of "prefix whenever `REPO` is non-empty" would move every
   reader's stored sort and filter from `zb.sort` to `zb.sort:<lane>` the day a deployment grew a
   second repository — and a choice that has to be made again is a choice that was forgotten. So
   the question asked is "is this the primary", through `isPrimary`, and the primary reads and
   writes the bare key under either spelling. A single-corpus deployment and the standalone file,
   which has no lane at all, are therefore byte-for-byte what they were, and nobody's stored
   choice is forgotten by this change. `isPrimary` is declared with the corpus helpers below and
   is hoisted; only `let` bindings are subject to the TDZ this block is placed above for. */
function prefKey(name){ return isPrimary(REPO) ? name : name + ":" + REPO; }

const RANK_WHY = {
  authored: () => "your authored order",
  program:  f => `inherited from ${f}, its program`,
  slice:    f => `its most urgent slice, ${f}`,
  dependency: f => `${f} waits on this, so it is at least as urgent`,
};
/* THE CHIP SAYS WHERE ITS NUMBER CAME FROM, in words, on the chip.
   It used to say it in a BORDER STYLE — solid for a rank a human wrote, dashed for one this
   board worked out — which then needed a sentence under the page's `i` translating the two,
   and a reader who never opened that panel had a number with no provenance. `#3` is now a
   rank somebody authored and `#3 via SL-168` is one this board derived, naming the row it
   derived it from; the encoding is read instead of decoded, and the sentence is gone.
   `tabindex` because the full reason rides a tooltip, and a tooltip no keyboard can reach is
   a tooltip half the readers do not have. */
function rankChip(n, src, from, soft){
  if (!n) return "";
  const why = (RANK_WHY[src] || (() => "inherited"))(from);
  const inh = src && src !== "authored";
  /* THE SOURCE ID IS THE SAME DESTINATION IT IS ANYWHERE ELSE — a plain `via SL-168` next to
     a chip that links SL-168 on the row above was the gap. `mdown` resolves through `routeOf`
     and leaves an unknown id as text, so a rank whose `from` is not on this board stays plain.

     `soft` IS `mdown`'s OWN, PASSED THROUGH, and the one caller that sets it is `rowHtml`: a
     program row is itself a `<button>`, and a `<button class="term">` inside one does not nest —
     the HTML parser closes the row at the inner start tag, and everything written after
     `via SL-149` (the `not placed` chip, the count cell, the chevron) lands beside the row as
     orphaned cells. Measured on the production corpus, on the one unplaced program ranked
     through a slice. The header's chip list and the entity tables sit in a `<div>` and a `<td>`
     and keep the real button, which is keyboard-activable on its own. */
  const via = inh && from ? ` <i>via ${mdown(from, soft)}</i>` : "";
  return `<span class="chip rank${inh ? " inh" : ""}" tabindex="0"
    data-tip="Priority ${n} — ${why}">#${n}${via}</span>`;
}

/* ── ONE PRIORITY READING PER PROGRAM (ENG-10692) ─────────────────────────────
   `rankChip` above reads a rank off its triple, and for a slice or a PRD that is enough. For a
   PROGRAM it was not, and production showed three ways: `#1 via SL-118` beside `not ranked` on a
   program nobody placed (PG-15), `#2 via SL-135` on a program the person placed 5th with the 5
   nowhere on the row (PG-21), and `#1 via SL-089` on a withdrawn program's header (PG-14).

   So a program gets ONE reading, built here and drawn by the resting row, the program header and
   Reorder mode alike:

     * `priority N` — the fleet's number. A PRIORITY and not a place in line: programs share one
       (lowest wins, and a program a placed one needs takes that number), and the scheduler's graph
       keys sit above it, so "2nd in line" would promise a queue position nothing keeps.
     * `you placed it 5th` — the person's own act, said only when the fleet's number differs from
       it. When they agree, `priority 4` already is the placement, and the tooltip says so.
     * `PG-08 needs it` — the reason, naming the program whose placement the number is
       (`rankRoot`), never the slice id the resolver walked through; the slice is in the tooltip.
     * `not in your order` — the absence, in the words Reorder mode uses for the same list.

   REORDER MODE DRAWS LESS, ON PURPOSE. The position box is the person's placement and it moves as
   they drag; a chip repeating `priority 2 · you placed it 5th` beside a box that now reads 3 would
   put the contradiction back. So the mode keeps only the fact a draft cannot make stale — who
   needs it — and the absence on a row the draft leaves below the line.

   A PARKED PROGRAM HAS NO READING. Withdrawn or waived, it is out of the plan: `board.py` resolves
   it to no rank, and a payload from before that change is read the same way here. */
function ordinal(n){
  const tens = n % 100, ones = n % 10;
  const tail = tens >= 11 && tens <= 13 ? "th" : ones === 1 ? "st" : ones === 2 ? "nd" : ones === 3 ? "rd" : "th";
  return `${n}${tail}`;
}
/* ── A PLACEMENT IS A PLACE IN AN ORDER, AND THE PAGE SAYS THE PLACE (ENG-10701, K-06) ─────────
   The store keeps a NUMBER per placement, and the page used to print that number. The two stop
   agreeing the moment a placed program is parked: Reorder mode lists only the programs in play,
   so PG-29 waived at 5 left the visible order reading 1 2 3 4 6 7 — "you placed it 8th" on the
   6th row — and a save then numbered the visible rows 1..7 straight over the hidden 7, so when
   PG-08 came back two programs shared a priority nobody chose.

   The truthful model is the one a person holds: an ORDER. The page reads a placement as its
   place among the programs you can order (the stored numbers sorted, parked ones left out), and
   every inherited priority as the place of the program it comes from (`rankRoot`). The store
   keeps a hidden placement's NEIGHBOURS — a save never adds, removes, reorders or restamps a
   placement it did not show (ENG-10692), but renumbers it so it stays directly behind the shown
   program that sat above it before the edit, the whole sequence dense 1..n — so nothing collides
   and a parked program comes back where it was left (`store/tiers.declare`; RK-02 measured the
   number-keeping cut bringing PG-29 back ahead of the neighbour it was parked behind). Dispatch
   compares the stored numbers and only compares them, so the order it keeps and the places this
   page prints are the same order. */
function orderPositions(){
  const at = Object.create(null);
  reorderPlaced().forEach((p, i) => { at[p.id] = i + 1; });
  return at;
}
/* The place a stored number stands for: its program's own place when the payload names the
   program (`rankRoot`), otherwise one after every orderable placement stored ahead of it — the
   only reading of a number whose program is parked or unknown that keeps "lower is sooner". */
function placeOf(n, root){
  if (!n) return 0;
  const at = orderPositions();
  if (root && at[root]) return at[root];
  return 1 + reorderPlaced().filter(p => authoredOf(p) < n).length;
}
/* THE NUMBER A PERSON READS IS A PLACE IN WHAT IS DRAWN. While the resting list renders under the
   priority sort, `VIEW_ORDER` holds the stored numbers of the placed programs the list DRAWS,
   sorted — "hide proven" and every other filter leave placed programs out of it, and counting them
   made "In your order" read 11 over a column that ran to 16. The stored numbers stay the source of
   truth for ORDER; a stored number reads as how many drawn placements sit at or before it. Null
   everywhere else (Reorder mode, which draws the whole order, and the entity pages). */
let VIEW_ORDER = null;
function viewPlace(n){
  return VIEW_ORDER && n ? Math.max(1, VIEW_ORDER.filter(a => a <= n).length) : n;
}
function priorityOf(p){
  if (isParked(p)) return null;
  const mine = VIEW_ORDER ? (isPlaced(p) ? viewPlace(authoredOf(p)) : 0) : orderPositions()[p.id] || 0;
  const own = authoredOf(p);
  const stored = Number(p.rank) || 0;
  const from = p.rankRoot && p.rankRoot !== p.id ? String(p.rankRoot) : "";
  const rank = !stored ? 0 : VIEW_ORDER ? viewPlace(stored) : own && stored >= own ? mine : placeOf(stored, from);
  const raised = rank > 0 && (!mine || rank < mine);
  const root = raised ? from : "";
  return { mine: mine, rank: rank, raised: raised, root: root, via: raised && p.rankFrom ? String(p.rankFrom) : "" };
}
const NOT_IN_ORDER = "not in your order";
const NOT_IN_ORDER_TIP = "You have not placed this program, and nothing in your order waits on it, so it has no priority.";
function priorityWhy(r){
  const what = r.via ? `waits on ${r.via} in this program` : "waits on this program";
  return `${r.root ? `${r.root}, ${ordinal(r.rank)} in your order,` : "A program in your order"} ${what}`;
}
function priorityChip(cls, tip, text){
  return `<span class="chip ${cls}" tabindex="0" data-tip="${esc(tip)}">${text}</span>`;
}
/* `where` is `row`, `head` or `reorder`; `absent` is whether this surface names the absence at
   all (the resting list does only under its priority sort, where the line splits the two halves).
   `soft` is `rankChip`'s: a row is itself a link, so the id it names stays plain text there. */
function programRankChip(p, where, absent){
  const r = priorityOf(p);
  if (!r) return "";
  const needs = r.raised ? `${r.root ? mdown(r.root, where !== "head") : "a program in your order"} needs it` : "";
  const none = absent ? priorityChip("unplaced", NOT_IN_ORDER_TIP, NOT_IN_ORDER) : "";
  if (where === "reorder"){
    return r.raised
      ? priorityChip("rank inh", `${priorityWhy(r)}, so the fleet treats this program as at least as urgent as `
          + `${r.root || "that program"}, wherever you place either of them.`, needs)
      : none;
  }
  if (!r.rank) return none;
  if (!r.raised){
    return priorityChip("rank", `You placed this program ${ordinal(r.mine)} in your order, so the fleet gives `
      + `its work priority ${r.rank}.`, `priority ${r.rank}`);
  }
  const said = [`priority ${r.rank}`].concat(r.mine ? [`you placed it ${ordinal(r.mine)}`] : [], [needs]);
  return priorityChip("rank inh", `${priorityWhy(r)}, so the fleet gives this program priority ${r.rank}. `
    + (r.mine ? `You placed it ${ordinal(r.mine)}.` : "You have not placed it."), said.join(" &middot; "));
}

/* ── THE SAME WORDS ONE AND TWO LEVELS DOWN (ENG-10701, K-09) ───────────────────────────────
   A program read `priority 3 · PG-25 needs it` while its slices read `#3 via SL-190`, its PRDs
   `#3 via SL-131`, a to-do row `#7` with "your authored order" in the tooltip, and the dependency
   map `SL-131 · PG-17 · #3` — one number in two vocabularies, the second naming the resolver's
   path instead of the reason. A slice or a PRD now says it the way its program does:

     * `priority N` — its program's place in your order, when that is where the number comes from;
     * `priority N · PG-25 needs it` — when the number is another program's, through an open need.

   And a FINISHED CUT CARRIES NONE. A slice that is complete, withdrawn, waived or whose ground is
   met has no work left to order (`board.py::_need_met`, the same test the resolver stops at), and
   `#3 via PG-25` on a withdrawn slice claimed an urgency nothing will ever act on. A PRD that has
   shipped or was cancelled is the same absence at the next level down. */
const FINISHED_CUT = ["complete", "withdrawn", "waived"];
function cutFinished(s){ return !s || FINISHED_CUT.includes(s.state) || !!s.groundMet; }
function cutRoot(s){
  if (s.rankRoot) return String(s.rankRoot);
  return s.rankSrc === "program" ? String(s.program || "") : "";
}
/* `what` is "slice" or "PRD"; `s` is the slice (the PRD's own, for a PRD); `n` the stored rank. */
function workRankChip(what, s, n, soft){
  if (!n || cutFinished(s)) return "";
  const root = cutRoot(s);
  const rank = placeOf(n, root);
  const needs = !!root && root !== s.program;
  const via = needs && s.rankSrc === "dependency" && s.rankFrom ? ` (${s.rankFrom} waits on it)` : "";
  const subject = what === "slice" ? "this slice" : `${s.id}, the slice this PRD moves`;
  const tip = needs
    ? `${root}, ${ordinal(rank)} in your order, needs ${subject}${via}, so the fleet gives its work priority ${rank}.`
    : `${s.program} is ${ordinal(rank)} in your order, so the fleet gives this ${what}'s work priority ${rank}.`;
  const text = `priority ${rank}` + (needs ? ` &middot; ${mdown(root, soft)} needs it` : "");
  return priorityChip(needs ? "rank inh" : "rank", tip, text);
}
function sliceRankChip(s, soft){ return workRankChip("slice", s, Number(s && s.rank) || 0, soft); }
function prdRankChip(r, s, soft){
  return !r || TERMINAL.includes(r.status) ? "" : workRankChip("PRD", s, Number(r.rank) || 0, soft);
}
/* A to-do row names an id of any tier; its chip is that entity's own reading. */
function entityRankChip(id){
  if (PG[id]) return programRankChip(PG[id], "head", false);
  if (SL[id]) return sliceRankChip(SL[id]);
  const r = PRD[id];
  return r ? prdRankChip(r, SL[r.slice]) : "";
}
/* The dependency map's node: a link already, so the id is text, and a finished cut says nothing. */
function nodeRank(s, dot){
  const n = Number(s.rank) || 0;
  return !n || cutFinished(s) ? "" : ` ${dot} priority ${placeOf(n, cutRoot(s))}`;
}

/* ── a term, explained where it stands ─────────────────────────────────────── */
/*
 * A WORD THIS BOARD CAN DEFINE CARRIES ITS DEFINITION AS HOVER TEXT. This is what replaced
 * the definitional paragraph that used to sit under half the section headings on this board:
 * a definition written beside a table is a second copy of the register's own sentence, and
 * two copies is exactly the failure the requirement registers exist to prevent. So the word
 * itself carries the definition, everywhere the word appears, and there is one text.
 *
 * IT USED TO BE A LINK TO A GLOSSARY PAGE, AND THE PAGE IS GONE. The corpus's own words (a
 * program, a slice, a capability) are explained on the Knowledge page now, one row per kind out
 * of `KGUIDE`; the deployment's words (box, lane, claim, lease, run) have no page at all and are
 * explained where they are used. A reader who taps a word to learn what it means keeps their
 * place: the definition opens in the shared `#tip` popover — on hover, on keyboard focus, and on
 * a tap — and `showTip` points the word's `aria-describedby` at it while it is open.
 *
 * WHERE THE WORDS COME FROM, in order: `KGUIDE`, the one list the Knowledge page and the Build
 * page read, for a word that names a kind of knowledge; then `GLOSS`, which is the corpus's
 * `specs/glossary.md` plus whatever the host contributes (`/api/glossary` on the deployed app).
 * A term neither knows renders as plain text rather than as a word promising a definition it
 * does not have, so this answers correctly on a corpus with no glossary at all.
 */
/* THE DEFINITION AS ESCAPED PLAIN TEXT, ready for an attribute — or "" when there is none.
   `value` names one member of a closed vocabulary (a liveness state, an eligibility code, a
   dispatch position): its own meaning leads, headed by the words a person saw on the chip
   (`SAYS`), and the term's definition follows. */
function termTip(key, value){
  const guide = KGUIDE_BY[key];
  const t = GLOSS[key];
  const head = guide ? `${esc(guide.nm)}: ${esc(guide.def)}`
    : t ? `${esc(t.term || t.k)}: ${mdText(t.what || "")}` : "";
  if (value == null || value === "") return head;
  const v = t && (t.values || []).find(x => x && x.value === value);
  if (!v) return head;
  const said = v.says ? String(v.says) : SAYS ? String(SAYS(v.value) || "") : "";
  const name = said && said !== v.value ? `${esc(said)} (${esc(v.value)})` : esc(v.value);
  return `${name}: ${mdText(v.meaning || "")}` + (head ? "\n\n" + head : "");
}
function term(key, label){
  const text = esc(label == null ? key : label);
  const tip = termTip(key);
  return tip ? `<span class="term" tabindex="0" data-term="${esc(key)}" data-tip="${tip}" data-tip-lines>${text}</span>` : text;
}
/* THE SAME HOVER TEXT ON A HOST'S OWN ELEMENT — a chip, a mark, a slug — for the places that used
   to be a link into the glossary and are now the definition itself. `o.tip` is what that one
   element says about itself (raw text; escaped here, once), and it leads; `o.value` names the
   member of the term's vocabulary it shows. A term this board cannot define keeps the element's
   own words alone, which is still an element a keyboard can reach. */
function defined(key, cls, inner, attrs, opts){
  const o = opts || {};
  const own = o.tip ? esc(o.tip) : "";
  const def = termTip(key, o.value);
  const tip = [own, def].filter(Boolean).join("\n\n");
  return `<span class="${cls}" tabindex="0" data-term="${esc(key)}"${
    tip ? ` data-tip="${tip}" data-tip-lines` : ""}${attrs || ""}>${inner}</span>`;
}

/* THE ONE BOX A ROW'S RIGHT-HAND CELL DRAWS WHEN THERE IS NO COMMAND TO RUN — and it is the
   host's `.seat`, not a shape of its own (the PG-08 operator report). The operator met the same
   cell in three styles: the host's seat with a Start control and a line of helper prose under it,
   a `.waitbox` with a "Status" caption over a sentence nobody could click, and under that a bare
   "Open ENG-11683" text link. ONE shape now: a `.seat`, whose state line is the status, and when
   the status has somewhere to go the status IS the control — an `.act.card.primary` anchor with
   the seat's own `→` at its far edge, exactly the host's "Answer it". No caption, no second link,
   no sentence explaining the control.

   `go` is a route (`issue:ENG-9`, `prd:0637`) and the row's one control; without it the box is a
   `.seat.grey` stating a fact and carrying nothing to press. `tone` picks the seat's paint by the
   product's four state colours — `call` (brass: a person's move) is the default under a control,
   `grey` the default without one; `work` (in flight) and `warn` (something is wrong) are the
   callers' to name. The `<a>` and not a `<button>` because a destination is a link (ENG-10590):
   middle-click, hover URL and "copy link" all work, and the plain click routes in-page through
   the same `data-go` path every render test reads. */
function waitbox(text, go, tone){
  const said = esc(text || FLEET.wait);
  if (!go) return `<span class="seat ${tone || "grey"}"><span class="st">${said}</span></span>`;
  const paint = tone || "call";
  return `<span class="seat ${paint}">${
    link(go, paint === "call" ? "act card primary" : "act card", `${said} <span class="arw">→</span>`)}</span>`;
}

/* THE THIRD ANSWER IN A COLUMN THAT ONLY HAD TWO — and it is an ERROR, not an answer.

   THIS BOX SAID "Your call — no command settles this; it is a sentence to write into the
   register", on the theory that `actionCommands` is the caller's file, every key in it is
   optional, and a finding with no command behind it is therefore a permanent and legitimate
   state of the payload. That reasoning is sound about this PACKAGE, which ships stdlib-only
   with no guidance at all. It is false about any board that HAS guidance, and that is the only
   kind anybody looks at.

   MEASURED, on the corpus this was written for: 60 findings, and the number carrying no
   command is ZERO. Every `add()` in `board.py` passes one, and the deployment's guidance names
   a template for all nine keys — including `program_bar_author` and `slice_bar_author`, the
   two this box was written for. So the branch could not fire, and the one way to reach it was
   for somebody to DELETE a key. Dressing that as a considered answer is the exact failure the
   old note was trying to avoid, one level up: it does not invent a command, it invents a
   REASON, and a reader who believes it stops looking for the bug.

   A FINDING IS EMITTED BECAUSE SOMETHING HAS TO BE DONE ABOUT IT. A row that states a problem
   and hands over no way to act on it is not a judgement waiting for a sentence — it is a hole
   in the guidance, and the row is unactionable until somebody fills it.

   SO IT NAMES THE KEY (`cmdKey`, carried for this and nothing else) and stops there. Still no
   invented command, which was the old note's real concern and remains right: a plausible verb
   would be typed. This is the one box on the page a reader should never see. */
function nocmdbox(key){
  /* THE SAME `.seat` AS EVERY OTHER ANSWER IN THIS CELL, in the attention paint: the state line
     names the defect, the seat's one sentence line names the key. */
  return `<span class="seat warn"><span class="st">No command</span>
    <span class="meta">This finding names no command, which is a defect &mdash; the board's guidance
    supplies no ${key ? `<code>${esc(key)}</code>` : "key for it"}. Nothing is invented here, so
    the row cannot be acted on until that key is restored.</span></span>`;
}

/* What a HOST may put in place of the "Run this" box, per row. The THIRD extension point in
   this file and it is the same three lines as the other two — this package is the RECORD and
   may not learn that somewhere there is a machine a command could be run on. It knows how to
   SPELL a command; a page with a server behind it can make the same row openable.

   `null` is a real answer and not a failure: it means "the host has nothing to say about this
   row", and the command stays exactly the text below. The standalone board registers nothing,
   so every row there is the text and always was. */
let RUN_ACTION = null;

/* The command with its real argument, so the row is runnable rather than descriptive.
   `built:false` is an affordance whose tool nobody has written yet — shown, never hidden.

   `id` is the row's entity — `PG-19`, `SL-004`, a PRD number, a requirement id — and the KIND
   is resolved here rather than by the host, because `routeOf` is this file's own answer to
   "which register holds this id" and a second derivation of it in a host page is a second thing
   to get wrong. `entityKindOf` reads that answer one level down, because a corpus id's route
   begins with `knowledge` and its register is the kind AFTER it. An id in no register resolves
   to `""`, which is an honest "this row names nothing I know" rather than a guess. */
function runbox(cmd, built, id){
  if (!cmd) return "";
  const plain = `<span class="runbox${built ? "" : " todo"}">
    <span class="lbl">Run this</span><code>${esc(cmd)}</code>
    ${built ? "" : '<span class="nb">command not built yet</span>'}</span>`;
  if (!RUN_ACTION) return plain;
  /* `plain` GOES TO THE HOST rather than being re-spelled there. A host that wanted to add a
     control beside the command would otherwise have to write this markup a second time, and the
     second copy is how the two pages' rows stop looking alike — the same reason there is one
     `board.js` and not two. It composes or it replaces; it never re-renders. */
  /* AND THE ENTITY'S OWN SHAPE FIELDS, off its typed row — the same three `hostAsks` hands a page
     about its own subject, here for a row about ANY entity. `board.py` stamps `shape`,
     `shapeTerminal` and `shapeBuilt` on every program, slice and PRD; a host that meets a row
     whose command is the attended twin of the fleet's shaping command can only tell so by reading
     them, and this file is the one that holds the typed rows. Empty on an id no register holds. */
  const own = PG[id] || SL[id] || PRD[id] || {};
  const swapped = RUN_ACTION({ cmd, built: !!built, id: id || "",
                               kind: entityKindOf(id), plain,
                               shape: own.shape || "", shapeTerminal: own.shapeTerminal || "",
                               shapeBuilt: !!own.shapeBuilt });
  return swapped == null ? plain : swapped;
}

/* WHAT A HOST PUTS AT THE TOP OF AN ENTITY PAGE — the FIFTH extension point, and it is the same
   seam as `runAction` one register over: this package is the RECORD and may not learn what a
   question is, while a host with a fleet behind it is the only half that can say which question
   sets are owed against a program or a slice. The call site is the SECOND one for the card a host
   already renders on an idea's own page — the card itself is the host's and does not change here.

   Called with the page's own identity — `{ kind, id, program, programName }`, where `program` is
   the slice's or PRD's program (its own id on a program page) and `programName` that program's
   authored name (`""` when the register holds none; a slice page's line about its program's
   drive reads it, ENG-10558) — because this file already resolved those registers and a host
   reading them a second time is a second thing to get wrong. A STRING is inserted as-is; `""`,
   `null` and `undefined` all mean "nothing on this page", which is what a host that has not
   answered yet and one with nothing to say both return.

   AND THE SHAPING AFFORDANCE'S INPUTS, off the row itself: `shape` (the headless command the
   page's button hands this entity to), `shapeTerminal` (the attended command offered beside it),
   `shapeBuilt` (whether the fleet's is built), and a PRD's `status` — the one reading a host
   needs to tell a stub from a drafted PRD. All three tiers carry the three shape fields, stamped
   by the generator from the caller's `shape` table and EMPTY when the caller declared none; this
   file forwards them and never derives one. `status` is `""` on a program or a slice, whose
   ship-state is computed and never a field. `slice` is a PRD's slice, `""` on the other two
   pages, for the reason `program` is there: a PRD's questions are owed against the cut it sits
   in and the route carries only its number. The PRD page has this slot too, so a host has one
   seam for all three kinds and the same position on each page — under the header, before
   "To do here". */
let ASKS = null;
function asks(fn){ ASKS = fn || null; }
/* THE HOST'S OWN PAGE FOR A PRD (the New UI draws a PRD as its item page). `fn(ctx)` answers markup, or anything else
   for "not mine", and then `viewPrd` draws as it always has. Never asked while a page is embedded in another. */
let PRD_PAGE = null;
function prdPage(fn){ PRD_PAGE = fn || null; }
function hostedPrd(n){
  if (PRD_PAGE && !EMBEDDING && PRD[n]){
    const r = PRD[n];
    const said = PRD_PAGE({ n: String(n), row: r, slice: SL[r.slice] || null, program: PG[r.program] || null,
      waves: () => prdWavesSection(r) });
    if (typeof said === "string") return said;
  }
  return viewPrd(n);
}

/* WHAT A HOST KNOWS ABOUT AN ENTITY THIS CORPUS DOES NOT HOLD — the EIGHTH extension point, and the
   same shape as `asks` (ENG-10707, I-09). This package is the RECORD, and the served register is all
   it has: an id it does not hold is a mistyped link or a renamed row, and it says so. A host with a
   fleet behind it can know one more thing — that the fleet MERGED the entity a minute ago and the
   next sync serves it — and "renamed or removed" under the ribbon that just announced it is the
   defect. Called with `{ kind, id }` for a program, a slice or a PRD page `viewMissing` is about to
   draw; an answer of `{ title, html }` replaces the sentence (the way back stays), and anything else
   leaves the record's own reading standing. The standalone page registers nothing. */
let MISSING_NOTE = null;
function missingNote(fn){ MISSING_NOTE = fn || null; }

function hostAsks(kind, id, program, row, programName, into){
  if (!ASKS) return "";
  const r = row || {};
  const said = ASKS({ kind: kind, id: id, program: program || "", programName: programName || "",
                      slice: r.slice || "",
                      shape: r.shape || "", shapeTerminal: r.shapeTerminal || "",
                      shapeBuilt: !!r.shapeBuilt, status: r.status || "", ...(r.linkOnly ? { linkOnly: true } : {}) });
  /* A HOST MAY ANSWER WITH MORE THAN THE SLOT'S MARKUP (ENG-10570, U-9): `{ html, next }`, where
     `next` is what the page's own "next step" should read while the host's box is the move —
     a PRD stub with a fleet box saying "Fill this PRD" beside a header saying "run
     `/<ns>:prd:create`" was two commands for one move on one screen. `into`, when the caller
     passes an object, receives it; a string answer is the slot alone, exactly as before. */
  if (said && typeof said === "object"){
    if (into){
      /* AND A SMALL CONTROL FOR THE PAGE'S HEADER: an already-shaped program's "Shape it
         again…" is a secondary move, so it sits beside the header chips rather than in a box of its
         own that says nothing but "shaped". Markup, placed as given; `""` when the host has none. */
      into.head = typeof said.head === "string" ? said.head : "";
      into.next = typeof said.next === "string" ? said.next : "";
      /* AND WHERE THE ISSUE BEHIND THIS ROW STANDS RIGHT NOW (ENG-10589): `{ key, state,
         sentence, go }` off the fleet's own backlog, or nothing. A PRD page rendered "waiting
         for the fleet — nothing for you to do" from the register's status while the Fleet page
         showed the same issue implementing for hours; the register says what was planned, the
         host says what is happening, and the page prefers the host where it has an answer. */
      into.live = said.live && typeof said.live === "object" && said.live.key ? said.live : null;
      /* AND ONE SENTENCE FOR THE STATUS SECTION (ENG-10590): what the fleet is doing with this
         PRD right now, when the host knows a RUN — "is being implemented on <machine>" outranks
         the position word alone. */
      into.status = typeof said.status === "string" ? said.status : "";
      /* AND WHETHER THIS PRD IS A RECORD (ENG-10704, B-01): the shaping route's own refusal for a stub in a cut
         that takes no new work, as the host holds it — one sentence, and then no attended step on this page. */
      into.record = typeof said.record === "string" ? said.record : "";
      /* AND WHETHER THAT STATUS IS A LIVE SHAPING'S (the v0.5.94 audit): while the fleet is filling
         the PRD, the step is not a person's to start, so the page draws no "To do here" row that
         says it waits on them — one state for whose move it is, the host's box. */
      into.shaping = !!said.shaping;
      /* AND WHETHER A RUN IS DOING THE STEP RIGHT NOW (owner, on #prd:0008): its state is the page's Status and its box,
         so a "next step" reading "↑ Being filled" was the same state said again. Then the page draws no next step at all. */
      into.inFlight = !!said.inFlight;
      /* AND THE HOST'S OWN ROWS FOR THE PROGRAM PAGE'S ONE TO-DO LIST (the operator, on PG-36: "Waiting on
         you" and the to-dos were the same thing twice). What the host knows waits on this program — a drive
         the fleet stopped, a finished drive's ship, a driven program's person step, or a close the fleet is
         making itself — arrives as rows of that list, never as a second box above it. `[]` for none. */
      /* AND WHOSE TURN A RUN THE FLEET HOLDS IS (`fleetTurn`): the page's section for its card is not "Waiting on a person" while nobody owes an answer. */
      into.fleetTurn = !!said.fleetTurn;
      into.todo = Array.isArray(said.todo) ? said.todo.filter(r => r && typeof r === "object" && (r.title || Array.isArray(r.replaces))) : [];
    }
    return typeof said.html === "string" ? said.html : "";
  }
  return typeof said === "string" ? said : "";
}

/* QUESTION FIRST, THE ENTITY'S OWN SECTIONS FOLDED BEHIND A DISCLOSURE (ENG-11733).

   When a host supplies a card slot for an entity page, the question a person came to answer is
   the FIRST thing under the header and the entity's own sections — *Where it is*, *Delivery*,
   the to-dos, the slice list — fold into one `Context` disclosure under it. Before this the card
   sat below the entity's own reading: on production's `#program:PG-08` the to-dos began at
   y = 1482px at 390×844, two full phone screens below the header, and the reader's whole errand
   was to answer the card.

   THE RECORD DOES NOT KNOW WHAT A QUESTION IS, so it does not decide whether to draw this: the
   slot's own EMPTINESS does. `""` (the standalone default, and a host with nothing owed) leaves
   the page exactly as it always was — every section where it was — and only a non-empty slot,
   which is a host saying a person has something to answer, folds the rest. The folded markup is
   unchanged, only nested: `test_js_render_section_order` still finds every `.grp` it measures,
   and a section rendered inside an unopened `<details>` is still in the document, which is what
   every other reading of these pages reads. */
/* THE ACT BEFORE THE HEADER ON A PHONE, THE HEADER FIRST ON A DESK (audit 6). At 390px the pinned
   act sat under the entity's header — 1.2 to 1.9 screens down — so a person opening an item from
   "Needs you" scrolled before they could act. The markup keeps the desk order; `fleet.css` turns
   the pair into a column at phone width and lifts the act above the header. No slot, no wrapper:
   the page is exactly as it was. */
function pinFirst(head, pin){
  const act = String(pin || "");
  return act.trim() ? `<div class="pinfirst">${head}<div class="pinfirst-act">${act}</div></div>` : head;
}

function asksFirst(slot, rest, head){
  /* ONLY A REAL QUESTION FOLDS THE REST. The host's slot also carries the shape box and the
     drive line when those are live without a card (ENG-10558 / ENG-10563); those stay above the
     entity's own sections without folding them — a box saying "Start shaping" is not a question
     the reader came to answer, and folding *Where it is* under it would hide the page for nothing. */
  const asks = String(slot || "");
  const question = /qfirst|ib-page-qs|qflow/.test(asks);
  /* A WAITING QUESTION COMES RIGHT AFTER WHAT THE PAGE IS (owner, P0: the ask, its context and its control are on the first
     screen). A PRD's own summary and fact grid are a long paragraph and a table; read first, they put the question a screen
     and a half down. The header is cut after its title row: the title, then the question, then the summary and the facts. */
  const cut = question && typeof head === "string" ? head.indexOf(EHDR_SPLIT) : -1;
  if (cut >= 0){
    /* What follows the cut, without the closing tag of the header it was cut out of. Nothing left (a header with no summary,
       state line or facts) draws no second block: an empty bordered box under the question says nothing. */
    const tail = head.slice(cut + EHDR_SPLIT.length).replace(/<\/div>\s*$/, "");
    const filled = tail.trim() !== "";
    /* ONE RULE, NOT TWO: the title row loses its bottom rule when a second block follows, and that block keeps its own. */
    const lead = (filled ? head.slice(0, cut).replace('<div class="ehdr">', '<div class="ehdr ehdr-lead">') : head.slice(0, cut)) + "</div>";
    const more = filled ? `<div class="ehdr ehdr-more">${tail}</div>` : "";
    return `${pinFirst(lead, asks)}${more}<details class="qctx"><summary class="qctx-s">Context</summary>${rest}</details>`;
  }
  const top = head === undefined ? asks : pinFirst(head, asks);
  return question
    ? `${top}<details class="qctx"><summary class="qctx-s">Context</summary>${rest}</details>`
    : top + rest;
}

/* THE "Drive this program" SECTION, HOST-SWAPPED — the SIXTH extension point and the same three
   lines. `viewProgram` renders one section with the command's own affordance, and this package
   knows how to spell that command but nothing about who is driving it or whether a cycle just
   ran. A host that knows replaces the WHOLE section, because the state line, the command kept
   visible underneath and the control are one composition and splitting it would leave this file
   choosing which half a host may state. `null` (the standalone default, and a host with nothing
   to add) keeps the section exactly as it was: the command and its run affordance.

   Called with `{ id, cmd, built, name, needs }` — the register values this file already holds, never a
   URL, a request shape or a session id. `needs` is how many of this program's moves only a person can
   make (`personsMoves`, the set the page's "Needs you" section lists), so a host saying the fleet drives
   the program can also say it still needs a person rather than contradict that list (ENG-10705, RV-04). */
let DRIVE = null;
function drive(fn){ DRIVE = fn || null; }

function hostDriver(p, cmd, built){
  if (!DRIVE) return "";
  const swapped = DRIVE({ id: p.id, cmd: cmd, built: !!built, name: p.name, needs: personsMoves(p.id).length });
  return typeof swapped === "string" && swapped ? swapped : "";
}

function driverSection(p){
  return hostDriver(p, p.deliver, p.deliverBuilt) ||
    `<section class="grp"><div class="grp-h"><h3>Delivery</h3></div>
      ${entityList([{ id: p.id, title: p.name, sev: 3, badges: [],
        sub: "Starts one session that drives this program and verifies what moves. " +
             "You start it, and when it ends nothing starts it again.",
        right: runbox(p.deliver, p.deliverBuilt, p.id) }])}</section>`;
}

/* WHAT A HOST PUTS ON A PROGRAM'S ROW IN THE LIST — the SEVENTH extension point, and the same
   three lines as the six before it. This package is the RECORD: it knows a program's state, its
   cuts and its proof, and it may not learn that somewhere a fleet's agent has stopped on a
   question about one. A host with a fleet behind it is the only half that can say *"a question
   waits on this program"*, and the Programs list is where a person looks for that (ENG-10618).

   Called per row with `{ kind: "program", id }` — the row's identity and nothing more — at
   RENDER time rather than pushed once, for `badges`' reason: a reading that lands after the list
   painted still reaches the row on the next render. A STRING is inserted among the row's own
   chips, after the fleet's `with …` / `N to do` chip and before `blocks N`; `""`, `null` and
   `undefined` all mean "nothing on this row", which is what a host that has not answered yet
   and one with nothing to say both return. The standalone page registers nothing, so every row
   there is the row it always was. */
let ROW_MARKS = null;
function rowMarks(fn){ ROW_MARKS = fn || null; }

function hostRowMarks(p){
  if (!ROW_MARKS) return "";
  const said = ROW_MARKS({ kind: "program", id: p.id });
  return typeof said === "string" ? said : "";
}

/* HOW MANY QUESTIONS WAIT ON A PROGRAM — the EIGHTH extension point, and the same three lines
   (ENG-10676). `rowMarks` hands this file a STRING to put on a row, and a string is the right
   shape for a chip and the wrong shape for a question the list has to answer for itself: "is
   this program one a person is needed on?" (the `needs you` filter) and "how many programs with
   a question does this view leave out?" (the line the list ends with). Parsing the chip back
   into a number would tie the list to the host's markup; asking a second time, for the number,
   does not. Called with the program's id at render time, for `rowMarks`' reason; answers a
   count, and `0`, `NaN`, `null` and an unregistered host all read as "none waits", which is
   what the standalone page always has. The row's chip is the host's other reading of this same
   per-program figure, so the two agree by construction rather than by care.

   THE MASTHEAD IS NOT A THIRD READING OF IT, and reading it as one was a defect. Its figure is
   every question waiting — the per-program sums PLUS the sets the served register can place
   under no program at all (a question keyed to a slice or a PRD the register no longer holds;
   `api/inbox.py::_waiting` lists them as `unplaced` rather than dropping them, because a
   question nothing can chip is still a question waiting on a person). Nothing this file can
   reach through THIS seam counts those: it asks per program, and they are on none. The total
   has its own seam, one down, for exactly that reason. */
let WAITING = null;
function waiting(fn){ WAITING = fn || null; }

/* WHETHER THE FLEET IS DELIVERING A PROGRAM RIGHT NOW — the ELEVENTH extension point, and the one
   reading every delivery-shaped fact on a program's page and row derives from.

   This file reads the register, and the register cannot know a person pressed Start: measured on
   production's PG-16 while its drive box said "A cycle is running now … Driven by you since 31m
   ago", the page beside it said "Delivery: Idle — Nothing is moving", listed "Start delivery —
   Stalled … Nobody is moving this" as a to-do, and its header chip read "building · idle". Four
   readings of the corpus, each true of the register and false of the program. So the host answers
   ONE word per program — `running` (a cycle is running), `waiting` (the delivery agent asked a
   person and waits), `between` (driven, no cycle running — the fleet starts the next), `stopped` —
   plus how many of the delivery agent's questions are open, and every reading below takes it:
   `stateChip`, `whereItIs`' Delivery and Questions tiles, the stalled row (`asMet`, so the to-do
   list, "needs you" and every count agree) and `needsYou`. Called with the program's id at render
   time for `waiting`'s reason; `null`, `""`, an unregistered host and a word this file does not
   know all read as "nothing to add", which is the standalone page's reading always. */
let DELIVERY = null;
function delivery(fn){ DELIVERY = fn || null; }
/* `waiting-on-you` AND `fleet-then-you` (PROD PG-21) are a driven program whose next step is a person's — now, or
   once the fleet's own work on it lands (`dispatch.drive.reading`). PROD's PG-21 read `between` under a step only a
   person could take, so the chip said "building · driven" and Delivery "The fleet starts the next delivery cycle on
   its own" for a day. The host's word carries the step (`person`) and the program's open bugs and tasks (`work`);
   nothing here re-derives either. */
const DELIVERY_READINGS = ["running", "waiting", "between", "waiting-on-you", "fleet-then-you", "stopped"];
/* THE READINGS UNDER WHICH THE FLEET HOLDS THE DRIVE — a cycle, a question, or between them, a person's step owed or not. */
const DRIVEN_READINGS = ["running", "waiting", "between", "waiting-on-you", "fleet-then-you"];

/* A DRIVE'S SHORT WAIT WORDS, LOWER-CASED FOR A CHIP: the host's `waitingOn` ("Waiting on the live check", "2 questions
   for you"), or the questions count, or — only on a host that sends neither — "waiting on you". */
function waitWords(d){
  const on = String((d && d.waitingOn) || "");
  if (on) return on.charAt(0).toLowerCase() + on.slice(1);
  const q = Number(d && d.questions) || 0;
  return q ? `${q} question${q === 1 ? "" : "s"} for you` : "waiting on you";
}

function deliveryOf(id){
  if (!DELIVERY) return null;
  const said = DELIVERY(String(id || ""));
  if (!said || !DELIVERY_READINGS.includes(said.reading)) return null;
  const q = Number(said.questions);
  return { reading: said.reading, questions: q > 0 ? q : 0,
           person: said.person && typeof said.person === "object" ? said.person : null,
           work: Array.isArray(said.work) ? said.work : [], waitingOn: String(said.waitingOn || "") };
}

/* DRIVEN NOW: a cycle running, a question out, or between cycles — the fleet is moving it. A
   stopped drive is not: the register's own reading stands for it. */
function drivenNow(id){
  const d = deliveryOf(id);
  return !!d && d.reading !== "stopped";
}

/* HAS ANYBODY EVER PRESSED START ON THIS PROGRAM — the row's drive chip. The operator
   read production's PG-30 as driven for a day; nobody had ever started it, and no row on the list
   said so, because a program nobody started reads exactly like one between drives: the register's
   own chip. So every open program row says which of three it is — `driven` (a cycle running, a
   question out, or between cycles), `stopped` (started once, stopped since), `never started`.

   "Never started" is an ANSWER, not an absence: the host says `none` for a program it has read and
   found no drive for (the service's own word, `dispatch.drive.reading`), and `deliveryOf` keeps
   ignoring that word, so every other reading on the page is unchanged. A host that has not read
   yet, a failed read and the standalone page all answer nothing, and the row draws no chip —
   "never started" is never guessed from a missing read. */
function driveChip(p){
  if (!DELIVERY) return "";
  const said = DELIVERY(String(p.id || ""));
  const word = said && typeof said.reading === "string" ? said.reading : "";
  /* A CLOSED PROGRAM (complete, withdrawn, proof waived) says "driven" if it still is — a drive
     left running on a program nobody is building any more is exactly what the reader must see —
     and nothing otherwise: "never started" on a withdrawn row is a to-do that is not one. */
  const closed = p.complete || p.state === "withdrawn" || p.state === "waived";
  /* AND A DRIVE LEFT ON A CLOSED PROGRAM WITH NOTHING LIVE IS INERT, and says so (the operator's
     "say inert"). The host's `inert` (`dispatch.drive.inert`: driven, withdrawn or waived with
     nothing open, nothing running, waiting or carried back) — production's PG-41 (waived) and PG-16
     (withdrawn) read "driven" here with nothing run since they closed. A cycle still carrying an answer
     back is live, reads "driven", and is not inert. */
  if (closed && said && said.inert === true)
    return `<span class="chip drive-inert" tabindex="0" data-tip="This program is closed, so no cycle runs on it and nothing moves it, though its delivery was never stopped. A withdrawn program's delivery is stopped by the fleet's next check.">&#9675; closed, drive inert</span>`;
  if (DRIVEN_READINGS.includes(word))
    return `<span class="chip drive-on" tabindex="0" data-tip="The fleet is delivering this program: somebody pressed Start delivering and nobody has stopped it.">&#9679; driven</span>`;
  if (closed) return "";
  if (word === "stopped")
    return `<span class="chip drive-off" tabindex="0" data-tip="Delivery was started once and is stopped now. Nothing moves this program until somebody starts it again.">&#9632; stopped</span>`;
  if (word === "none")
    return `<span class="chip drive-never" tabindex="0" data-tip="Nobody has ever pressed Start delivering on this program, so the fleet is not moving it.">&#9675; never started</span>`;
  return "";
}

/* A PRD THE FLEET PARKED ON A HUMAN ACTION — the NINTH extension point, `waiting`'s twin (ENG-10704, P-20).
   An `advance` row is the fleet's by construction ("nothing for you to do"), and production's PRD 0608 sat
   under that sentence for a day while its issue waited on a person's action, and nothing said so. This file
   cannot know that — the tracker's position is the host's — so the host answers for a PRD number, or
   nothing, and a parked PRD's row reads as the person's move it is.

   THE ANSWER'S SHAPE, and every field but `key` is optional — this file forwards them and derives none:
     `key`        the issue the fleet parked, `ENG-9`. Required; an answer without it is no answer.
     `go`         the route the status control opens — `issue:ENG-9`, or `prd:0637` when the host would
                  rather land the reader on the record. Absent, the control opens `issue:<key>`.
     `ask`        the action itself, in full, in the run's own words: what the fleet asked a person to
                  do. The row's second line carries it whole (its first sentence visible, the rest on
                  the tooltip, as every `sub` is).
     `asked`      the older field — the ask's first sentence alone. Read when `ask` is absent.
     `askMissing` `true` when the host has read the runs behind the park and none of them wrote down
                  what it asked. Distinct from "not read yet" (both fields absent, this flag unset),
                  which the row says nothing about because the host may still be reading.
     `reason`     NOT PART OF THE ANSWER, and named here only to say so: the app's `parkedFor`
                  no longer sends the backlog's reason for the position ("waiting on a human
                  ACTION"), and a host that still hands one gets it ignored — a reason is why the
                  tracker holds the issue, not what a person has to do about it, and printing it
                  in the ask's place is the defect PG-08 reported. */
let PARKED_ON = null;
function parked(fn){ PARKED_ON = fn || null; }
function parkedOn(n){
  if (!PARKED_ON) return null;
  const said = PARKED_ON(String(n));
  return said && typeof said === "object" && said.key ? said : null;
}
/* WHERE A PRD'S ISSUE STANDS RIGHT NOW, FOR A ROW (ENG-10795) — the TENTH extension point, `parked`'s
   twin one run-state earlier. A slice's "PRDs in this slice" rows read the authored `status:` alone, so
   production's SL-192 rendered all six of its PRDs as `planned` / "Waiting for the fleet to implement"
   while five were being implemented on named boxes and the sixth sat queued behind a dependency, unable
   to be picked. The PRD page already reads the host's overlay (`hostAsks`'s `into.live`, ENG-10589);
   the slice's rows need the same fact per row, so the two pages cannot disagree about one PRD.

   Called with the PRD's number at render time, for `rowMarks`' reason; answers `{ key, state, sentence,
   go, pickable, status }` — the same shape `hostAsks` puts in `into.live`, with two additions the row
   needs and the page header did not: `pickable` (the scheduler's own answer, so a queued-and-unpickable
   row reads as blocked rather than as one more thing in flight) and `status` (the run's own sentence —
   "is being implemented on <machine> right now" — when the host holds a run). `null`, `undefined` and an
   unregistered host all mean "the record's own reading stands", which is what the standalone page always
   says; a row the `parked` seam claims never reaches this one, because a person's move outranks anything
   the fleet is doing. */
let LIVE_ROW = null;
function live(fn){ LIVE_ROW = fn || null; }
function liveRowOf(n){
  if (!LIVE_ROW) return null;
  const said = LIVE_ROW(String(n));
  return said && typeof said === "object" && said.key ? said : null;
}
/* ONE LEAD-IN FOR A PARKED PRD (ENG-10767): the action's issue and the run's own first sentence, the same
   words on every surface that names the park — "To do here", "PRDs in this slice", the Needs-you row. SL-185
   drew two lead-ins for one parked PRD (the issue key on one, the action alone on the other). */
function parkedLeadIn(on){
  /* NOBODY WROTE THE ACTION DOWN (PG-08): the host read the runs and found no ask. Said as
     that, and never dressed as one — the old fallback printed the backlog's REASON ("waiting on a human
     ACTION") in the ask's place, which told a reader what the tracker knew and nothing about what to do. */
  const ask = String(on.ask || on.asked || "").trim().replace(/[.!?]?$/, "");
  if (ask) return `Waiting on a human action — ${on.key}: ${ask}.`;
  if (on.askMissing) return `Parked on an action nobody wrote down — ${on.key}.`;
  /* No ask and no `askMissing`: the host has not read the runs yet, or holds no run at all. The row
     names the park and the issue and stops — it does not guess at the action. */
  return `Waiting on a human action — ${on.key}.`;
}
/* THE STATUS ON A PARKED ROW'S CONTROL — one spelling for the "To do here" list, the program page's rows
   and the slice's "PRDs in this slice" list, so no surface can drift to a second one. */
function parkedStatus(on){ return `Waiting on a person — ${on.key}`; }
/* WHERE THE CONTROL GOES: the host's route when it named one, the issue otherwise. */
function parkedGo(on){ return on.go || "issue:" + on.key; }
/* The row as a person meets it: the fleet's `advance` row for a parked PRD becomes a person's move that names
   the action's issue. Every count and list that reads rows reads them through this, so they agree. */
function asMet(a){
  /* THE STALLED ROW OF A PROGRAM THE FLEET IS DRIVING IS THE FLEET'S. `board.py` stamps
     it off the register ("nothing in flight … Nobody is moving this"); the host knows somebody
     started the drive. It stays on the page for the drive box to read its command (`viewProgram`'s
     `carried`), and leaves every list and count a person reads as theirs to do. */
  if (a && a.group === "stalled" && !a.fleet && drivenNow(a.id)) return { ...a, fleet: true, person: false };
  const on = a && a.fleet ? parkedOn(a.id) : null;
  return on ? { ...a, fleet: false, person: true, cmd: "", parkedKey: String(on.key), parkedGo: parkedGo(on),
                /* THE ACTION ITSELF WHEN THE HOST HAS IT (ENG-10704): the run's own words, so a person on the
                   list knows what to do without opening the PRD. */
                why: parkedLeadIn(on),
                waiting: parkedStatus(on) } : a;
}

function questionsWaiting(p){
  /* THE DELIVERY AGENT'S OWN QUESTION COUNTS WHATEVER THE OTHER READ SAYS: the drive
     reading is re-read on the program's own page and the waiting read on its own pace, and a box
     reading "Waiting on your answer" over a tile reading "None waiting" is the two disagreeing. The
     larger of the two, never a sum: they count the same sets on the program's own key. */
  const d = deliveryOf(p.id);
  const own = d ? d.questions : 0;
  const n = WAITING ? Number(WAITING(p.id)) : 0;
  return Math.max(n > 0 ? n : 0, own);
}

/* EVERY QUESTION WAITING — the TENTH extension point, `waiting`'s denominator, and a correction
   rather than an addition (ENG-10676's reshaping, as reviewed).

   `asksTally` read its total by SUMMING the seam above over every program, and called that "the
   figure the masthead prints". It is not: the masthead prints the document's own `waiting`, which
   is that sum PLUS the sets no program row can carry. So a question keyed to a retired slice —
   a state the server has a name, a branch and a test for — was structurally invisible to a count
   that could only ask per program, and the toolbar read `1 of 1 question` with no `part` under a
   masthead reading 2: the page positively asserting it showed everything while one was missing,
   which is the very defect this whole change exists to end, in its second unit.

   SO THE TOTAL IS ASKED FOR, NEVER DERIVED. The host answers with the figure it prints itself
   (`app.js`: `Board.waitingTotal(waitingCount)` — the same function `asksHtml` calls, off the
   same document as `waiting`), so the marker and this line are one expression and cannot
   disagree by construction — the property `todoTally` has against the tab badge, where `all` and
   `actionTotals().needsHuman` are the identical reduce.

   UNREGISTERED MEANS NO FIGURE AT ALL, never a fallback to the per-program sum. A host that
   answers `waiting` and not this is a host whose masthead this page cannot match, and the whole
   rule here is that a count which might be wrong is not printed: absent is honest, `1 of 1` over
   a masthead saying 2 is not. `0`, `NaN` and a negative all read as "none waits", as they do one
   seam up. */
let WAITING_TOTAL = null;
function waitingTotal(fn){ WAITING_TOTAL = fn || null; }
function questionsTotal(){
  if (!WAITING_TOTAL) return 0;
  const n = Number(WAITING_TOTAL());
  return n > 0 ? n : 0;
}

/* The FOURTH extension point, same three lines, same reason: this package knows how to READ an
   authored program order — `rank`/`rankSrc`/`rankFrom` are already on every program — and it may
   not learn that somewhere a database will write one back. `null` (the standalone default) means
   there is nowhere a drag could report to, which is why `reorderToggle` renders nothing at all
   rather than a button that would do nothing when pressed — the same rule `runbox` keeps for a
   command with nowhere to run.

   Called with TWO ARGUMENTS — the new order, as the full list of PLACED program ids, top to
   bottom, and the SCOPE, every program id the mode listed, placed or not — and NOTHING ELSE: no
   URL, no HTTP method, no request shape. The scope is what makes a save a claim about the rows the
   reader saw rather than about every placement stored: a host sends it so that a placement the
   mode never listed (a parked program's, an orphan's) survives the save (ENG-10692). `fleet-service` is free to
   change any of those three tomorrow and this file would not need to change with them. It returns
   a promise; this file re-renders on either branch so a rejected write never leaves a drag's
   leftover transform or busy state on the page. Called ONCE per Save, never per gesture: the
   mode edits a draft (`RZ_DRAFT`) and this is where the draft goes when the reader presses
   Save order. */
let REORDER = null;
/* Whether the Programs list is in Reorder mode right now. A HOST fact this file owns, not one a
   host sets — `REORDER` says whether the capability EXISTS, this says whether the reader is USING
   it, and the second can only ever be true when the first is: see the guard at the top of
   `viewBoard`. */
let REORDER_MODE = false;
/* `"order"` while the save is in flight, or "" — `PR.busy`'s mirror, kept here rather than
   folded into `REORDER_MODE` because a busy list and an open mode are different facts: the mode
   stays open across a write, and closing it mid-write would strand the promise with nothing left
   to re-render into. */
let REORDER_BUSY = "";
/* The host's own words about why a write failed, or `null`. A message rather than a code: this
   file does not know the shape of the host's error and asks for nothing but a sentence. */
let REORDER_ERR = null;
/* What the live region says right now — entering the mode, moving a card, leaving it. Rendered
   inline as `#rz-live`'s initial text rather than poked at afterwards, because every one of these
   changes is already followed by a full re-render (the mode toggling, a card moving, a write
   settling), and a second write to the DOM node the render just replaced would be racing itself. */
let REORDER_ANNOUNCE = "";
/* WHERE A HOST SAYS WHAT AN ACT DID, or `null`. Called as `NOTIFY(html, tone)` — markup this file
   wrote and escaped, and `"ok"` or `"err"` — once per settled save. A host with a notification
   surface of its own (fleet-service's toasts: every act's result is a toast there) takes the
   save's result off the page; without one, the result is said where it always was — in the bar,
   next to Save, and in the live region on the list. */
let NOTIFY = null;

/* ── the nav's attention badges: the THIRD injected capability, and the same seam ────────────
 *
 * A quiet count on a `.tab`, coloured only when something on it needs a human — and this file
 * may not compute a single one of them. Every number behind a badge is fleet-SERVICE data: the
 * dispatcher's own gates, the workstation's own sessions. `fleet-knowledge` is the record; it
 * ships as a stdlib-only submodule with no server behind it at all, and a corpus payload has no
 * queue and no open terminal to count.
 *
 * SO THE HOST SUPPLIES A FUNCTION, exactly as `reorder` and `runAction` do, and for the same
 * reason `terms` is a function and not a stored array: called at PAINT time rather than pushed
 * once, so a background read landing on a page the reader is not standing on still reaches the
 * tab before they navigate to it. Its answer is `{ [dataGo]: count }` — a plain object keyed by
 * the tab's own `data-go`, absent or zero wherever nothing needs a person. Absent function,
 * absent key and zero all render identically: no badge, no empty slot, no reserved width.
 *
 * `paintBadges` is exported on its own, not folded into `badges`, because the count can move
 * with NO route change at all — a poll landing while the reader sits on an unrelated page — and
 * the host has to be able to say "repaint the nav" without pretending a navigation happened.
 */
let BADGES_EXTRA = null;

/* THE VISIBLE LABEL, WITH THE BADGE ITSELF EXCLUDED. A badge is a child ELEMENT appended to
   the `.tab` button, and `textContent` walks every descendant — so reading it back after the
   first paint would fold the digits into the very sentence meant to explain them, and the
   mobile sheet's "where am I" row (`paintNav`, below) would say "Queue3" once a count landed.
   Read off the TEXT NODES only, never memoised: `app.js` rewrites the Programs tab's own text
   once, after its corpus payload names an intent title, and a cached first reading would go on
   repeating whatever was there before that rewrite — "Programs" — forever after. Skipping the
   one child that is not a text node costs nothing a cache would have saved, and it can never be
   stale, because there is nothing left standing between it and the DOM. */
function tabLabel(t){
  let label = "";
  t.childNodes.forEach(node => { if (node.nodeType === 3) label += node.textContent; });
  return label.trim();
}

/* Register the host's counter and paint immediately — a host that calls this after the first
   route has already rendered must not wait for a second navigation to see it take effect. */
function badges(fn){ BADGES_EXTRA = fn || null; paintBadges(); }

/* THE REPAINT ITSELF, over every `.tab` there is, called from `render` on every navigation and
   exported so a host can call it again whenever ITS OWN data changes with no navigation at all.
   `n === 0` and "the key is missing" are one answer, never two: a host that omits a quiet tab
   from its object gets exactly the silence it would get by naming it at zero. */
function paintBadges(){
  const counts = BADGES_EXTRA ? (BADGES_EXTRA() || {}) : {};
  document.querySelectorAll(".tab").forEach(t => {
    const n = Number(counts[t.dataset.go]) || 0;
    let chip = t.querySelector(".tbadge");
    if (n > 0){
      // CAPTURED HERE, NOT UNCONDITIONALLY ABOVE. `app.js` rewrites the Programs tab's own
      // text once, after its own corpus payload names an intent title — a plain `.textContent`
      // assignment on `board`'s tab, made before this ever has anything to badge (the figure
      // it would draw needs the very same payload, so it cannot arrive first). Memoising on
      // every call regardless of `n` would grab whatever text happened to be there on the
      // FIRST paint — before boot, always "Programs" — and go on repeating it forever even
      // after the real title replaced it. Reading it only the moment a badge is actually
      // drawn means the rewrite has already happened by the only time this can be wrong.
      const label = tabLabel(t);
      if (!chip){
        chip = document.createElement("span");
        chip.className = "tbadge";
        // DECORATION, NOT A SECOND ANNOUNCEMENT. The count reaches a screen reader through the
        // tab's own `aria-label` below, in a full sentence — "Queue, 3 need you" — so the digit
        // alone, hidden here, is never read out a second time with no sentence around it.
        chip.setAttribute("aria-hidden", "true");
        t.appendChild(chip);
      }
      chip.textContent = String(n);
      t.setAttribute("aria-label", `${label}, ${n} need${n === 1 ? "s" : ""} you`);
    } else {
      if (chip) chip.remove();
      // REMOVED, NOT EMPTIED. An `aria-label=""` overrides the element's own text for assistive
      // tech (the accessible name computes to nothing), where removing it falls straight back to
      // the plain label every reader already gets — the honest "nothing to say" this whole
      // feature is built around.
      t.removeAttribute("aria-label");
    }
  });
}

/* `conceptPanel` STOOD HERE. It rendered the corpus's own glossary row for a program, a slice
   or a PRD into the `i` panel on that entity's page — and the `i` came off every page on the
   operator's word. The definition itself did not go anywhere: it is `specs/glossary.md`'s row,
   and it is the hover text on the word wherever the word appears (`term()`). */

/* ONE header for every entity: breadcrumb, id, name, state, facts. */
/* WHERE A HEADER MAY BE CUT IN TWO (`asksFirst`): what the entity is (crumbs, id, title, badges) above, what it says about
   itself (the promise, the one-line state, the fact grid) below. An HTML comment, so a page that never cuts it is unchanged. */
const EHDR_SPLIT = "<!--ehdr-split-->";
/* STEP 4 (FLT-1282): IN A REPOSITORY THAT PLANS BY AREA a program finishes the slices it has and takes no new one.
   The board writes `closedToNewWork`; the header says it as ONE CHIP and nothing longer (a header holds chips and state, never prose, owner
   call). The explanation is the chip's hover text, and the Overview's "New work" row says it once in a line. `""` everywhere else,
   so a repository that has not opted in sees today's page unchanged. Said as a feature, never an area, and never a config file. */
const CLOSED_TO_NEW_WORK_TIP = "Finishes the slices it has; new work goes to a feature.";
function closedToNewWorkChip(p, cls){
  if (!p || !p.closedToNewWork) return "";
  return `<span class="${cls || "chip"}" title="${esc(CLOSED_TO_NEW_WORK_TIP)}">Closed to new work</span>`;
}

function entityHeader({ crumbs, id, name, chips, promise, promiseNote, facts, line }){
  /* A PAGE MAY DROP THE CRUMB ROW, THE FACT GRID OR BOTH (the program page does): an empty list draws
     nothing, and every other caller passes both and reads as before. `line` is one quiet sentence of
     state under the title, for the page that replaced the fact grid with it. */
  return `${crumbs.length ? `<nav class="crumbs">${crumbs.map((c, i) =>
      `${i ? '<span class="sep">&rsaquo;</span>' : ""}${c.go
        ? link(c.go, "lnk", esc(c.label))
        : `<span class="here">${esc(c.label)}</span>`}`).join("")}</nav>` : ""}
    <div class="ehdr">
      <div class="etop"><span class="eid-lg">${esc(id)}</span>
        <h2>${esc(name)}</h2>
        <span class="ebadges">${chips.join("")}</span></div>${EHDR_SPLIT}
      ${promise ? `<p class="promise">${mdown(promise)}</p>`
        : promiseNote ? `<p class="promise nodesc">${esc(promiseNote)}</p>` : ""}
      ${line ? `<p class="ehline">${line}</p>` : ""}
      ${facts.length ? `<div class="kv">${facts.map(([k, v]) =>
        `<div><span>${esc(k)}</span><b>${v}</b></div>`).join("")}</div>` : ""}
    </div>`;
}

/* ONE list everywhere: a two-line row — id, title, rank chip, badges, then the first sentence
   of the promise. The full text rides a body-level tooltip, so a long one is never clipped by
   the table's own overflow. Titles navigate; there is no separate "Open" button anywhere. */
function entityList(items, opts = {}){
  if (!items.length) return `<p class="empty-note">${esc(opts.empty || "Nothing here.")}</p>`;
  const hasRight = items.some(i => i.right);
  /* COLUMNS, WHEN THE CALLER SAYS SO (the program's Slices list): progress and chips each get a cell of
     their own instead of trailing the title on one wrapping line, so every row's chips and bar start
     at the same x. Every other list keeps the one-line shape. */
  const cols = items.some(i => i.progress !== undefined);
  const more = extra => extra.length
    ? `<span class="chip more" data-tip="${esc(extra.map(b => b.replace(/<[^>]+>/g, "").trim()).join("  ·  "))}"
                tabindex="0">+${extra.length}</span>` : "";
  const name = i => i.go
    ? link(i.go, "lt-nm lnk", esc(i.title))
    : `<span class="lt-nm">${esc(i.title)}</span>`;
  return `<div class="box"><table class="ltab tp">${items.map(i => {
    /* A TO-DO ROW SAYS ITS WHOLE REASON (`whole`): the program page's one list replaced the "Waiting on you"
       card, which printed the move's reason in full, so the row may not cut it to its first sentence. */
    const full = i.sub || "", brief = i.whole ? String(full).trim() : firstSentence(full);
    const extra = (i.badges || []).slice(3);
    return `<tr class="s${i.sev || 3}">
      <td class="lt-id">${i.num ? `<span class="lt-num">${esc(i.num)}</span>` : ""}${
        /* A SPACE, IN THE TEXT ITSELF (prod v0.5.98): `.lt-num`'s `margin-right` puts a visible
           gap between the rank and the id on screen, but the DOM text is the two runs back to
           back — "1" then "SL-233" — so a reader who copies the row or has it read aloud gets
           "1SL-233" and "10727", a rank glued to an id that reads as neither. The margin already
           does the visual work; this is the one character that makes the TEXT correct too. */
        i.num && i.id ? " " : ""}${i.id ? badge(i.id, "", i.id) : ""}</td>
      <td class="lt-main">
        <div class="lt-l1">${name(i)}${i.who || ""}${cols ? "" : (i.chip !== undefined ? i.chip : rankChip(i.rank, i.rankSrc, i.rankFrom))}${i.rail || ""}
          ${cols ? "" : (i.badges || []).slice(0, 3).join("") + more(extra)}</div>
        ${brief || i.lead ? `<div class="lt-l2${i.whole ? " whole" : ""}" data-tip="${mdText(full)}" tabindex="0">${
          i.lead ? `<span class="lt-lead">${esc(i.lead)}</span>${brief ? " &middot; " : ""}` : ""}${
          i.subLabel ? `<b>${esc(i.subLabel)}</b>` : ""}${brief ? mdown(mdTrim(brief)) : ""}</div>` : ""}</td>
      ${cols ? `<td class="lt-pg">${i.progress || ""}</td><td class="lt-ch">${
        i.chip !== undefined ? i.chip : rankChip(i.rank, i.rankSrc, i.rankFrom)}${(i.badges || []).join("")}</td>` : ""}
      ${hasRight ? `<td class="lt-rt">${i.right || ""}</td>` : ""}</tr>`;
  }).join("")}</table></div>`;
}

/* ONE SECTION, SPELLED ONCE — the `<section class="grp">` heading block sixteen call sites in
   this file already write out by hand, with the same three classes and the same order.

   IT IS NOT A NEW COMPONENT AND THERE IS NO NEW CSS: `.grp`, `.grp-h`, `.grp-h h3`, `.grp-h .n`
   and `.grp-b` are exactly what those sixteen emit, and this returns the same markup they do.
   The knowledge views below write eleven more of them — four tab sections, a call to action, a
   stated refusal and one per relation — and eleven more hand-copies of a four-line block is how
   the seventeenth comes out subtly different. The existing sites are deliberately left alone:
   this change is about the corpus, not about rewriting the board around a helper. */
/* THE BLURB GOES THROUGH `mdown`, NEVER RAW (ENG-10599, P2-10): a relation group's note is the
   server's own prose (`knowledge.RELATION_NOTES`), written with code spans — "This journey's
   `covers:`, unioned with the map's `Tested by`." — and `esc` printed the backticks as
   characters on the journey page. `mdown` escapes first and reads the marks second, as every
   other corpus sentence on this page does. */
function grp(title, n, blurb, body){
  return `<section class="grp"><div class="grp-h"><h3>${esc(title)}</h3>${
    n == null ? "" : `<span class="n">${esc(n)}</span>`}</div>${
    blurb ? `<p class="grp-b">${mdown(blurb)}</p>` : ""}${body}</section>`;
}

/* A TO-DO IS TITLED BY ITS MOVE: "Name the proof", "Refine SL-175", "Close the program" —
   `board.py` stamps `action` on every row. The entity's name moves to the second line, ahead of the
   reason, and the id badge and the link stay. A row from a producer that stamps no `action` (a
   knowledge finding, an older payload) keeps its title and reads exactly as it did. */
function actionItems(list){
  return list.map(a => ({ id: a.id, title: a.action || a.title,
    lead: a.sliceLead || (a.action && a.action !== a.title ? a.title : ""),
    sub: a.why, sev: a.sev,
    go: routeOf(a.id), rank: a.rank, rankSrc: a.rankSrc, rankFrom: a.rankFrom, chip: entityRankChip(a.id),
    badges: [],
    /* ONE BOX, FOUR ANSWERS (PG-08): a parked row's status is its control and opens the
       park — no second "Open ENG-…" link under it; the fleet's row states its wait and carries
       nothing to press; a command is the host's seat or the record's "Run this"; a move no command
       makes (a drill, ENG-10704 X18) states what it is; and a row with no command at all is the
       defect it is. */
    right: a.parkedKey ? waitbox(a.waiting, a.parkedGo || "issue:" + a.parkedKey)
         : a.fleet ? waitbox(a.waiting)
         : a.cmd ? runbox(a.cmd, a.built, a.id)
         : a.waiting ? waitbox(a.waiting)
         : nocmdbox(a.cmdKey) }));
}

/* `cmdBox` STOOD HERE — the collapsed "What you can run here" at the foot of a view. The
   operator asked it off the What-to-do-next page first and then off ALL of them, and its last
   four callers (Programs, and the program, slice and PRD pages) went with it.

   WHAT LEFT WITH IT AND WHAT DID NOT, measured on the deployed corpus rather than argued.
   Every command any of those boxes listed — 21 across six views — is already a row on the
   COMMANDS page, with what it acts on, when to reach for it and how it is reached. So no
   command left the product.

   THE ONE THING THAT DID IS THE PIPELINE STRIP: `pipe` and `pipeLabel` ("A PRD's path"),
   rendered under the slice page's box alone, which put five commands in ORDER behind an arrow.
   Its five members are all in the catalogue too, so what is gone is the ordering claim rather
   than any of the commands — and the catalogue is a table, which has no order to state one in.
   Both keys are untouched on the wire and `test_board.py` still holds the payload to carrying
   them, so restoring the strip is a rendering decision and not a data one.

   `runbox` and `waitbox` are NOT this and did not go: those are the per-ROW affordance — the
   command that settles the finding on the row it sits on — and every action list still carries
   them. */

/* ── the page head ───────────────────────────────────────────────────────── */
/*
 * THE `i` CONTROL IS GONE, and with it the panel it disclosed. It sat in the top-right corner
 * of every page — in the mast's `#headslot` where the shell offered one, inline otherwise —
 * and the operator asked for it off every page.
 *
 * `about` IS GONE TOO, and every call site with it. `pageHead` kept the parameter for a while
 * after the panel that read it disappeared, on the theory that the prose behind it was each
 * view's own considered explanation of itself and dropping it would rewrite forty call sites in
 * one removal pass — so it sat there, computed and discarded, on every single render. Fifteen
 * of those explanations, one per view, never reached a reader for as long as the parameter went
 * unread, which is the operator's standing rule in its purest form: a box explaining the UX is
 * bad UX, and an explanation nobody can even see is not a milder version of that, it is the
 * same defect with better cover. The forty call sites got rewritten anyway.
 *
 * THE TITLE IS NOT ON THE PAGE. The mast's nav names every page and marks the one you are on,
 * so a headline repeating it under the nav was a second answer to "where am I". The title
 * keeps its one remaining reader — the browser tab, which this tells directly. A page that
 * failed to load still says why ON the page, in its `lede`.
 */
function pageHead(title, lede){
  /* A PAGE DRAWN INSIDE ANOTHER (`embed`) owns neither the tab's title nor the shell's slot: the
     page around it does. */
  if (!EMBEDDING){
    document.title = title;
    /* The shell's slot is emptied rather than left alone: a host that painted a control into it
       before this change must not be left showing a stale one. */
    const slot = document.getElementById("headslot");
    if (slot) slot.innerHTML = "";
  }
  return lede ? `<p class="lede">${lede}</p>` : "";
}

/* SET WHILE `embed` DRAWS A PAGE INSIDE ANOTHER ONE — read by `pageHead` alone. */
let EMBEDDING = false;

/* WHICH LAYOUT IS LIVE, ASKED OF THE STYLESHEET. `fleet.css` sets `--sheet:1` inside its one
   media query, so the breakpoint is written once, in the file that owns it. A `matchMedia`
   here would be a second copy of `40rem` that nothing keeps in step — and the two disagreeing
   is invisible until the nav lands in the wrong state on one screen width. */
function sheetMode(){
  return getComputedStyle(document.documentElement).getPropertyValue("--sheet").trim() === "1";
}

/* ── the nav, where eight destinations do not fit across one head ───────────
 *
 * Below the stylesheet's one breakpoint the tab row collapses into a single control whose
 * LABEL IS THE PAGE YOU ARE ON, so the masthead still answers "where am I" without being
 * opened. Tapping it drops every destination in register order: nothing off-screen, nothing
 * to swipe for. A row that scrolls sideways was the alternative and it is worse — eight tabs
 * are some 880px of strip, so three of them are never on screen and nothing says they exist.
 *
 * A PATTERN THIS FILE ALREADY HAS, not a new one: `aria-expanded` on a button, the panel
 * after it in the DOM, `hidden` toggled, Escape closing it and handing focus back. The
 * Sort/Filter dropdowns are the other use of it.
 *
 * BUILT HERE RATHER THAN IN EITHER PAGE'S MARKUP. Two pages carry this masthead and their tab
 * lists differ — six destinations on the standalone board, eight in the deployed app — so a
 * hand-written button in each file would be two copies of one control, which is the drift the
 * whole shared-file arrangement exists to prevent. The renderer that owns the nav owns the
 * control over it.
 */
const NAV_ID = "pagenav";
let navOpen = false;

/* The label is read off the tab the router already marked current, so "where am I" has ONE
   answer and this control cannot come to disagree with the rail in the open list.

   `tabLabel`, NEVER `.textContent` — a badged tab carries a `.tbadge` child, and `textContent`
   walks every descendant. Reading it raw would fold the count into this sentence the moment one
   landed, and the collapsed sheet would announce "Queue3" as the page you are on. */
function paintNav(focusTrigger){
  const btn = document.querySelector("[data-nav]");
  const nav = document.getElementById(NAV_ID);
  if (!btn || !nav) return;
  const here = document.querySelector('.tab[aria-current="true"]');
  if (here) btn.querySelector(".navb-here").textContent = tabLabel(here);
  /* THE WIDE LAYOUT HAS NO DISCLOSURE, so the nav must never be left `hidden` there. `.tabs`
     sets a display and so beats `[hidden]`'s UA rule: the row would be on screen AND out of
     the accessibility tree, which is the worst of both. Opening the sheet and then widening
     the window is the path that gets you there. */
  const sheet = sheetMode();
  if (!sheet) navOpen = false;
  btn.setAttribute("aria-expanded", String(navOpen));
  btn.querySelector(".car").textContent = navOpen ? "\u25B4" : "\u25BE";
  nav.hidden = sheet && !navOpen;
  if (!navOpen && focusTrigger) btn.focus();
}

function initNav(){
  const mast = document.querySelector(".mast");
  /* A HOST THAT DRAWS ITS OWN PHONE NAV SAYS SO ON THE MAST (`data-own-nav`): the deployed shell's
     sidebar and tab bar replaced this disclosure there, and a second one would fold a nav the
     reader already has. The standalone board carries no marker and keeps the disclosure. */
  if (mast && mast.hasAttribute("data-own-nav")) return;
  const nav = mast && mast.querySelector("nav.tabs");
  const h1 = mast && mast.querySelector("h1");
  if (!mast || !nav || !h1 || document.querySelector("[data-nav]")) return;
  nav.id = NAV_ID;
  /* USE THE ROW THAT IS ALREADY THERE. The two pages do not agree about this: the deployed
     shell puts its title in a flex row beside a provenance control, and the standalone board
     has the title as a bare child of the masthead. Wrapping the first would nest a row inside
     a row and strand that control outside it — so the class is ADDED to whatever already
     holds the title, and a row is created only where there is none. */
  let row = h1.parentElement;
  if (!row || row.classList.contains("wrap") || row.classList.contains("mast")){
    row = document.createElement("div");
    h1.parentNode.insertBefore(row, h1);
    row.appendChild(h1);
  }
  row.classList.add("mast-row");
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "navb";
  btn.setAttribute("data-nav", "");
  btn.setAttribute("aria-controls", NAV_ID);
  btn.innerHTML = '<span class="navb-here"></span><span class="car"></span>';
  /* Straight after the title, so the row reads title, then where you are, then whatever
     chrome the host put beside it — and the nav it discloses still follows it in the DOM. */
  h1.insertAdjacentElement("afterend", btn);
  paintNav(false);
}
window.addEventListener("resize", () => paintNav(false));

/* ── 1. Programs, with a quiet toolbar ───────────────────────────────────── */

/* THE BLOCK THAT STOOD HERE READ AN ORDER NOBODY COULD EDIT, AND IT IS GONE — and the flat,
   cross-program "what to do next" view that stood here after it is gone too, folded into this
   one. `viewNext` grouped every finding by category, across every program at once, because that
   was the only place a finding lived: a program page showed nothing behind it. Now every finding
   already lives behind the program that owns it (`viewProgram`'s "To do here"), so the aggregate
   half of what `viewNext` gave a reader — how much needs a person, how much the fleet already
   has, how much cannot even be acted on yet — is `actionTotals` below, folded into this page's
   own strip, and the per-finding half is the drill-in. Nothing here reads `D.priority` any more
   either: the authored order moved into the fleet's own database when the Priorities page was
   built, and what that did to this board is on every rank chip and, now, on the Reorder mode
   above. */

/* THE BOARD-LEVEL COUNTS `viewNext` USED TO OPEN WITH. Only the findings a reader would actually
   see behind a drill-in are counted — the same `D.groups` guard that view kept, so a finding
   whose group this build carries no title for cannot inflate a number nothing under it explains. */
function actionTotals(){
  // A HOST MAY ASK BEFORE THE PAYLOAD ARRIVES — `paintBadges` runs on EVERY render, which
  // includes the very first one, before `boot` ever lands — and a corpus that never loads at
  // all still has a nav to paint. `D.actions`/`D.groups` missing is the SAME "nothing to
  // report" as `D` being null outright, not a second case: `Array.isArray` rather than a
  // second null check, so a payload that carries every OTHER field this file reads (a stub
  // built for a page that has nothing to do with Programs) degrades to zero rather than
  // throwing out of a render nobody asked this function to join.
  const actions = Array.isArray(D && D.actions) ? D.actions : [];
  const groups = Array.isArray(D && D.groups) ? D.groups : [];
  const listed = actions.filter(a => groups.some(g => g.key === a.group));
  const mine = listed.filter(a => !a.fleet);
  return {
    mine: mine.length,
    finish: mine.filter(a => a.group === "finish").length,
    unbuilt: mine.filter(a => !a.built).length,
    // THE PROGRAMS NAV BADGE'S WHOLE SOURCE. `advance` never reaches it, because it is
    // `{actor}`'s own row and never a person's.
    /* ONE COUNT (ENG-10704, P-07): the "What to do next" badge is the sum of every program's "N to do"
       (`todoCount`), so the chips on the list the tab opens, the parked folds included, add up to it.
       THE ADVISORIES COUNT (the program lifecycle): `hygiene` — no proof named, no bar
       written — used to be left out of both as a judgement rather than a to-do, and production's PG-08
       carried a yellow "no proof named" line under a row with no to-do on it. The operator's rule since:
       a thing a person must settle is a to-do with a command, or it is not shown at all. */
    needsHuman: D && Array.isArray(D.programs) ? D.programs.reduce((n, p) => n + todoCount(p.id), 0) : 0,
  };
}

/* ── 2. Programs, with a quiet toolbar ───────────────────────────────────── */

let sortKey = store.get(prefKey("zb.sort"), "priority");
let filters = new Set((store.get(prefKey("zb.filters"), "hideComplete") || "").split(",").filter(Boolean));
let openDD = null;
const SORTS = [["priority", "your priority order"], ["attention", "most open actions"], ["blocking", "blocks the most"],
               ["live", "live work"], ["id", "id"]];
/* `needs you` LEADS THE MENU (ENG-10676): the one narrowing a reader reaches for after the
   masthead says a program is waiting on them, and the one that answers "which rows are mine?"
   Its key is spelled the way a person types it into a link. */
const FILTERS = [["needs-you", "needs you"], ["hideComplete", "hide proven"], ["stalled", "stalled only"],
                 ["noProof", "no proof named"], ["hasLive", "has live work"]];
const NEEDS_YOU = "needs-you";
/* MY PROGRAMS (PRD 0839): ONE control narrows the list to the programs the signed-in person is
   responsible for. The list OPENS ON EVERY PROGRAM — the narrowing is opt-in (it used to be seeded
   ON, and a fresh visit read "1 of 26" with the rest of the fleet's programs out of sight). It is
   DELIBERATELY NOT a member of `filters`: that set is the reader's PERSISTED preference
   (`zb.filters`), and the PRD puts a persisted per-person filter out of scope. So `mine` lives in
   its own module state, seeded OFF, carried only in the route (`mine=1` when on; a legacy `mine=0`
   link still reads as off), and re-seeded on a corpus switch like the rest of the page's per-visit
   state. Nothing was ever stored, so there is no saved "mine" to migrate. It is INERT when the viewer is
   unknown (a laptop stack, a port-forward): a deployment that cannot say who is reading shows every
   program rather than emptying the board. */
const MINE = "mine";
let mineOn = false;
/* THE NEW UI'S FILTER BAR adds three per-visit narrowings beside it, all NEVER persisted: the
   search text over id and name (`pgQ`), a single-choice "Assigned" (`whoSel`: "" = anyone, "none" = nobody, or an owner's
   email; "me" is `mineOn` itself so `mine=1` links keep their meaning), and the dimension whose checklist is open. */
let pgQ = "";
let whoSel = "";
let pgOpen = null;
let pgFm = null;
/* The "Assigned" value a count asks about while it is counted (`drawnWho`); undefined otherwise. */
let WHO_OVR;

/* THE SORT AND THE FILTERS ARE ROUTE STATE (ENG-10599, P2-9). The hash stayed `#board` after
   toggling "hide proven", so a shared link lost the view — the state lived in the reader's
   browser (`zb.sort` / `zb.filters`) and nowhere a link could carry it. A toggle is a
   navigation now, on the Runs and Queue pages' rule ("the query is the route"):
   `#board:sort=attention&filter=stalled,noProof`; `filter=none` is the empty set, which is a
   choice and not an absence. The DEFAULT state — the reader's own saved preference — is
   written OUT of the route, so a plain `#board` is what a reader who never touched a control
   still gets, and a route arriving WITH a query sets the state it names and saves it, so the
   choice a link carried in outlives the page as one made here would. */
const BOARD_ROUTE = "board";
function boardQuery(arg){
  const q = {};
  String(arg || "").split("&").filter(Boolean).forEach(part => {
    const at = part.indexOf("=");
    if (at < 0) return;
    q[decodeURIComponent(part.slice(0, at))] = decodeURIComponent(part.slice(at + 1));
  });
  return q;
}
/* THE ROUTE THE READER'S OWN VIEW IS AT — the sort and the filter set, so a toggle is a
   navigation and a shared link carries the view. It used to take the filter set as a PARAMETER,
   for one caller: the line under a list that left a questioned row out linked `needs you` while
   keeping the reader's sort (ENG-10676). That line is gone — the count carries its own shape now,
   see `todoCount`'s standing rule — and with it the only reason this function ever had to write a
   route for a view nobody was looking at. */
function boardRoute(){
  const parts = [];
  if (sortKey !== "priority") parts.push("sort=" + encodeURIComponent(sortKey));
  const chosen = FILTERS.map(f => f[0]).filter(k => filters.has(k)).join(",");
  if (chosen !== "hideComplete") parts.push("filter=" + (chosen || "none"));
  /* THE NARROWING IS CARRIED ONLY IN THE ROUTE (PRD 0839): its DEFAULT is OFF, so only the narrowed
     state is written — a plain `#board` is every program. Only when a viewer is known: with none the
     filter does nothing, and a `mine=1` in a shared link would name a choice that narrows nothing. */
  if (RZ_VIEWER && mineOn) parts.push("mine=1");
  else if (whoSel) parts.push("who=" + encodeURIComponent(whoSel));
  return BOARD_ROUTE + (parts.length ? ":" + parts.join("&") : "");
}
/* WHAT A ROUTE'S QUERY SAYS, APPLIED — called by the router before the list paints. No query
   leaves the saved preference alone; a query names the sort, the filters, or both. */
function boardArrive(arg){
  if (arg === undefined || arg === "") return;
  const q = boardQuery(arg);
  if (q.sort !== undefined && SORTS.some(sk => sk[0] === q.sort)){
    sortKey = q.sort; store.set(prefKey("zb.sort"), sortKey);
  }
  if (q.filter !== undefined){
    const known = new Set(FILTERS.map(f => f[0]));
    filters = new Set(q.filter === "none" ? [] : q.filter.split(",").filter(k => known.has(k)));
    store.set(prefKey("zb.filters"), [...filters].join(","));
  }
  /* THE NARROWING IS NEVER PERSISTED (PRD 0839): a route that names it sets THIS visit's state and
     writes nothing to `zb.filters` — clearing it is a per-visit look at every program. */
  if (q.mine !== undefined) mineOn = q.mine === "1";
  if (q.who !== undefined) whoSel = q.who;
}
/* EVERY action tied to this entity, whether or not it needs a person — the set `viewProgram`'s
   drill-in shows in full. */
const entityActions = id => D.actions.map(asMet).filter(a => a.id === id ||
  (PG[id] && PG[id].sl.some(s => s.id === a.id || (s.prds || []).some(r => r.n === a.id))));
/* EVERY MOVE A PERSON OWES, ACROSS EVERY PROGRAM — the host's one list of what waits on a person
   ("Needs you") reads the plan's half of it here rather than re-deriving it from `D.actions`: the rows
   `asMet` hands a person (so a stalled row the fleet is driving is not among them), in a group this
   build titles (`actionTotals`' guard), that ONLY a person makes (`person`) — closing, naming a proof,
   running a drill — plus the one ordinary to-do that is a person's start rather than a command's: a
   program nobody is driving (`stalled`). A parked PRD's row is left out: its issue is the host's own
   row, and one thing waiting must not be listed twice. `[]` before the payload lands. */
function personMoves(){
  const actions = Array.isArray(D && D.actions) ? D.actions : [];
  const groups = Array.isArray(D && D.groups) ? D.groups : [];
  return actions.map(asMet).filter(a => groups.some(g => g.key === a.group) && !a.parkedKey
    && personOwes(a, programIdOf(a.id)) && (a.person || a.group === "stalled"));
}
/* A PROGRAM'S SLICES AS THEIR STATES, for the host's "Move a program" card: the program `id` is — or
   the one whose slices hold it, when it is a slice or a PRD (`personMoves`' own reach) — its name,
   and each served slice's state token, in the register's order. `null` when the served register
   names no such program; nothing is counted that the payload does not state. */
function programBar(id){
  const own = PG[id] || Object.values(PG).find(p => (p.sl || []).some(s => s.id === id || (s.prds || []).some(r => r.n === id)));
  if (!own) return null;
  return { id: String(own.id), name: String(own.name || ""), states: (own.sl || []).map(s => String(s.state || "")) };
}
/* THE DAY A PROGRAM'S CLOSING CHECK PASSED, or `""` — the `closed` the host joins onto the payload's program rows
   from its own record of the check (this file never derives it), so a host page decides "the fleet closed this"
   without waiting on a drive. */
function programClosed(id){
  const own = PG[String(id || "")];
  return own && own.closed ? String(own.closed) : "";
}
/* THE MOVES ONLY A PERSON CAN MAKE ON THIS PROGRAM (V-01 of #589's verification). `planning` rows are keyed on the
   PRD's number, and this read used to stop at the program and its slices — so production's PG-15 was in "needs you"
   on 0592 and 0621 while its row read "with the fleet" and its page listed nothing. Read over the same reach as
   `personsMove`, so the list, the row and the page name one set. */
const personsMoves = id => entityActions(id).filter(a => a.person && personOwes(a, programIdOf(a.id)));
/* ONLY the ones that need a PERSON. `viewNext` used to split `D.actions` into `mine`/`fleet` for
   the whole board at once; this is that same split, read per program, so the list can say which
   programs are actually waiting on the reader and which only look busy. */
const openCount = id => entityActions(id).filter(a => !a.fleet).length;
/* "N TO DO", ONE DEFINITION FOR THE ROW, THE PAGE AND THE BADGE (ENG-10704, P-07): the rows a program's page lists
   that are not the fleet's own, less the advisories — a cut or a program that names no proof or authors no bar is a
   judgement, not something stuck, which is the operator's distinction `actionTotals` has drawn for the badge all
   along. The badge is the sum of this over every program, so the chips on the list it opens, folds included, add
   up to it; before, the badge left the advisories out while every chip counted them.

   ══ THE STANDING RULE FOR EVERY NUMBER DERIVED FROM THIS ONE — READ IT BEFORE YOU ADD A LINE ══
   THIS PAGE NEVER EXPLAINS ITSELF IN PROSE. A NUMBER THAT NEEDS A SENTENCE TO EXPLAIN IT IS A
   NUMBER IN THE WRONG SHAPE — reshape the number, never annotate it.

   The same mistake was made three times on this one count, and the third time was fixed by
   repeating it:
     · ENG-10683 wrote a definition sentence under the list ("N programs need you — each has a
       question waiting or a to-do only a person can do: …"). Read back in production: "wtf is
       there raw text on the What to do next page … remove that."
     · ENG-10733 removed it and left a bare hidden count.
     · ENG-10764 was a REAL defect — the badge read 14 while the visible chips summed to 11,
       with nothing reconciling them — and was fixed with a new sentence of exactly the same
       shape ("3 to-dos are on programs hidden by this view — show them"). Same reaction: "WTF
       is there now another raw text message … its not properly designed."

   The defect was never the missing sentence; it was a total presented as if it were a view.
   So the count is presented as `shown of total` (`todoTally`, below, in the page's own `X of Y`
   idiom — `.showing`, `slicesDone`, the strip's stats), the gap is arithmetic a reader does in
   their head, and the CAUSE of the gap rides the filter control that is doing the hiding
   (`filterHides`), because that is the thing a person would click. No note, no link, no
   tooltip restating any of it. If a future reading genuinely cannot be put in `of N` form, say
   so and change the shape of the number — do not reach for prose a fourth time.

   A THIRD INSTANCE WAS FOUND AND TAKEN THE SAME WAY, and the finding matters more than the fix:
     · ENG-10676 ended a filtered list with "N more programs with a question waiting are hidden
       by this view — show them" — the same sentence, in the SECOND unit this page totals.
   It escaped both of the readings above only because a question is the HOST'S fact and the
   standalone page registers no host, so it drew nothing off production. It is `asksTally` now —
   `1 of 3 questions`, the same `X of Y`, beside the to-do figure, with its cause on the same
   filter chip. THE LESSON FOR THE NEXT READER: a note that never rendered in front of the
   operator is not a note that passed; look for the prose the seams switch off, not only the
   prose you can see. */
/* ONE SET, THE COUNT'S AND THE NEW PAGE'S: every move a person owes on this program. The badge and the row's "N to do" count it
   (`todoCount`), and the New UI program page DRAWS it (`tuTodoSlot`) -- "1 to do" on the board over a page that listed nothing was two
   computations disagreeing, one of them a count with no page behind it. */
const programOwed = id => entityActions(id).filter(a => personOwes(a, id));
const todoCount = id => programOwed(id).length;
/* THE ONE PREDICATE FOR "A PERSON OWES THIS": a row that is not the fleet's own and that the program's driver
   does not own. The list's badge (`todoCount`), the program page's To-do list (`viewProgram`) and the cockpit
   (`personMoves`) all call it, so a number can never name rows the other two decline to show (PG-044:
   "6 to do" over an empty page and an empty cockpit). `programId` is the program the row sits on. */
const personOwes = (a, programId) => !a.fleet && !(programId && driverHandles(a, programId));
/* A program with live work and nothing in it for a person — the fleet has it, and the reader's
   attention is better spent elsewhere. `!p.nsl` and `p.complete` never reach here: `flight`
   already implies neither. */
const fleetMoving = p => p.flight && !openCount(p.id) && !needsYou(p);

/* THE AUTHORED GROUP, ALWAYS AHEAD OF THE INHERITED ONE — the ordering `applyFilters` uses for
   "your priority order" and the one Reorder mode reads (unfiltered) to build its own list. Two
   programs can both carry a numeric `rank` — one because a person placed it, one because it
   inherited a slice's urgency — and sorting the two groups together as one numeric column is
   exactly the mixing the operator asked off this page: an inherited rank is not a place in the
   reader's own order, so it may never outrank, or interleave with, one that is. The placed group
   sits in the person's own order (`authored`, never the resolved `rank` — see `authoredOf`); the
   unplaced one keeps the OLD tie-break (`rank || 999`, then id), so "nobody has authored anything
   yet" degrades to the id order this page always fell back to — `placed` is simply empty and
   `unplaced` is everyone, sorted exactly as before. */
function priorityOrder(list){
  return { placed: list.filter(isPlaced).sort(byAuthored),
           unplaced: list.filter(p => !isPlaced(p)).sort(byUrgency) };
}

/* A PROGRAM A PERSON IS NEEDED ON (ENG-10676, narrowed by ENG-10683): a question waits on it —
   its own, its cuts' or its PRDs', through the host's seam — or a finding sits on it that ONLY A
   PERSON CAN MOVE: `person`, which `board.py` stamps on closing a proven program, naming a proof
   or running the drill a finished one waits on, a planning verb the fleet does not run, a
   decomposed program's own "no proof named". A waived cut carries no row of its own any more: the
   program closes over it. NOT EVERY TO-DO. #581 read the row's "N to do" chip
   here, and on production `v0.5.64` that listed 21 of 22 programs: decompose, cut a slice's PRDs
   and start driving are the fleet's to do once a person presses the button the page already
   carries, and a filter that lists them lists the plan. The chip stays the wider count
   (`openCount`); this is the narrow one, read over the program, its cuts AND its cuts' PRDs —
   a `planning` row is keyed on the PRD's number, never on the cut. */
const personsMove = p => D.actions.map(asMet).some(a => a.person && personOwes(a, programIdOf(a.id)) && (a.id === p.id ||
  (p.sl || []).some(s => s.id === a.id || (s.prds || []).some(r => r.n === a.id))));
const needsYou = p => questionsWaiting(p) > 0 || personsMove(p);

/* STALLED IS THE FINDING (X5 of the inventory, ENG-10683). The "stalled only" filter and the stalled stat carried
   their own predicate — slices, nothing in flight, not proven — and on production it counted PG-08 (no proof
   named), PG-29 (never decomposed) and PG-13 / PG-24 (nothing left to move), none of whose pages shows a stalled
   finding. One predicate: the page carries `board.py`'s `stalled` row. It reaches a parked program that carries
   it, as Needs-you does, so the list, the stat and the pages cannot disagree. */
const isStalled = p => !drivenNow(p.id) && D.actions.some(a => a.group === "stalled" && a.id === p.id);

/* WHAT A FILTER MAY REACH. Every filter narrows the plan — the parked two are drawn in the
   folds at the foot and nowhere else — except `needs you`, which reaches into the folds on
   purpose: the production case was a WAIVED program with a question waiting on it, drawn only
   inside a fold nobody opens, under a masthead that said one was waiting. A question or a
   to-do on a parked program is no less a person's, and a filter named "needs you" that could
   not find it would be the second surface to hide the same row. */
/* `set` IS THE FILTER SET TO READ, the reader's own by default. Named rather than assumed so
   `filterHides` can ask what this view would draw with ONE filter lifted, without the round
   trip through the module-level `filters` that a temporary swap would be. */
function filterBase(set){
  const f = set || filters;
  return f.has(NEEDS_YOU) || f.has("stalled") ? D.programs.slice() : activePrograms();
}

/* THE DEFAULT VIEW NEVER OPENS EMPTY (ENG-22536). "hide proven" is on out of the box, so a
   deployment whose every program in play is proven opened on "Nothing matches these filters"
   under a summary that said a program was in play — the first thing a reader saw on a new
   install. The filter still hides proven programs whenever another program is left to show;
   it yields only when it would hide the whole plan. The empty list is removed rather than
   explained: this page never explains itself in prose (`todoCount`'s standing rule). */
function onlyProvenInPlay(){
  const active = activePrograms();
  return active.length > 0 && active.every(p => p.complete);
}

/* ONE PREDICATE PER PROGRAM FOR EVERY ACTIVE FILTER, read by the list AND the parked folds
   (ENG-10704, P-22): "has live work" left both folds drawn with no live work in them. */
function passesFilters(p, fold, set){
  const f = set || filters;
  const who = WHO_OVR;
  /* The bar's search over the program's id and name, and its "Assigned" other than "me" (NEW UI only: both stay empty otherwise). */
  if (pgQ && (p.id + " " + (p.name || p.title || "")).toLowerCase().indexOf(pgQ.trim().toLowerCase()) < 0) return false;
  const w = who !== undefined ? who : (whoSel || (mineOn ? "me" : ""));
  if (w === "none" && Array.isArray(p.owners) && p.owners.length) return false;
  if (w && w !== "me" && w !== "none" && !(Array.isArray(p.owners) && p.owners.includes(w))) return false;
  if (w === "me" && who !== undefined && RZ_VIEWER && !(Array.isArray(p.owners) && p.owners.includes(RZ_VIEWER))) return false;
  /* MY PROGRAMS (PRD 0839): a program passes iff its `owners` include the viewer. INERT when the
     viewer is unknown — a deployment that cannot say who is reading shows every program. An
     unowned program has no owner, so it fails here, which is AC-2 and AC-4: it appears in no one's
     narrowed list. A view filter, never a permission: the program stays reachable wherever linked. */
  if (who === undefined && mineOn && RZ_VIEWER && !(Array.isArray(p.owners) && p.owners.includes(RZ_VIEWER))) return false;
  /* `needs you` KEEPS THE FOLDS WHOLE (ENG-10683's decision): its list already reaches into them, and a
     parked program it draws leaves its fold through `LISTED`. Every narrowing filter narrows a fold
     exactly as it narrows the list. */
  if (!fold && f.has(NEEDS_YOU) && !needsYou(p)) return false;
  if (f.has("hideComplete") && p.complete && !onlyProvenInPlay()) return false;
  if (f.has("stalled") && !isStalled(p)) return false;
  if (f.has("noProof") && p.proof.length) return false;
  if (f.has("hasLive") && !(p.livePRDs > 0)) return false;
  return true;
}

function applyFilters(){
  let list = filterBase().filter(p => passesFilters(p));
  if (sortKey !== "priority"){
    const key = { attention: p => -openCount(p.id), blocking: p => -p.blast, live: p => -p.livePRDs, id: p => p.id };
    return list.sort((a, b) => { const x = key[sortKey](a), y = key[sortKey](b);
      return x < y ? -1 : x > y ? 1 : a.id.localeCompare(b.id); });
  }
  const { placed, unplaced } = priorityOrder(list);
  return placed.concat(unplaced);
}

/* ══ THE BADGE'S OWN HIDDEN HALF, MADE ARITHMETIC (ENG-10764, superseding its first fix) ══
   The masthead badge is `Σ todoCount` over EVERY program (P-07's "one count" rule); the default
   view hides the proven ones — "hide proven" is on out of the box — and each of production's
   five carries a person-only "Close it" to-do with NO question behind it, so the questions half
   below (keyed on `questionsWaiting`) never sees them: the badge read 14 over rows that summed
   to 11 and nothing reconciled the two. That was fixed once with a sentence under the list and the
   sentence was rejected on sight — twice, on the same page. See `todoCount`'s standing rule.
   The number is the fix: the toolbar prints `11 of 14 to do`, so the gap IS the number.

   WHAT THE VIEW DRAWS is the list PLUS the rows the parked folds carry. A collapsed `<details>`
   is drawn — one click, no navigation, no filter change — and `filterBase` always reaches the
   parked programs, so counting them as hidden would invent a gap the reader cannot close by
   changing anything. (The removed note excluded them for exactly this reason, which left its
   own arithmetic — shown + hidden ≠ total — needing the very explanation it then wrote out.) */
function drawnPrograms(set){
  const f = set || filters;
  const ids = new Set(filterBase(f).filter(p => passesFilters(p, false, f)).map(p => p.id));
  D.programs.forEach(p => {
    if (isParked(p) && !ids.has(p.id) && passesFilters(p, true, f)) ids.add(p.id);
  });
  return ids;
}
const todosOver = ids => D.programs.reduce((n, p) => n + (ids.has(p.id) ? todoCount(p.id) : 0), 0);
/* SHOWN AND TOTAL, IN THE UNIT THE BADGE COUNTS. `all` is `actionTotals().needsHuman` by
   construction — the same sum over the same programs — so the tab badge and this line can never
   disagree, and `all - shown` is what every narrowing between them is hiding. */
function todoTally(){
  const all = D.programs.reduce((n, p) => n + todoCount(p.id), 0);
  if (!all) return "";
  const shown = todosOver(drawnPrograms());
  const part = shown < all ? " part" : "";
  return `<span class="todos${part}" data-todos-shown="${shown}" data-todos-all="${all}">${shown} of ${all} to do</span>`;
}
/* ══ THE THIRD RETURN OF THE SAME PATTERN, ANSWERED THE SAME WAY (ENG-10676, reshaped) ══
   A `<p>` used to END the list — "N more programs with a question waiting are hidden by this
   view — show them" — and it is gone, because it was the identical defect in a second unit: the
   masthead totals the questions waiting on programs, a filtered view shows fewer, and a SENTENCE
   was carrying the difference. See `todoCount`'s standing rule; this is what "reshape the number"
   means when it is met a fourth time. It survived two rejections only because it never rendered
   in front of the operator: a question is the HOST's fact (`waiting`), and the standalone page —
   which every reading before this one was taken on — has no host, so `questionsWaiting` was 0
   everywhere and the line never drew. Production draws it.

   COUNTED IN QUESTIONS, NOT IN PROGRAMS, which the deleted line was and had to say out loud
   ("N more programs …") because it disagreed with the masthead's own unit beside it. `all` is
   the masthead's figure ITSELF, through `waitingTotal` — never a sum this file builds out of the
   per-program seam, which cannot see a question no program can carry and once made this line
   read `1 of 1` under a masthead saying 2 (see that seam's own comment). So the marker above and
   this line are one expression, exactly as `todoTally`'s `all` and the tab badge are. Absent, not
   zero, when nothing waits: a permanent `0 of 0` in the toolbar is the chrome nobody reads by the
   second week, and it is what every host-less page shows.

   `shown` COUNTS ONLY WHAT THE VIEW DRAWS, so an unplaced question is in `all` and in no view:
   the figure reads partial and stays partial, which is true — this page cannot show a row that
   does not exist, and the masthead beside it is the way to the set. A partial reading nobody can
   close is not a defect; a whole reading that is false is. */
const asksOver = ids => D.programs.reduce((n, p) => n + (ids.has(p.id) ? questionsWaiting(p) : 0), 0);
function asksTally(){
  const all = questionsTotal();
  if (!all) return "";
  const shown = asksOver(drawnPrograms());
  const part = shown < all ? " part" : "";
  return `<span class="asks${part}" data-asks-shown="${shown}" data-asks-all="${all}">${shown} of ${all} question${
    all === 1 ? "" : "s"}</span>`;
}
/* THE CAUSE RIDES THE CONTROL DOING THE HIDING, and nowhere else: what would come back if THIS
   filter were lifted, on the filter's own chip and its own menu row — the thing a reader would
   click. Every filter here narrows (`drawnPrograms` with one lifted is a superset of the drawn
   set), so this is never negative; with two filters on, each names its own reach and they may
   overlap rather than sum, which is what "lift this one and N come back" honestly means. */
function filterHides(key){
  if (!filters.has(key)) return { todo: 0, asks: 0 };
  const drawn = drawnPrograms();
  const without = drawnPrograms(new Set([...filters].filter(k => k !== key)));
  return { todo: todosOver(without) - todosOver(drawn), asks: asksOver(without) - asksOver(drawn) };
}
/* EACH UNIT NAMED, because two counts now stand beside this chip and a bare "5 hidden" would be
   a figure the reader cannot attach to either of them. The nouns and their order are the
   toolbar's own ("to do", then "questions"), so the chip reads as the arithmetic those two
   lines are missing. A unit this filter hides none of is left out rather than printed as a
   zero — the rule the whole label already keeps. */
const hidesLabel = key => {
  const n = filterHides(key);
  if (!n.todo && !n.asks) return "";
  const said = [n.todo ? `${n.todo} to do` : "",
                n.asks ? `${n.asks} question${n.asks === 1 ? "" : "s"}` : ""].filter(Boolean).join(", ");
  return `<span class="fh" data-hides="${n.todo}" data-hides-asks="${n.asks}">${said} hidden</span>`;
};

/* SORT AND FILTER ARE NOT OFFERED WHILE YOU REORDER, AND THAT IS A DECISION AND NOT AN OMISSION.
   The write is always "the whole order, top to bottom" (`commitOrder`'s own contract) — never a
   patch — so a filter that had trimmed the view, or a sort that had interleaved placed and
   unplaced programs, would make that write a claim about rows the reader never saw drop past the
   fold: a silent partial order, which is the one thing this mode may never produce. Sort goes
   along with filter rather than merely filter, because the boundary line Reorder mode drags
   across only means anything when the list is grouped placed-then-unplaced — sorted by
   "blocking" or "live work" that grouping is gone and there is no single line left to drop
   across. So this toolbar is the RESTING list's; Reorder mode draws `reorderBar` in its place —
   the two controls that mode has (Save, Cancel) rather than two it has switched off — and the
   click handler below still guards the sort and filter attributes defensively. */
/* IT IS THE LIST PAGES' FILTER BAR (`filterBar`): Sort is its Sort, and the five filters are its
   first on/off fields — each a checkbox in the Filter menu and a chip when it is on, the figure
   it hides riding both (`hidesLabel`). "hide proven" is ON OUT OF THE BOX, so it is a quiet chip
   that can be turned off and not removed, and turned off it reads "proven shown" with a × that
   puts it back. Both stay route state (`boardRoute`), so a toggle is a navigation and a link
   carries the view. The counts at the row's end are the toolbar's own: to do, questions, shown. */
const FILTER_OFF = { hideComplete: "proven shown" };
const FILTER_ON = new Set(["hideComplete"]);
/* THE NEW UI'S BAR: the one filter component (`tuFilterBar`, team-filter.js) — Filter, a chip per choice, Search and Display (Sort) at the right. Same state as the old bar (`filters`, `sortKey`,
   `mineOn`, all route state); only the control that draws it differs. Each count is what would match under the OTHER
   active filters. "Hidden" under Proven has no count: lifting it brings proven programs back, a figure the old bar
   carried as its "N to do hidden" note and the tally beside the bar still says. */
const PG_STATUS = [["needs-you", "Needs you"], ["stalled", "Stalled"], ["hasLive", "Has live work"], ["noProof", "No proof named"]];
function toolbarNew(shown, total){
  const base = () => new Set([...filters].filter(k => !PG_STATUS.some(x => x[0] === k)));
  const statusN = k => drawnPrograms(new Set([...base(), k])).size;
  const owners = [];
  D.programs.forEach(p => (Array.isArray(p.owners) ? p.owners : []).forEach(o => { if (o !== RZ_VIEWER && owners.indexOf(o) < 0) owners.push(o); }));
  if (whoSel && whoSel !== "none" && whoSel !== "me" && owners.indexOf(whoSel) < 0) owners.push(whoSel);
  /* EACH COUNT IS THE LIST'S OWN: the programs `applyFilters` draws (the figure "N matching" prints) with this "Assigned" value
     in force and the reader's other filters kept, through the same predicate (`passesFilters`) the list runs. It was
     `drawnPrograms()`, which also counts the parked programs the folds hold, so Unassigned read 21 where picking it listed 3. */
  const whoN = w => { WHO_OVR = w; try { return applyFilters().length; } finally { WHO_OVR = undefined; } };
  const who = [...(RZ_VIEWER ? [{ id: "me", label: "Assigned to me", count: whoN("me") }] : []),
    { id: "none", label: "Unassigned", count: whoN("none") },
    ...owners.slice(0, 6).map(o => ({ id: o, label: "Assigned to " + o.split("@")[0], count: whoN(o) }))];
  const spec = {
    views: [], tabs: false,
    search: { placeholder: "Search id or name\u2026" },
    dims: [
      { key: "status", label: "Status", multi: true, opts: PG_STATUS.map(([k, l]) => ({ id: k, label: l, count: statusN(k) })) },
      { key: "proven", label: "Proven", multi: false, def: ["hide"], opts: [{ id: "hide", label: "Hidden" }, { id: "show", label: "Shown" }] },
      { key: "who", label: "Assigned", multi: false, opts: who },
    ],
    sort: { label: "Sort", opts: SORTS.map(([k, l]) => ({ id: k, label: l })) },
    extra: `<span class="tally">${todoTally()}${asksTally()}</span>`,
    matching: shown,
  };
  const state = { q: pgQ, sel: {
    status: PG_STATUS.map(x => x[0]).filter(k => filters.has(k)),
    proven: [filters.has("hideComplete") ? "hide" : "show"],
    who: mineOn && RZ_VIEWER ? ["me"] : whoSel ? [whoSel] : [] }, sort: sortKey, open: pgOpen, fm: pgFm };
  PG_SPEC = spec; PG_STATE = state;
  /* Bound on every draw: team-filter.js loads after this file, and binding is an assignment. */
  tuFilterBarBind("programs", { state: () => PG_STATE, spec: () => PG_SPEC, change: programsBarChange });
  return tuFilterBar(spec, state, "programs");
}
let PG_SPEC = null;
let PG_STATE = null;
function programsBarChange(kind){
  if (REORDER_MODE) return;
  const st = PG_STATE;
  if (!st) return;
  if (kind === "open" || kind === "fq" || kind === "sug" || kind === "view"){ pgOpen = st.open || null; pgFm = st.fm || null; render(openRoute()); return; }
  pgOpen = st.open || null; pgFm = st.fm || null;
  if (kind === "q"){
    pgQ = st.q || "";
    render(openRoute());
    const el = main && main.querySelector ? main.querySelector('[data-keep="tf-q"]') : null;
    if (el && el.focus){ el.focus({ preventScroll: true }); try { el.setSelectionRange(el.value.length, el.value.length); } catch (_e){ /* not a text input */ } }
    return;
  }
  if (kind === "sort"){ sortKey = st.sort || "priority"; store.set(prefKey("zb.sort"), sortKey); go(boardRoute()); return; }
  if (kind === "dim"){
    const sel = st.sel || {};
    PG_STATUS.forEach(([k]) => { if ((sel.status || []).indexOf(k) >= 0) filters.add(k); else filters.delete(k); });
    if ((sel.proven || []).indexOf("show") >= 0) filters.delete("hideComplete"); else filters.add("hideComplete");
    const w = (sel.who || [])[0] || "";
    mineOn = w === "me"; whoSel = w && w !== "me" ? w : "";
    pgQ = st.q || "";
    store.set(prefKey("zb.filters"), [...filters].join(","));
    go(boardRoute());
  }
}

function toolbar(shown, total){
  if (typeof tuNewUi === "function" && tuNewUi() && typeof tuFilterBar === "function" && typeof tuFilterBarBind === "function") return toolbarNew(shown, total);
  const said = l => l.charAt(0).toUpperCase() + l.slice(1);
  return filterBar({
    id: BOARD_ROUTE,
    noun: ["program", "programs"],
    matched: shown,
    count: `<span class="tally">${todoTally()}${asksTally()}<span class="showing">${shown} of ${total}</span></span>`,
    fields: [...FILTERS.map(([k, l]) => ({ id: k, label: said(l), flag: true, value: filters.has(k) ? ["on"] : [],
      def: FILTER_ON.has(k) ? ["on"] : [], off: FILTER_OFF[k], after: hidesLabel(k) })),
      /* MY PROGRAMS (PRD 0839): OFF by default — the list opens on every program — so, like
         "stalled only", it is a checkbox in the Filter menu and a chip with an × only while it
         narrows; the × returns to every program. The narrowing itself is module state, not `filters`
         (per-visit, never persisted), so its `value` reads `mineOn` and no `zb.filters` write
         follows a toggle. Absent when no viewer is known: with nothing saying who is reading the
         filter does nothing, and a chip that narrowed nothing would be a control that lies. */
      ...(RZ_VIEWER ? [{ id: MINE, label: "My programs", flag: true, value: mineOn ? ["on"] : [],
        def: [], after: "" }] : [])],
    sort: { value: sortKey, def: "priority", options: SORTS },
    on: {
      set: (k, vals) => {
        if (REORDER_MODE) return;
        if (k === MINE){ mineOn = vals.length > 0; go(boardRoute()); return; }
        if (vals.length) filters.add(k); else filters.delete(k);
        store.set(prefKey("zb.filters"), [...filters].join(","));
        go(boardRoute());
      },
      sort: k => {
        if (REORDER_MODE) return;
        sortKey = k || "priority"; store.set(prefKey("zb.sort"), sortKey);
        go(boardRoute());
      },
      /* CLEAR RETURNS TO THE PAGE AS IT OPENS OUT OF THE BOX: your priority order, "hide proven" —
         and every program, the narrowing off (PRD 0839). */
      clear: () => {
        if (REORDER_MODE) return;
        filters = new Set(FILTER_ON); sortKey = "priority"; mineOn = false;
        store.set(prefKey("zb.filters"), [...filters].join(",")); store.set(prefKey("zb.sort"), sortKey);
        go(boardRoute());
      },
    },
  });
}

/* ── the filter bar: one search, one Filter menu, a chip for each filter in force ─────────────
 *
 * EVERY LIST NARROWS ITS ROWS THE SAME WAY, AND THIS IS THE ONE PLACE THAT WAY IS WRITTEN. Queue,
 * Runs and Fleet each grew their own row of labelled boxes, a phone fold that hid what was set, and
 * a select that could pick one value where the API takes several. The operator chose one pattern
 * for every list (the filters mockup's Option A): one row — search,
 * Filter, Sort where the page sorts, the match count at the right — and under it one chip per filter
 * in force. A page DECLARES its fields; it never draws a control.
 *
 * THE PAGE OWNS ITS STATE AND THIS FILE OWNS NOTHING BUT THE OPEN MENU. Where a filter lives stays
 * where it lived — Queue's and Runs' in the route, the repository widening in the reader's storage —
 * so a link and a reload keep working exactly as before. The spec hands in each field's CURRENT
 * values and an `on` of callbacks; a click here calls one of them and the page navigates or
 * repaints as it always did. The only thing held here is which menu is open, at which level, with
 * what typed into it, because the ten-second repaint replaces the markup and a menu that shut itself
 * every tick would be a menu nobody can use.
 *
 *   filterBar({
 *     id: "queue",                       // one bar per page; keys the open menu and every data-keep
 *     noun: ["issue", "issues"],         // the sheet's "Show N issues"
 *     matched: 34,                       // the count the sheet's button and the empty state say
 *     count: "<b>34</b> of 127",         // the row's right-hand count, as markup, or "" for none
 *     search: { value, placeholder, label, said, tip, live },   // `said` leads the empty state's
 *                                        // "Issue is “ENG-1”"; `live` commits per keystroke, else Enter
 *     fields: [{ id, label, multi, values: [{ v, t, n, dead }], value: [..], def: [..], note, tip, menu,
 *                flag, off, after }],
 *     sort: { value, def, options: [[key, words], ..], note },
 *     on: { set(field, values), search(text), sort(key), clear(), paint() },
 *   })
 *
 * `def` IS A DEFAULT THE PAGE ALWAYS APPLIES — the repository in hand, the Queue's in-scope work. It
 * draws as a DASHED chip that can be changed and never removed, and Clear returns to it; a value
 * that differs from it is a solid chip with a ×, and × is "back to the default". A field whose
 * default is not empty and whose value IS empty reads "any" — a widening, and a filter in force.
 * `n` IS THE API'S COUNT OR IT IS ABSENT: a value with no count shows no number, and `0` is a
 * measurement. `multi` IS WHAT THE API ACCEPTS, never a preference: a parameter it takes once is a
 * radio. `menu: false` is a chip with no menu row — a narrowing another page linked in with.
 * A value's `dead` is the reason it cannot be picked now ("no bug runs ended in this window"): drawn,
 * disabled, and saying why, so a reader is never left on a filter that matches nothing untold.
 *
 * `flag: true` IS AN ON/OFF FILTER — the Programs list's "needs you", "hide proven" — with no values
 * to drill into: its menu row is its checkbox, its value is `["on"]` or `[]`, its chip is its own
 * words, and `off` is what the chip says when a flag that is ON by default has been turned off
 * ("proven shown"). `after` is markup a field carries on its chip and its menu row, for what the
 * filter is hiding ("3 to do hidden") — the figure rides the control that is doing the hiding.
 *
 * A PAGE WITH NOTHING TO NARROW DRAWS NO BAR (the mockup's second rule): no search, no field, no
 * sort and no chip is an empty string, which is the single-repository Bugs list's case.
 *
 * ON A PHONE THE SAME MENU IS A BOTTOM SHEET, and the stylesheet decides that, not this file:
 * `fleet.css`'s one breakpoint turns the panel into a sheet over a scrim, shows its heading and its
 * "Show N" button, and folds the row to search plus two icons. One markup, one breakpoint.
 */

/* The last spec each bar rendered, by id — what a click is resolved against. */
const FB = {};
/* THE OPEN MENU: `{ id, kind, from: "filter" | "sort", at: "" | field id | "__sort", q }`. `kind` is
   the route kind it was opened on, so a menu left open on one page is not open on the next. */
let FB_OPEN = null;
const FB_ICON = {
  search: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="m10.5 10.5 3 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  filter: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 3.5h12M4.5 8h7M7 12.5h2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  sort: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3v10m0 0-2.5-2.5M5 13l2.5-2.5M11 13V3m0 0L8.5 5.5M11 3l2.5 2.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};
/* A VALUE RIDES AN ATTRIBUTE ENCODED, because `|` separates the parts and a `"` would end the
   `data-keep` selector the focus restore builds from it. */
const fbEnc = v => encodeURIComponent(String(v));
const fbDec = v => { try { return decodeURIComponent(v); } catch (e) { return String(v); } };
const fbParts = el => String(el.getAttribute(el.__fb) || "").split("|").map(fbDec);
const fbGroup = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
const fbSame = (a, b) => (a || []).map(String).sort().join("\n") === (b || []).map(String).sort().join("\n");

function fbVals(f){ return Array.isArray(f.value) ? f.value.map(String) : []; }
function fbHasDef(f){ return Array.isArray(f.def) && f.def.length > 0; }
/* AT ITS DEFAULT: the dashed chip. IN FORCE: the solid one — a value that is not the default, or
   the empty widening of a field that has one. Neither: no chip. */
function fbAtDefault(f){ return fbHasDef(f) && fbSame(fbVals(f), f.def); }
function fbInForce(f){ return !fbAtDefault(f) && (fbVals(f).length > 0 || fbHasDef(f)); }
function fbField(spec, fid){ return (spec.fields || []).find(f => f.id === fid) || null; }
function fbWord(f, v){
  const hit = (f.values || []).find(x => String(x.v) === String(v));
  return hit ? String(hit.t) : String(v);
}
/* WHAT A CHIP SAYS: one or two values by name, more by number with the names in its tip. */
function fbSummary(f){
  if (f.flag) return fbVals(f).length ? String(f.label) : String(f.off || "not " + f.label);
  const vals = fbVals(f);
  if (!vals.length) return "any";
  if (vals.length <= 2) return vals.map(v => fbWord(f, v)).join(" or ");
  return `any of ${vals.length}`;
}
function fbSorted(spec){ return !!spec.sort && String(spec.sort.value || "") !== String(spec.sort.def || ""); }
function fbSortWords(spec){
  const hit = (spec.sort.options || []).find(o => String(o[0]) === String(spec.sort.value || ""));
  return hit ? hit[1] : ((spec.sort.options || [])[0] || ["", ""])[1];
}
function fbDirty(spec){
  return (spec.fields || []).some(fbInForce) || !!(spec.search && spec.search.value) || fbSorted(spec);
}
function fbOpenOf(id){
  const kind = (location.hash.slice(1) || "board").split(":")[0];
  return FB_OPEN && FB_OPEN.id === id && FB_OPEN.kind === kind ? FB_OPEN : null;
}
const fbNum = n => n === null || n === undefined ? "" : `<span class="fb-num${Number(n) ? "" : " z"}">${fbGroup(n)}</span>`;

function fbValueItem(spec, f, x, lead){
  const on = fbVals(f).includes(String(x.v));
  return `<button type="button" class="ddi fb-mi" role="${f.multi ? "menuitemcheckbox" : "menuitemradio"}" aria-checked="${on}"${
    x.dead && !on ? ` disabled data-tip="${esc(x.dead)}"` : ""}
    data-fb-tog="${esc(spec.id)}|${fbEnc(f.id)}|${fbEnc(x.v)}" data-fb-mi="${esc(spec.id)}" data-keep="fb:${esc(spec.id)}:v:${fbEnc(f.id)}:${fbEnc(x.v)}"><span
    class="fb-box${f.multi ? "" : " rd"}" aria-hidden="true">${on && f.multi ? "&check;" : ""}</span><span class="fb-l">${
    lead ? `<span class="fb-in">${esc(f.label)} &rsaquo;</span> ` : ""}${esc(x.t)}</span>${fbNum(x.n)}</button>`;
}
function fbFieldItem(spec, f){
  if (f.flag){
    const on = fbVals(f).length > 0;
    return `<button type="button" class="ddi fb-mi" role="menuitemcheckbox" aria-checked="${on}"
      data-fb-tog="${esc(spec.id)}|${fbEnc(f.id)}|on" data-fb-mi="${esc(spec.id)}" data-keep="fb:${esc(spec.id)}:v:${fbEnc(f.id)}:on"><span
      class="fb-box" aria-hidden="true">${on ? "&check;" : ""}</span><span class="fb-l">${esc(f.label)}${f.after || ""}</span></button>`;
  }
  return `<button type="button" class="ddi fb-mi" role="menuitem" data-fb-at="${esc(spec.id)}|${fbEnc(f.id)}"
    data-fb-mi="${esc(spec.id)}" data-keep="fb:${esc(spec.id)}:at:${fbEnc(f.id)}"><span class="fb-l">${esc(f.label)}</span><span
    class="fb-sum">${esc(fbSummary(f))}</span><span class="fb-gt" aria-hidden="true">&rsaquo;</span></button>`;
}
function fbNote(text){ return text ? `<p class="fb-note">${esc(text)}</p>` : ""; }

/* THE MENU, AT ONE OF FOUR LEVELS: the fields with what each is set to; one field's values; what the
   typed words match across every field ("bug", "imp"); or the sort orders. */
function fbMenu(spec, open){
  const id = esc(spec.id);
  const fields = (spec.fields || []).filter(f => f.menu !== false);
  const typed = String(open.q || "");
  const sorting = open.at === "__sort";
  let body;
  if (sorting){
    body = (spec.sort.options || []).map(([k, words]) => {
      const on = String(spec.sort.value || "") === String(k);
      return `<button type="button" class="ddi fb-mi" role="menuitemradio" aria-checked="${on}" data-fb-sort="${id}|${fbEnc(k)}"
        data-fb-mi="${id}" data-keep="fb:${id}:s:${fbEnc(k || "default")}"><span class="fb-box rd" aria-hidden="true"></span><span class="fb-l">${esc(words)}</span></button>`;
    }).join("") + fbNote(spec.sort.note);
  } else if (open.at && fbField(spec, open.at)){
    const f = fbField(spec, open.at);
    body = `<button type="button" class="fb-back" data-fb-at="${id}|" data-fb-mi="${id}" data-keep="fb:${id}:back">&lsaquo; ${esc(f.label)}</button>`
      + ((f.values || []).length ? f.values.map(x => fbValueItem(spec, f, x, false)).join("") : fbNote(f.empty || "Nothing to choose from yet."))
      + fbNote(f.note);
  } else if (typed.trim()){
    const t = typed.trim().toLowerCase();
    const hits = [];
    fields.forEach(f => {
      if (String(f.label).toLowerCase().startsWith(t) || (f.flag && String(f.label).toLowerCase().includes(t))){
        hits.push(fbFieldItem(spec, f));
      }
      if (f.flag) return;
      (f.values || []).forEach(x => {
        if (String(x.t).toLowerCase().includes(t) || String(x.v).toLowerCase().includes(t)) hits.push(fbValueItem(spec, f, x, true));
      });
    });
    body = hits.length ? hits.slice(0, 12).join("") : fbNote(`No filter and no value is called “${typed.trim()}”.`);
  } else {
    body = fields.map(f => fbFieldItem(spec, f)).join("");
  }
  const n = Number(spec.matched);
  const noun = spec.noun || ["row", "rows"];
  const go = isFinite(n) && spec.matched !== null && spec.matched !== undefined
    ? `Show ${fbGroup(n)} ${n === 1 ? noun[0] : noun[1]}` : "Show";
  return `<span class="fb-scrim" data-fb-close="${id}" aria-hidden="true"></span><div class="ddp fb-m" role="dialog"
    aria-label="${sorting ? "Sort" : "Filters"}" data-fb-m="${id}"><div class="fb-sh"><b>${sorting ? "Sort" : "Filters"}</b>${
    !sorting && fbDirty(spec) ? `<button type="button" class="fb-clr" data-fb-clear="${id}" data-keep="fb:${id}:sheet-clear">Clear</button>` : ""}</div>${
    sorting ? "" : `<input class="fb-find" type="text" data-fb-find="${id}" data-keep="fb:${id}:find" placeholder="Filter by&hellip;"
    aria-label="Find a filter or a value" value="${esc(typed)}" autocomplete="off" spellcheck="false">`}<div class="fb-list" role="menu">${body}</div><button
    type="button" class="fb-go" data-fb-close="${id}" data-keep="fb:${id}:go">${esc(go)}</button></div>`;
}

/* ONE CHIP PER FILTER IN FORCE, AND THE DEFAULTS AS QUIET ONES. The chip names its field and its
   value in words, a click on it opens the menu at that field, and × takes it back to the default. */
function fbChips(spec){
  const id = esc(spec.id);
  const chips = (spec.fields || []).filter(f => fbInForce(f) || fbAtDefault(f)).map(f => {
    const quiet = fbAtDefault(f);
    const all = fbVals(f).map(v => fbWord(f, v)).join(", ");
    const tip = f.tip || (fbVals(f).length > 2 ? all : "");
    const words = f.flag ? `<b>${esc(fbSummary(f))}</b>${f.after || ""}`
      : `<span class="f">${esc(f.label)}</span> is <b>${esc(fbSummary(f))}</b>${f.after || ""}`;
    const face = f.menu === false
      ? `<span class="fb-cb"${tip ? ` tabindex="0" data-tip="${esc(tip)}"` : ""}>${f.words ? f.words : words}</span>`
      : `<button type="button" class="fb-cb" data-fb-chip="${id}|${fbEnc(f.id)}" data-keep="fb:${id}:chip:${fbEnc(f.id)}"${
          tip ? ` data-tip="${esc(tip)}"` : ""} aria-label="${esc(f.flag ? fbSummary(f) : `${f.label} is ${fbSummary(f)}`)}${
          quiet ? " (the default)" : ""}: change it">${words}</button>`;
    const x = quiet ? "" : `<button type="button" class="fb-cx" data-fb-rm="${id}|${fbEnc(f.id)}" data-keep="fb:${id}:rm:${fbEnc(f.id)}"
      aria-label="Remove ${esc(f.label)}${fbHasDef(f) ? ", back to its default" : ""}">&times;</button>`;
    return `<span class="fb-chip${quiet ? " def" : ""}" data-fb-f="${esc(f.id)}">${face}${x}</span>`;
  });
  if (fbSorted(spec)){
    chips.push(`<span class="fb-chip" data-fb-f="__sort"><button type="button" class="fb-cb" data-fb-chip="${id}|__sort" data-keep="fb:${id}:chip:__sort"><span
      class="f">Sort</span> <b>${esc(fbSortWords(spec))}</b></button><button type="button" class="fb-cx" data-fb-rm="${id}|__sort"
      data-keep="fb:${id}:rm:__sort" aria-label="Remove the sort">&times;</button></span>`);
  }
  const clear = fbDirty(spec) ? `<button type="button" class="fb-clr" data-fb-clear="${id}" data-keep="fb:${id}:clear">Clear</button>` : "";
  return chips.length || clear ? `<div class="fb-chips">${chips.join("")}${clear}</div>` : "";
}

/* ── the New UI's filter bar: the SAME spec, drawn by the one filter component (`team-filter.js`) ──────────────
 *
 * OWNER-DECIDED: one filter component on every page that filters. `tuFilterBar` (`team-filter.js`) is it: a Filter button
 * that opens a menu of fields and then of values, a segmented chip for each choice, Search and Display at the right. THIS is the small
 * adapter that lets the pages built on `filterBar` use it WITHOUT changing a line of theirs. With the New UI switch on, `filterBar(spec)`
 * hands the spec to `fbNewBar`; off, or where `team-filter.js` is not loaded (the standalone board), it draws the bar above exactly
 * as it always did.
 *
 * WHAT MAPS ONE TO ONE: `fields` -> the component's fields (`multi` -> a checklist, else one choice; `values[].n` -> the count, absent
 * stays absent; `values[].dead` -> a value that cannot be picked now, with its reason), `search` -> the search box (`live` commits per
 * pause in typing, otherwise on Enter), `sort.options` -> Sort in Display, `count` -> the match figure at the right, and every callback
 * in `on` is still the thing a change calls — the page keeps its state where it kept it.
 *
 * WHAT THIS ADDS, because the pages declare things the component has a word for:
 *   `def`      a default the page always applies draws as a QUIET chip with no x; a different value is solid, and its x
 *              (and Clear all) return to the default.
 *   `note`     the line in a field's menu (what the counts are counts of).
 *   `menu:false` a narrowing another page linked in with: a pinned chip with an x and no menu.
 * A spec with an on/off `flag` field (the Programs list) is not drawn here: that page owns its own New UI field list. */
const NB = {};
const fbX = t => String(t == null ? "" : t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function fbNewOn(spec){
  return typeof tuNewUi === "function" && tuNewUi() && typeof tuFilterBar === "function" && typeof tuFilterBarBind === "function"
    && !(spec.fields || []).some(f => f.flag);
}
const fbNewRoute = () => (location.hash.slice(1) || "board").split(":")[0];
const fbMenuFields = spec => (spec.fields || []).filter(f => f.menu !== false);

function fbNewSpec(spec, named){
  return {
    search: spec.search ? { placeholder: spec.search.placeholder || spec.search.label || "Search", tip: spec.search.tip, enter: !spec.search.live } : false,
    dims: fbMenuFields(spec).map(f => ({ key: String(f.id), label: String(f.label), icon: f.icon, multi: !!f.multi, tip: f.tip, note: f.note, empty: f.empty,
      def: fbHasDef(f) ? f.def.map(String) : undefined,
      opts: (f.values || []).map(x => ({ id: String(x.v), label: String(x.t), count: x.n === null || x.n === undefined ? undefined : x.n,
        dead: x.dead ? String(x.dead) : undefined })) })),
    sort: spec.sort ? { label: "Sort", note: spec.sort.note, opts: (spec.sort.options || []).map(o => ({ id: String(o[0]), label: String(o[1]) })) } : undefined,
    pinned: named.map(f => ({ id: String(f.id), label: String(f.label), tip: f.tip, words: f.words || `${fbX(f.label)}: <b>${fbX(fbSummary(f))}</b>` })),
    countHtml: spec.count || "",
    dirty: fbDirty(spec),
  };
}

function fbNewBar(spec){
  const id = spec.id;
  const route = fbNewRoute();
  const st = NB[id] || (NB[id] = { open: null, fm: null, q: "", lastQ: "", route: "" });
  if (st.route !== route){ st.open = null; st.fm = null; st.route = route; }
  st.sel = {};
  fbMenuFields(spec).forEach(f => { st.sel[String(f.id)] = fbVals(f); });
  const want = String((spec.search && spec.search.value) || "");
  if (st.q === st.lastQ || st.q == null) st.q = want;
  st.lastQ = want;
  if (spec.sort) st.sort = String(spec.sort.value || "");
  const named = (spec.fields || []).filter(f => f.menu === false && fbInForce(f));
  const tu = fbNewSpec(spec, named);
  st.tu = tu;
  tuFilterBarBind(id, { state: () => NB[id], spec: () => NB[id].tu, change: (kind, arg) => fbNewChange(id, kind, arg),
    clear: () => { NB[id].open = null; NB[id].fm = null; return spec.on.clear(); } });
  if (!tu.search && !tu.dims.length && !tu.sort && !named.length) return "";
  return tuFilterBar(tu, st, id).replace('<div class="tf" ', '<div class="tf tf-fbb" ');
}

function fbNewChange(id, kind, arg){
  const st = NB[id], spec = FB[id];
  if (!st || !spec || st.route !== fbNewRoute()) return;
  if (kind === "dim"){
    const f = fbMenuFields(spec).find(x => !fbSame(st.sel[String(x.id)] || [], fbVals(x)));
    if (!f) return fbPaint(spec, null);
    let vals = (st.sel[String(f.id)] || []).map(String);
    /* A SINGLE CHOICE UNTICKED GOES BACK TO ITS DEFAULT, as the old menu did: it never offered "none" on a field with one. */
    if (!vals.length && !f.multi && fbHasDef(f)) vals = f.def.map(String);
    if (fbSame(vals, fbVals(f))) return fbPaint(spec, null);
    return spec.on.set(f.id, vals);
  }
  if (kind === "pin"){
    const f = (spec.fields || []).find(x => String(x.id) === String(arg));
    return f ? spec.on.set(f.id, fbHasDef(f) ? f.def.map(String) : []) : fbPaint(spec, null);
  }
  if (kind === "sort"){ if (spec.on.sort) return spec.on.sort(st.sort); return; }
  if (kind === "q"){
    if (!spec.search || !spec.on.search) return;
    /* A live search commits on every pause; a server-read search was committed by Enter, trimmed, as the old box did. */
    const text = spec.search.live ? st.q : String(st.q || "").trim();
    st.lastQ = st.q;
    return spec.on.search(text);
  }
  return fbPaint(spec, null);
}

/* THE SEGMENTED VIEW STRIPS (`.qtabs`) AS THE MOCKUP'S QUIET SAVED-VIEW TABS, in the New UI: the same buttons with the same
   `data-*` the page's own delegated handlers read, redrawn as `tuViewTabs` draws a view (underline, muted count). Off, or without
   `team-ui.js`, the markup is returned untouched. */
function viewTabs(html){
  if (!(typeof tuNewUi === "function" && tuNewUi())) return html;
  return String(html).replace(/<div class="qtabs"( role="tablist" aria-label="[^"]*")>([\s\S]*?)<\/div>/, (m, label, inner) =>
    `<div class="tu-fb-views tu-fbq"${label}>${inner.replace(/<button class="qtab((?: [a-z]+)*)"([^>]*)>/g, (b, cls, rest) => {
      const on = /\bon\b/.test(cls);
      const tone = cls.replace(/\bon\b/, "").trim();
      return `<button${/ type="/.test(rest) ? "" : ' type="button"'} class="tu-qv${tone ? " " + tone : ""}"${rest} aria-pressed="${on}">`;
    }).replace(/<span class="n">/g, '<span class="tu-fb-n">')}</div>`);
}

function filterBar(spec){
  FB[spec.id] = spec;
  if (fbNewOn(spec)) return fbNewBar(spec);
  const id = esc(spec.id);
  const open = fbOpenOf(spec.id);
  const n = (spec.fields || []).filter(fbInForce).length;
  const s = spec.search;
  const search = s ? `<label class="fb-s"${s.tip ? ` data-tip="${esc(s.tip)}"` : ""}>${FB_ICON.search}<input type="search"
    data-fb-search="${id}" data-keep="fb:${id}:search" placeholder="${esc(s.placeholder || "Search")}"
    aria-label="${esc(s.label || "Search")}" value="${esc(s.value || "")}" spellcheck="false" autocomplete="off"></label>` : "";
  const filter = (spec.fields || []).some(f => f.menu !== false)
    ? `<span class="dd fb-a"><button type="button" class="ddb fb-b" data-fb-open="${id}|filter" data-keep="fb:${id}:filter"
        aria-haspopup="dialog" aria-expanded="${!!(open && open.from === "filter")}" aria-label="Filter${n ? `, ${n} set` : ""}">${
        FB_ICON.filter}<span class="fb-w">Filter</span>${n ? `<span class="cnt">${n}</span>` : ""}</button>${
        open && open.from === "filter" ? fbMenu(spec, open) : ""}</span>` : "";
  const sort = spec.sort
    ? `<span class="dd fb-a"><button type="button" class="ddb fb-b fb-sortb" data-fb-open="${id}|sort" data-keep="fb:${id}:sort"
        aria-haspopup="dialog" aria-expanded="${!!(open && open.from === "sort")}" aria-label="Sort: ${esc(fbSortWords(spec))}">${
        FB_ICON.sort}<span class="fb-w"><span class="ddk">Sort</span> ${esc(fbSortWords(spec))}</span>${
        fbSorted(spec) ? `<span class="cnt fb-sortn">1</span>` : ""}</button>${open && open.from === "sort" ? fbMenu(spec, open) : ""}</span>` : "";
  const count = spec.count ? `<span class="fb-n">${spec.count}</span>` : "";
  const chips = fbChips(spec);
  if (!search && !filter && !sort && !chips) return "";
  /* THE CHIPS SIT ON THE BUTTONS' ROW, to the right of Filter and Sort (the operator's
     call): a strip of its own under the row read as a second control bar, and the default chip
     ("Scope is in scope") looked like a selector detached from the button that edits it. The
     count keeps the row's far end; on a phone the chips drop to a sideways strip under it
     (`fleet.css`). */
  return `<div class="fb" data-fb="${id}"><div class="fb-row">${search}${filter}${sort}${chips}${count}</div></div>`;
}

/* AN EMPTY LIST SAYS WHY (the mockup's sixth rule): each filter in force by name, a way to remove
   each one, and Clear. With nothing in force it is the caller's own sentence (`bare`), because an
   empty view with no filter on it is a fact about the view and not about a filter. */
function filterEmpty(id, o){
  const spec = FB[id];
  const opts = o || {};
  if (!spec) return opts.bare || "";
  const parts = (spec.fields || []).filter(fbInForce)
    .map(f => ({ rm: `${esc(spec.id)}|${fbEnc(f.id)}`, t: f.menu === false && f.said ? f.said : f.flag ? fbSummary(f) : `${f.label} is ${fbSummary(f)}` }));
  if (spec.search && spec.search.value){
    parts.push({ rm: `${esc(spec.id)}|__search`, t: `${spec.search.said || "Matching"} “${spec.search.value}”` });
  }
  if (!parts.length) return opts.bare || "";
  const inside = (spec.fields || []).filter(fbAtDefault).map(f => `${f.label.toLowerCase()} ${fbSummary(f)}`).join(" and ");
  const noun = spec.noun || ["row", "rows"];
  return `<div class="fb-none"><p class="fb-none-h">No ${esc(noun[1])} match these filters.</p>
    <p>${parts.map(p => esc(p.t)).join(" and ")}${inside ? `, inside ${esc(inside)}` : ""}${
      opts.view ? `, in the ${esc(opts.view)} view` : ""}.${opts.lead ? ` ${opts.lead}` : ""} Remove one to widen the list.</p>
    <div class="fb-none-a">${parts.map(p => `<button type="button" class="act" data-fb-rm="${p.rm}">Remove ${esc(p.t)}</button>`).join("")}<button
      type="button" class="act primary" data-fb-clear="${esc(spec.id)}">Clear filters</button></div></div>`;
}

/* ── driving it ── */

/* REPAINT, THEN PUT THE CARET WHERE THE READER'S HANDS ARE. The page's own paint when it gave one
   (a patch, which keeps the element under the caret), else a render of the route in hand. */
function fbPaint(spec, keep){
  if (spec && spec.on && spec.on.paint) spec.on.paint(); else render(openRoute());
  if (!keep || !main) return;
  const el = main.querySelector(`[data-keep="${keep}"]`);
  if (el && el.focus) el.focus({ preventScroll: true });
}
/* WHERE FOCUS GOES WHEN A MENU OPENS: the find box on a desk, the first row in a sheet — the phone
   keyboard is not what a reader who tapped Filter asked for. */
function fbFirst(id){
  if (!main || !main.querySelector) return null;
  const find = !sheetMode() && main.querySelector(`[data-fb-find="${id}"]`);
  return find || main.querySelector(`[data-fb-mi="${id}"]`);
}
function fbOpenMenu(id, from, at){
  const spec = FB[id];
  if (!spec) return;
  FB_OPEN = { id, kind: (location.hash.slice(1) || "board").split(":")[0], from, at: at || "", q: "" };
  fbPaint(spec, null);
  const first = fbFirst(id);
  if (first && first.focus) first.focus({ preventScroll: true });
}
/* CLOSING HANDS FOCUS BACK TO THE BUTTON THAT OPENED IT, the rule every overlay here keeps. */
function fbClose(focusBack){
  if (!FB_OPEN) return;
  const was = FB_OPEN;
  FB_OPEN = null;
  fbPaint(FB[was.id], focusBack ? `fb:${was.id}:${was.from}` : null);
}
function fbToggle(f, v){
  if (f.flag) return fbVals(f).length ? [] : ["on"];
  const sel = fbVals(f);
  if (f.multi) return sel.includes(v) ? sel.filter(x => x !== v) : sel.concat([v]);
  if (sel.includes(v)) return fbHasDef(f) ? sel : [];
  return [v];
}
/* THE ARROWS WALK THE MENU'S ROWS; Home and End go to either end. */
function fbStep(id, from, key){
  if (!main || !main.querySelectorAll) return;
  const rows = Array.prototype.slice.call(main.querySelectorAll(`[data-fb-mi="${id}"]`));
  if (!rows.length) return;
  const at = rows.indexOf(from);
  const next = key === "Home" ? 0 : key === "End" ? rows.length - 1
    : key === "ArrowDown" ? (at < 0 ? 0 : Math.min(rows.length - 1, at + 1)) : Math.max(0, at - 1);
  if (key === "ArrowUp" && at <= 0){
    const find = main.querySelector(`[data-fb-find="${id}"]`);
    if (find && !sheetMode()) return find.focus();
  }
  rows[next].focus();
}
function fbAt(e, attr){
  const el = e.target.closest ? e.target.closest(`[${attr}]`) : null;
  if (el) el.__fb = attr;
  return el;
}

/* Geometry with a counted label. Never a percentage of progress, and never a projection. */
function bar(p){
  const segs = [["complete", p.done], ["flight", p.flight], ["unproven", p.unproven], ["idle", p.idle]];
  const tot = p.nsl || 1;
  const fill = segs.filter(([, n]) => n > 0)
    .map(([k, n]) => `<i class="seg-${k}" style="width:${(n / tot * 100).toFixed(2)}%"></i>`).join("");
  const parts = [];
  if (p.done) parts.push(`${p.done} done`);
  if (p.flight) parts.push(`${p.flight} in flight`);
  if (p.unproven) parts.push(`${p.unproven} awaiting proof`);
  if (p.idle) parts.push(`${p.idle} not started`);
  return `<div class="barwrap"><div class="bar">${fill}</div>
    <div class="barlab">${p.nsl ? parts.join(" · ") : "no slices cut"}</div></div>`;
}
/* THE FIVE READINGS WERE A CLOSED SET WITH A HOLE IN IT. A program every one of whose open cuts
   comes after an unfinished cut read `idle` — the same word as a program nobody has picked up —
   and the two are different facts: one is waiting on a decision, the other is ordered behind
   work somewhere else.
   The sixth reading is derived, never carried: `blockedSlices` reads the `blockedBy` the
   payload already holds per slice, so this adds a reading and not a field.

   IT SITS BELOW `flight`, and that order is the claim. A program with something in flight is
   moving whatever its graph says, and a chip about the order would be arguing with the row's
   own counts. It sits ABOVE `unproven` and `idle` because both of those describe a
   program somebody could act on today, which this one is not.

   THE WORD IS NOT "blocked", AND THAT IS DELIBERATE. The people reading this board also work a
   tracker whose own workflow positions are called `Blocked · decision` and `Blocked · action` —
   states a human parks an issue in. This is a different noun sharing an English word: it is a
   reading over the slice graph, and nothing here has been parked by anybody.

   AND IT IS NOT "nothing can start" ANY MORE (ENG-10638). A slice's `Depends on` ORDERS work and
   never withholds it: a PRD dispatches once its own `depends_on` and `blockedBy` are met,
   whatever the cuts around it read. "after other slices" states the order without claiming a
   block the dispatcher does not make.

   The chip NAMES THE CUTS AND WHAT THEY WAIT ON. The word alone would send the reader into the
   program page to find out waiting on what — which is the trip the chip exists to save. */
/* ── the ordering seam: Reorder mode, present only when a host injects `REORDER` ──────────── */

/* THE AUTHORED ORDER, READ OFF THE PAYLOAD EVERY PAGE ALREADY CARRIES — off `authored`, THE NUMBER
   A PERSON WROTE ON THE PROGRAM, and never off the resolved `rank`/`rankSrc` (ENG-10673).

   It used to be read off `rankSrc === "authored"`, on the argument that `board.py`'s own word for
   "a person placed THIS program" was already on every row. It was not: `ranks()`'s UP pass hands
   a placed program the LOWEST number any cut inside it resolved to, and when that cut is a
   prerequisite of somebody else's #1 the program reads `rank: 1, rankSrc: "slice"` — the
   resolution, truthfully, and the person's own placement nowhere on the wire. Measured on the
   production plan: `PG-21` placed at 5, resolved to 2 through `SL-135`, drawn under
   the "Not ranked" line with a `not ranked` chip — and because every write here is the WHOLE
   order with absent ids cleared, the next drag of any other row withdrew it. `authored` is the
   number itself, `0` for nobody, stamped on every program; a payload from before it carried the
   field (a hand-built one, a standalone page over an older `board.py`) is read the old way, which
   is exactly as right as it ever was for a program nothing pulled up. */
function authoredOf(p){
  if (p.authored !== undefined && p.authored !== null) return Number(p.authored) || 0;
  return p.rankSrc === "authored" ? (Number(p.rank) || 0) : 0;
}
const isPlaced = p => authoredOf(p) > 0;
/* THE TWO ORDERS EITHER SIDE OF THE LINE. Placed programs sit in the person's own order, and
   nothing else may reorder them — a tie is impossible (`declare` writes list positions) and the id
   only breaks one a hand-built payload could carry. Unplaced programs sit by inherited urgency,
   the most urgent first, then id: the same reading `applyFilters` gives the resting list, so
   entering Reorder mode moves no row the reader was looking at. */
const byAuthored = (a, b) => (authoredOf(a) - authoredOf(b)) || a.id.localeCompare(b.id);
const byUrgency = (a, b) => { const x = a.rank || 999, y = b.rank || 999;
  return x < y ? -1 : x > y ? 1 : a.id.localeCompare(b.id); };
/* THE PROGRAMS IN THE PLAN. Every list, count and reorder on this page reads these; the parked
   two — waived, withdrawn — are drawn by `parkedSection` at the foot and nowhere else. A parked
   program that a person had placed KEEPS that placement through every save — a save is scoped to
   the rows Reorder mode lists (ENG-10692), and it used to clear this one unseen — and reads no
   priority while it is parked (`priorityOf`). */
const activePrograms = () => D.programs.filter(p => !isParked(p));
/* HOW MANY PROGRAMS, SAID ONCE (ENG-10589). The Programs list printed the plan (16) and the
   Knowledge hub printed the register (22), both under the word "programs"; the difference was
   the parked ones, which the list draws at the foot and out of its counts. Both surfaces now
   print both figures from this one reading, so neither can be read as the other's mistake. */
function programTally(){
  return { all: D.programs.length, inPlay: activePrograms().length };
}
/* THE CUTS A PROGRAM KEPT, AND HOW ITS PROGRESS IS COUNTED (ENG-10589). A withdrawn cut leaves
   the completion arithmetic — `rollup.board` reads a program proven over one — so a fraction
   whose denominator still counted it ("1 of 2 slices done" under a proven chip, PG-12 on the
   production board) could never reach its own denominator. The row and the program page both
   count over the kept cuts and name the withdrawn ones beside the fraction. `withdrawnSlices`
   is derived on the wire and on the store's rebuild alike; a payload from before it existed
   reads as keeping every cut, which is what it always said. */
function keptCuts(p){
  const withdrawn = Number(p.withdrawnSlices) || 0;
  return { kept: Math.max(0, (Number(p.nsl) || 0) - withdrawn), withdrawn: withdrawn };
}
function slicesDone(p, tail){
  const c = keptCuts(p);
  if (!c.kept && !c.withdrawn) return "—";
  return `${p.done} of ${c.kept}${tail || ""}`;
}
/* THE WITHDRAWN CUTS, NAMED BESIDE THE FRACTION THEY ARE OUT OF — or nothing. */
function withdrawnNote(p){
  const c = keptCuts(p);
  return c.withdrawn ? `<span class="wd">${c.withdrawn} withdrawn</span>` : "";
}
function reorderPlaced(){
  return activePrograms().filter(isPlaced).sort(byAuthored);
}
function reorderUnplaced(){
  return activePrograms().filter(p => !isPlaced(p)).sort(byUrgency);
}
/* The order as the server last confirmed it — what the payload says, top to bottom. */
const reorderIds = () => reorderPlaced().map(p => p.id);

/* ══ THE DRAFT. Reorder mode edits a COPY of the order and writes it ONCE, on Save (ENG-10673).

   It used to write on every gesture: a drop, an Alt+arrow, an Alt+Enter each POSTed the whole
   order, re-read the board and repainted the list under the reader's hands. Twenty programs and
   most of them unplaced is twenty writes to get one from the bottom to the top — each a lease
   dispatched against an order nobody meant yet — and a failed one mid-sequence left the list
   showing neither what was asked for nor what was stored. So the mode holds `RZ_DRAFT`, the
   list of placed ids as the reader is arranging it, against `RZ_SAVED`, the list as it was when
   the mode opened (or was last saved); `rzDirty` is whether the two differ, which is what the
   bar says and what enables Save. Every act below — a drop, a control, a typed position, a
   key — edits the draft and re-renders; nothing reaches `REORDER` until `commitOrder`. */
let RZ_DRAFT = null;
let RZ_SAVED = null;
/* THE ORDER THE DRAFT WAS BASED ON, AND WHAT HAPPENS WHEN SOMEBODY ELSE SAVED IN BETWEEN
   (ENG-10701, K-01). Two windows in Reorder mode both used to say "Order saved." — the second
   silently wrote its stale draft over the first. The payload carries the order's revision
   (`rankOrder`, stamped by the service); the draft remembers it in `RZ_BASE` and the save sends
   it, so the service refuses a save whose base is gone (409) and names who changed the order and
   when. `RZ_CONFLICT` is that refusal — or the same fact learned early, when a newer order arrives
   while the draft is open — and the bar offers the two honest ways on: show their order (keeping
   this draft listed beside it, `RZ_MINE`) or save this one over it deliberately. */
let RZ_BASE = null;
let RZ_CONFLICT = null;
let RZ_MINE = null;
/* THE ONE ROW IN THE TAB ORDER (ENG-10701, K-05). The list is a single Tab stop: this row holds
   `tabindex="0"`, every other row and every control inside a row `-1`, and the arrow keys walk it.
   A row per Tab stop, with its box and five buttons as five more, made reaching the foot of twenty
   programs 95 Tabs. It is also the row whose full controls a phone shows (`rz-on`). */
let RZ_ACTIVE = "";
/* A COPY, always: every editor below splices, and the draft is compared against `RZ_SAVED`
   afterwards — an editor handed the array itself would make `rzDirty` compare a thing with
   itself. Out of the mode this is the confirmed order, which is what `commitOrder`'s callers
   from a host (`tests` publish it) expect to be reading. */
function draftOrder(){
  return (RZ_DRAFT || reorderIds()).slice();
}
function draftPlaced(){
  const by = Object.create(null);
  activePrograms().forEach(p => { by[p.id] = p; });
  return draftOrder().map(id => by[id]).filter(Boolean);
}
function draftUnplaced(){
  const placed = new Set(draftOrder());
  return activePrograms().filter(p => !placed.has(p.id)).sort(byUrgency);
}
function rzDirty(){
  return RZ_DRAFT !== null && !reorderSame(RZ_DRAFT, RZ_SAVED || []);
}
/* What the live region says on the way in, for a screen reader: the keys `keydown` below acts on.
   It used to promise "Up or Down moves the focused row" and "Escape leaves", neither of which held
   on every row (ENG-10701, K-10); the visible line (`rzLead`) teaches the ways a hand moves a row. */
const RZ_ENTERED = "Reorder mode. The arrow keys choose a program; Alt with an arrow moves it one place, "
  + "Alt with Home or End moves it to the top or bottom of your order, and a number puts it at that "
  + "position. Nothing is saved until you press Save order.";
/* ONE SHORT LINE PER ROW, for a screen reader (ENG-10701, RK-09): every row used to be described by
   the whole shortcuts paragraph, read again on every arrow step. The way in is said once (above). */
const RZ_ROW_HELP = "Alt with an arrow moves it one place, Alt with Home or End to the top or bottom, "
  + "a number to that position; Delete takes it out.";
/* WHO IS READING, when the host knows (ENG-10701, RK-06) — so an order this same person saved in
   another tab is "you", not an email address reported as somebody else's. */
let RZ_VIEWER = "";
function viewer(email){
  const was = RZ_VIEWER;
  RZ_VIEWER = email ? String(email).trim() : "";
  if (was === RZ_VIEWER) return;
  /* WHO IS READING CHANGED THE NARROWED LIST (PRD 0839, design D8). The viewer arrives from
     `/api/status` AFTER the board's first render, so the board repaints when it lands — otherwise
     the list would stay unnarrowed until the next navigation. `mine` is inert until then (an
     unknown viewer shows every program), so there is no empty flash. Guarded by route, so a status
     landing on another page repaints nothing. */
  if (D !== null && routeParts(openRoute())[0] === BOARD_ROUTE) render(openRoute());
}
function rzEnter(focusId){
  REORDER_MODE = true;
  RZ_DRAFT = reorderIds();
  RZ_SAVED = RZ_DRAFT.slice();
  RZ_BASE = orderRevision();
  RZ_CONFLICT = null;
  RZ_MINE = null;
  RZ_ACTIVE = focusId || "";
  REORDER_ERR = null;
  REORDER_ANNOUNCE = RZ_ENTERED;
}
/* Out, discarding whatever was not saved — `Cancel`'s act, and `Escape`'s once the draft is
   clean. A drag or a long-press in flight goes with it. */
function rzLeave(){
  REORDER_MODE = false;
  RZ_DRAFT = null;
  RZ_SAVED = null;
  RZ_BASE = null;
  RZ_CONFLICT = null;
  RZ_MINE = null;
  RZ_ACTIVE = "";
  REORDER_ERR = null;
  REORDER_ANNOUNCE = "";
  rzDisarm();
  rzEnd(false);
}
/* The order revision the payload was read at, or `null` from a payload that carries none (the
   standalone page, a service from before `rankOrder`) — and then the save sends no base at all. */
function orderRevision(){
  const o = D && D.rankOrder;
  const n = o ? Number(o.revision) : NaN;
  return Number.isFinite(n) ? n : null;
}

function reorderToggle(){
  if (!REORDER || REORDER_MODE) return "";
  return `<button class="act" type="button" data-rz-toggle data-keep="rz-toggle">Reorder</button>`;
}

/* THE BAR THAT SAYS WHETHER THE ORDER IS SAVED, AND SAVES IT. Sticky to the BOTTOM of the
   viewport rather than the top: the masthead is already sticky at the top and its height is the
   viewport's business (two rows on a phone), so a second top-stuck bar would either hide under
   it or have to measure it; the bottom is free, it is where a thumb rests, and it stays in view
   however far down a twenty-row list the reader has scrolled. `Cancel` carries `data-rz-toggle`
   because it IS the other half of the Reorder button — the same control in the other state — so
   the caret that was on `Reorder` lands on `Cancel` and comes back again, through one `data-keep`.
   `Save order` is enabled only by a draft that differs from what is stored: a save of nothing is a
   write nobody asked for. */
function reorderBar(said){
  const placed = draftPlaced().length;
  const total = activePrograms().length;
  const busy = REORDER_BUSY !== "";
  const dirty = rzDirty();
  const state = busy ? "Saving…" : dirty ? "Changes not saved yet" : "No changes yet";
  /* WHAT HAPPENED TO THE LAST ACT IS SAID IN THE BAR, next to Save (ENG-10701, K-03, K-07). The
     live line and a failed save's sentence both used to sit above the list — 4,000 px away from
     the Save a person had just pressed on a phone, and scrolled off screen after a move at any
     width. The bar is stuck to the bottom of the viewport, so this is where the person is. */
  return `<div class="rz-bar" data-rz-bar role="region" aria-label="Save or cancel the reorder">
    ${rzConflictHtml()}${reorderError()}
    <div class="lgn" id="rz-live" aria-live="polite">${said === RZ_ENTERED
      /* THE WAY IN IS FOR A SCREEN READER. Drawn, it filled a third of a phone above Save; the line
         above the list (`rzLead`) is what a sighted reader is taught by. */
      ? `<span class="rz-quiet">${esc(said)}</span>` : esc(said || "")}</div>
    <span class="rz-state${dirty && !busy ? " dirty" : ""}" data-rz-state="${busy ? "busy" : dirty ? "dirty" : "clean"}">${state}</span>
    <span class="showing">${placed} of ${total} in your order</span>
    <button class="act primary" type="button" data-rz-save data-keep="rz-save"${dirty && !busy ? "" : " disabled"}>Save order</button>
    <button class="act" type="button" data-rz-toggle data-keep="rz-toggle"${busy ? " disabled" : ""}>Cancel</button>
    <span class="chip" id="rz-how" tabindex="0" data-tip="${RZ_HOW}" aria-label="${RZ_HOW}">shortcuts</span>
  </div>`;
}

/* A FAILED SAVE SAYS SO AND KEEPS THE DRAFT — the reader's work is on screen, the bar still says
   it is unsaved, and Save is still there to press. The old wording ("what is on screen is what
   was last confirmed") described a mode that threw the edit away; this one does not.

   IN A PERSON'S WORDS (ENG-10701, K-07). It used to print the host's sentence verbatim — "the
   request did not reach the API: " followed by the browser's own fetch error, "502 upstream unreachable: <urlopen error …> —
   and the body was not this API's JSON at all". `rzFailure` turns the refusal into what happened
   to the person's order; the host's own words stay one hover away, under "details". */
function reorderError(){
  if (!REORDER_ERR) return "";
  const detail = REORDER_ERR.detail
    ? ` <span class="chip" tabindex="0" data-tip="${esc(REORDER_ERR.detail)}">details</span>` : "";
  return `<p class="rz-note rz-fail" role="alert" data-rz-fail><b>The order was not saved.</b>
    ${esc(REORDER_ERR.text)} Your changes are still here &mdash; press Save order to try again.${detail}</p>`;
}
function rzFailure(err){
  const status = Number(err && err.status) || 0;
  const code = String((err && err.code) || "");
  const detail = err && err.message ? String(err.message) : "";
  if (code === "unreachable" || status === 502 || status === 503 || status === 504){
    return { text: "Fleet could not be reached.", detail: detail };
  }
  if (code === "not-json" || status === 401 || status === 403){
    return { text: "Fleet did not accept the request as you — you may have been signed out; sign in again in another tab.", detail: detail };
  }
  if (status >= 500) return { text: "Fleet ran into an error while saving it.", detail: detail };
  if (status >= 400) return { text: `Fleet refused this order${detail ? ": " + detail : "."}`, detail: "" };
  return { text: "The save did not finish.", detail: detail };
}

/* WHO CHANGED THE ORDER, AND WHEN — the refusal's own facts, said once in the bar. */
function rzWhen(at){
  const d = at ? new Date(at) : null;
  if (!d || !Number.isFinite(d.getTime())) return "";
  const hm = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return new Date().toDateString() === d.toDateString()
    ? ` at ${hm}` : ` on ${d.toLocaleDateString([], { month: "short", day: "numeric" })} at ${hm}`;
}
function rzYou(c){ return !!(RZ_VIEWER && c && c.changedBy && String(c.changedBy) === RZ_VIEWER); }
function rzWho(c){ return !c || !c.changedBy ? "Someone" : rzYou(c) ? "You" : String(c.changedBy); }
/* "X changed the order at 07:41" — or, when X is the reader in another tab, said so. */
function rzChanged(c){
  return `${rzWho(c)} changed the order${rzYou(c) ? " in another tab" : ""}${rzWhen(c && c.changedAt)}`;
}
function rzConflictHtml(){
  const c = RZ_CONFLICT;
  if (!c) return "";
  const off = REORDER_BUSY !== "" ? " disabled" : "";
  const theirs = rzYou(c) ? "it" : "theirs";
  const why = c.early ? `while you were editing, so saving yours now would replace ${theirs}.`
                      : "after you started editing, so your order was not saved.";
  return `<div class="rz-note rz-conflict" role="alert" data-rz-conflict>
    <p><b>${esc(rzChanged(c))}</b> ${why} Your changes are still here.</p>
    <span class="rz-note-acts">
      <button class="act" type="button" data-rz-theirs data-keep="rz-theirs"${off}>${rzYou(c) ? "Show that order" : "Show their order"}</button>
      <button class="act" type="button" data-rz-over data-keep="rz-over"${off}>Save mine over it</button></span>
  </div>`;
}

/* What a stale save's refusal says, read off the host's error: `order-changed`, and the revision
   that replaced the base. Anything else is a failure, not a conflict. */
function rzStale(err){
  const p = err && err.code === "order-changed" ? (err.detail || {}) : null;
  if (!p || !Number.isFinite(Number(p.revision))) return null;
  return { revision: Number(p.revision), changedBy: p.changedBy || null, changedAt: p.changedAt || null,
           order: Array.isArray(p.order) ? p.order.map(String) : [],
           reload: typeof err.reload === "function" ? err.reload : null, early: false };
}

/* THEIR ORDER, LOADED — read again from the service when the host can, so the whole list (every
   program's placement, not only the ids the refusal named) is the one now stored — and this
   person's draft kept beside it. `RZ_BASE` moves to their revision FIRST, so the reboot this
   triggers does not raise the same conflict again. */
function rzTakeTheirs(){
  const c = RZ_CONFLICT;
  if (!c || REORDER_BUSY) return;
  const mine = draftOrder();
  RZ_BASE = c.revision;
  REORDER_BUSY = "theirs";
  rzRerender();
  const land = () => {
    REORDER_BUSY = "";
    const inPlay = new Set(activePrograms().map(p => p.id));
    const theirs = orderRevision() === c.revision ? reorderIds() : c.order.filter(id => inPlay.has(id));
    RZ_DRAFT = theirs.slice();
    RZ_SAVED = theirs.slice();
    RZ_CONFLICT = null;
    RZ_MINE = mine.filter(id => inPlay.has(id));
    REORDER_ERR = null;
    REORDER_ANNOUNCE = `Showing the order ${rzYou(c) ? "you saved in another tab" : `${rzWho(c)} saved`}; `
      + "yours is above the list, to compare.";
    rzRerender();
    /* AND THE COMPARISON IS WHERE THE PERSON CAN SEE IT (ENG-10701, RK-05): on a phone it sat a
       screen above the bar they had just pressed, with the sentence that named it clipped. The
       region scrolls into view and the caret lands on the way back to their own order. */
    const box = main && main.querySelector('[data-keep="rz-mine-box"]');
    if (box && box.scrollIntoView) box.scrollIntoView({ block: "start" });
    const back = main && main.querySelector('[data-keep="rz-mine"]');
    if (back && back.focus) back.focus({ preventScroll: true });
  };
  Promise.resolve().then(() => (c.reload ? c.reload() : null)).then(land, land);
}
/* This person's order back in the list, over theirs — a deliberate act, and Save then replaces
   theirs knowingly: the base is their revision. The caret goes to Save, the act this one leads to. */
function rzUseMine(){
  if (!RZ_MINE) return;
  const inPlay = new Set(activePrograms().map(p => p.id));
  RZ_DRAFT = RZ_MINE.filter(id => inPlay.has(id));
  RZ_MINE = null;
  REORDER_ANNOUNCE = "Your order is back in the list. Save order replaces the saved one.";
  rzRerender();
  const save = main && main.querySelector('[data-keep="rz-save"]');
  if (save && save.focus) save.focus({ preventScroll: true });
}

/* A NEWER ORDER, NAMED WHILE A DRAFT IS OPEN ON THE LIST (ENG-10701, RK-07). The list is not
   replaced under an unsaved draft — `busy()` holds the reload back — so the host reads the order's
   head instead and hands it here; a revision past the draft's base is the conflict, said in the bar
   now rather than on Save. Only the bar is repainted: the rows, and a position box somebody may be
   typing into, are left exactly as they are. */
function orderHead(head){
  if (!REORDER_MODE || REORDER_BUSY || !rzDirty() || !head) return;
  const now = Number(head.revision);
  if (!Number.isFinite(now) || RZ_BASE === null || now === RZ_BASE) return;
  if (RZ_CONFLICT && RZ_CONFLICT.revision === now) return;
  RZ_CONFLICT = { revision: now, changedBy: head.changedBy || null, changedAt: head.changedAt || null,
                  order: Array.isArray(head.order) ? head.order.map(String) : [], reload: null, early: true };
  REORDER_ANNOUNCE = `${rzChanged(RZ_CONFLICT)} while you were editing. Your changes are still here.`;
  rzPaintBar();
}
function rzPaintBar(){
  const bar = main && main.querySelector("[data-rz-bar]");
  if (!bar || !("outerHTML" in bar)){ rzRerender(); return; }
  const keep = focusedKeep();
  bar.outerHTML = reorderBar(REORDER_ANNOUNCE);
  refocus(keep);
}

/* The shortcuts, in the row's own words, behind the chip in the bar. Every act named here is
   one the row also offers as a control, so nothing is reachable only by a key or only by a
   pointer. */
const RZ_HOW = "Move a row with its Top or Place at top button, by typing a number into its position "
  + "box (3 puts it third), or by dragging it: on a touch screen press and hold a row or grab the "
  + "&#8942;&#8942; handle, and the page scrolls while you hold a row near the top or bottom edge. "
  + "From a keyboard the list is one Tab stop: &uarr; and &darr; choose a row, Home and End the first "
  + "and last, Page Up and Page Down ten at a time; Alt with &uarr; or &darr; moves the chosen row one "
  + "place, across the line too, Alt with Home or End moves it to the top or bottom of your order, "
  + "a number (or Enter) opens its position box, Delete takes it out, and Escape leaves. "
  + "Nothing is written until you press Save order.";

/* THE LINES ABOVE THE LIST, while the mode is open (ENG-10701). One sentence that is true on every
   row and at every width (K-10); the parked placements the list does not show, named, so a number
   that skips is never a mystery (K-06); and, after "Show their order", this person's own order for
   comparison with a way to put it back (K-01). */
function rzLead(){
  /* THE KEY THAT MOVES IS ON THE LINE A SIGHTED KEYBOARD USER READS (RK-03): the arrows walk the
     list as on any list, and nothing else on screen said what moves a row. */
  const intro = `<p class="rz-intro" id="rz-intro">Move a row with Top, its position number, a drag, or
    Alt+&uarr;/&darr; from the keyboard &mdash; nothing is saved until you press Save order.</p>
    <span id="rz-row-help" class="rz-quiet">${esc(RZ_ROW_HELP)}</span>`;
  const parked = D.programs.filter(p => isParked(p) && authoredOf(p) > 0).sort(byAuthored);
  const one = parked.length === 1;
  const names = parked.map(p => p.id);
  const listed = names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names.join("");
  const held = parked.length
    ? `<p class="rz-parked" data-rz-parked>${esc(listed)} ${one ? "is parked and keeps its place" : "are parked and keep their places"}
        in your order, so ${one ? "it comes" : "they come"} back where you left ${one ? "it" : "them"}.</p>` : "";
  const mine = RZ_MINE && RZ_MINE.length
    ? `<div class="rz-mine" role="region" aria-label="Your order before you loaded the saved one" data-keep="rz-mine-box">
        <b>Your order, to compare:</b>
        <ol class="rz-mine-list" data-rz-mine-list>${RZ_MINE.map(id =>
          `<li><span class="id">${esc(id)}</span> ${esc((PG[id] && PG[id].name) || "")}</li>`).join("")}</ol>
        <button class="act" type="button" data-rz-mine data-keep="rz-mine">Use my order again</button>
        <button class="act" type="button" data-rz-dismiss data-keep="rz-dismiss">Hide</button></div>` : "";
  return intro + held + mine;
}

/* THE LINE BETWEEN "your order" AND "everything else" IN REORDER MODE — not a second section and
   not a second list, so there is exactly one list container on the mode's page (`viewBoard`'s own
   `.rows`) and the act this line names is a drop ACROSS it, never a drop INTO a different box. At
   rest the same split is two groups of the card (`boardGroup`); here it is drawn always and
   carries `data-rz-boundary`, which `rzAim` scans exactly like a row: dropping above it places or repositions, dropping below it (including into the
   empty space this element's own CSS gives it) unplaces, and that is true even when one side of
   the line currently has nothing on it, which is what makes the very first placement and the
   very last withdrawal possible with nothing but this one element to aim at. */
function boundaryHtml(){
  return `<div class="rz-boundary" data-rz-boundary aria-hidden="true">
    <span>Not in your order</span><i>drop a row below this line to take it out of your order</i></div>`;
}

/* Focus retention across a re-render, generalised from `app.js`'s own `repaint()` — the same
   `data-keep` contract, read back here because a row is markup this file owns and a repaint
   that dropped its own reader's caret mid-act would be the bug this whole seam exists to avoid.
   A CONTROL THAT WENT AWAY HANDS THE CARET TO ITS ROW: `Up` on the row that just reached the top
   is disabled in the next render, and a disabled button cannot hold focus, so the reader would
   otherwise land on the document body with the row they were working on scrolled who knows
   where. Every control names its row (`data-rz-row`) so the fallback has a subject. */
function rzRerender(){
  const on = document.activeElement && document.activeElement.getAttribute ? document.activeElement : null;
  const keep = on ? on.getAttribute("data-keep") : null;
  const row = on ? on.getAttribute("data-rz-row") : null;
  render(location.hash.slice(1) || "board");
  let again = keep && main && main.querySelector(`[data-keep="${keep}"]`);
  if ((!again || again.disabled) && row) again = main && main.querySelector(`[data-keep="rz-card-${row}"]`);
  if (again && again.focus) again.focus({ preventScroll: true });
}

/* THE ROW IT WAS ABOUT, IN VIEW AND HOLDING THE CARET (ENG-10701, K-03). "Place at top" on the
   bottom program sent it to the head of a list that had scrolled far past it, and the page stayed
   where it was — the row gone, a faint line above the list saying where. `block: "nearest"` moves
   the page only when the row is not already in view, and `.row-rz`'s scroll margin keeps it clear
   of the sticky masthead and the Save bar. */
function rzReveal(id, scroll){
  const card = id && main && main.querySelector(`[data-keep="rz-card-${id}"]`);
  if (!card) return;
  if (scroll !== false && card.scrollIntoView) card.scrollIntoView({ block: "nearest" });
  if (card.focus) card.focus({ preventScroll: true });
}
/* THE ARROW KEYS WALK THE LIST (K-05): the rows in the order they are drawn, placed then not, the
   line between them no obstacle. `step` is a count, or "first" / "last". */
const RZ_PAGE = 10;
function rzWalk(from, step){
  const ids = draftPlaced().map(p => p.id).concat(draftUnplaced().map(p => p.id));
  if (!ids.length) return;
  const at = Math.max(0, ids.indexOf(from));
  const to = step === "first" ? 0 : step === "last" ? ids.length - 1
    : Math.min(Math.max(at + step, 0), ids.length - 1);
  if (ids[to] !== RZ_ACTIVE){
    RZ_ACTIVE = ids[to];
    rzRerender();
  }
  rzReveal(ids[to]);
}
/* A NUMBER TYPED ON A ROW opens its position box with that digit in it; Enter puts the row there.
   Enter or Space on the row opens the box as it is, contents selected — the one thing "activate"
   can mean on a row whose place is a number (RK-03: Enter used to take the program out). */
function rzTypeInto(id, digit){
  const box = main && main.querySelector(`[data-keep="rz-pos-${id}"]`);
  if (!box) return;
  if (digit !== undefined) box.value = digit;
  if (box.focus) box.focus();
  if (digit === undefined && box.select) box.select();
}

/* ONE WRITE, THE WHOLE ORDER, ON SAVE — `declareOrder`'s ported discipline: what is sent is the
   full list of placed ids, never a patch, so the server holds an order somebody meant at every
   instant. Busy while the host's promise is in flight, so a second press cannot race the first;
   the error is the host's own sentence, carried without this file knowing what produced it.
   A save that lands closes the mode — the reader asked for this order and has it — and the
   live region says so on the list that now shows it. A save that fails keeps everything: the
   draft, the mode, the caret. */
function commitOrder(order, basedOn){
  if (!REORDER || REORDER_BUSY) return;
  /* THE ROWS THIS SAVE IS ABOUT (ENG-10692): every program the mode listed, above the line and
     below it — `activePrograms`, the same reading `draftPlaced`/`draftUnplaced` split. The host
     sends it as the write's scope, so a placement the mode never showed is left as it is rather
     than cleared by an order that did not name it. And the order sent is only ever programs IN
     that scope: a draft kept while another page was open can outlive a program that has since been
     parked, and placing it would be a claim about a row this save never showed. */
  const scope = activePrograms().map(p => p.id);
  const inPlay = new Set(scope);
  const sending = order.filter(id => inPlay.has(id));
  /* THE REVISION THE DRAFT WAS BASED ON (K-01), or the one a refusal named when the person chose
     to save over it. `null` sends no base, which is the unconditional write it always was. */
  const base = basedOn !== undefined ? basedOn : RZ_BASE;
  REORDER_BUSY = "order";
  REORDER_ERR = null;
  rzRerender();
  Promise.resolve()
    .then(() => REORDER(sending.slice(), scope.slice(), base))
    .then(
      () => {
        REORDER_BUSY = "";
        RZ_SAVED = sending;
        RZ_DRAFT = null;
        REORDER_MODE = false;
        RZ_BASE = null;
        RZ_CONFLICT = null;
        RZ_MINE = null;
        REORDER_ANNOUNCE = NOTIFY ? "" : "Order saved.";
        if (NOTIFY) NOTIFY("<b>Order saved.</b>", "ok");
        rzRerender();
        /* THE CARET WAS ON SAVE, WHICH IS GONE: it lands on the Reorder button, the control the
           mode came from, rather than on the document body with the list scrolled who knows
           where. */
        const back = main && main.querySelector('[data-keep="rz-toggle"]');
        if (back && back.focus) back.focus({ preventScroll: true });
      },
      err => {
        REORDER_BUSY = "";
        const stale = rzStale(err);
        if (stale){
          RZ_CONFLICT = stale;
          REORDER_ERR = null;
          REORDER_ANNOUNCE = `${rzChanged(stale)} after you started editing, so your order was not saved. `
            + "Your changes are still here.";
          rzRerender();
          const theirs = main && main.querySelector('[data-keep="rz-theirs"]');
          if (theirs && theirs.focus) theirs.focus({ preventScroll: true });
          return;
        }
        const failed = rzFailure(err);
        if (NOTIFY){
          /* THE HOST SAYS IT, AND THE BAR DOES NOT SAY IT TWICE: its state line still reads
             "Changes not saved yet" and Save is still there to press. */
          REORDER_ERR = null;
          REORDER_ANNOUNCE = "";
          const detail = failed.detail
            ? ` <span class="chip" tabindex="0" data-tip="${esc(failed.detail)}">details</span>` : "";
          NOTIFY(`<b>The order was not saved.</b> ${esc(failed.text)} Your changes are still here &mdash; press Save order to try again.${detail}`, "err");
        } else {
          REORDER_ERR = failed;
          REORDER_ANNOUNCE = `The order was not saved. ${failed.text} Your changes are still here.`;
        }
        rzRerender();
      },
    );
}

/* ══ THE EDITS, each pure over an order and each ending in `rzEdit`, which is the only writer
   of the draft. `orderMovedTo` is the one primitive: the id out, then in at the index, clamped —
   a placement and a move are the same act with a different starting side. */
function orderMovedTo(order, id, at){
  const next = order.filter(other => other !== id);
  const to = Math.min(Math.max(at, 0), next.length);
  next.splice(to, 0, id);
  return next;
}

/* The order with one row moved one place — the arrow-key act, pure over the draft rather than
   over the DOM, which a drag in progress may be moving by hand. */
function reorderMoved(id, by){
  const order = draftOrder();
  const at = order.indexOf(id);
  if (at < 0) return order;
  const to = Math.min(Math.max(at + by, 0), order.length - 1);
  order.splice(at, 1);
  order.splice(to, 0, id);
  return order;
}

/* The order a drop declares. `into` is the list it lands on: "placed" is a move or a placement,
   anything else is a withdrawal — `pDropped`'s exact shape, ported. */
function reorderDropped(id, into, before){
  const order = draftOrder().filter(other => other !== id);
  if (into !== "placed") return order;
  const at = before ? order.indexOf(before) : -1;
  if (at < 0) order.push(id); else order.splice(at, 0, id);
  return order;
}

function reorderSame(one, other){
  return one.length === other.length && one.every((id, at) => id === other[at]);
}

/* The draft, changed — or not: an act that lands where the row already was re-renders (a typed
   box goes back to what it said) and announces nothing, so a mis-aimed grab is silent. */
function rzEdit(next, said, id){
  if (reorderSame(next, draftOrder())){ rzRerender(); return; }
  if (id) RZ_ACTIVE = id;
  RZ_DRAFT = next;
  REORDER_ANNOUNCE = said;
  rzRerender();
  if (id) rzReveal(id);
}

/* THE FIVE CONTROLS ON A PLACED ROW AND THE TWO ON AN UNPLACED ONE, by name. `top` and `bottom`
   are one act for both sides — a placed row moves there, an unplaced one is placed there — which
   is what lets a program at the foot of twenty unplaced ones reach the head of the order in one
   press, the case the operator named. `up`, `down` and `out` are a placed row's own. */
/* EVERY ANNOUNCEMENT SAYS WHERE THE ROW WENT (ENG-10701, K-11): "moved to the top, position 1 of
   7", never "moved at the top" with no position. `keys` is the keyboard's reading of Up and Down,
   which crosses the line the buttons stop at: Alt+Up on an unplaced row places it at the bottom of
   the order, Alt+Down on the last placed row takes it out. */
function rzAct(id, act, keys){
  const order = draftOrder();
  const at = order.indexOf(id);
  const placed = at >= 0;
  const n = placed ? order.length : order.length + 1;
  if (act === "top") return rzEdit(orderMovedTo(order, id, 0), placed
    ? `${id} moved to the top, position 1 of ${n}.` : `${id} placed at the top of your order, position 1 of ${n}.`, id);
  if (act === "bottom") return rzEdit(orderMovedTo(order, id, order.length), placed
    ? `${id} moved to the bottom, position ${n} of ${n}.` : `${id} placed at the bottom of your order, position ${n} of ${n}.`, id);
  if (!placed) return keys && act === "up" ? rzAct(id, "bottom") : undefined;
  if (act === "up") return rzEdit(reorderMoved(id, -1), `${id} moved up to position ${Math.max(at, 1)} of ${n}.`, id);
  if (act === "down" && keys && at === order.length - 1) return rzAct(id, "out");
  if (act === "down") return rzEdit(reorderMoved(id, 1), `${id} moved down to position ${Math.min(at + 2, n)} of ${n}.`, id);
  if (act === "out") return rzEdit(order.filter(other => other !== id), `${id} taken out of your order.`, id);
}

/* A POSITION, TYPED. `3` puts the row third, whichever side of the line it came from; a number
   past the end puts it last, `0` and below first, and anything that is not a number leaves the
   draft alone and puts the box back to what it said. The bound is the draft's own length: a
   placed row can go as far as the last place, an unplaced one to the place after it. */
function rzPosition(id, typed){
  const n = parseInt(String(typed === undefined || typed === null ? "" : typed).trim(), 10);
  if (!isFinite(n)){ rzRerender(); return; }
  const order = draftOrder();
  const placed = order.indexOf(id) >= 0;
  const last = placed ? order.length : order.length + 1;
  const pos = Math.min(Math.max(n, 1), last);
  const next = orderMovedTo(order, id, pos - 1);
  rzEdit(next, `${id} ${placed ? "moved to" : "placed at"} position ${pos} of ${next.length}.`, id);
}

/* ══ THE DRAG, ported from the priorities page's own — pointer events, not the HTML5 API that
   never fires on a touch screen. `setPointerCapture` is what makes this a drag rather than a
   hover: captured, the pointer goes on reporting to the row after it has left it, so a drop
   lands on the row even if the finger lifts somewhere past the edge of the list.

   TWO THINGS IT DID NOT DO, AND NOW DOES (ENG-10673). It never scrolled: a row held at the edge
   of the viewport stayed there, and a list of twenty programs is two to five screens tall, so a
   drag from the foot could reach nothing above the fold — measured, the drop landed on whichever
   unplaced row was at the top of the screen, which reads as "unplaced" and writes nothing. And
   on a phone it began only on the grip, because a finger anywhere else is the reader scrolling —
   which is still true, and is why a press that does not move for a third of a second is now the
   other way to begin one: a scroll starts moving at once, a hold does not. */
let RZ_MARK = null;
let RZD = null;
/* A TOUCH THAT MAY BECOME A DRAG: the row, the pointer and where it was put down, held for
   `RZ_PRESS_MS`. A move before then is a scroll and disarms it; the timer firing makes it `RZD`. */
let RZ_ARMED = null;
let RZ_PRESS = 0;
/* THE AUTO-SCROLL, one timer, rearmed while the pointer stays in an edge zone. `RZ_EDGE` is how
   far from the edge the zone reaches, `RZ_SPEED` how many pixels one tick moves at the very edge
   (proportionally fewer further in), `RZ_TICK` a frame. A timeout rather than an animation frame
   so a run of ticks is a chain a test can see armed and a drop can cut, never a synchronous
   recursion. */
let RZ_SCROLL = 0;
const RZ_PRESS_MS = 350;
const RZ_EDGE = 64;
const RZ_SPEED = 18;
const RZ_TICK = 16;

function rzMark(){
  if (!RZ_MARK){
    RZ_MARK = document.createElement("div");
    RZ_MARK.className = "rz-drop";
    RZ_MARK.setAttribute("aria-hidden", "true");
  }
  return RZ_MARK;
}
function rzUnmark(){
  if (RZ_MARK && RZ_MARK.parentNode) RZ_MARK.parentNode.removeChild(RZ_MARK);
}

/* Where the row would land, over ONE list rather than two: the row (or the boundary line) whose
   top half the pointer has crossed. Measured off rectangles rather than off `e.target`, because
   the pointer is captured to the dragged row and every move reports that row whatever is
   underneath — `pzAim`'s exact reasoning, ported. The boundary is scanned exactly like a row and
   never dragged (it carries no `data-rz-card`, so the exclusion below never has to name it), and
   that is what lets `rzZone` answer "placed" or "unplaced" from ONE element instead of from which
   of two containers the pointer was closest to. */
function rzAim(x, y){
  const list = main && main.querySelector("[data-rz-list]");
  if (!list) return null;
  const markers = Array.prototype.slice.call(list.querySelectorAll("[data-rz-card],[data-rz-boundary]"))
    .filter(el => el !== (RZD && RZD.card));
  let before = null;
  for (const el of markers){
    const rect = el.getBoundingClientRect();
    if (y < rect.top + rect.height / 2){ before = el; break; }
  }
  return { list: list, before: before };
}

/* WHAT A DROP AT `before` MEANS, read off ONE row (or the boundary) rather than off which of two
   containers it landed in. `before === null` is "past everything, including the boundary" —
   which can only be true in the whitespace the boundary's own CSS leaves below it — so it always
   reads as "unplaced", the same answer an empty "Not placed" list used to give a drop it could
   not otherwise measure. Dropping ON the boundary itself is "the last placed position": the line
   sits directly between the two groups, so being asked to land in front of it is being asked to
   land at the bottom of the one above it. */
function rzZone(before){
  if (!before) return { into: "unplaced", beforeId: "" };
  if (before.getAttribute("data-rz-boundary") !== null) return { into: "placed", beforeId: "" };
  const zone = before.getAttribute("data-rz-from");
  return { into: zone, beforeId: zone === "placed" ? before.getAttribute("data-rz-card") : "" };
}

/* The scroll position, read where a browser keeps it and `0` where nothing does. */
function rzScrollTop(){
  return window.scrollY || (document.documentElement && document.documentElement.scrollTop) || 0;
}

/* A drag begins: the row is captured to the pointer and remembers where it was picked up — the
   pointer AND the page's scroll, because the row's translate has to make up for both. `lifted`
   says whether the row has visibly moved; a long-press lifts at once, since the finger under it
   is not going to travel four pixels first. */
function rzBegin(card, e, lifted){
  RZD = { id: card.getAttribute("data-rz-card"), card: card, pointer: e.pointerId,
          x: e.clientX, y: e.clientY, cx: e.clientX, cy: e.clientY, sy: rzScrollTop(),
          lifted: false, aim: null, v: 0 };
  if (card.focus) card.focus({ preventScroll: true });
  if (card.setPointerCapture && e.pointerId !== undefined){
    try { card.setPointerCapture(e.pointerId); } catch (err){ /* a pointer already gone */ }
  }
  if (lifted) rzLift();
}
function rzLift(){
  RZD.lifted = true;
  RZD.card.classList.add("rz-lift");
}
function rzArm(card, e){
  rzDisarm();
  RZ_ARMED = { card: card, pointer: e.pointerId, x: e.clientX, y: e.clientY, e: e };
  RZ_PRESS = setTimeout(() => {
    const armed = RZ_ARMED;
    RZ_ARMED = null;
    RZ_PRESS = 0;
    if (!armed || RZD || !REORDER_MODE || REORDER_BUSY) return;
    rzBegin(armed.card, armed.e, true);
    rzFollow();
  }, RZ_PRESS_MS);
}
function rzDisarm(){
  if (RZ_PRESS) clearTimeout(RZ_PRESS);
  RZ_PRESS = 0;
  RZ_ARMED = null;
}

/* The row under the pointer and the marker where it would land — called on every move AND on
   every scroll tick, because a scroll moves the list under a pointer that has not moved. */
function rzFollow(){
  if (!RZD || !RZD.lifted) return;
  const dx = RZD.cx - RZD.x;
  const dy = RZD.cy - RZD.y + (rzScrollTop() - RZD.sy);
  RZD.card.style.setProperty("transform", "translate(" + dx + "px, " + dy + "px)");
  RZD.aim = rzAim(RZD.cx, RZD.cy);
  if (!RZD.aim) return;
  const mark = rzMark();
  if (RZD.aim.before) RZD.aim.list.insertBefore(mark, RZD.aim.before);
  else RZD.aim.list.appendChild(mark);
}

/* THE EDGE ZONES: `RZ_EDGE` pixels below whatever is stuck to the top of the viewport (the
   masthead) and above whatever is stuck to its bottom (the Save bar), so a row held under either
   still scrolls the list rather than sitting behind it. The speed climbs towards the edge and is
   zero outside the zone; a change from zero to something starts the tick chain, and the chain
   stops itself when the pointer leaves the zone, the page can scroll no further, or the drag ends. */
function rzEdges(){
  const vh = window.innerHeight || 0;
  const mast = document.querySelector(".mast");
  const bar = main && main.querySelector("[data-rz-bar]");
  const top = mast && mast.getBoundingClientRect ? Math.max(0, mast.getBoundingClientRect().bottom) : 0;
  const bottom = bar && bar.getBoundingClientRect ? Math.min(vh, Math.max(top, bar.getBoundingClientRect().top)) : vh;
  return { top: top, bottom: bottom };
}
function rzEdgeScroll(){
  if (!RZD || !RZD.lifted) return;
  const edge = rzEdges();
  let v = 0;
  if (RZD.cy < edge.top + RZ_EDGE) v = -Math.ceil(RZ_SPEED * (1 - Math.max(0, RZD.cy - edge.top) / RZ_EDGE));
  else if (RZD.cy > edge.bottom - RZ_EDGE) v = Math.ceil(RZ_SPEED * (1 - Math.max(0, edge.bottom - RZD.cy) / RZ_EDGE));
  RZD.v = v;
  if (v && !RZ_SCROLL) rzScrollTick();
}
function rzScrollTick(){
  RZ_SCROLL = 0;
  if (!RZD || !RZD.lifted || !RZD.v || typeof window.scrollBy !== "function") return;
  const before = rzScrollTop();
  window.scrollBy(0, RZD.v);
  if (rzScrollTop() === before){ RZD.v = 0; return; }
  rzFollow();
  RZ_SCROLL = setTimeout(rzScrollTick, RZ_TICK);
}
function rzStopScroll(){
  if (RZ_SCROLL) clearTimeout(RZ_SCROLL);
  RZ_SCROLL = 0;
}

document.addEventListener("pointerdown", e => {
  if (!REORDER_MODE || RZD || REORDER_BUSY) return;
  if (e.button !== undefined && e.button !== 0) return;
  if (!e.target.closest) return;
  /* A CONTROL IS NOT A GRAB. The position box and the row's buttons sit on the row, and a
     pointer going down on one of them is that control's own act — taking it would make the
     box unfocusable and the buttons unclickable on the very rows they belong to. */
  if (e.target.closest("[data-rz-pos],[data-rz-act]")) return;
  const card = e.target.closest("[data-rz-card]");
  if (!card) return;
  /* ON TOUCH, THE GRIP BEGINS A DRAG AT ONCE AND THE REST OF THE ROW BEGINS ONE AFTER A HOLD —
     `pzGrip`'s rule, kept, and a second way in beside it. The grip is the only element carrying
     `touch-action:none`, so a finger anywhere else on the row is the reader scrolling until it
     has held still for `RZ_PRESS_MS`; NOT prevented here, so the browser is free to begin that
     scroll, and `rzArm`'s timer is what a scroll cancels by moving first. */
  if (e.pointerType && e.pointerType !== "mouse" && !e.target.closest("[data-rz-grip]")){
    rzArm(card, e);
    return;
  }
  e.preventDefault();
  rzBegin(card, e, false);
});

document.addEventListener("pointermove", e => {
  if (RZ_ARMED && (e.pointerId === undefined || e.pointerId === RZ_ARMED.pointer)){
    if (Math.abs(e.clientX - RZ_ARMED.x) + Math.abs(e.clientY - RZ_ARMED.y) > 8) rzDisarm();
  }
  if (!RZD || (e.pointerId !== undefined && e.pointerId !== RZD.pointer)) return;
  RZD.cx = e.clientX;
  RZD.cy = e.clientY;
  if (!RZD.lifted){
    if (Math.abs(RZD.cx - RZD.x) + Math.abs(RZD.cy - RZD.y) < 4) return;
    rzLift();
  }
  e.preventDefault();
  rzFollow();
  rzEdgeScroll();
});

/* A LIFTED ROW OWNS THE TOUCH. Once a hold has become a drag the browser must not turn the
   finger's next move into a scroll and take the pointer away with `pointercancel` — which is
   what it does to any touch that is not on a `touch-action:none` element. `passive:false` is the
   whole point of this listener: a passive one cannot prevent anything, and the browser treats a
   document-level touch listener as passive unless told otherwise. */
document.addEventListener("touchmove", e => {
  if (RZD && RZD.lifted && e.cancelable) e.preventDefault();
}, { passive: false });
/* And the long-press must not open the browser's own menu on the way to becoming a drag. */
document.addEventListener("contextmenu", e => {
  if (REORDER_MODE && (RZD || RZ_ARMED)) e.preventDefault();
});

function rzEnd(drop){
  rzStopScroll();
  const held = RZD;
  RZD = null;
  rzUnmark();
  if (!held) return;
  if (held.card.releasePointerCapture && held.pointer !== undefined){
    try { held.card.releasePointerCapture(held.pointer); } catch (err){ /* already released */ }
  }
  held.card.classList.remove("rz-lift");
  held.card.style.setProperty("transform", "");
  if (!drop || !held.lifted || !held.aim){ rzRerender(); return; }
  const { into, beforeId } = rzZone(held.aim.before);
  const order = reorderDropped(held.id, into, beforeId);
  const wasPlaced = draftOrder().indexOf(held.id) >= 0;
  const landed = order.indexOf(held.id) + 1;
  rzEdit(order, into === "placed"
    ? `${held.id} ${wasPlaced ? "moved to" : "placed at"} position ${landed} of ${order.length}.`
    : `${held.id} taken out of your order.`, held.id);
}

document.addEventListener("pointerup", e => {
  if (RZ_ARMED && (e.pointerId === undefined || e.pointerId === RZ_ARMED.pointer)) rzDisarm();
  if (RZD && e.pointerId !== undefined && e.pointerId !== RZD.pointer) return;
  rzEnd(true);
});
document.addEventListener("pointercancel", e => {
  if (RZ_ARMED && (e.pointerId === undefined || e.pointerId === RZ_ARMED.pointer)) rzDisarm();
  if (RZD && e.pointerId !== undefined && e.pointerId !== RZD.pointer) return;
  rzEnd(false);
});

/* THE POSITION BOX COMMITS ON CHANGE — a blur after typing, or the Enter the `keydown` listener
   below handles first; both reach `rzPosition`, which is idempotent, so a browser that fires
   `change` on Enter as well as on blur moves the row once. */
document.addEventListener("change", e => {
  if (!e.target.closest) return;
  const box = e.target.closest("[data-rz-pos]");
  if (!box || !REORDER_MODE) return;
  rzPosition(box.getAttribute("data-rz-pos"), box.value);
});



function stateChip(p, where){
  /* The two decisions first: a withdrawn program with every cut complete is still withdrawn,
     and a waived one with nothing in flight is waived rather than "awaiting proof". */
  if (p.state === "withdrawn") return '<span class="chip withdrawn">withdrawn</span>';
  if (p.state === "waived") return '<span class="chip waived">proof waived</span>';
  /* CLOSED BEATS PROVEN: the closing check passed — `closed`, the day it passed, joined onto the row by the host
     from its own record of the check — so the chip says it with no drive read at all. PROD v0.7.141: PG-21 was
     closed and its row still read "proven". */
  if (p.closed) return `<span class="chip complete">closed</span>`;
  if (p.complete) return `<span class="chip complete">${STATE.complete}</span>`;
  /* THE PHASE LEADS (the program lifecycle): shaping, building or closing — one word for where the
     program is in its life, computed by `board.py::program_phase`. A building program says whether
     anything is moving, because "building" alone cannot tell a busy program from a stuck one. A
     payload built before the phase existed carries none and reads exactly as it always did. */
  if (p.phase === "closing") return '<span class="chip complete">closing</span>';
  if (p.phase === "shaping") return '<span class="chip phase-shaping">shaping</span>';
  const pre = p.phase === "building" ? "building &middot; " : "";
  /* THE DRIVE LEADS WHERE THERE IS ONE: `deliveryOf` is the host's one word, so this
     chip and the box on the page cannot say "idle" and "a cycle is running" side by side. */
  const d = deliveryOf(p.id);
  if (d && d.reading === "running") return `<span class="chip flight">${pre}cycle running</span>`;
  if (d && d.reading === "waiting") return `<span class="chip unproven">${pre}${esc(waitWords(d))}</span>`;
  /* A PERSON'S STEP IS SAID ON EVERY CHIP, the row's too (PROD PG-21): "building · driven" stood over PG-21 for a
     day while the one move left was the reader's. The fleet's work landing first is still the fleet's turn. */
  /* AND IT SAYS WHAT IT WAITS ON (the operator, on PG-21): "waiting on the live check", never a bare "waiting on
     you" with nothing to click — the host's short words (`waitingOn`), lower-cased into the chip. */
  if (d && d.reading === "waiting-on-you") return `<span class="chip unproven">${pre}${esc(waitWords(d))}</span>`;
  if (d && d.reading === "fleet-then-you" && where === "row" && pre) return '<span class="chip flight">building</span>';
  if (d && d.reading === "fleet-then-you") return `<span class="chip flight">${pre}fleet, then you</span>`;
  /* ON A PROGRAMS LIST ROW THE DRIVE HAS ITS OWN CHIP (`driveChip`), so "driven" is
     said once, there: between cycles the row's state chip names the phase alone. The program page
     header keeps "building · driven" — it has no drive chip beside it. */
  if (d && d.reading === "between" && where === "row" && pre) return '<span class="chip flight">building</span>';
  if (d && d.reading === "between") return `<span class="chip flight">${pre}driven</span>`;
  if (p.flight) return `<span class="chip flight">${pre}in flight</span>`;
  if (!p.nsl) return '<span class="chip attn">empty</span>';
  const blk = blockedSlices(p);
  if (blk.length){
    const why = blk.map(s => `${s.id} waits on ${s.blockedBy.join(", ")}`).join("; ");
    return `<span class="chip attn" tabindex="0"
      data-tip="Every open slice comes after an unfinished slice in the build order — ${esc(why)}. The order ranks work; it holds nothing back: each PRD starts once its own dependencies are met.">${pre}after other slices</span>`;
  }
  if (p.unproven) return `<span class="chip unproven">${pre}awaiting proof</span>`;
  return `<span class="chip">${pre}idle</span>`;
}

/* ══ BEGIN THE DELIVERY RANGE ════════════════════════════════════════════════════════════════
 *
 * THE ONE COMPONENT ON EITHER PAGE THAT MAY SAY HOW LONG UNTIL SOMETHING SHIPS — a narrow reversal
 * of the standing rule that this file states no schedule, and a signed one. The operator took it
 * live, and the fleet repository records it as the delivery-range decision note under
 * `docs/design/`: a range from now, the P50 and the P85 side by side, with the history it was
 * drawn from one hover away — never one number, and never a calendar date. The service computes
 * it (`GET /api/delivery`, its own endpoint and its own cache, never part of the board payload);
 * this block only draws what the host hands it.
 *
 * THE STANDALONE PAGE NEVER HAS ONE. Nothing but the host calls `estimates`, so a page with no
 * server behind it draws every row, node and chain exactly as it did before the decision — and a
 * host whose read failed hands `null` and gets the same.
 *
 * HELD BY `test_ui.py`'s estimate-component guards, which find this block by its two marker lines:
 * the `estimat` stem is reachable here and nowhere else in this file (a call to `estimateChip` is
 * the one way out of the block), every rate word — how fast, how much fits, at this pace — is
 * refused inside it as everywhere, and what it renders may state a span of hours or days only
 * inside its own `data-estimate` element, never a date. A second component that wants to say how
 * long is a decision somebody signs in that file, not an edit that passes.
 *
 * ONE ENTRY PER PROGRAM, SLICE AND PRD, in the service's words: `state` (`estimated`, `none`,
 * `shipped`, `cancelled`, `abandoned`), `p50Hours`/`p85Hours` (both or neither), `lowerBound` with
 * `undecomposedSlices`, `flags`, `reason`. A settled thing draws nothing — the row already says
 * it shipped; `none` draws a dash with the reason behind it, because a range that was refused is
 * a different fact from one that was never asked for. */
let ESTIMATES = null;
const ESTIMATE_TABLE = { program: "programs", slice: "slices", prd: "prds" };
/* The flag's tag, and the sentence the popover explains it with. A flag this file does not know is
   still shown, in the service's own word, rather than dropped. */
const ESTIMATE_FLAGS = {
  "not-planned-yet": ["not planned yet",
    "Not planned yet: a PRD in it is still being written or designed, so the range adds the time a PRD usually takes to get from drafted to planned."],
  "in-flight": ["in flight",
    "In flight: the fleet is building it now, and the range counts only the part still ahead."],
  "excludes-waiting-on-you": ["excludes waiting on you",
    "Excludes waiting on you: a PRD in its chain waits on your decision, and the range reads as if you decided now."],
  "unknown-dependency": ["unknown prerequisite",
    "Unknown prerequisite: a PRD in its chain names one the corpus does not hold, so no range is drawn past it."],
  "cycle": ["dependency cycle",
    "Dependency cycle: PRDs in its chain wait on each other in a loop, so none of them can start."],
};

/* THE SEAM: the host hands the whole `/api/delivery` document, or `null`. Anything without a
   `basis` is not that document and reads as none at all. The host repaints; this only holds it. */
function estimates(doc){
  ESTIMATES = doc && typeof doc === "object" && doc.basis && typeof doc.basis === "object" ? doc : null;
}
function estimateOf(kind, id){
  if (!ESTIMATES || !ESTIMATE_TABLE[kind]) return null;
  const table = ESTIMATES[ESTIMATE_TABLE[kind]];
  const e = table && typeof table === "object" ? table[String(id)] : null;
  return e && typeof e === "object" ? e : null;
}
const estimateHours = v => (typeof v === "number" && isFinite(v) && v >= 0 ? v : null);

/* THE FACE: whole hours below two days, days after — half days while they are few enough for a
   half to matter. The boundary is on the ROUNDED hour, so nothing reads as "48h". */
function estimateShort(h){
  if (h < 1) return "<1h";
  if (Math.round(h) < 48) return Math.round(h) + "h";
  const d = h / 24;
  return (d < 10 ? Math.round(d * 2) / 2 : Math.round(d)) + "d";
}
/* THE SAME SPAN IN WORDS, for the popover and for a screen reader. */
function estimateLong(h){
  if (h < 1) return "an hour";
  if (Math.round(h) < 48){ const n = Math.round(h); return n + (n === 1 ? " hour" : " hours"); }
  const d = h / 24, n = d < 10 ? Math.round(d * 2) / 2 : Math.round(d);
  return n + (n === 1 ? " day" : " days");
}

/* WHAT THE RANGE WAS DRAWN FROM, in one sentence — the condition the decision set, beside every
   reading. Whole hours: the service's tenths are noise to a reader. */
function estimateBasis(){
  const b = ESTIMATES.basis, n = v => (estimateHours(v) === null ? "?" : Math.round(v));
  return `Simulation over ${n(b.samples)} PRDs shipped in the last ${n(b.windowDays)} days `
    + `(median ${n(b.medianHours)}h, P85 ${n(b.p85Hours)}h), ${n(b.openPrdsIncluded)} open PRDs incl. prerequisites.`;
}

function estimateChip(kind, id){
  const e = estimateOf(kind, id);
  if (!e) return "";
  const flags = Array.isArray(e.flags) ? e.flags.map(String) : [];
  const undecomposed = Number(e.undecomposedSlices) > 0 ? Math.round(Number(e.undecomposedSlices)) : 0;
  const tags = flags.map(f => (ESTIMATE_FLAGS[f] || [f.replace(/-/g, " ")])[0]);
  /* A SLICE'S OWN COUNT IS ITSELF: it says it is not cut, rather than "1 slice" about itself. */
  if (undecomposed) tags.push(kind === "slice" ? "not broken into PRDs yet"
    : `${undecomposed} slice${undecomposed === 1 ? "" : "s"} not broken into PRDs`);
  const said = flags.filter(f => ESTIMATE_FLAGS[f]).map(f => ESTIMATE_FLAGS[f][1]);
  const lines = [];
  let face, label;
  if (e.state === "estimated"){
    const p50 = estimateHours(e.p50Hours), p85 = estimateHours(e.p85Hours);
    /* A RANGE IS NEVER HALF A RANGE: one percentile without the other draws nothing. */
    if (p50 === null || p85 === null) return "";
    const floor = e.lowerBound === true;
    face = `${floor ? "&ge;" : "~"}${esc(estimateShort(p50))} &middot; ${esc(estimateShort(p85))}`;
    label = `50% chance within ${estimateLong(p50)}, 85% within ${estimateLong(p85)}`;
    lines.push(floor ? `At least this long: ${label}.` : `${label}.`);
    if (floor) lines.push(`${undecomposed || "Some"} of its slices ${undecomposed === 1 ? "is" : "are"} not broken into PRDs yet, and the range cannot count them.`);
    lines.push(estimateBasis());
    lines.push("It covers only PRDs already written; work not yet cut into a PRD is not in it.");
  } else if (e.state === "none"){
    face = "&mdash;";
    label = "No range: " + String(e.reason || "the service drew none");
    lines.push(label + ".");
  } else {
    return "";
  }
  lines.push(...said);
  if (ESTIMATES.waitingOnYou === "unread") lines.push("Which PRDs wait on your decision could not be read, so none is marked as waiting.");
  return `<span class="est${e.state === "none" ? " est-none" : ""}" data-estimate="${esc(kind)}" tabindex="0" data-tip-lines
      data-tip="${esc(lines.join("\n"))}" aria-label="${esc(label)}"><span class="est-r">${face}</span>${
      tags.map(t => `<span class="est-f">${esc(t)}</span>`).join("")}</span>`;
}
/* ══ END THE DELIVERY RANGE ══════════════════════════════════════════════════════════════════ */

/* WHO IS RESPONSIBLE FOR A PROGRAM (PRD 0839). The board payload stamps `owners` on EVERY program
   row — `[email, …]`, `[]` for one that names nobody — so an unowned program is the ordinary case
   and never a missing key. A standalone board carries no `owners`, and none reads as nobody. */
function ownNamed(p){ return Array.isArray(p && p.owners) ? p.owners.map(String) : []; }

/* THE ROW'S RESPONSIBLE-PEOPLE CONTROL, AND IT IS A SIBLING OF THE LINK, NEVER INSIDE IT
   (design D4). Interactive content cannot nest in an anchor — the parser closes the `<a>` at the
   `<button>`'s start tag — so the control lives beside the row in a `.rowwrap` and the row stays a
   real `<a href>` (ENG-10590: middle-click, Cmd-click, new tab and copy-link all still work). It
   shows only WHETHER a program names anyone; the names live in the picker (scope ledger #7). */
/* THE RESPONSIBLE PEOPLE, AS ROUND INITIALS. Up to three are stacked and the rest are a `+N`; a program
   that names nobody shows one dashed "assign" circle, so the way to set one is on the row and not a
   word that has to be read. It is still the ONE button beside the link and opens the same picker.
   The initial is the person's display name when the install's people list carries one
   (`people` entries may be `{email, name}`), else the first letter of the email. The tint is a hash
   of the email over the chart series, so a person keeps their colour on every row. */
const OWN_ADD = `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="6.5" cy="5.5" r="2.4" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M2.5 13c0-2.2 1.8-3.6 4-3.6 1 0 1.9.3 2.6.8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M12 9v5M9.5 11.5h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`;
const OWN_STACK = 3;
function ownInitial(email){
  const named = String(PEOPLE_NAMES[email] || "").replace(/[^\p{L}]/gu, "");
  const local = named || String(email).split("@")[0].replace(/[^\p{L}]/gu, "");
  return (local.charAt(0) || "?").toUpperCase();
}
function ownTint(email){
  let h = 0;
  for (const c of String(email)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return 1 + (h % 6);
}
/* ONE PERSON AS THE ROUND INITIAL — the Programs row's and the Queue row's alike (`Board.avatar`). `who` is
   an email or a plain name; never the full name on the glyph. A caller that has no other label for the
   person passes `tip`, and the initial becomes an image named "<tip>: <full name>"; the Programs row does
   not — its button already names every owner, so a label per initial would read each name twice. */
function ownAvatar(who, tip){
  const label = tip
    ? ` role="img" aria-label="${esc(tip + ": " + (PEOPLE_NAMES[who] ? `${PEOPLE_NAMES[who]} (${who})` : String(who)))}"`
    : "";
  return `<span class="av av${ownTint(who)}"${label}>${esc(ownInitial(who))}</span>`;
}
/* THE ONE "ADD AN ASSIGNEE" TRIGGER: the dashed round person-with-plus icon the Programs board draws, and the only one any page draws —
   the Programs row, an item's header, the Items and Cockpit rows and the program/slice header all come through here. `attrs` is the
   page's own hook (`data-own`, `data-tu-picker`...), `label` the accessible name, `tip` an optional hover. Only the look is shared: each page
   keeps its own picker and handler. */
function tuAddAssignee(o){
  const x = o || {};
  const tip = x.tip ? ` data-tip="${esc(x.tip)}" data-tip-lines` : "";
  return `<button class="own-av none" type="button" ${x.attrs || ""}${tip} aria-label="${esc(x.label || "Assign people")}"><span class="av add">${OWN_ADD}</span></button>`;
}
function ownChip(p){
  const named = ownNamed(p);
  const said = named.length
    ? `Change who is responsible for ${p.id}`
    : `Set who is responsible for ${p.id}`;
  const tip = named.length
    ? `Responsible: ${named.map(e => PEOPLE_NAMES[e] ? `${PEOPLE_NAMES[e]} (${e})` : e).join(", ")}\nClick to change`
    : `Nobody is responsible for ${p.id}\nClick to assign`;
  const inner = named.length
    ? named.slice(0, OWN_STACK).map(e => ownAvatar(e)).join("")
      + (named.length > OWN_STACK ? `<span class="av more">+${named.length - OWN_STACK}</span>` : "")
    : "";
  if (!named.length) return tuAddAssignee({ attrs: `data-own="${esc(p.id)}" data-keep="own:${esc(p.id)}" aria-haspopup="dialog"`, label: said, tip: tip });
  return `<button class="own-av set" type="button" data-own="${esc(p.id)}"
    data-keep="own:${esc(p.id)}" data-tip="${esc(tip)}" data-tip-lines aria-haspopup="dialog" aria-label="${esc(said)}">${inner}</button>`;
}

/* THE ROW'S THREE BADGES, EACH IN ITS OWN FIXED COLUMN (the compact-rows mockup): delivery, priority
   and to do. Everything else a row used to say as a chip is a quiet line under the name, the
   progress caption, or a tooltip. A badge that does not apply leaves its cell empty (a dash for
   delivery and priority, which are always a question) rather than saying "0 to do". */
const pill = (cls, tip, text) =>
  `<span class="pill ${cls}" tabindex="0" data-tip="${esc(tip)}">${text}</span>`;
function deliveryBadge(p){
  if (!DELIVERY) return "";
  const said = DELIVERY(String(p.id || ""));
  const word = said && typeof said.reading === "string" ? said.reading : "";
  const closed = p.complete || p.state === "withdrawn" || p.state === "waived";
  /* A closed program with an inert drive shows nothing: there is nothing to drive. */
  if (closed && said && said.inert === true) return "";
  if (DRIVEN_READINGS.includes(word))
    return pill("driven", "The fleet is delivering this program: somebody pressed Start delivering and nobody has stopped it.", "driven");
  if (closed) return "";
  if (word === "stopped")
    return pill("idle", "Not driven: delivery was started once and is stopped now. Nothing moves this program until somebody starts it again.", "not driven");
  if (word === "none")
    return pill("idle", "Not driven: nobody has ever pressed Start delivering on this program, so the fleet is not moving it.", "not driven");
  return "";
}
function priorityBadge(p){
  const r = priorityOf(p);
  if (!r || !r.rank) return "";
  if (!r.raised)
    return pill("prio", `Priority ${r.rank}: you placed this program ${ordinal(r.mine)} in your order, so the fleet gives its work priority ${r.rank}.`, `P${r.rank}`);
  return pill("prio inh", `${priorityWhy(r)}, so the fleet gives this program priority ${r.rank}. `
    + (r.mine ? `You placed it ${ordinal(r.mine)}.` : "You have not placed it."), `P${r.rank}`);
}
const todoBadge = n => n ? pill("todo", `${n} thing${n === 1 ? "" : "s"} only a person can do on this program. The program page says what, in order.`, `${n} for you`) : "";
const badgeCell = (cls, html) => `<span class="pc ${cls}">${html || '<span class="none" aria-hidden="true">&mdash;</span>'}</span>`;

/* WHERE THE PROGRAM IS IN ITS LIFE, as the one plain word the quiet line starts with. */
function phaseWord(p){
  if (p.state === "withdrawn") return "withdrawn";
  if (p.state === "waived") return "proof waived";
  if (p.closed) return "closed";
  if (p.complete) return STATE.complete;
  if (p.phase === "awaiting-proof") return "awaiting proof";
  return p.phase ? String(p.phase).replace(/-/g, " ") : (p.nsl ? "" : "no slices");
}
/* The progress caption's proof: named and shipped, named and open, waived, or missing. */
function proofCaption(p){
  if (p.proof && p.proof.length)
    return `<span${p.proofok ? ' class="ok"' : ""}>proof ${esc(proofText(p.proof))}${p.proofok ? " &check;" : ""}</span>`;
  return `<span class="miss">${p.waived ? "proof waived" : "no proof"}</span>`;
}
/* What the id says on hover: the kind and wave, and the whole description. */
function rowIdTip(p){
  const note = descNote(p.desc);
  const desc = note || String(p.desc || "").trim();
  return `${p.id} · ${p.kind}${p.wave ? ` · wave ${p.wave}` : ""}\n\n${desc}`;
}
/* THE DELIVERY RANGE IS THE ONE COMPONENT'S OWN ELEMENT, shown over the progress cell on hover or focus
   (css) — never a second rendering of it in this cell's tooltip, which would be the component's words
   outside the component. */
const rangeOf = p => estimateChip("program", p.id);
function progressCell(p){
  if (!p.nsl) return `<span class="prog"><span class="noslices">no slices cut yet</span>${rangeOf(p)}</span>`;
  const c = keptCuts(p);
  const seg = (k, n) => n > 0 ? `<i class="seg-${k}" style="width:${(n / (p.nsl || 1) * 100).toFixed(2)}%"></i>` : "";
  const lines = [`${p.done} of ${c.kept} slices done`
    + (p.flight ? `, ${p.flight} in flight` : "") + (p.unproven ? `, ${p.unproven} awaiting proof` : "")
    + (p.idle ? `, ${p.idle} not started` : "")];
  if (c.withdrawn) lines.push(`${c.withdrawn} withdrawn`);
  if (p.livePRDs) lines.push(`${p.livePRDs} live PRD${p.livePRDs > 1 ? "s" : ""}`);
  return `<span class="prog" tabindex="0" data-tip="${esc(lines.join("\n"))}" data-tip-lines>
    <span class="bar">${seg("complete", p.done)}${seg("flight", p.flight)}${seg("unproven", p.unproven)}${seg("idle", p.idle)}</span>
    <span class="cap"><span><b>${p.done}/${c.kept}</b> slices</span><span class="pf">${proofCaption(p)}</span></span>${rangeOf(p)}</span>`;
}
/* The column heads over a group's rows (desktop only; the phone's card has no columns). */
function progCols(){
  return `<div class="pcols" aria-hidden="true"><div class="prow-h"><span>Id</span><span>Program</span><span>Delivery</span><span>Priority</span><span>To do</span><span>Progress &middot; proof</span><span></span></div>${
    OWNERS ? '<span class="r">Responsible</span>' : ""}</div>`;
}

/* THE RESTING ROW: A LINK TO ITS PROGRAM (ENG-10590), so a program can be opened in a new tab
   from the list, which is the first thing anybody does with a list. `opts.markUnplaced` gates a
   per-row "not ranked" chip on the priority sort, where the boundary line makes the two halves
   meaningful. The id is escaped on both writes (the test that pinned the raw interpolation as a
   known defect pins the fix).

   AND, WHEN A HOST OFFERS THE OWNERS WRITE, THE ROW IS A `.rowwrap` HOLDING THE LINK AND THE
   RESPONSIBLE CONTROL BESIDE IT (PRD 0839, design D4). With no host — the standalone board, a
   build with no service behind it — the row is the plain link it always was: a control that could
   write nothing would be a control that lies.

   REORDER MODE DRAWS `reorderRowHtml` FOR THE SAME PROGRAM — the same id, name and chips, keyed
   by the same `data-keep`, in a `<div>` a person can hold, type into and press buttons on. It
   used to be this same element with drag attributes added, on the argument that swapping the
   element drops focus; it does not — `rzRerender` hands the caret back through `data-keep` on
   every repaint either way — and what the argument actually cost was every control: a `<button>`
   cannot hold a `<button>` or an `<input>` (the parser closes the outer one at the inner start
   tag, measured on the production corpus once already for the `via` link). What that row does
   NOT carry is the progress bar, the count and the description: a person deciding an order reads
   the name and the state, and a row a third the height is the difference between a list of
   twenty that drags and one that does not (ENG-10673). */
function rowHtml(p, opts){
  const o = opts || {};
  if (o.reorder) return reorderRowHtml(p, o);
  const n = todoCount(p.id);
  const moving = fleetMoving(p);
  const phase = phaseWord(p);
  const waits = waitingOn(p).filter(() => !p.complete);
  const wait = waits.length
    ? `<span class="wait" data-tip="${esc(waits.join(" · "))}">${esc(waits[0].replace(/:.*$/, ""))}${waits.length > 1 ? ` +${waits.length - 1}` : ""}</span>` : "";
  const quiet = [wait,
    p.blast ? `<span>blocks ${p.blast} program${p.blast > 1 ? "s" : ""}</span>` : "",
    dispositionFact(p.disposition) ? `<span>${dispositionFact(p.disposition)}</span>` : "",
    hostRowMarks(p)].filter(Boolean);
  const dot = '<span class="qsep">&middot;</span>';
  /* On a phone the proof leaves the progress caption (the bar takes that line with its count) and
     joins the quiet line, so it is said once at either width. */
  const pf = p.nsl ? `<span class="pf-m">${quiet.length ? dot : ""}${proofCaption(p)}</span>` : "";
  const sub = (phase ? `<span class="ph-d">${esc(phase)}${quiet.length ? dot : ""}</span>` : "") + quiet.join(dot) + pf;
  const link = `<a class="row prow${moving ? " row-fleet" : ""}" href="${esc(urlFor("program:" + p.id))}" data-go="program:${esc(p.id)}">
    <span class="ptop"><span class="id" tabindex="0" data-tip="${esc(rowIdTip(p))}" data-tip-lines>${esc(p.id)}</span>${phase ? `<span class="ph-m">&middot; ${esc(phase)}</span>` : ""}</span>
    <span class="main"><span class="rname">${esc(p.name)}</span>
      <span class="rsub">${sub}</span>
      <span class="rdesc">${descHtml(p.desc, true)}</span></span>
    <span class="psig">${badgeCell("pc-drv", deliveryBadge(p))}${badgeCell("pc-prio", priorityBadge(p))}${badgeCell("pc-todo", todoBadge(n))}</span>
    ${progressCell(p)}
    <span class="chev">&rsaquo;</span></a>`;
  return OWNERS ? `<div class="rowwrap">${link}${ownChip(p)}</div>` : link;
}

/* ── the responsible-people picker (PRD 0839) ────────────────────────────────────────────────
 *
 * THE PAGE NEVER FETCHES: board.js ships standalone with no server, so it learns no URL, no method
 * and no body. The host hands in the write (`owners(fn)`) and the candidate people
 * (`people(list)`) exactly as it hands in `reorder(fn)` and `viewer(email)` — see `api/app.py`'s
 * `Board.owners` / `Board.people`. Absent a write seam the row draws no control.
 *
 * The link is a DECLARATION, not a patch: the picker's checkboxes carry the whole set, and Save
 * writes it whole. The write is validated server-side against the people the install knows, so
 * the picker offers exactly those.
 */
let OWNERS = null;      // the host's write seam: (id, emails) => Promise<{owners: [...]}>
let PEOPLE = [];        // the install's candidate people (from /api/status's `people`)
let PEOPLE_NAMES = {};  // email -> display name, for the entries that carry one
function owners(fn){ OWNERS = fn || null; }
function people(list){
  const all = Array.isArray(list) ? list : [];
  /* An entry is an email, or `{email, name}` where the install knows a display name. */
  PEOPLE = all.map(x => String(x && typeof x === "object" ? x.email : x)).filter(Boolean);
  PEOPLE_NAMES = {};
  all.forEach(x => { if (x && typeof x === "object" && x.email && x.name) PEOPLE_NAMES[String(x.email)] = String(x.name); });
}

/* THE PEOPLE THE PICKER OFFERS: the install's own candidates, plus the viewer (always a teammate)
   and whoever the program already names (so an owner is never silently dropped from the list). */
function ownCandidates(p){
  const all = new Set(PEOPLE);
  if (RZ_VIEWER) all.add(RZ_VIEWER);
  ownNamed(p).forEach(email => all.add(email));
  return [...all].sort();
}
/* A FAILED SAVE SAYS SO AND KEEPS THE MODAL — the reader's ticks are still there to press Save
   on again. In a person's words, `rzFailure`'s shape one dialog over. */
function ownFailure(err){
  const status = Number(err && err.status) || 0;
  const code = String((err && err.code) || "");
  const detail = err && err.message ? String(err.message) : "";
  if (code === "unreachable" || status === 502 || status === 503 || status === 504) return "Fleet could not be reached.";
  if (code === "not-json" || status === 401 || status === 403) return "Fleet did not accept the request as you — you may have been signed out; sign in again in another tab.";
  if (status === 422) return detail || "That name is not a person this install knows.";
  if (status >= 500) return "Fleet ran into an error while saving this.";
  return detail ? `Fleet refused this: ${detail}` : "The save did not finish.";
}
/* THE PROGRAM'S RESPONSIBLE PEOPLE, in the one people modal (`peopleModal`): the ticks are the whole set, and Save writes it whole. */
function ownOpen(id){
  if (!OWNERS || !PG[id]) return;
  const p = PG[id];
  peopleModal({
    title: `Who is responsible for ${p.id}?`, role: "Responsible", noun: "program",
    intro: "Every person you pick opens their Programs list on this program. Choose from the people who have signed in to this install.",
    foot: "Anyone on the install can set this. It changes what each person sees — never what they may open.",
    people: ownCandidates(p).map(email => ({ email: email, name: PEOPLE_NAMES[email] || "" })), viewer: RZ_VIEWER, on: ownNamed(p),
    failure: ownFailure,
    apply: d => Promise.resolve(OWNERS(id, d.selected)).then(body => {
      if (PG[id]) PG[id].owners = body && Array.isArray(body.owners) ? body.owners.map(String) : d.selected;
      render(openRoute());
      return body;
    }),
    reanchor: () => (typeof document !== "undefined" && document.querySelector ? document.querySelector(`[data-own="${id}"]`) : null),
  });
}

/* ══ THE ONE PEOPLE MODAL ═══════════════════════════════════════════════════════════════════════
 *
 * Every place that names people for a thing — a feature's owners, a program's responsible people, an item's assignees, the
 * Cockpit's bulk Assignee — opens THIS modal, so there is one look, one keyboard and one way to be wrong. A page hands in what
 * is true (the candidates, who holds it now, and for a selection who holds it on only some of the items) and what Save does
 * (`apply`); it draws no list of its own. Centred on a scrim (`.dlg`), a search box, one row per person, Cancel and Save.
 *
 *   Board.peopleModal(spec) -> Promise<{ applied, result }>   opens it; settles when it closes
 *     spec = { title, intro, foot, noun, role,          words: the question, one sentence under it, the footnote; "Owner"/"Assigned" names the holders
 *              people: [{email, name}], viewer,          everyone who may be named (only addresses are people); the viewer is always offered
 *              on: [email], partial: [email], count,     holders now; for a selection, those on only some of its `count` items (a click makes them all)
 *              single,                                   true for a field that holds ONE person (a filing's assignee): choosing someone puts the rest off
 *              select: [email],                          ticks to open on when they differ from `on` (a retry after a refusal)
 *              err, blocked, clearLabel,                 an error to open with; a sentence that replaces the list (nothing can be set here); an "everyone off" button
 *              apply({add, remove, selected}) -> Promise Save. A refusal it throws is said in the modal, which stays open; a bulk apply keeps
 *                                                        its own per-row errors and undo (the Cockpit's toast) and resolves
 *              later: Promise<patch>,                    OPEN AT ONCE with what is known and fill the rest in when it settles: `patch` is any of the fields above
 *                                                        (people, on, partial, viewer, blocked, err...). Until then the rows are shown and Save is held; a refusal says so in the modal
 *              failure(err) -> words, reanchor() -> the control that opened it as drawn NOW (a page repaint behind the modal replaces it) }
 *   Board.peopleModalHtml(model) / peopleModalModel(spec) / peopleModalNext(model, email) / peopleModalDiff(model)   the pure halves
 *
 * A person is on, off or (for a selection) partial; a click turns partial into on, on into off, and off back to on (or to partial
 * again, for a person the items held on only some of them). Escape or a click on the scrim cancels; Tab stays inside; Enter in the
 * search box ticks the one person left; the control that opened it gets focus back. */
const PM_PERSON = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
function peopleModalModel(spec){
  const s = spec || {};
  const was = {};
  (s.on || []).forEach(e => { was[String(e)] = "on"; });
  (s.partial || []).forEach(e => { if (!was[String(e)]) was[String(e)] = "partial"; });
  const seen = {}, rows = [];
  const add = (email, name) => {
    email = String(email || "");
    if (!PM_PERSON.test(email) || seen[email]) return;
    seen[email] = true;
    rows.push({ email: email, name: String(name || "").trim() });
  };
  (s.people || []).forEach(x => (x && typeof x === "object" ? add(x.email, x.name) : add(x, "")));
  if (s.viewer) add(s.viewer, "");
  Object.keys(was).forEach(e => add(e, ""));
  const pick = {};
  rows.forEach(r => { pick[r.email] = was[r.email] || "off"; });
  if (Array.isArray(s.select)){ rows.forEach(r => { pick[r.email] = s.select.map(String).indexOf(r.email) >= 0 ? "on" : "off"; }); }
  return { title: String(s.title || "Who is it?"), intro: String(s.intro || ""), foot: String(s.foot || ""), noun: String(s.noun || "item"),
    single: !!s.single, role: String(s.role || "Assigned"), viewer: String(s.viewer || ""), count: Number(s.count) || 0, rows: rows, was: was, pick: pick,
    q: "", busy: false, loading: !!s.later, err: String(s.err || ""), blocked: String(s.blocked || ""), clearLabel: String(s.clearLabel || "") };
}
function peopleModalNext(m, email){
  const now = m.pick[email] || "off", was = m.was[email] || "off";
  const next = now === "partial" ? "on" : now === "on" ? "off" : (was === "partial" ? "partial" : "on");
  const pick = Object.assign({}, m.pick, { [email]: next });
  /* SINGLE-SELECT (a filing's one assignee): choosing someone puts everyone else off. */
  if (m.single && next === "on") Object.keys(pick).forEach(e => { if (e !== email) pick[e] = "off"; });
  return Object.assign({}, m, { pick: pick });
}
/* WHAT SAVE WRITES: who to add (ticked, and not on every item before), who to remove (cleared, and on any item before), and the whole ticked set. */
function peopleModalDiff(m){
  const add = [], remove = [], selected = [];
  m.rows.forEach(r => {
    const now = m.pick[r.email] || "off", was = m.was[r.email] || "off";
    if (now === "on") selected.push(r.email);
    if (now === "on" && was !== "on") add.push(r.email);
    if (now === "off" && was !== "off") remove.push(r.email);
  });
  return { add: add, remove: remove, selected: selected.sort(), changed: add.length + remove.length > 0 };
}
function peopleModalVisible(m){
  const q = m.q.trim().toLowerCase();
  return m.rows.filter(r => !q || r.email.toLowerCase().includes(q) || r.name.toLowerCase().includes(q));
}
function pmAvatar(r){
  const local = (r.name || r.email.split("@")[0]).replace(/[^\p{L}]/gu, "");
  return `<span class="av av${ownTint(r.email)}" aria-hidden="true">${esc((local.charAt(0) || "?").toUpperCase())}</span>`;
}
function peopleModalHtml(m){
  const hit = peopleModalVisible(m);
  const held = r => (m.was[r.email] || "off") !== "off";
  const you = r => r.email === m.viewer;
  const byName = (a, b) => (you(b) ? 1 : 0) - (you(a) ? 1 : 0) || (a.name || a.email).localeCompare(b.name || b.email);
  const row = r => {
    const st = m.pick[r.email] || "off";
    const tags = (you(r) ? `<span class="you">you</span>` : "") + (held(r)
      ? `<span class="ar-cur">${m.was[r.email] === "partial" && m.count ? `some of ${m.count}` : esc(m.role.toLowerCase())}</span>` : "");
    return `<label class="psn" data-pm-st="${st}"><input type="${m.single ? "radio" : "checkbox"}"${m.single ? ' name="pm-one"' : ""} data-pm-pick="${esc(r.email)}"${st === "on" ? " checked" : ""}${
      st === "partial" ? ' data-pm-mixed="1" aria-checked="mixed"' : ""}${m.busy ? " disabled" : ""}>${pmAvatar(r)}<span class="who">${
      r.name && r.name !== r.email ? `<span class="nm">${esc(r.name)}</span>` : ""}<span class="em">${esc(r.email)}</span></span>${
      tags ? `<span class="pm-tags">${tags}</span>` : ""}</label>`;
  };
  const now = hit.filter(held).sort(byName), rest = hit.filter(r => !held(r)).sort(byName);
  const body = m.blocked ? `<p class="dlg-empty">${esc(m.blocked)}</p>`
    : !m.rows.length && m.loading ? `<p class="dlg-empty" data-pm-loading role="status">Reading who can be named&hellip;</p>`
    : !m.rows.length ? `<p class="dlg-empty">No one has signed in to this install yet.</p>`
    : !hit.length ? `<p class="dlg-empty" data-pm-none>No one matches</p>`
    : (now.length ? `<div class="ar-sep">${esc(m.role)} now</div>${now.map(row).join("")}${rest.length ? `<div class="ar-sep">Everyone else</div>` : ""}` : "") + rest.map(row).join("");
  const off = m.busy ? " disabled" : "";
  const anyOn = m.rows.some(r => (m.pick[r.email] || "off") !== "off");
  return `<div class="scrim" aria-hidden="true" data-pm-cancel></div><div class="dlg pm" role="dialog" aria-modal="true" aria-labelledby="pm-h">
    <div class="dlg-h"><h3 id="pm-h">${esc(m.title)}</h3>${m.intro ? `<p>${esc(m.intro)}</p>` : ""}</div>
    ${m.err ? `<p class="dlg-err" role="alert">${esc(m.err)}</p>` : ""}
    ${m.blocked || !m.rows.length ? "" : `<div class="own-q"><input type="search" data-pm-q value="${esc(m.q)}" autocomplete="off" placeholder="Search by name or email" aria-label="Search people"${off}></div>`}
    <div class="dlg-b"${m.loading ? ' aria-busy="true"' : ""}>${m.loading && m.rows.length ? `<p class="quiet" data-pm-loading role="status">Reading who holds it now&hellip;</p>` : ""}${body}</div>
    <div class="dlg-f"><span class="quiet">${esc(m.foot)}</span>
      ${m.clearLabel && anyOn && !m.blocked ? `<button class="ar-rm" type="button" data-pm-clear${off}>${esc(m.clearLabel)}</button>` : ""}
      <button class="act ghost" type="button" data-pm-cancel${off}>${m.blocked ? "Close" : "Cancel"}</button>
      ${m.blocked ? "" : `<button class="act primary" type="button" data-pm-save${m.loading ? " disabled" : off}>${m.busy ? "Saving&hellip;" : "Save"}</button>`}</div></div>`;
}
/* FOCUS GOES BACK TO WHAT OPENED THE MODAL — BY IDENTITY, NOT BY ELEMENT. A page that repaints live (a poll, a save, a reload of the item
   page) replaces the opener, and an element remembered at open time is detached by the time the modal closes: focus fell to <body>.
   So the opener is remembered as WHAT IT IS (its own data attribute or id, and which of those it is) and looked up again when focus is
   handed back; and when the repaint has not landed yet the lookup is retried as the DOM changes and on a short timer, until the
   control is back, the reader has put focus somewhere else, or about two seconds have passed. */
function pmIdentity(el){
  if (!el || !el.attributes) return null;
  if (el.id) return { sel: `#${String(el.id).replace(/[^\w-]/g, "\\$&")}`, idx: 0 };
  const attrs = Array.prototype.slice.call(el.attributes);
  const pref = ["data-tc", "data-area-own", "data-own", "data-keep"];
  const hit = pref.map(n => attrs.find(a => a.name === n)).find(Boolean) || attrs.find(a => /^data-/.test(a.name));
  if (!hit) return null;
  const sel = hit.value ? `[${hit.name}="${String(hit.value).replace(/["\\]/g, "\\$&")}"]` : `[${hit.name}]`;
  const all = typeof document.querySelectorAll === "function" ? Array.prototype.slice.call(document.querySelectorAll(sel)) : [];
  return { sel: sel, idx: Math.max(0, all.indexOf(el)) };
}
function pmFind(id){
  if (!id || typeof document.querySelectorAll !== "function") return null;
  const all = Array.prototype.slice.call(document.querySelectorAll(id.sel)).filter(e => e.isConnected !== false);
  return all[id.idx] || all[0] || null;
}
function pmRestoreFocus(target){
  const doc = document;
  const bare = () => { const a = doc.activeElement; return !a || a === doc.body || a === doc.documentElement; };
  let obs = null, finished = false;
  const stop = () => { finished = true; if (obs && obs.disconnect) obs.disconnect(); };
  const attempt = () => {
    if (finished) return true;
    const t = target();
    if (t && t.isConnected !== false && doc.activeElement === t){ stop(); return true; }
    if (!bare()){ stop(); return true; }          // the reader (or the page) put focus somewhere real: leave it
    if (t && t.focus){ t.focus({ preventScroll: true }); if (doc.activeElement === t){ stop(); return true; } }
    return false;
  };
  if (attempt()) return;
  if (typeof MutationObserver === "function" && doc.body){
    obs = new MutationObserver(() => { attempt(); });
    obs.observe(doc.body, { childList: true, subtree: true });
  }
  const waits = [80, 250, 700, 1500];
  const tick = i => {
    if (finished) return;
    if (attempt()) return;
    if (i >= waits.length){ stop(); return; }
    setTimeout(() => tick(i + 1), waits[i]);
  };
  setTimeout(() => tick(0), 0);
}
let PM_OPEN = null;
function peopleModalClose(){ if (PM_OPEN) PM_OPEN.close({ applied: false }); }
function peopleModal(spec){
  const doc = typeof document !== "undefined" ? document : null;
  if (!doc || !doc.body || !doc.createElement) return Promise.resolve({ applied: false });
  peopleModalClose();
  return new Promise(resolve => {
    let m = peopleModalModel(spec);
    const layer = doc.createElement("div");
    layer.className = "pm-root";
    doc.body.appendChild(layer);
    const before = doc.activeElement;
    const ident = pmIdentity(before);
    const focusables = () => Array.prototype.slice.call(layer.querySelectorAll("input:not([disabled]),button:not([disabled])"));
    /* WHAT HAD FOCUS, handed back after a repaint: the search box (with its caret), one person's box or Save. */
    const paint = () => {
      const at = doc.activeElement;
      const had = at && layer.contains && layer.contains(at) ? { q: at.hasAttribute("data-pm-q"), who: at.getAttribute("data-pm-pick"), save: at.hasAttribute("data-pm-save") } : null;
      const list = layer.querySelector(".dlg-b");
      const top = list ? list.scrollTop : 0;
      layer.innerHTML = peopleModalHtml(m);
      Array.prototype.forEach.call(layer.querySelectorAll("[data-pm-mixed]"), el => { el.indeterminate = true; });
      const list2 = layer.querySelector(".dlg-b");
      if (list2) list2.scrollTop = top;
      let el = null;
      if (had && had.q) el = layer.querySelector("[data-pm-q]");
      else if (had && had.who) el = Array.prototype.find.call(layer.querySelectorAll("[data-pm-pick]"), x => x.getAttribute("data-pm-pick") === had.who);
      else if (had && had.save) el = layer.querySelector("[data-pm-save]");
      if (!el && !m.busy) el = layer.querySelector("[data-pm-q]") || layer.querySelector("button[data-pm-cancel]");
      if (el && el.focus){
        el.focus({ preventScroll: true });
        if (had && had.q && el.setSelectionRange) el.setSelectionRange(el.value.length, el.value.length);
      }
    };
    const close = result => {
      if (PM_OPEN !== handle) return;
      PM_OPEN = null;
      doc.removeEventListener("keydown", keys, true);
      if (layer.remove) layer.remove(); else if (layer.parentNode) layer.parentNode.removeChild(layer);
      /* FOCUS GOES BACK TO THE CONTROL THAT OPENED IT — as drawn NOW, by identity (`pmRestoreFocus`): the page may have repainted it. */
      pmRestoreFocus(() => {
        let back = typeof spec.reanchor === "function" ? spec.reanchor() : null;
        if (!back || back.isConnected === false) back = pmFind(ident);
        if (!back && before && before.isConnected !== false) back = before;
        return back;
      });
      resolve(result);
    };
    const save = () => {
      if (m.busy || m.blocked || m.loading) return;
      const d = peopleModalDiff(m);
      if (!d.changed) return close({ applied: false });
      m = Object.assign({}, m, { busy: true, err: "" });
      paint();
      Promise.resolve().then(() => spec.apply(d)).then(result => close({ applied: true, result: result }), err => {
        m = Object.assign({}, m, { busy: false, err: typeof spec.failure === "function" ? spec.failure(err) : String((err && err.message) || "That did not save.") });
        paint();
      });
    };
    const toggle = email => { m = peopleModalNext(m, email); paint(); };
    const keys = e => {
      if (e.key === "Escape"){
        /* Stopped here: a sheet under the modal (the filing form) must not also close on this Escape. */
        if (!m.busy){ e.preventDefault(); if (e.stopImmediatePropagation) e.stopImmediatePropagation(); close({ applied: false }); }
        return;
      }
      if (e.key === "Tab"){
        const all = focusables();
        if (!all.length){ e.preventDefault(); return; }
        const at = doc.activeElement, inside = at && layer.contains && layer.contains(at);
        if (!inside || (!e.shiftKey && at === all[all.length - 1])){ e.preventDefault(); all[0].focus(); }
        else if (e.shiftKey && at === all[0]){ e.preventDefault(); all[all.length - 1].focus(); }
        return;
      }
      const t = e.target;
      if (e.key === "Enter" && t && t.closest && t.closest("[data-pm-q]")){
        e.preventDefault();
        if (e.metaKey || e.ctrlKey) return save();
        const one = peopleModalVisible(m);
        if (one.length === 1) toggle(one[0].email);
      }
    };
    layer.addEventListener("click", e => {
      const t = e.target;
      if (!t || !t.closest) return;
      let el;
      if (t.closest("[data-pm-save]")){ e.preventDefault(); return save(); }
      if (t.closest("[data-pm-cancel]")){ e.preventDefault(); if (!m.busy) close({ applied: false }); return; }
      if (t.closest("[data-pm-clear]")){
        e.preventDefault();
        const pick = {};
        m.rows.forEach(r => { pick[r.email] = "off"; });
        m = Object.assign({}, m, { pick: pick });
        return paint();
      }
      if ((el = t.closest("[data-pm-pick]"))){
        /* The box is repainted from the model, so the browser's own tick is not the answer. */
        e.preventDefault();
        if (!m.busy && !m.loading) toggle(el.getAttribute("data-pm-pick"));
      }
    });
    layer.addEventListener("input", e => {
      const t = e.target;
      if (!t || !t.closest || !t.closest("[data-pm-q]")) return;
      m = Object.assign({}, m, { q: String(t.value || "") });
      paint();
    });
    const handle = { close: close };
    PM_OPEN = handle;
    doc.addEventListener("keydown", keys, true);
    paint();
    /* THE REST ARRIVES AFTER THE MODAL IS UP (`spec.later`): never a read the open waits on. A modal closed meanwhile ignores the answer. */
    if (spec.later && typeof spec.later.then === "function"){
      spec.later.then(patch => {
        if (PM_OPEN !== handle) return;
        const next = peopleModalModel(Object.assign({}, spec, patch || {}, { later: null }));
        m = Object.assign(next, { q: m.q });
        paint();
      }, err => {
        if (PM_OPEN !== handle) return;
        m = Object.assign({}, m, { loading: false, err: typeof spec.failure === "function" ? spec.failure(err) : String((err && err.message) || "Could not read who is assigned.") });
        paint();
      });
    }
  });
}

/* THE ROW NAMES NO MOVE (the program lifecycle). V-01 put each person-only move on the row with its
   reason and command; the operator asked for the count alone — the row says there is something to
   do, and the program page says what, in order, with the command. */

/* REORDER MODE'S ROW: grip · position box · id · name and chips · the controls (ENG-10673).

   EVERY WAY OF MOVING A ROW IS ON THE ROW. A position box you type into (`3` puts it third), and
   for a placed row `Top`, `Up`, `Down`, `Bottom` and `Take out`; for an unplaced one `Place at
   top` and `Place at bottom` — the one-press answer to a program at the foot of twenty unplaced
   ones that has to reach the head of the order. The drag and the keys are the other two ways at
   the same acts, never the only way at any of them. `Up` on the first row and `Down` on the last
   are disabled rather than absent, so the strip keeps its shape and the caret has somewhere to
   land (`rzRerender`'s fallback takes it to the row).

   The row is `tabindex="0"` and a `group`: focusable, so the keys in `keydown` have a subject;
   named by its position, so a screen reader hears "PG-21, position 5 of 6" and not a bare id.
   Its chips are the ones that bear on an order — the state, the kind, and the reorder reading
   of `programRankChip` (who needs it, or `not in your order`) — and not the fleet's `with …` / `N to do` or the host's
   marks, which are about attention rather than about position and cost a line each on a phone.
   `data-go` stays on it — the row is still this program's, and the click handler's guard is
   what keeps a click here from drilling in while the mode is open — and every control names
   its row (`data-rz-row`) for the focus fallback. `busy` disables the controls while a save is in
   flight, never the row, so the caret survives the write. */
/* ENG-10701 CHANGED FOUR THINGS ABOUT THIS ROW. It is never faded (K-02): `.row-fleet` dims a
   program the fleet is moving on the resting list, where it costs less attention, and here it
   made "Place at top" on the bottom program look disabled. It is in the Tab order only while it is
   `RZ_ACTIVE`, and nothing inside it ever is (K-05) — every control has a key on the row, so the
   list is walked with the arrows rather than tabbed through five stops a row; the chips' tooltips
   stay a hover away. `Top` / `Place at top` is marked `rz-main`: on a phone a row is one dense line
   carrying only that button (and the active row its full strip), so moving the bottom program to
   the top is one swipe and one tap rather than seven swipes through a 4,000px list. */
function reorderRowHtml(p, o){
  const placed = o.zone === "placed";
  const busy = REORDER_BUSY !== "";
  const id = esc(p.id);
  const pos = placed ? o.pos : 0;
  const on = RZ_ACTIVE === p.id;
  const label = placed ? `${p.id}, position ${pos} of ${o.of}` : `${p.id}, not in your order`;
  const act = (name, text, said, off, lead) => `<button class="act${lead ? " rz-main" : ""}" type="button" tabindex="-1" data-rz-act="${name}"
        data-rz-row="${id}" data-keep="rz-${name}-${id}" aria-label="${esc(said)}"${off || busy ? " disabled" : ""}>${text}</button>`;
  const acts = placed
    ? act("top", "Top", `Move ${p.id} to the top`, pos === 1, true)
      + act("up", "Up", `Move ${p.id} up one place`, pos === 1)
      + act("down", "Down", `Move ${p.id} down one place`, pos === o.of)
      + act("bottom", "Bottom", `Move ${p.id} to the bottom of your order`, pos === o.of)
      + act("out", "Take out", `Take ${p.id} out of your order`, false)
    : act("top", "Place at top", `Place ${p.id} at the top of your order`, false, true)
      + act("bottom", "Place at bottom", `Place ${p.id} at the bottom of your order`, false);
  /* A CHIP'S TOOLTIP STOP IS THE RESTING LIST'S. Here the row is the one stop, so the chips it
     shares with that list are drawn out of the Tab order rather than re-spelled. */
  const chips = `${stateChip(p)}<span class="chip kind">${esc(p.kind)}</span>
        ${programRankChip(p, "reorder", !placed)}`.replace(/tabindex="0"/g, 'tabindex="-1"');
  return `<div class="row row-rz${on ? " rz-on" : ""}${busy ? " rz-busy" : ""}" tabindex="${on ? "0" : "-1"}"
      role="group" aria-roledescription="sortable program" aria-label="${esc(label)}" aria-describedby="rz-row-help"
      data-rz-card="${id}" data-rz-from="${o.zone}" data-keep="rz-card-${id}" data-go="program:${id}">
    <span class="rz-grip" data-rz-grip aria-hidden="true">&#8942;&#8942;</span>
    <label class="rz-posw"><span class="rz-posl" aria-hidden="true">#</span><input class="rz-pos" tabindex="-1"
      type="number" inputmode="numeric" min="1" max="${placed ? o.of : o.of + 1}" value="${placed ? pos : ""}"
      placeholder="${placed ? "" : "&ndash;"}" data-rz-pos="${id}" data-rz-row="${id}" data-keep="rz-pos-${id}"
      aria-label="Position of ${id}, 1 is first"${busy ? " disabled" : ""}></label>
    <span class="id">${id}</span>
    <span class="rmain"><span class="rname">${esc(p.name)}</span>
      <span class="rmeta">${chips}</span></span>
    <span class="rz-acts">${acts}</span>
  </div>`;
}

/* A CORPUS WITH NO PLAN IN IT, AND IT IS NOT "NOTHING MATCHES THESE FILTERS". Most lanes a
   deployment serves carry a `knowledge/` holding a slot registry and nothing else — no
   `programs.md`, no slices, no PRDs — and a Programs list that answered that with the filter
   sentence would send the reader to the Filter menu to clear a narrowing they never set, on a
   list that has nothing to narrow. The two nothings are told apart on the ONE fact that
   separates them: whether the payload holds any program at all. The file is named by the
   corpus's own directory, which the payload carries, rather than spelled `knowledge/` here.

   NO TOOLBAR OVER IT. Sort, Filter and Reorder are controls over a list, and offering them over
   an absent one is a page pretending there is something to act on. NO STRIP EITHER (ENG-10706,
   M-11): six zeros over "carries no plan" read as a plan with nothing in it, and a page that has
   not loaded already says so in its own words (`corpusPlaceholder`). */
function noPlan(){ return D !== null && !D.programs.length; }
function noPlanNote(){
  const dir = String(D.corpusDir || "knowledge").replace(/\/+$/, "");
  return `<p class="empty-note" data-empty="plan">This repository carries no plan &mdash;
    <code>${esc(dir)}/programs.md</code> is absent or empty.</p>`;
}

function viewBoard(){
  try { return viewBoardBody(); } finally { VIEW_ORDER = null; }
}
function viewBoardBody(){
  /* `REORDER_MODE` can only be true while the capability that opened it still exists — a host
     that never registers one, or one that unregisters partway through a session, must not leave
     this page stuck showing rows with nowhere to report a drag to. */
  if (!REORDER && REORDER_MODE) rzLeave();
  let list, rows;
  LISTED = new Set();
  if (noPlan()){
    if (REORDER_MODE) rzLeave();
    list = [];
    rows = noPlanNote();
  } else if (REORDER_MODE){
    /* REORDER MODE READS THE FULL, UNFILTERED CORPUS, IN THE DRAFT'S ORDER — never
       `applyFilters()`. See `toolbar`'s own comment for why: the write is always the whole
       order, and a filtered or re-sorted view would make that write a claim about rows the reader
       never saw. `placed` and `unplaced` are rendered as ONE `.rows` list with ONE line between
       them — never the two named sections ("Your order" / "Not placed") this mode used to bring
       back as a page of its own. Each placed row is told its position and the count, which is
       what its box shows and its name says. */
    const placed = draftPlaced();
    const unplaced = draftUnplaced();
    list = placed.concat(unplaced);
    if (!list.some(p => p.id === RZ_ACTIVE)) RZ_ACTIVE = list.length ? list[0].id : "";
    rows = placed.map((p, i) => rowHtml(p, { reorder: true, zone: "placed", pos: i + 1, of: placed.length })).join("")
      + boundaryHtml()
      + unplaced.map(p => rowHtml(p, { reorder: true, zone: "unplaced", of: placed.length })).join("");
  } else {
    list = applyFilters();
    LISTED = new Set(list.map(p => p.id));
    VIEW_ORDER = sortKey === "priority" ? list.filter(isPlaced).map(authoredOf).sort((a, b) => a - b) : null;
    if (!list.length){
      /* THE SENTENCE THE READER CAME FOR. Under the narrowed list (PRD 0839) an empty view is the
         ANSWER — "you are not responsible for any program yet" — with the way out named, and the
         clear control still in the toolbar. Under `needs you` alone it is the answer too. Any
         other narrowing says so. */
      rows = mineOn && RZ_VIEWER
        ? `<p class="empty-note">You are not responsible for any program yet.
          <span class="sub">A teammate sets who is responsible from a program's row. Or clear the filter to see every program on this install.</span></p>`
        : filters.has(NEEDS_YOU) && filters.size === 1
          ? `<p class="empty-note">Nothing needs you &mdash; no program has a question waiting or a move only you can make.</p>`
          : `<p class="empty-note">Nothing matches these filters.</p>`;
    } else {
      /* THE SAME LINE, AT REST, IS A GROUP HEADER — the list pages' `.qg` — so the programs a
         person placed and the ones they did not are two groups of the one card, each with its
         count. Only under the priority sort: every other sort interleaves placed and unplaced on
         purpose, and a line drawn through that would claim a boundary that is not there, so it is
         one group under the sort's own name. */
      const boundary = sortKey === "priority" ? list.findIndex(p => !isPlaced(p)) : -1;
      const sortLabel = (SORTS.find(sk => sk[0] === sortKey) || SORTS[0])[1];
      rows = boundary > 0
        ? boardGroup("placed", "In your order", "the order a person set, top first", list.slice(0, boundary), { markUnplaced: true })
          + boardGroup("unplaced", "Not in your order", "listed after the programs you placed", list.slice(boundary), { markUnplaced: true })
        : sortKey === "priority" && boundary === 0
          ? boardGroup("unplaced", "Not in your order", "nobody has placed a program yet", list, {})
          : boardGroup("all", sortKey === "priority" ? "In your order" : "Programs in play",
              sortKey === "priority" ? "the order a person set, top first" : `sorted by ${sortLabel}`, list, {});
    }
  }
  /* THE LAST STAT IS BAR COVERAGE, and it is a count rather than a finding. A bar is optional
     at both tiers, so `board.py` deliberately declines to put a row on every entity without
     one — that would teach a reader to skip the view. The gap between this number and the two
     to its left is the honest way to state the same gap once, in one place.

     EVERY OTHER STAT COUNTS THE PLAN. `active` leaves out the parked programs, so a withdrawn
     one is not "stalled" and a waived one is not "complete"; the two groups at the foot carry
     their own counts, which is the only place those numbers appear. */
  const active = activePrograms();
  /* THE LIVE REGION SPEAKS OUT OF THE MODE — "Order saved." on the list that shows the saved order
     — AND KEEPS SAYING IT UNTIL THE PERSON'S NEXT ACT (ENG-10701, RK-01). It used to be cleared
     after the render that carried it, so a repaint the person did not ask for — the corpus re-read
     a save's own event brings, the heartbeat — wiped the confirmation 0.3 s after it appeared. A
     status is superseded by what the reader does next (a click, a navigation, entering the mode),
     never by what the page does on its own. */
  const said = REORDER_ANNOUNCE;
  /* THE FIGURES ARE THE BAR'S ONE-LINE STATUS, where the list pages keep theirs (the Queue's
     `.qbar`), and the Reorder act sits at the bar's end the way the Workstation's own act does.
     `stalled` takes its tone only on a count that is there: a red `0` is the page crying wolf on
     its calmest day. */
  const tally = programTally();
  const stalled = D.programs.filter(isStalled).length;
  const figures = [`<span><b>${tally.inPlay}</b> of ${tally.all} programs in play</span>`,
    `<span><b>${D.totals.slices}</b> slices</span>`,
    `<span><b>${D.totals.live}</b> live PRDs</span>`,
    `<span><b>${active.filter(p => p.complete).length}</b> ${STATE.complete}</span>`,
    `<span${stalled ? ` class="attn"` : ""}><b>${stalled}</b> stalled</span>`,
    `<span><b>${D.totals.bars}</b> of ${D.totals.programs + D.totals.slices} have success criteria</span>`];
  /* ONE CARD: the live groups, then the two parked folds as groups of the same card. Reorder mode
     keeps its one `.rows` list — the drag reads it whole — and draws no folds. */
  const card = REORDER_MODE || noPlan()
    ? `<div class="rows"${REORDER_MODE ? ' data-rz-list="all"' : ""}>${rows}</div>`
    : `<div class="ql pl">${rows}${
      parkedSection("waived", "Proof waived", "No composed proof is planned, and the programs baseline " +
        "says so with a reason beside each id. Out of every count above: a decision is not a gap.")}${
      parkedSection("withdrawn", "Withdrawn",
        "Out of the plan by a register decision — a decision record, or a successor the work folded " +
        "into. Nothing dispatches into these, and no finding asks anybody to move them.")}</div>`;
  return pageHead(boardName()) +
    (noPlan() ? "" : `<div class="qbar pl-bar"><p class="qstat">${figures.join(" &middot; ")}</p>${reorderToggle()}</div>`) +
    `${noPlan() ? "" : REORDER_MODE ? rzLead() : toolbar(list.length, filterBase().length)}${!REORDER_MODE && (REORDER || said)
      ? `<div class="lgn" id="rz-live" aria-live="polite">${esc(said)}</div>` : ""}
    ${card}${REORDER_MODE ? reorderBar(said) : ""}`;
}

/* ONE LIVE GROUP OF THE CARD, drawn as the Queue draws one. Whether a reader closed it is module
   state rather than DOM, for the Queue's reason: the page repaints on every corpus read. */
let BOARD_SHUT = {};
function boardGroup(g, name, hint, list, opts){
  if (!list.length) return "";
  return listGroup("pg", g, { open: !BOARD_SHUT[g], dot: g, name, count: list.length, hint,
    rows: progCols() + list.map(p => rowHtml(p, opts)).join("") });
}

/* ONE COLLAPSED GROUP PER PARKED STATE, at the foot, native `<details>` so the fold needs no
   state of its own: closed on arrival, and a reader who opens it gets the same rows the list
   above draws — with the register's own words for the decision on each. Absent entirely when
   the state has no programs, rather than an empty heading claiming a category. Hidden in
   Reorder mode: these rows are not part of the order being written, and a drag target that
   is not in the list is a row the write would silently drop. */
/* THE PROGRAMS THE LIST ABOVE DREW, so a fold never draws one a second time (ENG-10683). Only `needs you`
   reaches a parked program, and production drew PG-10, PG-18 and PG-23 twice under it — once in the
   list, once in their fold. `viewBoard` sets this before the folds render; a program the list shows is
   the list's, and the fold keeps the rest of the register's record. */
let LISTED = new Set();
function parkedSection(state, title, blurb){
  if (REORDER_MODE) return "";
  const rows = D.programs.filter(p => p.state === state && !LISTED.has(p.id) && passesFilters(p, true))
    .sort((a, b) => a.id.localeCompare(b.id));
  if (!rows.length) return "";
  /* A GROUP OF THE CARD, NOT A SECTION UNDER IT — the `.qg` header, its count and its state
     chip; the register's sentence for the decision is the header's hint and, whole, its tip. Still
     a native `<details>`, so it is closed on arrival and needs no state of its own. */
  return `<details class="qg parked" data-parked="${state}">
    <summary class="qg-h" title="${esc(blurb)}"><span class="tri"></span><i class="qg-i" data-pg="${state}"></i><span class="qg-n">${esc(title)}</span><span class="n">${rows.length}</span>
      <span class="chip ${state}">${esc(STATE[state])}</span><span class="qg-hint">${esc(blurb)}</span></summary>
    <div class="qg-rows">${progCols()}${rows.map(p => rowHtml(p, {})).join("")}</div>
  </details>`;
}

/* ── 3. Entity pages, one shape ──────────────────────────────────────────── */

/* WHAT MUST SHIP BEFORE THIS PROGRAM CAN BE PROVEN — the completion rule, drawn.
   A program completes when every one of its cuts is complete AND its own composed proof has
   shipped. Both halves were already on this page and neither was legible: the cuts were a flat
   list in authored order, which says nothing about what may start first, and the proof was a
   fact line beside four other fact lines, which says nothing about it being the LAST thing.

   THE NODE SET IS THE CLOSURE, NOT THE PROGRAM. That is the whole point and it is why this is
   not `viewDeps` filtered by program: `viewDeps` answers "what may the fleet start next,
   anywhere", one graph over every program, and its `ready` flag gates dispatch. This answers
   "what stands between this program and its proof", and the honest answer usually includes
   other people's work. Rendering only `p.sl` would draw a program as one cut from done while
   the PRDs its own PRDs `depends_on` — often another program's — are still standing.

   THE SAME BUILD STEPS AS `viewDeps`, over the same graph (`waveG`): PRDs and slices placed by
   `board.py`'s `prd_waves`, drawn with the same node (`waveNode`), so a PRD reads the same step
   on both pages.

   THE HIGHLIGHT COMES FOR FREE and that is why the container keeps `id="waves"` and the nodes
   keep `data-node`: `lightChain` is bound at the document, reads those two, and lights the
   transitive closure through `closure(id, "up"|"down")`. Only nodes drawn here can light,
   which is correct — a prerequisite outside this program's chain is not this page's business. */
/* A NODE ON EITHER MAP IS A LINK TO ITS SLICE (ENG-10590), opened with the same attributes the
   chain highlight reads (`data-node`). The id is escaped on every write — the map's raw
   interpolation was pinned as a known defect and is now pinned as fixed. */
function wnodeOpen(s, extra){
  return `<a class="wnode ${esc(s.state)}${extra}" href="${esc(urlFor("slice:" + s.id))}" data-go="slice:${esc(s.id)}" data-node="${esc(s.id)}">`;
}

const WAVE_KINDS = [["prd", "PRDs"], ["slice", "Slices"], ["program", "Programs"]];

/* THE LEGEND BOTH MAPS SHARE: the three relationships the highlight lights, then the three kinds
   of node — each swatch drawn with the node's own class, so the key is the thing it explains. */
function waveLegend(){
  return `<div class="legend"><span class="lg up">prerequisite</span>
      <span class="lg self">this one</span><span class="lg down">waits on it</span>
      <span class="lk k-prd">PRD</span><span class="lk k-slice">slice</span><span class="lk k-program">program</span>
      <span class="lgn" id="chain" aria-live="polite"></span></div>`;
}
const KIND_RANK = { program: 0, slice: 1, prd: 2 };

/* ONE NODE OF THE BUILD-STEP GRAPH, whichever kind. The kind is said twice — a tag in the id line
   and a class (`k-prd` / `k-slice` / `k-program`) the stylesheet gives each its own weight — so a
   reader can tell a PRD from the cut it sits in at a glance and a screen reader hears the word.
   Every node states what it waits on and what waits on it AT REST; lighting the chain only adds
   the transitive closure of two numbers already on the screen. `home` marks a node belonging to
   another program as `foreign`, on the program page. */
function waveNode(g, n, home){
  const x = n.x, up = g.up[n.id], down = g.down[n.id];
  const foreign = home && n.prog !== home ? " foreign" : "";
  const count = (k, one, many) => `${k} ${k === 1 ? one : many}`;
  if (n.kind === "slice"){
    const prds = [...up].filter(id => g.nodes[id].kind === "prd").length;
    /* THE CUT'S AUTHORED ORDER, SAID AND NOT DRAWN AS A WAIT: `Depends on` places nothing in a
       step any more, but it is still what the register says about which cut comes after which. */
    const after = (x.dep || []).length
      ? `<span class="none" data-tip="${esc("Ordered after " + x.dep.join(", ") + " in the slice register. Order only: this cut waits on its PRDs, not on those cuts.")}">after ${esc(x.dep.length > 2 ? x.dep.length + " slices" : x.dep.join(", "))}</span>` : "";
    return `${wnodeOpen(x, " k-slice" + foreign)}
        <div class="wi"><span class="wk">slice</span> ${esc(x.id)} &middot; ${esc(x.program)}${nodeRank(x, "&middot;")}</div>
        <div class="wn">${esc(x.name)}</div>
        <div class="we">
          ${prds ? `<span class="up">waits on ${count(prds, "PRD", "PRDs")}</span>` : `<span class="none">no open PRD</span>`}
          ${after}${estimateChip("slice", x.id)}
        </div>
      </a>`;
  }
  if (n.kind === "program"){
    const slices = [...up].filter(id => g.nodes[id].kind === "slice").length;
    const proofs = [...up].filter(id => g.nodes[id].kind === "prd").length;
    return `<a class="wnode k-program ${esc(x.state || "")}${foreign}" href="${esc(urlFor("program:" + x.id))}" data-go="program:${esc(x.id)}" data-node="${esc(x.id)}">
        <div class="wi"><span class="wk">program</span> ${esc(x.id)}</div>
        <div class="wn">${esc(x.name)}</div>
        <div class="we">
          ${slices ? `<span class="up">waits on ${count(slices, "slice", "slices")}</span>` : ""}
          ${proofs ? `<span class="up">${count(proofs, "proof PRD", "proof PRDs")} open</span>` : ""}
          ${!slices && !proofs ? `<span class="none">nothing open before it</span>` : ""}${estimateChip("program", x.id)}
        </div>
      </a>`;
  }
  const waits = up.size, holds = [...down].filter(id => g.nodes[id].kind === "prd").length;
  /* A PRD'S STATUS IS NOT A SLICE STATE, so it is not coloured through `STATE`: the fleet driving
     it reads as in flight, one still being written reads as the brass of work a person owes. */
  const tone = x.status === "shipped" ? " complete" : x.fleet ? " flight" : ["stub", "prd-drafted"].includes(x.status) ? " unproven" : "";
  return `<a class="wnode k-prd${tone}${foreign}" href="${esc(urlFor("prd:" + x.n))}" data-go="prd:${esc(x.n)}" data-node="${esc(x.n)}">
        <div class="wi"><span class="wk">PRD</span> ${esc(x.n)} · ${x.slice ? esc(x.slice) : "no slice"}</div>
        <div class="wn">${esc(x.title || "")}</div>
        <div class="we">
          ${waits ? `<span class="up">waits on ${waits}</span>` : ""}
          ${holds ? `<span class="down">blocks ${holds}</span>` : ""}
          <span class="none">${esc(x.status || "")}</span>${estimateChip("prd", x.n)}
        </div>
      </a>`;
}

/* THE COLUMNS: one per build step, the nodes in it grouped by the program they belong to — a
   step holding twenty-six PRDs across nine programs reads as nine short lists rather than one
   long one. Groups follow the human's program order (unranked last), `home` first on a program
   page; inside a group the program comes first, then its slices, then its PRDs, the ones holding
   up the most first. `group: false` draws a column as one list. */
function waveColumns(g, ids, o){
  const opts = o || {};
  const nodes = ids.map(id => g.nodes[id]).filter(Boolean);
  const max = nodes.reduce((m, n) => Math.max(m, n.x.wave), -1);
  const progRank = id => id === opts.home ? -1 : (PG[id] && Number(PG[id].rank)) || 1e6;
  const cols = [];
  for (let w = 0; w <= max; w++){
    const here = nodes.filter(n => n.x.wave === w);
    if (!here.length) continue;
    here.sort((a, b) => (progRank(a.prog) - progRank(b.prog)) || (a.prog === b.prog ? 0 : !a.prog ? 1 : !b.prog ? -1 : a.prog.localeCompare(b.prog))
      || (KIND_RANK[a.kind] - KIND_RANK[b.kind]) || (g.down[b.id].size - g.down[a.id].size) || a.id.localeCompare(b.id));
    let body = "", at = null;
    here.forEach(n => {
      if (opts.group !== false && n.prog !== at){
        at = n.prog;
        const pp = PG[n.prog];
        body += `<div class="wg">${n.prog ? `${esc(n.prog)}${pp ? " &middot; " + esc(pp.name) : ""}` : "in no slice"}</div>`;
      }
      body += waveNode(g, n, opts.home);
    });
    cols.push(`<div class="wave"><h4>${w === 0 ? term("wave", "Build step") : "Build step"} ${w} &middot; ${here.length}</h4><div class="inner">
      ${body}</div></div>`);
  }
  return cols;
}

function chainSection(p, live, finishInNeeds){
  const g = waveG();
  const cols = waveColumns(g, live.map(n => n.id), { home: p.id, group: false });
  /* THE TERMINAL COLUMN, AND THE ONE READING NOTHING ELSE ON THE BOARD GIVES. An empty cell
     reads `unproven`, which is a true statement and not an oversight — but a program that names
     no proof can never complete however much of it ships, and that deserves a node saying so
     rather than a blank. `proofok` is the register's own arithmetic; this only draws it. */
  const proof = p.proof.length
    ? p.proof.map(n => {
        if (isDrill(n)){
          /* A drill record has no page and no status to advance: the node names the stem, says
             what the record proves, and carries the verdict — the one fact that decides it. */
          const rec = drillOf(n);
          return `<div class="wnode proof ${rec && rec.verdict === "passed" ? "complete" : "unproven"}">
            <div class="wi">${esc(n)}</div>
            <div class="wn">${rec ? "a drill record" + (rec.daemonSha ? " proving " + esc(rec.daemonSha.slice(0, 12)) : "")
                                  : "no such drill record in the plan"}</div>
            <div class="we">${rec && rec.verdict === "passed"
              ? `<span class="down">passed</span>`
              : `<span class="up">${esc(rec ? rec.verdict : "not in the plan")}</span>`}</div>
          </div>`;
        }
        const r = PRD[n];
        /* `r.status` is a PRD status and NOT a slice state, so it does not go through `STATE` —
           that map holds `flight`/`complete`/`unproven` and would silently render nothing for
           `prd-drafted`. A proof naming a number the corpus does not carry is its own finding
           and says so rather than drawing an empty node. */
        /* WHAT IT PROVES, said (ENG-10599): the node names the PRD as a member of its cut AND as
           the program's proof — and where that cut's own proof is waived, says both are true
           in one breath, because the chip on the slice row two sections down says "proof
           waived" about the same cut. */
        const cut = r && r.slice ? SL[r.slice] : null;
        const waivedCut = cut && cut.state === "waived";
        return `<a class="wnode proof ${p.proofok ? "complete" : "flight"}" href="${esc(urlFor("prd:" + n))}" data-go="prd:${esc(n)}">
          <div class="wi">${esc(n)}${r && r.slice ? " &middot; in " + esc(r.slice) : ""} &middot; proves the program</div>
          <div class="wn">${esc(r && r.title ? r.title : "the composed proof")}</div>
          <div class="we">${p.proofok
            ? `<span class="down">shipped</span>`
            : `<span class="up">${esc(r ? r.status : "not in the plan")}</span>`}</div>
          ${waivedCut ? `<div class="wx">${esc(r.slice)}&#39;s own proof is waived &mdash; this PRD proves the program, not the slice.</div>` : ""}
        </a>`;
      }).join("")
    /* `unproven` and not `attn`: `.wnode` carries exactly three state rules — `complete`,
       `flight`, `unproven` — and `attn` is a `.chip` class with no `.wnode` rule behind it, so
       it would render as an unstyled grey node that looks like a data gap rather than a
       finding. Brass is also the honest colour: an empty cell reads `unproven`. */
    : `<div class="wnode proof unproven"><div class="wi">no proof named</div>
        <div class="wn">this program can never be proven</div>
        <div class="we"><span class="up">unproven</span></div></div>`;
  /* THE OPEN BUGS AND TASKS ON THIS PROGRAM (PROD PG-21), the host's `work` (`candidates.program_work`): what
     carries the program's label or cites one of its cuts. PROD's PG-21 listed one slice and its proof here while
     the bugs fixing SL-188's bar — the work its owed proof waited on — appeared nowhere on the page. Each node is
     the issue, its state and the cut it cites; the host decides what is linked, this only draws it. */
  const work = (deliveryOf(p.id) || {}).work || [];
  if (work.length){
    const nodes = work.map(w => {
      const key = String(w.issue || "");
      const tone = w.fleet ? " flight" : " unproven";
      return `<a class="wnode k-issue${tone}" href="${esc(urlFor("issue:" + key))}" data-go="issue:${esc(key)}" data-node="${esc(key)}">
          <div class="wi"><span class="wk">${esc(String(w.kind || "issue"))}</span> ${esc(key)}${w.cut ? " &middot; " + esc(String(w.cut)) : ""}</div>
          <div class="wn">${esc(String(w.title || ""))}</div>
          <div class="we"><span class="${w.fleet ? "up" : "none"}">${esc(String(w.state || ""))}</span>${
            w.because ? `<span class="none">waits on ${esc(String(w.because))}</span>` : ""}</div>
        </a>`;
    }).join("");
    cols.push(`<div class="wave"><h4>Open bugs &amp; tasks &middot; ${work.length}</h4><div class="inner">${nodes}</div></div>`);
  }
  cols.push(`<div class="wave"><h4>Proof</h4><div class="inner">${proof}</div></div>`);

  /* NO `strip` HERE, and that is a slot decision rather than a taste one. `viewDeps` is a
     standalone page and states its figures in one; an entity page states them in `entityHeader`,
     where every other number about this program already is. It also matters mechanically: the
     section-order test reads the FIRST element of each slot class, so a strip drawn below the
     "To do here" list would assert the stats slot after the list slot and fail — correctly,
     because that is not the order the operator put them in. The two counts this view would have
     put in a strip are one fact line above. */
  return `<section class="grp"><div class="grp-h">
      <h3>What must ship to prove this</h3><span class="n">${live.length + work.length}</span></div>
    ${waveLegend()}
    ${live.length ? "" : chainClear(p, finishInNeeds)}
    <div class="waves" id="waves">${cols.join("")}</div>
  </section>`;
}

/* WHAT AN EMPTY CHAIN MEANS, WHICH IS THREE THINGS (ENG-10589). The one sentence it used to say
   — "only the proof remains" — was printed over a program whose proof had SHIPPED, because the
   note was written before a chain could be empty for any other reason. Proven; proof shipped but
   a waived cut holds the program short of proven; or proof outstanding. */
/* THE WAIVED CUTS OF A PROGRAM, by id, off its own served cuts — the record a close names. */
function waivedCuts(p){ return (p.sl || []).filter(s => s.state === "waived").map(s => s.id); }
function waivedList(p){
  const ids = waivedCuts(p);
  return ids.length < 2 ? ids.join("") : `${ids.slice(0, -1).join(", ")} and ${ids[ids.length - 1]}`;
}

function chainClear(p, finishInNeeds){
  /* "EVERY SLICE" ONLY WHEN EVERY SLICE (ENG-10683). The walk of production's program pages read "Every slice in
     this chain is proven" over PG-12 and PG-22 (withdrawn slices), the withdrawn PG-14 and PG-20 (nothing done)
     and the waived PG-10 and PG-23 (waived slices). Each emptiness now says what its counts are. */
  const done = Number(p.done) || 0, waived = Number(p.waivedSlices) || 0, withdrawn = Number(p.withdrawnSlices) || 0;
  /* A WAIVED CUT IS SETTLED: the program closes over it, so a proven program names its
     waived cuts beside the withdrawn ones rather than calling them a gap. */
  const parked = [waivedCuts(p).length ? `${waivedList(p)} waived by decision` : "", withdrawn ? `${withdrawn} withdrawn` : ""]
    .filter(Boolean).join(", ");
  if (p.closed){
    return `<p class="empty-note">The proof shipped, every slice this program kept is settled, and the program
      was closed on ${esc(String(p.closed))}. Nothing is left on it.</p>`;
  }
  if (p.complete && waivedCuts(p).length){
    /* The waived cuts are KEPT cuts, so "the N this program kept are proven" would undercount them. */
    const proven = done ? `${done} slice${done === 1 ? "" : "s"} ${esc(STATE.complete)}, ` : "";
    return `<p class="empty-note">${proven}${parked}, and the proof shipped. Nothing stands between this program and
      closing.</p>`;
  }
  if (p.complete && parked){
    return `<p class="empty-note">The ${done} slice${done === 1 ? "" : "s"} this program kept ${done === 1 ? "is" : "are"}
      ${esc(STATE.complete)} (${parked}) and the proof shipped. Nothing stands between this program and
      closing.</p>`;
  }
  if (p.complete){
    return `<p class="empty-note">Every slice in this chain is ${esc(STATE.complete)} and the proof
      shipped. Nothing stands between this program and being ${esc(STATE.complete)}.</p>`;
  }
  if (p.proofok){
    return `<p class="empty-note">No open slice stands before the proof, and the proof shipped.</p>`;
  }
  if (p.state === "withdrawn"){
    return `<p class="empty-note">This program was withdrawn from the plan, so nothing in this chain is waiting to be
      proven.</p>`;
  }
  const counted = [done ? `${done} slice${done === 1 ? "" : "s"} done` : "no slice done"];
  if (waived) counted.push(`${waived} waived by a written decision`);
  if (withdrawn) counted.push(`${withdrawn} withdrawn`);
  const lead = counted.length === 1 ? "" : `This program has ${counted.slice(0, -1).join(", ")} and ${counted[counted.length - 1]}.`;
  if (p.waived && !(p.proof || []).length){
    return `<p class="empty-note">${lead || "Every slice of this program is done."} Its proof is waived by a written
      decision${waived ? " too" : ""}, so nothing in this chain is left to prove.</p>`;
  }
  if (lead){
    return `<p class="empty-note">${lead} Only the proof remains &mdash; which is exactly what
      <b>${esc(STATE["awaiting-proof"])}</b> means.</p>`;
  }
  return `<p class="empty-note">Every slice in this chain is ${esc(STATE.complete)}. Only the
      proof remains &mdash; which is exactly what <b>${esc(STATE["awaiting-proof"])}</b>
      means, and the one state a count of finished slices cannot distinguish from done.</p>`;
}

/* ── the program lifecycle ─────────────────────────────────────────────── */
/*
 * A PROGRAM IS NOT A LADDER. Questions, shaping and delivery run side by side, and shaping reopens
 * whenever new work turns up mid-delivery; closing is the one step that truly comes last. So the
 * program page states four tracks at a glance (`whereItIs`), lists every move a person owes in the
 * order it is worked (`todoList`), and says what delivery waits on when it cannot start yet
 * (`deliveryGates`). Every reading here is off the payload — `phase`, `stage`, `order` are
 * `board.py`'s — and nothing is re-derived.
 */
const STAGE_TITLE = { shaping: "Shaping", delivery: "Delivery", close: "Close" };

function stageOf(a){ return STAGE_TITLE[a.stage] ? a.stage : "shaping"; }

/* Whether the program has any PRD written at all — the point where delivery becomes a thing to
   talk about. Before it, the Delivery track is not drawn. */
function prdsWritten(p){ return p.sl.some(s => (s.prds || []).length); }

/* Whether any PRD of the program sits at a status the fleet builds from — planned, or past it. A
   program is "in flight" the moment any PRD is open, stubs included, so `p.flight` cannot say this. */
function fleetBuilding(p){ return p.sl.some(s => (s.prds || []).some(r => r.fleet)); }

/* Whether the program has a proof in hand — named or waived. Close is never offered without one. */
function proofSettled(p){ return !!((p.proof || []).length || p.waived); }

/* NOTHING LEFT TO BUILD: slices are cut and none the program kept is open — each is done, waived or
   withdrawn. Delivery then has nothing to move, and says so calmly. */
function nothingToBuild(p){ return !!(p.sl || []).length && !p.sl.some(openSlice); }

/* THE ONE STEPPER — a line of stops with one pip each, shared by the bug, idea and program pages
   (the host's `fdTimeline` hands its stops here, so there is one renderer and one stylesheet). A
   stop is `done`, `here` (brass: its result waits on the reader), `run` (the fleet is in it now),
   `stopped` (a run that ended short), `off` (dashed: a stop the page cannot vouch for) or `gone`
   (a terminal that replaced the rest). Each carries one short word (`name`), one mono sub-line
   (`sub`, clipped with its whole text on `title`) and, optionally, one sentence (`why`).

   AT A PHONE'S WIDTH THE ROW OF STOPS DOES NOT FIT — five columns of seventy pixels wrapped every
   label and broke sub-lines mid-word (ENG-12483). There the list is kept for a screen reader and
   the eye gets a pill per stop, the CURRENT stop's name with "step N of M", its sub-line and its
   sentence. No vertical list and no "show all steps": the operator's call, the pills are enough.
   `next` adds one "Next:" line naming the stop after the current one (the program page's).

   THE CURRENT STOP is the first that waits on the reader or ended short, else the first the fleet
   is in, else the last one finished, else the first. */
function stepper(stops, label, opts = {}){
  const list = stops || [];
  const plain = h => String(h || "").replace(/<[^>]*>/g, "").replace(/&middot;/g, "·").replace(/&amp;/g, "&");
  let at = list.findIndex(s => s.state === "here" || s.state === "stopped");
  if (at < 0) at = list.findIndex(s => s.state === "run");
  if (at < 0) for (let i = list.length - 1; i >= 0; i--){ if (list[i].state === "done" || list[i].state === "gone"){ at = i; break; } }
  if (at < 0) at = 0;
  const cur = list[at] || {};
  const nxt = opts.next ? list[at + 1] : null;
  const rows = list.map(stop => {
    const sub = String(stop.sub || "");
    const tip = plain(sub);
    return `<li class="fd-stop${stop.state ? " " + stop.state : ""}"><i class="fd-pip" aria-hidden="true"></i><b>${stop.name}</b><span${
      tip ? ` title="${esc(tip)}"` : ""}>${sub || "&nbsp;"}</span>${stop.why ? `<em class="fd-why">${stop.why}</em>` : ""}</li>`;
  }).join("");
  const phone = list.length ? `<div class="stp-ph" aria-hidden="true"><div class="stp-bar">${
      list.map(s => `<i${s.state ? ` class="${s.state}"` : ""}></i>`).join("")}</div>
    <div class="stp-now${cur.state ? " " + cur.state : ""}"><b>${cur.name}</b><span class="stp-n">step ${at + 1} of ${list.length}</span></div>${
      cur.sub ? `<div class="stp-sub">${cur.sub}</div>` : ""}${cur.why ? `<div class="stp-why">${cur.why}</div>` : ""}${
      nxt ? `<div class="stp-next"><span>Next:</span> ${nxt.name}${nxt.sub ? " &middot; " + nxt.sub : ""}</div>` : ""}</div>` : "";
  return `<div class="stp"><ol class="fd-tl" style="--n:${list.length}" aria-label="${esc(label || "Where it stands")}">${rows}</ol>${phone}</div>`;
}

function lcStop(name, state, sub, why){ return { name, state, sub, why }; }

/* THE PROGRAM'S LIFECYCLE: ONE LINE, THREE STEPS, EXACTLY ONE OF THEM CURRENT (PROD PG-21, after 0.7.182).

   It used to be four stops drawn as parallel tracks — Questions, Shaping, Delivery, Close — each lit by
   its own predicate, so PG-21 read Questions (brass) → Shaping (green check) → Delivery (brass): an
   attention step before a done one and two "current" steps at once. "Questions" is not a step a program
   passes through; waiting on a person is a STATE of the step the program is in.

   THE MODEL (`programLifecycle`, held by `tests/test_board_js_lifecycle.py` over every state it can
   produce): the steps are Shaping → Delivery → Close, the current one is the register's own word for
   where the program is in its life (`p.phase`, `board.py::program_phase` — which never moves a program
   back: a new slice cut mid-delivery reopens shaping beside delivery, it does not make shaping current
   again), every step before it is `done` and every step after it `upcoming`. Monotonic by construction.
   The current step carries a `tone` (`here` — a person owes it something; `run` — the fleet is on it;
   `stopped`; `done` — a closed program's last step) and an optional `badge`, e.g. "2 questions for you".
   A closed program's current step is Close, with tone `done`. Withdrawn programs have no lifecycle. */
const LIFECYCLE_STEPS = ["Shaping", "Delivery", "Close"];
/* A PASSED STEP'S SUB-LINE: the English word for a step behind the program, never the tracker's position. */
const STEP_DONE = "Done";
const PHASE_STEP = { shaping: 0, building: 1, closing: 2, proven: 2, waived: 2, closed: 2 };

function lifecycleIndex(p){
  if (p.closed || p.phase === "closed" || p.complete) return 2;
  const i = PHASE_STEP[String(p.phase || "")];
  return i === undefined ? 0 : i;
}

function programLifecycle(p, todos, driver, given){
  if (p.state === "withdrawn") return [];
  const list = todos || [];
  const at = lifecycleIndex(p);
  /* `given` IS FOR THE MODEL TEST: the drive's word and the question count a page reads off its host, handed in
     so every combination can be enumerated without a host. A page passes nothing. */
  const q = given && "q" in given ? Number(given.q) || 0 : questionsWaiting(p);
  const d = given && "d" in given ? given.d : deliveryOf(p.id);
  const driven = !!d && DRIVEN_READINGS.includes(d.reading);
  const badge = q ? `${q} question${q === 1 ? "" : "s"} for you` : "";
  const shaping = list.filter(a => stageOf(a) === "shaping").length;
  const closeRows = list.filter(a => stageOf(a) === "close").length;
  const toPlan = (p.sl || []).filter(openSlice).reduce((n, s) => n + ((s.prds || []).length
    ? (s.prds || []).filter(r => ["stub", "prd-drafted", "designed"].includes(r.status)).length : 1), 0);
  const live = Number(p.livePRDs) || 0;
  /* THE CURRENT STEP'S WORDS — one sub-line and one sentence, and its tone. Nothing here names a command:
     what a person can do is on the page below it, as questions with their answers. */
  function shapingNow(){
    if (q) return ["here", badge, "The fleet asked something it needs before it can build."];
    if (shaping) return ["here", `${shaping} to do`, "Moves only you can make before the fleet can build."];
    if (driven) return ["run", toPlan ? `${toPlan} still to plan` : "With the fleet",
      `Cut and planned by ${FLEET.actor} as the program is driven.`];
    if (d && d.reading === "stopped") return ["stopped", "Stopped", "Delivery is stopped. Nothing moves until somebody starts driving it again."];
    return ["here", toPlan ? `${toPlan} still to plan` : "Not planned yet", "Nothing is planned for the fleet yet."];
  }
  function deliveryNow(){
    if (q) return ["here", badge, "The delivery agent asked something and goes on once it is answered."];
    if (d && d.reading === "running") return ["run", "Cycle running", "A delivery cycle is working on this program now."];
    if (d && d.reading === "waiting-on-you") return ["here", d.waitingOn || "Waiting on you",
      "The fleet has built everything it can; what is left needs a person."];
    if (d && d.reading === "fleet-then-you") return ["run", "With the fleet", "The fleet is working on what has to land first."];
    if (d && d.reading === "between") return ["run", "Driven", "The fleet starts the next delivery cycle on its own."];
    if (d && d.reading === "stopped") return ["stopped", "Stopped", fleetBuilding(p)
      ? "Delivery is stopped; PRDs already planned still build. Start driving to move the rest."
      : "Delivery is stopped. Nothing moves until somebody starts driving it again."];
    if (fleetBuilding(p)) return ["run", "Building", "The fleet has planned work."];
    if (p.flight) return ["here", `${live} PRD${live === 1 ? "" : "s"} in planning`, "Nothing is planned for the fleet yet."];
    return ["here", "Idle", driver ? "Nothing is moving." : "Waits on the checks below."];
  }
  function closeNow(){
    if (p.closed) return ["done", "Closed", `Closed ${esc(String(p.closed))}: the closing check passed.`];
    if (p.complete) return ["done", String(STATE.complete), waivedCuts(p).length
      ? `The proof shipped; ${esc(waivedList(p))} ${waivedCuts(p).length === 1 ? "was" : "were"} waived by decision.`
      : "The proof shipped and every kept slice is done."];
    if (q) return ["here", badge, "The fleet asked something before it can close."];
    if (closeRows) return ["here", `${closeRows} to do`, p.proofok ? "The proof shipped; closing it is yours."
      : "Every slice is done or waived; the proof is what is left."];
    return ["run", "Closing", "The closing check runs as a run of its own."];
  }
  const now = [shapingNow, deliveryNow, closeNow][at]();
  /* A PASSED STEP STAYS PASSED, AND SAYS WHAT IS STILL OPEN BESIDE IT: a slice cut mid-delivery reopens planning,
     never the Shaping step ("it never moves a program back", `program_phase`) — so Shaping reads done, with what is
     still to plan, and never "every PRD is planned" over a stub the page lists two lines down. */
  const doneWords = [
    toPlan ? [`${toPlan} still to plan`, driven ? `Planned by ${FLEET.actor} as the program is driven.` : "Planned as delivery goes."]
      : [STEP_DONE, "Every slice is cut."],
    [STEP_DONE, waivedCuts(p).length ? "Every slice is done or waived." : "Every slice is done."],
    [STEP_DONE, "Closed."],
  ];
  const nslKept = Number(p.nsl) - (Number(p.withdrawnSlices) || 0);
  const upcomingWords = [
    ["", ""],
    ["Not yet", "Starts once a PRD is written and planned."],
    [Number(p.done) ? `${Number(p.done)} of ${nslKept} slices done` : "Not yet", p.proofok ? "The proof shipped." : "Waits on the proof shipping."],
  ];
  return LIFECYCLE_STEPS.map((name, i) => i < at
    ? { name, state: "done", tone: "done", sub: doneWords[i][0], why: doneWords[i][1], badge: "" }
    : i === at
      ? { name, state: "current", tone: now[0], sub: now[1], why: now[2], badge: now[0] === "done" ? "" : badge }
      : { name, state: "upcoming", tone: "", sub: upcomingWords[i][0], why: upcomingWords[i][1], badge: "" });
}

/* THE STEPPER'S STOPS OFF THE MODEL: a done step is `done`, the current one carries its tone (one highlighted
   pip), an upcoming one is plain grey. The badge rides the current step's sub-line: "Delivery · 2 questions for you". */
function lifecycleStops(steps){
  return steps.map(s => lcStop(s.name, s.state === "upcoming" ? "" : s.tone,
    s.badge && s.badge !== s.sub ? `${s.sub} &middot; ${s.badge}` : s.sub, s.why));
}

function whereItIs(p, todos, driver){
  if (p.state === "withdrawn") return "";
  return `<div class="grp lc-where"><div class="grp-h"><h3>Where it is</h3></div>
    ${stepper(lifecycleStops(programLifecycle(p, todos, driver)), "Where this program is", { next: true })}</div>`;
}

/* A SLICE'S PROGRESS — one horizontal segmented bar on its Slices row (the program stepper's own
   `.stp-bar` segments, so it is the application's one progress idiom) with the count beside it:
   PRDs written, in flight, awaiting proof, proven — read off the slice's own `state` and nothing
   else. A parked cut (waived, withdrawn, every PRD cancelled) draws a greyed bar and no count; its
   chip beside it says which. */
const SLICE_RAIL = {
  empty: ["", "", "", ""],
  flight: ["done", "run", "", ""],
  "awaiting-proof": ["done", "done", "run", ""],
  unproven: ["done", "done", "here", ""],
  complete: ["done", "done", "done", "done"],
};
function sliceRail(s){
  const dots = SLICE_RAIL[s.state];
  const parked = !dots;
  const marks = dots || ["gone", "gone", "gone", "gone"];
  const n = marks.filter(m => m === "done").length;
  return `<span class="sl-prog${parked ? " parked" : ""}"${parked ? ' aria-hidden="true"' : ` role="img" aria-label="${n} of 4 steps done"`}><span class="stp-bar">${
    marks.map(m => `<i${m ? ` class="${m}"` : ""}></i>`).join("")}</span>${parked ? "" : `<b>${n}/4</b>`}</span>`;
}

/* ONE LIST, GROUPED BY TRACK, NUMBERED IN THE ORDER IT IS WORKED — AND THE ONLY LIST OF WHAT IS LEFT (the
   operator, on PG-36: *"WAITING ON YOU and TODO are basically the same thing"*). The page used to
   draw the host's "Waiting on you" card above *Where it is* and this list below it, and a proven program's
   "Close the program" was both, twice. Now every move left on the program is ONE row here, said once, with
   who makes it: the reader (`You`) or the fleet. The record's own rows are the reader's; the host's rows
   (`hostAsks`' `todo`) add what only a host knows — a drive the fleet stopped, a finished drive's ship, a
   driven program's person step, a close the fleet is making itself — and a host row may REPLACE a record
   row of the same move (`replaces`), so a close the fleet runs is never also listed as the reader's.

   THE ORDER IS WHAT BLOCKS COMPLETION: the tracks in the order a program is worked (shaping, delivery,
   close), and inside a track the reader's urgent host rows first (a stopped drive moves nothing until it
   is restarted), then the record's rows most-important-first, then what the fleet is doing itself. The
   count is the reader's moves, the number the program's row on the list carries. `data-todo` stays on it:
   it is where the drive box's "Name a proof" pointer leads (ENG-10704, G-09). */
function whoChip(who){
  return who === "fleet"
    ? `<span class="chip who fleet">${esc(FLEET.Actor || "The automation")}</span>`
    : `<span class="chip who you">You</span>`;
}

function hostTodoItem(r){
  return { id: String(r.id || ""), title: String(r.title || ""), lead: String(r.lead || ""), sub: String(r.why || ""),
    sev: Number(r.sev) || (r.who === "fleet" ? 3 : 1), go: r.go ? String(r.go) : "", chip: "",
    right: typeof r.right === "string" ? r.right : "", who: whoChip(r.who), whole: true, badges: [] };
}

/* A DRIVEN PROGRAM'S ROWS CARRY NO LAUNCH (PROD PG-21): while the fleet drives a program, whatever
   has to run — a slice edit, a proof, a close — is the driver's to dispatch, and a person is handed questions with
   their answers, never a "Start …" or "Run …". A row keeps its words and says who moves it; its command is not a
   button. Only a program NOTHING drives offers a launch, and then at the standard size. */
function drivenByFleet(id){
  const d = deliveryOf(id);
  return !!d && DRIVEN_READINGS.includes(d.reading);
}
function withoutLaunch(a){
  return a.parkedKey ? a : { ...a, cmd: "", fleet: true, waiting: a.waiting || `${FLEET.Actor} dispatches this when it is needed` };
}

function todoList(p, todos, host){
  const t = todoStages(p, todos, host);
  if (!t) return "";
  return `<section class="grp" data-todo="${esc(p.id)}"><div class="grp-h"><h3>To do</h3>
    ${t.yours ? `<span class="n">${t.yours}</span>` : ""}</div>${t.parts}</section>`;
}
/* THE STAGED ROWS AND THE COUNT OF THE ONES A PERSON OWES, for any page's frame (the old page's section, the New UI page's slot). `null` when empty. */
function todoStages(p, todos, host){
  const driven = drivenByFleet(p.id);
  const extra = (host || []).filter(r => r && r.title).map(r => driven && r.right ? { ...r, right: "" } : r);
  if (!todos.length && !extra.length) return null;
  let n = 0;
  const parts = ["shaping", "delivery", "close"].map(st => {
    const rows = todos.filter(a => stageOf(a) === st).map(a => driven ? withoutLaunch(a) : a);
    const mine = extra.filter(r => r.who !== "fleet" && stageOf(r) === st);
    const theirs = extra.filter(r => r.who === "fleet" && stageOf(r) === st);
    if (!rows.length && !mine.length && !theirs.length) return "";
    const items = [...mine.map(hostTodoItem),
                   ...actionItems(rows).map(i => ({ ...i, who: whoChip(driven ? "fleet" : "you"), whole: true })),
                   ...theirs.map(hostTodoItem)].map(i => ({ ...i, num: String(++n) }));
    return `<div class="lc-stage"><h4>${STAGE_TITLE[st]}</h4>${entityList(items)}</div>`;
  }).join("");
  const yours = (driven ? 0 : todos.length) + extra.filter(r => r.who !== "fleet").length;
  return { parts: parts, yours: yours };
}

/* WHAT DELIVERY WAITS ON, WHEN NOTHING CAN START IT. Drawn only once a PRD is written — before
   that there is nothing to deliver and the track says so in its tile — and never on a finished or
   withdrawn program. Three checks, each a fact off the payload; the to-do that settles a failing
   one is already in the list above. */
function deliveryGates(p){
  if (p.state === "withdrawn" || !prdsWritten(p)) return "";
  if (nothingToBuild(p)) return nothingToBuildSection();
  if (p.complete || p.phase === "closing") return "";
  const planned = fleetBuilding(p);
  const gates = [
    [Number(p.nsl) > 0 && !(p.requires && !p.requires.length && !p.flight), "Slices cut, with a build order"],
    [proofSettled(p), "A proof is named, or waived by a written decision"],
    [planned, "At least one planned PRD waiting to be built"],
  ];
  /* ALL THREE HOLD: delivery is startable, and the to-do (or the driver) that starts it is the one
     place that says so. A checklist of ticks beside it would be the page explaining itself. */
  if (gates.every(([ok]) => ok)) return "";
  return `<section class="grp"><div class="grp-h"><h3>Delivery</h3></div>
    <div class="lc-gates"><p>${planned ? "The fleet is building what is planned. Continuous delivery starts once all three hold."
      : "Nothing is being built. Starting delivery becomes a to-do once all three hold."}</p>
    <ul>${gates.map(([ok, t]) => `<li class="${ok ? "ok" : "no"}"><b>${ok ? "&check;" : "&times;"}</b> ${t}</li>`).join("")}</ul>
    </div></section>`;
}

/* THE CALM DELIVERY SECTION: every slice the program kept is done or waived, so there is
   nothing for delivery to move. Neutral, no control, and never an instruction to close — closing is
   the Close to-do's. */
function nothingToBuildSection(){
  return `<section class="grp"><div class="grp-h"><h3>Delivery</h3><span class="n">done</span></div>
    <p class="empty-note">Nothing left to build &mdash; every slice is done or waived.</p></section>`;
}

/* WHEN THE FLEET IS DRIVING A PROGRAM, THE DRIVER OWNS EVERY MOVE BUT THE LAST. The delivery cycle
   writes, designs, plans, refines and starts the work itself, in background sessions with no approval
   (`program/deliver.md`: *"prd:create → background, freely. No human gate"*) — so "Write PRDs for SL-256"
   or "Design PRD 0641" under a program the fleet is driving is the driver's own next move, listed as the
   reader's. The operator's ruling: the driver drives ALL tasks, maybe not the very last. DRIVEN is the
   host's own word (`running` or `between`; a `waiting` drive asked a person something and a `stopped`
   one moves nothing). Hidden are the driver's groups (`DRIVER_GROUPS`); what stays is the close, the
   judgements only a person can write (a proof to name, roots to decide, a stalled or empty program), and
   any PRD parked on a human action — nothing a person must do is ever hidden.
   ONE PREDICATE: the program page and the slice page both filter through it, with the PROGRAM's id. */
const DRIVER_GROUPS = ["promise", "start", "planning", "refine", "finish"];
function driverHandles(a, programId){
  const d = deliveryOf(programId);
  return !!d && ["running", "between", "waiting-on-you", "fleet-then-you"].includes(d.reading)
    && DRIVER_GROUPS.includes(a.group) && !a.parkedKey;
}

/* A ROW IS NOT A PERSON'S MOVE WHEN ITS PROGRAM'S DRIVER OWNS IT. A drafted PRD whose design waits on other PRDs
   (or on the fleet itself) is stamped `person: true` by the record, which cannot see the drive; counting it as
   "a move only a person can make" while the program is driven contradicted the drive's own `personStep: null`.
   One reading — the program of the row's own id, then `driverHandles` — for the plan's list, the program's
   "needs you" chip and a PRD's ownership sentence. */
function programIdOf(id){
  if (PG[id]) return id;
  const p = Object.values(PG).find(q => (q.sl || []).some(s => s.id === id || (s.prds || []).some(r => r.n === id)));
  return p ? p.id : "";
}
const driverOwns = a => { const pid = programIdOf(a.id); return !!pid && driverHandles(a, pid); };

/* A TO-DO ABOUT A SLICE NAMES ITS SLICE: "SL-206 · <title>" — for a row keyed on the slice and for a row keyed
   on one of its PRDs ("SL-206 · <PRD title>"). A program-level row carries none. */
function withSliceLabels(rows){
  return rows.map(a => {
    const sl = SL[a.id] || (PRD[a.id] && SL[PRD[a.id].slice]);
    return sl ? { ...a, sliceLead: `${sl.id} \u00b7 ${a.title}` } : a;
  });
}

/* REFINING A SLICE BY HAND, WHEN THE DRIVER WILL NOT. The slice page's "Refine this slice" / "Refine it
   again…" box is gone with every other control there, and `board.py` raises a `refine` row only for an empty
   cut with no bar — so a cut already refined, or one in flight, would have had no way to be refined from any
   page. One row per open slice that has no `refine` row yet and a built shaping command: its command is the
   slice's own shaping terminal, so the host draws the same "Refine this slice" control on it. `refine` is a
   driver group (`DRIVER_GROUPS`): hidden while the program is driven, shown when the driver is stuck. */
function refineAgainRows(p, mine){
  /* ONLY WHERE A HOST HOLDS THE DRIVE AND IT IS NOT MOVING: a driven program's refinements are the driver's
     (`driverHandles`), and a board with no host has no shaping to offer. A drive that is waiting on an answer
     or stopped — or a program nobody has started — is exactly "the driver will not". */
  const d = deliveryOf(p.id);
  if (!DELIVERY || (d && d.reading !== "waiting" && d.reading !== "stopped")) return [];
  return (p.sl || []).filter(s => openSlice(s) && s.shape && s.shapeTerminal && s.shapeBuilt
      && !mine.some(a => a.id === s.id && a.group === "refine"))
    .map(s => ({ group: "refine", sev: 3, id: s.id, title: s.name, action: `Refine ${s.id} again`,
      why: "Reopen this slice's promise and sharpen it with the fleet.",
      cmd: s.shapeTerminal, cmdKey: "slice_refine", built: true, fleet: false, person: true, order: 4,
      rank: s.rank, rankSrc: s.rankSrc, rankFrom: s.rankFrom, blocks: [], depthBehind: 0, stage: "shaping" }));
}

function viewProgram(id){
  if (tuOn()) return tuProgramPage(id);
  const p = PG[id];
  /* MOST IMPORTANT FIRST — the operator's own phrase for it, and the honest reading of it once
     told the real dispatch-graph critical path is not reachable from a corpus-only board: the
     new `depthBehind` (the longest chain waiting behind this thing), then `blocks` (how many
     other slices sit on it directly) — see `board.py::graph`'s own comment for why the first
     is a stand-in and not the thing itself. Ties fall back to `actions()`'s own emission order,
     which is already roughly severity-first. */
  const own = new Set([id, ...p.sl.map(s => s.id)]);
  const mine = entityActions(id)
    /* A PRD's row reaches this page only when it is not the fleet's own: `advance` is "nothing for you to do". */
    .filter(a => own.has(a.id) || !a.fleet)
    .slice()
    .sort((a, b) => (b.depthBehind - a.depthBehind) || (b.blocks.length - a.blocks.length));
  /* EVERY MOVE A PERSON OWES ON THIS PROGRAM IS ONE LIST, IN THE ORDER IT IS WORKED (the program
     lifecycle): `order` is the step (`board.py::STAGE_OF_GROUP`), and inside a step the old
     most-important-first reading still breaks the tie. There used to be two lists — "Needs you" and
     "To do here" — split on who could make the move, and a program with no proof named showed it in
     one while its row counted the other. */
  /* EVERY SLICE MOVE LIVES HERE, LABELLED WITH ITS SLICE (owner ruling: to-dos are program-level
     only; the slice page is a read page). A slice-keyed row and a PRD-keyed row both arrive keyed on their
     own id, so each is stamped with `sliceLead` — "SL-206 · <title>" — for the second line. */
  const todos = withSliceLabels(mine.concat(refineAgainRows(p, mine)))
    .filter(a => personOwes(a, id)).sort((a, b) => ((a.order || 5) - (b.order || 5)));
  /* M-2 (ENG-10704): whether THIS program's own waived-slice `finish` row (`chainClear`'s
     "One of N …" / "This waived slice alone …" sentence) landed in `needs` or `rest` — read
     straight off the same partition above (`mine` already scopes to this program AND its own
     slices, which is where a waived cut's `finish` row is keyed), so the sentence's own
     section-name hint can never say a section the row is not actually drawn in. */
  const finishInNeeds = true;
  /* `data-todo` IS WHERE THE DRIVE BOX'S POINTER LEADS (ENG-10704, G-09): "Name a proof" and "Close it" are
     person-only moves, and this section is where they are. */
  /* Computed once for the chain section below. */
  const chain = programChain(p);
  /* THE ONE COMMAND THIS PAGE OFFERS WHEN NOTHING IS WRONG — AND ONLY WHEN IT CAN BE DRIVEN.

     Every other command on an entity page hangs off a FINDING, so the page's whole affordance
     disappears the moment the corpus is healthy. Driving a program is the one command that is
     not a repair: it starts the session that moves the program and checks what moved, and the
     moment a reader most wants it is the moment no finding fires.

     ONE NEXT STEP PER PROGRAM, AND `board.py` DECIDES IT. `program_step` derives the step
     from the program's state — no proof named and no waiver means `prove` and nothing else; a
     proof named or waived and open work means `deliver` (a waiver answers the proof, ENG-10683);
     complete means `ship` — and `drive()` stamps `deliver` on a program
     ONLY when driving is that step and something is in flight. So a program with no proof
     arrives here with `deliver` empty and this section is simply absent: not disabled, not
     drawn beside the `prove` row — absent. That is the contract, not a rendering choice: the
     driver refuses a program with no finish line on its first step, and two Start controls on
     one page (`prove` beside `deliver`) is the defect this replaced. This file does not
     re-derive the step; a second predicate here would be a second thing to keep in step.

     NOT TWICE ON ONE PAGE. When nothing is in flight the `stalled` finding carries this same
     command with the reading that provoked it — strictly more than this box can say — and
     `board.py` stamps `""` for exactly that program, so the FINDING is the one site. The guard
     below keeps that true for a payload built by hand as well: compared on the command itself
     rather than on the finding's name, because what must not happen twice is the command.
     Taking the command off the finding instead would leave a row stating a problem and handing
     over nothing, which is the shape `nocmdbox` reports as a defect in the guidance.

     `deliver` is also `""` on a project whose guidance names no `program_deliver`, and `runbox`
     answers `""` on that — so the section is absent rather than broken, and no command is
     spelled here to fill it. The section's own composition is `driverSection`, where a HOST
     that knows the fleet is already driving the program may replace it whole (ENG-10347). */
  /* THE STALLED FINDING CARRIES THE SAME COMMAND (`board.py` stamps `deliver` empty for exactly
     that program, so the row is the one site). STANDALONE that stays true. WITH A HOST the
     driver is the fleet's, not a session the reader starts, so the host's box renders from the
     row's command and the row points up at it (`runAffordance` on the host: the pointer, only
     on this page) — one driver per page, and it is the box (ENG-10558). */
  const carried = mine.find(a => a.cmdKey === "program_deliver" && a.cmd) || null;
  const driver = p.deliver && !mine.some(a => a.cmd === p.deliver) ? driverSection(p)
    : carried && !p.deliver ? hostDriver(p, carried.cmd, carried.built)
    /* THE ONE CASE `""` CANNOT SAY (ENG-10558): driving IS this program's next step and the
       corpus's vocabulary names no driver. Measured on the Harbour sample: a fleet-driven
       program showed no *Drive this program* at all and nothing said why. One calm sentence,
       no control — the fix is in the repository's `fleet.toml`, not on this page. */
    : !p.deliver && p.deliverMissing ? `<section class="grp"><div class="grp-h"><h3>Delivery</h3></div>
      <p class="empty-note">Driving isn&rsquo;t set up for this repository: its <code>fleet.toml</code> names
      no <code>program_deliver</code> command yet. Whoever looks after the repository adds one, and this
      box appears.</p></section>`
    /* NOTHING TO DRIVE, AND THE HOST MAY STILL HAVE A SENTENCE: an undecomposed or a complete
       program carries no command and no finding with one, and this file has nothing to say —
       but a host that knows why the fleet cannot drive it says so (ENG-10558, R-2). The seam
       answers `""` for the standalone board and for a host with nothing to add. */
    : hostDriver(p, "", false) || deliveryGates(p);
  /* THE HOST'S SLOT IS COMPOSED HERE, BEFORE THE HEADER, so a control it hands the header (`head`: an
     already-shaped program's "Shape it again…") sits beside the chips. Same position in the call order
     relative to the driver and the to-dos as before, so the host's paint marks read as they did. */
  const hostSaid = {};
  const asksHtml = hostAsks("program", p.id, p.id, p, p.name, hostSaid);
  /* THE ONE TO-DO LIST: the record's rows, less any a host row replaces, and the host's rows
     beside them — composed after the host's slot, which is where the host says them. */
  const hostRows = hostSaid.todo || [];
  const replaced = new Set(hostRows.flatMap(r => Array.isArray(r.replaces) ? r.replaces : []));
  const listed = replaced.size ? todos.filter(a => !replaced.has(a.group)) : todos;
  const todoSection = todoList(p, listed, hostRows);
  /* THE HEADER IS THE TITLE, ITS STATE, AND ONE QUIET LINE — no crumb row (the nav already names
     Programs and the sidebar holds the way back), no kind chip, no "N to do" chip (the to-do section
     is the count), and no fact grid: slices done and the proof are the line, said only when they
     matter. What the grid also carried (live PRDs, blocks, waiting on a prerequisite, chain to the
     proof, success criteria) is on the cuts below, the chain section and the Dependencies page. */
  const bits = [(slicesDone(p, "") === "—" ? "" : slicesDone(p, " slices done")) + (withdrawnNote(p) ? " &middot; " + withdrawnNote(p) : ""),
    p.closed ? `closed ${esc(String(p.closed))}` : "",
    p.complete && waivedCuts(p).length ? `${p.closed ? "closed" : "closes"} with ${esc(waivedList(p))} waived` : "",
    /* THE PROOF ONLY WHEN IT MATTERS: a shipped proof is the norm and says nothing. */
    p.state === "withdrawn" ? "" : p.proof.length ? (p.proofok ? "" : `proof ${p.proof.map(n => proofBadge(n)).join(" ")} not shipped`)
      : p.waived ? "proof waived by a written decision" : p.owed ? "" : "no proof named",
    /* THE REASON A PROGRAM IS STILL OPEN, WHEN IT IS A DEFERRED WAIVER. */
    ...waitingOn(p).map(esc),
    dispositionFact(p.disposition) || "",
    p.cutCommand ? `a program holds at least two slices &mdash; <code>${esc(p.cutCommand)}</code> cuts another` : ""].filter(Boolean);
  const head = entityHeader({
    crumbs: [],
    id: p.id, name: p.name,
    promise: p.desc, promiseNote: descNote(p.desc),
    chips: [stateChip(p), programRankChip(p, "head", true), closedToNewWorkChip(p), hostSaid.head || ""],
    line: bits.join(" &middot; "),
    facts: [],
  });
  const slices = p.sl.map(s => ({
    id: s.id, title: s.name, go: "slice:" + s.id,
    rank: s.rank, rankSrc: s.rankSrc, rankFrom: s.rankFrom, chip: sliceRankChip(s),
    progress: sliceRail(s),
    sub: s.done_when, subLabel: "Done when",
    /* A parked cut is neutral, like a finished one: it is the one row on this list nobody is
       being asked to move. Its decision chip sits SECOND, inside the three the row shows, so
       the register's own words are on the line and not folded into a "+N". */
    sev: PARKED.includes(s.state) || s.state === "complete" ? 3 : s.blockedBy.length ? 2 : 1,
    badges: [sliceStateChip(s),
             ...(dispositionChip(s.disposition) ? [dispositionChip(s.disposition)] : []),
             `<span class="chip kind">${esc(s.kind)}</span>`,
             /* ONLY AN OPEN CUT WAITS (ENG-10704): a withdrawn or proven cut wore a red "waits on". */
             ...(openSlice(s) ? s.blockedBy : []).map(d => badge("waits on " + d, "attn", d)),
             ...(s.blocks.length ? [badge("blocks " + s.blocks.length, "", s.blocks[0])] : []),
             ...s.proof.map(n => isDrill(n) ? proofBadge(n) : badge("proof " + n, "", n))],
  }));
  /* THE HOST'S SLOT FIRST, THE DRIVE BOX DIRECTLY UNDER IT, THEN THE FINDINGS. The slot is under
     the header on every entity page — the same seam, the same position, the shaping box and the
     cards a run wrote (ENG-10561, ENG-10563) — and the drive box follows it so the card a driven
     program is waiting on and the box that says "waiting on your answer" are one scroll position
     (ENG-10558's rule, kept by adjacency rather than by putting the cards after the findings).
     A finding is a repair and comes after both: the reader's own moves, then the record's. */
  /* WHERE IT IS, THEN THE HOST'S SLOT, THEN DELIVERY, THEN THE TO-DOS. The tracks read as part of
     the header (a `div`, not a section: the host's slot stays the first section under it on
     every entity page). The question cards and the Delivery box stay adjacent — a driven program's box
     saying "waiting on your answer" and the card it waits on are one scroll position (ENG-10558) — and
     the ordered to-do list follows them. */
  /* QUESTION FIRST (ENG-11733): the host's card slot leads the page's own sections, and every section
     this page owns below *Where it is* — the driver, the to-dos, the chain and the slices — folds under
     it. An absent slot arrives as `""` and `asksFirst` leaves the page exactly as it was. */
  /* WHERE IT IS, DIRECTLY UNDER THE HEADER — ALWAYS (the operator, on PG-36: *"'Where it is' must always be
     at the top, right below the header"*). It is part of the header's reading, so it rides with the header
     into `asksFirst`: above the host's slot, above a question card, and never folded into *Context*. */
  const where = whereItIs(p, listed.concat(hostRows.filter(r => r.title && r.who !== "fleet")), driver);
  return asksFirst(asksHtml,
    driver +
    todoSection +
    /* BEFORE the flat list on purpose. The list is the detail — every cut this program owns, in
       authored order. This is the orientation: what stands between the program and its proof,
       in the order it can be done, including the parts that are not this program's to do. A
       program with no cuts gets no chain and the list's own empty sentence speaks instead. */
    (p.sl.length ? chainSection(p, chain, finishInNeeds) : "") +
    `<section class="grp"><div class="grp-h"><h3>Slices</h3><span class="n">${p.sl.length}</span>
       </div>
      ${entityList(slices, { empty: "No slices. Nothing can be planned or started in this program until one is cut." })}
    </section>`, head + where);
}

/* THE WORK A SLICE PAGE CANNOT HOLD, SAID WHERE IT IS MISSING (ENG-10771).

   Tasks and bugs skip the plan ladder on purpose — per this repository's own model they are born
   directly in the tracker and have no git file, ever — so a slice's page, which renders off the
   git-tracked PRDs, has nothing to show them from. Production's slice pages drew "To do here" and
   "PRDs in this slice" and said nothing about it, so a reader looking for a cut's tasks or bugs
   found nothing and no way to learn that nothing is exactly what to expect.

   ONE SENTENCE, IN THE HEADING BLOCK rather than only in the empty state: a slice with PRDs drawn
   is precisely the page where a reader might assume the list is exhaustive, and an empty-state-only
   note would leave that reader nothing. `grp-b` is the same blurb class the other sections use.

   NO LINK, AND THAT IS MEASURED RATHER THAN LAZY. The issue asked for "a link to the tracker's
   issues labeled with this slice, if the data is available" — and it is not: tracker-born work
   carries no `slice:` label (`tracker_labels.PROGRAM_PARENT`'s comment records that the program
   group "never reached tracker-born work (bug/task/cleanup … which has no git file to carry a
   `slice:`)", measured at 0 of 57 open issues on the live board), and `board.js` holds no
   tracker URL at all. A search link could only be guessed, so the sentence names where the work
   lives instead. */
function sliceTaskNote(){
  return `<p class="grp-b">Tasks and bugs skip the plan ladder on purpose: they are born in the
    tracker with no plan file, so a slice's page never lists them &mdash; the tracker is where they
    live.</p>`;
}

/* A PRD'S PROGRESS, the slice row's own bar (`.sl-prog` over the stepper's `.stp-bar` segments): drafted,
   planned, implementing, shipped — read off the status alone. A stub has none lit; a closed-unshipped PRD
   (cancelled, superseded) draws the greyed bar and no count, as a parked cut does. */
const PRD_STEPS = { stub: 0, "prd-drafted": 1, planned: 2, implementing: 3, shipped: 4 };
function prdProgress(status){
  const n = PRD_STEPS[status];
  const parked = n === undefined;
  const k = parked ? 0 : n;
  const seg = i => i < k ? (i === 2 && k === 3 ? "run" : "done") : "";
  const doneN = [0, 1, 2, 3].filter(i => seg(i) === "done").length;
  return `<span class="sl-prog${parked ? " parked" : ""}"${parked ? ' aria-hidden="true"' : ` role="img" aria-label="${doneN} of 4 steps done"`}><span class="stp-bar">${
    [0, 1, 2, 3].map(i => `<i${parked ? ' class="gone"' : seg(i) ? ` class="${seg(i)}"` : ""}></i>`).join("")}</span>${parked ? "" : `<b>${doneN}/4</b>`}</span>`;
}

function viewSlice(id){
  if (tuOn()) return tuSlicePage(id);
  const s = SL[id], p = PG[s.program];
  /* A SLICE'S PAGE IS A READ PAGE (owner ruling: "TODOs should only be on program level"):
     title, state, promise, one quiet line and the PRDs. Every move a person owes on this cut — refine it,
     start its PRDs, design or plan one, name its proof — is a row of the PROGRAM page's "Your to-dos",
     labelled with this slice (`viewProgram`'s `sliceLead`), so no action is drawn here and none is lost. */
  /* THE HEADER IS THE TITLE, ITS STATE, AND ONE QUIET LINE (the program page's own shape): no crumb row, no
     kind or build-step chip, no fact grid. The line says PRDs shipped, the proof only when it is a
     problem, what the cut waits on and a disposition. `blocks` and the success criteria are on the
     Dependencies page and the cut's detail file. */
  const bits = [s.n ? `${s.nship} of ${s.n} PRDs shipped` : "no PRDs yet",
    s.proof.length ? (s.proven ? "" : `proof ${s.proof.map(n => proofBadge(n, "")).join(" ")} not shipped`)
      : s.state === "waived" ? "proof waived &mdash; this slice names no proof of its own" + housedProofs(s)
      : s.owed ? `proof owed &mdash; ${esc(s.owed)}`
      : "no proof named",
    openSlice(s) && s.blockedBy.length ? `waits on ${s.blockedBy.map(d => badge(d, "attn", d)).join(" ")}` : "",
    sliceDispositionFact(s) || ""].filter(Boolean);
  const head = entityHeader({
    crumbs: [],
    id: s.id, name: s.name, promise: s.done_when,
    chips: [sliceStateChip(s), sliceRankChip(s)],
    line: bits.join(" &middot; "),
    facts: [],
  });
  /* B-1 (ENG-10704) + L-1 (ENG-10767): THIS LIST READ `r.fleet` DIRECTLY — the raw "the fleet owns it"
     flag `board.py` stamped when it built the plan — instead of the parked reading every other surface
     on this page already goes through. Production's SL-185 drew 0608 here as `with the fleet` /
     "Waiting for the fleet to implement" directly under its own "To do here" row, which reads the SAME
     PRD through `asMet`/`parkedOn` as "Waiting on a human action — ENG-10308: …": two opposite readings
     of one PRD on one page. After B-1 the list went through `parkedOn`, but still used a different
     lead-in ("Waiting on a person — <action>") that dropped the issue key the "To do here" row carries
     — one parked PRD, two lead-ins. `parkedLeadIn` is the one sentence both surfaces share. */
  const prds = s.prds.map(r => {
    const on = r.fleet ? parkedOn(r.n) : null;
    /* THE ROW'S LIVE READING (ENG-10795): where the PRD's issue stands right now, off the same host
       overlay the PRD page reads — running on a box, queued, or blocked behind a gate. A parked row wins
       (a person's move outranks the fleet's), terminal rows keep their own words, and a person's row
       (`r.cmd`) was never the fleet's to describe. Without a host, or before the host's backlog read
       has landed, `liveRowOf` answers nothing and the row says what it always said. */
    const at = on || !r.fleet || TERMINAL.includes(r.status) ? null : liveRowOf(r.n);
    const blocked = !!(at && at.pickable === false);
    const yours = !r.fleet && r.cmd && !on;
    return {
      id: r.n, title: r.title, go: "prd:" + r.n, rank: r.rank, rankSrc: r.rankSrc,
      rankFrom: r.rankFrom, sev: TERMINAL.includes(r.status) ? 3 : 1,
      /* A PRD IS EXACTLY AS URGENT AS ITS SLICE: the same priority chip on every row is the header's chip again. */
      chip: r.rank === s.rank ? "" : prdRankChip(r, s),
      progress: prdProgress(r.status),
      sub: on ? parkedLeadIn(on)
           : at ? (at.status || `${at.key} \u00b7 ${at.state}${at.sentence ? " \u2014 " + at.sentence : ""}`) : "",
      badges: [`<span class="chip ${TERMINAL.includes(r.status) ? (r.status === "shipped" ? "complete" : "") : "flight"}">${esc(r.status)}</span>`,
               ...(on ? [`<span class="chip unproven">your move</span>`]
                   : blocked ? [`<span class="chip attn">blocked &mdash; not pickable</span>`]
                   : r.fleet ? [`<span class="chip flight">with ${esc(FLEET.actor)}</span>`]
                   : yours ? [`<span class="chip unproven">your move</span>`] : [])],
      /* READ-ONLY (owner): a PRD row on the slice page carries a STATE and no command. A parked
         row's status opens the park, a row the host places carries its position (opening the issue), the
         fleet's row states its wait; a person's own move has no control here — it is a to-do on the PROGRAM
         page, labelled with this slice. */
      right: on ? waitbox(parkedStatus(on), parkedGo(on))
           : at ? waitbox(blocked ? (at.sentence || `${at.key} is queued — nothing picks it up while that holds.`)
                                  : `${at.key} · ${at.state}`,
                          at.go || "issue:" + at.key, blocked ? "warn" : at.status ? "work" : "grey")
           : r.fleet ? waitbox(FLEET.wait) : "",
    };
  });
  /* L-6 (ENG-10704): an empty cut under a program `board.py` still reads `decompose` (its one
     next step, ENG-10704 item 8) offered nothing but "No PRDs yet. This slice is a promise
     nobody has started." — true, and silent about the one fact that matters: nothing here can
     start until the program is decomposed, while SL-184 next door (a decomposed program's own
     empty cut) offers `prd:create`. Read off `D.actions` — the SAME "undecomposed" row `board.py`
     gates on `program_step(p) == "decompose"` (item 8) — rather than re-deriving `requires == []`
     here, so this page and the To-do row it is beside can never disagree about which is true. */
  const progUndecomposed = !!(p && D.actions.some(a => a.id === p.id && a.group === "undecomposed"));
  /* QUESTION FIRST (ENG-11733): the card slot leads, and the cut's own sections fold under it. */
  return asksFirst(hostAsks("slice", s.id, s.program, s, p ? p.name : ""),
    `<section class="grp"><div class="grp-h"><h3>PRDs in this slice</h3>
       <span class="n">${s.prds.length}</span></div>
      ${entityList(prds, { empty: progUndecomposed
        ? `No PRDs yet — decomposition comes first. ${p.id} names no decomposition roots yet, `
          + `so nothing writes a PRD into this cut until that run names them.`
        : "No PRDs yet. This slice is a promise nobody has started." })}
      ${sliceTaskNote()}
    </section>`, head);
}

/* ── THE NEW PROGRAM, SLICE AND PROGRAMS PAGES, BEHIND THE OLD/NEW SWITCH ─────────────────────────────
 *
 * The owner's prototype (the "program page v2" mockup) recast the three pages in the item page's own
 * frame: header with the progress roll-up, then "Waiting on a person", then "Delivery", then tabs. They
 * are ADDED BESIDE the existing renderers, not in place of them: `viewProgram` and `viewSlice`
 * each begin with one line that asks `tuOn()` and, when the switch is on, hands over to
 * `tuProgramPage` or `tuSlicePage`. With the switch off (the default) the old
 * renderers run byte for byte as they did.
 *
 * THE SWITCH IS THE SHARED MODULE'S (`static/team-ui.js`, `tuNewUi()`), reached through `typeof` so this
 * file works whether or not that module is loaded: absent, the answer is "old UI".
 *
 * EVERY NUMBER HERE IS READ, NEVER INVENTED. A PRD's state is its status and the open PRDs it waits on
 * (`waveG()`, the same graph the Dependencies page draws); its wave is the payload's own `wave` (`board.py`'s
 * `prd_waves`); "frees" is how many open PRDs wait on it. The host (`app.js`) supplies the delivery box, the
 * delivery log and the activity rows through `tuDeliveryBox`, `tuProgramFacts`; where it supplies nothing the
 * page says so plainly rather than drawing a figure.
 */
function tuOn(){
  try { return typeof tuNewUi === "function" && !!tuNewUi(); } catch (err){ return false; }
}

/* WHAT THE HOST HANDS THE NEW PAGES: `deliveryBox(row, facts)` — the Delivery slot's markup from the drive
   document, `""` where the old seam would draw nothing — and `programFacts(id)` — the last cycle, the cycles
   the service serves, the activity rows. Absent, the page draws the old box and says nothing it cannot read. */
let TU_HOST = null;
function tuHost(h){ TU_HOST = h && typeof h === "object" ? h : null; }

/* THE FOUR READINGS OF A PRD'S PLACE IN ITS PROGRAM, in the order the roll-up bar draws them. */
const TU_STATE = {
  shipped: { cls: "d", name: "Shipped", leg: "shipped" },
  ready: { cls: "r", name: "Ready to build", leg: "ready to build" },
  waits: { cls: "w", name: "Waits on earlier PRDs", leg: "wait on earlier PRDs" },
  proof: { cls: "p", name: "The proof · waits on all", leg: "the proof, which waits on all" },
};
const TU_ORDER = ["shipped", "ready", "waits", "proof"];
/* Which tab each page is on, the Plan tab's grouping, and the Programs list's responsible filter. */
const TU_TABS = {};

/* ONE ROW PER LIVE PRD OF THE PROGRAM, with the facts the pages draw. A cancelled PRD is not work and is
   not counted; a shipped one is done. An open PRD is `waits` when an open PRD in play stands before it
   (the build-step graph's `up`), `proof` when it is the program's composed proof and still waits, else
   `ready`. */
function tuPrds(p){
  const g = waveG();
  const proofs = new Set((p.proof || []).map(String));
  const out = [];
  (p.sl || []).forEach(s => (s.prds || []).forEach(r => {
    if (r.status === "cancelled") return;
    const n = String(r.n);
    const shipped = r.status === "shipped";
    const prd = k => !!g.nodes[k] && g.nodes[k].kind === "prd";
    const blockers = shipped ? [] : [...(g.up[n] || [])].filter(prd);
    const frees = shipped ? 0 : [...(g.down[n] || [])].filter(prd).length;
    const isProof = proofs.has(n);
    out.push({ n: n, title: String(r.title || ""), slice: s.id, status: String(r.status || ""),
      state: shipped ? "shipped" : blockers.length ? (isProof ? "proof" : "waits") : "ready",
      blockers: blockers, frees: frees, wave: typeof r.wave === "number" ? r.wave : 0, isProof: isProof });
  }));
  return out;
}
/* A SLICE'S COLOUR IS ITS PLACE IN THE PROGRAM: six hues, reused beyond six. */
/* THE TYPE BADGE IS THE SHARED MODULE'S (`team-ui.js`); a plain chip stands in where it is not loaded. */
function tuBadge(kind){
  return typeof tuTypeBadge === "function" ? tuTypeBadge(kind, false) : `<span class="chip">${kind === "slice" ? "Slice" : "Program"}</span>`;
}
function tuHue(p){
  const at = {};
  (p.sl || []).forEach((s, i) => { at[s.id] = i % 6; });
  return at;
}
function tuCount(rows, k){ return rows.filter(r => r.state === k).length; }

function tuBar(rows, small){
  const segs = TU_ORDER.filter(k => tuCount(rows, k));
  const said = segs.map(k => `${tuCount(rows, k)} ${TU_STATE[k].leg}`).join(", ");
  return `<div class="tu-ru-bar${small ? " sm" : ""}"${segs.length ? ` role="img" aria-label="${esc(said)}"` : ' aria-hidden="true"'}>${segs.map(k =>
    `<i class="${TU_STATE[k].cls}" style="flex:${tuCount(rows, k)}" title="${esc(TU_STATE[k].name)}: ${tuCount(rows, k)}"></i>`).join("")}</div>`;
}
/* ONE ROW PER SLICE UNDER THE PROGRAM'S BAR: its own bar, "x of y", and the way into its page. */
/* THE AMBER NOTE A SLICE WEARS WHEN A PRD IT HOLDS WAITS ON A PERSON: "· 0709 waits on a person". */
let TU_HOLDS = [];  // the holds of the page being drawn, for the rows that wear a note
function tuHoldNote(mine){
  const here = tuHoldsIn(TU_HOLDS, mine);
  if (!here.length) return "";
  const nums = here.map(h => String(h.prd));
  return ` <span class="tu-hold-note">&middot; ${esc(nums.join(", "))} ${nums.length === 1 ? "waits" : "wait"} on a person</span>`;
}
function tuSliceRoll(p, rows){
  if (!(p.sl || []).length) return "";
  const hue = tuHue(p);
  return `<div class="tu-ru-sl">${p.sl.map(s => {
    const mine = rows.filter(r => r.slice === s.id);
    const done = tuCount(mine, "shipped");
    return link("slice:" + s.id, "tu-ru-row",
      `<span class="tu-id"><i class="tu-dot tu-s${hue[s.id]}"></i>${esc(s.id)}</span><span class="tu-t">${esc(s.name)}${tuHoldNote(mine)}</span>${tuBar(mine, true)}<span class="tu-mono tu-sm">${mine.length ? `${done} of ${mine.length}` : "no PRDs"}</span><span class="tu-chev">&rsaquo;</span>`);
  }).join("")}</div>`;
}
function tuLegend(p){
  const hue = tuHue(p);
  return `<div class="tu-sl-leg">${(p.sl || []).map(s => `<span><i class="tu-dot tu-s${hue[s.id]}"></i>${esc(s.id)} ${esc(s.name)}</span>`).join("")}</div>`;
}

/* THE ORDER OF WORK: what shipped first, then Now (nothing in the way), then Then 1, 2 … by the payload's own wave. */
function tuWaveChip(r, hue){
  return link("prd:" + r.n, `tu-wc tu-s${hue[r.slice]}${r.frees >= 10 ? " big" : ""}`,
    `<b>${esc(r.n)}</b><span>${esc(r.title)}</span>${r.frees >= 6 ? `<em>frees ${r.frees}</em>` : ""}`,
    ` title="${esc(r.title + " · frees " + r.frees)}"`);
}
function tuWaves(p, rows, compact){
  const hue = tuHue(p);
  const done = rows.filter(r => r.state === "shipped");
  const open = rows.filter(r => r.state !== "shipped");
  const row = (cls, label, list) => `<div class="tu-wv${cls ? " " + cls : ""}"><div class="tu-wv-l"><b>${label}</b><small>${list.length}</small></div><div class="tu-wv-c">${
    list.map(r => tuWaveChip(r, hue)).join("")}</div></div>`;
  const levels = [...new Set(open.map(r => r.wave))].sort((a, b) => a - b);
  let h = done.length ? row("done", STEP_DONE, done) : "";
  levels.forEach(w => {
    h += row(w === 0 ? "now" : "", w === 0 ? "Now" : "Then " + w,
      open.filter(r => r.wave === w).sort((a, b) => b.frees - a.frees));
  });
  return `<div class="tu-wvs${compact ? " cmp" : ""}">${h}</div>`;
}

/* THE PLAN TABLE: one row per PRD — its state as a pill, what it waits on, what it frees. */
function tuPill(r){
  const k = r.state;
  return `<span class="tu-stp ${TU_STATE[k].cls}">${k === "shipped" ? "Shipped" : k === "ready" ? "Ready" : k === "proof" ? "Proof · last" : "Waits on " + r.blockers.length}</span>`;
}
/* THE LINE UNDER A PRD'S TITLE: its register status where that says something the State pill does not (a shipped row's would
   repeat the pill), and that it is the program's composed proof. */
function tuPrdSub(r){
  const bits = [r.state === "shipped" ? "" : r.status, r.isProof ? "the program's composed proof" : ""].filter(Boolean);
  return bits.length ? `<div class="tu-s">${esc(bits.join(" \u00b7 "))}</div>` : "";
}
function tuPrdTable(p, list, rows, showSlice){
  const hue = tuHue(p);
  const by = {};
  rows.forEach(r => { by[r.n] = r; });
  if (!list.length) return `<p class="tu-sm tu-muted tu-pad">No PRDs here yet.</p>`;
  /* A ROW THAT WAITS ON EVERY OTHER OPEN PRD OF THE PROGRAM (the proof does) says so in a word, not in one chip each;
     any other row shows at most six and counts the rest. `rows` can be one slice's, so the program's own are read. */
  const others = tuPrds(p).filter(x => x.state !== "shipped").length - 1;
  const waitsOn = r => {
    if (r.blockers.length > 6 && (r.state === "proof" || r.blockers.length >= others)) return `<span class="tu-faint" title="${esc(r.blockers.join(", "))}">all ${r.blockers.length} other PRDs</span>`;
    const chip = k => `<span class="tu-kc${by[k] && by[k].state === "ready" ? " r" : ""}">${esc(k)}</span>`;
    return r.blockers.slice(0, 6).map(chip).join("") + (r.blockers.length > 6 ? `<span class="tu-kc tu-more-n" title="${esc(r.blockers.slice(6).join(", "))}">+${r.blockers.length - 6}</span>` : "");
  };
  return `<div class="tu-tbl"><div class="tu-th tu-colsQ"><span>PRD</span><span>Title</span><span>State</span><span>Waits on</span><span class="r">Frees</span><span></span></div>${
    list.map(r => link("prd:" + r.n, "tu-tr tu-colsQ",
      `<span class="tu-id">${showSlice ? `<i class="tu-dot tu-s${hue[r.slice]}"></i>` : ""}${esc(r.n)}</span>
      <span><div class="tu-t">${esc(r.title)}</div>${tuPrdSub(r)}</span>
      <span>${tuPill(r)}</span>
      <span class="tu-sm tu-wo">${r.state === "shipped" ? `<span class="tu-faint">&mdash;</span>`
        : r.blockers.length ? waitsOn(r)
        : `<span class="tu-faint">nothing in its way</span>`}</span>
      <span class="tu-age">${r.frees ? (r.frees >= 10 ? `<b class="tu-attn">${r.frees}</b>` : r.frees) : "—"}</span><span class="tu-chev">&rsaquo;</span>`)).join("")}</div>`;
}
/* A SLICE'S KIND IN PLAIN WORDS: the register's own word for the cut, "gap-set", is the one that needs saying. */
function sliceKindWords(kind){
  const k = String(kind || "");
  return k === "gap-set" ? "closes gaps" : k.replace(/-/g, " ");
}
/* A PROOF LIST AS LINKS: each PRD to its page, a drill as words. */
function tuProofLinks(list){
  return (list || []).map(n => isDrill(n) ? `<span title="${esc(drillStem(n))}">drill ${esc(drillShort(n))}</span>` : link("prd:" + n, "tu-lnk", "PRD " + esc(n))).join(", ");
}
/* ONE SLICE'S CARD: what it promises, what proves it, its bar — and the chips the old Slices list carried. */
function tuSliceCard(p, s, rows, solo){
  const mine = rows.filter(r => r.slice === s.id).sort((a, b) => (a.wave - b.wave) || (b.frees - a.frees));
  const hue = tuHue(p);
  const done = tuCount(mine, "shipped");
  const head = solo ? "" : `<div class="tu-slc"><div class="tu-slc-h"><i class="tu-dot tu-s${hue[s.id]}"></i>${link("slice:" + s.id, "tu-mono", esc(s.id))}<b>${esc(s.name)}</b>
      <span class="chip kind">${esc(sliceKindWords(s.kind))}</span>${dispositionChip(s.disposition) || ""}${(openSlice(s) ? s.blockedBy : []).map(d => badge("waits on " + d, "attn", d)).join("")}${
        s.blocks && s.blocks.length ? badge("blocks " + s.blocks.length, "", s.blocks[0]) : ""}${tuHoldNote(mine)}
      <span class="tu-grow"></span><span class="tu-sm tu-muted">${done} of ${mine.length} shipped</span></div>
    <div class="tu-slc-b"><div><span class="tu-lbl2">Done when</span>${esc(String(s.done_when || "").replace(/`/g, ""))}</div>
      <div><span class="tu-lbl2">Proved by</span>${(s.proof || []).length ? tuProofLinks(s.proof) : '<span class="tu-faint">no proof named</span>'}</div></div>${tuBar(mine, false)}</div>`;
  return `<section class="tu-slb">${head}${tuPrdTable(p, mine, rows, false)}</section>`;
}
/* ── THE DETAIL PAGES' SHARED PARTS ────────────────────────────────────────────────────────────────────────
   One definition of each part every item page is made of: the tab bar, the facts row, key/value rows, the jump rail and the document
   frame, the meta line under a title, and the id linker (an id in prose is a link only where it has a page). The program, slice and PRD
   pages draw them here; the Fleet service's idea, filing and issue pages reach the same functions through `Board` (`team-ui.js` only
   forwards). Their CSS is in `fleet.css`. A second writer of any of this markup fails the emitter ratchet
   (`test_each_shared_part_has_one_emitter`). ──────────────────────────────────────────────────────────────── */
/* THE TAB BAR. `tabs` = [{ id, label, n?, ask?, html?, attrs? }]; `attr` is the attribute a click handler reads ("data-tu-tab" on an
 issue's or a program's page, "data-tu-ftab" on a filing's). `html` says the label is markup; `attrs` is extra, already-escaped attributes
 (a program page's `data-tu-page`). One row that scrolls sideways on a phone and never wraps (`.tu-tabs` in this file's CSS). */
function tuTabBar(tabs, active, attr){
return `<nav class="tu-tabs">${(Array.isArray(tabs) ? tabs : []).map(t =>
  `<button type="button" ${attr}="${esc(t.id)}"${t.attrs ? " " + t.attrs : ""}${t.ask ? ' class="tu-tab-ask"' : ""} aria-pressed="${active === t.id}">${t.html ? t.label : esc(t.label)}` +
  `${t.n != null && t.n !== "" ? ` <span class="tu-n">${esc(t.n)}</span>` : ""}</button>`).join("")}</nav>`;
}

/* THE FACTS ROW: label-and-value chips in one wrapping line. `facts` = [{ k, v (html), cls?, tone? }]; a fact with no value is
   not drawn, and none at all draws nothing. */
function tuFactsRow(facts){
  const out = (Array.isArray(facts) ? facts : []).filter((f) => f && f.v != null && String(f.v) !== "").map((f) =>
    `<span class="tu-f${f.tone ? " tu-f-" + esc(f.tone) : ""}"><span class="tu-fk">${esc(f.k)}</span><span class="tu-fv${f.cls ? " " + esc(f.cls) : ""}">${f.v}</span></span>`);
  return out.length ? `<div class="tu-facts">${out.join("")}</div>` : "";
}

/* KEY / VALUE ROWS (a PRD's relations, a proposal's placement): `rows` = [{ k, v (html) }]; empty rows are not drawn. */
function tuRelRows(rows){
  const out = (Array.isArray(rows) ? rows : []).filter((r) => r && r.v != null && String(r.v) !== "").map((r) =>
    `<div class="tu-rr"><span class="tu-rk">${esc(r.k)}</span><span>${r.v}</span></div>`);
  return out.length ? `<div class="tu-rels">${out.join("")}</div>` : "";
}

/* THE JUMP RAIL beside a long document: `heads` = [{ id, text }]. A click scrolls to the heading with that id (the board's
   one `[data-anchor]` handler). Hidden on a phone, where the headings stay. "" when there is nothing to jump to. */
function tuJumpRail(heads, label){
  const list = (Array.isArray(heads) ? heads : []).filter((x) => x && x.id);
  const name = label || "On this page";
  /* On a phone the side list is one compact "Jump to..." select above the text (`.tu-rail` CSS): same headings, one control. */
  return list.length ? `<nav class="tu-rail" aria-label="${esc(name)}"><div class="tu-eb">${esc(name)}</div>${list.map((x) =>
    `<button type="button" class="tu-rl" data-anchor="${esc(x.id)}">${x.text}</button>`).join("")}` +
    `<select class="tu-jump" data-tu-jump aria-label="Jump to"><option value="">Jump to&hellip;</option>${list.map((x) =>
      `<option value="${esc(x.id)}">${String(x.text).replace(/<[^>]+>/g, "")}</option>`).join("")}</select></nav>` : "";
}
if (typeof document !== "undefined" && document && typeof document.addEventListener === "function"){
document.addEventListener("change", e => {
  const sel = e.target && e.target.closest ? e.target.closest("[data-tu-jump]") : null;
  if (!sel || !sel.value) return;
  const to = document.getElementById(sel.value);
  if (to && typeof to.scrollIntoView === "function") to.scrollIntoView({ behavior: "smooth", block: "start" });
  sel.value = "";
});
}

/* A LONG DOCUMENT'S FRAME: its source line ("Filed by ... / PRD 0942 as it reads on main"), the document column (one 46rem measure for
   everything in it) and, beside it, the jump rail. One emitter for the request tab and the PRD tab. `rail` is `tuJumpRail`'s html or "". */
function tuDocFrame(rail, source, main){
  return `<div class="tu-docwrap${rail ? " tu-docrail" : ""}">${rail || ""}<div class="tu-docmain">` +
    `${source ? `<p class="tu-src">${source}</p>` : ""}${main || ""}</div></div>`;
}

/* THE META LINE under a title: its parts (html), a dot between. Parts with no words are dropped. Each part is its own `.tu-mp`
   and carries the dot that PRECEDES it, drawn in the gap before the part (never after the one before), so when the line wraps
   the dot is the first thing on the new row and the line's own clip cuts it off: no row ends in a "·" and none starts with one. */
function tuMetaLine(parts){
  /* A part with no words of its own is dropped, except a mount point (the assignee row paints into it later). */
  const bits = (Array.isArray(parts) ? parts : []).filter((m) => /data-mount|data-tu-assignees/.test(String(m == null ? "" : m)) || String(m == null ? "" : m).replace(/<[^>]*>|&[#\w]+;/g, "").replace(/[\s·,]+/g, "") !== "");
  return bits.length ? `<div class="tu-meta">${bits.map((m, i) => `<span class="tu-mp">${i ? '<span class="tu-dot-s">·</span>' : ""}${m}</span>`).join("")}</div>` : "";
}

/* THE ID LINKER. A token's destination by its shape: program, slice (and a slice criterion), tracker issue, idea key, PRD
   number, capability and requirement rows (`knowledge:<kind>:<id>`). `opts.repo` addresses another repository's page; `opts.gh`
   is that repository's GitHub address, which a pull request number (`#2598`) and a file reference (`api/x.py:143`) link under. */
/* A pull request number is only a link where the text says it is one ("PR #2598", "pull request #2598", "open #2587", "stacked on
   #2587"): a bare "#112233" is a colour. A file reference needs a path with a slash and a known source extension. */
const PR_CTX = "(?:(?:PRs?|pull requests?|open|stacked on|and|see|[Ff]ixed (?:in|by)|[Mm]erged (?:in|by))\\s+|(?:PRs?|pull requests?)\\s+(?:#\\d{3,6}(?:,\\s*|\\s+and\\s+|\\s*&amp;\\s*|\\s*&\\s*))+)";
const ID_RE = new RegExp("(?<![\\w\\/.&-])(?:PRD[ -](\\d{4})|(SL\\d+-C\\d+|[A-Z][A-Z0-9]{1,9}-\\d{1,7})(?![\\w-])|(?<=" + PR_CTX + ")#(\\d{3,6})(?![\\w])|((?:[\\w.-]+\\/)+[\\w.-]+\\.(?:py|js|ts|tsx|go|md|ya?ml|json|css|html|sql|sh|toml)):(\\d+)(?:-\\d+)?|([\\w.-]+\\/[\\w.-]+)#(\\d{1,6})(?![\\w]))", "g");
const ID_NOT = /^(?:SHA|UTF|ISO|RFC|AES|RSA|TLS|CVE|PCI|SOC|IEEE|ECMA|HTTP|TCP|UDP|MD|EC|HMAC|ED|SSH|PKCS|FIPS|NIST|WCAG|ARIA|OWASP|CWE|IPV|SQL|XML|JSON|API|AC|OD)$/;
/* WHERE AN ID GOES: [route, linked]. A program, slice, tracker issue or idea key always has a page. A capability or requirement row has one only
   where the register that holds it is the one this page reads (`Board.routeOf` answers), or, for a capability id (a global name), in another
   repository's own page; anything else is a NAMED chip, never a link to nothing. */
function idGo(t, repo){
  let m;
  if (/^PG-\d+$/.test(t)) return ["program:" + t, true];
  if (/^SL-\d+$/.test(t)) return ["slice:" + t, true];
  if ((m = t.match(/^SL(\d+)-C\d+$/))) return ["slice:SL-" + m[1], true];
  if (/^(?:ENG|FLT)-\d+$/.test(t)) return ["issue:" + t, true];
  if (/^INTAKE-\d+$/.test(t)) return ["idea:" + t, true];
  if ((m = t.match(/^([A-Z][A-Z0-9]{1,9})-\d{3,7}$/)) && !ID_NOT.test(m[1])){
    const here = !repo || repo === REPO;
    const held = here ? routeOf(t) : "";
    if (held) return [held, true];
    if (!here && m[1] === "CAP") return ["knowledge:capability:" + t, true];
    return ["", false];
  }
  return null;
}
/* A LINK TO A KNOWN ROUTE, in the id style: the one place the `tu-ref` anchor is written. `label` is html. */
function tuRefLink(go, label, repo){
  return link(go, "tu-ref", label, "", repo || undefined);
}
function tuIdMark(t, opts){
  const o = opts || {};
  const got = idGo(String(t), o.repo);
  if (!got) return "";
  return got[0] ? tuRefLink(got[0], o.label != null ? o.label : esc(t), o.repo)
    : `<span class="tu-ref tu-ref-named" title="Named, not routed: this page holds no register for it">${esc(t)}</span>`;
}
/* The HTML of a rendered paragraph with every id in its text a link. Text inside an existing link, button, code span or code block is left
   alone; a token this does not recognise stays text. Idempotent: a linked id is inside an anchor the second pass skips. */
function tuLinkIds(html, opts){
  const o = opts || {};
  const gh = String(o.gh || "").replace(/\/+$/, "");
  const slug = gh.replace(/^https?:\/\/[^/]+\//, "");
  /* An `owner/repo#N` is linked only to a repository this install knows (`opts.known`: the lanes' repository addresses, with the page's own):
     `docs/guide#2` is a path and a number, not a pull request. The link goes to that repository's own address. */
  const known = {};
  (Array.isArray(o.known) ? o.known : []).concat(gh ? [gh] : []).forEach((u) => {
    const base = String(u || "").replace(/\/+$/, "");
    const m = base.match(/^https?:\/\/[^/]+\/([^/]+\/[^/]+)$/);
    if (m) known[m[1].toLowerCase()] = base;
  });
  let skip = 0;
  let code = 0;
  return String(html == null ? "" : html).split(/(<[^>]*>)/).map((part, i) => {
    if (i % 2){
      if (/^<(?:a|button|pre)\b/i.test(part)) skip++;
      else if (/^<\/(?:a|button|pre)\b/i.test(part)) skip = Math.max(0, skip - 1);
      else if (/^<code\b/i.test(part)) code++;
      else if (/^<\/code\b/i.test(part)) code = Math.max(0, code - 1);
      return part;
    }
    if (skip) return part;
    /* A code span is a literal: left alone, unless the whole span is one file reference (`api/x.py:143`), which is a reference. */
    if (code && !/^\s*(?:[\w.-]+\/)+[\w.-]+\.(?:py|js|ts|tsx|go|md|ya?ml|json|css|html|sql|sh|toml):\d+(?:-\d+)?\s*$/.test(part)) return part;
    return part.replace(ID_RE, (m, prd, id, pr, file, _line, ghRepo, ghNum) => {
      if (prd) return tuRefLink("prd:" + prd, esc(m), o.repo);
      if (id) return tuIdMark(id, o) || m;
      if (ghRepo) return known[ghRepo.toLowerCase()] ? `<a class="tu-ref" href="${esc(known[ghRepo.toLowerCase()])}/pull/${esc(ghNum)}" target="_blank" rel="noopener">${m}</a>` : m;
      if (pr) return gh ? `<a class="tu-ref" href="${esc(gh)}/pull/${esc(pr)}" target="_blank" rel="noopener">#${pr}</a>` : m;
      if (file) return gh && slug ? `<a class="tu-ref tu-ref-file" href="${esc(gh)}/search?q=${encodeURIComponent("repo:" + slug + " path:" + file)}&amp;type=code" target="_blank" rel="noopener" title="Find ${esc(file)} in ${esc(slug)}">${m}</a>` : m;
      return m;
    });
  }).join("");
}

/* THE ONE DETAIL-PAGE HEADER (owner: "one header layout across every detail page"). Every page that has a card header
   draws it HERE and nowhere else (`test_js_render_one_header.py` holds the line): program, slice, PRD, issue, filing, component,
   machine. The slots, top to bottom:
     crumbs    the breadcrumb above the card (html, as the page already built it);
     row 1     badge · mini stepper dots · KEY chip · ids (PRD, program, slice) · kind · priority · mode, then at the far right the
               page's primary `buttons` (Edit, Stop driving, Shell) and the `menu` (the "⋯", `tuHeaderMenu`'s html or "");
     title     the serif h1 (`title`, html);
     props     the item page's properties line (`props`, html or ""): priority, feature, labels, each a control (`team-props.js`);
     meta      ONE line, in this order and no other: state (bold sans) · since · assigned · lane · ownerNow ("owner today") · `facts` · `run` (the
               run-state chip, then `prs`, the item's pull-request chip, always last). A slot with nothing in it is skipped;
     steps     the stepper, inside the card, below the meta (`steps`, html or "").
   `ask` is a question box that leads the page: the title block is then its own card, the box follows it, and the stepper is a second card
   under the box (so the question and its answer control are on the first screen); `askAfterSteps` keeps the stepper in the one card instead. */
function tuHeader(o){
  const x = o || {};
  const all = (v) => (Array.isArray(v) ? v : [v]).filter(Boolean).join("");
  const key = x.key ? `<span class="tu-chip tu-key">${esc(x.key)}</span>` : "";
  /* THE ACTIONS ARE THEIR OWN BOX, pinned to the top-right at every width: only the badges wrap, never the buttons or the "⋯". */
  const acts = `${all(x.buttons)}${x.menu || ""}`;
  const row1 = `<div class="tu-chips"><div class="tu-hl">${x.badge || ""}${x.mini || ""}${key}${all(x.ids)}${x.kind || ""}${x.prio || ""}${x.mode || ""}</div>${acts ? `<div class="tu-hact">${acts}</div>` : ""}</div>`;
  const parts = [x.state ? `<span class="tu-st">${x.state}</span>` : "", x.since ? `since ${x.since}` : "", x.assigned || "",
    x.lane ? `lane ${x.lane}` : "", x.ownerNow ? `owner today ${x.ownerNow}` : "", ...(Array.isArray(x.facts) ? x.facts : []), x.run || "", x.prs || ""];
  /* `links` is the item page's Links row: directly under the status line, above the step strip (`tuLinksRow`). */
  const head = `${row1}<h1 class="tu-ttl">${x.title || ""}</h1>${x.props || ""}${tuMetaLine(parts)}${x.links || ""}`;
  const steps = x.steps || "";
  const crumbs = x.crumbs || "";
  /* ONE ORDER ON EVERY DETAIL PAGE: the header, the step strip, then the question card. The question used to be able to LEAD the card
     (the program page and a PRD's interview drew it between the title block and the stepper, `askAfterSteps` being the slice page's
     opt-out), which is how one page came to disagree with every other. There is no longer a way to ask for the old order; a page that
     passes `askAfterSteps` (the slice page still does) gets what every page gets. */
  return `${crumbs}<header class="tu-ph">${head}${steps}</header>${x.ask || ""}`;
}
function tuSlot(label, inner){
  return `<section class="tu-slot"><div class="tu-slot-l">${label}</div>${inner}</section>`;
}
/* THE RUNNING BOX of an item page, from the host (`runBox`): the shared work card while a background run is live on the item, with the way to
   open its conversation. `""` without a host, and while nothing runs: the standalone board has no fleet. */
function tuRunSlot(key){
  const box = TU_HOST && typeof TU_HOST.runBox === "function" ? (() => { try { return TU_HOST.runBox(key, false) || ""; } catch (err){ return ""; } })() : "";
  return box ? tuSlot("What&rsquo;s running", box) : "";
}
function tuTabs(page, cur, defs){
  return tuTabBar(defs.map(([v, l]) => ({ id: v, label: l, html: true, attrs: `data-tu-page="${esc(page)}" data-keep="tu-tab-${v}"` })), cur, "data-tu-tab");
}
function tuTabOf(page, fallback, ok){
  const at = TU_TABS[page];
  return ok.includes(at) ? at : fallback;
}

/* ASSIGNED: the program's and the slice's people, inline in the header's meta line (it was a separate "Responsible" row). `tuMountAssignees`
   (the shared module, with its "+" picker) paints it into the host after the page is on screen (`tuMountAll`), writing through the
   owners route. What is inside until then, and where the module is absent, is the owners data and picker this file already had. */
function tuAssigned(p, kind){
  const named = ownNamed(p);
  const raw = named.length
    ? named.slice(0, OWN_STACK).map(e => ownAvatar(e)).join("") + `<span>${named.map(e => esc(PEOPLE_NAMES[e] || e)).join(", ")}</span>`
    : "";
  /* WHERE THE SHARED MODULE PAINTS THE ROW, THE OWNERS DATA IS NOT SHOWN IN ITS PLACE (C1): it is the raw form and it sat on screen
     until the assignees read landed, then changed shape. The row says it is reading instead. */
  const who = tuOn() && typeof tuMountAssignees === "function" ? `<span class="tu-faint">Reading&hellip;</span>` : raw;
  const k = kind || "program";
  return `<span class="tu-ass tu-ass-inl" data-tu-assignees="${esc(p.id)}" data-tu-kind="${k}"><span class="tu-people"><span class="tu-pp"><span class="tu-lbl">Assigned</span><span class="tu-v">${who}${k === "program" && OWNERS ? ownChip(p) : ""}</span></span></span></span><span class="tu-pres" data-tu-pres="${k}:${esc(p.id)}"></span>`;
}
/* AFTER THE PAINT: hand every responsible host on the page to the shared module. */
function tuMountAll(route){
  const head = String(route).split(":")[0];
  if (!tuOn() || typeof tuMountAssignees !== "function" || (head !== "program" && head !== "slice")) return;
  const host = main && main.querySelector ? main.querySelector("[data-tu-assignees]") : null;
  const id = host && host.getAttribute ? host.getAttribute("data-tu-assignees") : "";
  const item = head === "slice" ? SL[id] : PG[id];
  if (!id || !item) return;
  try { tuMountAssignees(host, head, id, item); } catch (err){ /* the fallback inside the host stays */ }
}
ROUTED.push(tuMountAll);
/* WHO ELSE HAS THIS PAGE OPEN: after the paint, hand the program or slice page's presence host to the shared heartbeat
   (`tuPresenceAttach`, static/team-ui.js). Only behind the New UI switch; a page with no host is left alone. */
const TU_PRES_WHERE = { overview: "the overview", plan: "the plan", slices: "the slices", delivery: "the delivery log", activity: "the activity", prds: "the PRDs", order: "the order of work" };
function tuPresenceRoute(route){
  if (!tuOn() || typeof tuPresenceAttach !== "function") return;
  const head = String(route).split(":")[0];
  if (head !== "program" && head !== "slice") return;
  const host = main && main.querySelector ? main.querySelector("[data-tu-pres]") : null;
  const at = host && host.getAttribute ? String(host.getAttribute("data-tu-pres") || "") : "";
  const cut = at.indexOf(":");
  if (cut < 1) return;
  const page = at;
  try { tuPresenceAttach(at.slice(0, cut), at.slice(cut + 1), () => TU_PRES_WHERE[TU_TABS[page]] || (head === "slice" ? "the PRDs" : "the overview")); } catch (err){ /* the page does not depend on it */ }
}
ROUTED.push(tuPresenceRoute);
function tuDrivenPill(p, always){
  if (!DELIVERY) return "";
  const closed = p.complete || p.state === "withdrawn" || p.state === "waived";
  const said = DELIVERY(String(p.id || ""));
  /* NOT READ YET IS NOT "NOT DRIVEN" (C1): the drive document is a slow read of its own, and `DELIVERY` answers null until it or the
     list has landed. The chip said "Not driven" over a driven program for the seconds in between; it now says it is checking. */
  if (said === null || said === undefined) return closed && !always ? "" : `<span class="tu-dchip">Checking&hellip;</span>`;
  const word = said && typeof said.reading === "string" ? said.reading : "";
  const on = DRIVEN_READINGS.includes(word) && !(said && said.inert);
  if (closed && !on && !always) return "";
  return `<span class="tu-dchip${on ? " on" : ""}">${on ? "Driven" : "Not driven"}</span>`;
}

/* "PROVED BY" in plain words, each PRD a link to its page. A drill is the record of one observation of the composed path and
   belongs to the Proven step, which names it ("Drill 0900-PG30 · unproven — a person runs it"); it is said here only where no PRD
   proves the program, and then as words, never as the record's id in a chip. */
function tuProofSaid(proof){
  const prds = proof.filter(n => !isDrill(n));
  if (prds.length) return `proved by ${prds.map(n => link("prd:" + n, "tu-lnk", "PRD " + esc(n))).join(", ")}`;
  return `proved by ${proof.map(n => `<span title="${esc(drillStem(n))}">drill ${esc(drillShort(n))}</span>`).join(", ")}`;
}

/* WHAT THE HOST'S DELIVERY BOX NEEDS THAT ONLY THE PLAN KNOWS: what is building, what is ready for a seat,
   and how many PRDs each one holds back. */
function tuDeliveryFacts(rows){
  const building = rows.filter(r => r.state !== "shipped" && (() => { const at = liveRowOf(r.n); return !!(at && at.status); })());
  const live = new Set(building.map(r => r.n));
  const frees = {};
  rows.forEach(r => { frees[r.n] = r.frees; });
  const brief = r => ({ n: r.n, title: r.title });
  /* WHAT IS LEFT TO PLAN, off the PRDs' own statuses: `stub` needs its PRD, `prd-drafted` its design, `designed` its plan. */
  const at = s => rows.filter(r => r.status === s).length;
  return { building: building.map(brief), ready: rows.filter(r => r.state === "ready" && !live.has(r.n)).map(brief), frees: frees, total: rows.length,
    plan: { total: rows.length, stub: at("stub"), drafted: at("prd-drafted"), designed: at("designed") } };
}

/* THE OUTCOME IS ITS FIRST SENTENCE(S); THE EXAMPLE FOLDS UNDER IT. The example starts at the first later sentence of
   the opening paragraph that tells a scene (a time of day, "for example"), else at the second paragraph; with neither,
   nothing is folded and nothing is invented. */
const TU_EXAMPLE = /^(for (example|instance)|e\.g\.|an? example|imagine|picture)\b|\b\d{1,2}(:\d{2})?\s?(am|pm)\b/i;
function tuOutcome(p){
  const note = descNote(p.desc);
  if (note) return `<p class="tu-pov-lead tu-muted">${esc(note)}</p>`;
  const paras = String(p.desc).trim().split(/\n\s*\n/);
  const first = paras.shift();
  const sents = first.split(/(?<=[.!?])\s+(?=[A-Z])/);
  const at = sents.findIndex((x, i) => i > 0 && TU_EXAMPLE.test(x));
  const lead = at > 0 ? sents.slice(0, at).join(" ") : first;
  const more = (at > 0 ? [sents.slice(at).join(" ")] : []).concat(paras);
  return `<div class="tu-pov-lead">${mdown(lead)}</div>${more.length
    ? `<details class="tu-pov-ex"><summary>An example</summary><div class="tu-md">${mdown(more.join("\n\n"))}</div></details>` : ""}`;
}
/* THE PROGRAM'S DECISIONS (the owner's call): the answered questions of every PRD and slice in it, newest first -- no store of
   their own. A program nobody has answered a question in draws neither the block nor the tab, and no sentence in their place.
   EVERY ONE IS DRAWN BY THE ITEM PAGE'S ONE DECISION RENDERER (`team-item.js`: `tuItemDecisionCard`, `tuItemDecisionLog`): this
   file keeps no card of its own, so the program page's log is the item page's log -- the same card, fields, order, clamp and
   links -- and only the reading it hands over (`tuDecisionOpts`) is the program's. */
function tuDecisionOpts(hostFacts, scope, noun){
  return { scope: scope, readAt: String((hostFacts && hostFacts.readAt) || ""), viewer: String((hostFacts && hostFacts.viewer) || ""),
    noun: noun, more: !!(hostFacts && hostFacts.decisionsMore), md: mdBlock };
}
/* `own` = the page's OWN answered question sets (`pageQuestions(...).answeredRows`): rows of the same card, merged into this one log with
   the child decisions and sorted newest first by it -- an answered set is never drawn on the page top. */
function tuDecisionLog(kind, id, decs, hostFacts, own){
  if (typeof tuItemDecisionLog !== "function") return "";
  return tuItemDecisionLog([...(own || []), ...decs.map(tuItemProgramDecisionRow)], tuDecisionOpts(hostFacts, kind + ":" + id, kind));
}
/* WHERE IT STANDS: ONE FUNCTION FOR THE PROGRAM PAGE AND THE SLICE PAGE (the owner's call): four one-line rows -- Built, Proof, Waits on
   you, Fleet -- each a mark (done / now / later), a label and a sentence. `rows` = [{ k, m: "done" | "now" | "later", t: html }]. Neither page
   draws this section itself, and neither words a row differently from the other: they hand over what they know. */
function tuWhereItStands(rows){
  const mark = { done: "&#10003;", now: "&bull;", later: "&#9675;" };
  return `<section class="tu-ws"><h3 class="tu-h3">Where it stands</h3><ul class="tu-ws-l">${rows.map(r =>
    `<li class="tu-ws-r tu-ws-${r.m}"><span class="tu-ws-m">${mark[r.m] || mark.later}</span><span class="tu-ws-k">${esc(r.k)}</span><span class="tu-ws-t">${r.t}</span></li>`).join("")}</ul></section>`;
}
/* THE PROOF ROW, which a program and a slice say in the same words: what proves it, and what is still owed. */
function tuProofStand(o){
  const proof = o.proof || [];
  const pname = n => isDrill(n) ? "Drill " + drillShort(n) : "PRD " + n;
  const open = proof.find(n => isDrill(n) ? (drillOf(n) || {}).verdict !== "passed" : !(PRD[n] && PRD[n].status === "shipped"));
  if (o.waived && !proof.length) return { k: "Proof", m: "done", t: "Proof waived by a written decision" };
  if (proof.length && open){
    return { k: "Proof", m: "now", t: isDrill(open) ? `${esc(pname(open))} &middot; ${esc((drillOf(open) || {}).verdict || "unproven")} &mdash; a person runs it`
      : `${esc(pname(open))} is ${esc((PRD[open] || {}).status || "not written")}` };
  }
  if (proof.length) return { k: "Proof", m: "done", t: `${esc(proof.map(pname).join(", "))} ${o.proved ? "drove" : "drives"} the composed path` };
  return o.owed ? { k: "Proof", m: "now", t: `Owed: ${esc(o.owed)}` } : { k: "Proof", m: "later", t: "No proof named" };
}
/* THE ROW OF WHAT WAITS ON A PERSON: the held-up PRDs by name, each a link to where the answer happens. */
function tuWaitsStand(holds, extra){
  const named = holds.slice(0, 3).map(h => link(h.route || ("prd:" + h.prd), "tu-lnk", esc(h.linkText || h.issue || ("PRD " + h.prd)))).join(", ") + (holds.length > 3 ? ` +${holds.length - 3}` : "");
  if (holds.length) return { k: "Waits on you", m: "now", t: `${holds.length} item${holds.length === 1 ? "" : "s"}: ${named}` };
  return extra ? { k: "Waits on you", m: "now", t: extra } : { k: "Waits on you", m: "done", t: "Nothing waits on a person" };
}
/* THE FLEET ROW: who drives the program and when it last ran, in the words the old running line used. The chip on the status line
   says whether it is running now; this row says what it has done. */
function tuFleetStand(p, hostFacts, holds, nothingLeft){
  const f = hostFacts || {};
  if (p && p.closed) return { k: "Fleet", m: "done", t: `Closed ${esc(tuDay(p.closed))}; starts again on its own if the program changes` };
  if (f.driven === true){
    const cycles = f.cycleCount ? ` &middot; ${esc(f.cycleCount)} cycle${Number(f.cycleCount) === 1 ? "" : "s"}${f.lastCycleWhen || f.lastCycle ? ", the last " + esc(f.lastCycleWhen || f.lastCycle) : ""}` : "";
    const next = nothingLeft && holds.length ? " &middot; the next cycle starts once you act" : "";
    return { k: "Fleet", m: "later", t: `Driven${f.startedBy ? " by " + esc(f.startedBy) : ""}${f.startedAt ? " since " + esc(f.startedAt) : ""}${cycles}${next}` };
  }
  if (f.driven === false) return { k: "Fleet", m: "later", t: `Not driven${f.notDrivable ? " &mdash; " + esc(f.notDrivable) : ""}` };
  return { k: "Fleet", m: "later", t: "Checking&hellip;" };
}
function tuProgramStands(p, rows, facts, holds, hostFacts){
  const total = rows.length;
  const shipped = rows.filter(r => r.state === "shipped").length;
  const nsl = (p.sl || []).length;
  const slicesDone = (p.sl || []).filter(s => s.state === "complete").length;
  const waived = waivedCuts(p);
  const built = total ? `${shipped} of ${total} PRD${total === 1 ? "" : "s"} shipped` : "No PRDs are written yet";
  const cuts = nsl ? ` &middot; ${slicesDone} of ${nsl} slice${nsl === 1 ? "" : "s"} done${waived.length ? `, ${waived.length} waived by a written decision` : ""}` : "";
  const nothingLeft = !(facts.building || []).length && !(facts.ready || []).length && rows.every(r => r.state === "shipped");
  const rowsOut = [{ k: "Built", m: total && shipped === total ? "done" : total ? "now" : "later", t: built + cuts },
    tuProofStand({ proof: p.proof, waived: p.waived, owed: p.owed, proved: !!(p.proofok || p.complete || p.closed) }),
    tuWaitsStand(holds), tuFleetStand(p, hostFacts, holds, nothingLeft)];
  /* A PROGRAM CLOSED TO NEW WORK SAYS WHERE NEW WORK GOES, ONCE, HERE (never in the header). */
  if (p.closedToNewWork) rowsOut.push({ k: "New work", m: "later", t: "Goes to a feature, not this program" });
  return rowsOut;
}
function tuSliceStands(s, p, rows, holds, hostFacts, asked, empty, driveText){
  const total = rows.length;
  const shipped = rows.filter(r => r.state === "shipped").length;
  const open = !!(asked && asked.open);
  const built = total ? `${shipped} of ${total} PRD${total === 1 ? "" : "s"} shipped` : empty || "No PRDs are written yet";
  const unread = !hostFacts || hostFacts.driven === null || hostFacts.driven === undefined;
  const drive = !p ? { k: "Fleet", m: "later", t: "Not part of a program" }
    : unread && driveText ? { k: "Fleet", m: "later", t: driveText } : tuFleetStand(p, hostFacts, holds, false);
  const fleet = p && hostFacts && hostFacts.driven === true
    ? { k: "Fleet", m: "later", t: `Driven as part of ${link("program:" + p.id, "tu-lnk", esc(p.id))}${hostFacts.startedBy ? " by " + esc(hostFacts.startedBy) : ""}` } : drive;
  /* A SLICE DRIVEN ON ITS OWN is driven, whatever its program says: the Delivery box above is running it. */
  const alone = TU_HOST && typeof TU_HOST.sliceDriven === "function" && (() => { try { return !!TU_HOST.sliceDriven(s); } catch (err){ return false; } })();
  const fleetRow = alone && !(hostFacts && hostFacts.driven === true) ? { k: "Fleet", m: "later", t: "Driven on its own &mdash; only this slice" } : fleet;
  return [{ k: "Built", m: total && shipped === total ? "done" : total ? "now" : "later", t: built },
    tuProofStand({ proof: s.proof, waived: s.state === "waived", owed: s.owed, proved: !!s.proven }),
    tuWaitsStand(holds, open ? "A question is waiting on you &mdash; it is the box above" : ""), fleetRow];
}
/* THE OVERVIEW TAB: the item pages' "In plain words" (`tuItemPlain`, the one section), then the stands rows, then the slices. */
function tuPlainWords(html){
  return typeof tuItemPlain === "function" ? tuItemPlain(html, "") : `<section><h3 class="tu-h3">In plain words</h3><div class="tu-ov1-text">${html}</div></section>`;
}
function tuOverview(p, rows, stands){
  return `<div class="tu-pov">${tuPlainWords(tuOutcome(p))}${tuWhereItStands(stands)}
    <section><div class="tu-pov-h"><h3 class="tu-h3">Slices <span class="tu-sm tu-muted">&middot; ${p.sl.length}</span></h3></div>${tuSlicesList(p, rows)}${rows.length ? `<p class="tu-sm"><button type="button" class="tu-lnk" data-tu-tab="plan" data-tu-page="program:${esc(p.id)}" data-keep="tu-ov-plan">See the plan, slice by slice &rarr;</button></p>` : ""}</section></div>`;
}
function tuSlicesList(p, rows){
  return (p.sl || []).length ? tuSliceRoll(p, rows)
    : `<p class="tu-sm tu-muted">No slices. Nothing can be planned or started in this program until one is cut.</p>`;
}
/* THE SLICES TAB, the prototype's Plan blocks: one per slice with what it promises, what proves it, its bar and its PRDs. */
function tuSlicesTab(p, rows){
  return (p.sl || []).length ? p.sl.map(s => tuSliceCard(p, s, rows, false)).join("")
    : `<p class="tu-sm tu-muted">No slices. Nothing can be planned or started in this program until one is cut.</p>`;
}
/* THE PLAN TAB (the owner's call): the slice cards are the view; above them the ORDER OF WORK as chips (one block, `tuWaves`, with the
   slice legend the chips' dots refer to), and below them the cross-program chain, collapsed. No Group by, no second PRD table. */
function tuPlanTab(p, rows){
  const order = rows.length ? `<section class="tu-slb">${tuLegend(p)}${tuWaves(p, rows, true)}</section>` : "";
  const chain = (p.sl || []).length
    ? `<details class="tu-more"><summary>Everything standing between this program and its proof, across programs</summary>${chainSection(p, programChain(p), true)}</details>` : "";
  return `${order}${tuSlicesTab(p, rows)}${chain}`;
}
/* A DAY AS THE ITEM PAGES SAY IT: an ISO day reads "6 Oct" (with the year when it is not this one). Anything else is left as written. */
const TU_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function tuDay(v){
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v == null ? "" : v));
  if (!m) return String(v == null ? "" : v);
  const label = Number(m[3]) + " " + TU_MON[Number(m[2]) - 1];
  return Number(m[1]) === new Date().getFullYear() ? label : label + " " + m[1];
}
/* THE PRIORITY THE PROGRAMS LIST SHOWS: the place among the placed programs that list draws (it hides the proven ones), as the item
   page's plain "P3" chip. A closed or parked program has none, and neither has one nobody placed. */
function tuPrioChip(p){
  if (p.closed || p.complete) return "";
  const saved = VIEW_ORDER;
  let r = null;
  try {
    VIEW_ORDER = applyFilters().filter(isPlaced).map(authoredOf).sort((a, b) => a - b);
    r = priorityOf(p);
  } catch (err){ r = null; } finally { VIEW_ORDER = saved; }
  return r && r.rank ? `<span class="tu-chip" title="Priority ${r.rank} in your order of programs">P${r.rank}</span>` : "";
}

/* THE STEP STRIP: Shaped, Planned, Building, Proven, Closed, each in the words of data the page already reads. The first step not
   done is the current one; every later one is still to come. */
/* TRUE WHILE A PROGRAM PAGE DRAWS A CLOSING CHECK THE FLEET GAVE UP ON (`ship-escalated`): the Closed step then says so. */
let TU_CLOSING = false;
function tuProgramSteps(p, rows, facts, holds){
  const total = rows.length;
  const shipped = rows.filter(r => r.state === "shipped").length;
  const plan = facts.plan || { total: total, stub: 0, drafted: 0, designed: 0 };
  const left = (Number(plan.stub) || 0) + (Number(plan.drafted) || 0) + (Number(plan.designed) || 0);
  const nsl = (p.sl || []).length;
  const waived = waivedCuts(p);
  const slicesDone = (p.sl || []).filter(s => s.state === "complete").length;
  const proof = p.proof || [];
  const pname = n => isDrill(n) ? "Drill " + drillShort(n) : "PRD " + n;
  const proofShipped = !!(p.proofok || p.complete || p.closed);
  const shapedOk = nsl > 0;
  const plannedOk = shapedOk && total > 0 && left === 0;
  const builtOk = (plannedOk && shipped === total) || proofShipped || p.phase === "closing" || p.phase === "proven";
  const closedOk = !!p.closed;
  const open = proof.find(n => isDrill(n) ? (drillOf(n) || {}).verdict !== "passed" : !(PRD[n] && PRD[n].status === "shipped"));
  const oneHold = holds.length ? ` &middot; PRD ${esc(holds[0].prd || holds[0].issue)} waits on a person${holds.length > 1 ? ` (+${holds.length - 1})` : ""}` : "";
  const openProof = !open ? ""
    : isDrill(open) ? `${pname(open)} &middot; ${esc((drillOf(open) || {}).verdict || "unproven")} &mdash; a person runs it`
    : `${pname(open)} is ${esc((PRD[open] || {}).status || "not written")}`;
  const text = {
    shaped: [nsl ? `${nsl} slice${nsl === 1 ? "" : "s"} cut` : "", "No slice is cut yet"],
    planned: [total ? (total === 1 ? "The PRD has its PRD, design and plan" : `All ${total} PRDs have PRD, design and plan`) : "",
      left ? `${left} of ${total} PRD${total === 1 ? "" : "s"} still ${left === 1 ? "needs" : "need"} planning` : "No PRDs are written yet"],
    building: [slicesDone || waived.length ? `${slicesDone} slice${slicesDone === 1 ? "" : "s"} done${waived.length ? `, ${waived.length} waived by a written decision` : ""}` : `${shipped} of ${total} PRDs shipped`,
      `${shipped} of ${total} shipped${oneHold}`],
    proven: [proof.length ? `${proof.map(pname).join(", ")} drove the composed path` : p.waived ? "Proof waived by a written decision" : "Proof shipped",
      p.waived && !proof.length ? "Proof waived by a written decision" : openProof || (p.owed ? `Owed: ${esc(p.owed)}` : proof.length ? "Waits on the proof" : "No proof named")],
    closed: [p.closed ? `${esc(tuDay(p.closed))} &middot; closing record` : "Closed", TU_CLOSING ? "The closing check could not close it and needs a person" : "Closes when the closing check passes"],
  };
  const flags = [shapedOk, plannedOk, builtOk, proofShipped, closedOk];
  const names = [["shaped", "Shaped"], ["planned", "Planned"], ["building", "Building"], ["proven", "Proven"], ["closed", "Closed"]];
  const firstOpen = flags.indexOf(false);
  const out = names.map(([k, label], i) => {
    const kind = firstOpen < 0 || i < firstOpen ? "done" : i === firstOpen ? "cur" : "todo";
    const body = kind === "done" ? text[k][0] : kind === "cur" ? text[k][1] : (k === "proven" && proof.length ? `${pname(proof[0])} drives the composed path` : text[k][1]);
    /* ONLY PROVEN CARRIES A PERSON (the mockup): a hold under Building is said in its text, and the fleet is still building the rest. */
    const who = kind === "cur" && k === "proven" && open && isDrill(open) ? "person" : "fleet";
    return { kind: kind, label: label, body: body, who: who };
  });
  return tuStepMarkup(out);
}
/* THE STEP STRIP'S MARKUP, the item page's: the list under the title and the five dots beside the chips. */
function tuStepMarkup(out){
  const list = `<div class="tu-jr2"><ol class="tu-jr2-steps">${out.map(x =>
    `<li class="tu-${x.kind}"><div class="tu-jn"><span class="tu-dot2">${x.kind === "done" ? "&#10003;" : ""}</span><b>${x.label}</b><span class="tu-who tu-${x.who}">${x.who === "person" ? "person" : "Fleet"}</span></div><div class="tu-jb">${x.body}</div></li>`).join("")}</ol></div>`;
  const mini = `<span class="tu-mini tu-jr2-mini">${out.map(x => `<i class="${x.kind === "done" ? "tu-d" : x.kind === "cur" ? "tu-c" : ""}"></i>`).join("")}</span>`;
  /* THE STATE THE HEADER'S META LINE LEADS WITH: the current step in its DOING word ("Planning"), or the last step's done word
     once every step is done. A step's name is its done word, so the current step's name said "Planned" beside "3 of 3 PRDs still
     need planning" on one strip (a customer install found it). */
  const cur = out.find(x => x.kind === "cur");
  const at = cur || out[out.length - 1];
  return { list: list, mini: mini, state: !at ? "" : cur ? (TU_STEP_DOING[cur.label] || cur.label) : at.label };
}
/* EACH STEP'S DOING WORD, by its done word (the label `tuProgramSteps` / `tuSliceSteps` draw). */
const TU_STEP_DOING = { Shaped: "Shaping", Planned: "Planning", Building: "Building", Proven: "Proving", Closed: "Closing" };
/* A SLICE'S FIVE STEPS, the program's, one tier down and read off the same facts: it is cut (Shaped), its PRDs have PRD, design and
   plan (Planned), they have shipped (Building), what proves it has (Proven), and its "Done when" is met (Closed). The first not done
   is the current one. A held PRD is said under Building; only Proven can be a person's. */
function tuSliceSteps(s, rows, holds){
  const total = rows.length;
  const shipped = rows.filter(r => r.state === "shipped").length;
  const at = st => rows.filter(r => r.status === st).length;
  const left = at("stub") + at("prd-drafted") + at("designed");
  const proof = s.proof || [];
  const pname = n => isDrill(n) ? "Drill " + drillShort(n) : "PRD " + n;
  const open = proof.find(n => isDrill(n) ? (drillOf(n) || {}).verdict !== "passed" : !(PRD[n] && PRD[n].status === "shipped"));
  const provenOk = !!s.proven || s.state === "complete" || s.state === "waived";
  const plannedOk = total > 0 && left === 0;
  const builtOk = (plannedOk && shipped === total) || provenOk;
  const closedOk = s.state === "complete";
  const oneHold = holds.length ? ` &middot; PRD ${esc(holds[0].prd || holds[0].issue)} waits on a person${holds.length > 1 ? ` (+${holds.length - 1})` : ""}` : "";
  const featureName = s.program ? "" : String(((typeof dpAreaOf === "function" && dpAreaOf({ kind: "slice", sid: s.id })) || {}).name || s.area || "");
  const text = {
    shaped: [s.program ? `Cut inside ${esc(s.program)}` : featureName ? `Cut inside the ${esc(featureName)} feature` : "Cut as its own slice", ""],
    planned: [total === 1 ? "The PRD has its PRD, design and plan" : `All ${total} PRDs have PRD, design and plan`,
      total ? `${left} of ${total} PRD${total === 1 ? "" : "s"} still ${left === 1 ? "needs" : "need"} planning` : "No PRDs are written yet"],
    building: [`${shipped} of ${total} PRDs shipped`, `${shipped} of ${total} shipped${oneHold}`],
    proven: [proof.length ? `${proof.map(pname).join(", ")} proved it` : "Proof shipped",
      proof.length ? (open ? (isDrill(open) ? `${pname(open)} &middot; ${esc((drillOf(open) || {}).verdict || "unproven")} &mdash; a person runs it` : `${pname(open)} is ${esc((PRD[open] || {}).status || "not written")}`)
        : "Waits on the proof") : (s.owed ? `Owed: ${esc(s.owed)}` : "No proof named")],
    closed: [`Done when is met`, "Its Done when is met once every PRD has shipped and the proof has"],
  };
  const flags = [true, plannedOk, builtOk, provenOk, closedOk];
  const names = [["shaped", "Shaped"], ["planned", "Planned"], ["building", "Building"], ["proven", "Proven"], ["closed", "Closed"]];
  const firstOpen = flags.indexOf(false);
  return tuStepMarkup(names.map(([k, label], i) => {
    const kind = firstOpen < 0 || i < firstOpen ? "done" : i === firstOpen ? "cur" : "todo";
    const body = kind === "done" ? text[k][0] : text[k][1] || text[k][0];
    return { kind: kind, label: label, body: body, who: kind === "cur" && k === "proven" && open && isDrill(open) ? "person" : "fleet" };
  }));
}

/* WAITING ON A PERSON: one card per PRD held up on a person (the drive document's holds the service names), each linking to
   the page where the answer happens, then the host's own question cards. Nothing at all when nothing waits. */
/* THE ONE ASK FRAME — every card that asks a person for something is drawn in these three zones, in this order, and
   nothing else (the owner: "first content why/what/context then action/answer/whatever buttons", "the same pattern
   across all pages"):
     1. WHY AND WHAT — a plain-words heading for the ask, an "asked by … · when" line, a reason of one or two sentences;
     2. THE CONTENT — numbered steps, or the question with its options (and the designs it is about, above the options),
        and a recorded fact as a green-edged line;
     3. THE ACTIONS — last, behind a hairline: ONE primary that settles the ask, then quieter secondaries, each with a
        one-line muted hint saying when it applies;
   and the run's own raw text folded at the very bottom, under "What the run wrote".
   No control is ever drawn before zone 1. It lives HERE, in the stdlib-only `board.js`, rather than in `team-ui.js`, because
   a host with no Fleet draws held-up cards with it too (`tuHoldCards`) and `team-ui.js` is not shipped there; every Fleet
   renderer reaches it as `Board.askFrame`. `test_js_render_ask_frame.py` holds every ask card to this order.
   `o`: { cls, attrs, heading, by, why, whyLabel, zone1 (raw html, after the structured part), content, recorded,
          pre (raw, before the heading), headId, headCls, actAttrs, primary (html), primaryHint, secondary: [{ html, hint }], fold: { label, html } } — every value is already-escaped HTML. */
/* THE QUESTION BOX (`o.box`; the owner approved the mockup): the same three zones, drawn as ONE column on ONE background.
     PINNED HEAD (zone 1)  — eyebrow ("Fleet asked · <age>"), the question as the heading, ONE reason line and, only when there
                             is more, a "More context" toggle at its end;
     THE MIDDLE (zone 2)   — the only part that scrolls: the context the toggle opens, then the designs, the options, the answer;
     PINNED FOOT (zone 3)  — the count, the quiet buttons, ONE primary, behind a full-width rule.
   The box is capped at half of the container it sits in and keeps one inset on every section, so the zones' edges all line up.
   `o.eyebrow`, `o.reason` and `o.more` are already-escaped HTML; `o.moreAttrs` is stamped on the toggle (its open state survives a
   repaint). The hints the plain frame draws under each button stay in the markup and are hidden by the box's stylesheet: the box
   says less. The scroll cue (`.tu-fr-mid[data-bx-scroll]`) is set by the page while the middle actually overflows. */
function askFrame(o){
  const box = !!o.box;
  /* THE PLAIN FRAME says who asked and why in a labelled block; THE BOX says the same in the head's two lines: the eyebrow over the
     heading, and the reason under it with the toggle (`<details>`, never inside a `<p>`: the parser would close the paragraph). */
  const why = box ? "" : o.why
    ? `<div class="tu-fr-why">${o.whyLabel === "" ? "" : `<h4 class="tu-fr-z">${o.whyLabel || "Why it is on you"}</h4>`}<div class="tu-fr-t">${o.why}</div></div>` : "";
  /* IN A BOX THE TOGGLE AND ITS BLOCK ARE ALWAYS DRAWN, and the stylesheet hides both while the block is empty (`.tu-bx-more:empty`): a
     wrapper that learns of more context after the card was drawn (the slot's family badge, who asked, what it is about) puts it INTO the
     block, and the one toggle shows. Nothing a person needs is dropped; it is folded. Both labels are in the summary and the stylesheet
     shows one (`display:none` takes the other out of the accessible name too), so the name is always what is shown. */
  const toggle = box ? `<details class="tu-mdet"${o.moreAttrs ? " " + o.moreAttrs : ""}><summary><span class="tu-m-more">${o.moreLabel || "More context"}</span><span class="tu-m-less">Less</span></summary></details>` : "";
  const lead = box ? (o.eyebrow ? `<span class="tu-bx-meta">${o.eyebrow}</span>` : "") : "";
  const reason = box && (o.reason || toggle) ? `<div class="tu-bx-reason">${o.reason ? `<div class="tu-bx-r">${o.reason}</div>` : ""}${toggle}</div>` : "";
  const z1 = `<div class="tu-fr-1" data-fr-zone="why">${o.pre || ""}${lead}${o.heading ? `<h3 class="tu-fr-h${o.headCls ? " " + o.headCls : ""}"${o.headId ? ` id="${o.headId}"` : ""}>${o.heading}</h3>` : ""}${
    box ? "" : o.by ? `<p class="tu-fr-by">${o.by}</p>` : ""}${why}${reason}${o.zone1 || ""}</div>`;
  const more = box ? `<div class="tu-bx-more">${o.more || ""}</div>` : "";
  const inner = `${more}${o.content || ""}${o.recorded ? `<p class="tu-fr-rec">${o.recorded}</p>` : ""}`;
  const z2 = box || o.content || o.recorded
    ? (box ? `<div class="tu-fr-mid">` : "") + `<div class="tu-fr-2" data-fr-zone="content">${inner}</div>` + (box ? "</div>" : "") : "";
  /* IN A BOX A BUTTON'S HINT IS ITS `title` (plain text on hover), not a line of its own under it: the box says less. */
  /* A HINT IS TEXT, NOT MARKUP: its tags come off and the few entities a hint carries are read as the characters they name. */
  const NAMED = { rsquo: "\u2019", mdash: "\u2014", middot: "\u00b7", amp: "&", quot: '"', lt: "<", gt: ">" };
  const plain = h => String(h).replace(/<[^>]*>/g, "").replace(/&#(x[0-9a-f]+|\d+);/gi, (m, n) => { const c = n[0] === "x" || n[0] === "X" ? parseInt(n.slice(1), 16) : parseInt(n, 10); return c > 0 && c < 0x110000 ? String.fromCodePoint(c) : m; }).replace(/&(\w+);/g, (m, n) => (NAMED[n] !== undefined ? NAMED[n] : m));
  const hintTitle = h => ` title="${esc(plain(h))}"`;
  const hint = h => h ? (box ? "" : `<span class="tu-fr-hint">${h}</span>`) : "";
  const sec = (o.secondary || []).filter(x => x && x.html).map(x =>
    `<div class="tu-fr-sec"${box && x.hint ? hintTitle(x.hint) : ""}>${x.html}${hint(x.hint)}</div>`).join("");
  const z3 = o.primary || sec
    ? `<div class="tu-fr-3" data-fr-zone="act"${o.actAttrs ? " " + o.actAttrs : ""}>${o.primary ? `<div class="tu-fr-pri"${box && o.primaryHint ? hintTitle(o.primaryHint) : ""}>${o.primary}${hint(o.primaryHint)}</div>` : ""}${sec}</div>` : "";
  const fold = o.fold && o.fold.html
    ? `<details class="tu-fr-fold"><summary>${o.fold.label || "What the run wrote"}</summary><div class="tu-fr-old">${o.fold.html}</div></details>` : "";
  return `<section class="tu-fr${box ? " tu-box" : ""}${o.cls ? " " + o.cls : ""}"${o.attrs ? " " + o.attrs : ""}>${z1}${z2}${z3}${fold}</section>`;
}

/* WAITING ON A PERSON: one card per PRD held up on a person (the drive document's holds the service names), then the host's own
   question cards. Each is the ask frame: the question being waited on leads (what and why), the way there is the one primary. */
function tuHoldCards(holds, asks){
  const cards = holds.map(h => askFrame({
    cls: "tu-wcard", attrs: `data-tu-hold="${esc(h.issue || h.prd)}"`,
    heading: h.heading ? esc(h.heading) : h.prd ? `${h.tag === "Decide" ? "Answer one question to unblock" : "Held up on a person:"} PRD ${esc(h.prd)}` : esc(h.title || h.issue),
    by: h.byline ? esc(h.byline) : `<span class="tu-wcard-g">${esc(h.tag || "By hand")}</span> held up &middot; 1 ${h.prd ? "PRD" : "item"}${
      h.prd ? " &middot; " + link("prd:" + h.prd, "tu-lnk", "PRD " + esc(h.prd)) + " &middot; " + esc(h.title || h.issue) : ""}`,
    why: h.why ? esc(h.why) : "", whyLabel: "Why it is held up",
    primary: h.releaseHtml || (h.route ? link(h.route, "act primary filled", "Open " + esc(h.linkText || h.issue || "it") + " &rarr;") : ""),
  })).join("");
  return cards + (asks || "");
}
/* THE HOLDS OF A PROGRAM'S PAGE: the drive document's own (a PRD held by hand or on an approval), then a person's own
   planning hold (ENG-21070), then one for every PRD a question is open on that the document does not already name. A
   question is answered on that PRD's own page, so it is a card with a way there, never the interview itself (the
   owner: "ONE card for the held-up PRD"). */
function tuHolds(hostFacts){
  const f = hostFacts || {};
  const holds = Array.isArray(f.holds) ? f.holds.slice() : [];
  const seen = new Set(holds.map(h => String(h.prd || h.issue || "")));
  /* A HOLD A PERSON'S OWN SESSION LEFT (ENG-21070): the host marks the row `localHold` and supplies its release
     control (`releaseHtml`). It is a person's to release, never the fleet's, and never a timer's. */
  (Array.isArray(f.planningHolds) ? f.planningHolds : []).forEach(h => {
    const id = String(h && (h.issue || h.key) || "");
    const prd = String(h && h.prd || "");
    if (!id || seen.has(id) || (prd && seen.has(prd))) return;
    seen.add(id);
    if (prd) seen.add(prd);
    holds.push({ ...h, prd: prd, issue: id, linkText: String(h.title || id) });
  });
  (Array.isArray(f.asks) ? f.asks : []).forEach(a => {
    const n = String(a && a.prd || "");
    if (!n || seen.has(n)) return;
    seen.add(n);
    holds.push({ prd: n, issue: "PRD " + n, linkText: "PRD " + n, title: String((PRD[n] || {}).title || a.title || ("PRD " + n)), tag: "Decide",
      why: a.prompt ? `Waits for a person to answer: ${a.prompt}` : "Waits until a person answers its question.", route: "prd:" + n });
  });
  return holds;
}
/* THE HOLDS THAT BELONG TO ONE SLICE: the PRDs it holds, by the plan's own rows. */
function tuHoldsIn(holds, rows){
  const mine = new Set(rows.map(r => String(r.n)));
  return holds.filter(h => mine.has(String(h.prd || "")));
}
function tuTextOf(v){
  if (Array.isArray(v)) return v.length ? `<ul class="tu-ul">${v.map(x => `<li>${esc(typeof x === "string" ? x : JSON.stringify(x))}</li>`).join("")}</ul>` : "";
  if (v == null || v === "") return "";
  return `<p>${esc(typeof v === "string" || typeof v === "number" ? String(v) : JSON.stringify(v))}</p>`;
}
function tuActivity(p, facts){
  const rows = (facts && Array.isArray(facts.activity)) ? facts.activity : [];
  if (!rows.length || typeof tuItemProgramActivity !== "function") return `<div class="tu-dl"><div class="tu-pane-empty">Nothing is recorded for ${esc(p.id)} yet. Starting or stopping its drive, and each delivery cycle, appear here.</div></div>`;
  /* THE ONE TIMELINE (`team-item.js`), the item pages' Activity: a delivery cycle is an event of its own kind, a day's cycles one line. */
  return tuItemProgramActivity(rows.map(r => Object.assign({}, r, { moved: r.moved ? tuTextOf(r.moved) : "" })),
    { scope: "act:program:" + p.id, readAt: String((facts && facts.readAt) || ""), viewer: String((facts && facts.viewer) || ""), md: mdBlock });
}

/* ── the program page ────────────────────────────────────────────────────────────────────────────── */
function tuProgramPage(id){
  const p = PG[id];
  const rows = tuPrds(p);
  const own = new Set([id, ...p.sl.map(s => s.id)]);
  const mine = entityActions(id)
    .filter(a => own.has(a.id) || !a.fleet)
    .slice()
    .sort((a, b) => (b.depthBehind - a.depthBehind) || (b.blocks.length - a.blocks.length));
  const carried = mine.find(a => a.cmdKey === "program_deliver" && a.cmd) || null;
  const stalled = !!p.deliver && mine.some(a => a.cmd === p.deliver);
  const dcmd = p.deliver && !stalled ? p.deliver : carried && !p.deliver ? carried.cmd : "";
  const dbuilt = p.deliver && !stalled ? p.deliverBuilt : carried && !p.deliver ? carried.built : false;
  const facts = tuDeliveryFacts(rows);
  /* The host's box is read for its side effects only (it records the drive command the header control writes with); its markup is no longer drawn. */
  let box = "";
  if (TU_HOST && typeof TU_HOST.deliveryBox === "function"){
    try { box = TU_HOST.deliveryBox({ id: p.id, cmd: dcmd, built: !!dbuilt, name: p.name, needs: personsMoves(p.id).length }, facts) || ""; }
    catch (err){ box = ""; }
  }
  const hostSaid = {};
  /* THE QUESTIONS ARE NOT DRAWN HERE (`linkOnly`): a PRD's interview is answered on that PRD's own page, and this page's
     "Waiting on a person" slot is one card per held-up PRD with the way there (`tuHolds`). */
  const asksHtml = hostAsks("program", p.id, p.id, Object.assign({}, p, { linkOnly: true }), p.name, hostSaid);
  const hostFacts = TU_HOST && typeof TU_HOST.programFacts === "function" ? (() => { try { return TU_HOST.programFacts(p.id) || {}; } catch (err){ return {}; } })() : {};

  const bits = [withdrawnNote(p) || "",
    p.closed ? `closed ${esc(String(p.closed))}` : "",
    p.complete && waivedCuts(p).length ? `${p.closed ? "closed" : "closes"} with ${esc(waivedList(p))} waived` : "",
    ...waitingOn(p).map(esc),
    dispositionFact(p.disposition) || "",
    p.cutCommand ? `a program holds at least two slices &mdash; <code>${esc(p.cutCommand)}</code> cuts another` : ""].filter(Boolean);
  const proof = p.state === "withdrawn" ? ""
    : p.proof.length ? tuProofSaid(p.proof)
    : p.waived ? "proof waived by a written decision" : p.owed ? "" : "no proof named";
  /* THE LAST CYCLE'S HEALTH IS ONLY SAID WHERE IT IS RECORDED: the newest served cycle's own word, or "failed" off the drive document. */
  const newest = Array.isArray(hostFacts.cycles) && hostFacts.cycles.length
    ? hostFacts.cycles.reduce((a, c) => ((Date.parse(c && c.at) || 0) >= (Date.parse(a && a.at) || 0) ? c : a)) : null;
  const health = hostFacts.failed ? "failed" : newest && newest.health ? String(newest.health) : "";
  const last = hostFacts.lastCycle ? `last delivery cycle ${esc(hostFacts.lastCycleHead || hostFacts.lastCycle)}${health ? `, <span class="${hostFacts.failed ? "tu-attn" : "tu-ok"}">${esc(health)}</span>` : ""}` : "";
  const holds = tuHolds(hostFacts);
  TU_HOLDS = holds;
  TU_CLOSING = hostFacts.closing === "ship-escalated";
  const stepsOut = tuProgramSteps(p, rows, facts, holds);
  const shippedN = rows.filter(r => r.state === "shipped").length;
  const shippedSaid = rows.length ? `${shippedN} of ${rows.length} PRD${rows.length === 1 ? "" : "s"} shipped` : "";
  /* A closed program's meta is "closed <day>" (the generated board states no date of its own, so there is no "since"): the waived slices and the proof say the rest on the Building and Closed steps. */
  const facts2 = p.closed ? [proof, shippedSaid, last, `closed ${esc(tuDay(p.closed))}`] : [proof, shippedSaid, last, ...bits];
  const pill = (p.closed ? `<span class="tu-dchip">Closed</span>` : tuDrivenPill(p, true)) + closedToNewWorkChip(p, "tu-chip");
  /* THE TAB COUNTS THE CYCLES THAT HAVE RUN (the drive document's count): the log may serve fewer of them in full, and a tab that
     said 0 over 26 cycles contradicted the line under it. */
  const nCycles = Math.max(Array.isArray(hostFacts.cycles) ? hostFacts.cycles.length : 0, Number(hostFacts.cycleCount) || 0);
  /* THE BADGE COUNTS WHAT THE TIMELINE LISTS: the item pages' folded events (`tuItemProgramActivityCount`), not the raw ones. */
  const actEvents = Array.isArray(hostFacts.activity) ? hostFacts.activity : [];
  const nAct = typeof tuItemProgramActivityCount === "function"
    ? tuItemProgramActivityCount(actEvents.map(r => Object.assign({}, r, { moved: r.moved ? tuTextOf(r.moved) : "" })), { readAt: String(hostFacts.readAt || ""), viewer: String(hostFacts.viewer || "") }) : actEvents.length;
  const decs = Array.isArray(hostFacts.decisions) ? hostFacts.decisions : [];
  const header = `<div class="tu-crumbs2">${link("board", "tu-lnk", "Programs")} &rsaquo; <span class="tu-mono">${esc(p.id)}</span></div>
    `;
  /* THE FLEET'S WORK ON A SHAPING OF THIS PROGRAM is the run chip at the end of the meta line and its conversation and Snooze are the
     header's ⋯ menu (the host's shared `tuHeaderMenu`). */
  const work = TU_HOST && typeof TU_HOST.sliceHeader === "function" ? (() => { try { return TU_HOST.sliceHeader("program", id, { title: p.name, about: String(p.desc || "") }) || {}; } catch (err){ return {}; } })() : {};
  const waiting = tuHoldCards(holds, asksHtml) + (hostFacts.closingCard || "");
  /* A QUIET PROGRAM SAYS SO, once both readings are in (the drive document's holds and the questions): a line drawn before them
     would say "nothing waits" over a hold that has not landed. */
  const read = hostFacts.driven != null && Array.isArray(hostFacts.asks);
  /* THE PROGRAM'S OWN QUESTIONS (a shaping interview on it), open and answered, on its own page: the item page's frame and card.
     A child PRD's question stays the compact held-up card above, which leads to that PRD's page. */
  const asked = TU_HOST && typeof TU_HOST.pageQuestions === "function" ? (() => { try { return TU_HOST.pageQuestions("program", id); } catch (err){ return null; } })() : null;
  const slotAsk = asked && asked.open ? tuSlot("Waiting on a person", asked.open) : "";
  /* ONLY WHAT IS OPEN IS ON THE PAGE TOP: the answered sets are in the Decision log tab and nowhere else. */
  const ownDone = asked && Array.isArray(asked.answeredRows) ? asked.answeredRows : [];
  const nDec = decs.length + ownDone.length;
  /* THE MOVES A PERSON OWES ON THIS PROGRAM, drawn: the very set the board's "N to do" counts (`programOwed`). A program nobody has started
     owes one (start it), and the page used to draw no list at all. */
  const owed = withSliceLabels(programOwed(id)).sort((a, b) => ((a.order || 5) - (b.order || 5)));
  const todoStaged = owed.length ? todoStages(p, owed, []) : null;
  const slotTodo = todoStaged ? tuSlot("To do", `<div class="tu-todo" data-todo="${esc(p.id)}">${todoStaged.parts}</div>`) : "";
  const slotWaiting = (waiting.trim() ? tuSlot("Waiting on a person", waiting)
    : read && !slotAsk && !slotTodo ? tuSlot("Waiting on a person", `<div class="tu-slot-empty" data-tu-noask>Nothing waits on a person here.</div>`) : "");
  /* THE TABS ARE THE ITEM PAGES' (Overview, Decision log, Activity) plus the one this page has of its own, Plan, which is drawn only where PRDs
     exist. Slices, PRDs and the Delivery log are not tabs: the slices are the Plan, and a delivery cycle is an Activity row. */
  const page = "program:" + id;
  const ids = ["overview", ...(rows.length ? ["plan"] : []), "decisions", "activity"];
  const tab = tuTabOf(page, "overview", ids);
  const label = { overview: ["Overview", null], plan: ["Plan", rows.length], decisions: ["Decision log", nDec || null], activity: ["Activity", nAct || null] };
  const tabs = tuTabBar(ids.map(v => ({ id: v, label: label[v][0], n: label[v][1], attrs: `data-tu-page="${esc(page)}" data-keep="tu-tab-${v}"` })), tab, "data-tu-tab");
  const pane = tab === "plan" ? `<div class="tu-ph-ppad">${tuPlanTab(p, rows)}</div>`
    : tab === "decisions" ? tuDecisionLog("program", p.id, decs, hostFacts, ownDone)
    : tab === "activity" ? tuActivity(p, hostFacts)
    : tuOverview(p, rows, tuProgramStands(p, rows, facts, holds, hostFacts));
  /* THE DRIVE IS THE SHARED RUN CHIP on the status line (the host's `driveChip`, over the same `fleetWorkLine` the item pages use), not a box of
     its own: "Paused · waiting for you" while a PRD is held up on a person, "Working" while one builds, nothing while nothing runs. */
  const driveChipHtml = TU_HOST && typeof TU_HOST.driveChip === "function"
    ? (() => { try { return TU_HOST.driveChip(id, { holds: holds.length, building: (facts.building || []).length, ready: (facts.ready || []).length, closed: !!p.closed }) || ""; } catch (err){ return ""; } })() : "";
  const headerOut = tuHeader({ crumbs: header, badge: tuBadge("program"), mini: stepsOut.mini, key: p.id, prio: tuPrioChip(p), mode: pill,
    props: tuPlacedLine(dpAreasOfProgram(p.id), "The features its slices and PRDs are placed in; each is edited in its own git row", p.id),
    buttons: [hostSaid.head || ""], menu: work.menu || "", title: esc(p.name), state: stepsOut.state, assigned: tuAssigned(p, "program"),
    facts: facts2, run: work.chip || driveChipHtml, steps: stepsOut.list, ask: slotAsk });
  return `<div class="tu-page tu-item">${headerOut}${tuRunSlot(p.id)}${slotWaiting}${slotTodo}${tabs}<div class="tu-tabpane">${pane}</div></div>`;
}

/* ── a slice's PRDs, as the Items list draws a row ──────────────────────────────────────────────── */
/* WHO THE TRACKER SAYS IS WAITING ON A PERSON, in the Items list's own words, by the issue's position. */
const TU_PERSON_WAIT = { "human-wip": "held by hand", "blocked-decision": "waiting on a decision", "blocked-action": "needs a person's hands",
  "awaiting-merge": "waiting on a merge approval" };
/* THE ITEMS LIST'S "SINCE": how long ago, between two instants the payload states. */
function tuSinceWord(iso, readAt){
  const a = Date.parse(iso || ""), b = Date.parse(readAt || "");
  if (!isFinite(a) || !isFinite(b)) return "";
  const m = Math.floor(Math.max(0, Math.round((b - a) / 1000)) / 60);
  if (m < 1) return "now";
  if (m < 60) return m + "m";
  const h = Math.floor(m / 60);
  return h < 48 ? h + "h " + (m % 60) + "m" : Math.floor(h / 24) + "d " + (h % 24) + "h";
}
/* THE STEP A PRD STANDS ON, in the Items list's words: "Building", "Building › Design". */
function tuStepWhere(doc, fallback){
  const steps = (doc && doc.steps) || [];
  const at = steps.findIndex(x => x.state === "current");
  if (at >= 0 && typeof tuSteps !== "undefined" && tuSteps[at]){
    const sub = steps[at].sub;
    return tuSteps[at].name + (sub && Array.isArray(sub.items) && sub.items[sub.at] ? " › " + sub.items[sub.at] : "");
  }
  if (steps.length && steps[steps.length - 1].state === "done") return "Shipped";
  return fallback;
}
function tuStatusWord(status){
  const w = String(status || "").replace(/-/g, " ");
  return w.charAt(0).toUpperCase() + w.slice(1);
}
/* ONE PRD OF A SLICE: key, title, the kind chip with its step bar, what it is waiting for, who has it, since when. What the
   row says about the PRD's state is the TRACKER'S (the issue behind it, through the host); a PRD no issue carries yet says
   so, and says what the plan says it waits on -- never a "ready" worked out from the plan alone. */
function tuSlicePrdRow(r){
  const issue = TU_HOST && typeof TU_HOST.prdIssue === "function" ? (() => { try { return TU_HOST.prdIssue(r.n); } catch (err){ return null; } })() : null;
  const shipped = r.state === "shipped";
  let doc = null;
  try {
    doc = typeof tuJourneyFromFacts === "function"
      ? tuJourneyFromFacts({ position: shipped ? "done" : issue ? issue.position : "", kind: "prd", state: issue ? issue.state : "" }, [], r.status) : null;
  } catch (err){ doc = null; }
  const where = tuStepWhere(doc, tuStatusWord(r.status));
  const person = issue && TU_PERSON_WAIT[issue.position];
  const wait = shipped ? `<span class="tu-faint tu-sm">shipped</span>`
    : person ? `<span class="tu-st tu-ask">${esc(person)}</span>`
    : issue ? `<span class="tu-sm tu-muted">${esc(issue.state)}</span>`
    : r.blockers.length ? `<span class="tu-sm tu-muted">waits on ${esc(r.blockers.slice(0, 2).join(", "))}${r.blockers.length > 2 ? ` +${r.blockers.length - 2}` : ""}</span>`
    : `<span class="tu-faint tu-sm">no issue yet</span>`;
  const people = issue ? issue.people : [];
  const who = people.length ? esc(people.map(e => typeof tuPersonName === "function" ? tuPersonName(e) : e).join(", ")) : `<span class="tu-faint">nobody</span>`;
  const since = issue && !shipped ? tuSinceWord(issue.since, issue.readAt) : "";
  const badge = typeof tuTypeBadge === "function" ? tuTypeBadge("prd", false) : `<span class="chip">PRD</span>`;
  const rail = doc && typeof tuMiniRail === "function" ? tuMiniRail(doc) : "";
  return link("prd:" + r.n, "tu-tr tu-cols",
    `<span class="tu-id"><span class="tu-idl">${esc(r.n)}</span></span>
    <span><span class="tu-t">${esc(r.title)}</span>${r.isProof ? `<div class="tu-s">the program's composed proof</div>` : ""}</span>
    <span class="tu-ww">${badge}<span class="tu-wl">${rail}<span>${esc(where)}</span></span></span>
    <span class="tu-fams">${wait}</span><span class="tu-sm">${who}</span>
    <span class="tu-age">${esc(since)}</span><span class="tu-chev">&rsaquo;</span>`, ` data-tu-row="${esc(r.n)}"`);
}
/* THE FILTER A LONG LIST EARNS: the shared bar, only from about eight rows. Kept per slice, in memory. */
const TU_PRD_FILTER_FROM = 8;
let TU_PRD_FB = {};
let TU_PRD_FB_ID = "";
function tuPrdFbState(id){
  if (!TU_PRD_FB[id]) TU_PRD_FB[id] = { q: "", sel: { state: [] }, open: null };
  return TU_PRD_FB[id];
}
const TU_PRD_STATES = [["open", "Not shipped yet"], ["shipped", "Shipped"]];
function tuPrdPass(r, st){
  const needle = String(st.q || "").trim().toLowerCase();
  const picked = (st.sel && st.sel.state) || [];
  return (!needle || (r.n + " " + r.title).toLowerCase().indexOf(needle) >= 0)
    && (!picked.length || picked.indexOf(r.state === "shipped" ? "shipped" : "open") >= 0);
}
function tuSlicePrds(s, rows){
  const sorted = rows.slice().sort((a, b) => (a.wave - b.wave) || (b.frees - a.frees));
  const head = `<div class="tu-th tu-cols"><span>PRD</span><span>Title</span><span>What &middot; where</span><span>Waiting for</span><span>Assigned</span><span class="tu-r">Since</span><span></span></div>`;
  if (rows.length < TU_PRD_FILTER_FROM || typeof tuFilterBar !== "function"){
    return `<div class="tu-tbl">${head}${sorted.map(tuSlicePrdRow).join("")}</div>`;
  }
  const st = tuPrdFbState(s.id);
  TU_PRD_FB_ID = s.id;
  const shown = sorted.filter(r => tuPrdPass(r, st));
  const spec = { search: { placeholder: "Search key or title…" },
    dims: [{ key: "state", label: "State", multi: true,
      opts: TU_PRD_STATES.map(o => ({ id: o[0], label: o[1], count: rows.filter(r => (r.state === "shipped" ? "shipped" : "open") === o[0]).length })) }],
    matching: shown.length };
  if (typeof tuFilterBarBind === "function"){
    tuFilterBarBind("slice-prds", { state: () => tuPrdFbState(TU_PRD_FB_ID), spec: () => spec,
      change: () => { render(openRoute()); } });
  }
  return `${tuFilterBar(spec, st, "slice-prds")}${shown.length
    ? `<div class="tu-tbl">${head}${shown.map(tuSlicePrdRow).join("")}</div>` : `<div class="tu-slot-empty">Nothing matches these choices.</div>`}`;
}

/* ── WHAT AN ITEM WAITS ON, WHAT IT UNBLOCKS, AND A SLICE'S PATH TO DONE ──────────────────────────────────────────
 *
 * The owner-approved dependencies mockup (`knowledge/mockups/`, the dependencies page), screens 1 and 2, and the
 * owner's decisions on it: ONE "Waiting on" list joins a PRD's `depends_on` and a tracker `blocked by` link, each row
 * tagged with where its edge is written (D1); a slice's `Depends on` is shown dashed and grey as "Comes after · order
 * only", never as a wait (D2).
 *
 * ONE GRAPH, TWO KINDS OF EDGE THAT HOLD START, BOTH ALREADY SERVED:
 *   a PRD's `depends_on`   the board payload's `dep` on each PRD row: a PRD number, or a tracker key (whose state is
 *                          `/api/prd-chain/{n}`'s, through `prereqs`, when the board does not hold the issue);
 *   a tracker `blocked by` the backlog's `blockedBy` on each board entry (the host's `depEntries`), inverted here once
 *                          for "Unblocks".
 * A PRD and the tracker issue that carries it (`entry.prd`) are ONE node, so an edge written on either side lands on
 * the same item. A slice's `Depends on` is NOT in this graph: since ENG-10638 it orders and never holds start.
 *
 * THE CRITICAL PATH IS COMPUTED, NEVER STORED, by the dispatcher's own rule: the longest chain of open, start-holding
 * edges (`dispatch/ranking.py`'s `_depths`, the upward rank `routing._critical_path_depth` sorts by as key 6 of
 * `priority_key`, over the same two edge kinds). A slice's path is the longest such chain ending at its open proof
 * (else at its deepest open PRD); a tie goes to the link that frees most (key 7, the transitive unlock count, which
 * `dpFrees` counts the way `ranking._reachable` does). Work outside the slice that holds a step is drawn in the step it
 * stands on, dashed, with its area.
 *
 * WHERE AN ITEM SITS is `areaview.place`'s answer, read through the host (`areaIndex`, the served `GET /api/areas`),
 * with the slice's own `area` as the fallback for a PRD. An area nothing names is no tag at all, never a guess.
 *
 * NOTHING HERE WRITES, and nothing on a program page changes: legacy programs keep their page and its order of work.
 */
const DP_DONE_PRD = ["shipped", "cancelled"];
const DP_KEY = /^[A-Z][A-Z0-9]*-\d+$/;
const DP_SETTLED = ["completed", "canceled"];
function dpCall(name){
  if (!TU_HOST || typeof TU_HOST[name] !== "function") return null;
  const args = Array.prototype.slice.call(arguments, 1);
  try { return TU_HOST[name].apply(null, args); } catch (err){ return null; }
}
/* THE HOST'S BOARD ENTRIES: `{ list, readAt }`, every open tracker issue of this repository the backlog carries. */
function dpEntries(){
  const got = dpCall("depEntries");
  return got && Array.isArray(got.list) ? got : { list: [], readAt: "" };
}
let DP_MEMO = { d: null, list: null, chain: null, g: null };
/* THE GRAPH, built once per board payload and per backlog reading. */
function dpG(){
  const got = dpEntries();
  /* WHAT THE CHAIN READS SAID about each tracker key a PRD's `depends_on` names: a read landing changes a key's state. */
  const chainSig = PREREQS ? Object.values(PRD).filter(r => (r.dep || []).some(d => DP_KEY.test(String(d)))).map(r => {
    const said = prereqsOf(r.n);
    return r.n + ":" + ((said && said.prerequisites) || []).map(o => o.ref + (o.built ? "+" : "-")).join(",");
  }).join("|") : "";
  if (DP_MEMO.d === D && DP_MEMO.list === got.list && DP_MEMO.chain === chainSig && DP_MEMO.g) return DP_MEMO.g;
  DP_MEMO = { d: D, list: got.list, chain: chainSig, g: dpBuild(got.list, got.readAt) };
  return DP_MEMO.g;
}
function dpBuild(entries, readAt){
  const nodes = {}, up = {}, down = {}, via = {}, byKey = {};
  const add = (id, n) => { if (!nodes[id]){ nodes[id] = n; up[id] = new Set(); down[id] = new Set(); } return nodes[id]; };
  Object.values(PRD).forEach(r => {
    if (r.status === "cancelled") return;
    add("prd:" + r.n, { id: "prd:" + r.n, kind: "prd", n: String(r.n), key: "", x: r, entry: null, open: !DP_DONE_PRD.includes(r.status),
      slice: String(r.slice || ""), title: String(r.title || "") });
  });
  entries.forEach(e => {
    const key = String((e && e.identifier) || "");
    if (!key || byKey[key]) return;
    const prd = e.prd ? "prd:" + e.prd : "";
    if (prd && nodes[prd]){
      byKey[key] = prd;
      nodes[prd].entry = e;
      nodes[prd].key = key;
      return;
    }
    byKey[key] = key;
    add(key, { id: key, kind: String(e.kind || "issue").toLowerCase(), key: key, entry: e, open: true, slice: "", title: String(e.title || "") });
  });
  /* A KEY THE BOARD DOES NOT HOLD is known only through the edge that names it: its `stateType` says whether it is settled. */
  const ref = (k, b) => {
    if (byKey[k]) return byKey[k];
    byKey[k] = k;
    const settled = b ? (b.built === true || DP_SETTLED.includes(String(b.stateType || ""))) : true;
    add(k, { id: k, kind: String((b && b.type) || "issue").toLowerCase(), key: k, entry: null, open: !settled, slice: "",
      title: String((b && b.title) || ""), state: String((b && b.state) || (b ? "" : "not on the board")) });
    return k;
  };
  const edge = (from, to, how) => {
    if (!nodes[from] || !nodes[to] || from === to) return;
    up[from].add(to);
    down[to].add(from);
    (via[from + ">" + to] = via[from + ">" + to] || new Set()).add(how);
  };
  Object.values(PRD).forEach(r => {
    if (!nodes["prd:" + r.n]) return;
    /* ASKED ONLY OF A PRD THAT NAMES A TRACKER KEY: the host answers `prereqs` with a read per PRD. */
    const info = {};
    if ((r.dep || []).some(d => DP_KEY.test(String(d)))){
      const said = prereqsOf(r.n);
      ((said && said.prerequisites) || []).forEach(o => { info[o.ref] = o; });
    }
    (r.dep || []).forEach(d => {
      const s = String(d);
      if (DP_KEY.test(s)) edge("prd:" + r.n, ref(s, info[s] || null), "dep");
      else if (nodes["prd:" + s]) edge("prd:" + r.n, "prd:" + s, "dep");
    });
  });
  entries.forEach(e => {
    const from = byKey[String((e && e.identifier) || "")];
    (Array.isArray(e && e.blockedBy) ? e.blockedBy : []).forEach(b => { if (b && b.key) edge(from, ref(String(b.key), b), "tracker"); });
  });
  return { nodes, up, down, via, byKey, readAt: String(readAt || ""), lv: null, fr: {} };
}
const dpOpenUp = (g, id) => [...(g.up[id] || [])].filter(x => g.nodes[x] && g.nodes[x].open);
const dpOpenDown = (g, id) => [...(g.down[id] || [])].filter(x => g.nodes[x] && g.nodes[x].open);
/* THE STEP AN OPEN ITEM STANDS ON: nothing open before it is 0, else one past the deepest open thing it waits on. A loop
   contributes no depth (`ranking._depths`' own guard). */
function dpLevels(g){
  if (g.lv) return g.lv;
  const lv = {}, stack = new Set();
  const walk = id => {
    if (lv[id] !== undefined) return lv[id];
    if (stack.has(id)) return 0;
    stack.add(id);
    let best = 0;
    dpOpenUp(g, id).forEach(p => { best = Math.max(best, 1 + walk(p)); });
    stack.delete(id);
    lv[id] = best;
    return best;
  };
  Object.keys(g.nodes).forEach(id => { if (g.nodes[id].open) walk(id); });
  g.lv = lv;
  return lv;
}
/* HOW MANY OPEN ITEMS FINISHING THIS RELEASES, directly or down the chain: the dispatcher's unlock count when the
   backlog carries the ranked key for it (`ranking.keyed.blastRadius`, negated on the wire), else the same count over this
   graph. */
function dpFrees(g, id){
  if (g.fr[id] !== undefined) return g.fr[id];
  const n = g.nodes[id];
  const keyed = n && n.entry && n.entry.ranking && n.entry.ranking.keyed;
  let out;
  if (keyed && typeof keyed.blastRadius === "number") out = Math.abs(keyed.blastRadius);
  else {
    const seen = new Set(), stack = dpOpenDown(g, id);
    while (stack.length){
      const x = stack.pop();
      if (seen.has(x) || x === id) continue;
      seen.add(x);
      dpOpenDown(g, x).forEach(y => stack.push(y));
    }
    out = seen.size;
  }
  g.fr[id] = out;
  return out;
}
/* THE AREA AN ITEM IS PLACED IN, `{ slug, name }` or null: `areaview.place`'s answer, a PRD falling back to its slice's. */
function dpAreaOf(n){
  if (!n) return null;
  const idx = dpCall("areaIndex") || null;
  const named = slug => slug ? { slug: String(slug), name: String((idx && idx.names && idx.names[slug]) || slug) } : null;
  if (n.kind === "slice"){
    const s = SL[n.sid];
    return named((idx && idx.slice && idx.slice[n.sid]) || (s && s.area) || "");
  }
  if (n.kind === "prd"){
    const s = SL[n.slice];
    return named((idx && idx.prd && idx.prd[n.n]) || (idx && idx.slice && idx.slice[n.slice]) || (s && s.area) || "");
  }
  return named((idx && idx.issue && idx.issue[n.key]) || "");
}
/* THE AREAS A PROGRAM TOUCHES, `[{ slug, name }]` (`areaview.place`'s `programs` per area), or null while the placement has not been read. */
function dpAreasOfProgram(id){
  const idx = dpCall("areaIndex") || null;
  if (!idx) return null;
  return ((idx.program && idx.program[id]) || []).map(slug => ({ slug: String(slug), name: String((idx.names && idx.names[slug]) || slug) }));
}
/* THE HEADER'S PROPERTIES LINE FOR A SLICE OR A PROGRAM: Feature only, read-only (`tuPlacedProps`, the item pages' line renderer). */
function tuPlacedLine(areas, why, key){
  if ((areas == null && !key) || typeof tuPlacedProps !== "function") return "";
  return tuPlacedProps(areas == null ? null : areas.map(a => ({ area: a.slug, name: a.name })), why, key);
}
const dpSameArea = (a, b) => !!(a && b && a.slug === b.slug);
/* AN ITEM AS A READER NAMES IT: "PRD 0915" or its key, its route and the words for where it stands. */
function dpName(n){ return n.kind === "prd" ? "PRD " + n.n : n.key; }
function dpShort(n){ return n.kind === "prd" ? n.n : n.key; }
function dpRoute(n){ return n.kind === "prd" ? "prd:" + n.n : "issue:" + n.key; }
const DP_PERSON = { "blocked-decision": "a decision", "blocked-action": "an action", "awaiting-merge": "a merge", "human-wip": "held by hand" };
function dpPerson(n){
  const e = n && n.entry;
  if (!e) return "";
  if (e.needsYou === true || DP_PERSON[e.position]) return DP_PERSON[e.position] || "a person";
  return "";
}
function dpState(n){
  if (n.kind === "prd"){
    if (n.x && n.x.status === "shipped") return "Shipped";
    if (n.entry && n.entry.state) return String(n.entry.state);
    return "Not started";
  }
  if (n.entry && n.entry.state) return String(n.entry.state);
  if (n.state) return n.state;
  return n.open ? "open" : STEP_DONE;
}
function dpKindWord(n){
  if (n.kind === "prd") return "PRD";
  const k = String(n.kind || "issue").replace(/-/g, " ");
  return k === "issue" ? "" : k;
}
/* "3d", "5h", "12m": how long between two instants the page was handed, in the board's compact units (an elapsed
   MEASUREMENT, never a sentence that reads as a plan — `tuSinceWord`'s rule). */
function dpAgo(iso, readAt){
  const a = Date.parse(iso || ""), b = Date.parse(readAt || "");
  if (!isFinite(a) || !isFinite(b)) return "";
  const m = Math.max(0, Math.round((b - a) / 60000));
  if (m < 60) return m + "m";
  const h = Math.floor(m / 60);
  return h < 48 ? h + "h" : Math.floor(h / 24) + "d";
}

/* ── the critical path of a slice ─────────────────────────────────────────────────────────────── */

/* EVERYTHING A SLICE'S PATH IS DRAWN FROM: its own PRDs, the open things outside it that hold one of them, the steps and
   the longest chain. Computed on every paint from the graph above, never written anywhere. */
function dpSlicePath(sid){
  const g = dpG();
  const s = SL[sid];
  if (!s) return null;
  if (!g.paths) g.paths = {};
  if (g.paths[sid]) return g.paths[sid];
  const own = Object.values(g.nodes).filter(n => n.kind === "prd" && n.slice === sid).map(n => n.id).sort();
  const mine = new Set(own);
  const open = own.filter(id => g.nodes[id].open);
  const lv = dpLevels(g);
  const outside = [];
  open.forEach(id => dpOpenUp(g, id).forEach(p => { if (!mine.has(p) && outside.indexOf(p) < 0) outside.push(p); }));
  const proof = (s.proof || []).map(x => "prd:" + x).filter(id => mine.has(id) && g.nodes[id].open);
  const rank = (a, b) => (lv[b] - lv[a]) || (dpFrees(g, b) - dpFrees(g, a)) || (a < b ? -1 : a > b ? 1 : 0);
  const target = proof.slice().sort(rank)[0] || open.slice().sort(rank)[0] || "";
  const chain = [];
  const seen = new Set();
  let at = target;
  while (at && !seen.has(at)){
    seen.add(at);
    chain.unshift(at);
    at = dpOpenUp(g, at).sort(rank)[0] || "";
  }
  const later = [];
  open.forEach(id => dpOpenDown(g, id).forEach(x => { if (!mine.has(x) && later.indexOf(x) < 0) later.push(x); }));
  g.paths[sid] = { g, s, own, open, shipped: own.filter(id => !g.nodes[id].open), outside, proof, chain, later, lv };
  return g.paths[sid];
}
/* WHO A PARK IS ASKED OF, in the host's words for an actor (a run stamp reads "Fleet", an address the person's name);
   the standalone board has no host and prints what it was handed. */
/* THE PEOPLE AN ITEM IS ASSIGNED TO (addresses), from its entry's `assignees`: assignment is the only who. An item nobody
   is assigned to names nobody; its own reason text says what it waits on. */
function dpAssignees(e){
  return e && Array.isArray(e.assignees) ? e.assignees.map(x => String(x || "").trim()).filter(x => x.indexOf("@") >= 0) : [];
}
function dpAssignedWords(e){
  const who = dpAssignees(e);
  return who.length ? " &middot; asked of " + who.map(w => esc(dpWho(w))).join(", ") : "";
}
function dpWho(x){ return typeof tuActorWords === "function" ? tuActorWords(x) : String(x == null ? "" : x); }
/* A SLICE'S CHAIN AND OUTSIDE HOLDERS AS THE IDS A READER KNOWS, for the render tests. */
function dpSlicePathIds(sid){
  const p = dpSlicePath(sid);
  return p ? { chain: p.chain.map(id => dpShort(p.g.nodes[id])), outside: p.outside.map(id => dpShort(p.g.nodes[id])) } : null;
}
/* THE SLICE WHOSE CRITICAL PATH THIS ITEM IS ON, as `{ sid, chain }`, or null. A task or a bug has no slice of its own,
   so it is never told it is on one. */
function dpOnPath(g, id){
  const n = g.nodes[id];
  if (!n || n.kind !== "prd" || !n.slice || !n.open) return null;
  const p = dpSlicePath(n.slice);
  return p && p.chain.indexOf(id) >= 0 && p.chain.length > 1 ? { sid: n.slice, chain: p.chain } : null;
}
function dpChainHtml(g, chain){
  return chain.map(id => link(dpRoute(g.nodes[id]), "tu-lnk tu-mono", esc(dpShort(g.nodes[id])))).join(" &rarr; ");
}

/* ── the item block: Waiting on / Unblocks / Comes after ──────────────────────────────────────── */

const DP_TAG = { dep: ["depends_on", "where-file"], tracker: ["blocked by", "where-tracker"] };
function dpWhereTags(set){
  return [...(set || [])].sort().map(how => DP_TAG[how] ? `<span class="tu-dp-wh tu-dp-${DP_TAG[how][1]}" title="${
    how === "dep" ? "Written in the PRD file's depends_on" : "A blocked-by link in the tracker"}">${esc(DP_TAG[how][0])}</span>` : "").join("");
}
function dpAreaTag(area){
  return area ? `<span class="tu-dp-area" title="In another feature">${esc(area.name)}</span>` : "";
}
function dpStatePill(n){
  const person = n.open ? dpPerson(n) : "";
  if (person) return `<span class="tu-dp-st ask">Waiting on a person</span>`;
  return `<span class="tu-dp-st${n.open ? "" : " done"}">${esc(dpState(n))}</span>`;
}
/* ONE ROW: what it is, its title, the area tag when it sits in another area, where the edge is written, its state; and
   under it the line that says how it relates to this item. `dir` is "up" (this waits on it) or "down" (it waits on this). */
function dpRow(g, selfId, id, dir, cp, opt){
  const n = g.nodes[id], self = g.nodes[selfId];
  const area = dpAreaOf(n), mine = dpAreaOf(self);
  const other = area && mine && !dpSameArea(area, mine) ? area : null;
  const how = dir === "up" ? g.via[selfId + ">" + id] : g.via[id + ">" + selfId];
  const bits = [];
  if (n.kind === "prd" && self.kind === "prd" && n.slice && n.slice === self.slice) bits.push("same slice");
  else if (n.kind === "prd" && n.slice) bits.push("slice " + link("slice:" + n.slice, "tu-lnk tu-mono", esc(n.slice)));
  else if (n.kind !== "prd" && dpKindWord(n)) bits.push(esc(dpKindWord(n)));
  if (other) bits.push("feature " + esc(other.name));
  else if (area && mine && n.kind !== "prd") bits.push("same feature");
  const person = n.open ? dpPerson(n) : "";
  const e = n.entry;
  const ago = e && e.since ? dpAgo(e.since, g.readAt) : "";
  if (person) bits.push(`${ago ? "parked " + esc(ago) + " &middot; " : ""}${esc(person)}${dpAssignedWords(e)}`);
  else if (n.open && ago && e) bits.push("since " + esc(ago));
  /* ON A SLICE'S LONGEST CHAIN: this item's own slice says so bare; another slice's names it. */
  const onPath = cp && cp.chain.indexOf(id) >= 0 ? cp : dpOnPath(g, id);
  if (onPath) bits.push(`<span class="tu-dp-cp">Critical path${cp && onPath.sid === cp.sid ? "" : " of " + esc(onPath.sid)}</span>`);
  if (dir === "down" && n.open){
    const more = dpFrees(g, id);
    if (more) bits.push(`frees ${more} more after it`);
  }
  const answer = person ? link(dpRoute(n), "tu-dp-ans", "Answer it") : "";
  const up = dir === "up" ? dpUpExtras(g, selfId, id, n, self, opt || {}) : { bits: [], chip: "", rm: "", tail: "" };
  up.bits.forEach(b => bits.push(b));
  return `<div class="tu-dp-row tu-dp-${dir}${n.open ? "" : " tu-dp-isdone tu-dp-stale"}${other ? " tu-dp-foreign" : ""}" data-dp-edge="${esc(dpShort(n))}">` +
    `<span class="tu-dp-glyph" aria-hidden="true">${ICON[dir === "up" ? "blockedBy" : "blocking"]}</span>` +
    `<div class="tu-dp-main"><div class="tu-dp-l1">${link(dpRoute(n), "tu-dp-id", (n.kind === "prd" ? "PRD " : "") + `<b>${esc(dpShort(n))}</b>`)}` +
    `<span class="tu-dp-t">${esc(n.title || (n.kind === "prd" ? "" : "a tracker issue"))}</span>${dpAreaTag(other)}` +
    `<span class="tu-dp-whs">${dpWhereTags(how)}</span>${up.chip}${dpStatePill(n)}</div>` +
    `${bits.length || answer || up.rm ? `<div class="tu-dp-l2">${bits.join(" &middot; ")}${answer}${up.rm}</div>` : ""}${up.tail}</div></div>`;
}
/* WHICH CHAINS ARE OPEN, kept across the page's repaints (a repaint rebuilds the markup): `tuDepsToggle` flips one. */
const DP_OPEN = new Set();
function tuDepsToggle(id){
  const k = String(id);
  if (DP_OPEN.has(k)) DP_OPEN.delete(k); else DP_OPEN.add(k);
  return DP_OPEN.has(k);
}
const dpByName = g => (a, b) => (dpShort(g.nodes[a]) < dpShort(g.nodes[b]) ? -1 : 1);
/* THE FIRST THING TO ACT ON among `ids`: one whose chain reaches a person (that is where the work stops), then by name. */
function dpPick(g, ids){
  const memo = {};
  const reaches = (x, stack) => {
    if (memo[x] !== undefined) return memo[x];
    if (stack.has(x)) return false;
    stack.add(x);
    const r = !!dpPerson(g.nodes[x]) || dpOpenUp(g, x).some(y => reaches(y, stack));
    stack.delete(x);
    memo[x] = r;
    return r;
  };
  const rank = x => (reaches(x, new Set()) ? 0 : 1);
  return ids.slice().sort((a, b) => (rank(a) - rank(b)) || dpByName(g)(a, b))[0] || "";
}
/* FROM A BLOCKER DOWN TO THE ROOT OF ITS WAIT: [the blocker, what it waits on, ..., the root]. A loop ends the walk. */
function dpWalk(g, start, from){
  const chain = [], seen = new Set([from]);
  let at = start;
  while (at && !seen.has(at)){
    seen.add(at);
    chain.push(at);
    at = dpPick(g, dpOpenUp(g, at).filter(x => !seen.has(x)));
  }
  return chain;
}
/* WHAT THE ITEM AT THE END OF A CHAIN NEEDS, in words: a person ("you" when it is the reader), else where it stands. */
function dpRootWords(n){
  if (dpPerson(n)){
    const who = dpAssignees(n.entry);
    if (!who.length) return "needs a person";
    const me = RZ_VIEWER ? RZ_VIEWER.toLowerCase() : "";
    return me && who.some(w => w.toLowerCase() === me) ? "needs you" : "needs " + dpWho(who[0]);
  }
  const e = n.entry;
  if (e && Array.isArray(e.reasons) && e.reasons.some(r => r && r.code === "running")) return "is being worked on now";
  return "is " + dpState(n);
}
/* WHAT ONLY AN "UP" ROW CARRIES: who holds the blocker, the repository when it is not this page's, what it is itself blocked by
   with the chain (Show chain), and, on a done blocker, the stale link and the one control that removes it. */
function dpUpExtras(g, selfId, id, n, self, opt){
  const bits = [], e = n.entry;
  let chip = "", rm = "", tail = "";
  const lane = e && e.lane ? String(e.lane) : "", mine = self.entry && self.entry.lane ? String(self.entry.lane) : "";
  if (lane && mine && lane !== mine) chip = `<span class="tu-dp-repo" title="In another repository">${esc(lane)}</span>`;
  if (n.open && e){
    const reasons = Array.isArray(e.reasons) ? e.reasons : [];
    const holder = String(e.holdTaker || "");
    if (reasons.some(r => r && r.code === "running")) bits.push("running now");
    else if (holder) bits.push("held by " + esc(dpWho(holder)));
    if (reasons.some(r => r && /stall|stuck/.test(String(r.code || "")))) bits.push(`<span class="tu-attn">stalled</span>`);
  }
  if (!n.open){
    bits.push("done &mdash; it no longer holds anything back");
    const mineKey = self.entry ? String(self.entry.identifier || "") : "";
    const named = self.entry && Array.isArray(self.entry.blockedBy) ? self.entry.blockedBy.find(b => b && b.key && g.byKey[String(b.key)] === id) : null;
    const edge = g.via[selfId + ">" + id];
    if (mineKey && named && edge && edge.has("tracker")){
      rm = ` <button type="button" class="tu-dp-rm" data-dp-unlink="${esc(String(named.key))}" data-dp-from="${esc(mineKey)}">Remove the link</button>`;
    } else bits.push(`<span class="tu-faint">written in the PRD file</span>`);
  }
  const ups = n.open ? dpOpenUp(g, id) : [];
  if (ups.length) bits.push(`itself blocked by ${ups.length}`);
  const seen = new Set(opt.seen || [selfId]);
  seen.add(id);
  const kids = ups.filter(x => !seen.has(x));
  if (kids.length && (opt.depth || 0) < 8){
    const open = DP_OPEN.has(id);
    tail = `<button type="button" class="tu-dp-chainb" data-dp-chain="${esc(id)}" aria-expanded="${open}">${open ? "Hide chain" : "Show chain"}</button>` +
      `<div class="tu-dp-chain"${open ? "" : " hidden"}>${kids.sort(dpByName(g)).map(k => dpRow(g, id, k, "up", null, { depth: (opt.depth || 0) + 1, seen: new Set(seen) })).join("")}</div>`;
  }
  return { bits, chip, rm, tail };
}
/* THE ONE HINT LINE A COCKPIT ROW CARRIES for a blocked item: "waits on KEY (State) · root KEY needs you". "" when nothing open holds it. */
function tuDepHint(key, alt){
  try {
    const g = dpG();
    const id = g.byKey[String(key || "")] || g.byKey[String(alt || "")] || "";
    const n = id ? g.nodes[id] : null;
    if (!n || !n.open) return "";
    const ups = dpOpenUp(g, id);
    if (!ups.length) return "";
    const first = dpPick(g, ups);
    const chain = dpWalk(g, first, id);
    const root = chain[chain.length - 1];
    let said = `waits on ${dpShort(g.nodes[first])} (${dpState(g.nodes[first])})`;
    if (root !== first || dpPerson(g.nodes[root])) said += ` · root ${dpShort(g.nodes[root])} ${dpRootWords(g.nodes[root])}`;
    return said;
  } catch (_e){ return ""; }
}
function dpHead(title, count, lead){
  return `<div class="tu-dp-h"><h3 class="tu-h3">${title}</h3>${count ? `<span class="tu-dp-n">${count}</span>` : ""}${lead ? `<span class="tu-dp-lead">${lead}</span>` : ""}</div>`;
}
/* THE ITEM'S OWN WAIT ON A PERSON, as the first row of Waiting on: a parked bug holds everything below it. */
function dpParkRow(park, readAt){
  const ago = park.since ? dpAgo(park.since, readAt) : "";
  const kind = park.kind ? String(park.kind) : "a person";
  return `<div class="tu-dp-row tu-dp-up tu-dp-person" data-dp-edge="person"><span class="tu-dp-glyph" aria-hidden="true">${ICON.blockedBy}</span>` +
    `<div class="tu-dp-main"><div class="tu-dp-l1"><span class="tu-dp-id"><b>${esc(kind.charAt(0).toUpperCase() + kind.slice(1))}</b></span>` +
    `<span class="tu-dp-t">${esc(park.q || "")}</span><span class="tu-dp-whs"><span class="tu-dp-wh tu-dp-where-park">park</span></span>` +
    `<span class="tu-dp-st ask">Waiting on a person</span></div>` +
    `<div class="tu-dp-l2">${dpAssignees(park).length ? "asked of " + dpAssignees(park).map(w => esc(dpWho(w))).join(", ") : esc(park.reason || "a person answers it")}${ago ? " &middot; parked " + esc(ago) : ""}${
      park.answer ? park.answer : ""}</div></div></div>`;
}
/* THE BLOCK. `o` = { key, prd, park? }: the tracker key the page is about, the PRD number when it is a PRD, and the
   item's own person wait when it has one ({ kind, q, assignees, reason, since, answer }). Returns `{ html, waits, unblocks, area }`:
   the counts are the header's meta line, and `area` its "in area". One line, not a block, when there is nothing. */
function tuDepsBlock(o){
  const x = o || {};
  const g = dpG();
  const id = x.prd && g.nodes["prd:" + x.prd] ? "prd:" + x.prd : (g.byKey[String(x.key || "")] || "");
  const self = id ? g.nodes[id] : null;
  const area = self ? dpAreaOf(self) : null;
  const ups = self ? [...g.up[id]] : [];
  const downs = self ? dpOpenDown(g, id) : [];
  const openUps = ups.filter(u => g.nodes[u].open);
  const doneUps = ups.filter(u => !g.nodes[u].open);
  const s = self && self.kind === "prd" && self.slice ? SL[self.slice] : null;
  const after = s ? (s.dep || []).filter(d => SL[d] || d) : [];
  const park = x.park || null;
  /* THE COUNT IS ISSUES, NEVER THE PARK: an item parked on a person has no blocker issue, and "waits on 1" would invent one. */
  const waits = openUps.length;
  const held = openUps.length + (park ? 1 : 0);
  if (!openUps.length && !doneUps.length && !downs.length && !after.length && !park){
    return { html: `<p class="tu-dp-none" data-dp-none>Nothing is in the way, and nothing waits on this.</p>`, waits: 0, unblocks: 0, area, park: false, has: false };
  }
  const cp = self ? dpOnPath(g, id) : null;
  const byName = dpByName(g);
  const parts = [];
  /* ACT ON THIS FIRST: the first thing in the way that needs action, named at the end of its chain. */
  if (openUps.length){
    const first = dpPick(g, openUps);
    const chain = dpWalk(g, first, id);
    const root = g.nodes[chain[chain.length - 1]];
    const others = held - 1;
    parts.push(`<p class="tu-dp-act" data-dp-act>This waits on ${chain.map(c => link(dpRoute(g.nodes[c]), "tu-lnk tu-mono", esc(dpShort(g.nodes[c])))).join(" &larr; ")}, which ${esc(dpRootWords(root))}. ${
      others > 0 ? `${others} other thing${others === 1 ? " is" : "s are"} also in the way${park ? " (one is a person)" : ""}.` : "Nothing else is in the way."}</p>`);
  } else if (park){
    parts.push(`<p class="tu-dp-act" data-dp-act>This waits on a person${park.q ? ": " + esc(String(park.q).replace(/[.\s]+$/, "")) : ""}. Nothing else is in the way.</p>`);
  } else {
    parts.push(`<p class="tu-dp-act" data-dp-act>Nothing is in the way now.${doneUps.length ? " The links below are to work that is already done." : ""}</p>`);
  }
  if (cp){
    parts.push(`<p class="tu-dp-cpline" data-dp-critical><span class="tu-dp-cp">Critical path</span> This ${self.kind === "prd" ? "PRD" : "item"} is on the longest chain to finishing ${
      link("slice:" + cp.sid, "tu-lnk tu-mono", esc(cp.sid))}: ${dpChainHtml(g, cp.chain)} <span class="tu-faint">&middot; ${cp.chain.length} step${cp.chain.length === 1 ? "" : "s"} left</span></p>`);
  }
  if (openUps.length || doneUps.length || park){
    const lead = held ? `Fleet will not start this until ${held === 1 ? "it is" : "these are"} done.` : "Everything it waited on is done.";
    const count = [held ? `${held} open` : "", doneUps.length ? `${doneUps.length} done` : ""].filter(Boolean).join(" &middot; ");
    const rows = (park ? dpParkRow(park, g.readAt) : "") + openUps.sort(byName).map(u => dpRow(g, id, u, "up", cp)).join("") +
      doneUps.sort(byName).map(u => dpRow(g, id, u, "up", cp)).join("");
    parts.push(`<section class="tu-dp-sec" data-dp="waiting">${dpHead(park && !openUps.length && !doneUps.length ? "Waiting on <span class=\"tu-dp-who\">a person</span>" : "Waiting on", count, lead)}${rows}</section>`);
  }
  if (downs.length){
    const total = dpFrees(g, id);
    const foreign = area && downs.every(d => { const a = dpAreaOf(g.nodes[d]); return a && !dpSameArea(a, area); });
    const lead = foreign ? "Every one of them is in another feature." : `These can start when this ${self.kind === "prd" ? "ships" : "is done"}.`;
    const count = `${downs.length} wait${downs.length === 1 ? "s" : ""} on this${total > downs.length ? ` &middot; frees ${total} in total` : ""}`;
    parts.push(`<section class="tu-dp-sec" data-dp="unblocks">${dpHead("Unblocks", count, lead)}${downs.sort(byName).map(d => dpRow(g, id, d, "down", cp)).join("")}</section>`);
  }
  if (after.length){
    const rows = after.map(d => {
      const t = SL[d];
      const done = !!(t && !openSlice(t));
      return `<div class="tu-dp-row tu-dp-order${done ? " tu-dp-isdone" : ""}" data-dp-edge="${esc(d)}"><span class="tu-dp-glyph" aria-hidden="true"></span>` +
        `<div class="tu-dp-main"><div class="tu-dp-l1">${t ? link("slice:" + d, "tu-dp-id", `<b>${esc(d)}</b>`) : `<span class="tu-dp-id"><b>${esc(d)}</b></span>`}` +
        `<span class="tu-dp-t">${esc(t ? t.name : "")}</span><span class="tu-dp-whs"><span class="tu-dp-wh tu-dp-where-order">Depends on</span></span>` +
        `<span class="tu-dp-st${done ? " done" : ""}">${esc(t ? (done ? STEP_DONE : tuStatusWord(t.state)) : "not on the plan")}</span></div></div></div>`;
    }).join("");
    parts.push(`<section class="tu-dp-sec tu-dp-after" data-dp="after">${dpHead("Comes after", `${after.length} slice${after.length === 1 ? "" : "s"} &middot; order only`,
      `${esc(s.id)} is ordered after ${after.length === 1 ? "this slice" : "these slices"} in the plan. It does not hold start.`)}${rows}</section>`);
  }
  const legend = `<p class="tu-dp-legend"><span class="tu-dp-lg up">${ICON.blockedBy} holds start</span><span class="tu-dp-lg down">${ICON.blocking} this holds start for it</span>` +
    `<span class="tu-dp-lg order">order only</span><span class="tu-dp-area">Feature</span> in another feature</p>`;
  return { html: `<div class="tu-dp" data-dp-block>${parts.join("")}${legend}</div>`, waits: waits, unblocks: downs.length, area, park: !!park, has: true };
}

/* ── a slice's path to done ───────────────────────────────────────────────────────────────────── */

function dpChip(g, id, cpSet, foreignTo){
  const n = g.nodes[id];
  const area = dpAreaOf(n);
  const outside = !!foreignTo;
  const person = n.open ? dpPerson(n) : "";
  const waits = n.open ? dpOpenUp(g, id).map(u => dpShort(g.nodes[u])).sort() : [];
  const frees = n.open ? dpFrees(g, id) : 0;
  const bits = [];
  if (outside && area) bits.push(dpAreaTag(area));
  if (person) bits.push(`<span class="tu-dp-st ask">a person</span>`);
  else if (n.open && n.entry && n.entry.state) bits.push(`<span class="tu-dp-st">${esc(n.entry.state)}</span>`);
  if (waits.length) bits.push(`<span class="tu-faint">waits on ${esc(waits.join(", "))}</span>`);
  if (frees >= 2) bits.push(`<em>frees ${frees}</em>`);
  const proof = foreignTo === null && n.kind === "prd" && SL[n.slice] && (SL[n.slice].proof || []).indexOf(n.n) >= 0 ? " (proof)" : "";
  return link(dpRoute(n), `tu-dp-chip${cpSet.has(id) ? " cp" : ""}${outside ? " out" : ""}${n.open ? "" : " done"}`,
    `<b>${esc(dpShort(n))}</b><span class="tu-dp-ct">${esc((n.title || "") + proof)}</span>${bits.join("")}`, ` data-dp-node="${esc(dpShort(n))}"`);
}
/* THE SECTION: the critical path line, then Shipped, Now, Then 1, Then 2 … and the Proof last; then what outside the slice
   holds a step, what outside it waits on it, and its own `Depends on` as one dashed line. "" for a slice with no PRDs. */
function tuSlicePath(sid){
  const p = dpSlicePath(sid);
  if (!p || !p.own.length) return "";
  const g = p.g, lv = p.lv;
  const cpSet = new Set(p.chain.length > 1 ? p.chain : []);
  const rank = (a, b) => (cpSet.has(b) - cpSet.has(a)) || (dpFrees(g, b) - dpFrees(g, a)) || (a < b ? -1 : 1);
  const proof = new Set(p.proof);
  const stepIds = p.open.filter(id => !proof.has(id)).concat(p.outside);
  const levels = [...new Set(stepIds.map(id => lv[id] || 0))].sort((a, b) => a - b);
  const total = levels.length + (p.proof.length ? 1 : 0);
  const row = (cls, label, step, ids, mark) => `<div class="tu-wv tu-dp-wv${cls ? " " + cls : ""}"><div class="tu-wv-l"><b>${label}</b><small>${ids.length}</small>${
    step ? `<small class="tu-dp-step">step ${step}</small>` : ""}</div><div class="tu-wv-c">${ids.sort(rank).map(id => dpChip(g, id, cpSet, mark(id))).join("")}</div></div>`;
  const ownMark = id => (p.outside.indexOf(id) >= 0 ? "out" : null);
  let rows = p.shipped.length ? row("done", "Shipped", 0, p.shipped.slice(), () => null) : "";
  levels.forEach((w, i) => {
    const label = i === 0 && w === 0 ? "Now" : "Then " + (levels[0] === 0 ? i : i + 1);
    rows += row(i === 0 && w === 0 ? "now" : "", label, (i + 1) + (i === 0 ? " of " + total : ""), stepIds.filter(id => (lv[id] || 0) === w), ownMark);
  });
  if (p.proof.length) rows += row("proof", "Proof", total, p.proof.slice(), () => null);
  const head = p.chain.length ? g.nodes[p.chain[0]] : null;
  const headOut = head && p.outside.indexOf(head.id) >= 0;
  const headPerson = head && dpPerson(head);
  const headArea = head ? dpAreaOf(head) : null;
  const article = w => (/^[aeiou]/i.test(w) ? "an " : "a ") + w;
  let headSaid = "";
  if (head && headOut) headSaid = ` &middot; the first is ${esc(article(dpKindWord(head) || "issue"))}${headArea ? " in " + esc(headArea.name) : " outside this slice"}${headPerson ? " waiting on a person" : ""}`;
  else if (head && headPerson) headSaid = " &middot; the first waits on a person";
  const cpLine = p.chain.length > 1
    ? `<p class="tu-dp-cpline" data-dp-critical><span class="tu-dp-cp">Critical path</span> ${dpChainHtml(g, p.chain)} <span class="tu-faint">&middot; ${p.chain.length} steps${headSaid}</span></p>`
    : "";
  const stepOf = id => { const at = levels.indexOf(lv[id] || 0); return at < 0 ? "" : String(at + 1); };
  const outs = p.outside.map(id => { const n = g.nodes[id], a = dpAreaOf(n);
    return `${esc(dpKindWord(n) || "issue")} ${link(dpRoute(n), "tu-lnk tu-mono", esc(dpShort(n)))}${a ? " in " + esc(a.name) : ""} holds step ${stepOf(id)}`; });
  const laters = p.later.map(id => { const n = g.nodes[id], a = dpAreaOf(n);
    return `${link(dpRoute(n), "tu-lnk tu-mono", esc(dpName(n)))}${a ? " in " + esc(a.name) : ""}`; });
  const border = outs.length || laters.length ? `<p class="tu-sm tu-dp-border" data-dp-border>${outs.length ? `Outside this slice: ${outs.join("; ")}.` : ""}${
    outs.length && laters.length ? " " : ""}${laters.length ? `Waits on this slice: ${laters.join(", ")}.` : ""}</p>` : "";
  const deps = (p.s.dep || []);
  const after = deps.length ? `<p class="tu-sm tu-dp-afterline" data-dp-after><span class="tu-dp-wh tu-dp-where-order">Comes after</span> ${deps.map(d => {
    const t = SL[d];
    return `${t ? link("slice:" + d, "tu-lnk tu-mono", esc(d)) : esc(d)}${t ? ` (${!openSlice(t) ? "done" : esc(tuStatusWord(t.state).toLowerCase())})` : ""}`;
  }).join(", ")} in the plan. Order only &mdash; it does not hold start.</p>` : "";
  const left = p.open.length ? `${total} step${total === 1 ? "" : "s"} left` : "every PRD has shipped";
  return `<section class="tu-dp-path" data-dp-path="${esc(sid)}"><div class="tu-dp-h"><h3 class="tu-h3">Path to done</h3><span class="tu-dp-lead">${left}</span></div>` +
    `${cpLine}<div class="tu-wvs tu-dp-wvs">${rows}</div>${border}${after}</section>`;
}

/* ── the slice page ──────────────────────────────────────────────────────────────────────────────── */
function tuSlicePage(id){
  const s = SL[id], p = PG[s.program];
  /* A SLICE WITH NO PROGRAM (it lives under its feature area, FLT-1280) still has its PRDs: read as a program of one cut. */
  const rows = (p ? tuPrds(p) : tuPrds({ proof: s.proof || [], sl: [s] })).filter(r => r.slice === id);
  const area = String(s.area || "");
  /* THE HOST'S SLOT, AS THE OLD PAGE ASKS IT: cards a run wrote, the "being refined" sentence, and the one line
     about the program's drive — which this page draws in its own Delivery slot, so it is lifted out. */
  const turn = {};
  const asks = hostAsks("slice", s.id, s.program, s, p ? p.name : "", turn);
  const found = /<p class="drive-line slice-drive">[\s\S]*?<\/p>/.exec(asks || "");
  const rest = found ? asks.replace(found[0], "") : String(asks || "");
  /* THE HOST'S ONE LINE ABOUT THE DRIVE, as words: it says "Reading whether ..." while the read is out and "Couldn't load whether ..." when it
     failed, and the Fleet row says the same instead of a bare "Checking..." (the read re-tries by itself). */
  /* already HTML-escaped text (the host built it), so it is NOT escaped again */
  const driveText = found ? found[0].replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim() : "";
  /* WHAT THE PROGRAM'S DRIVE DOCUMENT SAYS ABOUT THIS CUT: the PRDs of it held up on a person (a hold by hand counts, not only a
     parked question), and who is driving. */
  const hostFacts = p && TU_HOST && typeof TU_HOST.programFacts === "function" ? (() => { try { return TU_HOST.programFacts(p.id) || {}; } catch (err){ return {}; } })() : {};
  const holds = tuHoldsIn(tuHolds(hostFacts), rows);
  TU_HOLDS = holds;
  const proof = s.proof.length ? `proved by ${tuProofLinks(s.proof)}${s.proven ? "" : " (not shipped)"}`
    : s.state === "waived" ? "proof waived &mdash; this slice names no proof of its own" + housedProofs(s)
    : s.owed ? `proof owed &mdash; ${esc(s.owed)}` : "no proof named";
  const after = (s.dep || []).length ? `after ${s.dep.map(d => SL[d] ? link("slice:" + d, "tu-lnk", esc(d)) : esc(d)).join(", ")}` : "";
  /* THE FLEET'S WORK ON A REFINEMENT IS THE STATE CHIP at the end of the status line, and its conversation and Snooze are the header's ⋯ menu
     (the host's shared `tuHeaderMenu`); the slice page draws no work card. */
  const work = TU_HOST && typeof TU_HOST.sliceHeader === "function" ? (() => { try { return TU_HOST.sliceHeader("slice", id, { title: s.name, doneWhen: String(s.done_when || ""), program: p ? p.id + (p.name ? " " + p.name : "") : "" }) || {}; } catch (err){ return {}; } })() : {};
  const stepsOut = tuSliceSteps(s, rows, holds);
  /* AN AREA SLICE'S CRUMBS LEAD TO ITS FEATURE AREA (the nav's "Features", `#areas:<slug>`), where the host serves that page. */
  const areaAt = !p && area ? dpAreaOf({ kind: "slice", sid: s.id }) : null;
  const areasPage = !!(TU_HOST && typeof TU_HOST.areaIndex === "function");
  const header = `<div class="tu-crumbs2">${p || !area ? link("board", "tu-lnk", "Programs") : areasPage ? link("areas", "tu-lnk", "Features") : "Features"} &rsaquo; ${p ? link("program:" + p.id, "tu-lnk", esc(p.id)) + " &rsaquo; "
    : area ? `${areasPage ? link("areas:" + (areaAt ? areaAt.slug : area), "tu-lnk", esc(areaAt ? areaAt.name : area)) : `<span>${esc(area)}</span>`} &rsaquo; ` : ""}<span class="tu-mono">${esc(s.id)}</span></div>
    `;
  /* WHERE IT LIVES (FLT-1280): its feature area, by the feature's name; a slice driven on its own says nothing about programs ("no
     program" is a planning term, not a fact the reader needs). A slice still naming no area says it needs one, which the migration
     (`fleet planning migrate`) or its next edit gives it. */
  const home = area ? `in feature <b>${esc(((areaAt || dpAreaOf({ kind: "slice", sid: s.id })) || {}).name || area)}</b>` : `<span class="tu-attn">needs a feature</span>`;
  /* THE PROPERTIES LINE'S FEATURE: where `areaview.place` puts the slice (its authored area, else its components', else its PRDs'), through the
     same area index the dependencies block reads; the authored area stands in until that is read. */
  const placed = dpAreaOf({ kind: "slice", sid: s.id });
  const sliceAreas = placed ? [placed] : (dpCall("areaIndex") ? [] : null);
  /* THE HEADER IS THE TITLE BLOCK AND THE STEP STRIP; the question box follows it, and the tabs follow the box (the owner's mockup). The roll-up
     line and Done when are the Overview tab's now. */
  /* THE SLICE'S OWN QUESTIONS, ON ITS OWN PAGE: the open set is drawn by the item page's frame and card, so it is answered here, and
     the sets already answered follow it read-only. A slice with neither draws neither -- no sentence saying so. */
  const asked = TU_HOST && typeof TU_HOST.pageQuestions === "function" ? (() => { try { return TU_HOST.pageQuestions("slice", id); } catch (err){ return null; } })() : null;
  const slotAsk = asked && asked.open ? tuSlot("Waiting on a person", asked.open) : "";
  const headerOut = tuHeader({ crumbs: header, badge: tuBadge("slice"), mini: stepsOut.mini, key: s.id,
    ids: p ? [`<span class="tu-chip">${esc(p.id)}</span>`] : [], kind: `<span class="tu-chip">${esc(sliceKindWords(s.kind))}</span>`, menu: work.menu || "",
    title: esc(s.name), state: stepsOut.state, assigned: tuAssigned(s, "slice"),
    props: tuPlacedLine(sliceAreas, "A slice's feature is edited in its git row", s.id),
    facts: [home, proof, after, `${rows.length} PRD${rows.length === 1 ? "" : "s"}`, sliceDispositionFact(s) || ""], run: work.chip || "", steps: stepsOut.list, ask: slotAsk, askAfterSteps: true });
  const ownDone = asked && Array.isArray(asked.answeredRows) ? asked.answeredRows : [];
  /* THE SLICE'S CHILDREN: the answered questions on its PRDs (and the slice's own, plain), from the slice's decisions read. A set the page
     already draws as a rich card of its own (`ownDone`) is dropped from it, so each question set is listed once. */
  const sliceDec = TU_HOST && typeof TU_HOST.sliceDecisions === "function" ? (() => { try { return TU_HOST.sliceDecisions(id) || null; } catch (err){ return null; } })() : null;
  const haveSets = new Set(ownDone.map(r => String(r.id || "").split(":")[0]));
  const childDec = ((sliceDec && sliceDec.list) || []).filter(d => !d.questionSetId || !haveSets.has(String(d.questionSetId)));
  const nDecs = childDec.length + ownDone.length;
  /* WHILE A QUESTION IS OPEN ITS BOX IS THE WAITING: the host's sentence "Being refined by the fleet now — it is waiting on an answer" said what
     the box says, so it is not drawn under it (the owner: too much text). The held-up PRD cards, which are not the box, still are. */
  const waiting = tuHoldCards(holds, asked && asked.open ? "" : String(rest).trim());
  /* THE SECTION AGREES WITH THE CARD IT HOLDS: the host says whose turn the refine is (`turn.fleetTurn`, the work card's own fact). A run the
     fleet holds is the fleet's work; the PRDs held up on a person
     keep "Waiting on a person". */
  const holdsOut = tuHoldCards(holds, "");
  /* THE RUN ITSELF IS THE HEADER'S CHIP (the page draws no work card); what stays in this section is whatever else the host says about it; an
     answered round is the Decision log's, never drawn here. */
  const fleetOut = turn.fleetTurn && !(asked && asked.open) ? String(rest).trim() : "";
  const slotWaiting = (turn.fleetTurn ? holdsOut : waiting).trim() ? tuSlot("Waiting on a person", turn.fleetTurn ? holdsOut : waiting) : "";
  const slotFleet = fleetOut ? tuSlot("The fleet&rsquo;s work", fleetOut) : "";
  const progUndecomposed = !!(p && D.actions.some(a => a.id === p.id && a.group === "undecomposed"));
  /* WHILE THE SLICE IS BEING REFINED a run waits on these answers, so "a promise nobody has started" is false: say what comes next. It is the
     Built row's sentence now that a slice with no PRDs has no Plan tab to say it in. */
  const empty = asked && asked.open ? "No PRDs yet &mdash; they are cut after the questions above are answered."
    : progUndecomposed ? `No PRDs yet &mdash; decomposition comes first. ${esc(p.id)} names no decomposition roots yet, so nothing writes a PRD into this cut until that run names them.`
    : "No PRDs yet. This slice is a promise nobody has started.";
  /* THE SLICE'S TABS ARE THE PROGRAM PAGE'S AND THE ITEM PAGES': Overview, Plan (only where PRDs exist), Decision log, Activity. Overview is
     "In plain words" where the slice states a summary of its own (`s.summary`, a field no slice carries yet), the stands rows (the program page's,
     one function), then Done when and Part of: the slice's existing words, never copy written for it. */
  const doneWhen = esc(String(s.done_when || "").replace(/`/g, ""));
  const lean = (label, html) => `<section><div class="tu-lbl2">${label}</div><div class="tu-pov-lead">${html}</div></section>`;
  const summary = String(s.summary || "").trim();
  /* THE PATH TO DONE (the approved dependencies mockup, screen 2): the order of work with the critical path threaded and
     outside blockers in the step they hold. A slice with no PRDs has no path and draws none. */
  const path = tuSlicePath(id);
  const overview = `<div class="tu-pov">${summary ? tuPlainWords(mdown(summary)) : ""}${path}${tuWhereItStands(tuSliceStands(s, p, rows, holds, hostFacts, asked, empty, driveText))}${
    doneWhen ? lean("Done when", doneWhen) : ""}${p ? lean("Part of", link("program:" + p.id, "tu-lnk", esc(p.id + " " + p.name))) : ""}${
    area ? lean("Feature", esc(area)) : ""}</div>`;
  const none = text => `<div class="tu-ph-ppad"><p class="tu-sm tu-muted">${text}</p></div>`;
  const plan = `<div class="tu-ph-ppad">${tuSlicePrds(s, rows)}</div>`;
  /* ALWAYS THE SHARED RENDERER, empty or not: the slice's empty log reads as the program's, the issue's and the PRD's do. */
  const decisions = tuDecisionLog("slice", s.id, childDec,
    { readAt: hostFacts.readAt, viewer: hostFacts.viewer, decisionsMore: !!(sliceDec && sliceDec.more) }, ownDone);
  const events = asked && Array.isArray(asked.asked) ? asked.asked : [];
  /* ACTIVITY HOLDS WHAT THE DECISION LOG HOLDS: the answers on the slice's PRDs count, as answered questions, beside the slice's own. */
  const childAnswered = childDec.map(d => {
    const by = String(d.answeredBy || d.by || "") === "unstamped" ? "" : String(d.answeredBy || d.by || "");
    const name = typeof tuItemActorName === "function" ? tuItemActorName(by, String(hostFacts.viewer || "")) : by;
    const machine = !!by && by.indexOf("@") < 0 && typeof tuActorIsMachine === "function" && tuActorIsMachine(by);
    /* A MACHINE-STAMPED ANSWER READS "Fleet", as the other Activity rows word it: the actor helper decides, not a hard-coded person. */
    return { at: String(d.answeredAt || ""), a: String(d.answer || ""),
      who: machine ? { kind: "agent", name, cmd: name, run: "" } : { kind: "person", name, email: by, cmd: "", run: "" } };
  });
  const activity = (events.length || ownDone.length || childAnswered.length) && typeof tuItemSliceActivity === "function"
    ? tuItemSliceActivity(events, [...ownDone, ...childAnswered], { scope: "act:slice:" + s.id, readAt: String(hostFacts.readAt || ""), viewer: String(hostFacts.viewer || "") })
    : none("Nothing is recorded for this slice yet. Each question Fleet asks and each answer appears here.");
  const count = n => n ? ` <span class="tu-n">${n}</span>` : "";
  const panes = [["overview", "Overview", overview], ...(rows.length ? [["plan", `Plan${count(rows.length)}`, plan]] : []),
    ["decisions", `Decision log${count(nDecs)}`, decisions], ["activity", "Activity", activity]];
  const page = "slice:" + id;
  const tab = tuTabOf(page, panes[0][0], panes.map(x => x[0]));
  const body = tuTabs(page, tab, panes.map(x => [x[0], x[1]])) + `<div class="tu-tabpane">${panes.find(x => x[0] === tab)[2]}</div>`;
  /* THE SLICE'S OWN DELIVERY BOX, for a slice with an area, or one under a program: either can be started on its own. The host draws it
     (`sliceDrive`, the service's `GET /api/drive/slice/{key}`); the standalone board has no fleet to start, so draws none. */
  const own = (area || p) && TU_HOST && typeof TU_HOST.sliceDrive === "function" ? (() => { try { return TU_HOST.sliceDrive(s) || ""; } catch (err){ return ""; } })() : "";
  const slotDrive = own ? tuSlot("Delivery", own) : "";
  return `<div class="tu-page tu-item">${headerOut}${tuRunSlot(s.id)}${slotDrive}${slotFleet}${slotWaiting}${body}</div>`;
}
/* THE NEW PAGES' OWN CONTROLS — tabs, the responsible filter — delegated from
   the document like every other control here. */
document.addEventListener("click", e => {
  if (!e.target.closest) return;
  let el;
  const tab = e.target.closest("[data-tu-tab]");
  if ((el = tab)){
    e.preventDefault();
    const to = el.getAttribute("data-tu-tab");
    if (to) TU_TABS[el.getAttribute("data-tu-page") || openRoute()] = to;
    return render(openRoute());
  }
});

/* THE PROGRAM'S DECISION LOG FILTERS AND SORTS as the item pages' do: the state is the shared renderer's (`team-item.js`), kept by
   scope; this page only repaints. */
document.addEventListener("click", e => {
  if (!e.target.closest || typeof tuItemDecisionLogSet !== "function") return;
  const hit = e.target.closest("[data-tu-lf]") || e.target.closest("[data-tu-sort]");
  const scope = hit && hit.getAttribute("data-tu-declog");
  if (!scope) return;
  const lf = hit.getAttribute("data-tu-lf");
  if (!tuItemDecisionLogSet(scope, lf || "", !lf)) return;
  e.preventDefault();
  render(openRoute());
});

/* ONE LINE FOR WHERE THE ISSUE STANDS: its key as a link, its position word. */
function liveLine(live){
  return `${link(live.go, "chip link", esc(live.key))} &middot; ${esc(live.state)}`;
}

/* WHAT A PRD'S STATUS MEANS, IN PLAIN WORDS (ENG-10590). The chip says `prd-drafted` or `planned`
   — the record's own word — and a product person reading the page could not tell whose move it
   was. One sentence, from the three facts the row already carries: terminal or live, the
   fleet's turn or a person's. */
/* WHOSE MOVE A LIVE PRD IS, in one sentence: a person's, when a row only a person can move is keyed on it
   (the same reading the program page's "Needs you" makes — `personsMoves`), with its reason and the issue's
   position when the host holds one; else the issue's live line; else the record's own words. */
function prdOwnership(r, host){
  const yours = personsMoves(r.n);
  if (yours.length){
    const at = host.live ? ` Its issue ${host.live.key} is at ${host.live.state}.` : "";
    return `Waiting on a person — ${firstSentence(yours[0].why)}${at}`;
  }
  /* A PRD NO TRACKER ISSUE CARRIES WHOSE BUILD WAITS ON A PERSON (`host.live.person`, a customer's PRD-0007): its park or
     stop, in the run's own words — never "in the fleet's hands" over a person's step. */
  if (host.live && host.live.person){
    const said = firstSentence(host.live.ask || "") || host.live.sentence || "its last run is waiting on a person";
    return `Waiting on a person — ${said} (${host.live.key} is at ${host.live.state}; answer it on Needs you).`;
  }
  return host.live ? `In the fleet's hands — its issue ${host.live.key} is at ${host.live.state}.` : prdStatusWords(r);
}

function prdStatusWords(r){
  if (r.status === "shipped") return "Shipped — the work landed.";
  if (TERMINAL.includes(r.status)) return `Closed without shipping — ${r.status}.`;
  /* A RECORD (ENG-10704, B-01): its cut was withdrawn from the plan — the roll-up's own `withdrawn` state — so
     nothing on this page moves it, and `advance` handed it no command. */
  if (r.closed) return r.closed === "withdrawn"
    ? "A record — its slice was withdrawn from the plan, so nothing here moves it."
    : "A record — its slice belongs to a program that is parked or proven, so nothing here moves it.";
  if (r.fleet) return `In the fleet's hands — a worker picks it up on its own; nothing for you to do.`;
  if (r.cmd) return `Waiting on a person — the next step is yours.`;
  /* A LIVE STATUS NO STEP IS WRITTEN FOR IS WORK UNDER WAY, NOT A DEAD END (ENG-10704, X9): an
     implementing or verified PRD read "no next step is recorded" and then "none — terminal". */
  if (OFF_BOARD[r.n]) return `Open at '${r.status}', and in no slice on the plan — nothing here moves it.`;
  /* NO STEPS WRITTEN AT ALL (ENG-17173): the repository's vocabulary names no command for any PRD
     status, so whose move this is cannot be read here — and "under way" would claim progress on a
     stub nobody touched. The fix is in the repository's `fleet.toml`, as the program page's driver says. */
  if (r.noSteps) return `At '${r.status}' — this repository's board vocabulary names no next step for a PRD, so the board cannot say whose move it is. Whoever looks after the repository points its fleet.toml at one.`;
  return `Under way at '${r.status}' — nothing here is yours to run.`;
}

/* ── THE PRD PAGE'S BUILD STEPS (PROD PRD 0864, the owner: "I don't see the dependency waves on that page; add that,
 * like we have it on programs") ──────────────────────────────────────────────────────────────────────────────
 *
 * THE PROGRAM PAGE'S OWN COMPONENT, over the other direction: `chainSection` draws what stands between a PROGRAM and its
 * proof, this draws what stands between a PRD and the day it can be built -- every PRD it `depends_on`, and theirs, as the
 * same `.waves` / `.wave` columns of the same `waveNode`, so a PRD reads the same on both pages. What it adds is the
 * GROUND: a prerequisite that is already built is drawn too (the program page leaves settled work out, because a step
 * counts UNMET prerequisites), in a first column of its own, so a reader sees at a glance how much of what this PRD builds
 * on exists. The unbuilt ones follow in build steps, the PRD itself last.
 *
 * A `depends_on:` ENTRY IS A PRD NUMBER OR A TRACKER KEY (`ENG-16070`, a bug fix the PRD waits for). A PRD's state is on
 * the payload; a key's lives in the issue ledger, so the host answers for it through `prereqs` -- `{prerequisites:
 * [{ref, kind, type, title, state, built, sentence}], hold}` -- and so does the sentence the driver is holding this PRD with, which this
 * file prints and never derives. A host with no answer draws the PRD prerequisites alone and says a key's state is unread.
 */
let PREREQS = null;
function prereqs(fn){ PREREQS = fn || null; }
function prereqsOf(n){
  if (!PREREQS) return null;
  const said = PREREQS(String(n));
  return said && typeof said === "object" && Array.isArray(said.prerequisites) ? said : null;
}
const TRACKER_KEY = /^[A-Z][A-Z0-9]*-\d+$/;
function prdBuilt(x){ return x.status === "shipped"; }
/* THE PRDS THAT BUILD ON THIS ONE (downstream): every PRD whose own `dep` lists it. They are NOT prerequisites and are
   never drawn into the waves -- a PRD that lists this one and is not listed by it waits on this PRD, not the reverse. */
function prdDependentsSection(r, rows){
  const later = Object.values(PRD).filter(x => x.n !== r.n && (x.dep || []).includes(r.n) && !rows[x.n])
    .sort((a, b) => a.n.localeCompare(b.n));
  if (!later.length) return "";
  const nodes = {}, up = {}, down = {};
  later.forEach(x => { nodes[x.n] = { id: x.n, kind: "prd", x, prog: x.program || "" }; up[x.n] = new Set(); down[x.n] = new Set(); });
  const g = { nodes, up, down };
  return `<section class="grp prd-waves" data-prd-dependents="${esc(r.n)}"><div class="grp-h">
      <h3>Builds on this PRD</h3><span class="n">${later.length}</span></div>
    <p class="grp-b">${later.length === 1 ? "This PRD lists" : "These PRDs list"} PRD ${esc(r.n)} as a prerequisite, so ${
      later.length === 1 ? "it waits" : "they wait"} on it. PRD ${esc(r.n)} does not wait on ${later.length === 1 ? "it" : "them"}.</p>
    <div class="waves"><div class="wave"><h4>Builds on this · ${later.length}</h4><div class="inner">${
      later.map(x => waveNode(g, g.nodes[x.n], "")).join("")}</div></div></div>
  </section>`;
}

function prdWavesSection(r){
  const deps = r.dep || [];
  if (!deps.length) return prdDependentsSection(r, {});
  const said = prereqsOf(r.n);
  const info = {};
  ((said && said.prerequisites) || []).forEach(o => { info[o.ref] = o; });
  /* THE CLOSURE OVER PRD NUMBERS: this PRD's prerequisites, and theirs. A tracker key is a leaf -- the host knows its
     state for THIS PRD's own entries only, so a key nested under another PRD is not drawn from here. */
  const rows = {}, keys = [];
  const walk = x => (x.dep || []).forEach(d => {
    if (TRACKER_KEY.test(d)){ if (x === r && !keys.includes(d)) keys.push(d); return; }
    if (rows[d] || d === r.n) return;
    rows[d] = PRD[d] || { n: d, title: "", status: "not in the plan", slice: "", program: "", dep: [], wave: null };
    walk(rows[d]);
  });
  walk(r);
  const nodes = {}, up = {}, down = {};
  const add = (id, kind, x) => { nodes[id] = { id, kind, x, prog: x.program || "" }; up[id] = new Set(); down[id] = new Set(); };
  Object.values(rows).forEach(x => add(x.n, "prd", x));
  add(r.n, "prd", r);
  const keyBuilt = k => !!(info[k] && info[k].built);
  const unbuiltKey = k => !keyBuilt(k);
  /* A PRD THAT LISTS THIS ONE BACK is a loop, not a step: it is said under the heading, and no edge is drawn into this PRD
     from the columns before it (it would be its own prerequisite). */
  const loops = Object.values(rows).filter(x => (x.dep || []).includes(r.n)).map(x => x.n).sort();
  const edge = (from, to) => { if (nodes[to] && to !== r.n && !(rows[to] ? prdBuilt(rows[to]) : false)){ up[from].add(to); down[to].add(from); } };
  Object.values(rows).concat([r]).forEach(x => (x.dep || []).forEach(d => { if (!TRACKER_KEY.test(d)) edge(x.n, d); }));
  /* AN UNBUILT KEY IS A NODE OF THE GRAPH TOO, so "waits on N" on this PRD counts it beside the PRDs. */
  keys.filter(unbuiltKey).forEach(k => { add(k, "issue", { n: k, program: "" }); up[r.n].add(k); down[k].add(r.n); });
  /* THE STEP OF AN UNBUILT PRD: nothing unbuilt beneath it is step 0, else one past the deepest. A key waits on no PRD. */
  const level = {};
  const stepOf = id => {
    if (level[id] !== undefined) return level[id];
    level[id] = 0;
    let deepest = -1;
    up[id].forEach(d => { deepest = Math.max(deepest, stepOf(d)); });
    level[id] = deepest + 1;
    return level[id];
  };
  const g = { nodes, up, down };
  const builtRows = Object.values(rows).filter(prdBuilt).sort((a, b) => a.n.localeCompare(b.n));
  const openRows = Object.values(rows).filter(x => !prdBuilt(x));
  openRows.forEach(x => stepOf(x.n));
  /* A KEY IS ALWAYS A PRIOR STEP TO THIS PRD ITSELF, so this PRD sits after it: the last column. */
  const keyNode = k => {
    const o = info[k] || null;
    const built = keyBuilt(k);
    const kind = o && o.type ? o.type : "issue";
    const tone = built ? " complete" : o ? " flight" : " unproven";
    return `<a class="wnode k-issue${tone}" href="${esc(urlFor("issue:" + k))}" data-go="issue:${esc(k)}" data-node="${esc(k)}">
        <div class="wi"><span class="wk">${esc(kind)}</span> ${esc(k)}</div>
        <div class="wn">${esc(o && o.title ? o.title : "a tracker issue")}</div>
        <div class="we"><span class="${built ? "none" : "up"}">${esc(o ? o.state : said ? "not seen by the fleet" : "state unread")}</span>${
          built ? "" : `<span class="none">${esc(o && o.sentence ? o.sentence : "must merge first")}</span>`}</div>
      </a>`;
  };
  const col = (title, inner) => `<div class="wave"><h4>${title}</h4><div class="inner">${inner}</div></div>`;
  const cols = [];
  const groundNodes = builtRows.map(x => waveNode(g, g.nodes[x.n], "")).concat(keys.filter(keyBuilt).map(keyNode));
  if (groundNodes.length) cols.push(col(`Already built &middot; ${groundNodes.length}`, groundNodes.join("")));
  const max = openRows.reduce((m, x) => Math.max(m, level[x.n]), -1);
  const openKeys = keys.filter(unbuiltKey);
  for (let w = 0; w <= max || (w === 0 && openKeys.length); w++){
    const here = openRows.filter(x => level[x.n] === w).sort((a, b) => a.n.localeCompare(b.n));
    const body = here.map(x => waveNode(g, g.nodes[x.n], "")).join("") + (w === 0 ? openKeys.map(keyNode).join("") : "");
    if (!body) continue;
    cols.push(col(`${w === 0 ? term("wave", "Build step") : "Build step"} ${w} &middot; ${here.length + (w === 0 ? openKeys.length : 0)}`, body));
  }
  cols.push(col("This PRD", waveNode(g, g.nodes[r.n], "")));
  const total = builtRows.length + openRows.length + keys.length;
  const built = builtRows.length + keys.filter(keyBuilt).length;
  const open = total - built;
  const hold = said && said.hold ? String(said.hold) : "";
  const lead = open
    ? `${built} of ${total} prerequisite${total === 1 ? "" : "s"} built &mdash; ${open} still ${open === 1 ? "stands" : "stand"} in front of this PRD.`
    : `Everything this PRD builds on is built (${total} prerequisite${total === 1 ? "" : "s"}).`;
  return `<section class="grp prd-waves" data-prd-waves="${esc(r.n)}"><div class="grp-h">
      <h3>What this PRD builds on</h3><span class="n">${total}</span></div>
    <p class="grp-b" data-prd-ground>${lead}</p>
    ${loops.length ? `<p class="grp-b" data-prd-loop><b>A loop:</b> ${esc(loops.map(n => "PRD " + n).join(" and "))} ${
      loops.length === 1 ? "also lists" : "also list"} this PRD as a prerequisite, so ${loops.length === 1 ? "the two wait" : "they wait"} on each other and neither can start.</p>` : ""}
    ${hold ? `<p class="grp-b" data-prd-hold><b>Why the fleet is holding it:</b> ${esc(hold)}</p>` : ""}
    ${waveLegend()}
    <div class="waves" id="prd-waves">${cols.join("")}</div>
  </section>${prdDependentsSection(r, rows)}`;
}

/* THE STUB'S OWN PLACEHOLDER LINE (`prd:create`'s stub template: "**Not written yet.** This PRD holds only the brief below …",
   and on an older stub "**Status:** stub. The body is written by `/<ns>:prd:create NNNN` at a terminal …"),
   which the sync takes for a stub's summary when it has no `## In Plain Words`. It says nothing about the PRD itself, so the page
   shows no summary instead (owner, on #prd:0008). */
const PRD_PLACEHOLDER_RE = /^\s*>?\s*\*\*(?:Status:\*\*\s*stub\b|Not written yet\.\*\*)/i;
function prdPlaceholder(text){
  return PRD_PLACEHOLDER_RE.test(String(text || ""));
}

/* THE STATUS AS A PERSON READS IT: `stub` is the register's word for "not written yet", and the page says that instead. */
function prdStatusPlain(status){
  return status === "stub" ? "being written" : String(status || "");
}

function viewPrd(n){
  const r = PRD[n], s = SL[r.slice], p = PG[r.program];
  const live = !TERMINAL.includes(r.status);
  /* THE HOST'S SLOT, ASKED FOR FIRST: what it says about the next step belongs in the header,
     which renders before the slot does. */
  const host = {};
  const slot = hostAsks("prd", r.n, r.program, r, p ? p.name : "", host);
  const head = entityHeader({
    crumbs: [{ label: "Programs", go: "board" },
             ...(p ? [{ label: p.id + " " + p.name, go: "program:" + p.id }] : []),
             ...(s ? [{ label: s.id + " " + s.name, go: "slice:" + s.id }] : []),
             { label: r.n }],
    id: r.n, name: r.title,
    chips: [`<span class="chip ${live ? "flight" : r.status === "shipped" ? "complete" : ""}">${esc(prdStatusPlain(r.status))}</span>`],
    /* WHAT THIS PRD IS FOR (ENG-12792): its plain-words summary — the authored `## In Plain Words`,
       or the bounded stand-in the sync derives — read off the row the board carries, the way a
       program page reads its detail file's sentence (`viewProgram`'s `desc`). Omitted when the row
       has none, so a corpus with no summary draws no empty promise line. */
    promise: prdPlaceholder(r.summary) ? "" : r.summary || "",
    /* A row nobody may run reports its status; it never hands over a command. */
    facts: [["slice", s ? badge(s.id, "", s.id)
              : OFF_BOARD[n] ? (OFF_BOARD[n].slice ? `none &mdash; its file names ${esc(OFF_BOARD[n].slice)}, which no slice on the plan holds`
                                                   : "none &mdash; no slice claims it")
              : "none"],
            ["program", p ? badge(p.id, "", p.id) : "none"],
            /* THE GLOSS DEFERS TO WHAT IS HAPPENING (ENG-10589's rule): a live run's sentence,
               then WHOSE MOVE IT IS, then the issue's live position, then the record's own reading —
               never "nothing for you to do" over an issue a person may well be needed on.
               WHOSE MOVE IT IS IS THE PROGRAM PAGE'S OWN READING (ENG-10704, R-01): `personsMoves`,
               the rows only a person can move, keyed here on the PRD. Production's 0592 and 0621 read
               "In the fleet's hands — its issue ENG-9979 is at <its design position>" beside
               `next step /<ns>:prd:design 0592`, because the issue's live line was preferred over the
               row that says a person's step waits. */
            /* L-2 (ENG-10704): `host.record`/`host.status` are the host's own already-safe HTML
               sentences — the same strings `sub: host.status || …` below inserts RAW — built with
               literal `&middot;`/`&mdash;` entities for punctuation. Wrapping them in `esc()` here
               too turned every `&` into `&amp;`, so a queued PRD's Status row printed the literal
               text `&middot;` / `&mdash;` instead of rendering "·" / "—" (0599, 0612, 0620).
               `prdOwnership`'s reading is this package's own plain sentence and still needs it. */
             /* THE AUTHORED STATUS AND THE TRACKER POSITION ARE NOT TWO PEERS (ENG-10867). The
                `status:` in the PRD's own git file is the fact; the tracker row beside it is
                where the work is queued, never a second ship-state. The two rows rendered one
                apart with bare labels, so a reader could take the issue's position for a rival
                reading of the PRD. The labels carry the reading, and only the pair whose
                ambiguity this is gets them: with no live issue there is no tracker row, so the
                status keeps its plain label. */
             ["status" + (host.live ? " (the authored fact)" : ""),
              /* NO DASH WITH NOTHING AFTER IT (PRD 0727, prod v0.5.98): the authored status and
                 the plain-English reading beside it were joined unconditionally, so a PRD whose
                 host, record and `prdOwnership` all had nothing further to add — none of the
                 three should ever be empty by this file's own contract, but a corpus can still
                 hand one an empty sentence — read "prd-drafted &mdash;" with nothing on the other
                 side of the mark. The mark is drawn only when there is a second half for it to
                 join. */
              (() => { const said = host.record || host.status || esc(prdOwnership(r, host));
                       return `${esc(prdStatusPlain(r.status))}${said ? ` &mdash; <i class="plain">${said}</i>` : ""}`; })()],
            /* THE HOST'S MOVE WINS THE NEXT STEP when it has one (ENG-10570, U-9): the fleet's
               box on this page IS the next step, and naming the attended command beside it was
               two commands for one move. Without a host, or with a host that has nothing to say,
               the record's own reading stands. */
            ...(host.inFlight ? [] : [["next step", host.record ? "none &mdash; its slice takes no new work"
                        : host.next ? host.next
                        : r.fleet && host.live ? liveLine(host.live)
                        : r.fleet ? esc(FLEET.wait)
                        : r.cmd ? `<code>${esc(r.cmd)}</code>`
                        /* A RECORD (ENG-10704, B-01): its slice takes no new work, so no step is written for it. */
                        : r.closed ? "none &mdash; its slice takes no new work"
                        : r.noSteps ? "none named &mdash; this repository&rsquo;s board vocabulary writes no PRD steps"
                        : live ? "none &mdash; nothing here is yours to run" : "none &mdash; terminal"]]),
            /* THE TRACKER'S OWN ROW FOR THIS PRD, when the host holds one: the issue and its
               position, one click away. The fact every other page about this work already shows. */
             ...(host.live ? [["tracker (where the work is queued)", liveLine(host.live)]] : [])],
  });
  /* The host slot in the same position the program and slice pages give it — under the header,
     before this page's own rows — so a host fills one seam for all three kinds. `r.program` is
     the PRD's program by way of its slice, already resolved above. */
  return asksFirst(slot, (r.fleet && host.live
      /* THE LIVE READING, IN THE TRACKER'S WORDS (ENG-10589): the position and the backlog's own
         sentence for it, never "nothing for you to do" restated over an issue a person may well
         be needed on. The issue page carries the run. */
      ? `<section class="grp"><div class="grp-h"><h3>Status</h3></div>
      ${entityList([{ id: r.n, title: r.title, sev: 3, badges: [],
        /* THE RUN OUTRANKS THE POSITION WORD (ENG-10590): "is being implemented on <machine>"
           when the host knows one, the tracker's position and the backlog's sentence otherwise.
           L-2 (ENG-10704): `sub` is prose `entityList` runs through `mdown`, which escapes it
           like any other corpus text — an HTML ENTITY REF here (`&middot;`, `&mdash;`) gets its
           own `&` escaped into `&amp;middot;`, so 0599/0612/0620 (no open or parked run, so
           `host.status` is empty and this fallback fired) printed the literal text `&middot;` /
           `&mdash;` instead of "·" / "—". A literal Unicode character survives `esc()`
           unchanged, exactly like `prdOwnership`'s own "—" a few lines up. */
        /* M-2 (ENG-10766): NO `esc()` HERE, on purpose — `entityList` runs `sub` through
           `mdown`, which escapes first itself, so a pre-escaped apostrophe (`&#39;`) had its
           `&` escaped into `&amp;#39;` and the page printed the literal text `&#39;` for every
           `'` (and `&`, `<`, `>`) in a backlog sentence. Raw text in, one escape out: the same
           contract `sub: a.why` in `actionItems` already runs under, and the same reason the
           fallback at 3602 uses raw words. */
        sub: host.status || `${host.live.key} · ${host.live.state}${host.live.sentence ? " — " + host.live.sentence : ""}`,
        /* THE POSITION IS THE CONTROL (PG-08), not a bare "Open ENG-…" beside it: the
           issue and where it stands, in flight while the host holds a run on it. A literal "·" and
           not `&middot;` — the Status section is held to carrying no entity (ENG-10766). */
        right: waitbox(`${host.live.key} · ${host.live.state}`, host.live.go || "issue:" + host.live.key,
                       host.status ? "work" : "grey") }])}</section>`
      : r.fleet
      ? `<section class="grp"><div class="grp-h"><h3>Status</h3></div>
      ${entityList([{ id: r.n, title: r.title, sev: 3, badges: [],
        sub: host.status || `Planned. ${FLEET.Actor} picks this up and implements it — nothing for you to do.`,
        right: waitbox(host.status ? "With the fleet now" : FLEET.wait, "", host.status ? "work" : "grey") }])}</section>`
      : r.cmd && !host.record && !host.shaping ? `<section class="grp"><div class="grp-h"><h3>To do here</h3></div>
      ${entityList([{ id: r.n, title: r.title, sev: 1, badges: [],
        /* WHEN THE HOST'S BOX IS THE MOVE (X8, ENG-10691): the sentence said the fleet only
           implements while the box beside it offered the fleet's fill. The step is still a
           person's to start — on the fleet, or in a terminal — and that is what it says. */
        sub: host.next
          /* ONE SENTENCE, so the row's visible first sentence carries it whole (`firstSentence`). */
          ? `Sitting at '${r.status}', and the next step is yours to start: hand it to ${FLEET.actor} or run it yourself in an agent session.`
          /* A DRAFTED PRD'S DESIGN IS THE FLEET'S WHILE ITS PROGRAM IS DRIVEN (0164, `prd:blueprint`), and
             this page cannot see whether it is — so the one sentence true either way (`board.py`'s own). */
          : r.status === "prd-drafted"
          ? `Sitting at '${r.status}': its design waits on you — or on ${FLEET.actor}, while its program is driven.`
          : `Sitting at '${r.status}'. ${FLEET.Actor} only implements, so this planning step waits on you.`,
        right: runbox(r.cmd, r.built, r.n) }])}</section>` : "") + prdWavesSection(r), head);
}

/* ── the block renderer ───────────────────────────────────────────────────
 *
 * `mdown` above is INLINE — code spans, bold, em — and that is all any row on this page
 * needed until a command's own text had to be readable here. This is the block layer over
 * it: it reuses `mdown` for everything inside a block, so there remains exactly one escaper
 * and one reading of a backtick on this page.
 *
 * WHY IT IS HAND-WRITTEN AND NOT A LIBRARY. `board.js` is served two ways — by the deployed
 * app, and as one self-contained file for a repository with no deployment. A vendored
 * renderer exists only in the first, so the second would silently lose the page. Ninety
 * lines that this corpus's own files are TESTED against is a smaller liability than a
 * feature that works in one of the two places it ships.
 *
 * WHAT IT COVERS, and the list is closed on purpose: fenced code, tables (with the separator
 * row's `:---:` / `---:` alignment), headings, blockquotes, ordered and unordered lists with
 * nesting, `- [ ]` / `- [x]` task items, horizontal rules, paragraphs, and — inside any of
 * them — `[text](url)` links to an allowed destination (`mdHref`) and bare or `<…>` http(s) URLs
 * (`MD_BARE`, `MD_AUTO`).
 * That is what the command corpus actually uses — measured, not guessed — and a construct
 * outside it renders as its own literal text rather than as broken markup.
 *
 * `opts.breaks` — A LINE BREAK A PERSON TYPED IS KEPT (GitHub's rule for issue and comment text,
 * as opposed to its rule for a document). A filing is written in a text box, not authored as a
 * document: "WHAT HAPPENS" on one line and the sentence under it on the next are two lines to the
 * person who typed them, and joining them into one paragraph ("WHAT HAPPENS A gated run…") is the
 * renderer rewriting the filer. Off by default, so a command's or a document's soft-wrapped prose
 * still reflows; the filing pages opt in.
 */
/* AN ANCHOR ON EVERY HEADING, so a long document can carry an on-this-page rail.
 *
 * DERIVED FROM THE TEXT AND NOTHING ELSE — no counter, no seen-set. `mdBlock` recurses into
 * blockquotes and nested list items, so a numbering scheme would need state threaded through
 * the recursion and would renumber the whole document the day somebody added a paragraph. Two
 * identical headings therefore share an id, which is a browser scrolling to the first of two
 * places with the same name: the rail still lands the reader in the right section, and nothing
 * about the document changes when it is edited elsewhere.
 *
 * `h-` PREFIXED because an id has to be usable as a CSS selector and a document heading is free
 * to start with a digit — a dated changelog entry is the ordinary case — while a CSS identifier
 * is not. */
function mdSlug(text){
  const flat = String(text == null ? "" : text)
    .toLowerCase()
    .replace(/[`*_]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/, "");
  return "h-" + (flat || "x");
}

/* `opts` rides to every inline pass and every nested block: `breaks`, `mdIds`' `{ host, tab, title }`, and `rel` (`mdRel`). */
function mdBlock(src, opts){
  const breaks = !!(opts && opts.breaks);
  const lines = String(src || "").replace(/\r\n?/g, "\n").split("\n");
  const out = [];
  let i = 0;

  const isTableSep = s => /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(s) && s.includes("-");
  const split = s => s.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map(c => c.trim());
  const cells = s => split(s).map(c => mdown(c, false, undefined, true, opts));
  /* THE SEPARATOR ROW CARRIES THE ALIGNMENT: `:-:` centres a column, `-:` sets it right, `:-` and
     `-` leave it where a table starts it. A class, not a `style=`, so the rule lives in the sheet. */
  const aligns = s => split(s).map(c => /^:.*:$/.test(c) ? "md-ac" : /:$/.test(c) ? "md-ar" : "");
  const cell = (tag, c, a) => `<${tag}${a ? ` class="${a}"` : ""}>${c}</${tag}>`;

  while (i < lines.length){
    const line = lines[i];

    /* Fenced code FIRST: everything inside a fence is literal, including things that look
       like every other construct here. A renderer that checked headings first would eat a
       `# comment` out of a shell block. */
    const fence = line.match(/^\s*```+\s*([A-Za-z0-9_+-]*)\s*$/);
    if (fence){
      const lang = fence[1] || "";
      const buf = [];
      i++;
      while (i < lines.length && !/^\s*```+\s*$/.test(lines[i])) buf.push(lines[i++]);
      i++; /* the closing fence, or the end of input — an unclosed fence still renders */
      out.push(`<pre class="md-pre"${lang ? ` data-lang="${esc(lang)}"` : ""}><code>${esc(buf.join("\n"))}</code></pre>`);
      continue;
    }

    if (/^\s*(---+|\*\*\*+|___+)\s*$/.test(line)){ out.push("<hr>"); i++; continue; }

    const head = line.match(/^\s*(#{1,6})\s+(.*)$/);
    if (head){
      const lv = Math.min(head[1].length + 1, 6); /* h1 in a doc becomes h2 on a page that has its own h1 */
      out.push(`<h${lv} class="md-h" id="${esc(mdSlug(head[2].trim()))}">${mdown(head[2].trim(), false, undefined, true, opts)}</h${lv}>`);
      i++; continue;
    }

    /* A table is a header row, a separator, then rows — the separator is what distinguishes
       it from a paragraph that happens to contain pipes. */
    if (line.includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1])){
      const head = cells(line);
      const al = aligns(lines[i + 1]);
      i += 2;
      const body = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) body.push(cells(lines[i++]));
      out.push(`<div class="md-tw"><table class="md-t"><thead><tr>${
        head.map((c, j) => cell("th", c, al[j])).join("")}</tr></thead><tbody>${
        body.map(r => `<tr>${r.map((c, j) => cell("td", c, al[j])).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }

    if (/^\s*>/.test(line)){
      const buf = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) buf.push(lines[i++].replace(/^\s*>\s?/, ""));
      out.push(`<blockquote class="md-q">${mdBlock(buf.join("\n"), opts)}</blockquote>`);
      continue;
    }

    /* Lists, with nesting by indentation. The whole run is consumed here rather than one
       item at a time, because an item's continuation lines belong to it. */
    const li = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
    if (li){
      const baseIndent = li[1].length;
      const ordered = /\d/.test(li[2]);
      const items = [];
      while (i < lines.length){
        const m = lines[i].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
        if (!m || m[1].length < baseIndent) break;
        /* A CHANGE OF MARKER KIND ENDS THE LIST: a numbered run after a bulleted one is a list of its own. */
        if (m[1].length === baseIndent && /\d/.test(m[2]) !== ordered) break;
        if (m[1].length > baseIndent){
          /* A deeper marker belongs to the item above: gather the whole nested run and
             recurse, so depth is handled by the same code rather than by a second parser. */
          const sub = [];
          while (i < lines.length && /^\s*([-*+]|\d+[.)])\s+/.test(lines[i]) &&
                 lines[i].match(/^(\s*)/)[1].length > baseIndent) sub.push(lines[i++]);
          if (items.length) items[items.length - 1].sub += "\n" + sub.join("\n");
          continue;
        }
        items.push({ text: m[3], sub: "" });
        i++;
        /* Continuation: an indented, non-marker, non-blank line under the current item.
           A FENCED BLOCK IS NOT CONTINUATION TEXT. Folding one into the item's sentence
           flattens the code AND leaks its ``` into the prose — and, worse, the closing fence
           then reads as an OPENING one, so everything after it in the document renders
           inside a code block that never ends. One command's output table vanished exactly
           that way. So a fence under an item is gathered whole and handed to the item's own
           sub-block, where the fence branch above renders it. */
        while (i < lines.length && lines[i].trim() && !/^\s*([-*+]|\d+[.)])\s+/.test(lines[i]) &&
               lines[i].match(/^(\s*)/)[1].length > baseIndent){
          if (/^\s*```/.test(lines[i])){
            const fbuf = [lines[i++]];
            while (i < lines.length && !/^\s*```+\s*$/.test(lines[i])) fbuf.push(lines[i++]);
            if (i < lines.length) fbuf.push(lines[i++]);
            items[items.length - 1].sub += "\n" + fbuf.join("\n");
            continue;
          }
          items[items.length - 1].text += " " + lines[i++].trim();
        }
        if (i < lines.length && !lines[i].trim()) {
          /* One blank line inside a list keeps the list; two end it. */
          const nx = i + 1 < lines.length ? lines[i + 1].match(/^(\s*)([-*+]|\d+[.)])\s+/) : null;
          if (nx && (nx[1].length !== baseIndent || /\d/.test(nx[2]) === ordered)) i++;
          else break;
        }
      }
      const tag = ordered ? "ol" : "ul";
      /* A TASK ITEM (`- [ ]`, `- [x]`) IS A CHECKBOX THE READER CANNOT TICK: this page shows a
         document, it does not edit one, so the box is `disabled` and the state is the author's. */
      const item = it => {
        const task = it.text.match(/^\[([ xX])\](?:\s+(.*))?$/);
        const text = mdown(task ? task[2] || "" : it.text, false, undefined, true, opts);
        const sub = it.sub.trim() ? mdBlock(it.sub, opts) : "";
        return task
          ? `<li class="md-task"><input type="checkbox" class="md-cb" disabled${task[1] === " " ? "" : " checked"}> ${text}${sub}</li>`
          : `<li>${text}${sub}</li>`;
      };
      const first = ordered ? parseInt(li[2], 10) : 1;
      out.push(`<${tag} class="md-l"${ordered && first !== 1 ? ` start="${first}"` : ""}>${items.map(item).join("")}</${tag}>`);
      continue;
    }

    if (!line.trim()){ i++; continue; }

    const buf = [];
    while (i < lines.length && lines[i].trim() &&
           !/^\s*(#{1,6}\s|>|```|---+\s*$|([-*+]|\d+[.)])\s)/.test(lines[i])) buf.push(lines[i++]);
    /* THE LOOP CANNOT STALL, and this line is the whole reason it cannot.
       The paragraph branch stops at anything a block branch above claims; if one of those
       regexes is ever narrower than this stop-set, a line matches here, is consumed by
       nothing, and `i` never moves — a hung tab, not a rendering bug. It has happened
       already: the heading branch was anchored at column 0 while this stop-set allowed
       leading whitespace, and one indented `## Bar` in the corpus spun the parser until the
       heap gave out. Aligning those two regexes fixed that instance; taking the line anyway
       when nothing else would is what stops the NEXT instance from being a hang. */
    if (!buf.length) buf.push(lines[i++]);
    out.push(`<p class="md-p">${breaks
      ? buf.map(one => mdown(one.trim(), false, undefined, true, opts)).join("<br>")
      : mdown(buf.join(" "), false, undefined, true, opts)}</p>`);
  }
  return out.join("\n");
}

/* ── 4-5. deps, commands ─────────────────────────────────────────────────── */

/* WHICH KINDS THE MAP DRAWS — route state, `deps:show=prd,slice`, so a filtered map is a link.
   No query is all three; an unknown kind is dropped; a query naming none of the three is all
   three again, because a map drawing nothing is not a view anybody asked for. */
function depsKinds(arg){
  const q = boardQuery(arg);
  const known = WAVE_KINDS.map(k => k[0]);
  const chosen = q.show === undefined ? known : q.show.split(",").filter(k => known.includes(k));
  return new Set(chosen.length ? chosen : known);
}
function depsRoute(kinds){
  const all = WAVE_KINDS.every(k => kinds.has(k[0]));
  return "deps" + (all ? "" : ":show=" + WAVE_KINDS.map(k => k[0]).filter(k => kinds.has(k)).join(","));
}

/* THE DEPENDENCIES PAGE'S FILTER BAR IN THE NEW UI. The state is rebuilt from the route on every paint (`DEPS_FB`); a
   tick navigates to the route that names the kinds, without scrolling the page back to the top. The shared bar always
   draws a search box unless the spec says `search: false`, and this page has nothing to search, so it says so rather than leave a
   control that does nothing. */
const DEPS_FB = { sel: {}, open: null };
let DEPS_SPEC = null;
function depsBar(kinds, of){
  const all = WAVE_KINDS.every(k => kinds.has(k[0]));
  DEPS_FB.sel = { kind: all ? [] : WAVE_KINDS.map(k => k[0]).filter(k => kinds.has(k)) };
  DEPS_SPEC = { search: false, dims: [{ key: "kind", label: "Kind", icon: "kind", multi: true, opts: WAVE_KINDS.map(([k, label]) => ({ id: k, label, count: of(k).length })) }] };
  tuFilterBarBind("deps", { state: () => DEPS_FB, spec: () => DEPS_SPEC, change: depsBarChange });
  return `<div role="group" aria-label="Kinds drawn">${tuFilterBar(DEPS_SPEC, DEPS_FB, "deps")}</div>`;
}
function depsBarChange(){
  const r = openRoute();
  if (r.split(":")[0] !== "deps"){ DEPS_FB.open = null; return; }
  const picked = new Set(DEPS_FB.sel.kind || []);
  const next = depsRoute(picked.size ? picked : new Set(WAVE_KINDS.map(k => k[0])));
  if (next === r){ render(r); return; }
  history.pushState({ r: next }, "", urlFor(next));
  render(next);
}

/* ── FLEET › DEPENDENCIES IN A REPOSITORY THAT PLANS BY AREAS (the approved dependencies mockup, screen 4; the owner's D3) ──────
 *
 * Inside one area the area page answers; what only this page can answer is the edges BETWEEN areas, and which of them are
 * stuck. So it opens on "Stuck across areas" (one group per pair of areas, worst first), with "All edges" and "Map" as
 * tabs. The edges, their areas, the stuck reading (D4) and the critical paths are the host's one read
 * (`GET /api/dependencies`, `depview.join` on the server); this file only draws them.
 *
 * THE MAP keeps the old build-step columns for the people who used them, grouped by AREA instead of by program, with
 * tasks and bugs as nodes (a blocked-by link holds start as a depends_on does) and no program node. A node waiting on an
 * item in another area is dashed. On a phone the map is not offered; the lists are.
 *
 * A repository that still plans by programs keeps the old page exactly (`viewDeps` below this is unchanged for it), and
 * so does the standalone board, which has no server to read.
 */
const ACROSS_TABS = [["", "Stuck across features"], ["all", "All edges"], ["map", "Map"]];
function acrossName(a, names){ return a ? (names[a] || a) : "no feature"; }
function acrossItem(r, extra){
  return link(r.route, "tu-dp-xi", `<b class="tu-mono">${esc(r.id)}</b>${extra || ""}<span class="tu-dp-xt">${esc(r.title || "")}</span>`);
}
/* ONE GROUP PER PAIR OF AREAS, in the server's order (worst first), so the group the worst edge is in comes first. */
function acrossGroups(edges){
  const groups = [];
  const at = {};
  edges.forEach(e => {
    const k = e.waiting.area + ">" + e.holder.area;
    if (!at[k]){ at[k] = { waiting: e.waiting.area, heldBy: e.holder.area, edges: [] }; groups.push(at[k]); }
    at[k].edges.push(e);
  });
  return groups;
}
function acrossWhy(e){
  if (e.stuck) return `<span class="tu-dp-why ${esc(e.stuck.code)}">${esc(e.stuck.why)}${Array.isArray(e.stuck.assignees) && e.stuck.assignees.length ? " &middot; " + e.stuck.assignees.map(w => esc(dpWho(w))).join(", ") : ""}</span><span class="tu-faint">${esc(e.holder.state || "")}</span>`;
  return `<span class="tu-dp-why moving">moving</span><span class="tu-faint">${esc(e.holder.state || "")}</span>`;
}
function acrossList(edges, names, only){
  const groups = acrossGroups(edges);
  if (!groups.length) return `<p class="tu-dp-none" data-across-empty>${only ? "Nothing is stuck between features." : "No item waits on an item in another feature."}</p>`;
  return groups.map(gr => {
    const stuck = gr.edges.filter(e => e.stuck);
    const critical = gr.edges.some(e => e.critical && e.stuck);
    const worst = stuck[0] ? stuck[0].stuck.why : "";
    const said = [`${gr.edges.length} edge${gr.edges.length === 1 ? "" : "s"}`, stuck.length ? (stuck.length === gr.edges.length && gr.edges.length > 1 ? "all stuck" : stuck.length === 1 && gr.edges.length === 1 ? "stuck · " + worst : `${stuck.length} stuck`) : "moving",
      critical ? "on a critical path" : ""].filter(Boolean).join(" &middot; ");
    const rows = gr.edges.map(e => `<div class="tu-dp-xrow${e.stuck ? " stuck" : ""}" data-across-edge="${esc(e.waiting.id)}<${esc(e.holder.id)}">` +
      `<div class="tu-dp-xw">${acrossItem(e.waiting, e.critical ? ` <span class="tu-dp-cp">Critical path</span>` : "")}</div>` +
      `<span class="tu-dp-xarr">&larr;<span class="w"> waits on</span></span>` +
      `<div class="tu-dp-xh">${acrossItem(e.holder, "")}</div>` +
      `<div class="tu-dp-xwhy">${acrossWhy(e)}</div></div>`).join("");
    return `<section class="tu-dp-xg" data-across-group="${esc(gr.waiting + ">" + gr.heldBy)}"><div class="tu-dp-xgh">` +
      `<b>${esc(acrossName(gr.waiting, names))}</b> waits on <b>${esc(acrossName(gr.heldBy, names))}</b>` +
      `<span class="tu-dp-xgs">${said}</span><span class="tu-grow"></span>${gr.waiting ? link("areas:" + gr.waiting, "tu-lnk", "Open " + esc(acrossName(gr.waiting, names)) + " &rsaquo;") : ""}</div>` +
      `<div class="tu-dp-xhead"><span>Waits</span><span></span><span>On</span><span>${only ? "Why stuck" : "Where it stands"}</span></div>${rows}</section>`;
  }).join("");
}
/* THE MAP: every item on an edge, in build steps (nothing open before it is Now), grouped by area inside each step. */
function acrossMap(edges, names){
  const nodes = {}, up = {};
  edges.forEach(e => {
    [e.waiting, e.holder].forEach(r => { if (!nodes[r.route]){ nodes[r.route] = r; up[r.route] = new Set(); } });
    up[e.waiting.route].add(e.holder.route);
  });
  const lv = {}, stack = new Set();
  const step = id => {
    if (lv[id] !== undefined) return lv[id];
    if (stack.has(id)) return 0;
    stack.add(id);
    let best = 0;
    up[id].forEach(p => { best = Math.max(best, 1 + step(p)); });
    stack.delete(id);
    lv[id] = best;
    return best;
  };
  Object.keys(nodes).forEach(step);
  const holds = {}, waits = {}, foreign = {}, crossN = {};
  edges.forEach(e => {
    holds[e.holder.route] = (holds[e.holder.route] || 0) + 1;
    waits[e.waiting.route] = (waits[e.waiting.route] || 0) + 1;
    if (e.cross){
      (foreign[e.waiting.route] = foreign[e.waiting.route] || new Set()).add(e.holder.area);
      crossN[e.waiting.route] = (crossN[e.waiting.route] || 0) + 1;
    }
  });
  const levels = [...new Set(Object.values(lv))].sort((a, b) => a - b);
  const cols = levels.map(w => {
    const ids = Object.keys(nodes).filter(id => lv[id] === w);
    const areas = [...new Set(ids.map(id => nodes[id].area))].sort((a, b) => acrossName(a, names).localeCompare(acrossName(b, names)));
    const inner = areas.map(a => `<div class="tu-dp-marea"><div class="tu-dp-mah">${esc(acrossName(a, names))}</div>${ids.filter(id => nodes[id].area === a).sort().map(id => {
      const r = nodes[id];
      const far = foreign[id] ? [...foreign[id]].map(x => acrossName(x, names)).join(", ") : "";
      return link(r.route, `wnode tu-dp-mnode${far ? " foreign" : ""}`, `<div class="wi"><span class="wk">${esc(r.kind === "prd" ? "PRD" : r.kind)}</span> ${esc(r.id)}${r.slice ? ` &middot; ${esc(r.slice)}` : ""}</div>` +
        `<div class="wn">${esc(r.title || "")}</div><div class="we">${waits[id] ? `<span class="up">waits on ${waits[id]}${far ? (crossN[id] === waits[id] ? "" : " &middot; " + crossN[id]) + " in " + esc(far) : ""}</span>` : ""}${
          holds[id] ? `<span class="down">holds ${holds[id]}</span>` : ""}</div>`, ` data-across-node="${esc(r.id)}"`);
    }).join("")}</div>`).join("");
    return `<div class="wave"><h4>${w === 0 ? "Now" : "Then " + w} &middot; ${ids.length}</h4><div class="inner">${inner}</div></div>`;
  });
  return `<div class="tu-dp-mapwrap" data-across-map><p class="tu-dp-mapphone">The map needs a wider screen. ${link("deps", "tu-lnk", "Stuck across features")}</p><p class="tu-sm tu-muted">The build steps of every item on an edge, grouped by feature. A node waiting on another feature is dashed.</p>` +
    `<div class="waves">${cols.join("")}</div></div>`;
}
function viewDepsAcross(arg, d){
  const tab = arg === "all" || arg === "map" ? arg : "";
  const names = {};
  (d.areas || []).forEach(a => { names[a.area] = a.name || a.area; });
  const edges = Array.isArray(d.edges) ? d.edges : [];
  const cross = edges.filter(e => e.cross);
  const stuck = cross.filter(e => e.stuck);
  const counts = { "": stuck.length, all: cross.length, map: null };
  /* The Map's tab carries its own class: the phone block hides it, since the map is not offered on a phone. */
  const tabs = `<nav class="tu-tabs tu-dp-xtabs">${ACROSS_TABS.map(([id, label]) => {
    const inner = `${esc(label)}${counts[id] != null ? ` <span class="tu-n">${counts[id]}</span>` : ""}`;
    const attrs = ` aria-pressed="${tab === id}" data-across-tab="${id || "stuck"}"`;
    return id === "map" ? link("deps:map", "tu-dp-xtab tu-dp-maptab", inner, attrs) : link(id ? "deps:" + id : "deps", "tu-dp-xtab", inner, attrs);
  }).join("")}</nav>`;
  const moving = cross.length - stuck.length;
  const body = tab === "map" ? acrossMap(edges, names)
    : tab === "all" ? acrossList(cross, names, false)
    : acrossList(stuck, names, true) + (moving ? `<p class="tu-sm tu-muted" data-across-moving>${moving} more edge${moving === 1 ? "" : "s"} across features ${moving === 1 ? "is" : "are"} moving. ${link("deps:all", "tu-lnk", "Show all edges")}</p>` : "");
  const after = Number(d.stuckAfterDays) || 3;
  return pageHead("Dependencies", "What waits on what between features, and what is stuck.") +
    `<div class="strip" data-across-stats>
      <div class="stat${stuck.length ? " attn" : ""}"><b>${stuck.length}</b><span>stuck across features</span></div>
      <div class="stat"><b>${cross.length}</b><span>edges across features</span></div>
      <div class="stat"><b>${Number(d.waiting) || 0}</b><span>open items waiting</span></div>
      <div class="stat"><b>${Number(d.longest) || 0}</b><span>steps on the longest chain</span></div>
    </div>${tabs}<div class="tu-dp-across" data-across="${tab || "stuck"}">${body}</div>
    <p class="tu-sm tu-faint">An edge is stuck when what it waits on waits on a person, is parked or failed, or has not moved for ${after} day${after === 1 ? "" : "s"}.${
      d.issuesRead === false ? " No tracker issues reach this repository, so only PRD depends_on edges are shown." : ""}</p>`;
}

function viewDeps(arg){
  /* WHERE THE HOST CAN READ THE EDGES BETWEEN AREAS (`TU_HOST.depsAcross`, the server's `GET /api/dependencies`),
     the page is the across-areas one above; the standalone board, and a reading with no features, keep the
     build-step map below. While the read is in flight the page says so rather than drawing the other one first. */
  const across = TU_HOST && typeof TU_HOST.depsAcross === "function" ? TU_HOST.depsAcross() : null;
  if (across && across.phase === "loading") return pageHead("Dependencies") + `<p class="tu-sm tu-muted" data-across-loading>Reading what waits on what&hellip;</p>`;
  if (across && across.data && Array.isArray(across.data.areas) && across.data.areas.length) return viewDepsAcross(arg, across.data);
  /* THE SAME NOTHING THE PROGRAMS LIST SAYS, for the same corpus. A graph drawn over no cuts is
     one empty wave under four zeros, which reads as a plan whose dependencies nobody recorded —
     a different fact from a plan that is not there. */
  if (noPlan()) return pageHead("Dependencies") + noPlanNote();
  const g = waveG();
  const kinds = depsKinds(arg);
  const all = Object.values(g.nodes);
  const of = k => all.filter(n => n.kind === k);
  const prds = of("prd");
  const waiting = prds.filter(n => g.up[n.id].size).length;
  const max = all.reduce((m, n) => Math.max(m, n.x.wave), -1);
  /* THE KIND CHIPS: each one a link to the map with that kind toggled, so the choice is a route
     and a shared link carries it. The last kind drawn cannot be switched off — its chip links to
     the map it is already on. */
  const chips = WAVE_KINDS.map(([k, label]) => {
    const on = kinds.has(k);
    const next = new Set(kinds);
    if (on && kinds.size > 1) next.delete(k); else next.add(k);
    return link(depsRoute(next), `wkf k-${k}${on ? " on" : ""}`,
      `${esc(label)} <b>${of(k).length}</b>`, ` aria-pressed="${on}"`);
  }).join("");
  /* THE NEW UI'S FILTER BAR (`tuFilterBar`): the same choice as a dashed "Kind" button over a checklist with each
     kind's count, a solid chip naming the kinds once the map is narrowed, and Clear all. Nothing chosen IS every kind,
     which is the route with no `show=`; the last kind unticked therefore returns to every kind, as the last chip could
     never be switched off. The choice is still the route, so a narrowed map is still a link. */
  const bar = tuOn() && typeof tuFilterBar === "function" ? depsBar(kinds, of) : "";
  /* BOTH EDGE COUNTS, ON EVERY NODE, WITHOUT TOUCHING ANYTHING (`waveNode`). Lighting the chain
     shows the TRANSITIVE closure of two numbers already on the screen; nothing has to say it is
     available. A kind switched off is not drawn, but the chain still runs through it — a PRD's
     prerequisites light whether or not the slice between them is on the page. */
  const cols = waveColumns(g, all.filter(n => kinds.has(n.kind)).map(n => n.id));
  return pageHead("Dependencies") +
    /* THE SET, AS COUNTS. The steps are PRD `depends_on` chains: a PRD waits on the open PRDs it
       names, a slice on its open PRDs, a program on its open slices and its proof. Shipped work is
       met and not drawn. */
    `<div class="strip">
      <div class="stat"><b>${prds.length}</b><span>open PRDs</span></div>
      <div class="stat${waiting ? " attn" : ""}"><b>${waiting}</b><span>wait on another open PRD</span></div>
      <div class="stat"><b>${max + 1}</b><span>build steps deep</span></div>
      <div class="stat"><b>${of("slice").length}</b><span>slices still in play</span></div>
      <div class="stat"><b>${D.totals.slices - of("slice").length}</b><span>${STATE.complete} or parked, not drawn</span></div>
    </div>
    ${bar || `<div class="wkfs" role="group" aria-label="Kinds drawn">${chips}</div>`}
    ${waveLegend()}
    <div class="waves" id="waves">${cols.join("")}</div>`;
}

/* `viewHealth` STOOD HERE and the operator asked for the whole page off. Its
   nav entry, its route and its render code went together; `D.health` and `D.baselines` are
   still in the payload this file is handed, and nothing renders them. */

/* A LIST ROW'S MARKS — ICONS, NOT SENTENCES. A clipped sentence in a pill was the widest thing on a
   row and said least; each fact is a glyph (and a count where there is one), and the sentence rides
   `data-tip` on hover. The table lives HERE and not in the host because this file draws rows too
   (the Agents list) and the standalone board loads nothing else; the host's Queue, Fleet and
   Workstation rows read the same table through `Board.icons` and `Board.mark`, so one glyph means
   one thing on every list. A mark with no icon is its count alone (`+3`). */
const ICON = {
  decision: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6.2 6.3a1.9 1.9 0 1 1 2.6 1.75c-.5.22-.8.6-.8 1.1v.35" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="11.4" r=".85" fill="currentColor"/></svg>',
  action: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="5.2" r="2.6" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2.9 14c.4-2.7 2.5-4.4 5.1-4.4s4.7 1.7 5.1 4.4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  blockedBy: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M3.6 12.4 12.4 3.6" stroke="currentColor" stroke-width="1.5"/></svg>',
  blocking: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 14.5V2.2m0 .6h8.2l-1.9 3.1 1.9 3.1H3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>',
  tries: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13 8a5 5 0 1 1-1.5-3.55M11.8 1.9v2.8H9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  reason: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 7.2v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="4.9" r=".85" fill="currentColor"/></svg>',
  /* The Runs row's second pass at work whose verdict already stood (`runRow`). */
  repeat: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.8 7a5 5 0 0 1 8.9-2.6M13.2 9a5 5 0 0 1-8.9 2.6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M11.9 1.9v2.7H9.2M4.1 14.1v-2.7h2.7" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  /* The Workstation row's marks (`wsMarks`): a countdown, a look, the machine, the pane, a loss. */
  clock: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 4.6V8l2.4 1.6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  eye: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.6 8s2.4-4.4 6.4-4.4S14.4 8 14.4 8s-2.4 4.4-6.4 4.4S1.6 8 1.6 8z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><circle cx="8" cy="8" r="1.8" fill="currentColor"/></svg>',
  box: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="2.2" y="3" width="11.6" height="4.2" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="2.2" y="8.8" width="11.6" height="4.2" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="4.9" cy="5.1" r=".8" fill="currentColor"/><circle cx="4.9" cy="10.9" r=".8" fill="currentColor"/></svg>',
  pane: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.8" y="2.6" width="12.4" height="10.8" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M4.6 6.4 6.6 8l-2 1.6M8.2 10.2h3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  lost: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.8" y="2.6" width="12.4" height="10.8" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="m5.6 5.6 4.8 4.8m0-4.8-4.8 4.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',

  /* The Agents row's: a reference the prompt names and the repository does not hold. */
  broken: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M7.3 4.7 8.7 3.3a2.5 2.5 0 0 1 3.5 3.5l-1.4 1.4M8.7 11.3l-1.4 1.4a2.5 2.5 0 0 1-3.5-3.5l1.4-1.4M2.6 2.6l10.8 10.8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};
function mark(icon, tone, tip, label, count){
  return `<span class="qm${tone ? " " + tone : ""}" tabindex="0" role="img" aria-label="${esc(label)}" data-tip="${esc(tip)}">${icon ? ICON[icon] : ""}${
    count ? `<b>${count}</b>` : ""}</span>`;
}

/* THE AGENTS PAGES, DERIVED — one repository at a time, and the index that compares them.
 *
 * WHAT THIS PAGE IS CALLED AND WHAT THE CODE CALLS IT ARE DELIBERATELY DIFFERENT, and nobody
 * should "fix" the divergence. A `.claude/commands/**` file is a PROMPT that a whole agent runs
 * — it declares a spine, gates, an actor per step and whether it may run headless — so the word
 * on the page is AGENT. The route is still `commands`, the detail route is still `command:`, the
 * payload block is still `commandTree`, the API is still `/api/commands/body`, and the directory
 * on disk is still `.claude/commands/`. Renaming any of those would be a wire change, a stored
 * shape change and a broken bookmark bought for a noun; renaming the noun a reader sees costs
 * nothing and is the only half that was ever wrong. The `/<ns>:*` strings stay exactly as they
 * are — that IS how an agent is invoked.
 *
 * THE HAND-WRITTEN CATALOGUE IS GONE. `legacyCatalogue()` stood at the foot of this page and
 * rendered `D.commands` — a prose list of what each command is FOR, authored in the deployment's
 * guidance ConfigMap and cross-checked against the tree. The operator's decision is that the
 * prose belongs in the repository, beside the agent it describes, where the spine's `intent`
 * already carries it. What that list said and the tree cannot is recorded in the report rather
 * than smuggled back in: `how` — typed / a board row starts it / the fleet dispatches it — was
 * three facts per command that ONLY the catalogue held. The tree can say what a command NEEDS
 * from a person and whether it MAY MERGE its own work, and both are shown; it cannot say the
 * other two, and nothing here invents them.
 */
/* AN EMPTY TREE IS `{}` AND `{}` IS TRUTHY, which is the whole reason this is not a one-liner.
   `store/board.command_tree` answers `{}` — deliberately, and it says why — for a repository
   with no command directory at all, so `(D && D.commandTree) || null` handed every reader below
   an object whose `commands` is `undefined` and the first `.length` threw. `null` is the one
   answer every branch here already knows how to render. */
function cmdTree(){ return treeOf(D); }

/* WHAT A COMMAND NEEDS FROM A PERSON, as one chip. `nothing` earns no chip: the absence of a
   demand is not news, and a chip on every row is a chip nobody reads. `answers` and `a decision`
   are the two the reader is scanning for, and they are different enough to colour apart — the
   fleet dispatches the first and refuses the second. An empty string is a command with no spine,
   which `no spine` already says beside it. */
/* THE SAME TWO FACTS ARE A MARK ON THE AGENTS LIST'S ROW (`needsMark`) — a glyph in the chip's tone,
   the chip's word as its label and its sentence as its tip — so the two spell them from one table. */
const NEEDS = {
  answers: { word: "asks", tone: "flight", icon: "decision",
    tip: "declares needs: answers — it stops and interviews; the fleet still dispatches it and it asks by writing" },
  "a decision": { word: "needs a person", tone: "unproven", icon: "action",
    tip: "declares needs: a decision — it cannot proceed without a human ruling, so the fleet never runs it unattended" },
};
function needsChip(c){
  const n = NEEDS[c.needs];
  return n ? `<span class="chip ${n.tone}" title="${esc(n.tip)}">${n.word}</span>` : "";
}
function needsMark(c){
  const n = NEEDS[c.needs];
  return n ? mark(n.icon, n.tone === "unproven" ? "brass" : n.tone, n.tip, n.word) : "";
}
function needsSentence(needs){
  if (needs === "nothing") return "nothing — it can finish unattended";
  if (needs === "answers") return "answers — it stops and interviews, at a terminal or by writing";
  if (needs === "a decision") return "a decision — it cannot proceed without a human ruling";
  return needs;
}
function treeOf(payload){
  const t = payload && payload.commandTree;
  return t && Array.isArray(t.commands) ? t : null;
}
function cmdById(id){ const t = cmdTree(); return t ? t.commands.find(c => c.id === id) : null; }
function slotById(id){ const t = cmdTree(); return t ? t.slots.find(x => x.id === id) : null; }

/* THE ROUTE FOR AN AGENT A HOST PAGE NAMES IN PROSE, or `null` when this repository carries no
   such agent — which is `term()`'s rule, one register over.

   A host page that argues about the work (what runs alone, what stops and asks, what may merge)
   names agents by the string a person types: `prd:implement`, `check`, `verify`. The only file
   that can answer *"does this repository carry that one"* is this one — the tree rides in the
   board payload and nothing exports it — so the host asks here rather than guessing, and a name
   the tree does not hold comes back `null` so the caller can render PLAIN TEXT. That half is the
   point: a link to an agent page that renders "no such agent" teaches a reader that none of the
   links on the page work, which is the failure `term()` already refuses for a word the glossary
   does not define.

   THE NAME IS NOT THE ID, and both are tried. `prd:implement` is what a reader types and what
   `commands.py` derives from the file's path; `prd-implement` is the route slug, which that same
   module mints from the spine's own `command:` when there is one and from the name otherwise. So
   the name is matched first and the dashed form second — the conversion `viewCommand`'s own
   cross-references already make, made once here instead of at every call site.

   IT RETURNS A ROUTE AND NOT A LINK on purpose: this package has no opinion about what a host's
   page looks like, and handing back markup would give it one. `Board.link` is exported beside
   this, and the caller pairs the two with its own class. */
function agentRoute(name){
  const t = cmdTree();
  if (!t) return null;
  const want = String(name == null ? "" : name);
  const c = t.commands.find(x => x.name === want) || t.commands.find(x => x.id === want.replace(/:/g, "-"));
  return c ? "command:" + c.id : null;
}

/* HOW AN AGENT IS TYPED, read off WHERE ITS FILE LIVES. `commands.namespace_of` is this
   package's own rule — *"a repository says what its commands are called by saying where they
   live, and nothing has to be configured twice"* — so `.claude/commands/<ns>` + `prd:create`
   is `/<ns>:prd:create`, and the same arithmetic answers for any tree. A constant here would
   be right in one repository and silently wrong in the next, which is the whole reason the rule
   is the directory's basename rather than a setting. */
function cmdNamespace(t){
  const dir = (t && t.scan && t.scan.directory) || "";
  return dir.replace(/\/+$/, "").split("/").pop() || "";
}
function cmdInvocation(t, c){
  const ns = cmdNamespace(t);
  return "/" + (ns ? ns + ":" : "") + c.name;
}

/* Every path any agent in this tree POINTS AT. The doc route serves exactly this set and
   nothing else (`api/pagedata.doc`: the allowlist is the corpus's citations, not the
   filesystem's layout), so it is also the set this page may draw as a link — a chip linking to
   a path nothing cites is a link to a 404, and a page full of those teaches the reader that
   none of them work. */
function citedPaths(t){
  const out = new Set();
  (t ? t.commands : []).forEach(c => c.references.forEach(r => {
    if (r.kind === "doc" && r.resolves) out.add(r.target);
  }));
  return out;
}

/* ── which repositories exist, and which one is on screen ─────────────────── */

function corpusRows(){ return (CORPORA && CORPORA.corpora) || []; }

/* THE KEY `?repo=` TAKES FOR THIS CORPUS, or `null` when it cannot be named at all.

   THE LANE A CORPUS ANSWERS FOR, when the server says which. `answersLane` is the primary's
   default lane when it was configured without one, its own lane otherwise, and `""` for a
   secondary that was configured without a lane and so answers for nothing — that corpus is
   genuinely unreachable (`api/entities.corpora` says so in as many words); it is listed and
   marked, never back-filled with a guess. A primary that somehow answers for nothing is still
   the primary and is still reachable by asking for nothing, so it keeps `""` rather than `null`.

   A SERVER THAT PREDATES THE FIELD gets the older rule: the primary is addressed by asking for
   NOTHING — that is what `api/deps._read` does with no `repo` — so its key is `""` whether or not
   it carries a lane, and a secondary's is its lane.

   AND ONE CORPUS ALONE IS ADDRESSED BY ASKING FOR NOTHING WHATEVER THE SERVER SAYS. A name is
   only needed where there is a choice; a deployment serving a single corpus has none, and giving
   its primary a name would put `?repo=` on every read, `zb.repo` in storage and a lane in the
   URL of a page whose reader can go nowhere else. So the one-corpus deployment stays exactly the
   page it was, and `REPO` means the primary there without ever waiting for the list. */
function keyOf(c){
  if (c.primary && !manyRepos()) return "";
  if (typeof c.answersLane === "string") return c.answersLane || (c.primary ? "" : null);
  return c.primary ? "" : (c.lane || null);
}

/* THE PRIMARY'S KEY, as the list in hand spells it: `""` until the list lands (and for good on a
   server that cannot name the primary, or a deployment with nothing to tell it from), its lane
   name once a second corpus makes the name necessary. Every `""` the page holds for "the
   primary" is normalised through this, so that `REPO`, a `repo:` route with an empty argument
   and the selector's current mark all resolve to the same spelling at the same moment. */
function primaryKey(){
  const p = corpusRows().find(c => c.primary);
  const k = p ? keyOf(p) : null;
  return k === null ? "" : k;
}
function isPrimary(key){ return key === "" || key === primaryKey(); }

/* The name a person calls this repository. The lane it answers for, because that is the name
   `repo:*` labels and dispatch already use and the one `?repo=` takes — the primary answers for
   the default lane even when configured without one, and calling it by its URL's last segment
   would have the selector say `harbour` where every issue, label and query string says
   `primary`. The configured lane next, for a server that predates `answersLane`; the
   repository's own last path segment only when it answers for nothing at all. */
function repoName(c){
  if (!c) return "";
  if (c.answersLane) return c.answersLane;
  if (c.lane) return c.lane;
  const url = String((c.source && c.source.url) || "");
  return url.replace(/\.git$/, "").replace(/\/+$/, "").split(/[/:]/).pop() || url;
}

function corpusFor(key){
  const k = String(key || "").trim().toLowerCase();
  /* ONE CORPUS ANSWERS TO ITS OWN NAME TOO (ENG-10706): its key is `""` where there is nothing to
     choose, so `?repo=primary` on a single-corpus deployment used to be refused as a repository it does
     not serve — the one link to it that is certainly right. */
  return corpusRows().find(c => keyOf(c) === k || (c.primary && !manyRepos() && k && repoName(c) === k)) ||
    /* A NAME THE LANE HAD BEFORE A RENAME IS STILL ITS NAME. `formerNames` is what the lane was
       called before Settings › Repositories renamed it; a bookmark, a shared link or a stored
       choice made before the rename names one of them, and it was refused as a repository nobody
       serves on a customer install. Checked after every current name, so a name a live lane holds
       wins over one another lane gave up. */
    (k ? corpusRows().find(c => formerOf(c, k)) : null) || null;
}
/* THE KEY A NAME MEANS TODAY: a former name folded onto the lane it became, anything else as it
   was written (the caller refuses or honours it). */
function repoKeyFor(name){
  const c = name ? corpusFor(name) : null;
  const k = c ? keyOf(c) : null;
  return k === null ? name : k;
}
/* Is `key` a name corpus `c`'s lane was renamed away from? */
function formerOf(c, key){
  return Array.isArray(c.formerNames) && c.formerNames.some(n => String(n).toLowerCase() === key);
}

/* IS THERE ANYTHING TO CHOOSE BETWEEN? One configured corpus is the ordinary deployment and the
   standalone file both, and an index of one row is a click that tells the reader nothing they
   did not already know. So the Agents tab lands on the repository itself, and the index — and
   the selector in the crumb row — appear only when there is a second repository to compare. */
function manyRepos(){ return corpusRows().length > 1; }

/* ── where the choice lives when the page is not on screen ─────────────────
 *
 * THE REPOSITORY IS CHOSEN ONCE AND IT HAS TO SURVIVE THE READER LEAVING. Three places hold it,
 * in the order they win: the page URL (`?repo=<lane>`, so a reload, a bookmark and a shared link
 * all land on the repository the sender was looking at), `zb.repo` in storage (so a reader who
 * arrives with no `?repo=` at all lands where they last were), and the primary (the answer when
 * neither has been written). `askedRepo` reads the first two; `start` resolves what they name
 * against the list and falls to the primary, out loud, when they name nothing served.
 *
 * ONLY WHERE THERE IS A CHOICE. `urlFor` writes `?repo=` and `persistRepo` writes `zb.repo`
 * exclusively when a second corpus is listed — the same `manyRepos()` gate that hides the
 * selector — so a single-corpus deployment and the standalone page never see a query string
 * appear on their URL or a key appear in their storage. A `?repo=` a reader carried in by hand
 * on such a page is refused by name rather than honoured, and nothing writes it back.
 *
 * THE HASH IS THE ROUTE AND THE QUERY IS THE REPOSITORY, and every navigation writes BOTH.
 * The obvious economy — push `"#" + route` and let fragment resolution keep the query — leans on
 * the page's base URL being the document itself, which is true only while nothing sets a base
 * element (the shell once did, and a fragment then resolved with no query at all). So `urlFor`
 * spells the path, the query and the hash out in full wherever there is a second corpus, and `"#" + route` where there is not, which is the
 * one-corpus page's URL untouched. The page owns `repo` and nothing else in the query; a
 * parameter somebody else put there is carried along from the moment the list has landed, and
 * before that moment the first `enter` writes the bare fragment it always wrote — which is why
 * `askedRepo` is read before it, and why nothing else in the query is promised to survive
 * boot. */
function urlRepo(){
  /* WHATEVER ITS CASE (ENG-10706): a lane name is lower-case by construction, so `?repo=FLEET` in a
     pasted link can only mean `fleet` — it was refused as a repository nobody serves. */
  try { return (new URLSearchParams(location.search).get("repo") || "").trim().toLowerCase(); } catch { return ""; }
}
function askedRepo(){ return urlRepo() || store.get("zb.repo", "") || null; }
function urlFor(r, repo){
  if (!manyRepos()) return "#" + r;
  let q;
  try { q = new URLSearchParams(location.search); } catch { return "#" + r; }
  const about = repo || REPO;
  if (about) q.set("repo", about); else q.delete("repo");
  const s = q.toString();
  return location.pathname + (s ? "?" + s : "") + "#" + r;
}
/* The entry on screen, re-addressed to the repository on screen — never a new entry. */
function syncUrl(){
  const r = openRoute();
  history.replaceState({ r }, "", urlFor(r));
}
function persistRepo(){ if (manyRepos() && REPO) store.set("zb.repo", REPO); }
/* A STORED CHOICE MADE UNDER WHAT ITS LANE WAS CALLED BEFORE A RENAME is dropped, and nothing is
   said: it was right when it was made and it still reaches the same lane. `persistRepo` writes the
   current name back where there is a choice; the address is `syncUrl`'s, which writes `?repo=`
   from `REPO` — the current name — on the same pass. */
function renamedFrom(former){
  if (store.get("zb.repo", "") === former) try { localStorage.removeItem("zb.repo"); } catch { /* storage unavailable: nothing was kept */ }
}
function notifyRepo(){ REPO_HOOKS.forEach(fn => fn()); }

/* EVERYTHING A HOST'S SELECTOR NEEDS, IN ONE READ, so that the masthead's control and the crumb
   row's dropdown are two paintings of one state rather than two states. `rows` carries each
   corpus already keyed and named through the same two functions the crumb row uses; a host that
   re-derived either would be a second opinion about which name a repository answers to. */
function repoState(){
  return {
    key: REPO,
    many: manyRepos(),
    listed: CORPORA !== null,
    listErr: CORPORA_ERR,
    rows: corpusRows().map(c => ({
      key: keyOf(c), name: repoName(c), synced: !!c.synced, primary: !!c.primary,
    })),
    busy: SWITCH_BUSY,
    err: SWITCH_ERR,
    failed: SWITCH_FAILED,
    refused: REPO_REFUSED,
  };
}

/* One repository's command tree, and the state of getting it. The reader's OWN repository is
   already in `D` and is never fetched a second time for this. */
/* THE READER'S OWN REPOSITORY IS ALWAYS `ready`, WITH OR WITHOUT A TREE. Having read it and
   finding no agents is a FINDING (`repoFacts` calls it `none`); not having read it yet is a
   blank cell. Folding the two would report a repository with no agent tree as one nobody has
   got round to reading, which is the opposite of the thing this index exists to show. */
function treeState(key){
  if (key === REPO) return { state: "ready", tree: cmdTree(), err: null };
  return REPO_TREES[key] || { state: "idle", tree: null, err: null };
}

/* WHAT THE INDEX NEEDS AND `/api/corpora` DOES NOT CARRY. The corpora route answers identity,
   configuration and head — it says nothing about agents, because agents are in the board. So the
   index reads one board per repository, once per session, and every one of them is an ETagged
   read of a single commit: a revisit costs a 304 and no body.

   MARKED BEFORE THE FETCH, NEVER AFTER. `render` calls this on every paint of the index; a flag
   set on the way back would let the second paint fire a second fetch, and the two would chase
   each other for as long as the page was open. */
function wantRepoTrees(){
  if (!REPO_BOARD_LOADER) return;
  corpusRows().forEach(c => {
    const key = keyOf(c);
    if (key === null || key === REPO || !c.synced || REPO_TREES[key]) return;
    REPO_TREES[key] = { state: "loading", tree: null, err: null };
    REPO_BOARD_LOADER(key).then(
      payload => {
        REPO_TREES[key] = { state: "ready", tree: treeOf(payload), err: null };
        if (onAgentsList()) render(openRoute());
      },
      err => {
        REPO_TREES[key] = { state: "failed", tree: null, err: (err && err.message) || String(err) };
        if (onAgentsList()) render(openRoute());
      });
  });
}

/* THE FOUR NUMBERS A ROW IS COMPARED ON, or nulls when this repository has not been read. */
function repoFacts(key){
  const held = treeState(key);
  if (held.state !== "ready") return { state: held.state, err: held.err };
  const t = held.tree;
  const agents = t ? t.commands.length : 0;
  return {
    state: agents ? "ready" : "none",
    err: null,
    agents,
    spined: t ? t.commands.filter(c => c.hasSpine).length : 0,
    broken: t ? t.commands.reduce((n, c) => n + c.references.filter(r => !r.resolves).length, 0) : 0,
    filled: t ? t.slots.filter(s => s.filled).length : 0,
    slots: t ? t.slots.length : 0,
    registry: !!(t && t.registry),
  };
}

/* WORST FIRST, and "worst" is ranked rather than scored so the order is explicable. 0 is
   nothing to read at all, 1 is a tree with a finding in it, 3 is a tree with none — and 2 is
   RESERVED FOR A READING STILL IN FLIGHT, so a row that lands settles by at most one place
   instead of jumping the length of the list under the reader's eye. */
function repoTier(key, row){
  if (!row.synced) return 0;
  const f = repoFacts(key);
  if (f.state === "failed" || f.state === "none") return 0;
  if (f.state !== "ready") return 2;
  if (!f.registry || f.broken || f.filled < f.slots || f.spined < f.agents) return 1;
  return 3;
}

/* ── the index: every repository this deployment serves ───────────────────── */

/* ONE GROUP OF A LIST PAGE'S CARD, drawn as the host's Queue, Fleet and Ideas lists draw one: a
   header naming the group, its dot, its count and a hint, over its rows. `attr` names the group's
   family on the page (`data-<attr>` on the section and the dot, `data-<attr>-g` on the header the
   click handler reads), so the Programs list and the Agents list keep their own fold state and
   their own dot vocabulary through one markup. The dot is the group's STATE and not its name, so
   it is passed separately; `tip` is the hint in full where the hint is clipped. */
function listGroup(attr, key, o){
  const a = esc(attr), k = esc(key);
  return `<section class="qg" data-${a}="${k}">
    <button class="qg-h" type="button" data-${a}-g="${k}" data-keep="${a}:${k}" aria-expanded="${o.open}"${
      o.tip ? ` data-tip="${esc(o.tip)}"` : ""}><span class="tri"></span><i class="qg-i" data-${a}="${esc(o.dot)}"></i><span class="qg-n">${esc(o.name)}</span><span class="n">${o.count}</span>${
      o.hint ? `<span class="qg-hint">${esc(o.hint)}</span>` : ""}</button>${
    o.open ? `<div class="qg-rows">${o.rows}</div>` : ""}</section>`;
}

/* WHICH AGENTS-PAGE GROUPS A READER CLOSED — module state and not DOM, for `BOARD_SHUT`'s reason:
   the page repaints on every keystroke in the search box and on every corpus read. A search opens
   every group it has a match in, the Queue's rule: the reader asked to see the matches. */
let AG_SHUT = {};
function agGroup(key, o){
  return listGroup("ag", key, Object.assign({ open: !AG_SHUT[key] || !!CMD_Q.trim() }, o));
}

/* ONE REPOSITORY ON THE LIST'S LINE: its name, what state its reading is in, where it lives and
   the sentence a state carries, its three figures, and the one act. The figures are the row's
   marks — a number each, its word the tip — so the row reads across as every other list's does. */
function repoFigure(value, label, tone){
  return mark("", tone, label, `${value} ${label}`, value);
}

function repoIndexRow(c, key){
  const name = repoName(c);
  const f = repoFacts(key);
  const src = String((c.source && c.source.url) || "").replace(/^https?:\/\/[^/]+\//, "").replace(/\.git$/, "");

  /* A REPOSITORY THAT CANNOT BE NAMED IS NOT A LINK. `?repo=` matches on the lane and this one
     has none, so there is no request that would fetch its board — and a row that navigated
     anyway would land on the repository the reader was already reading. */
  const unreachable = key === null;
  const figs = f.state === "ready"
    ? repoFigure(f.agents, "agents", "") +
      repoFigure(`${f.spined}/${f.agents}`, "spined", f.spined < f.agents ? "brass" : "") +
      repoFigure(`${f.filled}/${f.slots}`, "slots filled", !f.slots || !f.filled ? "attn" : f.filled < f.slots ? "brass" : "")
    : f.state === "none"
    ? repoFigure(`${f.filled}/${f.slots}`, "slots filled", f.filled ? "brass" : "attn")
    : "";

  /* THE FOUR STATES THAT CANNOT BE ACTED ON, each a word in the status slot and its sentence in
     the text slot after the repository's path: a repository nothing has ever read, one nothing
     can name, one whose board refused, and one that has no agents to compare. The sentence is
     clipped to the line and whole in its tip. */
  const [word, tone, say] = !c.synced
    ? ["never synced", "attn", "Configured here, and no sync has ever produced a reading of it — so nothing can say what it holds."]
    : unreachable
    ? ["no lane", "attn", "This corpus is configured without a lane, and a lane is the name ?repo= takes. Its board cannot be asked for."]
    : f.state === "failed"
    ? ["could not be read", "attn", f.err || ""]
    : f.state === "none"
    ? ["no agents", "attn", "Every issue routed here runs on a generic mission prompt: no spine, no declared gates, no verify discipline beyond what the prompt spells out."]
    : f.state === "ready"
    ? [`${f.agents} agents`, "complete", ""]
    : ["reading", "", "Reading this repository’s board…"];

  const tier = repoTier(key, c);
  const tag = unreachable || !c.synced ? "div" : "button";
  const go = tag === "button" ? ` type="button" data-repo="${esc(key)}"` : "";
  return `<${tag} class="qr ag-r ag-repo s${tier === 0 ? "1" : tier === 1 ? "2" : "0"}"${go}>
    <span class="qr-k"><span class="lt-nm">${esc(name)}</span></span>
    <span class="ag-st"><span class="chip${tone ? " " + tone : ""}">${esc(word)}</span></span>
    <span class="qr-t"${say ? ` data-tip="${esc(say)}"` : ""}>${esc(src)}${c.primary ? " &middot; primary" : ""}${
      say ? `<span class="ag-sub">${esc(say)}</span>` : ""}</span>
    ${figs ? `<span class="qr-mk">${figs}</span>` : ""}
    <span class="qr-do">${f.state === "ready" ? `<span class="act">Open</span>` : ""}</span></${tag}>`;
}

function viewRepoIndex(){
  const rows = corpusRows()
    .map((c, i) => ({ c, key: keyOf(c), i }))
    .sort((a, b) => (repoTier(a.key, a.c) - repoTier(b.key, b.c)) || (a.i - b.i));

  const read = rows.filter(r => repoFacts(r.key).state === "ready" || repoFacts(r.key).state === "none");
  const none = read.filter(r => repoFacts(r.key).state === "none").length;
  const nospine = read.reduce((n, r) => {
    const f = repoFacts(r.key);
    return n + (f.state === "ready" ? f.agents - f.spined : 0);
  }, 0);
  const waiting = rows.length - read.length;

  const err = CORPORA_ERR
    ? `<div class="banner"><b>The list of repositories could not be read.</b>
       ${esc(CORPORA_ERR)} &mdash; what is below is the one repository this page already holds.</div>`
    : "";

  /* THE FIGURES ARE THE BAR'S ONE-LINE STATUS, where every list page keeps its own (`.qbar`). */
  const parts = [`<span><b>${rows.length}</b> repositories served</span>`,
    `<span${none ? ` class="attn"` : ""}><b>${none}</b> with no agents</span>`,
    `<span${nospine ? ` class="brass"` : ""}><b>${nospine}</b> agents with no spine</span>`];
  if (waiting) parts.push(`<span><b>${waiting}</b> still reading</span>`);
  const dot = none || rows.some(r => !r.c.synced) ? "bad" : nospine ? "part" : "ok";
  return pageHead("Agents") + err +
    `<div class="qbar"><p class="qstat">${parts.join(" &middot; ")}</p></div>
    <div class="ql ag">${agGroup("repos", { name: "By repository", count: rows.length, hint: "worst first", dot,
      rows: rows.map(r => repoIndexRow(r.c, r.key)).join("") })}</div>`;
}

/* ── the crumb row, and the one control that changes repository ───────────── */

/* ONE CONTROL, IN THE CRUMB ROW. A row of repository boxes at the top of every Agents page
   restates the index the reader has just come from, on every page, forever — so the selector is
   a dropdown the size of a breadcrumb, and it is present only when there is a second repository
   to choose. */
function repoCrumbs(key, tail){
  /* `mine`, not `here`. `here` is the obvious name for "the corpus this crumb row is about" and
     two other functions in this file already use it as a local for their own "the current one",
     which is precisely why the route reader is called `openRoute` rather than `here` — see it. */
  const mine = corpusFor(key);
  const name = mine ? repoName(mine) : "this repository";
  if (!manyRepos()){
    return `<div class="crumbs">${link("commands", "lnk", "Agents")}
      ${tail ? `<span class="sep">/</span><span class="here">${esc(tail)}</span>` : ""}</div>`;
  }
  const dot = c => {
    const f = repoFacts(keyOf(c));
    return f.state === "ready" && f.filled === f.slots && !f.broken ? "ok"
         : f.state === "ready" ? "part" : "none";
  };
  const items = corpusRows().map(c => {
    const k = keyOf(c);
    const f = repoFacts(k);
    const count = f.state === "ready" ? f.agents : f.state === "none" ? "no agents" : "&mdash;";
    return k === null
      ? `<span class="rmenu-off"><i class="dot none"></i><span class="nm">${esc(repoName(c))}</span>
         <span class="ct">no lane</span></span>`
      : `<button data-repo="${esc(k)}" aria-current="${k === key}"><i class="dot ${dot(c)}"></i>
         <span class="nm">${esc(repoName(c))}</span><span class="ct">${count}</span></button>`;
  }).join("");
  return `<div class="crumbs">${link("commands", "lnk", "Agents")}
    <span class="sep">/</span>
    <span class="dd">
      <button class="rsel" data-dd="repo" aria-expanded="${openDD === "repo"}">
        <i class="dot ${mine ? dot(mine) : "none"}"></i>${esc(name)}<span class="car">&#9662;</span></button>
      <div class="rmenu"${openDD === "repo" ? "" : " hidden"}>${items}
        ${link("commands", "all", `Compare all ${corpusRows().length} &rarr;`)}</div>
    </span>
    ${tail ? `<span class="sep">/</span><span class="here">${esc(tail)}</span>` : ""}</div>`;
}

/* ── one repository ───────────────────────────────────────────────────────── */

/* The reader's own narrowing of the agent table, held in the module rather than the hash: it is
   a lens on one page, not a place. Both are cleared by a repository switch — an agent name that
   matched in one tree means nothing in the next, and a reader who arrived at an empty table
   would have no way of knowing a filter they set somewhere else was the reason. */
let CMD_Q = "";
let CMD_GROUP = "family";

function agentMatches(c, q){
  if (!q) return true;
  return (c.name + " " + (c.intent || "") + " " + (c.title || "")).toLowerCase().includes(q);
}

/* THE FAMILY AN AGENT BELONGS TO, read off its own name. A command is `noun:verb` — `prd:create`,
   `prd:design`, `prd:implement` — and the noun is the artefact the whole family acts on, which is
   the closest thing to a lifecycle the TREE can state.
   IT IS NOT THE HAND-AUTHORED SEVEN-STAGE LIFECYCLE the mockup drew, and that is a deliberate
   refusal rather than an omission: that grouping is a list of stage names plus one row per
   command, and this file ships into six repositories and may not know any repository's command
   names. Writing it here would rebuild, in the renderer, exactly the hand-list this page was
   built to replace. */
function agentFamily(c){
  const at = c.name.lastIndexOf(":");
  return at < 0 ? "" : c.name.slice(0, at);
}

/* ONE AGENT ON THE LIST'S LINE: NAME · VERDICT · WHAT IT IS FOR · MARKS · SPINE. The name is
   the link to the agent's own page, which carries everything the line clips — its steps, its
   slots, its prompt. What it is for runs to the line's end and is whole in its tip; what it needs
   from a person and a broken reference are glyphs; the slots that block or degrade it stay chips,
   because each is the way into that slot's page.
   NO START ON THE ROW (the operator: "remove that start button"). The row used to end in
   the host's seat (`runbox`), one Start per agent — forty buttons down a page that is a REFERENCE
   of what the agent tree is, each one opening a workstation session on a click. Opening an agent
   is still one click away, on the agent's own page (its `invoke` row keeps `runbox`), and on the
   Workstation page's New-session form; the list itself states and links, it does not launch. */
function agentRow(c, t){
  const verdict = !t.registry
    ? `<span class="flag">unknown</span>`
    : c.verdict === "undeclared"
    ? `<span class="chip flight" data-tip="Declares no requires/optional slots, so nothing can be checked for it — in any repository.">not declared</span>`
    : c.verdict === "runs" ? `<span class="chip complete">runs here</span>`
    : `<span class="chip unproven">blocked</span>`;
  const brk = c.references.filter(r => !r.resolves).length;
  const said = `${brk} broken reference${brk > 1 ? "s" : ""}`;
  const marks = needsMark(c) +
    (brk ? mark("broken", "attn", `${said} — the prompt names ${brk > 1 ? "paths" : "a path"} this repository does not hold`, said, brk) : "") +
    (c.blockedBy.length ? `<span class="ag-need">needs ${c.blockedBy.map(slotChip).join(" ")}</span>` : "") +
    (c.degraded.length ? `<span class="ag-need">degraded: ${c.degraded.map(d => slotChip(d.slot)).join(" ")}</span>` : "");
  const use = c.intent || c.title;
  return `<div class="qr ag-r" data-agent="${esc(c.id)}">
    <span class="qr-k">${link("command:" + c.id, "lt-nm lnk", esc(c.name))}</span>
    <span class="ag-st">${verdict}</span>
    <span class="qr-t" data-tip="${esc(use)}">${esc(use)}</span>
    ${marks ? `<span class="qr-mk">${marks}</span>` : ""}
    <span class="qr-age">${c.hasSpine
      ? `<span data-tip="declares its own steps, gates and actors">${c.steps.length} steps</span>`
      : `<span class="attn" data-tip="declares no spine — no steps, no gates, no slots">no spine</span>`}</span></div>`;
}

/* THE FILTER BAR (`filterBar`): the search over the agents, live because it narrows rows this page
   already holds, and the grouping as the bar's Sort — by family, or one A–Z list. No filter menu:
   the page has nothing else to narrow by. Both stay module state (`CMD_Q`, `CMD_GROUP`). */
function agentFilters(t, shown){
  return filterBar({
    id: "commands",
    noun: ["agent", "agents"],
    matched: shown,
    count: `<span class="showing">${shown} of ${t.commands.length}</span>`,
    search: { value: CMD_Q, live: true, label: "Search agents", said: "Matching",
      placeholder: "Search agents and what they are for" },
    sort: { value: CMD_GROUP, def: "family", options: [["family", "by family"], ["az", "A–Z"]] },
    on: {
      search: text => { CMD_Q = text; render(openRoute()); },
      sort: k => { CMD_GROUP = k || "family"; render(openRoute()); },
      clear: () => { CMD_Q = ""; CMD_GROUP = "family"; render(openRoute()); },
    },
  });
}

/* A GROUP'S DOT IS ITS WORST ROW: filled green when every agent in it runs here, red when one is
   blocked, dashed when nothing can say (no registry), a plain ring otherwise. */
function agentDot(t, rows){
  if (!t.registry) return "unknown";
  if (rows.some(c => c.verdict !== "runs" && c.verdict !== "undeclared")) return "bad";
  return rows.every(c => c.verdict === "runs") ? "ok" : "part";
}

/* THE AGENT GROUPS OF THE CARD. By family, FLAT NAMES FIRST, then every family alphabetically. A
   command with no namespace is a top-level entry — `ask`, `route`, `check`, `verify` — and putting
   them first is the one ordering claim this file makes, because a reader meeting the tree for the
   first time meets those. Everything else is the tree's own alphabet. A–Z is one group of every
   match. */
function agentGroups(t, hit){
  const ns = cmdNamespace(t);
  if (!hit.length){
    return filterEmpty("commands", { bare: `<p class="empty-note">No agent matches &ldquo;${esc(CMD_Q)}&rdquo;.</p>` });
  }
  if (CMD_GROUP !== "family"){
    const rows = hit.slice().sort((a, b) => a.name.localeCompare(b.name));
    return agGroup("az", { name: "Every agent", count: rows.length, hint: "A–Z", dot: agentDot(t, rows),
      rows: rows.map(c => agentRow(c, t)).join("") });
  }
  const families = [...new Set(hit.map(agentFamily))].sort((a, b) =>
    (a === "" ? "" : "1" + a).localeCompare(b === "" ? "" : "1" + b));
  return families.map(f => {
    const rows = hit.filter(c => agentFamily(c) === f);
    return agGroup("family:" + f, { name: f || "On their own", count: rows.length,
      hint: f ? `/${ns ? ns + ":" : ""}${f}:…` : "typed by their own name", dot: agentDot(t, rows),
      rows: rows.map(c => agentRow(c, t)).join("") });
  }).join("");
}

/* THE SLOT REGISTRY, IN FULL — every question, whether this repository answers it, and with what
   file. Filled slots were invisible before: the page showed a `24/24` ratio and a detail page per
   slot, so *"which file answers `gate` here"* cost two clicks and a guess. The registry is the
   list; the checkout is the answer; both belong on one screen — as groups of the same card, under
   the agents, each counting what it has answered. The blurb is the header's hint, whole in its tip. */
function slotGroup(t, key, label, blurb, rows, cited, answered){
  if (!rows.length) return "";
  const filled = rows.filter(s => s.filled).length;
  const dot = filled === rows.length ? "ok"
    : rows.some(s => !s.filled && s.requirement === "mandatory") ? "bad" : "part";
  return agGroup(key, { name: label, count: answered ? `${filled}/${rows.length}` : rows.length, hint: blurb, tip: blurb, dot,
    rows: rows.map(s => slotRow(s, t, cited)).join("") });
}

/* ONE SLOT ON THE LIST'S LINE: ID · STATE · WHAT IT ANSWERS · WHERE · WHO DECLARES IT. What it
   answers carries what goes missing without it; where is the first file that answers it (or the
   pattern that would), and the rest are a count whose tip names them — every one of them is on the
   slot's own page. */
function slotRow(s, t, cited){
  /* A STUB is a scaffold placeholder: the file is there and answers nothing, so it is neither
     `filled` nor `missing` — it says so, and points at the file to write. */
  const state = s.filled
    ? `<span class="chip complete">filled</span>`
    : s.stub
    ? `<span class="chip ${s.requirement === "mandatory" ? "attn" : "unproven"}" data-tip="a placeholder — write the real answer in it">stub</span>`
    : s.requirement === "mandatory"
    ? `<span class="chip attn">missing</span>`
    : `<span class="chip unproven">not set</span>`;
  const paths = s.filled || s.stub ? s.matched : s.fill;
  const rest = paths.slice(1);
  const where = (paths.length ? pathChip(paths[0], cited, !s.filled && !s.stub) : "") +
    (rest.length ? mark("", "", rest.join("\n"), `${rest.length} more`, `+${rest.length}`) : "");
  const users = (t ? t.commands : []).filter(c => c.requires.includes(s.id) || c.optional.includes(s.id));
  const without = !s.filled && s.degrade ? s.degrade : "";
  return `<div class="qr ag-r ag-slot" data-slot="${esc(s.id)}">
    <span class="qr-k">${link("slot:" + s.id, "lt-nm lnk", esc(s.id))}</span>
    <span class="ag-st">${state}${s.requirement === "optional" ? `<span class="chip">optional</span>` : ""}</span>
    <span class="qr-t" data-tip="${esc(s.answers + (without ? " — without it: " + without : ""))}">${esc(s.answers)}${
      without ? `<span class="ag-sub">without it: ${esc(without)}</span>` : ""}</span>
    <span class="ag-where">${where}</span>
    <span class="qr-age">${users.length
      ? `${users.length} agent${users.length > 1 ? "s" : ""}`
      : `<span class="flag">none</span>`}</span></div>`;
}

/* A PATH IS A DESTINATION, NOT A LABEL — where it is one this corpus actually cites. `.chip`
   uppercases, which is right for FILLED and ruinous for `knowledge/specs/ui-spec.md`, so a path
   gets its own token. A path no agent points at is not a link: the doc route serves only the
   citation set, and a chip linking outside it links to a 404. */
function pathChip(p, cited, missing){
  const at = p.lastIndexOf("/");
  const dir = at < 0 ? "" : p.slice(0, at + 1);
  const base = at < 0 ? p : p.slice(at + 1);
  if (missing){
    return `<span class="pth gone"><span class="dir">${esc(dir)}</span>${esc(base)} &middot; nothing matches</span>`;
  }
  const inner = `<span class="dir">${esc(dir)}</span>${esc(base)}`;
  return cited && cited.has(p)
    ? link("doc:" + p, "pth", inner)
    : `<span class="pth flat">${inner}</span>`;
}

function viewRepo(key){
  const c = corpusFor(key);
  const crumbs = repoCrumbs(key, "");

  /* THE PAYLOAD IN HAND IS ONE REPOSITORY'S, so a route naming another one is a page that cannot
     be drawn until its board has been read. That is not an edge case: it is what a bookmark, a
     shared link and the back button all are, and a route that only worked when the reader had
     just clicked the selector would break all three. `render` starts the read; this says what is
     happening while it runs, and what happened if it did not. */
  if (key !== REPO){
    const name = repoName(c) || key || "the primary repository";
    return crumbs + pageHead("Agents") + (
      SWITCH_ERR && SWITCH_FAILED === key
        ? `<div class="banner"><b>${esc(name)} could not be read.</b> ${esc(SWITCH_ERR)}</div>`
      : !SWITCH_REPO
        ? `<p class="empty-note">This page holds one repository, and it is not ${esc(name)}.</p>`
        : `<p class="empty-note">Reading ${esc(name)}&hellip;</p>`);
  }

  const t = cmdTree();

  if (!t || !t.commands.length){
    /* THE EMPTY LANE, AND IT IS A FINDING RATHER THAN AN EMPTY STATE. A repository with no agent
       tree runs every issue routed to it on a generic mission prompt, which is a fact about how
       that work gets done and not an absence of content. */
    return crumbs + pageHead("Agents") + `
      <div class="qbar"><p class="qstat"><span class="attn"><b>0</b> agents</span> &middot;
        <span class="attn"><b>0</b> slots answered</span></p></div>
      <div class="banner"><b>${esc(repoName(c) || "This repository")} has no agent tree.</b>
        Every issue routed here runs on a generic mission prompt instead of a purpose-built
        agent &mdash; no spine, no declared gates, and no verify discipline beyond what the
        prompt spells out.</div>`;
  }

  const cited = citedPaths(t);
  const nospine = t.commands.filter(c2 => !c2.hasSpine).length;
  const broken = t.commands.reduce((n, c2) => n + c2.references.filter(r => !r.resolves).length, 0);
  const filled = t.slots.filter(s => s.filled).length;
  const orphans = t.slots.filter(s =>
    !t.commands.some(c2 => c2.requires.includes(s.id) || c2.optional.includes(s.id)));
  const hit = t.commands.filter(c2 => agentMatches(c2, CMD_Q.trim().toLowerCase()));

  const banner = !t.registry
    ? `<div class="banner"><b>This repository declares no slot registry.</b> Nothing can say which
       agents can run here &mdash; every verdict below is &ldquo;unknown&rdquo; rather than
       &ldquo;yes&rdquo;.</div>`
    : t.registryErrors.length
    ? `<div class="banner"><b>${t.registryErrors.length} problem(s) in the slot registry:</b>
       ${t.registryErrors.map(esc).join("; ")}.</div>`
    : "";

  /* THE FIGURES ARE THE BAR'S ONE-LINE STATUS, where every list page keeps its own (`.qbar`); a
     finding takes its tone only on a count that is there. */
  const figures = [`<span><b>${t.commands.length}</b> agents</span>`,
    `<span${nospine ? ` class="brass"` : ""}><b>${nospine}</b> without a spine</span>`,
    `<span${broken ? ` class="attn"` : ""}><b>${broken}</b> broken reference${broken === 1 ? "" : "s"}</span>`,
    `<span><b>${filled}/${t.slots.length}</b> slots filled</span>`,
    `<span><b>${t.commands.filter(c2 => c2.needs === "nothing").length}</b> need nobody</span>`,
    `<span><b>${t.commands.filter(c2 => c2.mayMerge).length}</b> may merge</span>`];
  const root = cmdNamespace(t) ? (t.scan.directory || "").split("/")[0] : "the agent tree";

  return crumbs + pageHead("Agents") + banner +
    `<div class="qbar"><p class="qstat">${figures.join(" &middot; ")}</p></div>` +
    agentFilters(t, hit.length) +
    `<div class="ql ag">${agentGroups(t, hit)}${
      slotGroup(t, "slots:shared", "Slots that ship with the agents", `Answered under ${root} and identical in
        every repository. A missing one means the agent tree is incomplete — never that this repository
        failed to supply something.`.replace(/\s+/g, " "), t.slots.filter(s => s.tier === "shared"), cited, true)}${
      slotGroup(t, "slots:repo", "Slots this repository must answer", `Questions about this codebase that no
        agent can guess. A mandatory one that is unanswered stops every agent requiring it; an optional one
        degrades the run in the way its own line names.`.replace(/\s+/g, " "), t.slots.filter(s => s.tier === "repo"), cited, true)}${
      slotGroup(t, "slots:orphans", "Declared by no agent", `In the registry, and named by no agent's requires or
        optional. Either an agent should be asking for it, or the row is stale — both are worth
        knowing.`.replace(/\s+/g, " "), orphans, cited)}</div>`;
}

/* THE AGENTS TAB'S LANDING. One repository and there is nothing to compare, so the tab IS that
   repository; more than one and it is the index. The standalone file — generated against one
   checkout, with no server to ask — always takes the first branch, which is the honest answer
   for a page that holds exactly one corpus. */
function viewCommands(){
  return manyRepos() ? viewRepoIndex() : viewRepo(REPO);
}

function slotChip(id){
  const sl = slotById(id);
  const cls = !sl ? "unproven" : sl.filled ? "complete" : sl.requirement === "mandatory" ? "unproven" : "flight";
  return link("slot:" + id, `chip ${cls} link`, esc(id));
}

/* ── one agent ───────────────────────────────────────────────────────────── */

/* The prompt arrives LATER than the page, or never. A megabyte of agent text cannot ride in the
   payload — it is seven times the whole board — so the deployed app fetches one on demand and
   the standalone file, which has no server to ask, names the path on disk. Both are answers;
   neither is a spinner that never resolves.

   `BODY_CACHE` IS KEYED BY REPOSITORY AND PATH, not by path alone. Two repositories' agent trees
   collide on the relative path the moment there are two of them — `.claude/commands/plan.md` is
   a perfectly ordinary name — and a cache keyed on the path would serve one repository's prompt
   under another's heading with nothing on the page saying so. */
let BODY_LOADER = null;
let DOC_LOADER = null;
let ACTION = null;
const BODY_CACHE = {};
const DOC_CACHE = {};
/* THE SAME SEAM AGAIN, FOR THE CORPUS — and it is two loaders rather than one for the reason
   `loadBody` and `loadDoc` are two: they answer different questions and one of them is far the
   larger. `loadKnowledge` reads a LIST or a DETAIL, which are ids, sentences and edges; `loadProse`
   reads the authored narrative, which is a document. A list item carries no prose, a detail
   carries no prose, and prose is its own request — that is what makes 1,849 requirements cost
   what twelve cost, and a single loader returning both would have quietly ended it.

   TWO CACHES FOR ONE REASON: `KNOWLEDGE_CACHE` holds parsed objects and `PROSE_CACHE` holds text,
   and `fetchText` fills both — see its `coerce` argument. Both are keyed through `textKey`, so a
   second repository's `GOV-001` is a different entry rather than the first one's answer. */
let KNOWLEDGE_LOADER = null;
let PROSE_LOADER = null;
const KNOWLEDGE_CACHE = {};
const PROSE_CACHE = {};
function textKey(path){ return REPO + " " + path; }

/* THE HEADINGS OF A RENDERED DOCUMENT, SO A RAIL CAN POINT AT THEM. Read off the SOURCE rather
   than out of the markup `mdBlock` produced, and the fenced-code branch is the whole reason: a
   `# comment` inside a shell block is not a heading, and a scanner over the HTML would have to
   re-derive that. `mdSlug` is the same function `mdBlock` puts on the element, so the rail and
   the document cannot come to disagree about where a heading is. */
function mdOutline(src){
  const out = [];
  let fenced = false;
  String(src || "").split(/\n/).forEach(line => {
    if (/^\s*```/.test(line)){ fenced = !fenced; return; }
    if (fenced) return;
    const m = line.match(/^\s*(#{1,3})\s+(.*)$/);
    if (m) out.push({ level: m[1].length, text: mdText(m[2].trim()), id: mdSlug(m[2].trim()) });
  });
  return out;
}

/* THE RAIL SCROLLS, IT DOES NOT NAVIGATE. An `<a href="#h-phase-a">` would write the app's own
   hash — the router owns that — so the reader's back button would take them to a route this page
   never had. A button and a scroll leave the history alone. */
function outlineRail(src, extraHead, extra){
  const heads = mdOutline(src);
  const more = extra || [];
  if (!heads.length && !more.length) return "";
  return `<nav class="rail">
    ${heads.length ? `<div class="rh">On this page</div>` : ""}
    ${heads.map(h => `<button class="rl l${h.level}" data-anchor="${esc(h.id)}">${h.text}</button>`).join("")}
    ${more.length ? `<div class="rh rh2">${esc(extraHead)}</div>${more.join("")}` : ""}
  </nav>`;
}

/* THE PROMPT THIS PAGE HAS, AND WHAT IT SAYS WHEN IT HAS NONE. Four answers and they are four
   different sentences: the standalone file carries the text INLINE (`catalogue(bodies=True)`), a
   deployed page has fetched it, a deployed page is fetching it, and a page with no server names
   the file on disk. A refusal is CACHED as `{err}` rather than as text, so a reader who comes
   back does not re-ask a question that has already been refused — and so a refusal can never
   render as a document whose contents are an error message. */
function held(cache, path){ return cache[textKey(path)]; }
function textOrNull(v){ return typeof v === "string" ? v : null; }

function bodyHtmlFor(c){
  const inlined = (cmdTree().bodies || {})[c.path];
  if (typeof inlined === "string") return { text: inlined, html: mdBlock(inlined) };
  const have = held(BODY_CACHE, c.path);
  if (typeof have === "string") return { text: have, html: mdBlock(have) };
  if (have) return { text: "", html: `<p class="empty-note">${esc(have.err)}</p>` };
  if (BODY_LOADER) return { text: "", html: `<p class="empty-note">Loading the prompt&hellip;</p>` };
  return { text: "", html: `<p class="note">The full text is not carried in this file &mdash; it is
    a megabyte of markdown across the tree. Open <code>${esc(c.path)}</code> in the repository.</p>` };
}

function viewCommand(id){
  const c = cmdById(id);
  if (!c) return pageHead("Agents") + `<p class="empty-note">No agent <code>${esc(id)}</code>.</p>`;
  const t = cmdTree();
  const cited = citedPaths(t);

  const crumbs = repoCrumbs(REPO, c.name);
  const verdict = c.verdict === "undeclared"
    ? `<span class="chip flight">declares nothing &mdash; cannot be vouched for</span>`
    : c.verdict === "runs"
    ? `<span class="chip complete">runs in this repository</span>`
    : `<span class="chip unproven">blocked</span>`;

  const slotKv = (ids, kind) => !ids.length ? "" :
    `<div class="mrow"><b>${kind}</b><span>${ids.map(slotChip).join(" ")}</span></div>`;

  const steps = c.steps.length ? `<section class="grp"><div class="grp-h"><h3>Steps</h3>
    <span class="n">from its spine</span></div>
    <div class="box"><table class="cmdtab">
      <thead><tr><th>#</th><th>Step</th><th>Kind</th><th>Actor</th><th>Gate</th></tr></thead>
      <tbody>${c.steps.map((s, n) => `<tr>
        <td class="mono">${n + 1}</td><td>${esc(s.name)}</td>
        <td><span class="chip">${esc(s.kind)}</span></td>
        <td class="mono">${esc(s.actor)}</td>
        <td>${s.gate ? `<span class="chip ${s.gate === "hard" ? "unproven" : "flight"}">${esc(s.gate)}</span>` : "&mdash;"}</td>
      </tr>`).join("")}</tbody></table></div></section>` : "";

  /* A REFERENCE IS A DESTINATION NOW. An agent is mostly instructions ABOUT other documents — the
     references ARE the structure — and a page that rendered the prompt and then handed its
     references out as inert text stopped one click short of the thing being read. A reference
     that does not resolve stays inert, because there is nothing behind it to open. */
  const refList = k => {
    const rs = c.references.filter(r => r.kind === k);
    if (!rs.length) return "";
    /* AN AGENT NAME IS A CHIP; A PATH IS A PATH. `.chip` is `text-transform:uppercase`,
       which is right for a status word and ruinous for a filename — it rendered
       `KNOWLEDGE/SPECS/UI-SPEC.MD`, losing the case that tells a reader where a path
       ends and a word begins. `pathChip` is the token for this and already dims the
       directory so the eye lands on the file; only the `command` kind, whose target is
       an agent NAME rather than a path, stays a chip. */
    return `<div class="mrow"><b>${k}</b><span>${rs.map(r =>
      r.kind === "command"
        ? (cmdById(r.target.replace(/:/g, "-"))
            ? link("command:" + r.target.replace(/:/g, "-"), "chip link", esc(r.target))
            : `<span class="chip unproven" title="${esc(r.target)}">${esc(r.target)} — not present</span>`)
        : pathChip(r.target, cited, !r.resolves)).join(" ")}</span></div>`;
  };

  const body = bodyHtmlFor(c);
  const readBy = t.commands.filter(o => o.id !== c.id &&
    o.references.some(r => r.kind === "command" && r.target.replace(/:/g, "-") === c.id));
  const rail = outlineRail(body.text, "Cited by", readBy.map(o =>
    link("command:" + o.id, "rl", esc(o.name))));

  return crumbs + pageHead("Agents") + `
    <div class="ehdr"><div class="etop"><h2 class="mono">${esc(c.name)}</h2>
      ${c.hasSpine ? `<span class="chip complete">${c.steps.length} steps</span>`
                   : `<span class="chip unproven">no spine</span>`}
      ${needsChip(c)}${c.mayMerge ? `<span class="chip flight">may merge</span>` : ""}</div>
      ${c.intent ? `<p class="promise">${esc(c.intent)}</p>` : ""}</div>
    <div class="strip">
      <div class="stat"><b>${c.steps.length || "&mdash;"}</b><span>steps</span></div>
      <div class="stat"><b>${c.lines}</b><span>lines</span></div>
      <div class="stat"><b>${c.references.length}</b><span>references</span></div>
    </div>
    <div class="cols"><div class="colmain">
      <div class="box">
        <div class="mrow"><b>verdict</b><span>${verdict}${c.blockedBy.length
          ? ` needs ${c.blockedBy.map(slotChip).join(" ")}` : ""}</span></div>
        <div class="mrow wide"><b>invoke</b><span>${runbox(cmdInvocation(t, c), true, "")}</span></div>
        <div class="mrow"><b>file</b><span>${pathChip(c.path, cited)}</span></div>
        ${c.needs ? `<div class="mrow"><b>needs</b><span>${esc(needsSentence(c.needs))}</span></div>` : ""}
        <div class="mrow"><b>may merge</b><span>${c.mayMerge ? "yes — this command may merge its own work" : "no — it hands off; the writer does not certify"}</span></div>
        ${slotKv(c.requires, "requires")}
        ${slotKv(c.optional, "optional")}
        ${c.unknownSlots.length ? `<div class="mrow"><b>undefined</b><span>${c.unknownSlots.map(x =>
          `<span class="chip unproven">${esc(x)}</span>`).join(" ")}</span></div>` : ""}
        ${refList("doc")}${refList("command")}${refList("script")}
      </div>
      ${steps}
      <section class="grp"><div class="grp-h"><h3>The prompt, in full</h3>
        <span class="n">${c.lines} lines</span></div>
        <div class="box"><div class="mdhead">rendered from ${pathChip(c.path, cited)}</div>
          <div class="md">${body.html}</div></div></section>
    </div>${rail}</div>`;
}

/* ── one document an agent reads ─────────────────────────────────────────── */

/* REACHED FROM ANY REFERENCE ON AN AGENT'S PAGE. An agent is mostly instructions about other
   files, so the reference list was the one part of that page a reader could not follow.
   `/api/commands/doc` serves exactly the set of paths some agent in this reading CITES — not a
   directory prefix — so every link this page draws is one the route will answer, and a path
   outside that set is not a route at all (`valid`). */
function viewDoc(path){
  const t = cmdTree();
  const cited = citedPaths(t);
  const at = path.lastIndexOf("/");
  const base = at < 0 ? path : path.slice(at + 1);
  const have = held(DOC_CACHE, path);

  /* WHO READS IT, off the tree rather than out of the answer. The API carries `citedBy` and this
     agrees with it by construction — both are the same citation rows — but the tree is in hand
     before the fetch lands, so the page answers half the question immediately. */
  const readers = (t ? t.commands : []).filter(c => c.references.some(r => r.target === path));

  const body = have === undefined
    ? (DOC_LOADER
        ? `<p class="empty-note">Loading the document&hellip;</p>`
        : `<p class="note">The full text is not carried in this file &mdash; it is a megabyte of
           markdown across the tree. Open <code>${esc(path)}</code> in the repository.</p>`)
    : typeof have === "string" ? mdBlock(have) : `<p class="empty-note">${esc(have.err)}</p>`;

  const rail = outlineRail(textOrNull(have) || "", "Read by",
    readers.map(c => link("command:" + c.id, "rl", esc(c.name))));

  return repoCrumbs(REPO, base) + pageHead("Agents") + `
    <div class="ehdr"><div class="etop"><h2>${esc(base)}</h2>
      <span class="chip">${readers.length} reader${readers.length === 1 ? "" : "s"}</span></div>
      <p class="promise">A document this repository&rsquo;s agents are told to read.</p></div>
    <div class="cols"><div class="colmain">
      <div class="box"><div class="mdhead">rendered from ${pathChip(path, null)}</div>
        <div class="md">${body}</div></div>
    </div>${rail}</div>`;
}

/* ── one slot ────────────────────────────────────────────────────────────── */

function viewSlot(id){
  const s = slotById(id);
  if (!s) return pageHead("Agents") + `<p class="empty-note">No slot <code>${esc(id)}</code>.</p>`;
  const t = cmdTree();
  const cited = citedPaths(t);

  const crumbs = repoCrumbs(REPO, s.id);
  const state = s.filled
    ? `<span class="chip complete">filled</span>`
    : s.stub
    ? `<span class="chip ${s.requirement === "mandatory" ? "unproven" : "flight"}">stub &mdash; a placeholder, ${s.requirement === "mandatory" ? "required" : "optional"}</span>`
    : s.requirement === "mandatory"
    ? `<span class="chip unproven">missing &mdash; required</span>`
    : `<span class="chip flight">not set &mdash; optional</span>`;

  /* Who is actually affected, read off the tree rather than off `consumedBy`: the declaration
     says who MEANS to use it, the join says who cannot run without it. Both are shown, because a
     slot no agent declares is as interesting as one that blocks four. */
  const blocks = t.commands.filter(c => c.blockedBy.includes(s.id));
  const declares = t.commands.filter(c => c.requires.includes(s.id) || c.optional.includes(s.id));

  const fills = s.fill.map(f => {
    const ok = !s.missing.includes(f);
    return `<div class="mrow"><b>${ok ? "resolves" : "missing"}</b><span><code>${esc(f)}</code>${
      ok ? "" : ` <span class="flag">nothing matches</span>`}</span></div>`;
  }).join("");

  const action = s.filled ? "" : `<section class="grp"><div class="grp-h"><h3>Fix it</h3></div>
    <div class="box">
      <p class="note">${s.requirement === "mandatory"
        ? `${blocks.length} agent(s) cannot run until this is answered.`
        : `Nothing is blocked. Without it: ${esc(s.degrade || "unspecified")}.`}</p>
      <div class="mrow"><b>author it</b><span><code>${esc((s.stub ? s.matched[0] : s.fill[0]) || "")}</code>${
        s.stub ? ` <span class="flag">placeholder &mdash; replace it</span>` : ""}</span></div>
      ${ACTION ? `<button class="act" data-slotfix="${esc(s.id)}">Open a session to write it</button>`
               : `<p class="note">Open a terminal in the repository and write that file.</p>`}
    </div></section>`;

  return crumbs + pageHead("Agents") + `
    <div class="ehdr"><div class="etop"><h2 class="mono">${esc(s.id)}</h2>${state}
      <span class="chip">${esc(s.tier)}</span></div>
      <p class="promise">${esc(s.answers)}</p></div>
    <div class="box">
      <div class="mrow"><b>tier</b><span>${esc(s.tier)} &middot; ${esc(s.requirement)}</span></div>
      ${s.degrade ? `<div class="mrow"><b>without it</b><span>${esc(s.degrade)}</span></div>` : ""}
      ${fills}
      ${s.matched.length ? `<div class="mrow"><b>answered in</b><span class="chiprow">${s.matched.map(m =>
        pathChip(m, cited)).join(" ")}</span></div>` : ""}
    </div>
    <section class="grp"><div class="grp-h"><h3>Who needs it</h3></div>
      <div class="box">
        ${blocks.length ? `<div class="mrow"><b>blocked</b><span>${blocks.map(c =>
          link("command:" + c.id, "chip unproven link", esc(c.name))).join(" ")}</span></div>` : ""}
        ${declares.length ? `<div class="mrow"><b>declares it</b><span>${declares.map(c =>
          link("command:" + c.id, "chip link", esc(c.name))).join(" ")}</span></div>`
          : `<p class="empty-note">No agent in this tree declares this slot.</p>`}
      </div></section>` + action;
}

/* ── 7. the glossary page STOOD HERE ───────────────────────────────────────
 * `viewGlossary` rendered every term — the corpus's `specs/glossary.md` and the host's
 * vocabulary — on one page, and every defined word on every other page was a link to it. The
 * page is gone: the corpus's kinds are explained on the Knowledge page, one row per
 * kind out of `KGUIDE`, and every word is now explained WHERE IT IS USED, as hover text
 * (`term()`, `defined()`). A reader who wanted to know what a lease is used to leave the page
 * they were reading to find out. A bookmarked `#glossary` or `#glossary:<term>` lands on the
 * Knowledge page (`canon`), never on a blank one.
 */

/* ── 8. the knowledge corpus: eight questions, one list, one detail page ────
 *
 * WHAT THIS TAB IS FOR. The board answers *what is happening now*. Everything on it is there
 * because of something that is not: a capability somebody promised, a requirement the system
 * shall hold to, a decision that refused an alternative, a component that owns the code. Those
 * lived in a second renderer with its own template, its own payload builder and its own
 * palette — two pages describing one repository, which is exactly the fork the shared
 * `fleet.css`/`board.js` arrangement exists to prevent. So the corpus arrives HERE, as a tab,
 * drawn with the components the rest of this file already draws with.
 *
 * EIGHT GROUPS, EACH A QUESTION RATHER THAN A TABLE NAME — who it is for, what someone can do,
 * what we build, what we promised, how it is checked, what is changing, how work is done here,
 * and what is computed — with one row per kind under each (`KGUIDE`). A reader who does not
 * already know the vocabulary can still find the row they want, which a list headed
 * "requirements / capabilities / components" does not give them, and every row folds open to
 * say what the kind is, how to tell it from its neighbours, and what one looks like.
 *
 * THREE SIZES, AND THE MIDDLE ONE IS THE POINT. A list item is an id, a name, one clipped
 * sentence, chips and facets — never prose. A detail is facts and relations — never prose.
 * Prose is its own request. That is what makes a corpus of this size affordable to browse: the
 * list below costs the same for 1,849 rows as for twelve, because it never carries the 1,837 it
 * is not showing.
 *
 * EVERY RELATION, BOTH DIRECTIONS, INCLUDING THE EMPTY ONES. A relation is authored once, on the
 * side that owns it, and served from both ends; a detail response names every group it has, and
 * this renders every group it names even when the group is empty. "Claimed by: nothing" is the
 * single most useful sentence on a requirement's page, and a renderer that skipped empty groups
 * would be unable to say it — a reader would see no heading and conclude the edge was not
 * modelled rather than that it is not there.
 */

/* THE GROUPS AND THEIR QUESTIONS are `KGUIDE`'s, below — the one list the page reads. */
/* WHERE A KIND LANDS WHEN THE PAYLOAD DOES NOT SAY. The payload's own `section` wins always; this
   is the floor under a corpus that shipped an index and no placement, so a kind is never
   invisible. System is the default rather than an arbitrary pick: it is the section the sections
   table itself leaves open ("components, layers — architecture lands here"), so an unrecognised
   kind arrives under the question that is already the broad one. */
const K_SECTION_OF = { journey: "product", area: "product", capability: "product",
                       requirement: "commitments", decision: "commitments" };
/* THE RELATION HEADINGS, and they are the seven authored edges' own names read back from the
   inverse side. This is a LABEL table and not a model: a response that names its own `label` wins
   outright, and a verb absent from here renders under the verb itself rather than being dropped —
   so a new edge is legible the day it is served and readable the day somebody names it. */
const K_REL = { claims: "Claims", claimedBy: "Claimed by", shipsIn: "Ships in", ships: "Ships",
                needs: "Needs", neededBy: "Needed by", moves: "Moves", settledBy: "Settled by",
                builds: "Builds", builtBy: "Built by", covers: "Covers", coveredBy: "Covered by",
                holds: "Holds", inArea: "In feature" };
/* ── WHAT EVERY KIND OF KNOWLEDGE IS: THE ONE LIST ────────────────────────────
 *
 * EVERY KIND THIS PRODUCT KEEPS ITS KNOWLEDGE IN, in the eight groups the Knowledge page shows
 * them under, each with how to tell it apart from its neighbours and one example of what it looks
 * like in a repository. ONE LIST, AND THREE READERS: the Knowledge page draws a row per entry
 * (`viewKnowledge`); the deployed app's Build-the-knowledge page links every "what you will
 * have" tile and every step's output into those rows by `id` (`Board.knowledgeGuide`,
 * `Board.kindLink`); and a word that names a kind carries the entry's definition as its hover
 * text (`termTip`). A second copy of any of these sentences would be the one that goes stale.
 *
 * EDITORIAL WORDS, AND THE PAYLOAD'S OWN STILL WIN. These are how a reader who does not already
 * have the vocabulary finds the row they want. The served index carries the corpus's arithmetic
 * — a count, a section, the flags worth a badge — and its own `title` and `blurb` when it has
 * them win over `nm` and `def` (`kTitle`, `kBlurb`). A kind the index serves and this list does
 * not know still renders, under its own name: an index is never narrowed to what this list
 * happens to know.
 *
 * THE EXAMPLES ARE EXAMPLES, and the page says so on every one ("Example", and an invented path in
 * an invented repository). Counts are never taken from here: a row's figure is read off the
 * payload (`kgCount`) or the row has none.
 *
 *   `life` — when the kind gets written: `setup` (the knowledge bootstrap writes it), `grows`
 *            (added as work happens; empty at first), `gen` (computed; never edited by hand).
 *   `ex`   — the example's shape: `row` {cols, vals}, `card` {id, title, f}, `list` {title, items, hi}.
 */
const KGUIDE = [
  { id: "who", h: "Who it is for", q: "Who uses the product, and why?", items: [
    { id: "persona", nm: "Product statement and personas", life: ["setup"],
      def: "One paragraph saying what the product is, and the kinds of people who use it, each with the one job they come to do.",
      tell: "A persona is a kind of user with a job, not a job title or a login role.",
      vs: "A login role (admin, member) is how the product grants access. One persona can hold several roles.",
      where: "strategy/product-vision.md", by: "Step 1 of building the knowledge, in your words.",
      ex: { shape: "card", src: "strategy/product-vision.md", id: "Persona", title: "Approver",
            f: [["Comes to", "Clear the orders waiting on their sign-off before the day's cut-off"],
                ["Uses", "Approvals inbox, order detail"], ["Evidence", "role approver, permission orders:approve"]] } },
  ] },
  { id: "product", h: "Product", q: "What can someone do?", items: [
    { id: "journey", nm: "Journeys", unit: "journeys", life: ["setup"],
      def: "How one kind of user gets a whole job done, from the moment they need it to the moment it is done, with numbered criteria anyone can check.",
      tell: "It starts from a real reason someone opens the product, not halfway through a screen.",
      vs: "A flow is one reusable stretch (\"sign in\", \"approve an order\"). A journey map strings flows into a whole job.",
      where: "journeys/flows/, journeys/maps/", by: "Step 6, confirmed by you. Each criterion is a promise.",
      ex: { shape: "list", src: "journeys/maps/buyer-orders-a-part.md", title: "A buyer orders a part that needs approval",
            items: ["The buyer finds the part by name or part number.", "The order shows the price the buyer saw, including tax.",
                    "The buyer sees \"Waiting for approval\" and the order cannot ship.",
                    "The approver gets the order in their inbox within a minute."], hi: 2 } },
    { id: "area", nm: "Features", unit: "features", life: ["setup"],
      def: "A group of capabilities a customer would recognise by name, like \"Ordering\" or \"Approvals\".",
      tell: "Would a customer use this name when describing the product? If only engineers would, it is still a feature, marked as substrate.",
      vs: "A component is how the code is split; a feature is how a customer sees the product. One feature can draw on several components.",
      where: "features/ordering.md", by: "Step 5. New work on this ground is filed under its feature.",
      ex: { shape: "card", src: "features/ordering.md", id: "Feature", title: "Ordering",
            f: [["Intent", "Buyers find parts and place orders at the price they were shown."], ["Holds", "14 capabilities"],
                ["Built on", "orders, pricing"]] } },
    { id: "capability", nm: "Capabilities", unit: "capabilities", life: ["setup"],
      def: "One thing the product lets someone do, as a short name, with the code that implements it and the test that proves it.",
      tell: "Still true tomorrow and checkable any time. \"Search works\" is too big; \"the Save button is enabled\" is too small.",
      vs: "A requirement is a rule that holds while someone uses a capability: the capability is approving an order, the requirement is that big orders need a second approver.",
      where: "a row in features/<feature>.md", by: "Steps 3 and 4. The id is permanent and never reused.",
      ex: { shape: "row", src: "features/ordering.md", cols: ["ID", "Capability", "Ships in", "Tested by"],
            vals: ["CAP-0007", "Order approval by a second reviewer", "(shipped)", "TestApprove_SecondReviewer"] } },
  ] },
  { id: "system", h: "System", q: "What do we build?", items: [
    { id: "component", nm: "Components", unit: "components", life: ["setup"],
      def: "A part of the system you would draw once on an architecture diagram, defined by the code it owns.",
      tell: "Can you name the code it owns, and would you draw it exactly once?",
      vs: "An outcome owns no code; it comes out of several components working together.",
      where: "specs/architecture/components.md", by: "Step 2 maps all of them; each counts as described once its part has been through steps 3–7.",
      ex: { shape: "row", src: "specs/architecture/components.md", cols: ["id", "layer", "owns", "depends on"],
            vals: ["orders", "domain", "internal/orders/, web/src/pages/orders/", "pricing, audit"] } },
    { id: "outcome", nm: "Outcomes", life: ["grows"],
      def: "A property the product has that no single part delivers, like \"an order page loads in under a second\".",
      tell: "If you could point at the code that delivers it, it is a component.",
      where: "a kind of program or slice; no file of its own", by: "People, when they plan work.",
      ex: { shape: "card", src: "programs/PG-02.md", id: "Outcome", title: "Every action leaves an audit record",
            f: [["Delivered by", "orders, approvals, audit"], ["True when", "An auditor can trace any order change to a person"]] } },
    { id: "archdoc", nm: "Architecture notes", life: ["grows"],
      def: "Longer write-ups of how a component works inside, shown on the Architecture page.",
      tell: "Explains how it is built, for engineers.", vs: "What the product promises lives in requirements, not here.",
      where: "specs/architecture/components/", by: "Engineers and agents, as the system changes.",
      ex: { shape: "card", src: "specs/architecture/components/orders.md", id: "Note", title: "How an order moves from draft to shipped",
            f: [["Covers", "states, who may move an order, what is audited"]] } },
  ] },
  { id: "commitments", h: "Commitments", q: "What did we promise, what did we refuse, and why?", items: [
    { id: "requirement", nm: "Requirements", unit: "requirements", life: ["setup", "grows"],
      def: "One sentence the system must always or never do, in a numbered list per domain. Each was kept by a person. It can also record a cost accepted or an option refused.",
      tell: "It reads \"shall\" or \"never\", and you could see it break.",
      vs: "Never edited in place and never deleted: a new row replaces an old one, and the old one stays to say what changed.",
      where: "requirements/orders.md", by: "Step 4 from the code; later PRDs add more.",
      ex: { shape: "row", src: "requirements/orders.md", cols: ["ID", "Statement", "Kind", "Status", "Source"],
            vals: ["ORD-004", "An order of more than 500 parts is refused until a second person approves it.", "invariant", "adopted", "orders/approve.go:58"] } },
    { id: "decision", nm: "Decisions", unit: "decisions", life: ["grows"],
      def: "A choice someone made, with the alternative they turned down and why.",
      tell: "Can you name the option that was rejected? If not, it is a fact, not a decision.",
      vs: "Building the knowledge never invents past decisions; they start when people make them.",
      where: "decisions/, or inside a PRD's design", by: "People and agents as work happens.",
      ex: { shape: "card", src: "decisions/approvals-stay-synchronous.md", id: "Decision", title: "Approvals stay synchronous",
            f: [["Chose", "The approver gets the answer on screen"], ["Refused", "A background queue"],
                ["Because", "Approvers act on the result immediately"]] } },
    { id: "todo", nm: "Open questions", life: ["grows"],
      def: "Things someone noticed and nobody has settled yet.",
      tell: "Not yet a decision and not yet a rule. Each one ends as one of those, or is dropped.",
      where: "todos.md", by: "Anyone.",
      ex: { shape: "card", src: "todos.md", id: "Open", title: "Does a cancelled order free its stock at once or at day end?",
            f: [["Raised by", "Approvals review, step 4"]] } },
  ] },
  { id: "checking", h: "Checking it", q: "How do we know the product keeps its promises?", items: [
    { id: "promise", nm: "Promises", life: ["gen"],
      def: "The capabilities, requirements and journey criteria the Quality desk checks. See the summary below.",
      tell: "Worked out from the kinds above, never written by hand.", where: "computed", by: "Computed.",
      ex: { shape: "row", src: "computed", cols: ["Capabilities", "Requirements", "Journey criteria"], vals: ["21", "29", "8"] } },
    { id: "environment", nm: "Test environments", life: ["setup"],
      def: "A running copy of the product the Quality desk may test against, with its address, test users and whether it may write there.",
      tell: "Credentials are named by the secret that holds them, never written down.",
      vs: "Your own product's copies are environments; the outside systems it talks to are test systems.",
      where: "environments/staging.json", by: "Step 7, where you choose the environment.",
      ex: { shape: "card", src: "environments/staging.json", id: "Environment", title: "staging",
            f: [["Address", "https://staging.orders.example"], ["May write", "yes"], ["Test users", "buyer, approver"],
                ["Password", "secret: staging-approver-password"]] } },
    { id: "scenario", nm: "Scenarios", life: ["grows"],
      def: "A named check that exercises several things together and judges the combination.",
      tell: "One journey criterion checks one thing; a scenario checks how several behave together.",
      where: "scenarios/", by: "People and the Quality desk.",
      ex: { shape: "card", src: "scenarios/approval-and-audit.md", id: "Scenario", title: "Approving an order leaves exactly one audit record",
            f: [["Exercises", "CAP-0007, ORD-004, audit"], ["Passes when", "one record, naming the approver"]] } },
    { id: "fixture", nm: "Test systems", life: ["grows"],
      def: "An outside system the product talks to, set up for testing, and how to reach it.",
      tell: "Something the product connects to, not the product itself.", where: "fixtures/", by: "People.",
      ex: { shape: "card", src: "fixtures/sap-procurement.json", id: "Test system", title: "SAP procurement (test tenant)",
            f: [["Used by", "the purchasing integration"], ["Login", "secret: sap-test-login"]] } },
    { id: "evidence", nm: "Check results and audits", life: ["grows"],
      def: "The dated record of every check: what was tested, the evidence, the verdict, and the second reviewer's opinion. Audits do the same for a whole topic, like security.",
      tell: "A record of something that happened, kept as written and never changed.",
      where: "audits/", by: "The Quality desk and audit runs.",
      ex: { shape: "row", src: "audits/results/orders.json", cols: ["Checked", "Promise", "Verdict", "Evidence", "Reviewer"],
            vals: ["3 Nov, 02:10", "ORD-004", "passed", "screenshot, request log", "agreed"] } },
  ] },
  { id: "delivery", h: "Delivery", q: "What is changing?", items: [
    { id: "program", nm: "Programs", unit: "programs", life: ["grows"],
      def: "A result someone gets, with a day it becomes true, delivered through at least two slices.",
      tell: "It names who gets what, and how you would know it is true. Its state is worked out, never typed in.",
      where: "programs/", by: "People.",
      ex: { shape: "card", src: "programs/PG-01.md", id: "PG-01", title: "A buyer can reorder last month's parts in one click",
            f: [["Slices", "SL-001, SL-002"], ["Proved by", "a buyer reorders on staging"]] } },
    { id: "slice", nm: "Slices", unit: "slices", life: ["grows"],
      def: "A planning cut inside a program, with its own \"done when\".",
      tell: "It completes, and \"done\" means more than each of its PRDs being done.", where: "slices/", by: "People.",
      ex: { shape: "card", src: "slices/SL-001.md", id: "SL-001", title: "Reorder from order history",
            f: [["Program", "PG-01"], ["Done when", "a buyer reorders end to end on staging"]] } },
    { id: "prd", nm: "PRDs", unit: "PRDs", life: ["grows"],
      def: "One piece of work an agent can build in a shift, with its design and plan. The only kind whose status a person writes.",
      tell: "It finishes, and you can say what \"done\" looks like before it starts.",
      where: "prds/0001-reorder-button/", by: "People write it; agents design, plan and build it.",
      ex: { shape: "card", src: "prds/0001-reorder-button/prd.md", id: "0001", title: "Reorder button on order history",
            f: [["Slice", "SL-001"], ["Status", "planned"], ["Promises", "CAP-0031, ORD-012"]] } },
    { id: "theme", nm: "Themes", life: ["grows"],
      def: "A label that cuts across programs, like \"compliance\", to see related work together.",
      tell: "Removing a theme loses a view but no information. It is only a label.",
      where: "a label; no file of its own", by: "People.",
      ex: { shape: "card", src: "label on programs", id: "Theme", title: "compliance", f: [["On", "PG-02, PG-05, PG-07"]] } },
    { id: "idea", nm: "Ideas", life: ["grows"],
      def: "An early idea with sketches or notes, before anyone has committed to it.",
      tell: "Nothing is promised yet. It becomes a PRD or is deleted.",
      where: "ideas/ (small ideas live in the tracker)", by: "Anyone.",
      ex: { shape: "card", src: "ideas/bulk-reorder/", id: "Idea", title: "Reorder many parts at once",
            f: [["Holds", "two mockups"], ["Delete when", "decided either way"]] } },
  ] },
  { id: "work", h: "How work is done here", q: "What do agents need to know to work in this repository?", items: [
    { id: "slots", nm: "Repository answers", life: ["setup"],
      def: "The answers each Fleet command needs about this repository: how to build and test it, how branches and PRs work, where generated code comes from.",
      tell: "Facts about this repository's tooling, not about the product.",
      where: "slots/, and the targets in .fleet/fleet.toml", by: "Step 1 reads them from your CI and build files.",
      ex: { shape: "row", src: ".fleet/fleet.toml", cols: ["Target", "Runs"], vals: ["lint · test-unit", "npm run lint · npm test"] } },
    { id: "spec", nm: "Conventions and specs", life: ["grows"],
      def: "How things are done here: coding conventions, API rules, design guidelines.",
      tell: "A rule for engineers about how to build.", vs: "What the product promises its users belongs in requirements.",
      where: "specs/", by: "Engineers.",
      ex: { shape: "card", src: "specs/api-design-guide.md", id: "Spec", title: "API design guide",
            f: [["Example rule", "every list endpoint is paginated"]] } },
    { id: "sop", nm: "Procedures", life: ["grows"],
      def: "Step-by-step instructions for something people do again and again, like cutting a release.",
      tell: "Written for a person to follow. The automated parts are Fleet commands.", where: "sops/", by: "People.",
      ex: { shape: "list", src: "sops/cut-a-release.md", title: "Cut a release",
            items: ["Tag the release.", "Roll it to staging and run the checks.", "Roll it to production."], hi: -1 } },
    { id: "retro", nm: "Retros and drills", life: ["grows"],
      def: "What happened when an agent did a piece of work, and the record of practised failovers.",
      tell: "Records of what happened, kept to improve how work is done.",
      where: "retros/, drills/", by: "Agents after each run; people after a drill.",
      ex: { shape: "card", src: "retros/bug/orders-approval-fix.md", id: "Retro", title: "Bug fix took three attempts",
            f: [["Why", "the test needed a real database"], ["Changed", "database tests now run in their own lane"]] } },
  ] },
  { id: "else", h: "Generated and everything else", q: "What is computed, and what else is stored?", items: [
    { id: "indexes", nm: "Generated indexes", life: ["gen"],
      def: "Tables computed from the rest: every decision in one list, which requirements are decided but not built yet, and old-to-new capability ids.",
      tell: "Never edit one; change the source and it is recomputed.",
      where: "adr-index.md, capability-aliases.md and others", by: "Computed.",
      ex: { shape: "row", src: "requirement status (computed)", cols: ["Decided, not built", "Built, not decided", "Drift"], vals: ["4", "0", "1"] } },
    { id: "documents", nm: "Documents", unit: "documents", life: ["grows"],
      def: "Everything else under knowledge/: background reference, regulations, demo pages, screenshots, drafts.",
      tell: "Useful to read, but nothing in it is a promise.",
      where: "reference/, regulatory/, demos/, artifacts/, work/", by: "Anyone.",
      ex: { shape: "card", src: "regulatory/gdpr-summary.md", id: "Document", title: "GDPR summary for order data",
            f: [["Kind", "regulatory reference"]] } },
  ] },
];
/* Every kind by its id — the lookup `termTip`, `kTitle` and `kBlurb` read. */
const KGUIDE_BY = {};
KGUIDE.forEach(g => g.items.forEach(k => { KGUIDE_BY[k.id] = k; }));
const K_LIMIT = 25;

/* THE READER'S NARROWING, HELD IN THE MODULE RATHER THAN IN THE HASH — `CMD_Q`'s own reason, one
   register over: it is a reading position and not a destination, and a URL that carried it would
   make "the requirements list" a different page for every filter anybody ever pasted. */
let K_TYPED = "";
let K_QUERY = "";
const K_FACET = {};
const K_TRAIL = {};
const K_AT = {};

/* WHAT WAS TYPED AND WHAT WAS ASKED ARE TWO VALUES, and the gap between them is a decision.
   A search over this corpus is a request to a server, so a fetch per keystroke is 1,849 rows
   queried nine times to spell "governance". Enter in the box hands what was typed over as
   `K_TYPED` (`kSubmit`) and promotes it to `K_QUERY`, which is the only one any request reads. */
function kAsk(){
  K_QUERY = K_TYPED.trim();
  Object.keys(K_TRAIL).forEach(k => { K_TRAIL[k] = [""]; K_AT[k] = 0; });
}
/* THE CORPUS SEARCH, COMMITTED — the filter bar's Enter (`kBar`). An id typed in full is a
   destination rather than a search: this corpus knows every id it holds, so `GOV-001` opens GOV-001
   and anything else is a question asked across every kind at once. A CLEARED BOX IS NOT A
   NAVIGATION: re-rendering in place keeps the reader on the list they were narrowing, where `go`
   would push a second history entry for the page they are on. */
function kSubmit(text){
  const typed = String(text || "").trim();
  const straight = typed && (routeOf(typed) || routeOf(typed.toUpperCase()));
  K_TYPED = typed;
  if (straight){ K_TYPED = ""; kAsk(); return go(straight); }
  kAsk();
  return K_QUERY ? go("knowledge:search") : render(openRoute());
}

function kKind(kind){ return KKINDS.find(k => k.kind === kind) || null; }
function kTitle(kind){ const k = kKind(kind); return (k && k.title) || (KGUIDE_BY[kind] || {}).nm || kind; }
function kBlurb(k){ return k.blurb || (KGUIDE_BY[k.kind] || {}).def || ""; }
function kSection(k){ return k.section || K_SECTION_OF[k.kind] || "system"; }
function kCount(k){
  if (k.count != null) return k.count;
  return (((KINDEX && KINDEX.ids) || {})[k.kind] || []).length;
}

/* ── the reads, through the host's seam ──────────────────────────────────── */

/* Where a corpus read has got to — `CORPUS`'s three states, per path. `absent` is the fourth and
   is not a failure: it is a deployment with no server behind this file at all, which is what the
   standalone page IS, and it has to be told apart from a fetch still in flight. */
function kHold(path){
  if (!KNOWLEDGE_LOADER) return { state: "absent" };
  const held = KNOWLEDGE_CACHE[textKey(path)];
  if (held === undefined) return { state: "loading" };
  if (held && held.err) return { state: "failed", detail: String(held.err) };
  return { state: "ready", data: held };
}
function kWant(path, route){
  if (!KNOWLEDGE_LOADER || KNOWLEDGE_CACHE[textKey(path)] !== undefined) return;
  fetchText(KNOWLEDGE_LOADER, KNOWLEDGE_CACHE, path, "This reading could not be fetched: ", route,
            v => (v && typeof v === "object" ? v : {}));
}
/* The same three states as markup, so no view below spells them twice. */
function kState(got, what){
  if (got.state === "absent"){
    return `<p class="empty-note">This board carries the corpus index and no server to read
      ${esc(what)} from. The deployed board answers it; a standalone page holds the ids only.</p>`;
  }
  if (got.state === "loading") return `<p class="empty-note">Reading ${esc(what)}&hellip;</p>`;
  return `<div class="banner"><b>${esc(got.detail || "the request did not complete")}</b></div>`;
}

/* WHAT A LIST REQUEST IS, spelled once. `{kind}` is a value in the path and every narrowing is a
   query parameter, so a new kind and a new facet each cost nothing here.

   A FACET IS ONE REPEATABLE `facet=name=value`, NEVER A PARAMETER OF ITS OWN — and getting that
   backwards is not a request that fails, which is why it shipped. This line emitted
   `?domain=governance`, a parameter the list route does not have; FastAPI drops what it was not
   asked for, so the response is **200 and the whole kind**. The toolbar then drew its filter
   chip over an unnarrowed page and the *"N of M"* count never moved — measured against the real
   route: `?layer=data&limit=25` answers 200 with `facet: None`, and `?facet=layer%3Ddata`
   answers 200 with `facet: ["layer=data"]`. Components-by-layer and areas-by-layer are the only
   way to browse the System section, and this was their only path.

   The refusal `api/knowledge.py`'s `_filters` exists for — a facet name this kind does not have
   is a 400 rather than a silent ignore, written precisely so a filter nobody applied cannot look
   like a filter that matched everything — was reached by nothing, because a parameter the
   signature never names is never handed to it.

   So the `=` between the name and the value is part of the VALUE and is encoded (`%3D`), and the
   parameter is pushed once per chosen facet: every one ANDs, server-side. */
/* Facet query parts shared by kind lists and the Documents browser — ONE spelling of
   `facet=name=value`, so a second copy cannot drift into a bare `?domain=` again. */
function kFacetQuery(kind){
  const parts = [];
  if (K_QUERY) parts.push("q=" + encodeURIComponent(K_QUERY));
  const chosen = K_FACET[kind] || {};
  Object.keys(chosen).forEach(f => { if (chosen[f]) parts.push("facet=" + encodeURIComponent(f + "=" + chosen[f])); });
  const cursor = (K_TRAIL[kind] || [""])[K_AT[kind] || 0] || "";
  if (cursor) parts.push("cursor=" + encodeURIComponent(cursor));
  parts.push("limit=" + K_LIMIT);
  return parts.join("&");
}
function kListPath(kind){
  return encodeURIComponent(kind) + "?" + kFacetQuery(kind);
}
/* THE PRD FINDER'S PATH (ENG-10915). Same chrome as a kind list — toolbar, pager, entity rows —
   but the filters are NAMED query parameters on `/api/prds` (`status`, `slice`, `program`,
   `on_board`) rather than repeatable `facet=name=value`, because PRDs are Delivery and that
   route already took `?slice=` before this page existed. The host maps the `prds?…` path onto
   `/api/prds`; this file still does not know a URL. */
function kPrdsPath(){
  const parts = [];
  if (K_QUERY) parts.push("q=" + encodeURIComponent(K_QUERY));
  const chosen = K_FACET.prds || {};
  ["status", "slice", "program", "on_board"].forEach(f => {
    if (chosen[f]) parts.push(encodeURIComponent(f) + "=" + encodeURIComponent(chosen[f]));
  });
  const cursor = (K_TRAIL.prds || [""])[K_AT.prds || 0] || "";
  if (cursor) parts.push("cursor=" + encodeURIComponent(cursor));
  parts.push("limit=" + K_LIMIT);
  return "prds?" + parts.join("&");
}
/* DOCUMENTS BROWSER (ENG-10916). Same chrome as a kind list against `/api/knowledge/documents`.
   Facets are type / lifecycle / home. Not a seventh knowledge kind — a generic file index. */
function kDocsPath(){
  return "documents?" + kFacetQuery("documents");
}
/* Path keeps real slashes so FastAPI's `{path}` converter matches; each segment is escaped. */
function kDocsEntityPath(path){
  return "documents/" + String(path || "").split("/").map(encodeURIComponent).join("/");
}
function kSearchPath(){ return "search?q=" + encodeURIComponent(K_QUERY) + "&limit=" + K_LIMIT; }
function kEntityPath(kind, id){ return encodeURIComponent(kind) + "/" + encodeURIComponent(id); }

const kItems = res => (res && (res.items || res.rows)) || [];
const kNext = res => (res && (res.next_cursor || res.nextCursor)) || "";
/* A RESPONSE'S FACETS, IN EITHER SHAPE IT MIGHT DECLARE THEM: a list of `{key, label, values}`,
   or a bare map of key to values. Both are read; neither is invented. A corpus that serves no
   facets draws no dropdowns, which is an honest "there is nothing to narrow by" rather than a row
   of empty controls. */
/* A FACET'S FIELD ID OR RAW VALUE, SAID IN WORDS: `on_board` is "On board", `prd-drafted` is "PRD drafted",
   `true` is "Yes". Only a lowercase machine word is rewritten — an id with a capital or a digit (`SL-173`,
   `ENG-12`) is the thing itself and is left exactly as it is, and a label the server already wrote is never
   touched (the caller passes it through when it differs from the raw value). */
const K_ACRONYMS = { prd: "PRD", pr: "PR", ci: "CI", id: "ID", ux: "UX", api: "API", url: "URL", adr: "ADR" };
function kWord(raw){
  const s = String(raw == null ? "" : raw);
  if (s === "true") return "Yes";
  if (s === "false") return "No";
  if (!/^[a-z][a-z_-]*$/.test(s)) return s;
  const words = s.split(/[_-]+/).filter(Boolean).map(w => K_ACRONYMS[w] || w);
  const first = words[0];
  if (first && !K_ACRONYMS[first.toLowerCase()]) words[0] = first.charAt(0).toUpperCase() + first.slice(1);
  return words.join(" ");
}
/* THE SERVER'S OWN LABEL WINS; a label that is just the raw key gets the words. */
function kLabelled(label, raw){
  return label && String(label) !== String(raw) ? String(label) : kWord(raw);
}
function kFacets(res){
  const f = (res && res.facets) || [];
  if (Array.isArray(f)) return f.map(g => { const key = g.key || g.facet;
    return { key, label: kLabelled(g.label, key), values: g.values || [] }; });
  return Object.keys(f).map(key => ({ key, label: kWord(key), values: f[key] || [] }));
}
/* THE DETAIL RESPONSE'S TWO SHAPES, AND BOTH ARE READ RATHER THAN ONE BEING DEMANDED.
   A stamped envelope carries the row under its own key — `{entity, relations, findings}`, which
   is what happens the moment a response has to say which reading it came from and the row stops
   being the whole body — and a baked payload IS the row, with its edges folded onto it. Neither
   is invented here: the first is what `/api/knowledge/{kind}/{id}` serves and the second is what
   every host without a server answers with.

   MEASURED, NOT ANTICIPATED. The shipped page read the flat shape against a server serving the
   nested one, so every detail page rendered its name, its chips, its summary and its facts blank
   while the payload carrying all four sat one key down — and the page did not throw, which is
   why it shipped green. The merge is a copy: the edges and the findings are taken from the
   RESPONSE when it names them and from the row when it does not. */
function kEntity(res){
  const r = (res && typeof res === "object") ? res : {};
  const e = (r.entity && typeof r.entity === "object") ? r.entity : r;
  const out = {};
  Object.keys(e).forEach(k => { out[k] = e[k]; });
  if (r.relations !== undefined) out.relations = r.relations;
  if (r.findings !== undefined) out.findings = r.findings;
  return out;
}

/* A RESPONSE'S RELATIONS, IN EITHER SHAPE IT MIGHT DECLARE THEM — `kFacets`' own rule, one
   register down. A list of groups, each naming its verb (`verb`, or `rel`/`key` from a host that
   spells it either of those ways) and its own heading; or a bare map of verb to rows, which a
   payload with nothing to say about ordering can still produce. A group's own `label` wins
   outright; `K_REL` is the floor, and a verb neither knows renders under the verb itself rather
   than under a blank heading. */
function kRelations(e){
  const rel = (e && e.relations) || [];
  const named = g => {
    const key = g.verb || g.rel || g.key || "";
    return { key: key, label: g.label || K_REL[key] || key, note: g.note || "", items: g.items || [] };
  };
  if (Array.isArray(rel)) return rel.map(named);
  return Object.keys(rel).map(key => named({ key, items: rel[key] }));
}

/* ── the rows ────────────────────────────────────────────────────────────── */

/* ONE ENTITY AS AN `entityList` ROW, whatever its kind — which is the whole claim of the shape.
   `sev` is the left-edge mark every list on this board already uses: a row with something to do
   about it is marked, a row that is merely a fact is not. */
function kRow(e, kind){
  const k = e.kind || kind;
  const flags = e.flags || {};
  /* THE ROUTE IS HANDED OVER RAW: `entityList` and `entityHeader` write it through `link`,
     which escapes the one time — a route escaped here as well would reach the page with its
     ampersands doubled. */
  return { id: e.id, title: e.name || e.id, sub: e.summary || "",
           /* A PRD IS NOT A KNOWLEDGE KIND (ENG-10704, R2-02): "Ships in" built `knowledge:prd:<n>`, a
              route no index holds, so every capability's PRD opened "No such prd". */
           go: k === "prd" ? "prd:" + e.id : "knowledge:" + k + ":" + e.id,
           sev: flags.startable || flags.unshipped || flags.undocumented ? 2 : 3,
           badges: (e.chips || []).map(c => badge(c.text, c.cls)) };
}

/* THE CALL TO ACTION, AND THE TWO ROWS IT MAY NEVER APPEAR ON.
   An `excluded` row records a refusal and an `accepted` row records a cost taken on purpose.
   A Start button under either argues against the row it is sitting beneath — so those two get a
   stated section saying why there is no command, and the finding is dropped even if one was
   served. The server is expected not to emit one; this is the second half of the same rule,
   because a rule enforced in one place is a rule that holds until the other place changes. */
function kSettled(e){
  const f = e.flags || {};
  return f.excluded ? "excluded" : f.accepted ? "accepted" : "";
}
function kFindings(e){
  return kSettled(e) ? [] : ((e.findings || []).filter(a => a && a.id));
}
function kCta(e){
  const found = kFindings(e);
  if (!found.length) return "";
  return grp("What to do here", found.length,
    "The same rows the board raises on a program or a slice — a finding, and the command that "
    + "moves it. `route` rather than a PRD: the ladder decides whether the work is a PRD, a slice "
    + "or a task, and that is route's job rather than this page's.",
    entityList(actionItems(found)));
}
function kStated(e){
  const settled = kSettled(e);
  if (settled === "excluded"){
    return grp("Deliberately not built", null, "Why there is no command here.",
      `<p class="empty-note">This row records a refusal. It is not a gap and there is nothing to
       start. It stays in the register with its reason beside it &mdash; a rejection whose reason
       has quietly expired is the most valuable row in the file, and it can only be spotted while
       the reason is still written down.</p>`);
  }
  if (settled === "accepted"){
    return grp("A cost we took on purpose", null, "Why there is no command here.",
      `<p class="empty-note">This row records an accepted cost, not an outstanding one. Nothing
       claims it because there is nothing to build &mdash; what it needs is re-reading when the
       premise it rested on changes.</p>`);
  }
  return "";
}

/* ── the tab ─────────────────────────────────────────────────────────────── */

/* EVERY KIND, ONE ROW EACH, UNDER THE QUESTION IT ANSWERS — eight groups out of `KGUIDE`, and a
   row folds open to say how to tell the kind apart from its neighbours, where it lives, who writes
   it, and what one looks like. THE ROWS STILL NAVIGATE: a kind the payload counts carries its
   count, and the count opens that kind's list exactly as the old one-line rows did. The fold-out
   explains; it never replaces the way in. A kind with no list route has no link, and a kind the
   payload does not count shows no figure — never one this file made up.

   PLACEMENT IS STILL DATA WHEN THE PAYLOAD HAS IT. A served kind's own `section` wins over the
   group `KGUIDE` files it under, so a corpus that moves a kind moves its row; a kind the index
   serves and the list does not know is a plain row under the group its section names, or the
   last group when the section names none.

   NO FETCH. This view is a directory of what the payload already describes, so it answers on a
   board whose server is unreachable and costs nothing to open — the lists behind it are where
   the reads are. */
/* Which rows the reader has open, held across repaints (`toggle`, below) — and the one a link
   from another page asked for (`kindLink`), which the router scrolls to once and forgets. The
   capability row starts open: it is the row a first-time reader most needs unfolded, and it shows
   the page's one affordance without a sentence saying it exists. */
const K_OPEN = new Set(["capability"]);
let K_JUMP = "";

const KG_LIFE = {
  setup: `<span class="chip kg-setup">written at setup</span>`,
  grows: `<span class="chip kg-grows">grows with work</span>`,
  gen: `<span class="chip kg-gen">generated</span>`,
};

/* A ROW'S FIGURE, OR NONE. Read off what this page already holds: the corpus index's per-kind
   counts and its Documents count, the board's own programs, slices and PRDs, and the agent tree's
   slots. Everything else has no figure, because nothing loaded here counts it. */
function kgCount(item){
  const k = kKind(item.id);
  if (k) return { n: String(kCount(k)), unit: item.unit || "", go: kServed() ? "knowledge:" + item.id : "" };
  if (item.id === "documents"){
    const c = KINDEX && KINDEX.documents && KINDEX.documents.count != null ? Number(KINDEX.documents.count) : null;
    return c == null ? null : { n: String(c), unit: item.unit, go: kServed() ? "knowledge:documents" : "" };
  }
  if (D === null) return null;
  if (item.id === "program" && kAreasMode()){
    /* A PROGRAM THAT IS COMPLETE, WITHDRAWN OR WAIVED IS HISTORY, NOT "IN PLAY". */
    const open = D.programs.filter(p => ["complete", "withdrawn", "waived"].indexOf(p.state) < 0).length;
    return { n: String(D.programs.length), unit: `${open} open`, go: "board" };
  }
  if (item.id === "program"){
    const t = programTally();
    return { n: String(t.all), unit: `${t.inPlay} in play`, go: "board" };
  }
  if (item.id === "slice") return { n: String((D.totals || {}).slices || 0), unit: item.unit, go: "deps" };
  /* PRDs ARE DELIVERY, NOT A KNOWLEDGE KIND (ENG-10915). The finder needs a server (`/api/prds`);
     without one the row still names the count the board already holds, and carries no link that
     could only say "not here". Each finder row's destination stays `prd:<n>`. */
  if (item.id === "prd") return { n: String(Object.keys(PRD).length), unit: item.unit, go: kServed() ? "knowledge:prds" : "" };
  if (item.id === "slots"){
    const t = cmdTree();
    const all = (t && t.slots) || [];
    return all.length ? { n: `${all.filter(s => s.filled).length} of ${all.length}`, unit: "answered", go: "" } : null;
  }
  return null;
}

/* THE EXAMPLE, in the shape the kind takes in a repository: a table row, a card, or a numbered list. */
function kgSpec(ex){
  let body;
  if (ex.shape === "row"){
    body = `<div class="kg-sp-tw"><table class="kg-sp-table"><thead><tr>${ex.cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead>
      <tbody><tr>${ex.vals.map((v, i) => `<td${i ? "" : ` class="kg-sp-id"`}>${esc(v)}</td>`).join("")}</tr></tbody></table></div>`;
  } else if (ex.shape === "list"){
    body = `<div class="kg-sp-c"><div class="kg-sp-title">${esc(ex.title)}</div><ol class="kg-sp-ol">${ex.items.map((it, i) =>
      `<li${i === ex.hi ? ` class="kg-sp-hi"` : ""}>${esc(it)}${i === ex.hi ? ` <span class="chip kg-setup">promise</span>` : ""}</li>`).join("")}</ol></div>`;
  } else {
    body = `<div class="kg-sp-c"><div class="kg-sp-head"><span class="chip">${esc(ex.id)}</span><span class="kg-sp-title">${esc(ex.title)}</span></div>
      <dl class="kg-sp-dl">${ex.f.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl></div>`;
  }
  return `<figure class="kg-spec"><figcaption><span class="kg-sp-k">Example</span><span class="kg-sp-src">${esc(ex.src)}</span></figcaption>${body}</figure>`;
}

/* ONE KIND. `k` is the served index's entry for it, when there is one — its title, its blurb and
   its chips win over the list's, as they always did. */
function kgRow(item, k){
  const nm = k ? kTitle(k.kind) : item.nm;
  const def = k ? kBlurb(k) : item.def;
  const cnt = kgCount(item);
  const fig = cnt ? `${esc(cnt.n)}${cnt.unit ? `<small>${esc(cnt.unit)}</small>` : ""}` : "";
  const count = cnt && cnt.go ? link(cnt.go, "kg-cnt", fig, ` aria-label="${esc(`Open the list: ${cnt.n} ${nm}`)}"`)
    : `<span class="kg-cnt">${fig}</span>`;
  const chips = k ? (k.chips || []).map(c => badge(c.text, c.cls)).join("") : "";
  const facts = `<dl class="kg-facts"><dt>How to tell</dt><dd>${esc(item.tell)}</dd>${
    item.vs ? `<dt>Not to confuse</dt><dd>${esc(item.vs)}</dd>` : ""}<dt>Lives in</dt><dd><code>${esc(item.where)}</code></dd>
    <dt>Written by</dt><dd>${esc(item.by)}</dd></dl>`;
  const open = cnt && cnt.go ? `<p class="kg-open">${link(cnt.go, "kg-open-a", `See all ${esc(nm.toLowerCase())} &rarr;`)}</p>` : "";
  return `<details class="kg-row" id="k-${esc(item.id)}" data-krow="${esc(item.id)}"${K_OPEN.has(item.id) ? " open" : ""}>
    <summary class="kg-sum" data-keep="k-${esc(item.id)}"><span class="kg-c">${(item.life || []).map(c => KG_LIFE[c] || "").join("")}</span>
      <span><span class="kg-nm">${esc(nm)}</span>${chips ? " " + chips : ""}<span class="kg-def">${mdown(def)}</span></span>
      ${count}<span class="kg-chev" aria-hidden="true">&#9656;</span></summary>
    <div class="kg-body"><div class="kg-fold"><div>${facts}${open}</div>${kgSpec(item.ex)}</div></div>
  </details>`;
}
/* A KIND THE INDEX SERVES AND THE LIST DOES NOT KNOW — under its own name, with its count and its
   way in, and nothing this file would have to invent to fold open. */
function kgBare(k){
  const go = kServed() ? "knowledge:" + k.kind : "";
  const n = esc(String(kCount(k)));
  return `<div class="kg-row" id="k-${esc(k.kind)}"><div class="kg-sum"><span class="kg-c"></span>
      <span><span class="kg-nm">${esc(kTitle(k.kind))}</span>${(k.chips || []).map(c => " " + badge(c.text, c.cls)).join("")}${
        kBlurb(k) ? `<span class="kg-def">${mdown(kBlurb(k))}</span>` : ""}</span>
      ${go ? link(go, "kg-cnt", n) : `<span class="kg-cnt">${n}</span>`}<span class="kg-chev"></span></div></div>`;
}

/* HOW THE MAIN KINDS FIT TOGETHER — drawn once, in the page's own tokens so it follows the theme. */
const KG_MAP = `<div class="kg-map"><svg viewBox="0 0 980 300" role="img" aria-label="Diagram: components own code; capabilities are grouped into features and walked by journeys; requirements constrain them; programs, slices and PRDs change them.">
  <defs><marker id="kg-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--faint)"/></marker></defs>
  <g fill="none" stroke="var(--rule-2)" stroke-width="1.5">
    <rect x="10" y="18" width="680" height="268" rx="3" stroke-dasharray="4 4"/>
    <rect x="730" y="18" width="240" height="268" rx="3" stroke-dasharray="4 4"/>
  </g>
  <text x="24" y="40" fill="var(--faint)" font-size="11" font-family="IBM Plex Mono, monospace" letter-spacing="1.2">DESCRIBES THE PRODUCT · NEVER "FINISHED"</text>
  <text x="744" y="40" fill="var(--faint)" font-size="11" font-family="IBM Plex Mono, monospace" letter-spacing="1.2">THE WORK · COMPLETES</text>
  <g font-size="14" font-weight="700">
    <rect x="30" y="140" width="130" height="50" rx="3" fill="var(--surface)" stroke="var(--proven)" stroke-width="1.5"/><text x="95" y="162" text-anchor="middle" fill="var(--ink)">Component</text><text x="95" y="179" text-anchor="middle" fill="var(--muted)" font-size="11" font-weight="400">owns code</text>
    <rect x="230" y="140" width="130" height="50" rx="3" fill="var(--surface)" stroke="var(--proven)" stroke-width="1.5"/><text x="295" y="162" text-anchor="middle" fill="var(--ink)">Capability</text><text x="295" y="179" text-anchor="middle" fill="var(--muted)" font-size="11" font-weight="400">something one can do</text>
    <rect x="430" y="70" width="130" height="50" rx="3" fill="var(--surface)" stroke="var(--proven)" stroke-width="1.5"/><text x="495" y="92" text-anchor="middle" fill="var(--ink)">Feature</text><text x="495" y="109" text-anchor="middle" fill="var(--muted)" font-size="11" font-weight="400">groups capabilities</text>
    <rect x="430" y="210" width="130" height="50" rx="3" fill="var(--surface)" stroke="var(--proven)" stroke-width="1.5"/><text x="495" y="232" text-anchor="middle" fill="var(--ink)">Journey</text><text x="495" y="249" text-anchor="middle" fill="var(--muted)" font-size="11" font-weight="400">walks capabilities</text>
    <rect x="230" y="56" width="130" height="50" rx="3" fill="var(--surface)" stroke="var(--brass-edge)" stroke-width="1.5"/><text x="295" y="78" text-anchor="middle" fill="var(--ink)">Requirement</text><text x="295" y="95" text-anchor="middle" fill="var(--muted)" font-size="11" font-weight="400">a rule that always holds</text>
    <rect x="30" y="56" width="130" height="50" rx="3" fill="var(--surface)" stroke="var(--brass-edge)" stroke-width="1.5"/><text x="95" y="78" text-anchor="middle" fill="var(--ink)">Decision</text><text x="95" y="95" text-anchor="middle" fill="var(--muted)" font-size="11" font-weight="400">why, and what we refused</text>
    <rect x="785" y="60" width="130" height="44" rx="3" fill="var(--surface)" stroke="var(--flight)" stroke-width="1.5"/><text x="850" y="87" text-anchor="middle" fill="var(--ink)">Program</text>
    <rect x="785" y="140" width="130" height="44" rx="3" fill="var(--surface)" stroke="var(--flight)" stroke-width="1.5"/><text x="850" y="167" text-anchor="middle" fill="var(--ink)">Slice</text>
    <rect x="785" y="220" width="130" height="44" rx="3" fill="var(--surface)" stroke="var(--flight)" stroke-width="1.5"/><text x="850" y="247" text-anchor="middle" fill="var(--ink)">PRD</text>
  </g>
  <g stroke="var(--faint)" stroke-width="1.4" fill="none" marker-end="url(#kg-ar)">
    <path d="M160 165 H226"/><path d="M360 158 L426 104"/><path d="M360 172 L426 226"/><path d="M295 106 V136"/><path d="M160 81 H226"/><path d="M850 104 V136"/><path d="M850 184 V216"/>
    <path d="M785 242 C720 242 690 280 620 280 L360 280 C310 280 295 240 295 194"/>
  </g>
  <g font-size="11" fill="var(--muted)">
    <text x="193" y="158" text-anchor="middle">enables</text>
    <text x="376" y="122" transform="rotate(-38 376 122)">grouped in</text>
    <text x="384" y="180" transform="rotate(38 384 180)">walked by</text>
    <text x="302" y="126">constrains</text>
    <text x="166" y="74">explains</text>
    <text x="858" y="124">cut into</text>
    <text x="858" y="204">built by</text>
    <text x="604" y="232">a PRD adds or changes these</text>
  </g>
</svg></div>`;

/* ── PLANNING BY FEATURE AREA (`D.planningMode === "areas"`) ─────────────────────────────────
 * A repository that plans by area has no open program and takes no new one; every live slice
 * names the feature area it belongs to (the owner's decision to plan by feature). The page
 * says so: the map's work column reads Feature → Slice → PRD, the Delivery rows describe slices
 * inside a feature, and "Work by feature" draws the drill-down the model now has. A repository
 * still on programs draws the page exactly as before. */
function kAreasMode(){ return !!D && D.planningMode === "areas"; }

const KG_MAP_AREAS = KG_MAP
  .replace(/<rect x="785" y="60"[^]*?Program<\/text>\n/, "")
  .replace('<rect x="785" y="140" width="130" height="44" rx="3" fill="var(--surface)" stroke="var(--flight)" stroke-width="1.5"/><text x="850" y="167"',
           '<rect x="785" y="73" width="130" height="44" rx="3" fill="var(--surface)" stroke="var(--flight)" stroke-width="1.5"/><text x="850" y="100"')
  .replace('<rect x="785" y="220" width="130" height="44" rx="3" fill="var(--surface)" stroke="var(--flight)" stroke-width="1.5"/><text x="850" y="247"',
           '<rect x="785" y="200" width="130" height="44" rx="3" fill="var(--surface)" stroke="var(--flight)" stroke-width="1.5"/><text x="850" y="227"')
  .replace('<path d="M850 104 V136"/><path d="M850 184 V216"/>', '<path d="M560 95 H781"/><path d="M850 117 V196"/>')
  .replace('<path d="M785 242 C720 242', '<path d="M785 222 C720 222')
  .replace('<text x="858" y="124">cut into</text>', '<text x="575" y="88">is cut into slices</text>')
  .replace('<text x="858" y="204">built by</text>', '<text x="858" y="162">built by</text>')
  .replace("programs, slices and PRDs change them.", "slices and PRDs change them.")
  .replace('<text x="604" y="232">a PRD adds or changes these</text>', '<text x="580" y="222">a PRD adds or<tspan x="580" dy="14">changes these</tspan></text>');

/* THE DELIVERY ROWS, REWRITTEN FOR A REPOSITORY THAT PLANS BY AREA. A program is shown once, as
   history; a theme is deferred and is no kind at all. */
const KG_AREAS_ROWS = {
  slice: { def: "A planning cut inside one feature, with its own “done when”.",
    tell: "It completes, and “done” means more than each of its PRDs being done. Every slice names the feature it belongs to.",
    where: "slices/, one row each, naming its feature",
    ex: { shape: "card", src: "slices/SL-001.md", id: "SL-001", title: "Reorder from order history",
          f: [["Feature", "ordering"], ["Done when", "a buyer reorders end to end on staging"]] } },
  prd: { ex: { shape: "card", src: "prds/0001-reorder-button/prd.md", id: "0001", title: "Reorder button on order history",
          f: [["Slice", "SL-001"], ["Feature", "ordering"], ["Status", "planned"], ["Promises", "CAP-0031, ORD-012"]] } },
  program: { nm: "Programs (closed)", life: [],
    def: "The grouping above slices that this repository used before it planned by feature. Every program here is closed and no new one is created; the old ids stay readable.",
    tell: "You only meet one when reading old work: a PG-NN id on a finished slice or a decision.",
    where: "programs/ (history, never rewritten)", by: "Nobody, any more.",
    ex: { shape: "card", src: "programs/PG-08.md", id: "PG-08", title: "A closed program",
          f: [["State", "superseded by features"], ["Slices", "moved to their feature"]] } },
  outcome: { where: "a kind of slice; no file of its own" },
};
const KG_AREAS_ORDER = { delivery: ["slice", "prd", "program", "idea"] };
const KG_AREAS_DROP = { theme: 1 };
function kGuide(){
  if (!kAreasMode()) return KGUIDE;
  return KGUIDE.map(g => {
    const items = g.items.filter(i => !KG_AREAS_DROP[i.id]).map(i => Object.assign({}, i, KG_AREAS_ROWS[i.id] || {}));
    const order = KG_AREAS_ORDER[g.id];
    if (order) items.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
    return Object.assign({}, g, { items });
  });
}

/* ── is this knowledge base ready to build on? ─────────────────────────────────
 * THE ANSWER THAT HEADS THE KNOWLEDGE PAGE (owner-approved mockup
 * the knowledge-readiness mockup under `knowledge/mockups/`): one verdict for the whole repository,
 * read from where the team has actually been changing code — `fleet_knowledge.readiness`, measured
 * by the sync and served at `api/knowledge/readiness`. Figures first, then the verdict and what
 * stands in the way, then the repository's parts in one list grouped by state, ranked by how much of
 * the recent change lands on each.
 *
 * READ ONCE PER REPOSITORY, the way the feature list is: `kBoot` clears it when the selection
 * moves, so another repository's verdict is never drawn over this one's corpus. A failed read is
 * its own state with a Try again, never an empty block that reads like "nothing to say". */
let K_READY = null;
let K_READY_ERR = "";
const KR_CHIP = {
  unmapped: ["kr-dash", "No part"],
  undescribed: ["", "Not described"],
  partial: ["attn-ish", "Partly described"],
  described: ["complete", "Described"],
  review: ["unproven", "Waiting on you"],
  stale: ["attn", "Changed"],
  drafted: ["flight", "Being described"],
};
/* A DESCRIPTION RUN'S OWN STATE, `api/part.py`'s words: it wins over the part's measured state while a run exists, because
   the measurement reads main and a run's pull request is not on main yet. */
const KR_RUN_CHIP = {
  running: ["now", "Describing"],
  waiting: ["wait", "Waiting on you"],
  "pr-open": ["flight", "PR open"],
  failed: ["attn", "Did not finish"],
  stopped: ["", "Stopped"],
  parked: ["", "Paused"],
};
const KR_STEPS = ["Survey", "Read files", "Draft", "Check with you", "Write &amp; open PR"];
const KR_SEG = { described: "kr-seg-done", review: "wt", stale: "kr-seg-stale", drafted: "run" };
const KR_SHOWN = 7;
/* THE PAGE'S OWN STATE FOR THE PARTS TABLE, all of it a person's or a reading's and none of it a thing a tick may reset:
   `K_PFOLD` a row's own fold (absent = the default for its state), `K_PSEEN` the run state last drawn (so a part that STARTS
   waiting is unfolded once), `K_PASKS` the question sets a waiting part owes, `K_PANS` the half-made answers (by set id, so
   a re-read never takes one), `K_PBUSY` a write in flight, `K_PERR` what a refused write said. */
let K_PALL = false;
let K_PFOLD = {};
let K_PSEEN = {};
let K_PASKS = {};
let K_PANS = {};
let K_PBUSY = {};
let K_PERR = {};
let K_PART = null;
let K_READY_BUSY = false;
function krPartReset(){ K_PALL = false; K_PFOLD = {}; K_PSEEN = {}; K_PASKS = {}; K_PANS = {}; K_PBUSY = {}; K_PERR = {}; }
function krPct(x){ return `${Math.round((Number(x) || 0) * 100)}%`; }
function krFmt(n){ return (Number(n) || 0).toLocaleString("en-US"); }
function krRunOf(p){ const r = p && p.run; return r && r.state && r.state !== "idle" ? r : null; }
/* A ROW HAS SOMETHING TO FOLD once a description exists for it: steps while it runs, questions while it waits, the pull request
   when it is open, the reason when it failed or stopped. */
function krFoldable(p){ return !!krRunOf(p); }
function krOpen(p){
  if (!krFoldable(p)) return false;
  if (Object.prototype.hasOwnProperty.call(K_PFOLD, p.id)) return !!K_PFOLD[p.id];
  return krRunOf(p).state === "waiting";
}
function krQuestions(p){
  const a = K_PASKS[p.id];
  if (!a || !a.sets) return null;
  return a.sets.reduce((n, s) => n + ((s.questions || []).length), 0);
}
/* WHAT THE PAGE DOES WITH EACH READING: a part that STARTED waiting is unfolded once, and a waiting part's questions are
   fetched (once per change of what it owes). Nothing else is forced on a re-read. */
function krApply(){
  const parts = K_READY && K_READY.reading && Array.isArray(K_READY.reading.parts) ? K_READY.reading.parts : [];
  parts.forEach(p => {
    const r = krRunOf(p);
    const now = r ? r.state : "idle";
    const was = K_PSEEN[p.id];
    if (now === "waiting" && was !== undefined && was !== "waiting") K_PFOLD[p.id] = true;
    if (now !== "waiting" && was === "waiting" && K_PASKS[p.id]) delete K_PASKS[p.id];
    K_PSEEN[p.id] = now;
    if (now === "waiting" && K_PART && K_PART.asks){
      const sig = `${r.openQuestions}:${r.step}`;
      const held = K_PASKS[p.id];
      if (!held || (held.sig !== sig && !held.loading)){
        K_PASKS[p.id] = { sig: sig, sets: held ? held.sets : null, loading: true, err: "" };
        K_PART.asks(r.key || `PART-${p.id}`).then(sets => {
          K_PASKS[p.id] = { sig: sig, sets: (Array.isArray(sets) ? sets : []).filter(s => s && Array.isArray(s.questions) && s.questions.length), loading: false, err: "" };
          krRedraw();
        }, err => {
          K_PASKS[p.id] = { sig: sig, sets: null, loading: false, err: (err && err.message) ? String(err.message) : String(err) };
          krRedraw();
        });
      }
    }
  });
}
function krRedraw(){ const r = routeParts(openRoute()); if (r[0] === "knowledge" && !r[1]) render(openRoute()); }
/* RE-READ, KEEPING WHAT IS DRAWN. Called by the host when the dispatch or inbox topic moved; a failed re-read leaves the
   reading on screen. It declines before the first reading has landed (that read is its own) and while one is in flight. */
function kReadyReload(){
  if (!KNOWLEDGE_LOADER || !K_READY || K_READY.state === "loading" || K_READY_BUSY) return;
  K_READY_BUSY = true;
  KNOWLEDGE_LOADER("readiness").then(
    p => { K_READY_BUSY = false; if (p) { K_READY = p; krApply(); } krRedraw(); },
    () => { K_READY_BUSY = false; });
}
function kReadyLoad(){
  if (K_READY !== null || !KNOWLEDGE_LOADER || !kServed()) return;
  K_READY = { state: "loading" };
  K_READY_ERR = "";
  KNOWLEDGE_LOADER("readiness").then(
    p => { K_READY = p || { state: "pending" }; krApply(); krRedraw(); },
    err => { K_READY = { state: "error" };
             K_READY_ERR = (err && err.message) ? String(err.message) : String(err); krRedraw(); });
}
function krChip(p, r){
  const c = r && r.stalled ? ["attn", "Not started"] : r ? (KR_RUN_CHIP[r.state] || KR_CHIP.undescribed) : (KR_CHIP[p.state] || KR_CHIP.undescribed);
  return `<span class="chip ${c[0]}">${c[1]}</span>`;
}
function krNote(p, r){
  if (r){
    if (r.state === "running" && r.stalled) return `<span class="kr-fail">not picked up &middot; can be stopped</span>`;
    if (r.state === "running") return `<span class="rd-none">started by ${esc(PEOPLE_NAMES[r.startedBy] || dpWho(r.startedBy || "someone"))}</span>`;
    if (r.state === "waiting"){
      const n = krQuestions(p);
      return `all files read &middot; ${n == null ? "questions" : n + (n === 1 ? " question" : " questions")}`;
    }
    if (r.state === "pr-open") return "counts once the PR is merged";
    if (r.state === "failed") return "stopped &middot; can be retried";
    if (r.state === "stopped") return "stopped &middot; nothing written";
    if (r.state === "parked") return "paused at its time limit";
  }
  if (p.unmapped) return `<span class="rd-none">${esc(String(p.files == null ? "" : p.files))} files</span>`;
  if (p.state === "undescribed") return `<span class="rd-none">nothing read yet</span>`;
  if (p.state === "partial" && p.unreadFiles) return `<b>${krFmt(p.unreadFiles)}</b> ${p.unreadFiles === 1 ? "file" : "files"} unread`;
  if (p.state === "described" || p.state === "stale") return p.capabilities ? `${esc(String(p.capabilities))} ${p.capabilities === 1 ? "capability" : "capabilities"}` : `<span class="rd-none">${esc(p.description || "")}</span>`;
  return `<span class="rd-none">${esc(p.description || "")}</span>`;
}
function krBar(p, r){
  let pct = 0, cls = KR_SEG[p.state] || "kr-seg-done";
  if (r){
    cls = r.state === "waiting" ? "wt" : r.state === "pr-open" ? "kr-seg-done" : "run";
    pct = r.state === "waiting" || r.state === "pr-open" ? 100 : (r.filesTotal ? Math.min(100, r.filesRead / r.filesTotal * 100) : 0);
  } else if (p.state === "described") pct = 100;
  return `<span class="bar"><i class="${cls}" style="width:${pct.toFixed(1)}%"></i></span>`;
}
function krAction(p, r, open){
  const id = esc(p.id);
  const busy = !!K_PBUSY[p.id];
  const dis = busy ? " disabled" : "";
  if (!r){
    if (p.unmapped || (p.state !== "undescribed" && p.state !== "partial" && p.state !== "stale")) return `<span class="rd-none">&mdash;</span>`;
    return K_PART && K_PART.act
      ? `<button class="act sm" type="button" data-kp="describe:${id}" data-keep="kp-go-${id}"${dis}>Describe</button>` : `<span class="rd-none">&mdash;</span>`;
  }
  if (r.state === "running" && r.stalled)
    return `<button class="act primary sm" type="button" data-kp="stop:${id}" data-keep="kp-stop-${id}"${dis}>Stop</button>`;
  if (r.state === "running"){
    const step = Math.min(Math.max(r.step || 1, 1), 5);
    const live = open ? `Describing&hellip; &middot; step ${step} of 5` : `step ${step} of 5 &middot; ${KR_STEPS[step - 1].replace("&amp;", "&")}`;
    return link("runs:issue=" + (r.key || "PART-" + p.id), "lnk", live);
  }
  if (r.state === "waiting"){
    const n = krQuestions(p);
    return `<button class="act primary sm" type="button" data-kp="answer:${id}" data-keep="kp-ans-${id}">Answer ${n == null ? "questions" : n + (n === 1 ? " question" : " questions")}</button>`;
  }
  if (r.state === "pr-open")
    return r.prUrl ? `<a class="act primary sm" href="${esc(r.prUrl)}" target="_blank" rel="noopener">Open PR</a>` : `<span class="rd-none">&mdash;</span>`;
  if (r.state === "failed")
    return `<button class="act primary sm" type="button" data-kp="continue:${id}" data-keep="kp-re-${id}"${dis}>${open ? "Retry" : "Did not finish &middot; Retry"}</button>`;
  return `<button class="act primary sm" type="button" data-kp="continue:${id}" data-keep="kp-re-${id}"${r.continuable && !busy ? "" : " disabled"}>Continue</button>`;
}
function krStepper(p, r){
  const step = Math.min(Math.max(r.step || 1, 1), 5);
  const id = esc(p.id);
  let out = "";
  KR_STEPS.forEach((name, i) => {
    const k = i + 1;
    const cls = k < step || r.state === "pr-open" ? "done"
      : k === step ? (r.state === "waiting" ? "wait" : r.state === "failed" ? "fail" : r.state === "running" ? "now" : "") : "";
    out += `<span class="${cls}">${k} ${name}</span>`;
  });
  let extra = "";
  if (r.state === "running" && r.stalled)
    extra = ` <span class="kr-fail">${esc(r.failure || "No run has started.")}</span>`;
  else if (r.state === "running")
    extra = " " + (K_PART && K_PART.act ? `<a class="lnk" role="button" tabindex="0" data-kp="stop:${id}">Stop</a>` : "");
  if (r.state === "stopped" || r.state === "parked")
    extra = ` <span class="note kr-inl">${esc(r.failure || (r.state === "parked" ? "Paused at its time limit." : "Stopped."))} Nothing was written to your repository.${r.continuable ? (r.filesRead ? " Continue picks up at the files not read yet." : " Continue starts from the beginning.") : ""}</span>`;
  if (r.state === "failed")
    extra = ` <span class="kr-fail">${esc(r.failure || "The run failed.")}${r.filesTotal ? ` It had read ${krFmt(r.filesRead)} of ${krFmt(r.filesTotal)} files.` : ""} Nothing was written to your repository. Retry continues from the files already read.</span>`;
  return `<div class="steps" data-stepper="${id}">${out}${extra}</div>`;
}
function krHeld(setId, qid){ return (K_PANS[setId] || {})[qid]; }
function krAnswerOf(h){
  if (!h) return null;
  if (h.cant === true) return { cantAnswer: true };
  if (h.optionId) return { optionId: h.optionId };
  const said = String(h.text || "").trim();
  return said ? { text: said } : null;
}
function krComplete(p){
  const a = K_PASKS[p.id];
  if (!a || !a.sets || !a.sets.length) return false;
  return a.sets.every(s => s.questions.every(q => !!krAnswerOf(krHeld(s.id, q.id))));
}
function krEnc(s){ return encodeURIComponent(String(s)); }
function krOption(s, q, o, held){
  const sel = held && held.optionId === o.id;
  const facts = [o.then, o.why && `Why: ${o.why}`, o.cost && `Cost: ${o.cost}`].filter(Boolean).map(x => esc(String(x))).join(" ");
  return `<button type="button" class="op${sel ? " sel" : ""}" aria-pressed="${sel ? "true" : "false"}" data-kp="pick:${krEnc(s.id)}:${krEnc(q.id)}:${krEnc(o.id)}">`
    + `<span class="dot"></span><span><b>${esc(o.label || "")}${o.recommended === true ? `<span class="rec">recommended</span>` : ""}</b>${facts ? `<small>${facts}</small>` : ""}</span></button>`;
}
function krCard(s, q, i){
  const held = krHeld(s.id, q.id) || {};
  const opts = (q.options || []).map((o, n) => [o, n]).sort((a, b) => ((b[0].recommended === true) - (a[0].recommended === true)) || (a[1] - b[1])).map(x => x[0]);
  const key = `${krEnc(s.id)}:${krEnc(q.id)}`;
  return `<div class="qc"><p class="q">${i}. ${esc(q.prompt || "")}</p>${q.context ? `<p class="why">${esc(String(q.context))}</p>` : ""}`
    + opts.map(o => krOption(s, q, o, held)).join("")
    + `<textarea class="ft" rows="1" maxlength="4000" data-kp-text="${key}" data-keep="kp-ft-${esc(s.id)}-${esc(q.id)}" placeholder="Or say it in your own words&hellip;">${esc(held.text || "")}</textarea>`
    + `<div class="qskip">${held.cant ? `<span class="chip">skipped</span> <a class="lnk" role="button" tabindex="0" data-kp="unskip:${key}">undo</a>`
      : `<a class="lnk" role="button" tabindex="0" data-kp="skip:${key}">Can&rsquo;t answer &mdash; carry on</a>`}</div></div>`;
}
function krPanel(p){
  const id = esc(p.id);
  const a = K_PASKS[p.id];
  let body;
  if (!a || a.loading && !a.sets) body = `<p class="note">Reading the questions&hellip;</p>`;
  else if (a.err) body = `<p class="note">The questions could not be read: ${esc(a.err)} <a class="lnk" role="button" tabindex="0" data-kp="reask:${id}">Try again</a></p>`;
  else if (!a.sets || !a.sets.length) body = `<p class="note">Fleet is waiting on an answer, but no question is open on the page right now.</p>`;
  else {
    let i = 0;
    const ok = krComplete(p);
    const sending = K_PBUSY[p.id] === "send";
    body = a.sets.map(s => s.questions.map(q => krCard(s, q, ++i)).join("")).join("")
      + `<div class="qfoot"><span>${ok ? "All answered. The run resumes when you send." : "Answer or skip each question to send."}</span><span>`
      + `<button class="act sm" type="button" data-kp="skipall:${id}"${sending ? " disabled" : ""}>Can&rsquo;t answer any &mdash; carry on</button> `
      + `<button class="act primary sm" type="button" data-kp="send:${id}" data-keep="kp-send-${id}"${ok && !sending ? "" : " disabled"}>Send answers</button></span></div>`;
  }
  const err = K_PERR[p.id] ? `<p class="kr-fail">${esc(K_PERR[p.id])}</p>` : "";
  return `<div class="qpanel" data-qpanel="${id}"><p class="note kr-inl">Fleet has read everything ${id} owns and drafted what it saw. It will not promise anything on your behalf.</p>${body}${err}</div>`;
}
function krRow(p){
  const r = krRunOf(p);
  const open = krOpen(p);
  const id = esc(p.id);
  const fold = krFoldable(p);
  const tri = fold ? `<span class="tri${open ? " openx" : ""}" data-kp="toggle:${id}" role="button" aria-expanded="${open}" aria-label="${open ? "Fold" : "Unfold"} ${id}"></span>` : `<span class="tri off"></span>`;
  const name = fold ? `<span class="lt-nm kr-fold" data-kp="toggle:${id}">${id}</span>`
    : p.unmapped ? `<span class="lt-nm">${id}</span>` : link("knowledge:component:" + p.id, "lt-nm", id);
  let x = "";
  if (open){
    if (r.state === "pr-open") x = `<p class="note kr-inl">The pull request for ${id} is open. It counts toward readiness once it is merged.${r.prUrl ? ` <a class="lnk" href="${esc(r.prUrl)}" target="_blank" rel="noopener">Open it</a>` : ""}</p>`;
    else x = krStepper(p, r) + (r.state === "waiting" ? krPanel(p) : "");
  }
  const err = !open && K_PERR[p.id] ? `<p class="kr-fail kr-rowerr">${esc(K_PERR[p.id])}</p>` : "";
  return `<div class="pp" data-row="${id}" data-open="${open}"><div class="rt${r && (r.state === "running" || r.state === "waiting") ? " now" : ""}">`
    + `<span class="rt-p">${tri}${name}</span><span class="rt-s">${krChip(p, r)}</span>`
    + `<span class="rt-sh" title="${esc(krPct(p.share))} of the code changes in the window"><b>${krPct(p.share)}</b></span>`
    + `<span class="rt-b">${krBar(p, r)}<span class="rd-n">${krNote(p, r)}</span></span>`
    + `<span class="rt-c">${krAction(p, r, open)}</span></div>${x ? `<div class="pp-x">${x}</div>` : ""}${err}</div>`;
}
function krStat(value, label, need, tone){
  return `<div class="stat kr-stat${tone ? " " + tone : ""}"><b>${value}</b><span>${esc(label)}</span><small>${need ? esc(need) : "&nbsp;"}</small></div>`;
}
function kReadySection(){
  if (!KNOWLEDGE_LOADER || !kServed()) return "";
  kReadyLoad();
  const st = K_READY && K_READY.state;
  if (!K_READY || st === "loading")
    return `<div class="empty-note kr-empty">Reading whether this knowledge base is ready to build on&hellip;</div>`;
  if (st === "error" || st === "failed")
    return `<div class="banner kr-verdict"><b>Whether this knowledge base is ready to build on could not be read.</b> `
      + `${esc(st === "failed" ? (K_READY.failure || "") : K_READY_ERR)} `
      + `<button type="button" class="act" data-kr-retry>Try again</button></div>`;
  if (st === "pending")
    return `<div class="empty-note kr-empty">Fleet has not measured this repository yet. It does on the next sync.</div>`;
  const r = K_READY.reading || {};
  if (r.schema !== 1) return "";
  const f = r.figures || {}, pol = r.policy || {};
  const parts = (Array.isArray(r.parts) ? r.parts : []).slice().sort((a, b) => (b.share || 0) - (a.share || 0));
  const under = (x, line) => x < line ? "attn" : "";
  /* THE QUESTIONS TILE: what the waiting parts owe now, else the reading's (unknown on the server, so a dash). */
  const waiting = parts.filter(p => (krRunOf(p) || {}).state === "waiting");
  const owed = waiting.reduce((n, p) => n + (krQuestions(p) == null ? (krRunOf(p).openQuestions || 0) : krQuestions(p)), 0);
  const q = waiting.length ? esc(String(owed)) : (f.questions == null ? "&mdash;" : esc(String(f.questions)));
  const strip = `<div class="strip kr-strip">`
    + krStat(krPct(f.coverage), "Change described", `need ${krPct(pol.threshold)}`, under(f.coverage, pol.threshold))
    + krStat(`${esc(String(f.described))} of ${esc(String(f.components))}`, "Parts described", "", "")
    + krStat(krPct(f.owned), "Code on the map", `need ${krPct(pol.owned)}`, under(f.owned, pol.owned))
    + krStat(q, "Questions for you", "", !waiting.length && f.questions ? "brass" : "")
    + krStat(esc(String(f.promisesChecked || 0)), "Promises checked", "", "")
    + `</div>`;
  const win = esc((r.window || {}).label || "window");
  const active = parts.filter(p => { const s = (krRunOf(p) || {}).state; return s === "running" || s === "waiting"; }).length;
  const note = active > 1 ? `<p class="note kr-multi" id="kr-multi">${active} parts being described</p>` : "";
  const blockers = (Array.isArray(r.blockers) ? r.blockers : []).filter(b => b.kind !== "coverage");
  const tag = { targets: "Basics", vision: "Basics", map: "Map", history: "History", coverage: "Coverage",
                blindspot: "Blind spot", questions: "Questions", stale: "Changed", unread: "Unread" };
  const ids = (r.describeNext || []).map(id => parts.find(p => p.id === id)).filter(p => p && !p.unmapped && !krRunOf(p));
  const sugg = ids[0];
  const covers = `${krPct(f.coverage)} of the code changes in the ${win} land on described parts (${krPct(pol.threshold)} needed).`;
  const verdict = r.verdict === "ready"
    ? `<div class="rd-head ok kr-verdict kr-ok" role="status"><h2>Ready to build on</h2><p>${covers} The remaining parts change rarely and can wait.</p>${note}</div>`
    : `<div class="rd-head kr-verdict kr-no" role="status"><h2>${r.verdict === "too-little-history" ? "Not enough history to say yet" : "Not ready to build yet"}</h2>`
      + `<p>${r.verdict === "too-little-history" ? "" : covers}${sugg ? ` Fleet suggests <b>${esc(sugg.id)}</b> next; it alone covers ${krPct(sugg.share)}.` : ""}</p>${note}`
      + (blockers.length ? `<ul class="strand-rows">${blockers.map(b => `<li><span class="chip kr-tag">${esc(tag[b.kind] || b.kind)}</span><span class="kr-why">${esc(b.text)}</span><span class="kr-act"></span></li>`).join("")}</ul>` : "")
      + `</div>`;
  const shown = K_PALL ? parts : parts.slice(0, KR_SHOWN);
  const head = `<div class="rd-h"><span>Parts to describe next</span><span>showing ${shown.length} of ${parts.length} parts &middot; sorted by share of recent change`
    + (parts.length > KR_SHOWN ? ` &middot; <a class="lnk" role="button" tabindex="0" data-kp="all:">${K_PALL ? "show fewer" : "show all " + parts.length}</a>` : "")
    + ` &middot; <a class="lnk" role="button" tabindex="0" data-kp="foldall:">Fold all</a> / <a class="lnk" role="button" tabindex="0" data-kp="unfoldall:">Unfold all</a>`
    + `</span></div>`;
  const table = parts.length ? `<div class="kr-tbl">` + head + `<div class="rd-card kr-list"><div class="rcol"><span>Part</span><span>State</span><span>Share</span><span>Read</span><span>Action</span></div>${shown.map(krRow).join("")}</div></div>` : "";
  const older = K_READY.failure ? `<p class="kr-note">The last measurement could not be made, so this one is older: ${esc(K_READY.failure)}</p>` : "";
  return strip + verdict + older + table + `<div class="kr-sep" aria-hidden="true"></div>`;
}
/* A WRITE: the part's own route, through the host. A refusal (`409 already-describing`, `base-not-current`...) is said beside the
   row it concerns, and nothing is drawn as started that the server did not accept. */
function krAct(id, action){
  if (!K_PART || !K_PART.act || K_PBUSY[id]) return;
  K_PBUSY[id] = action;
  delete K_PERR[id];
  if (action === "start") K_PFOLD[id] = true;
  krRedraw();
  Promise.resolve(K_PART.act(id, action)).then(
    () => { delete K_PBUSY[id]; kReadyReload(); krRedraw(); },
    err => { delete K_PBUSY[id]; K_PERR[id] = (err && err.message) ? String(err.message) : String(err); krRedraw(); });
}
function krSend(id, skipRest){
  const a = K_PASKS[id];
  if (!K_PART || !K_PART.answer || !a || !a.sets || K_PBUSY[id]) return;
  if (skipRest) a.sets.forEach(s => s.questions.forEach(q => {
    if (!krAnswerOf(krHeld(s.id, q.id))) (K_PANS[s.id] = K_PANS[s.id] || {})[q.id] = { cant: true };
  }));
  if (!a.sets.every(s => s.questions.every(q => krAnswerOf(krHeld(s.id, q.id))))) { krRedraw(); return; }
  K_PBUSY[id] = "send";
  delete K_PERR[id];
  krRedraw();
  Promise.all(a.sets.map(s => K_PART.answer(s.id, s.questions.map(q => Object.assign({ questionId: q.id }, krAnswerOf(krHeld(s.id, q.id))))))).then(
    () => {
      a.sets.forEach(s => { delete K_PANS[s.id]; });
      delete K_PBUSY[id]; delete K_PASKS[id];
      K_PFOLD[id] = false;
      kReadyReload(); krRedraw();
    },
    err => { delete K_PBUSY[id]; K_PERR[id] = (err && err.message) ? String(err.message) : String(err); krRedraw(); });
}
if (document.addEventListener){
  document.addEventListener("click", e => {
    const t = e.target && e.target.closest ? e.target : null;
    if (!t) return;
    if (t.closest("[data-kr-retry]")){ K_READY = null; krPartReset(); render(openRoute()); return; }
    const kp = t.closest("[data-kp]");
    if (!kp || kp.disabled) return;
    const raw = kp.getAttribute("data-kp");
    const at = raw.indexOf(":");
    const act = raw.slice(0, at);
    const rest = raw.slice(at + 1).split(":").map(decodeURIComponent);
    const parts = K_READY && K_READY.reading && Array.isArray(K_READY.reading.parts) ? K_READY.reading.parts : [];
    const part = parts.find(p => p.id === rest[0]);
    if (act === "describe") return krAct(rest[0], "start");
    if (act === "stop") return krAct(rest[0], "stop");
    if (act === "continue") return krAct(rest[0], "continue");
    if (act === "toggle" && part){ K_PFOLD[part.id] = !krOpen(part); return render(openRoute()); }
    if (act === "answer" && part){
      K_PFOLD[part.id] = true;
      render(openRoute());
      const panel = document.querySelector ? document.querySelector(`[data-qpanel="${part.id}"]`) : null;
      if (panel && panel.scrollIntoView) panel.scrollIntoView({ block: "center" });
      return;
    }
    if (act === "all"){ K_PALL = !K_PALL; return render(openRoute()); }
    if (act === "foldall" || act === "unfoldall"){
      parts.forEach(p => { if (krFoldable(p)) K_PFOLD[p.id] = act === "unfoldall"; });
      return render(openRoute());
    }
    if (act === "pick"){ (K_PANS[rest[0]] = K_PANS[rest[0]] || {})[rest[1]] = { optionId: rest[2] }; return render(openRoute()); }
    if (act === "skip"){ (K_PANS[rest[0]] = K_PANS[rest[0]] || {})[rest[1]] = { cant: true }; return render(openRoute()); }
    if (act === "unskip"){ delete (K_PANS[rest[0]] || {})[rest[1]]; return render(openRoute()); }
    if (act === "skipall") return krSend(rest[0], true);
    if (act === "send") return krSend(rest[0], false);
    if (act === "reask"){ delete K_PASKS[rest[0]]; krApply(); return render(openRoute()); }
  });
  /* A DRAFT IS HELD AS IT IS TYPED and the page is not repainted for it: only the Send button is re-derived in place, so the
     caret stays where the person left it (a repaint on a later reading keeps the focused field by its `data-keep`). */
  document.addEventListener("input", e => {
    const t = e.target && e.target.closest ? e.target.closest("[data-kp-text]") : null;
    if (!t) return;
    const [setId, qid] = t.getAttribute("data-kp-text").split(":").map(decodeURIComponent);
    const said = String(t.value || "");
    const set = (K_PANS[setId] = K_PANS[setId] || {});
    if (said.trim()) set[qid] = { text: said }; else if (set[qid] && !set[qid].optionId && !set[qid].cant) delete set[qid];
    const parts = K_READY && K_READY.reading && Array.isArray(K_READY.reading.parts) ? K_READY.reading.parts : [];
    const owner = parts.find(p => K_PASKS[p.id] && (K_PASKS[p.id].sets || []).some(s => s.id === setId));
    const send = owner && document.querySelector ? document.querySelector(`[data-keep="kp-send-${owner.id}"]`) : null;
    if (send) send.disabled = !krComplete(owner) || K_PBUSY[owner.id] === "send";
  });
}

/* THE FEATURE LIST, read once per repository the way the corpus index is: the Knowledge page
   itself makes no other request, so an unreadable list leaves the page as it was. */
let K_AREAS = null;
let K_AREAS_ERR = false;
let K_AREAS_DONE = false;
let K_AREAS_MORE = 0;
let K_WF = "live";
/* THE LIST IS PAGED (the list route's ceiling is 200 a page) and the page follows `next_cursor`, a few pages
   at most, so no feature is dropped silently. A read that fails leaves K_AREAS_ERR set and a retry button. */
function kAreasLoad(){
  if (K_AREAS !== null || !KNOWLEDGE_LOADER || !kServed()) return;
  K_AREAS = [];
  K_AREAS_ERR = false;
  K_AREAS_DONE = false;
  K_AREAS_MORE = 0;
  const redraw = () => { const r = routeParts(openRoute()); if (r[0] === "knowledge" && !r[1]) render(openRoute()); };
  const page = (path, left) => KNOWLEDGE_LOADER(path).then(p => {
    K_AREAS = K_AREAS.concat((p && p.items) || []);
    const next = p && p.next_cursor;
    if (next && left > 0) return page("area?cursor=" + encodeURIComponent(next) + "&limit=100", left - 1);
    if (next) K_AREAS_MORE = Number(p.total) || 1;
  });
  page("area?limit=100", 9).then(() => { K_AREAS_DONE = true; redraw(); }, () => { K_AREAS_ERR = true; redraw(); });
}
const KWF_LIVE = ["flight", "awaiting-proof", "empty"];
function kwfLive(s){ return KWF_LIVE.indexOf(s.state) >= 0; }
function kwfSlices(){
  const by = {};
  Object.keys(SL).forEach(id => { const s = SL[id]; (by[s.area || ""] = by[s.area || ""] || []).push(s); });
  Object.keys(by).forEach(a => by[a].sort((x, y) => (kwfLive(y) - kwfLive(x)) || String(y.id).localeCompare(String(x.id))));
  return by;
}
function kwfPrd(p){
  return `<li class="kwf-prd">${link("prd:" + p.n, "chip link", esc(p.n))}<span class="kwf-t">${esc(p.title || "")}</span>${
    badge(p.status, p.status === "shipped" ? "complete" : p.status === "cancelled" ? "withdrawn" : "flight")}</li>`;
}
function kwfSlice(s){
  const prds = s.prds || [];
  const head = `<span class="kwf-id">${link("slice:" + s.id, "chip link", esc(s.id))}</span>
    <span class="kwf-t"><b>${esc(s.name)}</b><span class="kwf-dw">${esc(firstSentence(s.done_when || "", 150))}</span></span>
    <span class="kwf-st">${s.kind ? `<span class="chip kind">${esc(s.kind)}</span>` : ""}${sliceStateChip(s)}</span>`;
  if (!prds.length) return `<li class="kwf-sl"><div class="kwf-sh">${head}</div></li>`;
  return `<li class="kwf-sl"><details data-krow="wfs:${esc(s.id)}"${K_OPEN.has("wfs:" + s.id) ? " open" : ""}>
    <summary class="kwf-sh">${head}<span class="kwf-n">${prds.length}<small>PRDs</small></span><span class="kg-chev" aria-hidden="true">&#9656;</span></summary>
    <ul class="kwf-prds">${prds.map(kwfPrd).join("")}</ul></details></li>`;
}
function kwfRow(key, name, blurb, slices, tag, goArea){
  const live = slices.filter(kwfLive).length;
  const chips = (live ? `<span class="chip flight">${live} live</span>` : "") + (tag || "");
  return `<details class="kg-row kwf-row" id="wf-${esc(key)}" data-krow="wf:${esc(key)}"${K_OPEN.has("wf:" + key) ? " open" : ""}>
    <summary class="kg-sum" data-keep="wf-${esc(key)}"><span class="kg-c">${chips}</span>
      <span><span class="kg-nm">${esc(name)}</span><span class="kg-def">${esc(blurb)}</span></span>
      <span class="kg-cnt">${slices.length}<small>slices</small></span><span class="kg-chev" aria-hidden="true">&#9656;</span></summary>
    <div class="kg-body kwf-body"><ul class="kwf-sls">${slices.map(kwfSlice).join("")}</ul>${
      goArea ? `<p class="kg-open">${link("knowledge:area:" + key, "kg-open-a", `Open the feature &rarr;`)}</p>` : ""}</div></details>`;
}
/* THE DRILL-DOWN: feature → slice → PRD. `bare` is the form that sits inside another row. */
function kwfTree(bare){
  if (K_AREAS_ERR) return `<p class="note">The feature list could not be read. <button type="button" class="kwf-seg" data-kwf-retry="1">Try again</button></p>`;
  if (K_AREAS === null || (K_AREAS.length === 0 && !K_AREAS_DONE)) return `<p class="note">Reading the feature list&hellip;</p>`;
  const by = kwfSlices();
  const known = {};
  K_AREAS.forEach(a => { known[a.id] = 1; });
  const mine = a => by[a.id] || [];
  const areas = K_AREAS.slice().sort((a, b) => (mine(b).filter(kwfLive).length - mine(a).filter(kwfLive).length)
    || (mine(b).length - mine(a).length) || String(a.name).localeCompare(String(b.name)));
  const shown = areas.filter(a => K_WF === "all" || mine(a).filter(kwfLive).length);
  const rows = shown.map(a => kwfRow(a.id, a.name, firstSentence(String(a.summary || "").replace(/[*`]/g, ""), 130), mine(a), "", true));
  /* A SLICE NAMING A FEATURE THE INDEX DOES NOT HOLD IS SHOWN, NEVER DROPPED. */
  Object.keys(by).filter(a => a && !known[a]).forEach(a => {
    const sl = by[a];
    if (K_WF !== "all" && !sl.some(kwfLive)) return;
    rows.push(kwfRow(a, a, "Named by its slices; no feature map with this id in the corpus.", sl, `<span class="chip attn">no feature map</span>`, false));
  });
  const none = by[""] || [];
  if (none.length && K_WF === "all")
    rows.push(kwfRow("none", "Closed before slices named a feature", "Finished and withdrawn slices from the program era. History is not rewritten.", none, `<span class="chip waived">history</span>`, false));
  const nLive = Object.keys(SL).filter(i => kwfLive(SL[i])).length;
  const seg = (k, label) => `<button type="button" class="kwf-seg${K_WF === k ? " on" : ""}" data-kwf="${k}" aria-pressed="${K_WF === k}">${label}</button>`;
  const bar = `<div class="kwf-bar" role="group" aria-label="Which features to list">${seg("live", `With live work`)}${seg("all", `All features`)}
    <span class="kwf-sum">${rows.length} ${rows.length === 1 ? "feature" : "features"} &middot; ${nLive} live slices</span></div>`;
  const more = K_AREAS_MORE ? `<p class="note">Showing the first ${K_AREAS.length} of ${K_AREAS_MORE} features.</p>` : "";
  const none0 = more + (K_AREAS.length ? "" : `<p class="note">The corpus holds no feature maps yet, so only the features slices name are listed.</p>`);
  return bar + none0 + (rows.length ? `<div class="box">${rows.join("")}</div>` : `<p class="note">No feature has live work.</p>`);
}
function kwfSection(){
  return `<section class="grp" id="k-workbyfeature" aria-labelledby="kg-workbyfeature"><div class="grp-h">
      <h3 id="kg-workbyfeature">Work by feature</h3><span class="n">Which slices are changing which feature?</span></div>
    <p class="grp-b">Every slice belongs to one feature. Open a feature to see its slices, and a slice to see the PRDs that build it.
      Programs are closed in this repository, so they are not a way in.</p>${kwfTree()}</section>`;
}
if (document.addEventListener){
  document.addEventListener("click", e => {
    const rt = e.target && e.target.closest ? e.target.closest("[data-kwf-retry]") : null;
    if (rt){ K_AREAS = null; render(openRoute()); return; }
    const b = e.target && e.target.closest ? e.target.closest("[data-kwf]") : null;
    if (!b) return;
    K_WF = b.getAttribute("data-kwf");
    render(openRoute());
  });
}

function viewKnowledge(){
  const state = kIndexState();
  const kinds = KKINDS.slice();
  /* FOUR ANSWERS, AND THREE OF THEM ARE NOT "an empty corpus". The Delivery rows are this file's
     own registers and render under every one of them, so the page is never blank. */
  const note = state === "absent"
      ? `<p class="note">This board has no server to read the corpus from, so the kinds below carry
         no counts and no id on any other page links into one. The deployed board answers it; a
         standalone page is the plan, read out of git.</p>`
    : state === "loading" ? `<p class="note">Reading the corpus index&hellip;</p>`
    : state === "failed" ? `<div class="banner"><b>${esc(KINDEX_ERR)}</b></div>`
    /* AN INDEX WITH A KIND FOR EVERYTHING AND A ROW FOR NOTHING IS THE EMPTY CORPUS, and it is
       the ordinary shape of a lane whose `knowledge/` holds a slot registry and nothing else:
       the server describes every kind it knows how to read and counts zero under each. Told
       apart from "no index at all" on the counts, and said in the corpus's own terms, so a
       reader who picked that lane learns the repository holds nothing rather than that this
       page failed to read it. */
    : kinds.length && kinds.every(k => !(Number(kCount(k)) || 0))
    ? `<p class="note" data-empty="index">This repository carries no knowledge index &mdash; every
       kind below counts nothing, so no id on any other page links into one. That is a fact about
       the corpus rather than about this page.</p>`
    : kinds.length ? ""
    : `<p class="note">This deployment serves no knowledge index, so the kinds below carry no
       counts and no id on any other page links into one. That is a fact about the corpus rather
       than about this page.</p>`;
  const GUIDE = kGuide();
  if (kAreasMode()) kAreasLoad();
  const ids = new Set(GUIDE.map(g => g.id));
  const rows = {};
  GUIDE.forEach(g => { rows[g.id] = []; });
  GUIDE.forEach(g => g.items.forEach(item => {
    const k = kKind(item.id);
    const at = k && k.section && ids.has(k.section) ? k.section : g.id;
    rows[at].push(kgRow(item, k));
  }));
  kinds.filter(k => !KGUIDE_BY[k.kind]).forEach(k => {
    const at = ids.has(kSection(k)) ? kSection(k) : GUIDE[GUIDE.length - 1].id;
    rows[at].push(kgBare(k));
  });
  const groupHtml = g => `<section class="grp" aria-labelledby="kg-${g.id}"><div class="grp-h">
      <h3 id="kg-${g.id}">${esc(g.h)}</h3><span class="n">${esc(g.q)}</span></div>
      <div class="box">${rows[g.id].join("")}</div></section>`;
  const groups = GUIDE.map(g => (g.id === "delivery" && kAreasMode() ? kwfSection() : "") + groupHtml(g)).join("");
  const desk = EXTRA.quality ? `<p class="kg-open">${link("quality", "kg-open-a", "Open the Quality desk &rarr;")}</p>` : "";
  /* THE PROMISE COUNTS ARE NOT HERE, AND THAT IS THE DATA'S ANSWER. They are the Quality desk's
     reading (`/api/quality/promises`), which this page does not load; a figure printed here would
     be one this file made up. */
  const promises = `<section class="grp" id="k-promises" aria-labelledby="kg-promises"><div class="grp-h">
      <h3 id="kg-promises">What the Quality desk checks</h3></div>
    <p class="grp-b">A promise is something the product has already committed to. Of everything on
      this page, the Quality desk checks only these three, against the live product, every night. A
      promise counts as kept only when a check passed it with evidence and a second reviewer did not
      dispute it.</p>
    <div class="kg-promise">
      <div><b>Capabilities</b><p>Every capability marked as shipped.</p></div>
      <div><b>Requirements</b><p>Every adopted rule that is not deferred.</p></div>
      <div><b>Journey criteria</b><p>Every numbered criterion of a live journey.</p></div>
    </div>${desk}</section>`;
  /* THE DEPLOYMENT'S OWN WORDS — box, lane, claim, run — are explained where they are used, and a
     standalone board has none of them, so only a page whose host contributed a vocabulary says so. */
  const fleetWords = TERMS_EXTRA && (TERMS_EXTRA() || []).length
    ? `<p class="kg-callout">Words that belong to Fleet itself rather than to your product (box, lane,
       claim, run and the rest) are not on this page. They show a short definition when you hover
       over them or tap them, wherever they appear.</p>` : "";
  return pageHead("Knowledge") + kReadySection() +
    `<p class="kg-intro">Everything Fleet knows about this product, kept as files in the repository
      under <code>knowledge/</code>. It records who the product is for, what it is made of, what
      people can do with it, what it promises, how those promises are checked, and the work under
      way to change it. Agents read it before they plan or build anything, and the Quality desk
      checks the live product against its promises.</p>` + note +
    `<section class="grp" aria-labelledby="kg-map"><div class="grp-h"><h3 id="kg-map">How the main kinds fit together</h3></div>
      <p class="grp-b">Read it from the left. Components own the code. Capabilities are what the code
        lets someone do. Features group capabilities, and journeys walk through them.
        Requirements are rules that hold across all of it. The delivery kinds, on the right, are the
        work that changes the rest. Everything else on this page supports one of these.</p>
      ${kAreasMode() ? KG_MAP_AREAS : KG_MAP}
      <div class="kg-legend"><span>${KG_LIFE.setup} the knowledge bootstrap writes it</span>
        <span>${KG_LIFE.grows} added as work happens; empty at first</span>
        <span>${KG_LIFE.gen} computed from the rest; never edited by hand</span></div>
    </section>` + groups + promises + fleetWords;
}

/* A WAY INTO ONE ROW OF THE KNOWLEDGE PAGE, for a page that names a kind — the Build page's tiles
   and its steps' outputs. A real link to `#knowledge` (so it opens in a new tab like any other),
   which on a plain click also opens that row and scrolls to it. An id the list does not hold is
   the words alone, never a link to a row that is not there. */
function knowledgeGuide(){ return KGUIDE; }
/* HOW A PERSON TYPES AN AGENT IN THIS REPOSITORY (`/<ns>:<name>`), read off where the agents
   live — see `cmdNamespace`. A page that wrote the namespace down would be right in one
   repository and wrong in the next. */
function invocation(name){ return cmdInvocation(cmdTree(), { name: String(name || "") }); }
function kindLink(id, cls, inner){
  return KGUIDE_BY[id] ? link("knowledge", cls, inner, ` data-kjump="${esc(id)}"`) : `<span class="${cls}">${inner}</span>`;
}

/* ── one kind, listed ────────────────────────────────────────────────────── */

/* THE NARROWING ROW IS THE LIST PAGES' FILTER BAR (`filterBar`): the corpus search, and one field
   per facet the server serves, each a single choice (`K_FACET` holds one value a facet) with the
   server's count on every value. A corpus that serves no facets draws no Filter, which is an honest
   "there is nothing to narrow by". The narrowing stays module state (`K_FACET`, `K_QUERY`). */
function kBar(id, kind, res, shown, total){
  const chosen = kind ? (K_FACET[kind] || {}) : {};
  return filterBar({
    id,
    noun: ["entry", "entries"],
    matched: shown,
    count: `<span class="showing">${esc(String(shown))} ${total == null ? "" : `of ${esc(String(total))}`}</span>`,
    search: { value: K_QUERY, label: "Search this corpus", placeholder: "Search this corpus, or an id",
      tip: "Enter searches every kind at once; an id typed in full opens it." },
    fields: kind ? kFacets(res).map(f => ({ id: f.key, label: f.label, multi: false,
      value: chosen[f.key] ? [chosen[f.key]] : [],
      values: (f.values || []).map(v => {
        const value = String(v.value != null ? v.value : v);
        return { v: value, t: kLabelled(v.label, value), n: v.count != null ? v.count : null };
      }) })) : [],
    on: {
      set: (facet, vals) => {
        const mine = K_FACET[kind] || (K_FACET[kind] = {});
        mine[facet] = vals[0] || "";
        K_TRAIL[kind] = [""]; K_AT[kind] = 0;
        render(openRoute());
      },
      search: kSubmit,
      clear: () => {
        if (kind) K_FACET[kind] = {};
        if (kind){ K_TRAIL[kind] = [""]; K_AT[kind] = 0; }
        kSubmit("");
      },
    },
  });
}
function kToolbar(kind, res, shown, total){ return kBar("k-" + kind, kind, res, shown, total); }

/* THE PAGER, AND IT IS A CURSOR RATHER THAN AN OFFSET. A cursor is forward-only, so "previous"
   is the trail of cursors this reader has already been handed rather than a subtraction: the
   trail is truncated at the current position before a new cursor is pushed, so paging forward
   after paging back cannot leave a stale branch behind it. A page number is deliberately absent —
   a cursor does not know one, and printing one would be a count this page cannot stand behind. */
function kPager(res, at, shown){
  const more = !!kNext(res);
  if (!more && !at) return "";
  return `<div class="ctl">
    <span class="showing">${esc(String(shown))} on this page</span>
    <button class="act" data-kpage="prev"${at ? "" : " disabled"}>&lsaquo; Previous</button>
    <button class="act" data-kpage="next"${more ? "" : " disabled"}>Next &rsaquo;</button></div>`;
}

function kCrumbs(tail, tailGo){
  return `<nav class="crumbs">${link("knowledge", "lnk", "Knowledge")}
    <span class="sep">&rsaquo;</span>${tailGo
      ? link(tailGo, "lnk", esc(tail))
      : `<span class="here">${esc(tail)}</span>`}</nav>`;
}

function viewKList(kind){
  const crumbs = kCrumbs(kTitle(kind));
  const got = kHold(kListPath(kind));
  if (got.state !== "ready") return crumbs + pageHead(kTitle(kind)) + kState(got, kTitle(kind).toLowerCase());
  const res = got.data;
  const items = kItems(res);
  const k = kKind(kind);
  const total = res.total != null ? res.total : (k ? kCount(k) : items.length);
  /* NO NOTE UNDER THE LIST, AND THE ABSENCE IS THE FIX RATHER THAN AN OMISSION. A paragraph
     stood here saying "a row carries an id, a name and one clipped sentence — never prose" and
     then how many rows paging reached. Both halves were the page explaining itself: the first
     described the rows the reader was already looking at, which is a design rule written down
     where a reader can only read it as instructions; the second answered "how far does this
     list go?" in prose, when `kToolbar` already answers it as a figure — `25 of 1254` — and
     `kPager` already says `25 on this page` beside the two buttons that move it.
     It also leaked the machinery: "paging is a cursor on the API" is a fact about this service,
     not about the corpus, and "1254 rows cost what 25 cost" spends the word `cost` on a surface
     that shows no money at all. A sentence explaining how to read a number is a sign the number
     was not self-explaining; this one was, so the sentence goes. */
  return crumbs + pageHead(kTitle(kind)) +
    kToolbar(kind, res, items.length, total) +
    entityList(items.map(e => kRow(e, kind)), { empty: "Nothing in this corpus matches that." }) +
    kPager(res, K_AT[kind] || 0, items.length);
}

/* THE PRD FINDER (ENG-10915). Same toolbar, pager and entity rows as `viewKList`, against
   `/api/prds` rather than a knowledge kind — PRDs are Delivery and must not join `KINDS`. Each
   row goes to `prd:<n>` via `kRow`'s existing special case, never `knowledge:prd:<n>`. */
function viewKPrds(){
  const title = "PRDs";
  const crumbs = kCrumbs(title);
  const got = kHold(kPrdsPath());
  if (got.state !== "ready") return crumbs + pageHead(title) + kState(got, "PRDs");
  const res = got.data;
  const items = kItems(res);
  const total = res.total != null ? res.total : items.length;
  return crumbs + pageHead(title) +
    kToolbar("prds", res, items.length, total) +
    entityList(items.map(e => kRow(e, "prd")), { empty: "Nothing in this corpus matches that." }) +
    kPager(res, K_AT.prds || 0, items.length);
}

/* DOCUMENTS LIST (ENG-10916). Same toolbar, pager and entity rows as `viewKList`, against
   `/api/knowledge/documents`. Each row opens `knowledge:documents:<path>`. */
function viewKDocs(){
  const title = "Documents";
  const crumbs = kCrumbs(title);
  const got = kHold(kDocsPath());
  if (got.state !== "ready") return crumbs + pageHead(title) + kState(got, "documents");
  const res = got.data;
  const items = kItems(res);
  const total = res.total != null ? res.total : items.length;
  return crumbs + pageHead(title) +
    kToolbar("documents", res, items.length, total) +
    entityList(items.map(e => kDocRow(e)), { empty: "Nothing in this corpus matches that." }) +
    kPager(res, K_AT.documents || 0, items.length);
}

function kDocRow(e){
  const path = e.path || e.id || "";
  return {
    id: path,
    title: e.name || e.title || path,
    sub: e.summary || "",
    go: "knowledge:documents:" + path,
    sev: e.sev != null ? e.sev : 3,
    badges: (e.chips || []).map(c => badge(c.text, c.cls)),
  };
}

/* ONE DOCUMENT — facts first, body fetched like `kProse`. */
function viewKDoc(path){
  const crumbs = [{ label: "Knowledge", go: "knowledge" },
                  { label: "Documents", go: "knowledge:documents" },
                  { label: path }];
  const got = kHold(kDocsEntityPath(path));
  if (got.state !== "ready"){
    return kCrumbs("Documents", "knowledge:documents") + pageHead(path) + kState(got, path);
  }
  const e = kEntity(got.data);
  const head = entityHeader({
    crumbs,
    id: e.path || e.id || path,
    name: e.name || e.title || path,
    chips: (e.chips || []).map(c => badge(c.text, c.cls)),
    promise: e.summary || "",
    promiseNote: e.summary ? "" : "This file carries no summary.",
    facts: [
      e.type ? ["Type", mdown(e.type)] : null,
      e.lifecycle ? ["Lifecycle", mdown(e.lifecycle)] : null,
      e.home ? ["Home", mdown(e.home)] : null,
      e.path || path ? ["Path", mdown(e.path || path)] : null,
    ].filter(Boolean),
  });
  return head + kDocProse(path);
}

function kDocProse(path){
  if (!PROSE_LOADER) return "";
  const held = PROSE_CACHE[textKey(kDocsEntityPath(path))];
  const written = held === undefined || (held && held.err) ? "" : kBlocks(held);
  const body = held === undefined ? `<p class="empty-note">Reading the document&hellip;</p>`
    : held && held.err ? `<div class="banner"><b>${esc(String(held.err))}</b></div>`
    : written ? `<div class="md">${written}</div>`
    : `<p class="empty-note">The corpus holds no body for this file at this commit.</p>`;
  const source = (held && !held.err && typeof held === "object" && held.source) ? String(held.source) : "";
  return grp("In the corpus", null,
    "Fetched when you open this page, never shipped with the list."
    + (source ? " Authored in " + source + "." : ""), body);
}

/* ── across every kind at once ───────────────────────────────────────────── */

function viewKSearch(){
  const crumbs = kCrumbs("Search");
  if (!K_QUERY) return crumbs + pageHead("Search") + `<p class="empty-note">Type something to
    search this corpus, and press Enter.</p>`;
  const got = kHold(kSearchPath());
  if (got.state !== "ready") return crumbs + pageHead("Search") + kState(got, "the search");
  const res = got.data;
  /* A GROUPED ANSWER IN EITHER SHAPE: a list of groups, or a map of kind to rows. */
  const groups = Array.isArray(res.groups) ? res.groups
    : Object.keys(res.results || {}).map(kind => ({ kind, items: (res.results || {})[kind] }));
  const found = groups.reduce((n, g) => n + kItems(g).length, 0);
  return crumbs + pageHead("Search") +
    kBar("k-search", "", res, found, null) +
    (found ? groups.filter(g => kItems(g).length).map(g => grp(
       g.title || kTitle(g.kind), g.total != null ? g.total : kItems(g).length, "",
       entityList(kItems(g).map(e => kRow(e, g.kind))))).join("")
     : `<p class="empty-note">Nothing in this corpus matches that.</p>`);
}

/* ── one entity, whatever its kind ───────────────────────────────────────── */

/* ── THE JOURNEY PAGE (journey-v1) ─────────────────────────────────────────────────────────────────────────────────
   One journey read WHOLE, from `GET /api/knowledge/journey/<id>/page`: the server parses the journey file structurally and
   joins three facts no single read holds (each covered capability's build state, the owning PRD's status, each criterion's
   last result off the Quality desk). This function only DRAWS that answer; it decides nothing. What the file did not say it
   does not draw: a step with no annotation has no place chip and no capability chips, a branch naming no step is listed under
   the happy path, a `covers:` entry that resolves to nothing is shown as unresolved — never dropped and never guessed. */
const JP_CAP = { "built": ["built", "Built"], "not-built": ["notbuilt", "Not built"], "unresolved": ["unresolved", "Unresolved"] };
const JP_STEP = { "built": ["built", "Built"], "partial": ["notbuilt", "Part not built"], "not-built": ["notbuilt", "Not built"] };
/* THE LAST RESULT OF A CRITERION, as [chip class, label, what it means]. An unknown word reads as "not checked", the
   honest floor: a result the page cannot name is a result it must not call a pass. */
const JP_RESULT = {
  "pass": ["pass", "Pass", "A check passed on the current release"],
  "fail": ["fail", "Fail", "A check failed on the current release"],
  "out-of-date": ["stale", "Out of date", "A check exists but has not run on the current release"],
  "not-checked": ["none", "Not checked", "No result recorded"],
  "flaky": ["flaky", "Flaky", "The check passes and fails on the same release"],
  "disputed": ["disputed", "Disputed", "The result is disputed"],
  "quarantined": ["quarantined", "Quarantined", "The check is set aside"],
  "unfinished": ["unfinished", "Unfinished", "A check started and has not finished"],
  "cant-run": ["cant-run", "Can't run", "The check cannot run here"],
};
const jpResult = r => JP_RESULT[r] || JP_RESULT["not-checked"];
const jpChip = (cls, label, tip) => `<span class="jp-chip ${esc(cls)}"${tip ? ` title="${esc(tip)}"` : ""}><i class="jp-d"></i>${esc(label)}</span>`;
const jpInitials = name => {
  const w = String(name || "").trim().split(/\s+/).filter(Boolean);
  return (w.length > 1 ? w[0][0] + w[1][0] : (w[0] || "?").slice(0, 2)).toUpperCase();
};
const jpCount = (n, one, many) => `<span><b>${n}</b> ${n === 1 ? one : (many || one + "s")}</span>`;
/* A summary clipped on a word boundary, for a row that is an index. */
const jpClip = (s, n) => {
  const t = String(s || "").replace(/\s+/g, " ").trim();
  if (t.length <= n) return t;
  const cut = t.slice(0, n), sp = cut.lastIndexOf(" ");
  return (sp > n * 0.6 ? cut.slice(0, sp) : cut).replace(/[\s,;:.—-]+$/, "") + "…";
};
function jpCapChip(c){
  const tip = c.name ? ` title="${esc(c.name)}"` : "";
  return c.state === "unresolved"
    ? `<span class="jp-chip jp-cap unresolved"${tip}>${esc(c.id)}</span>`
    : link("knowledge:capability:" + c.id, "jp-chip jp-cap", esc(c.id), tip);
}
function jpBranches(list){
  if (!list.length) return "";
  return `<div class="jp-br"><div class="jp-br-t">If it goes another way</div>${list.map(b =>
    `<div class="jp-b"><b>${mdown(b.title)}</b>${b.disposition ? `<span>${mdown(b.disposition)}</span>` : ""}</div>`).join("")}</div>`;
}
function jpStep(s){
  const caps = s.capabilities || [];
  const chips = [];
  if (s.on) chips.push(`<span class="jp-chip jp-surf">${mdown(s.on)}</span>`);
  if (s.on && caps.length) chips.push(`<span class="jp-sep"></span>`);
  caps.forEach(c => chips.push(jpCapChip(c)));
  if (s.state && JP_STEP[s.state]) chips.push(jpChip(JP_STEP[s.state][0], JP_STEP[s.state][1]));
  return `<li><div class="jp-node ${esc(s.state || "")}">${esc(s.n)}</div><div class="jp-step"><h4>${mdown(s.title)}</h4>`
    + (s.text ? `<p>${mdown(s.text)}</p>` : "")
    + (chips.length ? `<div class="jp-meta">${chips.join("")}</div>` : "") + `</div>${jpBranches(s.branches || [])}</li>`;
}
function jpJob(job){
  if (job && job.when && job.want && job.so){
    return `<p class="jp-job"><em>When</em> ${mdown(job.when)}, <em>I want to</em> ${mdown(job.want)}, <em>so I can</em> ${mdown(job.so)}.</p>`;
  }
  return job && job.text ? `<p class="jp-job">${mdown(job.text)}</p>` : "";
}
function jpStrip(p){
  const caps = p.capabilities || [], crit = p.criteria || [], prd = p.owning_prd;
  const capBar = caps.map(c => c.state === "built" ? "ok" : "nb");
  const BAR = { "pass": "ok", "fail": "bad", "not-checked": "" };
  const critBar = crit.map(c => (c.result in BAR ? BAR[c.result] : "od"));
  const s = p.summary || {};
  const notBuilt = caps.length - s.built;
  const t1 = caps.length
    ? `<div class="jp-n">${s.built}<span> of ${caps.length} built</span></div><div class="jp-bar">${capBar.map(c => `<i class="${c}"></i>`).join("")}</div>`
      + `<p>${notBuilt ? `${notBuilt} not built${s.unresolved ? `, ${s.unresolved} unresolved` : ""}` : "All built"}</p>`
    : `<div class="jp-n">None<span> named</span></div><p>This journey covers no capability.</p>`;
  const t2 = crit.length
    ? `<div class="jp-n">${s.with_result}<span> of ${crit.length} criteria have a result</span></div><div class="jp-bar">${critBar.map(c => `<i class="${c}"></i>`).join("")}</div>`
      + `<p>${crit.length - s.with_result} not checked or out of date</p>`
    : `<div class="jp-n">None<span> yet</span></div><p>This journey lists no acceptance criteria.</p>`;
  const t3 = prd
    ? `<div class="jp-n">${link("prd:" + prd.n, "", esc(prd.n))}<span> ${esc(prd.found ? (prd.status || "no status") : "not in this reading")}</span></div><p>${esc(prd.title || "")}</p>`
    : `<div class="jp-n">None<span> named</span></div><p>This journey names no owning PRD.</p>`;
  return `<section class="jp-strip"><div><small>Capability behind it</small>${t1}</div><div><small>Last checked</small>${t2}</div><div><small>Built by</small>${t3}</div></section>`;
}
function jpCriteria(p){
  const crit = p.criteria || [];
  if (!crit.length) return "";
  const seen = new Set(crit.map(c => c.result));
  const legend = [`<span><span class="jp-chip dev">DEV</span> checkable on the local stack</span>`,
                  `<span><span class="jp-chip ext">EXT</span> needs a real install</span>`]
    .concat(["pass", "fail", "flaky", "disputed", "quarantined", "unfinished", "cant-run"].filter(r => seen.has(r)).map(r =>
      `<span>${jpChip(jpResult(r)[0], jpResult(r)[1])} ${esc(jpResult(r)[2].toLowerCase())}</span>`))
    .concat([`<span>${jpChip("stale", "Out of date")} a check exists, not run on this release</span>`,
             `<span>${jpChip("none", "Not checked")} no result recorded</span>`]);
  const desk = EXTRA.quality ? `<span class="jp-sub">${link("quality", "", "Open in the Quality desk")}</span>` : "";
  return `<section class="jp-card jp-sec" id="jp-criteria"><h3 class="jp-h">Acceptance criteria<span class="jp-c">${crit.length}</span>${desk}</h3>`
    + `<div class="jp-lead">Each is observable on the running product and keeps its number when the journey is edited.</div><ol class="jp-ac">`
    + crit.map(c => {
        const r = jpResult(c.result);
        return `<li><span class="jp-no">${esc(c.n)}</span><div class="jp-tx">${mdown(c.text)}</div><div class="jp-rs">`
          + (c.tier ? `<span class="jp-chip ${esc(c.tier)}" title="${c.tier === "dev" ? "Checkable on the local stack" : "Needs a real install, tracker or machine"}">${esc(c.tier.toUpperCase())}</span>` : "")
          + jpChip(r[0], r[1], r[2]) + `</div></li>`;
      }).join("")
    + `</ol><div class="jp-legend">${legend.join("")}</div></section>`;
}
function jpCovers(p){
  const caps = p.capabilities || [];
  if (!caps.length) return "";
  return `<section class="jp-card jp-sec"><h3 class="jp-h">Covers<span class="jp-c">${caps.length}</span><span class="jp-sub">capabilities this journey exercises</span></h3>`
    + caps.map(c => {
        const st = JP_CAP[c.state] || JP_CAP["unresolved"];
        return `<div class="jp-row"><span class="jp-k">${c.state === "unresolved" ? esc(c.id) : link("knowledge:capability:" + c.id, "", esc(c.id))}</span>`
          + `<div><b>${c.state === "unresolved" ? "Not found in this reading" : esc(c.name || c.id)}</b><small>${mdown(jpClip(c.summary, 170))}</small></div>`
          + `<span class="jp-st">${jpChip(st[0], st[1])}</span></div>`;
      }).join("") + `</section>`;
}
/* What the file lacks, said plainly, with the page that defines the layout. A journey with neither a job statement nor
   steps is usually written in another shape, which the page cannot read and the knowledge check rejects. */
function jpMissing(p){
  const noJob = !(p.job && p.job.text);
  const what = noJob ? "has no <code>**Job statement:**</code> paragraph and no numbered steps under <code>## Happy path</code>"
    : "has no numbered steps under <code>## Happy path</code>";
  return `This journey file ${what}. ${link("docs:knowledge-base/journeys", "", "How to write a journey")}`;
}
function journeyPage(p){
  const crumbs = `<nav class="crumbs">${link("knowledge", "lnk", "Knowledge")}<span class="sep">&rsaquo;</span>`
    + `${link("knowledge:journey", "lnk", "Journeys")}<span class="sep">&rsaquo;</span><span class="here">${esc(p.id)}</span></nav>`;
  const c = p.counts || {};
  const hero = `<section class="jp-hero"><div class="jp-badges"><span class="jp-tag">Journey</span><span class="jp-tag jp-id">${esc(p.id)}</span>`
    + (p.tier ? `<span class="jp-tag">${esc(p.tier)}</span>` : "") + `</div><h2 class="jp-title">${esc(p.title)}</h2>${jpJob(p.job)}`
    + `<div class="jp-who">` + (p.persona ? `<div class="jp-pers"><div class="jp-av">${esc(jpInitials(p.persona))}</div><div><small>Who</small><b>${esc(p.persona)}</b></div></div>` : "")
    + `<div class="jp-facts">${jpCount(c.steps || 0, "step")}${jpCount(c.branches || 0, "branch", "branches")}${jpCount(c.criteria || 0, "acceptance criterion", "acceptance criteria")}${jpCount(c.capabilities || 0, "capability", "capabilities")}</div></div></section>`;
  const steps = p.steps || [], loose = p.loose_branches || [];
  const path = `<div class="jp-card"><h3 class="jp-h">Happy path<span class="jp-c">${steps.length} step${steps.length === 1 ? "" : "s"}</span></h3>`
    + (steps.length ? `<ol class="jp-tl">${steps.map(jpStep).join("")}</ol>` : `<div class="jp-empty">${jpMissing(p)}</div>`)
    + (loose.length ? `<div class="jp-lab" style="margin-top:1.2rem">Other ways it can go</div>${loose.map(b =>
        `<div class="jp-b" style="margin-top:.4rem"><b>${mdown(b.title)}</b>${b.disposition ? `<span>${mdown(b.disposition)}</span>` : ""}</div>`).join("")}` : "")
    + `</div>`;
  const prd = p.owning_prd;
  const rail = `<aside class="jp-rail">`
    + (p.preconditions || p.trigger ? `<div class="jp-card jp-span2">${p.preconditions ? `<div class="jp-lab">Before you start</div><p>${mdown(p.preconditions)}</p>` : ""}`
        + (p.trigger ? `<div class="jp-lab" style="margin-top:.8rem">It starts when</div><p>${mdown(p.trigger)}</p>` : "") + `</div>` : "")
    + ((p.surfaces || []).length ? `<div class="jp-card"><h3 class="jp-h">Where it happens</h3><div class="jp-chips">${p.surfaces.map(s => `<span class="jp-chip jp-surf">${mdown(s)}</span>`).join("")}</div></div>` : "")
    + `<div class="jp-card"><h3 class="jp-h">Built by</h3>` + (prd
        ? `<div class="jp-row"><span class="jp-k">${link("prd:" + prd.n, "", esc(prd.n))}</span><div><b>${esc(prd.title || "PRD " + prd.n)}</b><small>Owning PRD</small></div>`
          + `<span class="jp-st">${prd.found ? jpChip(prd.built ? "built" : "notbuilt", prd.built ? "Built" : (prd.status || "Not built")) : jpChip("unresolved", "Unresolved")}</span></div>`
        : `<div class="jp-empty">This journey names no owning PRD.</div>`) + `</div>`
    + (EXTRA.quality ? `<div class="jp-card jp-span2"><h3 class="jp-h">Quality desk</h3><p>Every criterion below is a promise the Quality desk can check.</p>`
        + `<p style="margin-top:.7rem">${link("quality", "", "Open this journey in the Quality desk &rarr;")}</p></div>` : "")
    + `<div class="jp-quiet jp-span2"><span>Writing or editing a journey?</span>${link("docs:knowledge-base/journeys", "", "How to write a journey")}</div></aside>`;
  const warn = (p.warnings || []).length
    ? `<div class="banner"><b>Some annotations in this journey were not read:</b> ${esc(p.warnings.join(" · "))}</div>` : "";
  return `<div class="jp${tuOn() ? " tu-page tu-item" : ""}">${crumbs}${hero}${jpStrip(p)}<div class="jp-cols">${path}${rail}</div>${jpCriteria(p)}${jpCovers(p)}${warn}</div>`;
}

function viewKEntity(kind, id){
  const crumbs = [{ label: "Knowledge", go: "knowledge" },
                  { label: kTitle(kind), go: "knowledge:" + kind },
                  { label: id }];
  const got = kHold(kEntityPath(kind, id));
  if (got.state !== "ready"){
    return kCrumbs(kTitle(kind), "knowledge:" + kind) + pageHead(id) + kState(got, id);
  }
  /* A JOURNEY IS DRAWN WHOLE when its page read arrived; while it is on the way the header says so, and when it
     failed (a reading that holds no file text for it) the generic page below answers as it always did. */
  if (kind === "journey"){
    const jp = kHold(kEntityPath(kind, id) + "/page");
    if (jp.state === "ready" && jp.data && Array.isArray(jp.data.steps)) return journeyPage(jp.data);
    if (jp.state === "loading") return kCrumbs(kTitle(kind), "knowledge:" + kind) + pageHead(kEntity(got.data).name || id) + kState(jp, "the journey");
  }
  const e = kEntity(got.data);
  /* IN THE NEW UI A KNOWLEDGE ROW (A COMPONENT, A CAPABILITY...) IS THE ONE HEADER (`tuHeader`) inside the one page frame (`.tu-page .tu-item`,
     the width and padding every detail page has): its layer is the meta line's bold lead ("Surfaces layer"), the rest of its key/value grid
     the facts ("detail doc: yes", "owns X", "never ships") and its promise sentence stays below the card. */
  const nu = tuOn();
  let nuHead = "";
  if (nu){
    const kvs = (e.facts || []).filter(f => f && f[1] != null && String(f[1]) !== "");
    const word = String(kind).replace(/[-_]/g, " ");
    const same = c => String(c.text || "").toLowerCase() === word.toLowerCase();
    const layer = kvs.find(f => String(f[0]).toLowerCase() === "layer");
    const layerWord = layer ? String(layer[1]).trim() : "";
    const order = f => (String(f[0]).toLowerCase() === "detail doc" ? 0 : 1);
    nuHead = tuHeader({
      crumbs: `<div class="tu-crumbs2">${crumbs.map((c, i) => `${i ? " &rsaquo; " : ""}${c.go ? link(c.go, "tu-lnk", esc(c.label)) : `<span class="tu-mono">${esc(c.label)}</span>`}`).join("")}</div>`,
      badge: `<span class="tu-ty tu-component">${esc(word.charAt(0).toUpperCase() + word.slice(1))}</span>`, key: e.id || id,
      ids: (e.chips || []).filter(c => !same(c)).map(c => badge(c.text, c.cls)),
      title: esc(e.name || kTitle(kind)),
      state: layerWord ? esc(layerWord.charAt(0).toUpperCase() + layerWord.slice(1) + " layer") : "",
      facts: kvs.filter(f => String(f[0]).toLowerCase() !== "layer").sort((a, b) => order(a) - order(b)).map(f => {
        const k = String(f[0]).toLowerCase();
        /* "owns X" is said as a fact, and a component that never ships says "never ships". */
        if (k === "owns") return `owns ${mdown(f[1])}`;
        if (k === "ship-state" && /^never/i.test(String(f[1]))) return "never ships";
        return `${esc(k)}: ${mdown(f[1])}`;
      }).filter(Boolean) })
      + (e.summary ? `<p class="promise">${mdown(e.summary)}</p>` : `<p class="promise nodesc">This row carries no summary.</p>`);
  }
  const head = nu ? nuHead : entityHeader({
    crumbs,
    id: e.id || id,
    name: e.name || kTitle(kind),
    chips: (e.chips || []).map(c => badge(c.text, c.cls)),
    promise: e.summary || "",
    promiseNote: e.summary ? "" : "This row carries no summary.",
    /* A FACT'S VALUE GOES THROUGH `mdown`, never raw. `entityHeader` inserts it as markup — every
       other caller hands it chips it built itself — and a corpus's own string is the one thing on
       this page that did not come from this file. `mdown` escapes first and then reads the
       corpus's marks, which is also how the same value renders on every other surface. */
    facts: (e.facts || []).map(f => [f[0], mdown(f[1])]),
  });
  const body = head + kCta(e) + kStated(e) +
    kRelations(e).map(g => grp(g.label, g.items.length, g.note,
      entityList(g.items.map(x => kRow(x, x.kind)), { empty: "Nothing." }))).join("") +
    kProse(kind, id);
  return nu ? `<div class="tu-page tu-item">${body}</div>` : body;
}

/* THE NARRATIVE AS THE CORPUS HOLDS IT: A LIST OF TITLED BLOCKS, and the titles are load-bearing
   rather than decoration. What a requirement *states* and why it was *adopted* are two different
   sentences and a reader acts on the difference; flattened into one string they arrive as one
   paragraph with no seam, and a capability's `Ships in` reads as part of the promise. So the
   blocks are rendered as blocks — one heading each, one markdown body each, in the order the
   corpus states them.

   RENDERED AS `mdBlock`'S OWN HEADING, which is what makes this cost no CSS: `.md-h` is the
   class that file already emits for a heading inside a document, and the whole is wrapped in the
   `.md` every other markdown surface on this board wraps its body in.

   A BARE STRING IS STILL READ. A host with no server bakes the text itself, and that is not a
   lesser shape — it is what a standalone page has. Blocks when there are blocks, the string when
   there is a string, and the empty note when there is neither. */
function kBlocks(held){
  if (typeof held === "string") return held.trim() ? mdBlock(held) : "";
  const blocks = (held && held.blocks) || [];
  return blocks.filter(b => b && String(b.body || "").trim()).map(b =>
    `<h3 class="md-h" id="${esc(mdSlug(b.title || ""))}">${esc(b.title || "")}</h3>${mdBlock(b.body)}`).join("");
}
/* THE AUTHORED NARRATIVE, FETCHED WHEN THE PAGE IS ALREADY ON SCREEN and never carried by the
   list or the detail that led here — `loadBody`'s own discipline, for the same reason: it is the
   largest thing behind this route and it is not what the reader came for. The facts, the chips
   and every edge are painted already; the prose arrives into a placeholder that says so. */
function kProse(kind, id){
  if (!PROSE_LOADER) return "";
  const held = PROSE_CACHE[textKey(kEntityPath(kind, id))];
  const written = held === undefined || (held && held.err) ? "" : kBlocks(held);
  const body = held === undefined ? `<p class="empty-note">Reading the narrative&hellip;</p>`
    : held && held.err ? `<div class="banner"><b>${esc(String(held.err))}</b></div>`
    : written ? `<div class="md">${written}</div>`
    : `<p class="empty-note">The corpus holds no narrative for this row &mdash; the summary and
       the edges above are everything it wrote down.</p>`;
  /* THE FILE IS NAMED WHEN THE RESPONSE NAMES IT, because this is an INDEX rather than a reader:
     every inlined field is capped, so what is on screen is enough to recognise the row and the
     rest of it is in the repository. A reader who has to go there should not have to guess where. */
  const source = (held && !held.err && typeof held === "object" && held.source) ? String(held.source) : "";
  return grp("In the corpus", null,
    "Fetched when you open this page, never shipped with the list. Every id in it is the same "
    + "destination it is in a row above." + (source ? " Authored in " + source + "." : ""), body);
}

/* ONE ROUTE KIND, FOUR VIEWS — the tab, a kind's list, the cross-kind search, and one entity.
   `knowledge:<kind>:<id>` splits on the first colon twice, so an id carrying punctuation (a
   decision record is a date and a slug) survives the parse whole. */
function viewKnowledgeRoute(arg){
  const at = String(arg || "").indexOf(":");
  if (!arg) return viewKnowledge();
  if (arg === "search") return viewKSearch();
  /* `prds` IS A LITERAL BESIDE `search`, NOT A KIND (ENG-10915). Adding `prd` to the index
     would start accepting `knowledge:prd:0592` through the generic entity view — worse than
     `viewPrd`, and the undo of ENG-10704. */
  if (arg === "prds") return viewKPrds();
  /* `documents` IS A LITERAL BESIDE `search`, NOT A KIND (ENG-10916). */
  if (arg === "documents") return viewKDocs();
  if (arg.startsWith("documents:")) return viewKDoc(arg.slice("documents:".length));
  if (at < 0) return kKind(arg) ? viewKList(arg) : viewKnowledge();
  return viewKEntity(arg.slice(0, at), arg.slice(at + 1));
}

/* WHAT THE ROUTE NEEDS READ, decided from the route and never from the markup that was just
   written — `render`'s own rule for the two text loaders one register over. */
function wantKnowledge(arg, route){
  const at = String(arg || "").indexOf(":");
  if (!arg) return;
  if (arg === "search"){ if (K_QUERY) kWant(kSearchPath(), route); return; }
  if (arg === "prds"){ kWant(kPrdsPath(), route); return; }
  if (arg === "documents"){ kWant(kDocsPath(), route); return; }
  if (arg.startsWith("documents:")){
    const path = arg.slice("documents:".length);
    const ep = kDocsEntityPath(path);
    kWant(ep, route);
    if (PROSE_LOADER && PROSE_CACHE[textKey(ep)] === undefined){
      fetchText(PROSE_LOADER, PROSE_CACHE, ep,
                "The document could not be read: ", route,
                v => (v && typeof v === "object" ? v : String(v || "")));
    }
    return;
  }
  if (at < 0){ if (kKind(arg)) kWant(kListPath(arg), route); return; }
  const kind = arg.slice(0, at), id = arg.slice(at + 1);
  kWant(kEntityPath(kind, id), route);
  if (kind === "journey") kWant(kEntityPath(kind, id) + "/page", route);
  if (PROSE_LOADER && PROSE_CACHE[textKey(kEntityPath(kind, id))] === undefined){
    /* THE COERCER IS WHY A DOCUMENT SURVIVES THIS CACHE. `fetchText`'s default is
       `String(text || "")` — right for the two loaders it was written for, which answer a file's
       bytes, and silently fatal for one that answers a document: `{blocks: […]}` becomes the
       eleven characters `[object Object]`, which is truthy, non-empty, and renders as itself.
       An object is kept as it arrived; a string still arrives as a string. */
    fetchText(PROSE_LOADER, PROSE_CACHE, kEntityPath(kind, id),
              "The narrative could not be read: ", route,
              v => (v && typeof v === "object" ? v : String(v || "")));
  }
}

/* ── router, with real history ───────────────────────────────────────────── */

const main = document.getElementById("main");
/* Did the last render land on an anchor of its own? A route that named a definition has
   already put it on screen, and scrolling to the top afterwards would take it away again. */
let anchored = false;
/* THE FIRST COLON SEPARATES, AND ONLY THE FIRST. `r.split(":")` was equivalent for every route
   this file had, because every argument was an id with no punctuation in it — and it silently
   truncates `doc:knowledge/specs/a:b.md` at the second colon, which is a route naming a file
   that is not the file. A path arrives from a corpus rather than from this file, so the parse
   has to survive whatever a repository chose to call something. */
function routeParts(r){
  const s = String(r || "");
  const at = s.indexOf(":");
  return at < 0 ? [s, undefined] : [s.slice(0, at), s.slice(at + 1)];
}

/* ONE FETCH, ONE CACHE, ONE REPAINT — for an agent's prompt and for a document it cites alike.
   MARKED BEFORE THE ANSWER: the cache entry is written on BOTH branches, so a refusal is a
   remembered answer rather than a question this page asks again on every paint. */
/* WHAT IS ALREADY BEING ASKED FOR. A separate set rather than a sentinel IN the cache, because
   the cache holds two kinds of answer already (the text, and a refusal) and a third meaning
   "still coming" would have to be told apart from both at every read. `render` runs more often
   than a reader navigates — a glossary fetch landing re-renders the route in place — so without
   this an agent page open while its prompt is in flight would ask for it again on every repaint. */
const TEXT_INFLIGHT = new Set();

/* `coerce` IS HOW THE CORPUS READS RIDE THIS SAME SEAM RATHER THAN A SECOND COPY OF IT. Every
   line here — the in-flight set, the cache entry written on BOTH branches, the repaint only if
   the reader is still on the route that asked — is the same discipline whether the answer is an
   agent's markdown or a knowledge entity's edges, and the ONE thing that differs is what a
   successful answer is stored as. Absent, it is text, which is every call site that predates
   this argument. */
function fetchText(loader, cache, path, blame, route, coerce){
  const key = textKey(path);
  if (TEXT_INFLIGHT.has(key)) return;
  TEXT_INFLIGHT.add(key);
  const done = () => {
    TEXT_INFLIGHT.delete(key);
    if ((location.hash.slice(1) || "board") === route) render(route);
  };
  loader(path).then(
    text => { cache[key] = coerce ? coerce(text) : String(text || ""); done(); },
    err => {
      cache[key] = { err: blame + ((err && err.message) || String(err)) };
      done();
    });
}

/* WHAT THE CORPUS CALLS ITS ACTION PAGE (BUG-7). The corpus names the board route through its
   payload's `intentTitle` — production calls it "What to do next" — and the shell's nav item and
   the breadcrumb already show that name. The browser tab did not: `viewBoard` and `titleFor`
   both spelled the shell's resting word "Programs", which is also a different page's name, so
   two Fleet tabs read alike and the tab named neither the page under it nor the corpus. Read the
   corpus's own name here, with the resting word only as the fallback for a payload that carries
   none (a standalone board, an older payload) — the same fallback `app.js`'s `paintIntentTab`
   uses for the nav item, so the tab and the nav cannot disagree. */
function boardName(){
  return (D && typeof D.intentTitle === "string" && D.intentTitle.trim()) ? D.intentTitle : "Programs";
}

/* WHAT THE TAB IS CALLED, FOR EVERY ROUTE (ENG-10589). `pageHead` titles the tab for the views
   that call it; the three entity views build their header through `entityHeader` and never did,
   so a PRD tab read "Stats" and a slice tab "Fleet" — whatever the previous page had said. The
   router now titles every route before the view paints, and a view that calls `pageHead` still
   has the last word. An entity's title is its id and name, which is what a reader sees in the
   tab strip; a host view's is its route word, capitalised, until its own `pageHead` runs. */
function titleFor(r){
  const [kind, arg] = routeParts(r);
  if (D !== null){
    if (kind === "program" && PG[arg]) return `${PG[arg].id} ${PG[arg].name}`;
    if (kind === "slice" && SL[arg]) return `${SL[arg].id} ${SL[arg].name}`;
    if (kind === "prd" && PRD[arg]) return `${PRD[arg].n} ${PRD[arg].title}`;
  }
  const word = kind === "settings" ? "Settings" : kind === "board" ? boardName() : kind === "deps" ? "Dependencies" : kind === "commands" ? "Agents"
             : kind.charAt(0).toUpperCase() + kind.slice(1);
  return arg && !["board", "deps", "commands", "settings"].includes(kind) ? `${arg} · ${word}` : word;
}

/* AN ID THIS CORPUS DOES NOT HOLD IS A PAGE, NEVER A REDIRECT (ENG-10589).
 *
 * `#program:PG-99`, `#slice:SL-999`, `#prd:9999`, `#command:nope`, `#knowledge:journey:x` and a
 * route kind this file has never heard of all used to land on the Programs list with the address
 * rewritten to `#board` and nothing said — so a mistyped link, a stale bookmark and a pasted id
 * that had since been renamed all "worked", and a reader learnt not to trust the address bar.
 * The two host views that already answered honestly (`#idea:INTAKE-999`, `#box:nope`) were the
 * model: the page says what is missing, keeps the address the reader arrived at, and offers the
 * way back. The deep-link rules are untouched: a route nobody can judge yet is HELD (rendered as
 * loading, the hash untouched), and only once the register that would hold the id is in hand
 * and does not hold it is the reader told so — never a rewrite in either state.
 *
 * ONE NOUN PER REGISTER, so the sentence names the kind of thing rather than the route word. A
 * kind this file does not route at all is said to be no page, which is the truthful reading of
 * `#nonsense` and of a route retired in an earlier version. */
const MISSING_NOUN = { program: "program", slice: "slice", prd: "PRD", command: "agent", slot: "slot",
                       doc: "document", repo: "repository" };

/* WHICH OTHER REPOSITORIES HOLD A PROGRAM, SLICE OR PRD THIS ONE DOES NOT. One ETagged board read per synced
   repository (`REPO_BOARD_LOADER`, a 304 on a revisit), once per repository and ref, remembered here until the
   repository on screen changes (`repoReset`). */
const ELSEWHERE = {};
/* THE ROUTE A CROSS-REPOSITORY HOP LANDED ON. It outlives `repoReset` (which clears ELSEWHERE) so a page reached by a hop
   never hops again, whatever the boards say: at most one hop per navigation. A reader's own navigation (`go`, Back) clears it. */
let HOPPED = "";
function holdsRef(payload, kind, id){
  if (!payload) return false;
  if (kind === "program") return (payload.programs || []).some(p => p.id === id);
  if (kind === "slice") return !!(payload.slices && payload.slices[id]);
  return Object.values(payload.slices || {}).some(s => (s.prds || []).some(x => String(x.n) === String(id)))
    || (payload.offBoardPrds || []).some(o => String(o.n) === String(id));
}
function lookElsewhere(kind, id){
  if (!REPO_BOARD_LOADER || !manyRepos()) return null;
  const ck = REPO + "|" + kind + ":" + id;
  if (ELSEWHERE[ck]) return ELSEWHERE[ck];
  const e = ELSEWHERE[ck] = { state: "loading", in: [], went: false };
  const others = corpusRows().filter(c => c.synced && keyOf(c) !== null && keyOf(c) !== REPO);
  let left = others.length;
  if (!left){ e.state = "ready"; return e; }
  others.forEach(c => {
    const key = keyOf(c);
    Promise.resolve().then(() => REPO_BOARD_LOADER(key)).then(
      payload => { if (holdsRef(payload, kind, id)) e.in.push({ key, name: repoName(c) || key }); },
      () => { /* a repository that cannot be read is one that does not say it holds the ref */ })
      .then(() => {
        if (--left > 0) return;
        e.state = "ready";
        if (openRoute() === kind + ":" + id) render(openRoute());
      });
  });
  return e;
}
function repoHref(key, r){
  let q;
  try { q = new URLSearchParams(location.search); } catch { return "#" + r; }
  q.set("repo", key);
  return location.pathname + "?" + q.toString() + "#" + r;
}
/* ONE HOLDER: GO THERE (the entry is replaced, so Back does not return to the miss; `ui=` rides `urlFor`). SEVERAL:
   LIST THEM. NONE: SAY NOTHING MORE (the not-found sentence stands). */
function elsewhereNote(kind, id, r, noun){
  if (EMBEDDING) return "";
  const e = lookElsewhere(kind, id);
  if (!e || e.state !== "ready" || !e.in.length) return "";
  if (e.failed){
    return `<div class="banner attn"><b>${esc(id)} is in ${esc(e.in[0].name)}, but it could not be opened there</b> &mdash; ${
      esc(e.failed)}. <a class="lnk" href="${esc(repoHref(e.in[0].key, r))}">Open it there</a></div>`;
  }
  if (e.in.length === 1 && SWITCH_REPO && HOPPED !== r){
    const to = e.in[0].key;
    if (!e.went){
      e.went = true;
      Promise.resolve().then(() => {
        if (openRoute() !== r) return;
        HOPPED = r;
        switchTo(to, { replace: true }).then(ok => {
          if (ok) return;
          HOPPED = "";
          e.failed = SWITCH_ERR || "the repository did not answer";
          if (openRoute() === r) render(r);
        });
      });
    }
    return `<div class="banner"><b>${esc(id)} is in ${esc(e.in[0].name)}</b> &mdash; opening it there&hellip;</div>`;
  }
  return `<div class="banner"><b>${esc(id)} is in:</b> ${e.in.map(h =>
    `<a class="lnk" href="${esc(repoHref(h.key, r))}">${esc(h.name)}</a>`).join(" &middot; ")}</div>`;
}

function viewMissing(r){
  const [kind, arg] = routeParts(r);
  /* THE HOST MAY OFFER ITS OWN HOME BESIDE THE BOARD (`missingBack`): the New UI's is the Cockpit. */
  const home = MISSING_BACK ? MISSING_BACK() : null;
  const back = `<p class="note"><button class="lnk" data-go="board">Back to the board</button>${
    home && home.route ? ` <button class="lnk" data-go="${esc(home.route)}">${esc(home.label || home.route)}</button>` : ""}</p>`;
  let noun = MISSING_NOUN[kind] || "";
  let id = arg;
  if (kind === "knowledge" && arg){
    const at = arg.indexOf(":");
    noun = at < 0 ? "kind of knowledge" : kTitle(arg.slice(0, at)).toLowerCase().replace(/s$/, "");
    id = at < 0 ? arg : arg.slice(at + 1);
    if (at >= 0 && !kKind(arg.slice(0, at))) noun = arg.slice(0, at);
    /* NOT "there is no such row" WHEN NOTHING COULD HAVE LOOKED: a board with no server to read
       the corpus from, or an index that failed, has not judged the id absent — it cannot open it,
       which is a different sentence and names a different remedy. */
    const state = kIndexState();
    if (state !== "ready" || !kServed()){
      const why = state === "failed" ? "the corpus index could not be read"
        : state === "ready" ? "this repository carries no knowledge index"
        : "this board has no server to read the knowledge corpus from";
      return pageHead(`Cannot open ${id}`) +
        `<div class="banner"><b>${esc(id)} cannot be opened here</b> &mdash; ${why}. The deployed
          board answers it; a standalone page is the plan, read out of git.</div>` + back;
    }
  }
  if (!noun || !id){
    return pageHead("No such page") +
      `<div class="banner"><b>There is no page called <code>${esc(kind)}</code> on this board.</b>
        The address may be from an earlier version, or mistyped.</div>` + back;
  }
  if (MISSING_NOTE && ["program", "slice", "prd"].includes(kind)){
    const said = MISSING_NOTE({ kind: kind, id: id });
    if (said && typeof said.html === "string" && said.html) return pageHead(said.title || id) + said.html + back;
  }
  const plan = ["program", "slice", "prd"].includes(kind) && noPlan() ? noPlanNote() : "";
  /* THE REF MAY LIVE IN ANOTHER REPOSITORY the reader can see (a link from a page that spans them all). */
  const elsewhere = ["program", "slice", "prd"].includes(kind) ? elsewhereNote(kind, id, r, noun) : "";
  return pageHead(`No such ${noun}: ${id}`) +
    `<div class="banner"><b>There is no ${esc(noun)} ${esc(id)} in this repository</b> &mdash; it may
      have been renamed or removed since the last sync.</div>` + elsewhere + plan + back;
}

/* IS THIS ROUTE A PAGE THIS CORPUS CANNOT DRAW: judged, and judged absent. Loading is not
   absent, and neither is a host view — those answer for themselves. */
function missing(r){
  if (!r) return false;
  return D !== null && !unjudged(r) && !valid(r);
}

/* ── the repaint that keeps the reader's place ───────────────────────────── */
/*
 * A REFRESH IS A PATCH OF THE LIVE TREE, NEVER A REPLACEMENT OF IT.
 *
 * THE DEFECT, measured in Chromium against a local stack. Every view here is a string, and
 * every repaint used to be `main.innerHTML = view()`: the whole subtree thrown away and parsed
 * again, ten seconds apart, on every page. A reader typing into the Queue's search box — a
 * field that commits on Enter and so holds its draft in the DOM and nowhere else — watched one
 * feed arrival replace `#main`'s children FOUR times, and after it the `<input>` was a different
 * element (`sameElement: false`), its value was the empty string the render carries, and the
 * caret sat at 0. `data-keep` had handed focus to the new element, which is exactly as far as
 * a focus restore can go: it cannot give back a caret, a selection, a half-typed word, an
 * `<option>` the reader picked, a scrolled list, or a `<details>` the reader opened, because the
 * elements holding all of those no longer exist. And a subtree removed and re-added is a document
 * whose height collapses for one layout and then grows back, which is the page scrolling under
 * the reader every ten seconds.
 *
 * SO THE NEW MARKUP IS PARSED INTO A TEMPLATE AND THE LIVE TREE IS WALKED AGAINST IT, and only
 * what differs is touched: an attribute that changed is set, a text node whose words moved is
 * rewritten, a node that is gone is removed, a node that is new is inserted, and everything else
 * — the element under the caret first of all — stays the element it was. A control's LIVE value
 * follows the render only when the render changed its mind about the default since the last
 * paint (a draft cleared after "Send"); a default the render repeats is a value the reader owns.
 * A `<details>` the reader toggled keeps their answer over the render's. And a host whose
 * children a script builds and moves (`data-mount`: the terminal and the agent pane) has its
 * attributes patched and its subtree left alone, where a replacement would have detached the
 * pane and reset its scroll every ten seconds — which is the failure `pane.move` was written to
 * undo.
 *
 * NOT A LIBRARY, AND WHY. idiomorph and morphdom do this and do it well; what rules them out is
 * where this file lives. `board.js` is inlined into one self-contained `file://` page by a
 * stdlib-only package and served byte for byte by the deployed app, so a dependency is a second
 * file both pages must carry, and the render harness (`tests/js/dom.js`) is deliberately not a
 * browser — nothing here could execute a library that walks a real DOM. Three hundred lines
 * that ask a dozen DOM methods are testable against a tree small enough to read.
 *
 * MATCHING, so a node is patched against the node it IS and not the one that happens to stand
 * where it stood. A new child is paired with an old sibling in this order: the sibling carrying
 * the same key (`id`, else `data-keep` — both are what the pages already call an element by);
 * else the first sibling whose subtree shares a key with the new child's (a row without an id of
 * its own still holds the links that name it); else, for a child with no keys at all, the first
 * sibling of the same tag that is not keyed and that the NEXT new child would not rather have.
 * A matched sibling standing further along is moved up to the cursor rather than the ones
 * before it removed, so an old node passed over is still there to be matched by a later new
 * child; what nothing claimed is removed at the end. That is the shape of idiomorph's id-set
 * walk, without its head merging and without a global lookup: a node never moves across parents.
 *
 * WHERE IT CANNOT RUN, IT DOES WHAT THE PAGE ALWAYS DID. A `template` with no `content` is a
 * document that cannot parse markup into nodes — the render harness — and there `patch` assigns
 * `innerHTML` exactly as before and returns false, so every string assertion over `#main` reads
 * what it always read. The morph itself has its own fixture, `tests/js/morph.js`, run over a
 * tree DOM built for it.
 */

/* `id` first, else `data-keep`: the two names the pages already give an element. Namespaced so
   an id and a keep that happen to share a spelling stay two keys. */
function morphKey(n){
  if (!n || n.nodeType !== 1 || !n.getAttribute) return "";
  const id = n.getAttribute("id");
  if (id) return "#" + id;
  const keep = n.getAttribute("data-keep");
  return keep ? "@" + keep : "";
}
function morphAlike(a, b){
  return !!a && !!b && a.nodeType === b.nodeType && a.nodeName === b.nodeName;
}
/* EVERY KEY UNDER EVERY NODE, once per side per patch: for each keyed element, its key is added
   to its own set and to each ancestor's up to the root. A parent's set is what says "the row you
   are looking for is inside this one", which is how a `<tr>` with no id of its own is still
   paired with the `<tr>` holding the same links. */
function morphKeys(root){
  const sets = new Map();
  const all = new Set();
  const keyed = root.querySelectorAll ? root.querySelectorAll("[id],[data-keep]") : [];
  for (let i = 0; i < keyed.length; i++){
    const key = morphKey(keyed[i]);
    if (!key) continue;
    all.add(key);
    for (let n = keyed[i]; n && n !== root; n = n.parentNode){
      let set = sets.get(n);
      if (!set){ set = new Set(); sets.set(n, set); }
      set.add(key);
    }
  }
  return { sets, all };
}
function morphShare(a, b){
  if (!a || !b) return false;
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  for (const k of small) if (large.has(k)) return true;
  return false;
}

/* THE ONE OLD SIBLING THE NEW CHILD IS, or null when it is new. See the file comment's
   "MATCHING" for the three tiers and their order. */
function morphMatch(cur, want, next, ctx){
  const key = morphKey(want);
  if (key){
    for (let n = cur; n; n = n.nextSibling){
      if (morphKey(n) === key && morphAlike(n, want)) return n;
    }
  }
  const wantKeys = ctx.to.sets.get(want);
  if (wantKeys){
    for (let n = cur; n; n = n.nextSibling){
      if (n.nodeType === 1 && morphAlike(n, want) && morphShare(ctx.from.sets.get(n), wantKeys)) return n;
    }
    /* A child with keys that no old sibling shares is new: pairing it with a keyless twin of the
       same tag would pour one row's state into another. */
    return null;
  }
  /* Keyless: the nearest same-tag sibling that is itself keyless, unless the next new child is
     the one it is for. */
  for (let n = cur; n; n = n.nextSibling){
    if (n.nodeType === 1 && ctx.from.sets.get(n)) continue;
    if (morphAlike(n, want)) return n;
    if (next && !ctx.to.sets.get(next) && morphAlike(n, next)) return null;
  }
  return null;
}

/* IS ANYTHING UNDER THIS OLD NODE STILL WANTED — a key of its own or of a descendant that the new
   render carries somewhere. A node nothing wants is removed where it stands; a node something
   wants is left for its turn. */
function morphClaimed(n, ctx){
  return n.nodeType === 1 && morphShare(ctx.from.sets.get(n), ctx.to.all);
}

function morphChildren(from, to, ctx){
  let cur = from.firstChild;
  let want = to.firstChild;
  while (want){
    /* Adopting `want` detaches it from the template, so its sibling is read first. */
    const next = want.nextSibling;
    const match = morphMatch(cur, want, next, ctx);
    if (match){
      /* THE MATCH STANDS FURTHER ALONG. Moving it up detaches it, and a detached element holding
         the caret is blurred by the browser — so when nothing between the cursor and the match is
         still wanted, the unwanted nodes go instead and the match never moves. Only when something
         in between is still wanted does the match come up to the cursor, and `morphGiveBack`
         hands the caret back if that took it. */
      while (cur !== match && !morphClaimed(cur, ctx)){
        const gone = cur;
        cur = cur.nextSibling;
        from.removeChild(gone);
      }
      if (match === cur) cur = cur.nextSibling;
      else from.insertBefore(match, cur);
      morphNode(match, want, ctx);
    } else {
      from.insertBefore(want, cur);
    }
    want = next;
  }
  while (cur){
    const gone = cur;
    cur = cur.nextSibling;
    from.removeChild(gone);
  }
}

/* A `<details>` THE READER TOGGLED KEEPS THEIR ANSWER. `toggle` does not bubble, so it is caught
   on the way down; the ones this file's own patching fires arrive one task later and are told
   apart by having been announced (`MORPH_TOGGLING`). A view that drives `open` from its own
   state prevents the native toggle on the summary — the Queue's groups already do — and so never
   lands here. */
const MORPH_TOUCHED = typeof WeakSet === "function" ? new WeakSet() : null;
const MORPH_TOGGLING = typeof WeakSet === "function" ? new WeakSet() : null;
if (MORPH_TOUCHED && document.addEventListener){
  document.addEventListener("toggle", e => {
    const el = e.target;
    if (!el || !el.nodeName || el.nodeName !== "DETAILS") return;
    if (MORPH_TOGGLING.has(el)){ MORPH_TOGGLING.delete(el); return; }
    MORPH_TOUCHED.add(el);
  }, true);
}
/* WHICH KNOWLEDGE ROWS ARE OPEN, written down as the reader opens them, so leaving the page and
   coming back draws them the way they were left (`K_OPEN`). */
if (document.addEventListener){
  document.addEventListener("toggle", e => {
    const d = e.target;
    const id = d && d.getAttribute ? d.getAttribute("data-krow") : null;
    if (!id) return;
    const open = typeof d.open === "boolean" ? d.open : d.getAttribute("open") !== null;
    if (open) K_OPEN.add(id); else K_OPEN.delete(id);
  }, true);
}

function morphAttrs(from, to){
  const readerOwnsOpen = from.nodeName === "DETAILS" && MORPH_TOUCHED && MORPH_TOUCHED.has(from);
  const want = to.attributes;
  for (let i = 0; i < want.length; i++){
    const name = want[i].name;
    if (readerOwnsOpen && name === "open") continue;
    const value = want[i].value;
    if (from.getAttribute(name) !== value){
      if (name === "open" && from.nodeName === "DETAILS" && MORPH_TOGGLING) MORPH_TOGGLING.add(from);
      from.setAttribute(name, value);
    }
  }
  const have = from.attributes;
  for (let i = have.length - 1; i >= 0; i--){
    const name = have[i].name;
    if (readerOwnsOpen && name === "open") continue;
    if (!to.hasAttribute(name)){
      if (name === "open" && from.nodeName === "DETAILS" && MORPH_TOGGLING) MORPH_TOGGLING.add(from);
      from.removeAttribute(name);
    }
  }
}

/* WHAT A CONTROL'S RENDER SAID LAST TIME, read before the attributes move: the default is the
   render's word, the live value is the reader's, and which one wins is decided by whether the
   render's word CHANGED. */
function morphDefault(el){
  switch (el.nodeName){
    case "INPUT":
      return el.type === "checkbox" || el.type === "radio" ? { checked: el.defaultChecked } : { value: el.defaultValue };
    case "TEXTAREA": return { value: el.defaultValue };
    case "OPTION": return { selected: el.defaultSelected };
    default: return null;
  }
}
/* `now` IS READ BEFORE THE CHILDREN ARE WALKED, not off `to` afterwards: a `<textarea>`'s default
   is its text, and the walk ADOPTS the template's text node into the live tree, leaving `to`
   empty — measured in the fixture as a cleared draft that never cleared. */
function morphControl(from, was, now){
  if (!was || !now) return;
  if ("checked" in was){
    if (was.checked !== now.checked && from.checked !== now.checked) from.checked = now.checked;
  } else if ("selected" in was){
    if (was.selected !== now.selected && from.selected !== now.selected) from.selected = now.selected;
  } else if (from.type !== "file"){
    if (was.value !== now.value && from.value !== now.value) from.value = now.value;
  }
}

function morphNode(from, to, ctx){
  if (from.nodeType !== 1){
    if (from.nodeValue !== to.nodeValue) from.nodeValue = to.nodeValue;
    return;
  }
  /* Attributes and children alike, and cheaper than walking; a control's live value is not part
     of the comparison, which is exactly why an untouched render leaves the reader's draft be. */
  if (from.isEqualNode && from.isEqualNode(to)) return;
  const was = morphDefault(from);
  const now = morphDefault(to);
  morphAttrs(from, to);
  if (from.hasAttribute("data-mount")) return;
  morphChildren(from, to, ctx);
  morphControl(from, was, now);
}

/* WHAT A REPLACEMENT WOULD LOSE, noted before and handed back after — for the one case the walk
   could not keep an element: a focused control the render moved to another parent, or a scrolled
   list rebuilt. Found again by its key; a control with no key that the walk lost is gone, as it
   always was. */
function morphSelector(key){
  const value = key.slice(1).replace(/["\\]/g, "\\$&");
  return `[${key[0] === "#" ? "id" : "data-keep"}="${value}"]`;
}
function morphNote(root){
  const on = document.activeElement;
  let focus = null;
  if (on && on !== document.body && root.contains(on)){
    focus = { el: on, key: morphKey(on), start: null, end: null, dir: null, top: on.scrollTop || 0 };
    try { focus.start = on.selectionStart; focus.end = on.selectionEnd; focus.dir = on.selectionDirection; }
    catch (_e) { /* a control with no text selection — nothing to give back */ }
  }
  const scrolled = [];
  const keyed = root.querySelectorAll ? root.querySelectorAll("[id],[data-keep]") : [];
  for (let i = 0; i < keyed.length; i++){
    const el = keyed[i];
    if (el.scrollTop || el.scrollLeft) scrolled.push({ el, key: morphKey(el), top: el.scrollTop, left: el.scrollLeft });
  }
  return { focus, scrolled };
}
function morphGiveBack(root, noted){
  noted.scrolled.forEach(s => {
    if (s.el.isConnected !== false && root.contains(s.el)) return;
    const again = s.key ? root.querySelector(morphSelector(s.key)) : null;
    if (again){ again.scrollTop = s.top; again.scrollLeft = s.left; }
  });
  const f = noted.focus;
  if (!f || document.activeElement === f.el) return;
  /* Still in the tree but no longer focused: it was moved (a move is a detach, and a detach
     blurs) or the render disabled it — the second is left as the render made it. Gone: found
     again by its key, or not at all. */
  const still = f.el.isConnected !== false && root.contains(f.el);
  const again = still ? f.el : f.key ? root.querySelector(morphSelector(f.key)) : null;
  if (!again || again.disabled || !again.focus) return;
  again.focus({ preventScroll: true });
  if (f.start != null && again.setSelectionRange){
    try { again.setSelectionRange(f.start, f.end, f.dir || "none"); } catch (_e) { /* not a text control */ }
  }
  if (f.top) again.scrollTop = f.top;
}

/* PATCH `root` TO SHOW `html`. True when the live tree was walked; false when this document
   cannot parse markup into nodes and the markup was assigned instead — the same page either way,
   and only the second one loses the reader's place. */
function patch(root, html){
  if (!root) return false;
  const tpl = document.createElement("template");
  if (!tpl || !("content" in tpl) || !tpl.content){ root.innerHTML = html; return false; }
  tpl.innerHTML = html;
  const noted = morphNote(root);
  const ctx = { from: morphKeys(root), to: morphKeys(tpl.content) };
  morphChildren(root, tpl.content, ctx);
  morphGiveBack(root, noted);
  return true;
}

/* THE ROUTE THAT IS ON SCREEN. A render of the same route is a refresh and is patched; a render
   of another route is a navigation, and a navigation paints fresh — nothing of the page the
   reader left is theirs to keep, not a scrolled list and not an opened fold, and `go` is about
   to scroll to the top regardless. */
let PAINTED = null;
function paintMain(r, html){
  const again = PAINTED === r;
  PAINTED = r;
  if (again) patch(main, html); else main.innerHTML = html;
}

/* A REPAINT NEVER MOVES THE READER'S CARET (ENG-10701, RK-01). Every view here is a string written
   into `#main`, so the element that held focus is destroyed by any render — and a render the person
   did not ask for (the corpus re-read after a save's own event, the heartbeat) dropped a keyboard
   reader to the top of the document 0.3 s after "Order saved.". The caret is handed back to the
   element carrying the same `data-keep`, the contract `app.js`'s `repaint` and `rzRerender` already
   keep for their own repaints, here for every render. Nothing is scrolled: the reader is where they
   were. */
function focusedKeep(){
  const on = document.activeElement;
  if (!on || !on.getAttribute || !main || !main.contains(on)) return null;
  return on.getAttribute("data-keep");
}
function refocus(keep){
  if (!keep || !main) return;
  const again = main.querySelector(`[data-keep="${keep}"]`);
  if (again && again.focus && !again.disabled) again.focus({ preventScroll: true });
}
/* A HOST'S OWN ROUTE ALIASES (`alias`), applied where every route enters: `render` and `openRoute`. A
   route the host has moved (`#apikeys` → `#settings:api-keys`, `#settings/secrets` → the colon
   form) is re-addressed IN PLACE — the entry on screen is replaced, never pushed — so an old link,
   a bookmark and the back button all land on the one canonical address. */
let ALIAS = null;
function alias(fn){ ALIAS = typeof fn === "function" ? fn : null; }

/* A ROUTE NAME THIS BOARD HAS NEVER HAD, FOR A HOST THAT WANTS IT SENT HOME. `unknown(fn)` is asked
   for every route whose KIND (the word before the first colon) is neither a view the host registered
   nor one this file draws itself, and answers the route to land on instead, or nothing to keep the
   missing page (`viewMissing`). It is about the NAME ONLY: `#issue:ENG-99999` is a known kind with
   an id nothing holds and keeps its own "not found" page; `#next`, a route retired long ago that
   bookmarks still carry, is the case this exists for. The standalone board registers nothing, so
   it still says "no page called" there.

   EVERY VIEW MUST BE REGISTERED BEFORE THE FIRST RENDER (`register` / `start`). A view registered
   lazily, after a render that asked for it, would have been judged unknown at that render and sent
   home. The hook is consulted ONCE per navigation: the route it names is painted as it stands, never
   put to the hook again, so a hook that answers with another unknown name gives one missing page
   and no loop. */
let MISSING_BACK = null;
function missingBack(fn){ MISSING_BACK = typeof fn === "function" ? fn : null; }
let UNKNOWN = null;
let REDIRECTED = false;
function unknown(fn){ UNKNOWN = typeof fn === "function" ? fn : null; }
const CORE_KINDS = ["program", "slice", "prd", "board", "deps", "commands", "repo", "command", "slot", "doc", "knowledge"];
function knownKind(kind){ return CORE_KINDS.includes(kind) || Object.prototype.hasOwnProperty.call(EXTRA, kind); }
/* IS THIS ROUTE'S NAME ONE THIS BOARD HAS, after the aliases: the question `render` asks before it
   consults `unknown`, exported so a test can walk every route the app answers to without painting any. */
function known(r){ const [kind] = routeParts(canon(r)); return !kind || knownKind(kind); }
/* THE GLOSSARY PAGE IS GONE, AND ITS ADDRESSES STILL LAND. Its corpus half is the
   Knowledge page now and its host half is hover text where each word is used, so a bookmarked
   `#glossary` or `#glossary:<term>` re-addresses to the Knowledge page rather than to a page that
   says there is no such page. Here, ahead of the host's alias, because the standalone board had
   the tab too. */
function canon(r){
  if (r === "glossary" || String(r || "").startsWith("glossary:")) return "knowledge";
  if (!ALIAS || !r) return r;
  const n = ALIAS(String(r));
  return typeof n === "string" && n && n !== r ? n : r;
}

function render(r){
  const moved = canon(r);
  if (moved !== r){
    if (location.hash.slice(1) === r) history.replaceState({ r: moved }, "", urlFor(moved));
    return render(moved);
  }
  const [kind, arg] = routeParts(r);
  /* AN UNKNOWN ROUTE NAME IS RE-ADDRESSED, NOT PAINTED, when the host says where it goes. The entry
     is REPLACED (as `canon` does) so the bad hash is not left in history for Back to land on. */
  if (UNKNOWN && !REDIRECTED && kind && !knownKind(kind)){
    const home = UNKNOWN(r);
    if (typeof home === "string" && home && home !== r){
      if (location.hash.slice(1) === r) history.replaceState({ r: home }, "", urlFor(home));
      REDIRECTED = true;
      try { return render(home); } finally { REDIRECTED = false; }
    }
  }
  document.title = titleFor(r);
  const caretKeep = focusedKeep();
  /* THE MISSING PAGE PAINTS AND STOPS: no body fetch, no document fetch, no corpus read for an
     id the index has already said it does not hold (`#knowledge:journey:x` used to fire two 404s
     on its way to the redirect). The tab strip, the badges and the host's route hooks still run,
     because the reader is still standing under that tab. */
  if (missing(r)){
    paintMain(r, viewMissing(r));
    const top = tabFor(kind, arg);
    document.querySelectorAll(".tab").forEach(t =>
      t.setAttribute("aria-current", String(t.dataset.go === top)));
    paintBadges();
    paintNav(false);
    anchored = false;
    refocus(caretKeep);
    ROUTED.forEach(fn => fn(r, arg));
    rzSettled(kind);
    return;
  }
  /* A host view first — it has its own data and does not wait on the corpus, which is what
     lets the Fleet tab answer on a database no sync has ever written to.
     Then the placeholder, when the corpus payload is not here yet or never arrived. */
  paintMain(r, viewFor(kind, arg));
  refocus(caretKeep);
  /* WHICH TAB LIGHTS. This is one fact with a second writer — `app.js`'s `WORLD_OF` says which
     WORLD a route belongs to and this says which TAB — so every kind added here has to be added
     there too, and `test_js_render_agents.py` asserts that neither map is missing a route the
     router accepts rather than leaving it to be remembered. */
  const top = tabFor(kind, arg);
  document.querySelectorAll(".tab").forEach(t =>
    t.setAttribute("aria-current", String(t.dataset.go === top)));
  // EVERY NAVIGATION REPAINTS THE BADGES TOO, for the reason it repaints `aria-current`: the
  // reader's own eyes just moved, and a stale count sitting on the tab they left is as wrong as
  // a stale "here" mark would be. `paintBadges` is ALSO exported so a host can call it again
  // between navigations, when its own data changes and the route does not.
  paintBadges();
  paintNav(false);
  /* A LINK INTO ONE KIND LANDS ON THAT KIND'S ROW (`kindLink`), already open.
     `go` scrolls to the top after this returns, which would undo the anchor — so rather than
     deferring past it, this SAYS it took an anchor and `go` leaves the scroll alone. No frame
     callback, no animation: `scrollIntoView` here is instant, and motion on this page is CSS
     motion so that one `prefers-reduced-motion` rule reaches all of it. The ask is used once:
     a later visit to the page opens at the top. */
  anchored = false;
  if (kind === "knowledge" && !arg && K_JUMP){
    const el = document.getElementById("k-" + K_JUMP);
    if (el && el.scrollIntoView){ el.scrollIntoView({ block: "start" }); anchored = true; }
  }
  K_JUMP = "";
  /* THE BODY IS FETCHED AFTER THE PAGE IS ON SCREEN, never before it. A command's text is
     the largest thing this app reads and it is not what the reader came for — the verdict,
     the slots and the steps are already painted, and the prose arrives into a placeholder
     that says so. A failed fetch replaces the placeholder with the reason; it never leaves a
     reader watching a spinner that has already given up. */
  /* WHAT TO FETCH IS DECIDED FROM THE ROUTE, never read back out of the markup that was just
     written. An earlier version asked `main.querySelector("[data-cmdbody]")` — the placeholder
     it had itself just drawn — which is a round trip through the document to learn a path this
     function already had, and it made the whole read invisible to anything that does not build a
     real node tree. The route names the agent; the agent names its file; the cache says whether
     it is already held. */
  const wanted = kind === "command" && BODY_LOADER ? cmdById(arg) : null;
  if (wanted && typeof (cmdTree().bodies || {})[wanted.path] !== "string" &&
      held(BODY_CACHE, wanted.path) === undefined){
    fetchText(BODY_LOADER, BODY_CACHE, wanted.path, "The prompt could not be read: ", r);
  }
  if (kind === "doc" && DOC_LOADER && arg && held(DOC_CACHE, arg) === undefined){
    fetchText(DOC_LOADER, DOC_CACHE, arg, "This document could not be read: ", r);
  }
  /* THE INDEX COMPARES REPOSITORIES, so it needs one reading per repository. Asked for AFTER
     the page is painted, for the reason the two above are: the rows, the names and the states
     are already on screen out of `/api/corpora`, and the counts arrive into cells that say they
     are still coming. */
  if ((kind === "commands" || (kind === "settings" && arg === "agents")) && manyRepos()) wantRepoTrees();
  /* AND A ROUTE NAMING A REPOSITORY THIS PAGE IS NOT HOLDING STARTS READING IT. After the paint,
     for the reason the three reads above are: the crumb row, the selector and the sentence saying
     which repository is coming are already on screen. An empty argument is the primary under
     whichever spelling the list gives it — see `primaryKey`. */
  if (kind === "repo"){
    const want = repoKeyFor(arg) || primaryKey();
    if (want !== REPO) wantRepo(want);
  }
  /* AND THE CORPUS, ASKED AFTER THE PAINT for the reason the three reads above are: the crumb
     row, the narrowing controls and the sentence saying what is still coming are already on
     screen, and a page that renders nothing while a fetch is in flight looks exactly like one
     whose fetch failed. */
  if (kind === "knowledge") wantKnowledge(arg, r);
  ROUTED.forEach(fn => fn(r, arg));
  rzSettled(kind);
}

/* WHICH VIEW A ROUTE KIND DRAWS — one dispatch, read by `render` and by `embed`. It sits between
   `render` and `valid` on purpose: that span is where the route-table guard reads the renderer's
   kinds from (`test_js_render_agents.accepted_in`). */
function viewFor(kind, arg){
  return EXTRA[kind] ? EXTRA[kind](arg)
       : D === null ? corpusPlaceholder()
       : kind === "program" ? viewProgram(arg)
       : kind === "slice" ? viewSlice(arg)
       : kind === "prd" ? hostedPrd(arg)
       : kind === "board" ? (boardArrive(arg), viewBoard())
       : kind === "deps" ? viewDeps(arg)
       : kind === "commands" ? viewCommands()
       : kind === "repo" ? viewRepo(repoKeyFor(arg) || primaryKey())
       : kind === "command" ? viewCommand(arg)
       : kind === "slot" ? viewSlot(arg)
       : kind === "doc" ? viewDoc(arg)
       : kind === "knowledge" ? viewKnowledgeRoute(arg)
       : viewBoard();
}

/* A ROUTE'S PAGE AS MARKUP, FOR A HOST THAT DRAWS IT INSIDE ONE OF ITS OWN PAGES ("Needs you" draws
   the page of the item it has open beside its list): the same view `render` paints, without the
   tab's title, the shell's slot or the route hooks, which stay the outer page's. A route with no
   page draws the missing page's own words. */
function embed(r){
  const [kind, arg] = routeParts(r);
  const was = EMBEDDING;
  EMBEDDING = true;
  try { return missing(r) ? viewMissing(r) : viewFor(kind, arg); }
  finally { EMBEDDING = was; }
}

function valid(r){
  const [k, a] = routeParts(r);
  if (EXTRA[k]) return true;
  /* With no payload there are no entities to name, so an entity route cannot be validated —
     but the four corpus VIEWS still exist and must still be reachable, or a failed fetch
     would silently rewrite every link on the page to "board". */
  if (D === null) return ["board", "deps", "commands", "knowledge"].includes(k);
  if (k === "program") return !!PG[a];
  if (k === "slice") return !!SL[a];
  if (k === "prd") return !!PRD[a];
  /* An agent or slot id this tree does not carry is not a route: the page would render its
     own "no such agent" and the reader would have no way back to a list that has one. */
  if (k === "command") return !!cmdById(a);
  if (k === "slot") return !!slotById(a);
  /* A REPOSITORY THIS DEPLOYMENT DOES NOT SERVE IS NOT A ROUTE, and neither is one configured
     without a lane: `?repo=` matches on the lane, so there is no request that would fetch its
     board and following the link would leave the reader on the repository they were already
     reading, under another repository's name. `repo:` with an empty argument is the PRIMARY and
     is always valid — that is the request every read made while there was only one. */
  if (k === "repo") return !a || corpusRows().some(c => keyOf(c) === a || formerOf(c, a));
  /* A PATH NO AGENT CITES IS NOT A DOCUMENT ROUTE. `/api/commands/doc` serves exactly the
     citation set and refuses everything else, so a hash outside it is a page whose only possible
     content is a 404 — and this file already holds the set, so it can say so without asking. */
  if (k === "doc") return citedPaths(cmdTree()).has(a);
  /* A KNOWLEDGE ROUTE IS ONLY A ROUTE WHERE THE CORPUS CAN ACTUALLY BE READ. `kServed()` is the
     same bound `routeOf` links under — the index without a server behind it is a set of ids with
     no pages — and inside it the argument still has to name something: a declared kind, the
     cross-kind search, or an id THIS corpus holds. An id it does not hold is a page whose only
     possible content is "no such row", and this file already knows the answer without asking. */
  if (k === "knowledge"){
    /* THE TAB ITSELF IS ALWAYS REACHABLE, and for the four views' reason one branch up: it is a
       destination in the mast, and a corpus that carries no index must land the reader on the page
       that SAYS so rather than silently on the Programs list. Everything BELOW the tab needs a
       corpus that can actually be read. */
    if (!a) return true;
    if (!kServed()) return false;
    if (a === "search") return true;
    if (a === "prds") return true;
    /* DOCUMENTS BROWSER (ENG-10916) — list and one file. Existence is the detail page's job. */
    if (a === "documents" || a.startsWith("documents:")) return true;
    const at = a.indexOf(":");
    if (at < 0) return !!kKind(a);
    const held = KIND_IDS[a.slice(0, at)];
    return !!held && held.has(a.slice(at + 1));
  }
  /* `next` AND `priorities` ARE DELIBERATELY ABSENT. Both routes retired — the first view they
     named folded into this one — and neither gets a redirect crafted for it: a hash naming
     either now falls into the SAME bucket as any other route this corpus never had, and is told
     it is no page (`viewMissing`) exactly as a typo is. */
  return ["board", "deps", "commands"].includes(k);
}
/* WHERE THE READER IS RIGHT NOW. `go` writes the hash before it renders, so this is the route
   on screen — which is what a control that repaints in place needs, and what several of them
   used to spell as the literal `"board"` because every one of them lived on that page.

   `openRoute` AND NOT `here`, which is the obvious name and the wrong one: two functions in this
   file already declare a local called `here` (`paintNav`'s current tab, `viewGlossary`'s current
   term) and neither would then be able to ask this question. A shadow that is harmless today is
   the shape of a bug tomorrow, and it would be a silent one. */
/* THE AGENTS LIST IS ON SCREEN: its own route, or the host's Settings page showing it. */
function onAgentsList(){
  const [k, a] = routeParts(openRoute());
  return k === "commands" || (k === "settings" && a === "agents");
}
function openRoute(){ return canon(location.hash.slice(1) || "board"); }

/* WHICH TAB A ROUTE KIND SITS UNDER — the mark `render` paints, and the HOME a reader lands on
   when the page they were reading does not exist in the repository they just picked. One
   function for both, so a route can never light one tab and fall to another. A kind this file
   does not group is its own tab (`board`, `deps`, every host view); an unknown kind is handed
   back as itself, and `render` draws the missing page for it exactly as for a typo. */
function tabOf(kind){
  return ["program", "slice", "prd"].includes(kind) ? "board"
       : ["repo", "command", "slot", "doc", "commands"].includes(kind) ? (ALIAS ? "settings" : "commands") : kind;
}
/* THE TAB A ROUTE LIGHTS, given its argument: a SLICE WITH NO PROGRAM lives under its feature (FLT-1280), so its page lights "Features",
   the tab its crumb leads to, and not "Programs". Every other route is `tabOf`'s. */
function tabFor(kind, arg){
  return kind === "slice" && arg && SL[arg] && !SL[arg].program ? "areas" : tabOf(kind);
}

/* ── changing repository ──────────────────────────────────────────────────
 *
 * EVERYTHING UN-KEYED IS RESET, and the list is not a matter of taste: each of these is a piece
 * of page state that has no repository in it, so it would carry a reading of the OLD repository
 * into the new one and there would be nothing on screen saying why. Measured against the ones
 * that bite: a `stalled only` filter set on a four-program lane leaves a two-program lane
 * looking empty; a search for `prd:` leaves an agent table saying "no agent matches" in a
 * repository that has thirty; and Reorder mode left open would be a drag whose drop writes an
 * order into whichever repository the payload happens to be by then.
 *
 * THE TWO CACHES ARE KEYED RATHER THAN CLEARED. `BODY_CACHE` and `DOC_CACHE` are keyed by
 * repository AND path (`textKey`), which is a stronger fix than emptying them: two repositories'
 * `.claude/commands/plan.md` no longer collide, AND a reader who switches back does not pay for
 * the same megabyte twice.
 *
 * THE SORT AND THE FILTER ARE RE-READ rather than reset. They are stored per repository
 * (`prefKey`), so what the new repository gets is whatever the reader last chose THERE — and a
 * repository they have never sorted gets the default, which is the same thing a reset would have
 * given them without throwing away the other repository's choice.
 */
function repoReset(key){
  REPO = key;
  for (const k of Object.keys(ELSEWHERE)) delete ELSEWHERE[k];
  SWITCH_ERR = null;
  SWITCH_FAILED = null;
  REPO_REFUSED = null;
  CMD_Q = "";
  CMD_GROUP = "family";
  AG_SHUT = {};
  openDD = null;
  anchored = false;
  REORDER_MODE = false;
  REORDER_BUSY = "";
  REORDER_ERR = null;
  REORDER_ANNOUNCE = "";
  RZ_DRAFT = null;
  RZ_SAVED = null;
  /* THE KNOWLEDGE LIST'S SEARCH, FACETS AND CURSOR ARE ONE REPOSITORY'S (ENG-10706): carried across
     a switch, the last repository's query and page-3 cursor were sent to the next one's list. */
  K_TYPED = "";
  K_QUERY = "";
  for (const held of [K_FACET, K_TRAIL, K_AT]) for (const k of Object.keys(held)) delete held[k];
  sortKey = store.get(prefKey("zb.sort"), "priority");
  filters = new Set((store.get(prefKey("zb.filters"), "hideComplete") || "").split(",").filter(Boolean));
  /* THE NARROWING IS PER-VISIT (PRD 0839): a repository switch re-seeds it OFF, like the first
     load — nothing about it is a reader's saved preference. */
  mineOn = false;
  /* AND THE CORPUS INDEX IS RE-READ, because it is the one piece of knowledge state that is not
     keyed by repository — see `kBoot`. After `REPO` has moved, so the host's own `?repo=` names
     the repository the reader just picked rather than the one they left. */
  kBoot(() => { if (routeParts(openRoute())[0] === "knowledge") render(openRoute()); });
  /* THE CHOICE OUTLIVES THE PAGE — see "where the choice lives". The URL is NOT written here:
     which history entry it lands on is the caller's decision, because a switch the reader made
     is a step the back button should undo and a switch the back button made is not. */
  persistRepo();
  notifyRepo();
}

/* PICKING A REPOSITORY IN THE CRUMB ROW IS A NAVIGATION AND NOTHING ELSE. It was tempting to
   make it a fetch that navigates when it lands, and that is the version that breaks a bookmark:
   the route would only ever work for a reader who had just clicked the control. So the click
   goes to the route, and the route is what decides it needs a board it does not have. The
   masthead's selector is the OTHER control over the same state and takes the other path,
   `switchTo`: it stays where the reader is. */
function repoSwitch(key){
  openDD = null;
  return go("repo:" + key);
}

/* WHERE A ROUTE LANDS ONCE THE REPOSITORY UNDER IT HAS CHANGED. The same route when the new
   payload still has it — `#board`, `#deps`, `#knowledge`, a host view, a `#program:PG-14` the new
   corpus also carries — and otherwise that tab's home: a program the new corpus lacks lands on
   the Programs list, an agent it lacks on the Agents tab, a knowledge id it lacks on the
   Knowledge tab. Never the app's default for all of them alike, which would drop a reader who
   was comparing agents onto the Programs list. A `repo:` route names a repository in the route
   itself, so it is re-spelt for the one just picked: the same page, about the new subject. */
function landing(r){
  const [kind] = routeParts(r);
  if (kind === "repo") return "repo:" + REPO;
  /* THE SORT AND FILTER STAY WITH THE REPOSITORY THEY WERE CHOSEN ON (ENG-10706, M-03). The route
     carries them (`#board:sort=…&filter=…`), and a query arriving on a route "sets the state it
     names and saves it" — so a switch that kept the query saved one repository's view as the
     other's. The list is re-entered bare and reads the new repository's own stored choice. */
  if (kind === BOARD_ROUTE) return BOARD_ROUTE;
  if (valid(r)) return r;
  /* An agent the new corpus lacks lands on the Agents list itself, not on the tab that frames it: a
     host that folds Agents into Settings would otherwise drop the reader on Settings' first pane. */
  return ["repo", "command", "slot", "doc", "commands"].includes(kind) ? "commands" : tabOf(kind);
}

/* WHAT A HOST HAS TO DO IS NOT DESCRIBED HERE, only asked for. `SWITCH_REPO` re-reads that
   repository's board and installs it (`Board.boot`), because everything the host keeps beside the
   payload — its own chrome, its nav counts, its arrival marks — has to move at the same instant
   and this file knows about none of it. It returns a promise; this file re-renders on either
   branch, so a refused read never leaves the page claiming to be somewhere it is not.

   ONE SWITCH, TWO ENTRANCES. The crumb row's dropdown navigates to `repo:<key>` and the route
   asks for the board it lacks (`wantRepo`, below); the masthead's selector and the back button
   ask for the repository directly and keep the reader where they are (`landing`). Both come
   through here, so what a switch RESETS, what it persists and whom it tells are written once.

   `replace` DECIDES WHICH HISTORY ENTRY CARRIES THE NEW REPOSITORY. A pick in the masthead is a
   step the reader took, so it PUSHES — the back button then returns them to the repository they
   left, on the page they left it at, which `popstate` honours below. A switch that is itself the
   back button's doing, or one a `repo:` route already pushed, re-addresses the entry on screen.

   THE LANDING IS COMPUTED WHEN THE BOARD ARRIVES, off the route on screen THEN — never off the
   route the switch was asked from. A reader who clicked the crumb row and, while the board was
   on the wire, moved to the Dependencies tab is on Dependencies when it lands, and the honest
   thing is to render the new repository's Dependencies rather than to yank them back to the
   page they left. */
function switchTo(key, opts){
  const o = opts || {};
  if (!SWITCH_REPO) return Promise.resolve(false);
  if (key === REPO) return Promise.resolve(true);
  if (SWITCH_BUSY === key) return Promise.resolve(false);
  SWITCH_BUSY = key;
  SWITCH_ERR = null;
  SWITCH_FAILED = null;
  notifyRepo();
  return SWITCH_REPO(key).then(
    () => {
      SWITCH_BUSY = null;
      repoReset(key);
      const land = landing(openRoute());
      openDD = null;
      navOpen = false;
      if (o.replace) history.replaceState({ r: land }, "", urlFor(land));
      else history.pushState({ r: land }, "", urlFor(land));
      render(land);
      if (!anchored) window.scrollTo(0, 0);
      return true;
    },
    err => {
      SWITCH_BUSY = null;
      SWITCH_FAILED = key;
      SWITCH_ERR = (err && err.message) ? String(err.message) : String(err);
      /* THE HOST'S TOAST SAYS IT (`NOTIFY`); the `repo:` page that cannot be drawn still says it too,
         because there it is the page's state rather than the result of a click. */
      if (NOTIFY){
        const name = repoName(corpusFor(key)) || key || "the primary repository";
        NOTIFY(`<b>${esc(name)} could not be read</b> &mdash; ${esc(SWITCH_ERR)}`, "err");
      }
      /* THE PAGE IS STILL THE REPOSITORY IT WAS, so the URL must say so too — a back-button
         switch has already moved the address to the repository that just refused. */
      if (o.replace) history.replaceState({ r: openRoute() }, "", urlFor(openRoute()));
      notifyRepo();
      render(openRoute());
      return false;
    });
}

/* THE `repo:` ROUTE'S HALF: a route naming a repository the page is not holding. TRIED ONCE PER
   FAILURE, and `SWITCH_FAILED` is why. The failure branch re-renders, the render sees a route
   whose repository is still not in hand, and without a record of what just refused it would ask
   again — a page that retries a refused request as fast as it can paint. The route is already
   on screen and already pushed, so the entry is re-addressed rather than pushed again. */
function wantRepo(key){
  if (!SWITCH_REPO || SWITCH_BUSY === key) return;
  if (SWITCH_ERR && SWITCH_FAILED === key) return;
  switchTo(key, { replace: true });
}

/* `urlFor(r)`, NOT `"#" + r`. A fragment-only URL resolves against the document's BASE URL, so
   it keeps the query only while the base is the document itself. When the shell still set a
   base element, `pushState("#deps")` after `/?repo=primary#board` landed on `/#deps` (measured in
   a browser) and the repository fell off the URL on the first click. The shell sets none now
   (BUG-1164), but the full URL does not depend on that: every navigation spells it out wherever
   there is a repository to carry (`urlFor`), and `"#" + r` exactly as before wherever there is not. */
/* THE KEYS AND THE BUTTON THAT MEAN "NOT HERE": the four modifiers a browser reads as open-elsewhere,
   and any button but the main one. `button` is read as a number because the harness's synthetic
   events carry none, and "absent" is the main button rather than a middle click. */
function modifiedClick(e){
  return !!(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || (Number(e.button) || 0) !== 0);
}

function go(r, push = true){
  HOPPED = "";
  /* NOT NORMALISED TO `board` (ENG-10589): a link to an id the corpus has since lost renders the
     missing page under its own route, so the reader sees which link went stale. */
  openDD = null;
  navOpen = false;
  /* A navigation is the reader's own act, and it supersedes whatever the last one said (RK-01). */
  if (!REORDER_MODE) REORDER_ANNOUNCE = "";
  if (push) history.pushState({ r }, "", urlFor(r));
  render(r);
  if (!anchored) window.scrollTo(0, 0);
}
/* GO TO A ROUTE IN THE REPOSITORY THAT OWNS IT. A script that navigates (an accept that lands on the feature it
   added to) has the same obligation a link has: `go(route)` alone keeps the reader's repository, and a route about
   another repository's record then renders under the wrong one (one repository's feature opened under another's: an empty
   page). Under the repository in hand, or with none named, this is `go`; for another served repository the
   entry is pushed under that repository's address and the selection moves first, exactly as a `data-go-repo` click. */
function goIn(r, repo){
  const about = String(repo || "");
  if (about && about !== REPO && SWITCH_REPO && corpusFor(about)){
    history.pushState({ r }, "", urlFor(r, about));
    return switchTo(keyOf(corpusFor(about)) || about, { replace: true });
  }
  return go(r);
}
/* THE BACK BUTTON CROSSES REPOSITORIES TOO. Every entry this page pushes carries the repository
   it was about (`urlFor`), so an entry whose `?repo=` names a repository other than the one in
   hand is a step back across a switch — and rendering its route over the CURRENT payload would
   put one repository's page under another repository's address, which is the lie this whole
   arrangement exists to refuse. So the repository moves first and the route renders after,
   through the same `switchTo` the selector uses, re-addressing the entry it is already on. An
   entry with no `?repo=` on a deployment that serves several is the primary's: the only pages
   written without one are the primary's on a server that cannot name it. Nothing here runs on
   one corpus or standalone — `manyRepos()` is false and the route is judged as it always was.

   AND THE ENTRY IS JUDGED, NOT TRUSTED. This handler used to render the route raw, on the
   reasoning that every entry this page writes was valid when it was written — which is true and
   is not the whole set. A fragment-only change of address is a same-document navigation and
   lands here too: a deep link pasted into a tab that is already open, a hash edited by hand, a
   link followed from another page under the same query. None of those was ever judged, and an
   id the corpus lacks reached `viewProgram` and threw — measured on `?repo=apps#board`
   followed by `?repo=apps#program:PG-01`, a corpus with no programs at all. The back
   button has the same hole one sync later, when the entity an entry names has since left the
   corpus. So the route goes through `enter`, exactly as a cold load's does: judged against what
   is in hand, corrected in place when it names nothing, held while nothing can judge it yet.
   The state stamped on the entry and the hash are one fact by construction (`urlFor` writes
   both from the same route), so reading the hash, as `enter` does, loses nothing. */
window.addEventListener("popstate", () => {
  HOPPED = "";
  if (manyRepos() && SWITCH_REPO){
    /* A FORMER NAME IS THE LANE IT BECAME, so an old entry naming the lane on screen is no switch. */
    const want = repoKeyFor(urlRepo()) || primaryKey();
    if (want !== REPO && (want === "" || corpusFor(want))){
      switchTo(keyOf(corpusFor(want) || {}) || want, { replace: true });
      return;
    }
    /* AN ENTRY NAMING A REPOSITORY NOTHING SERVES IS REFUSED BY NAME (ENG-10706), as a cold load's
       `?repo=` is — it used to render the page in hand under that name without a word. */
    if (want && want !== REPO && !corpusFor(want)){ REPO_REFUSED = { name: want, why: "not served" }; notifyRepo(); }
  }
  enter(HOME);
  if (!anchored) window.scrollTo(0, 0);
});
document.addEventListener("click", e => {
  /* A CHIP INSIDE A LINK EXPLAINS; IT DOES NOT NAVIGATE (ENG-12873). A tip-bearing chip carries
     its whole meaning in `data-tip`, and on a phone a tap is the only way to reach it. Inside a
     navigating row or a map node the nearest link is an ANCESTOR, so the browser's default link
     action won the tap and the popover never opened. This is the one place every chip in a link
     on either page gets stopped — the chip opens its own popover and the row's link is not
     followed, while a tap anywhere else on the row still routes. Three things are left alone: a
     chip that IS the link (`data-go` on the chip itself) keeps navigating, a modified click is
     the browser's to open elsewhere, and a real control wearing a tip (a chip's own close
     button, a filter toggle) is that control's, not the tip's. Desktop hover and keyboard focus
     are untouched — `showTip`'s mouseover/focusin listeners still own those. */
  const chip = e.target.closest("[data-tip]");
  const chipLink = chip && chip.closest("[data-go]");
  if (chip && chipLink && chipLink !== chip && !modifiedClick(e)
      && !e.target.closest("button,input,select,textarea")){
    e.preventDefault();
    if (e.stopPropagation) e.stopPropagation();
    showTip(chip);
    return;
  }
  /* A DEFINED WORD OPENS ITS DEFINITION ON A TAP TOO (`term()`, `defined()`). Hover and focus
     already do; a phone has neither, and the word is not inside a link to steal the tap. */
  if (chip && !chipLink && chip.getAttribute("data-term") !== null){ showTip(chip); return; }
  /* A WAY INTO ONE KIND OF KNOWLEDGE (`kindLink`): the row it names is open when the page paints,
     and the router scrolls to it. Not a return — the link itself still navigates, below. A modified
     click is the browser's, and opens the page in a new tab at the top. */
  const kj = e.target.closest("[data-kjump]");
  if (kj && !modifiedClick(e)){ K_JUMP = kj.getAttribute("data-kjump") || ""; K_OPEN.add(K_JUMP); }
  /* THE PERSON'S NEXT ACT SUPERSEDES THE LAST STATUS (RK-01) — any click outside Reorder mode;
     inside it every act writes its own sentence. */
  if (!REORDER_MODE) REORDER_ANNOUNCE = "";
  const nb = e.target.closest("[data-nav]");
  if (nb){ navOpen = !navOpen; return paintNav(false); }
  /* Any other click dismisses it, and deliberately does NOT return: picking a destination out
     of the open list must not cost the reader a second tap. */
  if (navOpen){ navOpen = false; paintNav(false); }
  /* A DROPDOWN IS INERT WHILE REORDER MODE IS OPEN — `toolbar`'s own comment gives the reason for
     the sort and filter (a filtered or re-sorted write would be a silent partial order), and their
     handlers refuse it too. */
  const dd = e.target.closest("[data-dd]");
  /* `openRoute()` RATHER THAN "board", and the repository selector is why. Every dropdown on this page
     used to live on the Programs list, so re-rendering "board" was both correct and shorter; the
     selector in the Agents crumb row is a `[data-dd]` on another page entirely, and opening it
     with the old line navigated the reader to the Programs list. */
  if (dd) { if (REORDER_MODE) return; openDD = openDD === dd.dataset.dd ? null : dd.dataset.dd; return render(openRoute()); }
  const pg = e.target.closest("[data-pg-g]");
  if (pg){ BOARD_SHUT[pg.dataset.pgG] = pg.getAttribute("aria-expanded") === "true"; return render(openRoute()); }
  const ag = e.target.closest("[data-ag-g]");
  if (ag){ AG_SHUT[ag.dataset.agG] = ag.getAttribute("aria-expanded") === "true"; return render(openRoute()); }
  /* THE REPOSITORY the whole page is about. */
  /* `getAttribute`, NOT `dataset`, AND THE DIFFERENCE IS NOT COSMETIC HERE. `data-repo=""` is a
     real value — the primary, addressed by asking for nothing — and it has to survive the read
     as the empty string rather than as a missing property. */
  const rp = e.target.closest("[data-repo]");
  if (rp) return repoSwitch(rp.getAttribute("data-repo") || "");
  /* THE CORPUS LIST'S OWN NARROWING. `getAttribute` and not `dataset` for `data-kvalue`, the
     same reason `data-repo` reads that way one line up: "" is a real value here — it is the
     "all" item and the cross in a filter chip — and it has to survive the read as the empty
     string rather than as a missing property.

     EVERY NARROWING RESETS THE PAGE TO THE FIRST. A cursor names a position in ONE result set;
     carried across a filter change it names a position in a set that no longer exists, and what
     comes back is a page of rows from somewhere in the middle of a different question. */
  const kp = e.target.closest("[data-kpage]");
  if (kp){
    let kind = routeParts(openRoute())[1] || "";
    if (kind.startsWith("documents")) kind = "documents";
    const trail = K_TRAIL[kind] || (K_TRAIL[kind] = [""]);
    const at = K_AT[kind] || 0;
    if (kp.getAttribute("data-kpage") === "prev"){ K_AT[kind] = Math.max(0, at - 1); }
    else {
      const listPath = kind === "prds" ? kPrdsPath()
        : kind === "documents" ? kDocsPath()
        : kListPath(kind);
      const next = kNext(kHold(listPath).data);
      if (!next) return;
      trail.length = at + 1;
      trail.push(next);
      K_AT[kind] = at + 1;
    }
    window.scrollTo(0, 0);
    return render(openRoute());
  }
  /* AN ANCHOR IN A RENDERED DOCUMENT SCROLLS, IT DOES NOT NAVIGATE — see `outlineRail`. */
  const an = e.target.closest("[data-anchor]");
  if (an){
    const el = document.getElementById(an.getAttribute("data-anchor"));
    if (el) el.scrollIntoView({ block: "start" });
    return;
  }
  const fx = e.target.closest("[data-slotfix]");
  if (fx) return ACTION && ACTION(fx.dataset.slotfix, slotById(fx.dataset.slotfix));
  /* REORDER MODE'S OWN CONTROLS, BEFORE THE ROW'S `data-go`: every one of them sits INSIDE a
     row that carries `data-go`, so `closest` on the row's attribute would answer for a click on
     its button. A control edits the draft; Save writes it; the toggle enters the mode or, from
     inside it, cancels — the same `data-rz-toggle` in both states, so the caret comes back to
     the same slot (`reorderBar`'s own comment). */
  /* THE CONFLICT'S TWO WAYS ON AND THE COMPARISON'S TWO (ENG-10701, K-01). */
  if (e.target.closest("[data-rz-theirs]")){
    if (REORDER_MODE && !REORDER_BUSY) rzTakeTheirs();
    return;
  }
  if (e.target.closest("[data-rz-over]")){
    if (REORDER_MODE && RZ_CONFLICT && !REORDER_BUSY) commitOrder(draftOrder(), RZ_CONFLICT.revision);
    return;
  }
  if (e.target.closest("[data-rz-mine]")){
    if (REORDER_MODE && !REORDER_BUSY) rzUseMine();
    return;
  }
  if (e.target.closest("[data-rz-dismiss]")){
    RZ_MINE = null;
    return rzRerender();
  }
  const ra = e.target.closest("[data-rz-act]");
  if (ra){
    if (!REORDER_MODE || REORDER_BUSY) return;
    return rzAct(ra.getAttribute("data-rz-row"), ra.getAttribute("data-rz-act"));
  }
  const rs = e.target.closest("[data-rz-save]");
  if (rs){
    if (!REORDER_MODE || !rzDirty()) return;
    return commitOrder(draftOrder());
  }
  const rz = e.target.closest("[data-rz-toggle]");
  if (rz){
    if (!REORDER) return;
    if (REORDER_MODE){ rzLeave(); return rzRerender(); }
    /* IN, WITH THE CARET ON THE FIRST ROW (K-05): the list is where the next key belongs, and the
       Cancel that replaced the button is one Tab past it. */
    rzEnter();
    rzRerender();
    return rzReveal(RZ_ACTIVE, false);
  }
  const t = e.target.closest("[data-go]");
  if (t) {
    /* A MODIFIED CLICK ON A REAL LINK IS THE BROWSER'S (ENG-10590): Cmd/Ctrl-click opens a new
       tab, Shift-click a new window, a middle button a background tab — and every one of those
       arrives here as a `click` the router used to swallow with `preventDefault`. An anchor
       with an `href` is left alone on those; a span or a button (no href to open anywhere) is
       routed as before, whatever keys are down. */
    if (modifiedClick(e) && t.getAttribute("href")) return;
    /* AND AN ANCHOR THAT ASKS FOR A NEW TAB GETS ONE (`mdIds`' `opts.tab`): routing it in-page
       would take the reader off the surface the new tab exists to leave alone. */
    if (t.getAttribute("target") === "_blank" && t.getAttribute("href")) return;
    e.preventDefault();
    /* DRILL-IN IS SUPPRESSED, THE ELEMENT IS NOT SWAPPED. The row that carries `data-go` is the
       same element whether or not Reorder mode is open — see `rowHtml`'s own comment — so what
       changes here is whether this handler ACTS on the attribute, never whether the attribute or
       the element exists. `data-rz-card` is only ever present on a row Reorder mode is rendering,
       so this never swallows a click on a breadcrumb or a badge outside that mode. */
    if (REORDER_MODE && t.getAttribute("data-rz-card") !== null){
      /* A TAP ON A ROW CHOOSES IT — on a phone that is what brings out its full controls. Judged by
         what is DRAWN, not by `RZ_ACTIVE`: the tap focused the row on the way down, and focus moves
         the Tab stop without a repaint, so by the click the row is already "active" and still drawn
         folded (measured at 390 px, ENG-10701). */
      const chosen = t.getAttribute("data-rz-card");
      if (chosen && (chosen !== RZ_ACTIVE || !t.classList || !t.classList.contains("rz-on"))){
        RZ_ACTIVE = chosen;
        rzRerender();
        rzReveal(chosen, false);
      }
      return;
    }
    /* A LINK TO ANOTHER REPOSITORY'S RECORD MOVES THE SELECTION FIRST (ENG-10706): the route is
       rendered against the payload in hand, so a fleet idea's PG-25 opened the primary's program. The
       entry is pushed under the record's repository and the switch re-addresses it in place. */
    return goIn(t.dataset.go, t.getAttribute("data-go-repo") || "");
  }
  if (openDD && !e.target.closest(".dd")) { openDD = null; render(openRoute()); }
});

document.addEventListener("keydown", e => {
  if (e.key !== "Escape") return;
  if (navOpen){ navOpen = false; return paintNav(true); }
});

/* ══ THE SAME ACTS FROM A KEYBOARD, plus the two this mode adds of its own: entering it and
   leaving it. A drag is not reachable from a keyboard, so a mode that could only be turned on by
   a pointer would make reordering mouse-only — the WCAG 2.1.1 failure the priorities page's own
   keyboard path was built to avoid, now reachable from a plain Programs row too.

   THE ARROWS ARE BARE (ENG-10673). They used to want `Alt`, on the argument that a focused row
   holds the caret for as long as a reader works here and a bare arrow is how every reader
   scrolls. A row holds the caret only while a reader has put it there — by Tab or by a click on
   the row they mean to move — and a reorderable list whose focused item does not move on an
   arrow is a list nobody can operate without reading the shortcuts first (the operator: "the UX
   sucks"). The page still scrolls on every arrow whose target is not a row, and on an arrow on an
   UNPLACED row, which has no place to move to and lets the key through. `Alt` still works, so a
   hand that learned the old chord is not wrong. */
document.addEventListener("keydown", e => {
  if (!e.target.closest) return;
  if (!REORDER_MODE){
    /* ENTER: Alt+Enter on a focused program row, on the Programs list only — a row on some
       other page that happens to link to a program (a badge, a breadcrumb) is not this. Focus
       follows the SAME ROW into Reorder mode, rather than landing wherever the browser defaults
       an element that just left the document — the reader asked to move THIS one. */
    if (!REORDER || !e.altKey || e.ctrlKey || e.metaKey || e.key !== "Enter") return;
    if ((location.hash.slice(1) || "").split(":")[0] !== "board") return;
    const row = e.target.closest("[data-go^='program:']");
    if (!row) return;
    e.preventDefault();
    const id = (row.getAttribute("data-go") || "").slice("program:".length);
    rzEnter(id);
    render(location.hash.slice(1) || "board");
    const entered = main && main.querySelector(`[data-keep="rz-card-${id}"]`);
    if (entered && entered.focus) entered.focus({ preventScroll: true });
    return;
  }
  /* INSIDE THE POSITION BOX the keys are the box's own — arrows step the number, digits type it.
     Enter commits what was typed (the `change` listener commits a blur), Escape puts the box back
     and hands the caret to its row. */
  const box = e.target.closest("[data-rz-pos]");
  if (box){
    if (e.key === "Enter"){ e.preventDefault(); rzPosition(box.getAttribute("data-rz-pos"), box.value); }
    else if (e.key === "Escape"){
      e.preventDefault();
      const id = box.getAttribute("data-rz-pos");
      render(location.hash.slice(1) || "board");
      const row = id && main && main.querySelector(`[data-keep="rz-card-${id}"]`);
      if (row && row.focus) row.focus({ preventScroll: true });
    }
    return;
  }
  /* LEAVE: Escape — with nothing unsaved. A draft that differs from what is stored is the
     reader's work, and one key must not throw it away: the caret goes to Save order, the live
     region says why, and Cancel is the deliberate act that discards. Focus lands back on the
     program's own row on the way out, for the same reason entering names a destination. */
  if (e.key === "Escape"){
    e.preventDefault();
    if (rzDirty()){
      REORDER_ANNOUNCE = "Changes not saved yet. Press Save order to keep them, or Cancel to drop them.";
      rzRerender();
      const save = main && main.querySelector('[data-keep="rz-save"]');
      if (save && save.focus) save.focus({ preventScroll: true });
      return;
    }
    const card = e.target.closest("[data-rz-card]");
    const id = card ? card.getAttribute("data-rz-card") : "";
    rzLeave();
    render(location.hash.slice(1) || "board");
    const left = id && main && main.querySelector(`[data-go="program:${id}"]`);
    if (left && left.focus) left.focus({ preventScroll: true });
    return;
  }
  if (REORDER_BUSY) return;
  const card = e.target.closest("[data-rz-card]");
  if (!card) return;
  const id = card.getAttribute("data-rz-card");
  const placed = card.getAttribute("data-rz-from") === "placed";
  /* THE LIST IS ONE TAB STOP AND THE ARROWS WALK IT (ENG-10701, K-05) — WAI-ARIA's composite
     widget, and the reversal of ENG-10673's bare arrow that moved the row: with a row per Tab
     stop, getting to the program at the foot of the list was 95 Tabs and the whole walk 197 keys.
     Moving is Alt+arrow, the chord editors move a line with; Home and End move to the ends as they
     did; Ctrl (Cmd on a Mac) with an arrow, Home or End jumps the caret to the first or last row;
     Page Up and Page Down walk ten rows. So the bottom program reaches the top in two keys from the
     first row — Ctrl+End, Home — and Tab from there is Save. */
  /* A BARE KEY MOVES THE CARET; ALT WITH IT MOVES THE ROW (RK-03). Home and End used to move the
     row itself, which on every other list means "first" and "last" — a first-time keyboard user
     reordered the board by looking for its top. Now every bare key does what a list does, and one
     modifier, Alt, turns the same key into the move: Alt+&uarr;/&darr; one place, Alt+Home/End to
     the ends. Ctrl (Cmd) with an arrow, Home or End still jumps the caret to the ends. */
  const far = e.ctrlKey || e.metaKey;
  if (e.key === "ArrowUp" || e.key === "ArrowDown"){
    e.preventDefault();
    const up = e.key === "ArrowUp";
    if (e.altKey) return rzAct(id, up ? "up" : "down", true);
    return rzWalk(id, far ? (up ? "first" : "last") : (up ? -1 : 1));
  }
  if (e.key === "PageUp" || e.key === "PageDown"){
    e.preventDefault();
    return rzWalk(id, e.key === "PageUp" ? -RZ_PAGE : RZ_PAGE);
  }
  if (e.key === "Home" || e.key === "End"){
    e.preventDefault();
    if (e.altKey && !far) return rzAct(id, e.key === "Home" ? "top" : "bottom");
    return rzWalk(id, e.key === "Home" ? "first" : "last");
  }
  if (far) return;
  if (/^[0-9]$/.test(e.key) && !e.altKey){ e.preventDefault(); return rzTypeInto(id, e.key); }
  if (e.key === "Enter" || e.key === " "){ e.preventDefault(); return rzTypeInto(id); }
  if ((e.key === "Delete" || e.key === "Backspace") && placed){ e.preventDefault(); return rzAct(id, "out"); }
});
/* THE TAB STOP FOLLOWS THE CARET, however it got there — a click, a tap on a row's box, a drag's
   own focus — without a repaint: the row that had the stop gives it up, this one takes it.

   AND NOTHING ELSE MOVES. It used to open the row's full strip too (`rz-on`), and on a phone that
   strip is a new line under the row: a tap on "Place at top" focused the button on the way down,
   the strip opened, the button moved, and the click landed on the empty space it had left — the
   bottom program's one-tap way to the top did nothing (measured at 390 px, ENG-10701). A row opens
   its strip only when it is chosen on purpose — walked to, tapped on its name, or moved — each of
   which repaints the list with it chosen. */
document.addEventListener("focusin", e => {
  if (!REORDER_MODE || !e.target || !e.target.closest) return;
  const card = e.target.closest("[data-rz-card]");
  const id = card && card.getAttribute("data-rz-card");
  if (!id || id === RZ_ACTIVE) return;
  const was = RZ_ACTIVE && main ? main.querySelector(`[data-keep="rz-card-${RZ_ACTIVE}"]`) : null;
  if (was && was !== card) was.setAttribute("tabindex", "-1");
  card.setAttribute("tabindex", "0");
  RZ_ACTIVE = id;
});
/* Recursive chain highlight on the build-step maps: every prerequisite beneath a node and
   everything that waits on it, transitively, over the one graph both maps draw (`waveG`) — a PRD's
   `depends_on` chain, up through the slice it sits in to the program that slice belongs to. */
function closure(id, dir){
  const g = waveG(), edges = g[dir] || {};
  const out = new Set(), stack = [id];
  while (stack.length){
    const n = stack.pop();
    for (const x of edges[n] || []){
      if (!out.has(x)){ out.add(x); stack.push(x); }
    }
  }
  return out;
}
function chainOf(id){
  return { up: [...closure(id, "up")].sort(), down: [...closure(id, "down")].sort() };
}
function lightChain(id){
  const waves = document.getElementById("waves");
  if (!waves || D === null) return;
  const up = closure(id, "up"), down = closure(id, "down");
  waves.classList.add("dim");
  waves.querySelectorAll("[data-node]").forEach(el => {
    const n = el.dataset.node;
    el.classList.toggle("hl-self", n === id);
    el.classList.toggle("hl-up", up.has(n));
    el.classList.toggle("hl-down", down.has(n));
  });
  const c = document.getElementById("chain");
  /* THE READOUT COUNTS WHAT IS DRAWN (ENG-10704, R-14): it counted finished slices nobody could see. */
  const drawn = new Set(Array.prototype.map.call(waves.querySelectorAll("[data-node]"), el => el.dataset.node));
  const upN = [...up].filter(n => drawn.has(n)).length, downN = [...down].filter(n => drawn.has(n)).length;
  if (c) c.textContent = `${id} - ${upN} prerequisite${upN === 1 ? "" : "s"} beneath it, `
    + `${downN} waiting on it`;
}
function clearChain(){
  const waves = document.getElementById("waves");
  if (!waves) return;
  waves.classList.remove("dim");
  waves.querySelectorAll("[data-node]").forEach(el =>
    el.classList.remove("hl-self", "hl-up", "hl-down"));
  /* EMPTY AT REST. It used to hold the instruction that told a reader the highlight existed;
     the nodes now carry their own edge counts, so this is a readout of the transitive closure
     and nothing else. `aria-live` is what makes it reach a screen reader when it fills. */
  const c = document.getElementById("chain");
  if (c) c.textContent = "";
}
document.addEventListener("mouseover", e => {
  const n = e.target.closest("[data-node]");
  if (n) lightChain(n.dataset.node);
  else if (!e.target.closest("#waves")) clearChain();
});
document.addEventListener("focusin", e => {
  const n = e.target.closest("[data-node]");
  if (n) lightChain(n.dataset.node);
});

/* Hover preview. Fixed to the viewport and flipped near the edges, so a long
   `Done when` is never clipped by the table's own scroll container. */
const tip = document.createElement("div");
tip.id = "tip"; tip.hidden = true; document.body.appendChild(tip);
if (tip.setAttribute) tip.setAttribute("role", "tooltip");
function showTip(el){
  const txt = el.getAttribute("data-tip");
  if (!txt) return;
  tip.textContent = txt; tip.hidden = false;
  /* WHAT A SCREEN READER HEARS ON FOCUS: the element is described by the popover it opened, which
     is how a word's definition reaches a reader who cannot see the hover. */
  if (el.setAttribute) el.setAttribute("aria-describedby", "tip");
  /* A MULTI-LINE TIP (`data-tip-lines`) keeps its line breaks; every other tip flows as before. */
  /* `getAttribute(…) !== null`, the accessor this function already reads `data-tip` with: a tip
     can be shown on any element that carries one, and `hasAttribute` is one more method to assume. */
  if (tip.classList) tip.classList.toggle("lines", el.getAttribute("data-tip-lines") !== null);
  const r = el.getBoundingClientRect(), t = tip.getBoundingClientRect();
  let left = Math.min(r.left, window.innerWidth - t.width - 12);
  let top = r.bottom + 8;
  if (top + t.height > window.innerHeight - 8) top = Math.max(8, r.top - t.height - 8);
  tip.style.left = Math.max(8, left) + "px";
  tip.style.top = top + "px";
}
const hideTip = () => { tip.hidden = true; };
document.addEventListener("mouseover", e => {
  const el = e.target.closest("[data-tip]");
  el ? showTip(el) : hideTip();
});
document.addEventListener("focusin", e => {
  const el = e.target.closest("[data-tip]");
  el ? showTip(el) : hideTip();
});
document.addEventListener("focusout", hideTip);
window.addEventListener("scroll", hideTip, { passive: true });


/* ── the payload arrives, or it does not ─────────────────────────────────── */

/* Everything derived from the payload, in one place. Called by `start` when the first reading
   lands, and by the host every time it re-reads the corpus after that.

   RETURNS WHETHER IT ENTERED THE ROUTE. A route the cold load arrived with is held in the hash,
   unjudged, until a payload exists to judge it against (`enter`, below) — and the payload that
   arrives first is not always `start`'s own, because the host's re-read can land inside the
   window. So the judgement is made HERE, by whichever payload is first, and the caller is told:
   `start` then has nothing left to enter and repaints nothing twice, and a host that repaints the
   hash raw afterwards repaints a route this file has already corrected. A payload that finds no
   hold — every re-read after boot, every switch — installs and returns `false`, exactly as it
   always did: a switch's landing belongs to `switchTo`, computed after the reset it owns. */
function boot(payload){
  D = payload;
  PG = Object.fromEntries(D.programs.map(p => [p.id, p]));
  SL = D.slices;
  /* A program carries its slices by id — the objects themselves are on the page once, under
     `slices`. Re-attaching them here is what lets every view above read `p.sl` directly. */
  D.programs.forEach(p => p.sl = (p.slices || []).map(i => SL[i]).filter(Boolean));
  PRD = {};
  Object.values(SL).forEach(s => s.prds.forEach(r => PRD[r.n] = { ...r, slice: s.id, program: s.program }));
  /* A PRD NO SLICE CLAIMS STILL HAS A PAGE (ENG-10704). Links to real PRDs — a capability's Ships in,
     an idea's proposal — opened "There is no PRD … it may have been removed" because only the PRDs a
     slice claims were indexed. `named` is the slice its own file names, which no register row holds. */
  OFF_BOARD = {};
  (D.offBoardPrds || []).forEach(o => { if (!PRD[o.n]){ OFF_BOARD[o.n] = o;
    PRD[o.n] = { n: o.n, title: o.title, status: o.status, slice: "", program: "", fleet: false, cmd: "", built: true, closed: "",
                 dep: o.dep || [], wave: o.wave, summary: o.summary || "" }; } });
  WAVE_G = null;
  FLEET = D.fleet || { wait: "", actor: "the automation", note: "" };
  /* A SENTENCE THAT OPENS ON THE ACTOR OPENS ON ITS CAPITAL (v0.5.94): "…'stub'. the fleet only
     implements" was `actor` in running-text case after a full stop. `board.py`'s `opener()` for the
     same vocabulary; derived here, never a second wire field. */
  FLEET = Object.assign({}, FLEET, { Actor: String(FLEET.actor || "").charAt(0).toUpperCase() + String(FLEET.actor || "").slice(1) });
  indexTerms();
  rzRebase();
  CORPUS = { state: "ready", detail: "", body: "" };
  /* The registers `routeOf` reads just moved, so a surface that keeps its own markup (an agent's
     thread) re-reads its ids against them. */
  refsChanged();
  if (!HELD) return false;
  enter(HOME);
  return true;
}

/* What a corpus view shows when there is no corpus payload to show.
   THREE STATES, NEVER ONE. "Fetching" and "the fetch failed" render the same blank page
   otherwise, and an operator debugging a blank page debugs the wrong thing.

   A HOST MAY REPLACE THE FAILED PAGE (ENG-16177). The deployed app's cold-install answers
   (`no-generation`, `no-corpus`) are the designed first-run state, not a fetch failure, and the
   host alone knows whether Set up is still incomplete — so it registers a note that returns
   markup for those, and leaves every other failure on this page. Returning a non-string (or
   nothing) keeps the failure title exactly as it always was. */
let CORPUS_NOTE = null;
function corpusNote(fn){ CORPUS_NOTE = fn || null; }

function corpusPlaceholder(){
  if (CORPUS.state === "loading"){
    return `<p class="empty-note" id="corpus-loading">Reading the board&hellip;</p>`;
  }
  if (CORPUS_NOTE){
    const said = CORPUS_NOTE(CORPUS);
    if (typeof said === "string" && said) return said;
  }
  return pageHead("The board could not be read",
      `This is a failure to FETCH the reading, not an empty corpus. The two look identical on a
       blank page, so this page says which it is.`) +
    `<div class="banner"><b>${esc(CORPUS.detail || "the request did not complete")}</b>
      ${CORPUS.body ? `<br><span class="mono">${esc(CORPUS.body)}</span>` : ""}</div>
    <p class="note">Fleet state is a separate question and is fetched separately &mdash; the
    <b>Fleet</b> tab still answers it when it is present.</p>`;
}

/* ── what a host page adds ───────────────────────────────────────────────── */

/* A route kind this package knows nothing about. `fleet` arrives this way. */
function register(views, onRoute){
  Object.assign(EXTRA, views || {});
  if (onRoute) ROUTED.push(onRoute);
}

/* Glossary sections the HOST defines. The deployed app contributes the vocabulary of the loop
   — box, lane, run, claim, lease, dispatch position, workstation session — because those are
   facts about a running fleet and this package is the record. Rows arrive in the corpus's own
   seven-field shape (`k`, `term`, `what`, `test`, `example`, `industry`, `where`, `sec`), so
   the view renders both halves with one function and there is no second layout to keep alike.

   A FUNCTION, called at index time: the host's rows come from a fetch that lands whenever it
   lands, and a stored array would be a snapshot of the moment before it arrived. */
function terms(fn){ TERMS_EXTRA = fn || null; indexTerms(); }

/* What the host says for a term's value — see `SAYS`. Registered once; hover text already on
   screen picks it up on its next render, which the host's own glossary fetch triggers. */
function says(fn){ SAYS = fn || null; }

/* What the host puts on a runnable row instead of the command text. Called for EVERY "Run this"
   affordance on every view — the action list, a slice's PRDs, a PRD page — with
   `{ cmd, built, id, kind, plain }`: the command, whether the tool exists, the row's entity and
   which register holds it, and the markup this file would have produced.

   Returning `null` keeps `plain` exactly as it is. That is the answer for a row the host cannot
   act on, and it is why registering this can never make a row LESS legible than it was. */
function runAction(fn){ RUN_ACTION = fn || null; }

/* What the host puts in charge of an authored program order. Called with the full list of
   PLACED program ids, top to bottom, and every program id the mode listed, and expected to return a promise — see `REORDER`'s own
   comment for the whole of the contract. Absent, `reorderToggle` renders nothing and the
   Programs list is exactly what it always was. */
function reorder(fn){ REORDER = fn || null; }

/* What the host puts in charge of saying what an act did — see `NOTIFY`. Absent, every result is
   said on the page, exactly as it always was. */
function notify(fn){ NOTIFY = fn || null; }

/* IS THE READER IN THE MIDDLE OF SOMETHING THIS FILE OWNS?
 *
 * ASKED BY A HOST THAT IS ABOUT TO REPLACE THE CORPUS UNDER THEM. The Plan tabs render from one
 * payload that `start` fetches once, and a live deployment now re-fetches it the moment a sync
 * advances the head — which is the right behaviour and would be intolerable in exactly one place:
 * Reorder mode, where the list the reader is dragging IS the list `boot` would replace. Dropping
 * a card into a list that changed under the pointer is worse than being one sync behind for as
 * long as somebody is holding a card.
 *
 * WHAT COUNTS IS NARROWER THAN "THE MODE IS OPEN" (ENG-10701, K-08). It used to be exactly that,
 * on every route — so a draft left open while the reader browsed froze every Plan page (a program
 * header stale after 45 s), and Cancel then left the list on the old order until the heartbeat,
 * 15–29 s. Now: a write in flight (`REORDER_BUSY` — a promise waiting to render into markup `boot`
 * would throw away), a card held or a press arming (`RZD`, `RZ_ARMED` — the list under a pointer),
 * or an UNSAVED draft while the reader is ON the list. A clean mode takes the new payload and
 * re-reads its draft from it (`rzRebase`); a draft on another page keeps its ids, and a newer order
 * that arrives meanwhile is named in the bar before Save is ever pressed. When none of these holds
 * any more the host hears it at once (`onIdle`), so a deferred reload is paid then and there. What
 * the host must NOT do is drop the update: `app.js` re-asks on idle and on its next frame.
 *
 * A FUNCTION AND NOT A FLAG the host reads, because the answer is a property of state this file
 * owns exclusively, and a boolean exported at boot would be a copy that is wrong a moment later.
 */
function busy(){
  return REORDER_BUSY !== "" || !!RZD || !!RZ_ARMED || (REORDER_MODE && rzDirty() && onBoard());
}
function onBoard(){ return routeParts(openRoute())[0] === "board"; }

/* THE HOST'S "NOTHING HELD ANY MORE" — called after every render that leaves `busy()` false, which
   covers Cancel, Escape, a landed save and walking off the list. `app.js` pays a deferred corpus
   read from it rather than waiting for the heartbeat. */
const IDLE_HOOKS = [];
function rzSettled(kind){
  rzAwayPaint(kind);
  if (!busy()) IDLE_HOOKS.forEach(fn => fn());
}

/* A NEW PAYLOAD UNDER AN OPEN REORDER MODE (K-08, K-01). Clean, the draft is the new order and the
   base its revision. Unsaved, the draft keeps its ids — less any program no longer in play — and
   a revision past the base is the conflict, said now rather than on Save. A save in flight is left
   alone: its own reload is what is landing. */
function rzRebase(){
  if (!REORDER_MODE || REORDER_BUSY) return;
  const now = orderRevision();
  if (!rzDirty()){
    const was = RZ_SAVED ? RZ_SAVED.slice() : [];
    RZ_DRAFT = reorderIds();
    RZ_SAVED = RZ_DRAFT.slice();
    if (now !== null && RZ_BASE !== null && now !== RZ_BASE && !reorderSame(was, RZ_SAVED)){
      REORDER_ANNOUNCE = `${rzChanged(D.rankOrder || {})}; this is it now.`;
    }
    RZ_BASE = now;
    RZ_CONFLICT = null;
    return;
  }
  const inPlay = new Set(activePrograms().map(p => p.id));
  RZ_DRAFT = RZ_DRAFT.filter(id => inPlay.has(id));
  RZ_SAVED = (RZ_SAVED || []).filter(id => inPlay.has(id));
  if (now !== null && RZ_BASE !== null && now !== RZ_BASE && (!RZ_CONFLICT || RZ_CONFLICT.revision !== now)){
    const o = D.rankOrder || {};
    RZ_CONFLICT = { revision: now, changedBy: o.changedBy || null, changedAt: o.changedAt || null,
                    order: reorderIds(), reload: null, early: true };
  }
}

/* AN UNSAVED ORDER IS NEVER LOST WITHOUT A WORD (ENG-10701, K-12). A reload or a closed tab asks
   first — the browser's own prompt, the only one it allows there. Walking to another page keeps
   the draft (it is still there on the way back), so that is not a loss to confirm; what a person
   meets instead is a line on every other page saying the order is not saved, with the way back. It
   lives outside `#main`, which a host's view repaints on its own schedule. */
function rzUnloadGuard(e){
  if (!REORDER_MODE || !rzDirty()) return false;
  if (e){
    if (typeof e.preventDefault === "function") e.preventDefault();
    e.returnValue = "";
  }
  return true;
}
window.addEventListener("beforeunload", rzUnloadGuard);
let RZ_AWAY = null;
function rzAwayPaint(kind){
  const show = REORDER_MODE && rzDirty() && kind !== "board";
  if (!show && !RZ_AWAY) return;
  if (!RZ_AWAY){
    RZ_AWAY = document.createElement("div");
    RZ_AWAY.className = "rz-away";
    RZ_AWAY.setAttribute("role", "status");
    document.body.appendChild(RZ_AWAY);
  }
  RZ_AWAY.hidden = !show;
  RZ_AWAY.innerHTML = show
    ? `Your new program order is not saved yet. ${link("board", "lnk", "Back to Reorder")}` : "";
}

/* Enter a route from scratch: the hash if it names a valid one, the home view otherwise.
 *
 * THE HASH IS NOT REWRITTEN WHILE THE PAYLOAD IS STILL ON THE WIRE. `valid` cannot judge an
 * entity route before the payload that defines its register has landed — `D` is null, so every
 * `program:`/`slice:`/`prd:` id is "invalid" — and the `replaceState` below used to overwrite
 * the entity deep link a cold load arrived with before anything could honour it. The
 * post-payload `enter` then re-resolved the `#board` THIS call had written rather than the link
 * the reader pasted, so `start`'s promised "re-resolves the hash against the index that is now
 * in hand" was denied by its own first step. So while there is no payload the asked route is
 * RENDERED — a loading state, which is what `render` draws for it — and the hash is left
 * exactly as it arrived; the register's arrival then validates the ORIGINAL hash against what is
 * now in hand. A route that was genuinely a typo is then SAID to be one, one payload later — the
 * missing page under the asked address (`viewMissing`), never a rewrite (ENG-10589).
 *
 * THE HOLD IS RECORDED, NOT ONLY TAKEN, and `boot` is why. The route sits in the hash while it
 * waits, which is enough for `start` — its own landing calls back here — and not enough for the
 * OTHER caller of `boot`: the deployed host re-installs the corpus on every sync the live feed
 * announces (`app.js`'s `rebootCorpus`) and then repaints the hash raw, trusting that whatever is
 * in it was judged when it was written. Inside the cold-load window nothing has judged it, so a
 * re-install that landed there — a sync moving the head while a slow first read was on the wire,
 * measured in a browser — put `viewSlice` in front of an id the payload does not hold. Two
 * outcomes, both wrong: the painter threw and the page stayed on "Reading the board…" with the
 * payload in hand, and every later raw repaint threw again. So `HELD` says that the route on
 * screen still owes a judgement, and `boot` settles it whichever payload arrives first.
 *
 * TWO REGISTERS ARRIVE LATE, NOT ONE. The corpus payload defines every entity id but the
 * knowledge ones; those are the index's (`kBoot`), a separate read that lands whenever it lands,
 * and a `knowledge:<kind>:<id>` link judged before it did was bounced for an id the index was
 * about to confirm. `unjudged` names both waits; the index's own arrival re-enters exactly as the
 * payload's does. */
let HELD = false;

/* CAN THIS ROUTE BE JUDGED YET? No route can be without the payload; a knowledge entity also
   needs the index, and only while that is genuinely on the wire — an index that failed, or a
   page with no server to read one from, answers now and gets `valid`'s verdict now. */
function unjudged(r){
  if (D === null) return true;
  const [k, a] = routeParts(r);
  return k === "knowledge" && !!a && kIndexState() === "loading";
}

function enter(home){
  const asked = location.hash.slice(1) || home || "board";
  if (unjudged(asked)){
    HELD = true;
    render(asked);
    return asked;
  }
  HELD = false;
  /* THE ASKED ROUTE IS THE ROUTE (ENG-10589). An id the corpus does not hold renders `viewMissing`
     under the address the reader arrived at; the entry is still re-addressed so it carries the
     repository it was judged against (`urlFor`), which is what a reload needs. */
  history.replaceState({ r: asked }, "", urlFor(asked));
  render(asked);
  return asked;
}

/* THE SEAM. `load` is a function returning a promise of the board payload:
   `() => Promise.resolve(baked)` in the standalone file, `key => fetch("/api/board?repo=" + key)`
   in the deployed app — it is handed the repository key this page has settled on, `""` for the
   primary, and the standalone file has no reason to look at it. Nothing else differs between the
   two pages. */
function start(opts){
  const o = opts || {};
  /* Host capabilities, every one of them optional and every one degrading to something honest.
     `loadBody` fetches one agent's markdown and `loadDoc` one document it cites; without either
     the page names the file on disk. `action` turns a missing slot into whatever this host can
     actually do about it; without it the page says what to write and leaves the doing to the
     reader. `corpora`/`repoBoard`/`switchRepo` are the multi-repository trio — without them
     this file holds exactly one corpus, which is what the standalone page IS. Nothing is faked. */
  BODY_LOADER = o.loadBody || null;
  DOC_LOADER = o.loadDoc || null;
  ACTION = o.action || null;
  /* THE CORPUS PAIR, and they are optional exactly like the six above. Without them this file
     holds the index and draws no link into it — which is what the standalone page IS, and is the
     honest reading rather than a link to a page nothing can fill. */
  KNOWLEDGE_LOADER = o.loadKnowledge || null;
  /* THE PARTS TABLE'S WRITES, optional like the rest: `{ act(part, action), asks(key), answer(setId, answers) }`. Without them the table
     is a reading and draws no Describe, Stop, Continue or answer control. */
  K_PART = o.part || null;
  PROSE_LOADER = o.loadProse || null;
  CORPORA_LOADER = o.corpora || null;
  REPO_BOARD_LOADER = o.repoBoard || null;
  SWITCH_REPO = o.switchRepo || null;
  register(o.views, o.onRoute);
  initNav();
  const home = HOME = o.home || "board";
  CORPUS = { state: "loading", detail: "", body: "" };
  /* READ BEFORE THE FIRST `enter`, WHICH USED TO REWRITE THE ADDRESS. `enter` re-addresses the
     entry to the route it settled on, and until the list has landed that address carries no
     query — so a `?repo=` a shared link arrived with was gone from the URL before anything had
     looked at it, and the page landed on storage's answer under a bookmark that named another
     repository. Measured under the harness. The first `enter` now
     holds an unjudged route without touching the address, so the order is no longer what saves
     the query; it stays because the read costs nothing and the property must not depend on it. */
  const asked = CORPORA_LOADER ? askedRepo() : null;
  enter(home);
  /* WHICH REPOSITORIES EXIST IS ASKED BESIDE THE BOARD, never behind it. The board is the page;
     this is the list of pages, and a deployment that cannot answer it must still be readable as
     the one repository it already handed over — so a failure here is recorded and shown on the
     Agents tab rather than raised. Its answer arrives whenever it arrives, and the two routes it
     changes re-render when it does. */
  /* THE CORPUS INDEX, ASKED ONCE AND BEFORE ANY PAGE NEEDS IT. Every page on this board can
     print an id, so the answer to "which register holds this one" cannot wait for the tab that
     is about it — which is exactly why `/api/corpora` is asked here too. `""` is the collection
     itself: the kinds, their counts and their ids.

     IT RE-ENTERS RATHER THAN RE-RENDERS. Arriving late changes what `valid()` accepts, so a
     reader who deep-linked to an entity landed on the home view while the answer was on the
     wire; `enter` re-resolves the hash against the index that is now in hand — and a route
     still HELD for this index is re-entered even when the index carries nothing, because an
     empty index IS the verdict on a knowledge link, not a reason to keep it waiting. Failure is
     RECORDED and shown on the tab rather than raised — the board is the page, and a deployment
     that cannot answer this must still be readable as the plan it already handed over. */
  const indexed = () => { if (HELD || KKINDS.length) enter(HOME); };
  const listed = CORPORA_LOADER
    ? CORPORA_LOADER().then(
        payload => { CORPORA = payload || null; CORPORA_ERR = null; },
        err => { CORPORA_ERR = (err && err.message) ? String(err.message) : String(err); })
    : Promise.resolve();
  /* `load` IS HANDED THE REPOSITORY IT IS READING. The standalone page ignores it; the deployed
     app spells it into `?repo=`. Asked for AFTER the repository is settled, below, so the first
     board a reader sees is the one their URL or their storage named. */
  const load = () => Promise.resolve()
    .then(() => (o.load ? o.load(REPO) : Promise.reject(new Error("no payload source was given"))))
    /* `boot` enters the held route itself and says so; this enters only when it found none to
       settle — the host's re-read got there first — and the hash it re-judges is then one that
       has already been corrected, against the newer payload. */
    .then(payload => { if (!boot(payload)) enter(home); return { ok: true }; })
    .catch(err => {
      CORPUS = {
        state: "failed",
        detail: (err && err.message) ? String(err.message) : String(err),
        body: (err && err.body) ? String(err.body) : "",
        /* THE REFUSAL CODE, when the host's fetch carried one (ENG-16177): `no-generation` and
           `no-corpus` are the designed cold states of a fresh install, and the host's corpus note
           needs the code — not only the sentence — to tell them from a real fetch failure. */
        code: (err && err.code) ? String(err.code) : "",
      };
      enter(home);
      return { ok: false, error: err };
    });
  /* WHICH REPOSITORY TO READ FIRST — see "where the choice lives" for the order. When nothing
     was asked for, the primary is the answer and the answer needs no list: the board and the
     list are read side by side exactly as they always were, and the list, when it lands, only
     gives the primary its name. When a repository WAS asked for — `?repo=` on the URL, or a
     stored choice — the list is read first, because the name has to be checked against what is
     served before a board is fetched for it: a name nothing serves falls to the primary, out
     loud, and the corpus index (`kBoot`) is read for the repository that was settled on rather
     than for the primary and again a moment later. One round trip, and only on the path where
     a wrong guess would cost a refused fetch and a second one anyway. */
  if (asked === null){
    kBoot(indexed);
    listed.then(() => settleRepo(null));
    return load();
  }
  return listed.then(() => {
    settleRepo(asked);
    kBoot(indexed);
    return load();
  });
}

/* THE LIST HAS LANDED; WHAT DOES THE PAGE HOLD NOW? Three things are settled at once, and they
   are settled here rather than in `start`'s two branches so that they cannot come to differ.

   THE ASK IS HONOURED OR REFUSED BY NAME. A name the list carries, for a corpus that has synced,
   becomes `REPO`. A name it does not carry — a lane this deployment does not serve, a typo, a
   corpus that was removed since the reader last chose it — and a name it carries for a corpus
   nothing has ever synced both fall to the primary, and the refusal is recorded so the host can
   say which name was refused and why. A list that could not be read cannot refuse anything, so
   the ask is taken on trust and the board read is what answers it: a refused board renders the
   server's own sentence, which is the most honest thing left to show.

   THE PRIMARY GETS ITS NAME. `REPO` was `""` for the primary until now; where a second corpus
   makes a name necessary it becomes the lane the primary answers for, in place, with no second
   fetch — the payload in hand is the same corpus under a new spelling.

   THE READER'S SORT AND FILTER FOLLOW. They were read at load under the primary's key; a page
   that settled on another repository re-reads them under that repository's. The primary's are
   left alone, because `prefKey` gives the primary the same key under either spelling — which is
   the whole reason `isPrimary` exists. Then the choice is written where it lives, the entry on
   screen is re-addressed, and every painter that draws this state is told. */
function settleRepo(asked){
  if (asked){
    const c = corpusFor(asked);
    /* A FORMER NAME LANDS IN SILENCE, on the lane it became; `syncUrl` below corrects the address
       to the name that lane has today. */
    if (c && c.synced && formerOf(c, asked)) renamedFrom(asked);
    if (c && c.synced) REPO = keyOf(c) || "";
    else if (CORPORA === null) REPO = asked;
    else {
      REPO_REFUSED = { name: asked, why: c ? "never synced" : "not served" };
      /* A REFUSED NAME IS NOT KEPT (ENG-10706): on one corpus nothing ever rewrote `zb.repo`, so a
         stale choice was asked for, and refused in silence, on every load. */
      if (store.get("zb.repo", "") === asked) try { localStorage.removeItem("zb.repo"); } catch { /* storage unavailable: nothing was kept */ };
    }
  }
  if (REPO === "") REPO = primaryKey();
  if (!isPrimary(REPO)){
    sortKey = store.get(prefKey("zb.sort"), "priority");
    filters = new Set((store.get(prefKey("zb.filters"), "hideComplete") || "").split(",").filter(Boolean));
    /* The narrowing re-seeds OFF for the repository being moved to (PRD 0839). */
    mineOn = false;
  }
  persistRepo();
  if (manyRepos()) syncUrl();
  if (onAgentsList() || ["repo", "command", "slot", "doc"].includes(routeParts(openRoute())[0])) render(openRoute());
  notifyRepo();
}

/* `esc`, `mdown`, `rankChip` and `go` are exported because a host view needs the SAME escaper,
   the SAME reading of the corpus's marks, the SAME explanation of an inherited rank and the
   SAME navigation as every row on this page. A second escaper is a second set of escaping
   bugs, and a second rank chip is two pages disagreeing about what "inherited from SL-168"
   means. `pageHead` is there for the same reason: a host page that set the document title and
   drew its lede its own way would be a second implementation of one head.

   `mdown` is on this list for a concrete reason and not for symmetry: the deployed app renders
   `/api/fleet`'s ineligibility sentences, which are Python docstrings and carry exactly the
   same two marks as the glossary rows this file renders — `**Not a fault**`, `` `has_slot` ``.
   A second inline renderer there would be a second place to get escaping wrong.

   `badges` and `paintBadges` are the nav's third injection seam (`reorder`, `runAction`); see
   the comment above `BADGES_EXTRA`. `actionTotals` is exported so a host can fold the Programs
   tab's OWN needs-you count into that same object without reading `D` directly — the corpus
   payload's shape is this file's to know, not the host's to reach into. */
/* `repo()` IS READ, NEVER SET. A host that has just switched repository knows which one it asked
   for; what it cannot know is whether this file has finished moving to it — the reset and the
   route change happen after the host's promise resolves — and a host that stamped its own answer
   in would be a second opinion about the page's subject. `repoState`, `switchTo` and `onRepo`
   are the masthead selector's three needs and nothing more: everything it paints, the one act it
   performs, and the moment to repaint. The state itself stays here, so the selector in the mast
   and the dropdown in the crumb row are two paintings of one fact. */
/* THE FILTER BAR'S LISTENERS (`filterBar`), delegated from the document like every other control
   here, and registered after the board's own so each of those keeps its place in the file. */
document.addEventListener("click", e => {
  if (!e.target.closest) return;
  let el;
  /* THE RESPONSIBLE-PEOPLE CONTROL AND ITS PICKER (PRD 0839), checked before the filter bar's
     listeners because the row's chip and the dialog's buttons are their own controls. */
  if ((el = e.target.closest("[data-own]"))){ e.preventDefault(); return ownOpen(el.getAttribute("data-own")); }
  if ((el = fbAt(e, "data-fb-open"))){
    e.preventDefault();
    const [id, from] = fbParts(el);
    if (FB_OPEN && FB_OPEN.id === id && FB_OPEN.from === from) return fbClose(true);
    return fbOpenMenu(id, from, from === "sort" ? "__sort" : "");
  }
  if ((el = fbAt(e, "data-fb-chip"))){
    e.preventDefault();
    const [id, fid] = fbParts(el);
    const spec = FB[id];
    /* MY PROGRAMS IS ITS OWN SINGLE CONTROL (PRD 0839): the chip toggles the narrowing directly —
       it has no values to choose from — while every other field's chip opens its menu. The chip
       is drawn only while it narrows, so one click on it shows every program again. */
    if (spec && fid === MINE && fbField(spec, MINE)){
      return spec.on.set(MINE, mineOn ? [] : ["on"]);
    }
    const f = FB[id] && fbField(FB[id], fid);
    return fbOpenMenu(id, fid === "__sort" ? "sort" : "filter", f && f.flag ? "" : fid);
  }
  if ((el = fbAt(e, "data-fb-at"))){
    e.preventDefault();
    const [id, fid] = fbParts(el);
    if (!FB_OPEN || FB_OPEN.id !== id) return;
    FB_OPEN.at = fid || "";
    FB_OPEN.q = "";
    fbPaint(FB[id], null);
    const first = main && main.querySelector && main.querySelector(`[data-fb-mi="${id}"]`);
    if (first && first.focus) first.focus({ preventScroll: true });
    return;
  }
  if ((el = fbAt(e, "data-fb-tog"))){
    e.preventDefault();
    const [id, fid, v] = fbParts(el);
    const spec = FB[id], f = spec && fbField(spec, fid);
    if (!f) return;
    /* THE CHANGE IS THE PAGE'S — a navigation on Queue and Runs, a repaint on Fleet — and the menu
       stays open across it, at the same level, so a second value is one more click. */
    return spec.on.set(fid, fbToggle(f, v));
  }
  if ((el = fbAt(e, "data-fb-sort"))){
    e.preventDefault();
    const [id, k] = fbParts(el);
    const spec = FB[id];
    if (!spec) return;
    const was = FB_OPEN;
    FB_OPEN = null;
    spec.on.sort(k);
    if (was && main){
      const back = main.querySelector(`[data-keep="fb:${id}:${was.from}"]`);
      if (back && back.focus) back.focus({ preventScroll: true });
    }
    return;
  }
  if ((el = fbAt(e, "data-fb-rm"))){
    e.preventDefault();
    const [id, fid] = fbParts(el);
    const spec = FB[id];
    if (!spec) return;
    if (fid === "__sort") return spec.on.sort(String(spec.sort.def || ""));
    if (fid === "__search") return spec.on.search("");
    const f = fbField(spec, fid);
    if (f) return spec.on.set(fid, fbHasDef(f) ? f.def.map(String) : []);
    return;
  }
  if ((el = fbAt(e, "data-fb-clear"))){
    e.preventDefault();
    const [id] = fbParts(el);
    /* CLEAR CLEARS FILTERS AND LEAVES THE VIEW ALONE — the page's `clear` keeps its tabs, as the
       Stats page always kept its window. */
    if (FB[id]) FB[id].on.clear();
    return;
  }
  if ((el = fbAt(e, "data-fb-close"))){
    e.preventDefault();
    return fbClose(true);
  }
  /* A CLICK ANYWHERE ELSE SHUTS AN OPEN MENU, as the Programs dropdowns do. */
  if (FB_OPEN && !e.target.closest("[data-fb-m]")) fbClose(false);
});

document.addEventListener("keydown", e => {
  if (!e.target.closest) return;
  let el;
  /* THE SEARCH COMMITS ON ENTER unless the page filters its own rows (`live`), for the Runs and
     Queue tabs' reason: each commit there is a navigation and a server read. */
  if ((el = fbAt(e, "data-fb-search"))){
    const [id] = fbParts(el);
    const spec = FB[id];
    if (e.key === "Enter" && spec){ e.preventDefault(); spec.on.search(String(el.value || "").trim()); }
    return;
  }
  if ((el = fbAt(e, "data-fb-find"))){
    const [id] = fbParts(el);
    if (e.key === "ArrowDown"){ e.preventDefault(); return fbStep(id, null, "ArrowDown"); }
    if (e.key === "Enter"){
      e.preventDefault();
      const first = main && main.querySelector && main.querySelector(`[data-fb-mi="${id}"]`);
      if (first && first.click) first.click();
      return;
    }
    if (e.key === "Escape"){ e.preventDefault(); return fbClose(true); }
    return;
  }
  if ((el = fbAt(e, "data-fb-mi"))){
    const [id] = fbParts(el);
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)){ e.preventDefault(); return fbStep(id, el, e.key); }
    if (e.key === "ArrowLeft" && FB_OPEN && FB_OPEN.at && FB_OPEN.at !== "__sort"){
      e.preventDefault();
      const fid = FB_OPEN.at;
      FB_OPEN.at = "";
      return fbPaint(FB[id], `fb:${id}:at:${fbEnc(fid)}`);
    }
    if (e.key === "Escape"){ e.preventDefault(); return fbClose(true); }
    return;
  }
  if (e.key === "Escape" && FB_OPEN && fbOpenOf(FB_OPEN.id)){ e.preventDefault(); fbClose(true); }
});

document.addEventListener("input", e => {
  if (!e.target.closest) return;
  let el;
  if ((el = fbAt(e, "data-fb-find"))){
    const [id] = fbParts(el);
    if (!FB_OPEN || FB_OPEN.id !== id) return;
    const at = el.selectionStart;
    FB_OPEN.q = String(el.value || "");
    FB_OPEN.at = "";
    fbPaint(FB[id], `fb:${id}:find`);
    const again = main && main.querySelector && main.querySelector(`[data-fb-find="${id}"]`);
    if (again && at != null && again.setSelectionRange) again.setSelectionRange(at, at);
    return;
  }
  if ((el = fbAt(e, "data-fb-search"))){
    const [id] = fbParts(el);
    const spec = FB[id];
    if (!spec || !spec.search) return;
    const v = String(el.value || "");
    /* A LIVE FIELD HANDS OVER WHAT WAS TYPED, UNTRIMMED — a space between two words is still being
       typed — and gets its caret back after the page repaints under it. A CLEARED FIELD COMMITS ON
       THE SPOT — there is no Enter in that gesture. */
    if (spec.search.live){
      const at = el.selectionStart;
      spec.on.search(v);
      const again = main && main.querySelector && main.querySelector(`[data-fb-search="${id}"]`);
      if (again && again !== el && again.focus){
        again.focus({ preventScroll: true });
        if (at != null && again.setSelectionRange) again.setSelectionRange(at, at);
      }
    } else if (v === "" && spec.search.value) spec.on.search("");
  }
});

/* WHERE A PROGRAM IS IN ITS LIFE, by id (`p.phase`: shaping, building, closing, proven, waived, closed, withdrawn); "" for an
     id the plan does not hold. Read-only; the New UI's Cockpit draws a program row's step strip from it. */
const programPhase = (id) => { const p = (D && D.programs || []).find(x => x && x.id === id); return p ? String(p.phase || (p.closed ? "closed" : "")) : ""; };

/* `sheet` IS `sheetMode`, HANDED OUT SO THE HOST NEVER ASKS THE QUESTION A SECOND WAY. The
   host places its alarm panel against its trigger with inline styles, and an inline style beats
   the stylesheet's bottom-sheet rules at the phone breakpoint — so the host has to know which
   layout is live before it writes them, and the only honest answer is the one this file already
   reads off `--sheet`. A `matchMedia` over there would be the second copy of the breakpoint the
   comment above `sheetMode` exists to refuse. */
  return { start, register, runAction, reorder, asks, drive, rowMarks, waiting, waitingTotal, parked, live, prereqs, terms, says, term, pageHead, boot, render, embed, alias, unknown, missingBack, known, go, enter,
           /* WHAT A HOST SAYS WHEN THE CORPUS FETCH FAILS (ENG-16177) — see `corpusNote`. */
           corpusNote, prdPage,
           /* A WORD'S DEFINITION AS HOVER TEXT ON A HOST'S OWN ELEMENT — see `defined`. */
           defined,
           programPhase,
           /* THE ONE LIST OF KNOWLEDGE KINDS, and a way into one kind's row on the Knowledge page —
              what the deployed app's Build-the-knowledge page reads, so it holds no copy. */
           knowledgeGuide, kindLink,
           /* HOW A PERSON TYPES AN AGENT IN THIS REPOSITORY — see `invocation`. */
           invocation,
          /* THE REPAINT THAT KEEPS THE READER'S PLACE: a host view that re-reads
             itself on a timer patches `#main` through this, never through `innerHTML`. */
          patch,
          /* THE ONE FILTER BAR every list page declares its fields to, and the empty state that
             names what it is hiding — see `filterBar`. */
          filterBar, filterEmpty, viewTabs, kWord,
          /* THE HOST'S OWN REGISTERS FOR AN ID IN PROSE, and the signal that any register moved — see
             `setHostRefs`. */
          setHostRefs, onRefs, refsChanged,
          esc, mdown, mdBlock, mdText, mdTrim, descNote, rankChip, badge, routeOf, badges, paintBadges, actionTotals, busy,
          /* THE PERSON'S MOVES ACROSS THE PLAN, AND THE CONTROL THAT MAKES ONE — "Needs you" lists the
             first and draws the second, the row's own affordance, never a copy of it. */
          personMoves, runbox, programBar, programClosed,
          /* QUESTION FIRST (ENG-11733): the host's idea page folds its own sections the same way
             this file folds a program's — one helper, both sides. */
          asksFirst, pinFirst,
          stateWord, notify,
          /* THE CHAIN A BUILD-STEP NODE LIGHTS, as ids — what the hover walks, readable without a
             pointer (and by the render tests, which have no geometry to hover with). */
          chainOf,
          /* THE ONE STEPPER the bug, idea and program pages share — see `stepper`. */
          stepper,
          /* THE PROGRAM LIFECYCLE MODEL behind its stepper — see `programLifecycle`. */
          programLifecycle,
          /* THE PROGRAM PAGE'S OWN PIECES, for the render tests: the step strip, the held-up cards, the priority chip and the day. */
          /* WHAT AN ITEM WAITS ON AND UNBLOCKS, AND A SLICE'S PATH TO DONE — see `tuDepsBlock` (the approved dependencies mockup). */
          tuDepsBlock, tuSlicePath, depSlicePath: dpSlicePathIds,
          askFrame, tuHeader, tuStepMarkup, tuProgramSteps, tuSliceSteps, tuHoldCards, tuHolds, tuHoldNote, tuProofSaid, tuProofLinks, tuPrioChip, tuDay, drillShort, sliceKindWords, tuPrdTable, tuWhereItStands, tuProgramStands, tuSliceStands,
          link, href: (r, repo) => urlFor(r, repo), agentRoute,
          /* THE DETAIL PAGES' SHARED PARTS — see the section above `tuSlot`. */
          tuTabBar, tuDepsToggle, tuDepHint, tuTabs, tuTabOf, tuPlainWords, tuFactsRow, tuRelRows, tuJumpRail, tuDocFrame, tuMetaLine, tuIdMark, tuLinkIds, tuRefLink, tuAddAssignee,
          /* THE LIST ROWS' GLYPHS AND THE MARK THAT DRAWS ONE — see `ICON`. */
          icons: ICON, mark, avatar: ownAvatar,
          /* THE ONE PEOPLE MODAL — see `peopleModal`. */
          peopleModal, peopleModalClose, peopleModalHtml, peopleModalModel, peopleModalNext, peopleModalDiff,
         /* THE KNOWLEDGE PAGE'S READINESS READ AGAIN, called by the host when the dispatch or inbox topic moved. */
         knowledgeReload: kReadyReload,
         main: () => main, loaded: () => D !== null, corpus: () => CORPUS, repo: () => REPO, sheet: sheetMode,
         /* WHAT THE SHARED POPOVER IS SAYING, if anything (ENG-12873): the one observable a tap
            test has that the popover DID open, since `#tip` lives on `body` outside `#main`. */
         tip: () => ({ open: !tip.hidden, text: String(tip.textContent || "") }),
         /* IS THIS ROUTE JUDGED ABSENT (ENG-10589) — so a host's per-page reads (a card slot, a
            drive, a shape document) can stand down for an id there is no page for. */
         missing,
         /* WHAT A HOST SAYS ON A MISSING ENTITY PAGE (ENG-10707, I-09) — see `missingNote`. */
         missingNote,
         repoState, goIn, switchTo: key => switchTo(key), onRepo: fn => { if (fn) REPO_HOOKS.push(fn); },
         /* ENG-10701, K-08: told when nothing this file owns holds a corpus reload back any more;
            RK-07: handed the order's head when a reload is held back, so a draft hears of a newer
            order; RK-06: told who is reading, so their own other tab is "you". */
         onIdle: fn => { if (fn) IDLE_HOOKS.push(fn); }, orderHead, viewer, owners, people,
         /* THE DELIVERY RANGE: the host hands `/api/delivery`'s document, or `null` — see the block
            between the two marker lines. */
         estimates,
         /* THE DELIVERY SEAM: the host's one reading per program — see `delivery`. Last, so the
            publish anchors other suites splice at stay as they were. */
         delivery,
         /* THE NEW PAGES' HOST SEAM (`tuHost`): the Delivery box, the log and the activity rows the new program
            page draws from the host's drive document. Last, for the same reason `delivery` is. */
         tuHost };
})();

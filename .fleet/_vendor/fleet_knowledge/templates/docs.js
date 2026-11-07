/* The Docs page — one product-docs markdown file, drawn as a designed page (`/api/docs/page`).
 *
 * THE CONTRACT IS `productdocs/README.md`, and this file implements exactly what it says. A page is
 * markdown plus a CLOSED catalogue of directive blocks; the parser below cuts the blocks out, every
 * block becomes one component, and every run of plain markdown between them goes through the app's
 * ONE markdown renderer, `Board.mdBlock`. There is no second renderer here, and that is not thrift:
 * two renderers disagree about the same paragraph the day either changes, and the reader sees a
 * bold on one page that is two asterisks on the next. Agents read the same files as plain markdown
 * (`docsmd.render_agent`), so a page is written once and has two readers.
 *
 * A HOST PAGE MODULE, KEEPING `quality.js`'S SEAM: this file spells no URL and reads nothing on its
 * own. `render(el, page, ctx)` is handed the `/api/docs/page` payload and a `ctx` that answers every
 * question the page asks — a live card (`ctx.live`), a term (`ctx.term`), another page
 * (`ctx.page`), where an app route or a docs page lives (`ctx.href`, `ctx.docHref`), the reader's
 * planning mode (`ctx.mode`), a command (`ctx.command`), the index (`ctx.index`) and a live part
 * of the app it draws itself (`ctx.embed`). The host owns
 * the network; this file owns the page.
 *
 * AN INVALID BLOCK IS A VISIBLE ERROR AND THE PAGE STILL RENDERS. The CI check refuses such a file
 * before it ships, so a reader should never see one; a writer previewing a draft must, in place,
 * with the line it came from. A page that went blank over one typo would hide the other forty
 * blocks that were fine.
 *
 * LIVE CARDS DRAW A SKELETON FIRST, THEN FILL. `ctx.live` is a read, and a page that waited for
 * every card before drawing anything would hold the whole article on its slowest card. The
 * skeleton keeps the card's height so the text under it does not jump when it fills; a card that
 * comes back `null` says so in words ("not found in this repository's knowledge") rather than
 * vanishing, because a docs page that silently drops its example teaches the reader nothing.
 *
 * A TERM IS A TOGGLETIP, NOT A TOOLTIP AND NOT A LINK. It is a real `<button>` (keyboard-reachable
 * for free), opens on click or Enter, closes on Escape with focus back on the word, and holds plain
 * text only — a link inside a bubble that closes when focus moves is a link no keyboard reader can
 * reach. Terms are UI only: the page ends with nothing extra, unlike the agent rendering, which
 * appends the definitions it used.
 *
 * EVERY CLASS IS `dx-`-PREFIXED and styled by `docs.css`, which composes `fleet.css` tokens and
 * declares none of its own. `md-*` classes inside a markdown run are `board.js`'s, styled by the
 * shared sheet, and are left exactly as `mdBlock` wrote them.
 */
(function(){
"use strict";

var D = window.FleetDocs || (window.FleetDocs = {});
D.screens = D.screens || {};
D.figures = D.figures || {};

/* -- the catalogue, read off the contract's table ------------------------------------------- */

/* `c`: a container (`:::name` … `:::`) rather than a leaf (`::name`). `attrs`: every attribute the
   block accepts and how — "req" must carry a value, "opt" may, "flag" is bare. `one`: exactly one
   of these must be present. `label`: a leaf that carries `[Label]`. */
var BLOCKS = {
  lede:    { c: true,  attrs: {} },
  steps:   { c: true,  attrs: {} },
  callout: { c: true,  attrs: { kind: "req", figure: "opt" } },
  mode:    { c: true,  attrs: { programs: "flag", areas: "flag" }, one: ["programs", "areas"] },
  compare: { c: true,  attrs: {} },
  diagram: { c: false, attrs: { name: "req", slice: "opt" } },
  live:    { c: false, attrs: { slice: "opt", area: "opt", prd: "opt", program: "opt", title: "req", quote: "opt" }, one: ["slice", "area", "prd", "program"] },
  screen:  { c: false, attrs: { route: "req", focus: "opt", pins: "opt" } },
  action:  { c: false, attrs: { route: "req" }, label: true },
  cards:   { c: false, attrs: { links: "req" } },
  command: { c: false, attrs: { name: "req" } },
  figure:  { c: false, attrs: { name: "req", alt: "req" } },
  ideas:   { c: true,  attrs: {} },
  path:    { c: false, attrs: { links: "req" } },
  pages:   { c: false, attrs: { links: "req" } },
  embed:   { c: false, attrs: { name: "req" } }
};
/* `::embed{name}`: a live part of the app, drawn by the host (`ctx.embed(name)`, a DOM node or an
   HTML string) into a slot this file leaves for it. Closed, like the diagrams. */
var EMBEDS = { "work-line": 1 };
var CALLOUTS = { why: "Why", tip: "Tip", careful: "Careful" };
var WHO = { you: "You", fleet: "Fleet", nobody: "Nobody" };
var DIAGRAMS = { "work-line": 1, "three-questions": 1, "knowledge-folder": 1, "knowledge-map": 1, "fleet-map": 1 };
var MODE_WORD = { programs: "Planning by programs", areas: "Planning by features" };
var FOR_WORD = { owner: "owners", developer: "developers", admin: "admins", everyone: "everyone" };
var KIND_WORD = { start: "Start here", concept: "Concept", guide: "Guide", troubleshooting: "Troubleshooting", reference: "Reference", job: "Job" };
var LIVE_NOUN = { slice: "slice", area: "feature", prd: "PRD", program: "program" };

/* -- small helpers -------------------------------------------------------------------------- */

function esc(s){
  return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function board(){ return window.Board || null; }
function ctxCall(ctx, name){
  var fn = ctx && ctx[name];
  if (typeof fn !== "function") return null;
  try { return fn.apply(ctx, Array.prototype.slice.call(arguments, 2)); } catch (e) { return null; }
}
function errHtml(message, line){
  return '<div class="dx-err" role="note"><b>This part of the page cannot be shown.</b> ' + esc(message) +
    (line ? ' <span class="dx-err-at">line ' + esc(line) + '</span>' : "") + "</div>";
}
/* A HEADING'S ANCHOR, derived from its text and nothing else — the rail and the heading compute
   it from the same string, so they cannot disagree. `dx-` prefixed: a docs heading must never
   collide with an id the shell owns. */
function slug(text){
  var flat = String(text || "").toLowerCase()
    .replace(/:(?:term|kbd)\[([^\]]*)\]/g, "$1")
    .replace(/[`*_]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60).replace(/-+$/, "");
  return "dx-h-" + (flat || "x");
}
function plainText(text){
  return String(text || "").replace(/:(?:term|kbd)\[([^\]]*)\]/g, "$1")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/[`*]/g, "");
}

/* -- the parser ----------------------------------------------------------------------------- */

/* `key="value"`, `key=value` or a bare `flag`, separated by whitespace. Anything else in the braces
   is an error rather than a guess: a half-read attribute list is how a `route` silently becomes
   the wrong route. */
function readAttrs(src){
  var out = {}, rest = String(src || "").trim(), m;
  var re = /^([A-Za-z][\w-]*)(?:=(?:"([^"]*)"|([^\s"]+)))?(?:\s+|$)/;
  while (rest){
    m = re.exec(rest);
    if (!m) return { error: "cannot read the attributes {" + src + "}" };
    if (Object.prototype.hasOwnProperty.call(out, m[1])) return { error: "attribute " + m[1] + " is given twice" };
    out[m[1]] = m[2] !== undefined ? m[2] : m[3] !== undefined ? m[3] : true;
    rest = rest.slice(m[0].length);
  }
  return { attrs: out };
}

/* Every rule the contract's table states about one block's attributes. Returns a message, or "". */
function checkAttrs(name, attrs, label){
  var spec = BLOCKS[name], k;
  for (k in attrs){
    if (!Object.prototype.hasOwnProperty.call(spec.attrs, k)) return (spec.c ? ":::" : "::") + name + " has no attribute " + k;
    if (spec.attrs[k] === "flag" && attrs[k] !== true) return k + " is a bare flag on :::" + name + ", not " + k + '="…"';
    if (spec.attrs[k] !== "flag" && (attrs[k] === true || attrs[k] === "")) return k + " on " + (spec.c ? ":::" : "::") + name + " needs a value";
  }
  for (k in spec.attrs){
    if (spec.attrs[k] === "req" && !Object.prototype.hasOwnProperty.call(attrs, k)) return (spec.c ? ":::" : "::") + name + " needs " + k + '="…"';
  }
  if (spec.one){
    var given = spec.one.filter(function(x){ return Object.prototype.hasOwnProperty.call(attrs, x); });
    if (given.length !== 1) return (spec.c ? ":::" : "::") + name + " takes exactly one of " + spec.one.join(", ");
  }
  if (spec.label && !String(label || "").trim()) return "::" + name + " needs a [Label]";
  if (!spec.label && label !== undefined) return "::" + name + " takes no [label]";
  if (name === "callout" && !CALLOUTS[attrs.kind]) return 'callout kind must be why, tip or careful, not "' + attrs.kind + '"';
  if (name === "diagram"){
    if (!DIAGRAMS[attrs.name]) return 'no diagram is called "' + attrs.name + '"';
    if (attrs.name === "three-questions" && !attrs.slice) return 'the three-questions diagram needs slice="SL-…"';
    if (attrs.name !== "three-questions" && attrs.slice) return "only the three-questions diagram takes a slice";
  }
  if (name === "screen" && !D.screens[attrs.route]) return 'there is no screen for the route "' + attrs.route + '"';
  if (name === "screen" && attrs.pins){
    var known = D.screens[attrs.route].anchors || [];
    var bad = String(attrs.pins).split(",").map(function(x){ return x.trim(); }).filter(function(x){ return known.indexOf(x) < 0; });
    if (bad.length) return "the " + attrs.route + " screen has no anchor " + bad.join(", ") + " (it has " + known.join(", ") + ")";
  }
  if (name === "figure" && !D.figures[attrs.name]) return 'no figure is registered as "' + attrs.name + '" in docs-figures.js';
  if (name === "embed" && !EMBEDS[attrs.name]) return 'no embed is called "' + attrs.name + '"';
  return "";
}

var RE_OPEN = /^:::([A-Za-z][\w-]*)(?:\{(.*)\})?\s*$/;
var RE_LEAF = /^::([A-Za-z][\w-]*)(?:\[([^\]]*)\])?(?:\{(.*)\})?\s*$/;
var RE_FENCE = /^\s*(```+|~~~+)/;
/* A TAG IS A NAME AFTER `<` AND THEN WHITESPACE, `/` OR `>` — so an autolink `<https://…>` and a
   comparison `a < b` are not tags, and `<br>`, `</div>` and `<img src=…>` are. */
var RE_TAG = /<\/?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?\/?>/;

/* `lines` with their 1-based line numbers in the page body, so an error points at the source. */
function numbered(text, first){
  return String(text).replace(/\r\n?/g, "\n").split("\n").map(function(t, i){ return { t: t, n: first + i }; });
}

/* THE BLOCK TREE. `top` is the page body; a container's body is parsed again with `top` false,
   where a container is an error (containers do not nest) and a leaf is fine. */
function parseLines(lines, top, errors){
  var nodes = [], run = [], fence = null, i = 0, seenHeading = false;
  function flush(){
    if (run.length && run.some(function(l){ return l.t.trim(); })) nodes.push({ type: "md", text: run.map(function(l){ return l.t; }).join("\n"), line: run[0].n });
    run = [];
  }
  function err(message, line, source){
    errors.push({ line: line, message: message });
    nodes.push({ type: "error", message: message, line: line, source: source || "" });
  }
  while (i < lines.length){
    var L = lines[i], m;
    if (fence){
      run.push(L); i++;
      if (new RegExp("^\\s*" + fence.charAt(0) + "{" + fence.length + ",}\\s*$").test(L.t)) fence = null;
      continue;
    }
    if ((m = RE_FENCE.exec(L.t))){ fence = m[1]; run.push(L); i++; continue; }

    if ((m = /^(#{1,6})\s+(.*)$/.exec(L.t))){
      flush();
      if (m[1].length === 1) err("the page title comes from front matter; never write a # heading", L.n, L.t);
      else if (m[1].length > 3) err("only ## and ### headings are part of a page", L.n, L.t);
      else if (!top) err("a heading cannot sit inside a block", L.n, L.t);
      else { nodes.push({ type: "heading", level: m[1].length, text: m[2].trim(), id: slug(m[2].trim()), line: L.n }); seenHeading = true; }
      i++; continue;
    }

    if ((m = RE_OPEN.exec(L.t)) && L.t.trim() !== ":::"){
      flush();
      var name = m[1], start = L.n, body = [], closed = false, innerFence = null;
      i++;
      while (i < lines.length){
        var B = lines[i];
        if (innerFence){ if (new RegExp("^\\s*" + innerFence.charAt(0) + "{" + innerFence.length + ",}\\s*$").test(B.t)) innerFence = null; body.push(B); i++; continue; }
        var fm = RE_FENCE.exec(B.t);
        if (fm){ innerFence = fm[1]; body.push(B); i++; continue; }
        if (B.t.trim() === ":::"){ closed = true; i++; break; }
        body.push(B); i++;
      }
      if (!top){ err(":::" + name + " cannot sit inside another block (containers do not nest)", start, L.t); continue; }
      if (!closed){ err(":::" + name + " is never closed with :::", start, L.t); continue; }
      if (!BLOCKS[name] || !BLOCKS[name].c){ err((BLOCKS[name] ? "::" + name + " is a leaf block, written on one line" : ":::" + name + " is not a known block"), start, L.t); continue; }
      var ca = readAttrs(m[2]);
      if (ca.error){ err(ca.error, start, L.t); continue; }
      var cbad = checkAttrs(name, ca.attrs);
      if (cbad){ err(cbad, start, L.t); continue; }
      container(name, ca.attrs, body, start, nodes, errors, seenHeading);
      continue;
    }
    if (L.t.trim() === ":::"){ flush(); err("a ::: closes nothing here", L.n, L.t); i++; continue; }

    if ((m = RE_LEAF.exec(L.t))){
      flush();
      var lname = m[1];
      i++;
      if (!BLOCKS[lname] || BLOCKS[lname].c){ err(BLOCKS[lname] ? ":::" + lname + " is a container, opened with ::: and closed with :::" : "::" + lname + " is not a known block", L.n, L.t); continue; }
      var la = readAttrs(m[3]);
      if (la.error){ err(la.error, L.n, L.t); continue; }
      var lbad = checkAttrs(lname, la.attrs, m[2]);
      if (lbad){ err(lbad, L.n, L.t); continue; }
      var leaf = { type: "block", name: lname, attrs: la.attrs, line: L.n };
      if (m[2] !== undefined) leaf.label = m[2];
      if (lname === "screen"){
        /* THE LEGEND IS THE NUMBERED LIST DIRECTLY UNDER THE BLOCK — no blank line between. */
        leaf.legend = [];
        while (i < lines.length && /^\d+[.)]\s+/.test(lines[i].t)){ leaf.legend.push(lines[i].t.replace(/^\d+[.)]\s+/, "")); i++; }
        var pinCount = leaf.attrs.pins ? String(leaf.attrs.pins).split(",").length : 0;
        if (leaf.legend.length !== pinCount){
          var lm = "the screen has " + pinCount + " pin" + (pinCount === 1 ? "" : "s") + " but " + leaf.legend.length + " legend item" + (leaf.legend.length === 1 ? "" : "s");
          errors.push({ line: L.n, message: lm });
          leaf.error = lm;
        }
      }
      nodes.push(leaf);
      continue;
    }

    if (/^\s*::?[A-Za-z]/.test(L.t) && /^\s*:{2,3}[A-Za-z]/.test(L.t)){
      flush();
      err("a block must start at the beginning of its own line, written exactly as the contract shows", L.n, L.t);
      i++; continue;
    }
    if (RE_TAG.test(L.t.replace(/`[^`]*`/g, ""))){
      errors.push({ line: L.n, message: "raw HTML is not allowed in a page" });
      flush();
      nodes.push({ type: "error", message: "raw HTML is not allowed in a page; it is shown as text", line: L.n, source: L.t });
    }
    run.push(L); i++;
  }
  flush();
  return nodes;
}

function container(name, attrs, body, line, nodes, errors, seenHeading){
  var sub = function(lines){ return parseLines(lines, false, errors); };
  var err = function(message){ errors.push({ line: line, message: message }); nodes.push({ type: "error", message: message, line: line }); };
  if (name === "ideas"){
    /* THE CONSTRUCTS A JOB NEEDS, two to four: `- **Name.** text`, one line each. */
    var ideas = [], bad = false;
    body.forEach(function(l){
      if (!l.t.trim()) return;
      var im = /^\s*[-*]\s+\*\*(.+?)\*\*\s*(.*)$/.exec(l.t);
      if (im) ideas.push({ name: im[1].replace(/\.\s*$/, ""), text: im[2] }); else bad = true;
    });
    if (bad || ideas.length < 2 || ideas.length > 4) return err(":::ideas holds 2 to 4 list items, each `- **Name.** text`");
    nodes.push({ type: "block", name: "ideas", attrs: attrs, items: ideas, line: line });
    return;
  }
  if (name === "lede"){
    if (seenHeading) return err(":::lede must come before the first ## heading");
    if (nodes.some(function(n){ return n.type === "block" && n.name === "lede"; })) return err("a page has at most one :::lede");
    nodes.push({ type: "block", name: "lede", attrs: attrs, text: body.map(function(l){ return l.t; }).join("\n").trim(), line: line });
    return;
  }
  if (name === "steps"){
    var items = [], cur = null, stray = false;
    body.forEach(function(l){
      var m = /^- \[([A-Za-z]+)\]\s+(.*)$/.exec(l.t);
      if (m){ cur = { who: m[1], first: m[2], rest: [], line: l.n }; items.push(cur); return; }
      if (!l.t.trim()){ if (cur) cur.rest.push({ t: "", n: l.n }); return; }
      if (cur && /^ {2}/.test(l.t)){ cur.rest.push({ t: l.t.slice(2), n: l.n }); return; }
      stray = true;
    });
    if (stray) return err("every line in :::steps is an item `- [you|fleet|nobody] **Title.** text` or indented two spaces under one");
    if (!items.length) return err(":::steps holds no items");
    var out = [];
    for (var k = 0; k < items.length; k++){
      var it = items[k];
      if (!WHO[it.who]){ errors.push({ line: it.line, message: "a step is [you], [fleet] or [nobody], not [" + it.who + "]" }); }
      var tm = /^\*\*(.+?)\*\*\s*(.*)$/.exec(it.first);
      if (!tm) errors.push({ line: it.line, message: "a step starts with its **Title.**" });
      var lines = [{ t: tm ? tm[2] : it.first, n: it.line }].concat(it.rest);
      out.push({ who: it.who, title: tm ? tm[1].replace(/\.\s*$/, "") : "", nodes: sub(lines), line: it.line,
        error: !WHO[it.who] ? "a step is [you], [fleet] or [nobody], not [" + it.who + "]" : (!tm ? "a step starts with its **Title.**" : "") });
    }
    nodes.push({ type: "block", name: "steps", attrs: attrs, items: out, line: line });
    return;
  }
  if (name === "compare"){
    var rows = body.filter(function(l){ return l.t.trim(); });
    var split = function(s){ return s.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map(function(c){ return c.trim(); }); };
    var isTable = rows.length >= 3 && rows.every(function(l){ return l.t.indexOf("|") >= 0; }) &&
      /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(rows[1].t) && rows[1].t.indexOf("-") >= 0;
    if (!isTable) return err(":::compare holds exactly one markdown table (a header row, a separator, then rows)");
    var head = split(rows[0].t);
    if (head.length < 2) return err(":::compare needs at least one option column after the first");
    nodes.push({ type: "block", name: "compare", attrs: attrs, head: head, rows: rows.slice(2).map(function(r){ return split(r.t); }), line: line });
    return;
  }
  /* callout, mode: a body of markdown that may hold leaf blocks. */
  nodes.push({ type: "block", name: name, attrs: attrs, nodes: sub(body), line: line });
}

/* ADJACENT `:::mode` BLOCKS BECOME ONE TAB SET. "Adjacent" means nothing but blank lines between
   them, which the parser has already dropped. */
function groupModes(nodes){
  var out = [];
  nodes.forEach(function(n){
    if (n.type === "block" && n.name === "mode"){
      var key = n.attrs.programs ? "programs" : "areas";
      var last = out[out.length - 1];
      var item = { mode: key, nodes: n.nodes, line: n.line };
      if (last && last.type === "modes") last.items.push(item);
      else out.push({ type: "modes", items: [item], line: n.line });
      return;
    }
    out.push(n);
  });
  return out;
}

/* `parse(body)` -> `{ nodes, errors }`. `body` is the page's markdown after its front matter (what
   `/api/docs/page` serves); a body that still carries front matter has it dropped here, so a test or
   a preview can hand the whole file. Nodes:
     {type:"md", text, line}                       a run of plain markdown, for `Board.mdBlock`
     {type:"heading", level:2|3, text, id, line}
     {type:"block", name, attrs, line, …}          lede {text} · steps {items:[{who,title,nodes}]}
                                                   · callout {nodes} · compare {head,rows}
                                                   · screen {legend} · action {label} · other leaves
     {type:"modes", items:[{mode, nodes}], line}   adjacent :::mode blocks, one tab set
     {type:"error", message, line, source}
   `errors` is `[{line, message}]`, every problem the page has, in order. */
function parse(body){
  var text = String(body == null ? "" : body).replace(/\r\n?/g, "\n");
  var first = 1;
  if (/^---\n/.test(text)){
    var end = text.indexOf("\n---", 4);
    if (end >= 0){
      var stop = text.indexOf("\n", end + 4);
      var cut = stop < 0 ? text.length : stop + 1;
      first += text.slice(0, cut).split("\n").length - 1;
      text = text.slice(cut);
    }
  }
  var errors = [];
  var nodes = groupModes(parseLines(numbered(text, first), true, errors));
  nodes.forEach(function(n){ if (n.type === "block" && n.name === "steps") n.items.forEach(function(it){ it.nodes = groupModes(it.nodes); }); });
  return { nodes: nodes, errors: errors };
}

/* -- inline: terms, keys and the two link families mdBlock does not know -------------------- */

/* THE ONE RENDERER STAYS THE ONE RENDERER. `:term[…]`, `:kbd[…]`, an `app:` link and a page-id link
   are cut out of the source and held behind private-use markers BEFORE `Board.mdBlock` sees the
   text, then put back into what it wrote. Everything else — paragraphs, lists, tables, code,
   emphasis — is `mdBlock`'s. Code spans and fences are skipped, so `` `:term[x]` `` stays code. */
var HOLD_A = "\uE000", HOLD_B = "\uE001";
var RE_HELD = /\uE000(\d+)\uE001/g;
var RE_INLINE = /:term\[([^\]\n]+)\]|:kbd\[([^\]\n]+)\]|\[([^\]\n]+)\]\((app:[A-Za-z][\w:-]*|[a-z0-9][a-z0-9-]*(?:\/[a-z0-9][a-z0-9-]*)*)\)/g;

function holdInline(src, held){
  var fence = null;
  return String(src).split("\n").map(function(line){
    var f = RE_FENCE.exec(line);
    if (fence){ if (f && f[1].charAt(0) === fence.charAt(0) && f[1].length >= fence.length && !line.replace(RE_FENCE, "").trim()) fence = null; return line; }
    if (f){ fence = f[1]; return line; }
    return line.split(/(`[^`\n]*`)/).map(function(part, i){
      if (i % 2) return part;
      return part.replace(RE_INLINE, function(all, term, kbd, text, dest){
        var h = term !== undefined ? { kind: "term", word: term } : kbd !== undefined ? { kind: "kbd", keys: kbd } : { kind: "link", text: text, dest: dest };
        return HOLD_A + (held.push(h) - 1) + HOLD_B;
      });
    }).join("");
  }).join("\n");
}

function inlineHtml(text, R){
  var B = board();
  if (B && typeof B.mdown === "function") return B.mdown(String(text), false, undefined, false);
  return esc(text);
}

function heldHtml(h, R){
  if (h.kind === "kbd"){
    return String(h.keys).split(/\s*\+\s*/).map(function(k){ return '<kbd class="dx-kbd">' + esc(k) + "</kbd>"; }).join('<span class="dx-kbd-plus">+</span>');
  }
  if (h.kind === "term"){
    var found = ctxCall(R.ctx, "term", h.word);
    if (!found || !found.def){
      R.errors.push({ line: 0, message: 'the term "' + h.word + '" is in neither terms.md nor the glossary' });
      return '<span class="dx-ierr" title="No definition for this word">' + esc(h.word) + "</span>";
    }
    var id = R.uid + "-t" + (R.terms++);
    return '<span class="dx-tt"><button type="button" class="dx-term" aria-expanded="false" aria-controls="' + id +
      '" data-dx-term="' + esc(id) + '" data-dx-word="' + esc(found.word || h.word) + '" data-dx-def="' + esc(found.def) + '">' +
      esc(h.word) + '</button><span class="dx-tip" id="' + id + '" role="status"></span></span>';
  }
  /* a link: `app:<route>` or a page id */
  var href = "", missing = false;
  if (/^app:/.test(h.dest)) href = ctxCall(R.ctx, "href", h.dest.slice(4)) || "";
  else {
    if (typeof (R.ctx && R.ctx.page) === "function" && !ctxCall(R.ctx, "page", h.dest)) missing = true;
    href = ctxCall(R.ctx, "docHref", h.dest) || "";
  }
  if (missing){
    R.errors.push({ line: 0, message: 'no docs page has the id "' + h.dest + '"' });
    return '<span class="dx-ierr" title="No docs page has the id ' + esc(h.dest) + '">' + inlineHtml(h.text, R) + "</span>";
  }
  return '<a class="md-a dx-a" href="' + esc(href) + '">' + inlineHtml(h.text, R) + "</a>";
}

function release(html, held, R){
  return String(html).replace(RE_HELD, function(_, i){ var h = held[Number(i)]; return h ? heldHtml(h, R) : ""; });
}

/* A RUN OF PLAIN MARKDOWN, through `Board.mdBlock` and nothing else. */
function mdRun(text, R){
  var held = [];
  var src = holdInline(text, held);
  var B = board();
  var html = B && typeof B.mdBlock === "function" ? B.mdBlock(src) : "<p>" + esc(src) + "</p>";
  return withCopy(release(html, held, R));
}
/* EVERY FENCED BLOCK GETS `::command`'S COPY BUTTON. A docs page's fences are things to paste — a
   `fleet init`, a `mkdir … && printf …` one-liner — and a reader selecting a line that scrolls
   sideways copies half of it. The block is still `mdBlock`'s `<pre class="md-pre">`, untouched:
   this only wraps it, so the one renderer stays the one renderer. The button copies the code's
   TEXT (the escaped markup read back), and the block scrolls inside itself, never the page. */
function unesc(s){
  return String(s).replace(/<[^>]*>/g, "").replace(/&(amp|lt|gt|quot|#39);/g, function(_, e){
    return { amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'" }[e];
  });
}
var RE_PRE = /<pre class="md-pre"[^>]*>[\s\S]*?<\/pre>/g;
function withCopy(html){
  return String(html).replace(RE_PRE, function(pre){
    var text = unesc(pre).replace(/\n$/, "");
    return '<div class="dx-code">' + pre + '<button type="button" class="dx-cmd-copy dx-code-copy" data-dx-copy="' + esc(text) + '">Copy</button></div>';
  });
}
/* One line of inline markdown — a heading, a step title, a legend item, a table cell. */
function mdLine(text, R){
  var held = [];
  return release(inlineHtml(holdInline(text, held), R), held, R);
}

/* -- the components ------------------------------------------------------------------------- */

function nodesHtml(nodes, R){ return nodes.map(function(n){ return nodeHtml(n, R); }).join(""); }

function nodeHtml(n, R){
  if (n.type === "md") return mdRun(n.text, R);
  if (n.type === "error") return errHtml(n.message, n.line);
  if (n.type === "heading"){
    return "<h" + n.level + ' class="dx-h dx-h' + n.level + '" id="' + esc(n.id) + '">' + mdLine(n.text, R) + "</h" + n.level + ">";
  }
  if (n.type === "modes") return modesHtml(n, R);
  if (n.type === "block"){
    var f = COMPONENTS[n.name];
    return f ? f(n, R) : errHtml("::" + n.name + " is not a known block", n.line);
  }
  return "";
}

function modesHtml(n, R){
  var mode = R.ctx && R.ctx.mode;
  var open = n.items.some(function(x){ return x.mode === mode; }) ? mode : n.items[0].mode;
  var base = R.uid + "-m" + (R.modes++);
  var tabs = n.items.map(function(x, i){
    var on = x.mode === open;
    return '<button type="button" class="dx-mode-tab" role="tab" id="' + base + "-t" + i + '" aria-controls="' + base + "-p" + i +
      '" aria-selected="' + on + '" tabindex="' + (on ? "0" : "-1") + '" data-dx-tab="' + esc(x.mode) + '">' +
      esc(MODE_WORD[x.mode] || x.mode) + '<small>' + (x.mode === mode ? "your repository" : "other repositories") + "</small></button>";
  }).join("");
  var panels = n.items.map(function(x, i){
    return '<div class="dx-mode-p" role="tabpanel" id="' + base + "-p" + i + '" aria-labelledby="' + base + "-t" + i +
      '" data-dx-panel="' + esc(x.mode) + '"' + (x.mode === open ? "" : " hidden") + ">" + nodesHtml(x.nodes, R) + "</div>";
  }).join("");
  return '<div class="dx-mode" data-dx-modes=""><div class="dx-mode-tabs" role="tablist" aria-label="How your repository plans">' + tabs + "</div>" + panels + "</div>";
}

/* -- live: a skeleton now, a card when `ctx.live` answers ----------------------------------- */

function liveKind(attrs){
  for (var k in LIVE_NOUN) if (Object.prototype.hasOwnProperty.call(attrs, k)) return k;
  return "";
}
function later(R, kind, id, fill){
  var key = R.uid + "-l" + (R.lives.length);
  R.lives.push({ key: key, kind: kind, id: id, fill: fill });
  return key;
}
function liveSkeleton(key, kind, id){
  return '<section class="dx-live" data-dx-live="' + esc(key) + '" aria-busy="true" aria-label="' + esc(LIVE_NOUN[kind] + " " + id) + '">' +
    '<div class="dx-live-h"><span class="dx-dot">Live from your knowledge</span><span class="dx-live-at">reading…</span></div>' +
    '<div class="dx-live-b"><span class="dx-sk dx-sk-t"></span><span class="dx-sk"></span><span class="dx-sk dx-sk-s"></span></div>' +
    '<div class="dx-live-f"><code>' + esc(id) + "</code></div></section>";
}
/* THE WRITTEN EXAMPLE, when the reader's repository does not hold the item (or could not be read):
   the page's own words for it, marked as Fleet's example, so the reader still sees a real one. */
function exampleCard(kind, id, ex){
  return '<div class="dx-live-h"><span class="dx-dot dx-dot-ex">Example from Fleet\'s own planning</span></div>' +
    '<div class="dx-live-b"><span class="dx-live-t">' + esc(ex.title) + "</span>" +
    (ex.quote ? '<blockquote class="dx-live-q">' + esc(ex.quote) + "</blockquote>" : "") + "</div>" +
    '<div class="dx-live-f"><code>' + esc(id) + "</code><span>" + esc(LIVE_NOUN[kind]) + "</span></div>";
}
function liveCard(kind, id, v, ex){
  if (!v && ex && ex.title) return exampleCard(kind, id, ex);
  if (v === undefined) return '<div class="dx-live-h"><span class="dx-dot dx-dot-off">Live from your knowledge</span></div>' +
    '<div class="dx-live-b dx-live-none">Could not read ' + esc(LIVE_NOUN[kind] + " " + id) + ' just now.</div><div class="dx-live-f"><code>' + esc(id) + "</code></div>";
  if (!v) return '<div class="dx-live-h"><span class="dx-dot dx-dot-off">Live from your knowledge</span></div>' +
    '<div class="dx-live-b dx-live-none"><b>' + esc(LIVE_NOUN[kind] + " " + id) + "</b> is not found in this repository's knowledge.</div>" +
    '<div class="dx-live-f"><code>' + esc(id) + "</code></div>";
  var fields = (v.fields || []).map(function(f){ return "<span>" + esc(f[0]) + " <b>" + esc(f[1]) + "</b></span>"; }).join("");
  return '<div class="dx-live-h"><span class="dx-dot">Live from your knowledge</span>' +
    (v.commit ? '<span class="dx-live-at">read at <code>' + esc(String(v.commit).slice(0, 7)) + "</code></span>" : "") + "</div>" +
    '<div class="dx-live-b"><span class="dx-live-t">' + esc(v.title || id) + "</span>" +
    (v.quote ? '<blockquote class="dx-live-q">' + esc(v.quote) + "</blockquote>" : "") +
    (fields ? '<div class="dx-kv">' + fields + "</div>" : "") + "</div>" +
    '<div class="dx-live-f"><code>' + esc(id) + "</code>" + (v.href ? '<a class="dx-live-open" href="' + esc(v.href) + '">Open this ' + esc(LIVE_NOUN[kind]) + " →</a>" : "") + "</div>";
}

/* -- the diagrams --------------------------------------------------------------------------- */

function field(v, re){
  var hit = (v && v.fields || []).filter(function(f){ return re.test(String(f[0])); })[0];
  return hit ? String(hit[1]) : "";
}
function threeQuestions(v, id){
  var here = function(x){ return '<div class="dx-qd-ex">Here: <b>' + (x ? esc(x) : "—") + "</b></div>"; };
  /* THE PROOF PRD IS THE PAYLOAD'S `prd` (the app's ctx adds it, with `prdRepo`, because the proof
     can live in another repository); the "Proven by" field is the fallback. A slice that HAS a proof
     never renders a bare dash. */
  var area = v ? field(v, /area/i) : "";
  var prd = "";
  if (v && v.prd) prd = "PRD " + String(v.prd).replace(/^PRD\s*/i, "");
  else if (v) { prd = field(v, /proven by/i) || field(v, /prd/i); if (prd && !/^PRD/i.test(prd)) prd = "PRD " + prd; }
  return '<div class="dx-qd-c"><span class="dx-qd-bar dx-qd-b1"></span><span class="dx-qd-q">Where does it belong?</span><div class="dx-qd-a">Feature</div>' +
      '<div class="dx-qd-d">A part of the product a customer would name.</div><span class="dx-life">never finishes</span>' + (v ? here(area) : "") + "</div>" +
    '<div class="dx-qd-c"><span class="dx-qd-bar dx-qd-b2"></span><span class="dx-qd-q">What will be true when we\'re done?</span><div class="dx-qd-a">Slice</div>' +
      '<div class="dx-qd-d">One sentence that is either true or not.</div><span class="dx-life dx-life-y">finishes</span>' + (v ? here(v.title || id) : "") + "</div>" +
    '<div class="dx-qd-c"><span class="dx-qd-bar dx-qd-b3"></span><span class="dx-qd-q">What does one agent build?</span><div class="dx-qd-a">PRD</div>' +
      '<div class="dx-qd-d">A piece one session can build, with checks it must pass.</div><span class="dx-life dx-life-y">finishes</span>' + (v ? here(prd) : "") + "</div>";
}

/* THE WORK LINE, as the app's own page names it: four bands, the stations a reader meets most, and
   each station's attendance in the page's words. A program step is drawn only for a repository
   that plans by programs. */
var LINE = [
  ["Decide what to build", [["File a feature request", "your call"], ["Interview the filer", "asks you"], ["Accept the proposal", "your call"]]],
  ["Make it buildable", [["Refine the slice", "asks you"], ["Draft the PRD", "asks you"], ["Design it", "asks you"], ["Plan it", "runs alone"]]],
  ["Build it", [["The triage gate", "runs alone"], ["Implement", "runs alone"], ["Verify", "runs alone"], ["Merged", "derived"]]],
  ["Close it", [["The slice reads complete", "derived"], ["Close the program", "runs alone", "programs"]]]
];
var ATT_CLASS = { "your call": "call", "asks you": "asks", "runs alone": "alone", "derived": "derived" };
function workLine(R){
  var mode = R.ctx && R.ctx.mode;
  return '<ol class="dx-wl">' + LINE.map(function(b, i){
    var st = b[1].filter(function(s){ return !s[2] || s[2] === mode; });
    return '<li class="dx-wl-band"><span class="dx-wl-n">Band ' + (i + 1) + '</span><b class="dx-wl-t">' + esc(b[0]) + '</b><ol class="dx-wl-st">' +
      st.map(function(s){ return '<li><span class="dx-wl-dot dx-att-' + ATT_CLASS[s[1]] + '"></span>' + esc(s[0]) + ' <span class="dx-att dx-att-' + ATT_CLASS[s[1]] + '">' + esc(s[1]) + "</span></li>"; }).join("") +
      "</ol></li>";
  }).join("") + "</ol>";
}
/* THE KNOWLEDGE FOLDER: where each kind of planning record lives. `programs.md` is drawn only for a
   repository that plans by programs. */
function knowledgeFolder(R){
  var mode = R.ctx && R.ctx.mode;
  var rows = [
    ["features/", "one file per feature — the parts of the product that never finish"],
    mode === "programs" ? ["programs.md", "every program, one row each"] : null,
    ["slices.md", "every slice, one row each: what will be true when it is done"],
    ["slices/", "a slice's own page, when it needs more than one row"],
    ["prds/", "one folder per PRD: what one session builds, and its checks"],
    ["requirements/", "the numbered promises, one register per domain"],
    ["decisions/", "decisions on the record, and why"]
  ].filter(Boolean);
  return '<div class="dx-kf"><div class="dx-kf-root">knowledge/</div><ul class="dx-kf-l">' +
    rows.map(function(r){ return '<li><code>' + esc(r[0]) + '</code><span>' + esc(r[1]) + "</span></li>"; }).join("") + "</ul></div>";
}

function links(n){
  return String(n.attrs.links || "").split(",").map(function(x){ return x.trim(); }).filter(Boolean);
}

/* THE KNOWLEDGE BASE ON ONE SCREEN: what the folder holds, by what it is FOR rather than by file —
   planning (what is changing), the product (what is true), commitments (what must stay true), and
   the repository's own answers and records. `knowledge-folder` is the same folder file by file. */
function knowledgeMap(R){
  var box = function(t, d, k){ return '<div class="dx-km-i' + (k ? " dx-km-" + k : "") + '"><b>' + esc(t) + "</b><span>" + esc(d) + "</span></div>"; };
  var by = function(w){ return '<i class="dx-km-by">' + esc(w) + "</i>"; };
  var programs = R.ctx && R.ctx.mode === "programs";
  return '<div class="dx-km"><div class="dx-km-h"><code>knowledge/</code><span>in your repository</span></div><div class="dx-km-g">' +
    '<div class="dx-km-c"><small>Planning: what is changing</small>' +
      box("Feature", "a part of the product · never finishes", "a") + by("holds") +
      box("Slice", "one sentence, true or not · finishes", "s") + by("built by") +
      box("PRD", "what one session builds · finishes", "p") +
      '<p class="dx-km-n">' + (programs ? "This repository also groups slices into <b>programs</b>, larger results several slices add up to." : "Optional: a <b>program</b> groups slices into a larger result.") + "</p></div>" +
    '<div class="dx-km-c"><small>The product: what is true</small>' +
      box("Capabilities and components", "what someone can do · what is built") + box("Journeys", "how a person gets a whole job done") +
      "<small>Commitments: what must stay true</small>" +
      box("Promises", "numbered requirements, never deleted") + box("Decisions", "why, so it outlives the conversation") + "</div>" +
    '<div class="dx-km-c"><small>About your repository</small>' +
      box("Slots", "your answers to the commands' questions") + box("Records", "check results, audits, retros") +
      box("Generated tables", "rendered from files, never edited by hand") + "</div>" +
    '</div><p class="dx-km-f">Agents read this folder before they build. The Quality desk checks the product against the promises in it.</p></div>';
}

/* FLEET ON ONE LINE: the four moves every change makes, who makes each, and what all four stand on. */
function fleetMap(){
  var step = function(who, t, d){ return '<div class="dx-fm-s dx-fm-' + who + '"><span class="dx-who dx-who-' + who + '">' + esc(WHO[who]) + "</span><b>" + esc(t) + "</b><span>" + esc(d) + "</span></div>"; };
  var arrow = '<i class="dx-fm-ar" aria-hidden="true">→</i>';
  return '<div class="dx-fm"><div class="dx-fm-row">' +
    step("you", "You file", "an idea, a bug or a task, and answer what only a person can") + arrow +
    step("fleet", "Fleet builds", "a session on one of your machines writes it and opens a pull request") + arrow +
    step("fleet", "A second session verifies", "one that never saw the code proves each claim, or sends it back") + arrow +
    step("nobody", "It merges", "and what it promised is checked from then on") +
    '</div><div class="dx-fm-base"><small>Everything above stands on</small><div>' +
    "<span><b>The knowledge base</b> what the product is and promised</span><span><b>Machines and seats</b> where sessions run, and how many at once</span><span><b>Your tools</b> MCP servers, secrets, API keys</span>" +
    "</div></div></div>";
}

/* -- screens -------------------------------------------------------------------------------- */

var SCREEN_LIVE = { areas: "area", program: "program", slice: "slice" };

/* PINS ARE NUMBERED IN THE ORDER THE CROP DRAWS THEM, NOT THE ORDER THE BLOCK LISTS THEM. A crop
   is drawn top to bottom and left to right, so its markup order is its reading order; numbering by
   `pins=` instead made the Program screen read 3, 2, 1 down the page, because its levers sit above
   its slices. So `pin` leaves a blank marker, the markers are numbered once the drawing is done, and
   `screen` re-orders the legend to match — the item a pin points at keeps its words, only its
   position moves. `order` is the anchor names in drawing order. */
var PIN_MARK = "\u0001";
var RE_PIN = /<span class="dx-pin" data-dx-pin="([^"]*)">\u0001<\/span>/g;
function screenPins(n){ return n.attrs.pins ? String(n.attrs.pins).split(",").map(function(x){ return x.trim(); }) : []; }
function screenInner(n, R, item){
  var s = D.screens[n.attrs.route];
  var pins = screenPins(n);
  var drawn = {};
  var pin = function(name){
    if (pins.indexOf(name) < 0 || drawn[name]) return "";
    drawn[name] = true;
    return '<span class="dx-pin" data-dx-pin="' + esc(name) + '">' + PIN_MARK + "</span>";
  };
  var body;
  try { body = s.draw({ focus: n.attrs.focus || "", item: item || null, pin: pin, esc: esc, mode: R.ctx && R.ctx.mode }); }
  catch (e) { return { html: errHtml("the " + n.attrs.route + " screen could not be drawn: " + (e && e.message || e), n.line), order: [] }; }
  var order = [];
  body = String(body).replace(RE_PIN, function(_, name){
    order.push(name);
    return '<span class="dx-pin" data-dx-pin="' + name + '">' + order.length + "</span>";
  });
  var lost = pins.filter(function(p){ return !drawn[p]; });
  return { order: order.map(function(nm){ return pins.filter(function(p){ return esc(p) === nm; })[0]; }),
    html: '<div class="dx-shot" aria-hidden="true"><div class="dx-chrome"><i></i><i></i><i></i><span>' + esc(s.title) + "</span></div>" +
    '<div class="dx-app">' + body + "</div></div>" +
    (lost.length ? errHtml("the " + n.attrs.route + " screen did not place the pin" + (lost.length > 1 ? "s " : " ") + lost.join(", "), n.line) : "") };
}
/* The legend in the crop's drawing order: `pins[j]` is described by `legend[j]`, so each drawn pin
   takes its own item along; an item for a pin the crop lost, or one past the pins, keeps its place
   at the end. */
function legendInOrder(n, order){
  var pins = screenPins(n);
  var seq = order.map(function(name){ return pins.indexOf(name); }).filter(function(j){ return j >= 0 && j < n.legend.length; });
  for (var j = 0; j < n.legend.length; j++) if (seq.indexOf(j) < 0) seq.push(j);
  return seq.map(function(j){ return n.legend[j]; });
}

var COMPONENTS = {
  lede: function(){ return ""; },
  steps: function(n, R){
    return '<ol class="dx-steps">' + n.items.map(function(it){
      var w = WHO[it.who] ? it.who : "fleet";
      return '<li class="dx-step"><span class="dx-who dx-who-' + w + '">' + esc(WHO[it.who] || it.who) + "</span>" +
        '<div class="dx-step-b">' + (it.error ? errHtml(it.error, it.line) : "") +
        (it.title ? '<h3 class="dx-step-t">' + mdLine(it.title, R) + "</h3>" : "") + nodesHtml(it.nodes, R) + "</div></li>";
    }).join("") + "</ol>";
  },
  callout: function(n, R){
    var k = n.attrs.kind;
    return '<aside class="dx-callout dx-callout-' + esc(k) + '" aria-label="' + esc(CALLOUTS[k]) + '"><span class="dx-callout-k" aria-hidden="true">' + esc(CALLOUTS[k]) + "</span>" +
      '<div class="dx-callout-b">' + (n.attrs.figure ? '<span class="dx-callout-fig">' + esc(n.attrs.figure) + "</span>" : "") + nodesHtml(n.nodes, R) + "</div></aside>";
  },
  compare: function(n, R){
    var cols = n.head.slice(1);
    return '<div class="dx-compare">' + cols.map(function(c, j){
      return '<section class="dx-opt"><h4 class="dx-opt-t">' + mdLine(c, R) + '</h4><dl class="dx-opt-l">' +
        n.rows.map(function(r){ return "<dt>" + mdLine(r[0] || "", R) + "</dt><dd>" + mdLine(r[j + 1] || "", R) + "</dd>"; }).join("") + "</dl></section>";
    }).join("") + "</div>";
  },
  diagram: function(n, R){
    var name = n.attrs.name;
    if (name === "work-line") return '<figure class="dx-diagram">' + workLine(R) + "</figure>";
    if (name === "knowledge-folder") return '<figure class="dx-diagram">' + knowledgeFolder(R) + "</figure>";
    if (name === "knowledge-map") return '<figure class="dx-diagram">' + knowledgeMap(R) + "</figure>";
    if (name === "fleet-map") return '<figure class="dx-diagram">' + fleetMap() + "</figure>";
    var id = n.attrs.slice;
    var key = later(R, "slice", id, function(v){ return v ? threeQuestions(v, id) : null; });
    return '<figure class="dx-diagram"><div class="dx-qd" data-dx-live="' + esc(key) + '" aria-busy="true">' + threeQuestions(null, id) + "</div></figure>";
  },
  live: function(n, R){
    var kind = liveKind(n.attrs), id = n.attrs[kind];
    var ex = { title: n.attrs.title || "", quote: n.attrs.quote || "" };
    var key = later(R, kind, id, function(v, failed){ return liveCard(kind, id, failed ? undefined : v, ex); });
    return liveSkeleton(key, kind, id);
  },
  screen: function(n, R){
    var s = D.screens[n.attrs.route];
    var kind = SCREEN_LIVE[n.attrs.route];
    var key = "";
    if (n.attrs.focus && kind){
      key = later(R, kind, n.attrs.focus, function(v){ return screenInner(n, R, v || null).html; });
    }
    var first = screenInner(n, R, null);
    var legend = legendInOrder(n, first.order);
    return '<figure class="dx-screen">' +
      '<figcaption class="dx-vh">A picture of the ' + esc(s.title) + " page" + (n.legend.length ? ", with numbered points:" : "") + "</figcaption>" +
      '<div class="dx-screen-f"' + (key ? ' data-dx-live="' + esc(key) + '"' : "") + ">" + first.html + "</div>" +
      (n.error ? errHtml(n.error, n.line) : "") +
      (legend.length ? '<ol class="dx-legend">' + legend.map(function(t, j){ return '<li><span class="dx-legend-n" aria-hidden="true">' + (j + 1) + "</span><span>" + mdLine(t, R) + "</span></li>"; }).join("") + "</ol>" : "") +
      "</figure>";
  },
  action: function(n, R){
    var href = ctxCall(R.ctx, "href", n.attrs.route) || "";
    return '<p class="dx-action-w"><a class="dx-action" href="' + esc(href) + '">' + esc(n.label) + ' <span aria-hidden="true">→</span></a></p>';
  },
  ideas: function(n, R){
    return '<div class="dx-ideas">' + n.items.map(function(it){
      /* the name and the text carry classes of their own: a rule on `.dx-idea b` also styled every
         bold word INSIDE the text as a block, and broke "OK, ATTENTION, …" one word to a line */
      return '<div class="dx-idea"><b class="dx-idea-n">' + esc(it.name) + '</b><span class="dx-idea-t">' + mdLine(it.text, R) + "</span></div>";
    }).join("") + "</div>";
  },
  /* A JOB'S READING PATH: numbered, each page with its summary and reading time, the first one
     marked as where to begin; the total time sits under the last. */
  path: function(n, R){
    var total = 0;
    var rows = links(n).map(function(id, i){
      var p = ctxCall(R.ctx, "page", id);
      if (!p) return "<li>" + errHtml('no docs page has the id "' + id + '"', n.line) + "</li>";
      if (p.minutes) total += p.minutes;
      return '<li><a class="dx-path-a" href="' + esc(p.href || ctxCall(R.ctx, "docHref", id) || "") + '"><span class="dx-path-n">' + (i + 1) + "</span>" +
        '<span class="dx-path-b"><b>' + esc(p.title) + "</b><span>" + esc(p.summary || "") + "</span></span>" +
        (p.minutes ? '<span class="dx-path-m">' + esc(p.minutes) + " min</span>" : "") + "</a></li>";
    });
    return '<ol class="dx-path">' + rows.join("") + "</ol>" + (total ? '<p class="dx-path-t">' + total + " minutes, in order</p>" : "");
  },
  pages: function(n, R){
    return '<ul class="dx-pages">' + links(n).map(function(id){
      var p = ctxCall(R.ctx, "page", id);
      if (!p) return "<li>" + errHtml('no docs page has the id "' + id + '"', n.line) + "</li>";
      return '<li><a href="' + esc(p.href || ctxCall(R.ctx, "docHref", id) || "") + '"><b>' + esc(p.title) + "</b><span>" + esc(p.summary || "") + "</span></a></li>";
    }).join("") + "</ul>";
  },
  /* A CARD THE PREVIOUS / NEXT PAIR ALREADY SHOWS IS DROPPED. A `::cards` row at the foot of a page
     sat right above the Previous and Next cards and often repeated one of them; the pair is the
     page's own, so the row gives way, and a row left with nothing draws nothing at all. */
  cards: function(n, R){
    var pg = R.page || {};
    var skip = [pg.prev && pg.prev.id, pg.next && pg.next.id].filter(Boolean);
    var ids = String(n.attrs.links).split(",").map(function(id){ return id.trim(); }).filter(function(id){ return id && skip.indexOf(id) < 0; });
    if (!ids.length) return "";
    return '<div class="dx-cards">' + ids.map(function(id){
      var p = ctxCall(R.ctx, "page", id);
      if (!p) return errHtml('no docs page has the id "' + id + '"', n.line);
      return '<a class="dx-card" href="' + esc(p.href || ctxCall(R.ctx, "docHref", id) || "") + '"><b>' + esc(p.title) + "</b><span>" + esc(p.summary || "") + "</span></a>";
    }).join("") + "</div>";
  },
  command: function(n, R){
    /* The repository's own tree first (typed the way it types it), then the tree Fleet ships,
       which the page payload carries (`commands`); only a name neither holds is an error. */
    var c = ctxCall(R.ctx, "command", n.attrs.name);
    var shipped = R.page && R.page.commands;
    if (!c && shipped && Object.prototype.hasOwnProperty.call(shipped, n.attrs.name)) c = { name: n.attrs.name, purpose: shipped[n.attrs.name] };
    if (!c) return errHtml('Fleet has no command "' + n.attrs.name + '"', n.line);
    var B = board();
    var shown = /^\//.test(c.name) ? c.name : (B && typeof B.invocation === "function" ? B.invocation(c.name) : "/" + c.name);
    return '<div class="dx-cmd"><code class="dx-cmd-n">' + esc(shown) + '</code><button type="button" class="dx-cmd-copy" data-dx-copy="' + esc(shown) +
      '">Copy</button><p class="dx-cmd-p">' + esc(c.purpose || "") + "</p></div>";
  },
  figure: function(n, R){
    var f = D.figures[n.attrs.name];
    var body;
    try { body = f.draw(R.ctx); } catch (e) { return errHtml("the figure " + n.attrs.name + " could not be drawn", n.line); }
    return '<figure class="dx-fig"><div aria-hidden="true">' + body + '</div><figcaption class="dx-vh">' + esc(n.attrs.alt) + "</figcaption></figure>";
  },
  /* A SLOT, FILLED ONCE THE PAGE IS IN THE TREE (`hangEmbeds`): the host's answer may be a live node
     it keeps repainting, which no string of markup could carry. */
  embed: function(n, R){
    var key = R.uid + "-e" + (R.embeds || (R.embeds = [])).length;
    R.embeds.push({ key: key, name: n.attrs.name, line: n.line });
    return '<div class="dx-embed" data-dx-embed="' + esc(key) + '"></div>';
  }
};

/* Hang each embed the host draws into its slot: a node is appended as it is (so the host can keep
   it current), a string is its markup, and anything else — no `ctx.embed`, or a name the host does
   not draw — is the visible error an invalid block always is. */
function hangEmbeds(el, R){
  (R.embeds || []).forEach(function(e){
    var slot = el.querySelector('[data-dx-embed="' + e.key + '"]');
    if (!slot) return;
    var v = ctxCall(R.ctx, "embed", e.name);
    if (v && typeof v === "object" && v.nodeType === 1) slot.appendChild(v);
    else if (typeof v === "string" && v) slot.innerHTML = v;
    else slot.innerHTML = errHtml("the app cannot draw the " + e.name + " embed here", e.line);
  });
}

/* -- the page ------------------------------------------------------------------------------- */

function sectionOf(index, id){
  var hit = null;
  ((index && index.sections) || []).forEach(function(s){ (s.pages || []).forEach(function(p){ if (p.id === id && !hit) hit = s; }); });
  return hit;
}
function forWords(list){
  var xs = (Array.isArray(list) ? list : list ? [list] : []).map(function(x){ return FOR_WORD[x] || x; });
  if (!xs.length) return "";
  return "For " + (xs.length === 1 ? xs[0] : xs.slice(0, -1).join(", ") + " and " + xs[xs.length - 1]);
}

function heroHtml(title, crumbs, lede, meta, big){
  return '<header class="dx-hero' + (big ? " dx-hero-home" : "") + '"><div class="dx-hero-in">' +
    '<div class="dx-hero-top">' + (crumbs ? '<nav class="dx-crumb" aria-label="Where this page is">' + crumbs + "</nav>" : "<span></span>") +
    (big ? "" : searchHtml(false)) + "</div>" +
    '<h1 class="dx-title">' + esc(title) + "</h1>" + (lede || "") + (big ? searchHtml(true) : "") +
    (meta ? '<div class="dx-meta">' + meta + "</div>" : "") + "</div></header>";
}

/* -- search --------------------------------------------------------------------------------- */

/* THE SEARCH BOX SITS IN THE BAND OF EVERY DOCS PAGE — large under the title on the home, compact
   beside the breadcrumb on a page — so finding a page is never a trip back to the contents. It is
   an ARIA combobox over a listbox of results: type, arrow through, Enter opens; `/` from anywhere
   on a docs page focuses it. The words searched are `/api/docs/search`'s, read once on first use
   through `ctx.search()` and matched here as the reader types: every query word must appear in a
   page's title or one of its sections, and a hit in a title outranks a heading, which outranks
   the prose. A result opens at the section it matched. */
var SEARCH_UID = 0;
function searchHtml(big){
  var id = "dx-sr" + (++SEARCH_UID);
  return '<div class="dx-search' + (big ? " dx-search-big" : "") + '" role="search" data-dx-search>' +
    '<svg class="dx-search-i" viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M13 13l4.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>' +
    '<input type="search" autocomplete="off" spellcheck="false" placeholder="' + (big ? "Search the docs, e.g. secrets, seats, slice" : "Search the docs") + '"' +
    ' role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="' + id + '" aria-label="Search the docs" data-dx-q>' +
    '<kbd class="dx-search-k" aria-hidden="true">/</kbd>' +
    '<div class="dx-search-r" id="' + id + '" role="listbox" aria-label="Search results" hidden></div></div>';
}

function words(q){
  return String(q || "").toLowerCase().split(/[^a-z0-9]+/).filter(function(w){ return w.length > 0; });
}

/* `search(payload, query)` → up to `limit` results, best first: `{id, title, section, heading,
   anchor, snippet}` where `snippet` is HTML (escaped, the query words in `<mark>`). Pure, for the
   tests. */
function search(payload, query, limit){
  var ws = words(query);
  if (!ws.length || !payload || !payload.pages) return [];
  var out = [];
  payload.pages.forEach(function(p, order){
    var title = String(p.title || "").toLowerCase(), summary = String(p.summary || "").toLowerCase();
    var best = null;
    (p.sections && p.sections.length ? p.sections : [{ h: "", a: "", t: "" }]).forEach(function(s){
      var head = String(s.h || "").toLowerCase(), text = String(s.t || "").toLowerCase();
      var score = 0, ok = true;
      ws.forEach(function(w){
        var at = function(hay){ var i = hay.indexOf(w); return i < 0 ? 0 : (i === 0 || /[^a-z0-9]/.test(hay.charAt(i - 1))) ? 2 : 1; };
        var a = at(title), b = at(head), c = at(summary), d = at(text);
        if (!(a || b || c || d)){ ok = false; return; }
        score += a * 6 + b * 3 + c * 1.5 + (d ? 0.5 + Math.min(text.split(w).length - 1, 6) * 0.15 : 0);
      });
      if (ok && (!best || score > best.score)) best = { score: score, s: s };
    });
    if (best) out.push({ score: best.score - order * 0.0001, p: p, s: best.s });
  });
  out.sort(function(a, b){ return b.score - a.score; });
  return out.slice(0, limit || 8).map(function(r){
    var inTitle = ws.every(function(w){ return String(r.p.title || "").toLowerCase().indexOf(w) >= 0; });
    var src = r.s.t && !(inTitle && !r.s.a) ? r.s.t : (r.p.summary || r.s.t || "");
    return { id: r.p.id, title: r.p.title, section: r.p.section || "", heading: r.s.h || "", anchor: r.s.a || "", snippet: snippet(src, ws) };
  });
}

function snippet(text, ws){
  text = String(text || "");
  var low = text.toLowerCase(), at = -1;
  ws.forEach(function(w){ var i = low.indexOf(w); if (i >= 0 && (at < 0 || i < at)) at = i; });
  var from = Math.max(0, at - 50), to = Math.min(text.length, Math.max(at, 0) + 130);
  if (from > 0){ var sp = text.indexOf(" ", from); if (sp > 0 && sp < at) from = sp + 1; }
  var cut = text.slice(from, to);
  var html = esc(cut);
  var re = new RegExp("(" + ws.map(function(w){ return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).sort(function(a, b){ return b.length - a.length; }).join("|") + ")", "gi");
  html = html.replace(re, "<mark>$1</mark>");
  return (from > 0 ? "… " : "") + html + (to < text.length ? " …" : "");
}

function searchRun(box, R){
  var input = box.querySelector("[data-dx-q]"), list = box.querySelector('[role="listbox"]');
  var q = input.value;
  var show = function(payload){
    if (input.value !== q) return;
    if (!words(q).length){ list.hidden = true; list.innerHTML = ""; input.setAttribute("aria-expanded", "false"); input.removeAttribute("aria-activedescendant"); return; }
    var hits = search(payload, q, 8);
    list.innerHTML = hits.length ? hits.map(function(h, i){
      return '<a role="option" id="' + list.id + "-" + i + '" aria-selected="' + (i === 0) + '" class="dx-sr-o" href="' + esc(ctxCall(R.ctx, "docHref", h.id) || "") + '" data-dx-hit="' + esc(h.id) + '" data-dx-anchor="' + esc(h.anchor) + '" tabindex="-1">' +
        "<small>" + esc(h.section) + (h.heading ? " › " + esc(h.heading) : "") + "</small><b>" + esc(h.title) + "</b><span>" + h.snippet + "</span></a>";
    }).join("") : '<p class="dx-sr-none">No page mentions <b>' + esc(q) + "</b>. Try a shorter word, or open the contents on the Docs home.</p>";
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    if (hits.length) input.setAttribute("aria-activedescendant", list.id + "-0"); else input.removeAttribute("aria-activedescendant");
  };
  if (R.searchData){ show(R.searchData); return; }
  var p;
  try { p = typeof R.ctx.search === "function" ? R.ctx.search() : null; } catch (e) { p = null; }
  if (p && typeof p.then === "function") p.then(function(d){ R.searchData = d; show(d); }, function(){ list.hidden = false; list.innerHTML = '<p class="dx-sr-none">Search could not be read. Try again in a moment.</p>'; });
  else { R.searchData = p || { pages: [] }; show(R.searchData); }
}

function searchClose(box){
  var input = box.querySelector("[data-dx-q]"), list = box.querySelector('[role="listbox"]');
  list.hidden = true;
  input.setAttribute("aria-expanded", "false");
  input.removeAttribute("aria-activedescendant");
}

/* Open a hit: the page by its link; the section once the page is drawn (`landPending`). A hit on
   the page already shown just scrolls. */
function searchOpen(el, hit){
  var anchor = hit.getAttribute("data-dx-anchor") || "";
  var here = el.querySelector("[data-dx-page]");
  if (here && here.getAttribute("data-dx-page") === hit.getAttribute("data-dx-hit")){
    var dest = anchor ? el.querySelector("#" + anchor) : here;
    if (dest && typeof dest.scrollIntoView === "function") dest.scrollIntoView({ block: "start" });
    return true;
  }
  D.pendingAnchor = anchor;
  return false;
}

function landPending(el){
  var anchor = D.pendingAnchor;
  if (!anchor) return;
  D.pendingAnchor = "";
  setTimeout(function(){
    var dest = el.querySelector("#" + anchor);
    if (dest && typeof dest.scrollIntoView === "function") dest.scrollIntoView({ block: "start" });
  }, 0);
}

function bindSearch(el, R){
  var boxes = el.querySelectorAll("[data-dx-search]");
  Array.prototype.forEach.call(boxes, function(box){
    var input = box.querySelector("[data-dx-q]"), list = box.querySelector('[role="listbox"]');
    input.addEventListener("input", function(){ searchRun(box, R); });
    input.addEventListener("focus", function(){ if (input.value) searchRun(box, R); });
    input.addEventListener("keydown", function(e){
      var opts = Array.prototype.slice.call(list.querySelectorAll('[role="option"]'));
      var cur = opts.filter(function(o){ return o.getAttribute("aria-selected") === "true"; })[0];
      var at = opts.indexOf(cur);
      if (e.key === "ArrowDown" || e.key === "ArrowUp"){
        if (!opts.length) return;
        e.preventDefault();
        var to = (at + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length;
        opts.forEach(function(o, i){ o.setAttribute("aria-selected", String(i === to)); });
        input.setAttribute("aria-activedescendant", opts[to].id);
        if (typeof opts[to].scrollIntoView === "function") opts[to].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter" && cur){
        e.preventDefault();
        if (searchOpen(el, cur)) searchClose(box); else location.href = cur.getAttribute("href");
      } else if (e.key === "Escape"){
        e.preventDefault();
        if (!list.hidden) searchClose(box); else { input.value = ""; input.blur(); }
      }
    });
    list.addEventListener("mousedown", function(e){ e.preventDefault(); });
    list.addEventListener("click", function(e){
      var hit = e.target && e.target.closest && e.target.closest("[data-dx-hit]");
      if (!hit) return;
      if (searchOpen(el, hit)){ e.preventDefault(); searchClose(box); }
    });
    input.addEventListener("blur", function(){ setTimeout(function(){ searchClose(box); }, 120); });
  });
}

/* `/` focuses the search box of whatever docs page is on screen, unless the reader is typing. */
if (typeof document !== "undefined" && document.addEventListener && !D.__slash){
  D.__slash = true;
  document.addEventListener("keydown", function(e){
    if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
    var a = document.activeElement;
    if (a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable)) return;
    var box = document.querySelector("[data-dx-search] [data-dx-q]");
    if (!box) return;
    e.preventDefault();
    box.focus();
  });
}

var UID = 0;
function state(ctx){ return { ctx: ctx || {}, uid: "dx" + (++UID), terms: 0, modes: 0, lives: [], errors: [] }; }

function pageHtml(page, R){
  var meta = page.meta || {};
  var doc = parse(page.body || "");
  var nodes = doc.nodes;
  var lede = nodes.filter(function(n){ return n.type === "block" && n.name === "lede"; })[0];
  var section = sectionOf(R.ctx.index, page.id);
  var home = ctxCall(R.ctx, "href", "docs") || "";
  /* The crumb names the JOB the page belongs to and links to it; a job page's crumb is Docs alone. */
  var inJob = section && section.id && section.id !== page.id;
  var crumbs = '<a href="' + esc(home) + '">Docs</a>' + (section && section.id !== page.id ? ' <span aria-hidden="true">›</span> ' +
    (inJob ? '<a href="' + esc(ctxCall(R.ctx, "docHref", section.id) || "") + '">' + esc(section.title) + "</a>" : "<span>" + esc(section.title) + "</span>") : "");
  var metaBits = [];
  if (meta.minutes) metaBits.push("<span><b>" + esc(meta.minutes) + " min</b> read</span>");
  var fw = forWords(meta["for"]);
  if (fw) metaBits.push("<span>" + esc(fw) + "</span>");
  if (KIND_WORD[meta.kind]) metaBits.push("<span>" + esc(KIND_WORD[meta.kind]) + "</span>");
  var heads = nodes.filter(function(n){ return n.type === "heading" && n.level === 2; });
  var article = nodesHtml(nodes, R);
  var rail = heads.length < 2 ? "" : '<nav class="dx-rail" aria-label="On this page"><p class="dx-rail-h">On this page</p><ol>' +
    heads.map(function(h){ return '<li><a href="#' + esc(h.id) + '" data-dx-jump="' + esc(h.id) + '">' + esc(plainText(h.text)) + "</a></li>"; }).join("") + "</ol></nav>";
  var pn = function(p, dir){
    if (!p) return "";
    var more = ctxCall(R.ctx, "page", p.id);
    return '<a class="dx-pn-c dx-pn-' + dir + '" href="' + esc(ctxCall(R.ctx, "docHref", p.id) || "") + '"><small>' + (dir === "prev" ? "← Previous" : "Next →") +
      "</small><b>" + esc(p.title) + "</b>" + (more && more.summary ? "<span>" + esc(more.summary) + "</span>" : "") + "</a>";
  };
  var prevNext = page.prev || page.next ? '<nav class="dx-pn" aria-label="Previous and next page">' + pn(page.prev, "prev") + pn(page.next, "next") + "</nav>" : "";
  return '<div class="dx" data-dx-page="' + esc(page.id || "") + '">' +
    heroHtml(meta.title || page.id || "Docs", crumbs, lede ? '<div class="dx-lede">' + mdRun(lede.text, R) + "</div>" : "", metaBits.join("")) +
    '<div class="dx-body' + (rail ? " dx-has-rail" : "") + '"><article class="dx-article">' + article + prevNext + "</article>" + rail + "</div></div>";
}

/* -- behaviour: one delegated listener per host element ------------------------------------- */

function closeTips(el, except){
  var open = el.querySelectorAll('[aria-expanded="true"]');
  for (var i = 0; i < open.length; i++){
    var b = open[i];
    if (b === except || !b.hasAttribute("data-dx-term")) continue;
    b.setAttribute("aria-expanded", "false");
    var tip = el.querySelector("#" + b.getAttribute("aria-controls"));
    if (tip) tip.textContent = "";
  }
}
function toggleTip(el, b){
  var tip = el.querySelector("#" + b.getAttribute("aria-controls"));
  var open = b.getAttribute("aria-expanded") === "true";
  closeTips(el, null);
  if (open || !tip) return;
  /* THE TEXT GOES IN ON OPEN, into a `role="status"` region, so a screen reader announces it; the
     region is emptied on close rather than hidden, so the next open is a change it announces again. */
  tip.innerHTML = "<b>" + esc(b.getAttribute("data-dx-word")) + "</b> " + esc(b.getAttribute("data-dx-def"));
  b.setAttribute("aria-expanded", "true");
}
function selectTab(el, tab, focus){
  var box = tab.closest("[data-dx-modes]");
  if (!box) return;
  var tabs = box.querySelectorAll("[data-dx-tab]");
  for (var i = 0; i < tabs.length; i++){
    var on = tabs[i] === tab;
    tabs[i].setAttribute("aria-selected", on ? "true" : "false");
    tabs[i].setAttribute("tabindex", on ? "0" : "-1");
    var p = box.querySelector("#" + tabs[i].getAttribute("aria-controls"));
    if (p) p.hidden = !on;
  }
  if (focus) tab.focus();
}

function bind(el){
  if (el.__fleetDocsBound) return;
  el.__fleetDocsBound = true;
  el.addEventListener("click", function(e){
    var t = e.target;
    if (!t || typeof t.closest !== "function") return;
    var term = t.closest("[data-dx-term]");
    if (term){ e.preventDefault(); toggleTip(el, term); return; }
    closeTips(el, null);
    var tab = t.closest("[data-dx-tab]");
    if (tab){ selectTab(el, tab, false); return; }
    var jump = t.closest("[data-dx-jump]");
    if (jump){
      var dest = el.querySelector("#" + jump.getAttribute("data-dx-jump"));
      /* AN IN-PAGE `#id` WOULD BE READ AS A ROUTE by a hash-routed app, so the rail scrolls rather
         than navigates — the href stays for a middle-click and for a reader with no script. */
      if (dest){
        e.preventDefault();
        var still = false;
        try { still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (x) { still = false; }
        if (typeof dest.scrollIntoView === "function") dest.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
      }
      return;
    }
    var copy = t.closest("[data-dx-copy]");
    if (copy){
      var text = copy.getAttribute("data-dx-copy");
      var done = function(word){ copy.textContent = word; setTimeout(function(){ copy.textContent = "Copy"; }, 1600); };
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function(){ done("Copied"); }, function(){ done("Copy failed"); });
        else done("Copy failed");
      } catch (x) { done("Copy failed"); }
    }
  });
  el.addEventListener("keydown", function(e){
    var t = e.target;
    if (!t || typeof t.closest !== "function") return;
    if (e.key === "Escape"){
      var open = Array.prototype.filter.call(el.querySelectorAll('[aria-expanded="true"]'), function(b){ return b.hasAttribute("data-dx-term"); })[0];
      if (open){ e.preventDefault(); closeTips(el, null); open.focus(); }
      return;
    }
    var term = t.closest("[data-dx-term]");
    if (term && (e.key === "Enter" || e.key === " ")){ e.preventDefault(); toggleTip(el, term); return; }
    var tab = t.closest("[data-dx-tab]");
    if (tab && (e.key === "ArrowRight" || e.key === "ArrowLeft" || e.key === "Home" || e.key === "End")){
      var all = tab.closest("[data-dx-modes]").querySelectorAll("[data-dx-tab]");
      var list = Array.prototype.slice.call(all), at = list.indexOf(tab);
      var to = e.key === "Home" ? 0 : e.key === "End" ? list.length - 1 : (at + (e.key === "ArrowRight" ? 1 : -1) + list.length) % list.length;
      e.preventDefault();
      selectTab(el, list[to], true);
    }
  });
}

/* Run every deferred read, and fill its element when it answers — unless the host has drawn
   another page into `el` since, which is what the generation guards. */
function fillLater(el, R){
  var gen = el.__fleetDocsGen;
  R.lives.forEach(function(l){
    var settle = function(v, failed){
      if (el.__fleetDocsGen !== gen) return;
      var node = el.querySelector('[data-dx-live="' + l.key + '"]');
      if (!node) return;
      var html = l.fill(v, failed);
      if (html === null){
        /* a diagram whose slice is unknown keeps its generic labels, quietly: the diagram still
           teaches without the example, and a line about a missing slice is noise to a reader */
        node.removeAttribute("aria-busy");
        return;
      }
      node.innerHTML = html;
      node.removeAttribute("aria-busy");
    };
    var p;
    try { p = typeof R.ctx.live === "function" ? R.ctx.live(l.kind, l.id) : null; } catch (e) { settle(null, true); return; }
    if (p && typeof p.then === "function") p.then(function(v){ settle(v || null, false); }, function(){ settle(null, true); });
    else settle(p || null, false);
  });
}

/* `render(el, page, ctx)` — draw one docs page into `el`. Returns the parse errors and the inline
   errors (unknown terms, missing pages) the render met, so a preview can list them. */
function render(el, page, ctx){
  var R = state(ctx);
  R.page = page || {};
  markRead(R.page.id);
  el.__fleetDocsGen = (el.__fleetDocsGen || 0) + 1;
  var html = pageHtml(page || {}, R);
  el.innerHTML = html;
  hangEmbeds(el, R);
  bind(el);
  bindSearch(el, R);
  fillLater(el, R);
  landPending(el);
  return { errors: parse((page && page.body) || "").errors.concat(R.errors) };
}

/* THE PICTURE ON A JOB CARD, one per job page's `icon:` — line drawings in the text colour. */
var ICONS = {
  understand: '<circle cx="10" cy="10" r="7"/><circle cx="10" cy="10" r="2.5"/>',
  daily: '<rect x="3" y="4" width="14" height="12" rx="2"/><path d="M6 8h8M6 11h5"/>',
  plan: '<rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><path d="M11 14h6"/>',
  knowledge: '<path d="M3 5.5A1.5 1.5 0 014.5 4H8l2 2h5.5A1.5 1.5 0 0117 7.5v7a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 013 14.5z"/>',
  sessions: '<rect x="2.5" y="4" width="15" height="12" rx="2"/><path d="M6 9l2.5 2L6 13M10.5 13H14"/>',
  tools: '<path d="M12.5 3.5a3.5 3.5 0 00-3.3 4.7L3.8 13.6a1.4 1.4 0 002 2l5.4-5.4a3.5 3.5 0 004.4-4.4l-2.1 2.1-2-.4-.4-2z"/>',
  team: '<circle cx="7" cy="7" r="2.6"/><circle cx="14" cy="8" r="2.1"/><path d="M2.5 16c.6-2.6 2.4-4 4.5-4s3.9 1.4 4.5 4M12 12.4c2.3-.4 4.4.8 5.2 3.6"/>',
  quality: '<path d="M10 2.8l6 2.4v4.3c0 3.7-2.6 6.4-6 7.7-3.4-1.3-6-4-6-7.7V5.2z"/><path d="M7.3 10l1.9 1.9 3.7-3.8"/>',
  fix: '<path d="M10 3L2.5 16h15z"/><path d="M10 8v3.5M10 13.6v.2"/>'
};
function icon(name){
  return '<svg class="dx-ico" viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + (ICONS[name] || ICONS.understand) + "</svg>";
}

/* WHAT THIS BROWSER HAS READ, so the home can show how far into each job a reader is. Kept per
   viewer in `localStorage`; a browser that refuses storage just shows every job unread. */
var READ_KEY = "fleet.docs.read";
function readIds(){
  try { var v = JSON.parse(window.localStorage.getItem(READ_KEY) || "[]"); return Array.isArray(v) ? v : []; } catch (e) { return []; }
}
function markRead(id){
  if (!id) return;
  try {
    var v = readIds();
    if (v.indexOf(id) < 0){ v.push(id); window.localStorage.setItem(READ_KEY, JSON.stringify(v.slice(-400))); }
  } catch (e) { /* storage refused: progress is a convenience, never a requirement */ }
}

/* `renderHome(el, index, ctx)` — the Docs home. NOT A LIST OF PAGES: a big search; the `learn`
   jobs drawn large, each with the picture of what it explains — that is the newcomer's way in;
   then the `use` and `run` jobs as one row each. Every card names ONE first read and how far
   this browser has got along the job's path. Then the tasks people come for most, one click
   each, and the generated reference, out of the way. An index with no jobs is drawn the old
   way: each section as a grid of cards. */
function renderHome(el, index, ctx){
  var R = state(ctx);
  el.__fleetDocsGen = (el.__fleetDocsGen || 0) + 1;
  var ix = index || {};
  var href = function(id){ return esc(ctxCall(R.ctx, "docHref", id) || ""); };
  var body;
  if (ix.jobs && ix.jobs.length){
    var read = readIds();
    var start = function(j){
      var p = (j.path || [])[0];
      return p ? '<span class="dx-hj-start">Start: <b>' + esc(p.title) + "</b>" + (p.minutes ? " · " + esc(p.minutes) + " min" : "") + ' <i aria-hidden="true">→</i></span>' : "";
    };
    var progress = function(j){
      var path = j.path || [];
      var done = path.filter(function(p){ return read.indexOf(p.id) >= 0; }).length;
      var word = done ? done + " of " + path.length + " read" : path.length + (path.length === 1 ? " step" : " steps") + " · " + j.count + (j.count === 1 ? " page" : " pages");
      return '<span class="dx-hj-prog">' + path.map(function(p){ return '<i class="' + (read.indexOf(p.id) >= 0 ? "on" : "") + '"></i>'; }).join("") + "<em>" + esc(word) + "</em></span>";
    };
    var text = function(j){
      return '<b class="dx-hj-n">' + esc(j.title) + '</b><span class="dx-hj-s">' + esc(j.summary || "") + "</span>" + start(j) + progress(j);
    };
    var of = function(g){ return ix.jobs.filter(function(j){ return (j.group || "use") === g; }); };
    var learn = of("learn").map(function(j){
      var pic = MINI[j.icon];
      return '<a class="dx-hj dx-hj-big dx-g-learn" href="' + href(j.id) + '"><div class="dx-hj-t"><span class="dx-hj-i">' + icon(j.icon) +
        '</span><div><small class="dx-hj-g">Learn</small>' + text(j) + "</div></div>" + (pic ? '<div class="dx-hj-pic" aria-hidden="true">' + pic() + "</div>" : "") + "</a>";
    }).join("");
    var group = function(g, title){
      var js = of(g);
      return js.length ? '<section class="dx-hg dx-g-' + g + '"><h2 class="dx-hg-h"><span aria-hidden="true"></span>' + esc(title) + '</h2><div class="dx-hg-l" style="--n:' + js.length + '">' +
        js.map(function(j){ return '<a class="dx-hj" href="' + href(j.id) + '"><span class="dx-hj-i">' + icon(j.icon) + "</span>" + text(j) + "</a>"; }).join("") + "</div></section>" : "";
    };
    var row = function(title, sub, items, cls){
      return items.length ? '<div class="dx-row"><h3>' + esc(title) + (sub ? "<em>" + esc(sub) + "</em>" : "") + '</h3><div class="dx-chips' + (cls ? " " + cls : "") + '">' +
        items.map(function(c){ return '<a href="' + href(c.id) + '">' + esc(c.label || c.title) + "</a>"; }).join("") + "</div></div>" : "";
    };
    body = (learn ? '<div class="dx-hl">' + learn + "</div>" : "") + group("use", "Use Fleet") + group("run", "Run Fleet") +
      row("Common tasks", "", ix.common || [], "") + row("Reference", "generated from the code", ix.reference || [], "dx-chips-q");
  } else {
    body = (ix.sections || []).map(function(s){
      return '<section class="dx-home-s"><h2 class="dx-h dx-h2">' + esc(s.title) + '</h2><div class="dx-home-g">' +
        (s.pages || []).map(function(p){
          return '<a class="dx-card" href="' + href(p.id) + '"><b>' + esc(p.title) + "</b><span>" + esc(p.summary || "") + "</span></a>";
        }).join("") + "</div></section>";
    }).join("") || '<p class="dx-note">No pages yet.</p>';
  }
  var summary = "Find the page for what you're trying to do, or search everything.";
  el.innerHTML = '<div class="dx dx-home">' + heroHtml(ix.title || "Fleet docs", "", '<div class="dx-lede"><p class="md-p">' + esc(summary) + "</p></div>", "", true) +
    '<div class="dx-body"><div class="dx-article dx-home-a">' + body + "</div></div></div>";
  bind(el);
  bindSearch(el, R);
  return { errors: [] };
}

/* THE PICTURE ON A LARGE `learn` CARD, by the job's icon. Fixed drawings of what the job explains,
   never live data: the home must draw before anything is read. */
var MINI = {
  /* The work line: you file, Fleet builds and a second session verifies — AS A LOOP, because a
     failed verify goes back to build until every claim holds — then it merges. */
  understand: function(){
    var n = function(who, t){ return '<span class="dx-nm dx-nm-' + who + '">' + esc(t) + "</span>"; };
    var cyc = '<svg class="dx-nm-cyc" viewBox="0 0 48 32" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M10 11C16 3 32 3 38 11"/><path d="M34.5 7.5L38.4 11.3 33.3 12.4"/><path d="M38 21C32 29 16 29 10 21"/><path d="M13.5 24.5L9.6 20.7 14.7 19.6"/></svg>';
    return '<div class="dx-nm-row">' + n("you", "You file") + "<i>→</i>" +
      '<div class="dx-nm-loop">' + n("fleet", "Build") + cyc + n("fleet", "Verify") + "<em>until every claim holds</em></div>" +
      "<i>→</i>" + n("nobody", "Merged") + '</div><div class="dx-nm-base"><span>Knowledge base</span><span>Machines and seats</span><span>Your tools</span></div>';
  },
  /* The knowledge folder at a glance: the three things it holds, three examples each. */
  knowledge: function(){
    var col = function(h, items){ return "<div><small>" + esc(h) + "</small>" + items.map(function(t){ return '<span class="' + (t[1] || "") + '">' + esc(t[0]) + "</span>"; }).join("") + "</div>"; };
    return '<div class="dx-km-mini">' + col("Planning", [["Feature", "a"], ["Slice", "s"], ["PRD", "p"]]) +
      col("The product", [["Capabilities"], ["Journeys"], ["Promises"]]) + col("Your repository", [["Slots"], ["Records"], ["Decisions"]]) + "</div>";
  }
};

D.parse = parse;
D.render = render;
D.renderHome = renderHome;
D.search = search;
D.pendingAnchor = "";
/* for the tests and for `docs-screens.js`: the catalogue as the parser reads it */
D.blocks = BLOCKS;
})();

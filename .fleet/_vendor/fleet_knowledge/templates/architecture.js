/* The architecture page — one repository's component registry, drawn as the diagram.
 *
 * `board.js` renders the corpus as LISTS (programs, requirements, decisions); this file renders
 * the same corpus's component registry as the DIAGRAM its registry is written for: layers as
 * bands, the two build-and-run stacks as a duo, the backbone beside all of it, and an outcome
 * axis on top. The visual reference is the generated page this view replaces
 * (`a prior checkout`'s `scripts/gen_architecture_diagram.py`) — bands, duo columns, rail, cards, the
 * per-layer counts, the three coverage states and the info modal are ports of that renderer's
 * behaviour, redrawn in this app's idiom and from this app's tokens. Nothing here inlines a
 * colour: `fleet.css`'s tokens are the palette (that was decision D2, and it is why no token is
 * declared in `architecture.css` either).
 *
 * THE SEAM IS THE SAME ONE `board.js` KEEPS. This file is `fleet-knowledge`'s and must not
 * learn a URL: `start()` takes the two reads from the host — `load` for the whole payload and
 * `loadProse` for one component's long-form description — and spells nothing but the shapes.
 * The deployed app points them at `GET /api/architecture?repo=<lane>` and the EXISTING
 * `GET /api/knowledge/component/{id}/prose`; the standalone board does not load this file at
 * all, so `fleet board` is untouched.
 *
 * THE PAYLOAD CARRIES NO PROSE, and that is the API doctrine rather than a convenience: a
 * page payload with every component's document in it is the cost this surface is arranged not
 * to pay. The one-liner rides the payload; the long-form is fetched on CLICK, into a modal
 * that is already on screen — the same "the body is fetched after the page is on screen"
 * discipline the knowledge views keep.
 *
 * WHAT DEGRADES, AND HOW. A corpus with no registry renders an empty state, never a 500. An
 * authored layout that names a layer the registry does not declare loses that one placement —
 * a band is skipped, a duo row keeps its known members, a column of nothing is dropped — and
 * if what is left draws nothing at all, the page falls back to the generic bands rather than
 * blank-paging. The validator (`checks/planning/components.py`) refuses these files at sync
 * time; the degrade is for readings that predate it.
 */

window.Architecture = (function(){
"use strict";

/* The two reads, handed in by the host. Without them the page says so rather than pretending. */
let ROUTE = "arch";
let LOAD = null;
let PROSE = null;

/* Where the read has got to — the same three-plus-one states every view here renders. */
let STATE = "cold";           /* cold | loading | ready | failed */
let DETAIL = "";
let DATA = null;
let LYR = {};                 /* layer id -> {name, description}, from DATA.layers */
/* The repository the read in hand was made for; `pace`'s arrival mark is repo + route, so a
   repository switch re-reads and nothing else does. */
let SEEN = "";

/* The info modal. `OPEN` is the card it is on; `SRC` is the "show source detail" toggle. Both
   are state, not DOM: the modal is part of the view's markup, so a repaint cannot strand one. */
let OPEN = null;              /* {id, kind} */
let SRC = false;

/* ONE PROSE CACHE, KEYED BY REPOSITORY. A modal re-opened within a repository costs nothing;
   a component read under repository A is never served for repository B. */
const PROSE_CACHE = new Map();

/* THE LAYERS THAT HOLD NO COMPONENTS — the outcome axis and the customer's own data. This is
   `fleet-knowledge`'s `checks/planning/_config.py: non_component_layers`, spelled here because
   the generic fallback reads it: a layer from that set draws its own axis's rows (outcomes /
   external) and never a components band, exactly as the reference generator hard-coded its two
   ids. The validator refuses a component that SITS in one of these layers, so a row here is
   never a card in the component sense. */
const NON_COMPONENT_LAYERS = ["business-value", "customer-data"];

/* The accent words an authored layout may spend. An allow-list, not a pass-through: authored
   data does not get to mint class names on this page, and a word outside the list degrades to
   the plain band rather than arriving in the DOM. Each maps to one rule in `architecture.css`. */
const STYLES = new Set(["agent", "brand", "gnd", "value", "seal", "core", "edge"]);

const INFO_SVG =
  '<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" focusable="false">' +
  '<circle cx="8" cy="8" r="6.6" fill="none" stroke="currentColor" stroke-width="1.3"/>' +
  '<circle cx="8" cy="4.9" r="0.95" fill="currentColor"/>' +
  '<path d="M8 7.2v4.2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>' +
  "</svg>";

/* THE PROVENANCE LABELS, in the words the reference modal used. The prose response names the
   file it was resolved from and nothing else, so the label is read off that file's shape — the
   three paths the resolver writes are conventional (`components/<id>.md`, `features/*.md`,
   `components.md`), and a shape it does not recognise leaves the path alone to say it. */
const PROV_COMPONENT = "Component detail";
const PROV_FEATURE = "From the feature — a customer-facing capability map, not the subsystem itself";
const PROV_REGISTRY = "No long-form description written yet — this is the registry one-liner";

/* ── the seam ──────────────────────────────────────────────────────────────── */

function start(opts){
  const o = opts || {};
  ROUTE = String(o.route || ROUTE);
  LOAD = o.load || null;
  PROSE = o.loadProse || null;
  /* DELEGATED, ONCE, LIKE EVERY LISTENER ON THIS PAGE. The controls are re-rendered with the
     view; the listener is not. */
  document.addEventListener("click", onClick);
  document.addEventListener("keydown", onKey);
}

/* ── the read ──────────────────────────────────────────────────────────────── */

/* CALLED AFTER EVERY RENDER, by the host's route hook. Arrival semantics: the mark is the
   repository plus the route kind, so entering the page reads, navigating away and back does
   not, and picking another repository re-reads the moment the page is on screen. A failed read
   stays failed until its own Try again — the same answer the Stats page gives. */
function pace(route){
  const kind = String(route || "").split(":")[0];
  if (kind !== ROUTE) return;
  const mark = Board.repo() + "|" + kind;
  if (mark === SEEN && STATE !== "cold") return;
  SEEN = mark;
  read();
}

function read(){
  if (!LOAD) return;
  const atSend = SEEN;
  STATE = "loading";
  DETAIL = "";
  OPEN = null;
  paint();
  LOAD(Board.repo()).then(payload => {
    if (atSend !== SEEN) return;   /* a newer question is in flight; its answer is the one to paint */
    boot(payload);
    STATE = "ready";
    paint();
  }, err => {
    if (atSend !== SEEN) return;
    STATE = "failed";
    DETAIL = err && err.message ? String(err.message) : String(err);
    paint();
  });
}

/* THE PAYLOAD, NORMALISED ONCE. Every field below this line is read off these shapes, so an
   absent list is an empty one here rather than a guard at every use. */
function boot(payload){
  DATA = payload && typeof payload === "object" ? payload : {};
  LYR = {};
  rows("layers").forEach(l => {
    if (!l || l.id == null) return;
    LYR[String(l.id)] = {
      name: l.name != null && String(l.name) !== "" ? String(l.name) : String(l.id),
      description: l.description != null ? String(l.description) : "",
    };
  });
}

function rows(name){
  return Array.isArray(DATA && DATA[name]) ? DATA[name] : [];
}

/* Registry order, when the rows carry positions — the contract names one on every axis. */
function ordered(list){
  if (list.length > 1 && list.every(r => r && typeof r.position === "number")){
    list.sort((a, b) => a.position - b.position);
  }
  return list;
}

/* ── the view ──────────────────────────────────────────────────────────────── */

function view(){
  if (STATE !== "ready"){
    return Board.pageHead("Architecture") +
      (STATE === "failed"
        ? `<div class="banner"><b>The component registry could not be read</b> &mdash; ${Board.esc(DETAIL)}</div>` +
          `<div class="live"><button class="act" data-arch-retry>Try again</button></div>`
        : `<p class="empty-note">Drawing the architecture&hellip;</p>`);
  }
  if (registryEmpty()){
    return Board.pageHead("Architecture") +
      `<p class="empty-note">This repository carries no component registry &mdash; nothing has been
        declared for the architecture page to draw.</p>`;
  }
  const authored = readLayout();
  let placements = placedFromLayout(authored).filter(Boolean);
  /* AN AUTHORED LAYOUT THAT DREW NOTHING IS NO LAYOUT. Every placement it named was unknown to
     the registry, or the file held none — either way the generic bands are the honest page, and
     a blank one is the failure a diagram exists to prevent. An axis band over an empty axis
     degrades to "" too, so the filter is what makes "drew nothing" mean anything at all. */
  if (!placements.length) placements = placedFromLayers().filter(Boolean);
  if (!placements.length){
    return Board.pageHead("Architecture") +
      `<p class="empty-note">The registry declares no layers &mdash; nothing to draw yet.</p>`;
  }
  return page(placements, authored);
}

function registryEmpty(){
  return !rows("layers").length && !rows("components").length &&
    !rows("external").length && !rows("outcomes").length;
}

/* The authored file, as the sync parsed it — or null, which is the generic fallback's cue.
   ONE ORDERED SEQUENCE OF PLACEMENTS, and the document order IS the draw order: a band and a
   duo are two `kind`s of the same array, so a layout that wants its build-and-run stacks
   mid-stack says so by position, and the renderer reads the file top to bottom exactly once. */
function readLayout(){
  const l = DATA.layout;
  if (!l || typeof l !== "object" || Array.isArray(l)) return null;
  return {
    diagram: l.diagram && typeof l.diagram === "object" ? l.diagram : {},
    placements: Array.isArray(l.placement) ? l.placement.filter(p => p && typeof p === "object") : [],
  };
}

/* THE THESIS STANDFIRST — markdown marks AND a small inline-HTML allowlist.
   The layout schema says `thesis (may carry inline HTML)`; the seeded diagram-layout.toml
   authors `<b>` for emphasis. Board.mdown escapes first and re-activates only the three
   markdown marks, so an authored bare `<b>` would print as literal text (ENG-10812). Restore
   the allowlist AFTER mdown: tags outside the set stay escaped, attributes on an allowlisted
   name stay escaped (the pattern matches bare names only), and title / band tag / count stay
   plain text — this channel is the thesis alone. */
const THESIS_INLINE = /&lt;(\/?)(b|i|em|strong|code)&gt;/gi;
function thesisHtml(s){
  return Board.mdown(s).replace(THESIS_INLINE, "<$1$2>");
}

function page(placements, authored){
  const d = (authored && authored.diagram) || {};
  const title = d.title != null && String(d.title) !== "" ? String(d.title) : "Architecture";
  const thesis = d.thesis != null ? String(d.thesis) : "";
  const head = `<h1>${Board.esc(title)}</h1>` + Board.pageHead(title, thesis ? thesisHtml(thesis) : "");
  const stack = `<div class="arch-stack">${placements.join("")}</div>`;
  const rail = railHtml(authored);
  return head + keyBar() +
    (rail ? `<div class="arch-plate">${stack}${rail}</div>` : stack) +
    footHtml() + modalHtml();
}

/* THE KEY, AND THE ONE TOGGLE THIS PAGE OWNS. The swatches are the three coverage states; the
   toggle reveals which paths each component owns. A checkbox would need a control rule this
   stylesheet does not have; the app's own button vocabulary says the same thing and is already
   here. `data-keep` is the repaint's focus anchor — a keyboard user toggling does not lose
   their place when the page repaints. */
function keyBar(){
  return `<div class="arch-bar"><div class="arch-keys">` +
    `<span class="arch-k"><span class="arch-sw"></span> Built</span>` +
    `<span class="arch-k"><span class="arch-sw arch-t"></span> Planned, not yet built</span>` +
    `<span class="arch-k"><span class="arch-sw arch-new"></span> Proposed — code exists, no component</span>` +
    `<span class="arch-k">${INFO_SVG} Click for detail</span>` +
    `</div><button class="act" data-arch-src data-keep="arch-src" aria-pressed="${SRC ? "true" : "false"}">Show source detail</button></div>`;
}

/* ── placements: the authored layout, then the generic fallback ────────────── */

function placedFromLayout(authored){
  if (!authored) return [];
  const out = [];
  authored.placements.forEach(p => {
    /* ONE PASS, IN DOCUMENT ORDER. A `duo` renders its columns; anything else is a band, and
       a placement that is neither — a kind the renderer does not spell, or no kind at all —
       loses its slot: the validator refuses such a file at sync time, and the degrade here is
       for readings that predate it. */
    if (p.kind === "duo"){
      const html = duoHtml(p);
      if (html) out.push(html);
      return;
    }
    if (p.kind !== "band") return;
    const id = String(p.layer || "");
    /* An UNKNOWN LAYER LOSES ITS BAND, not the page. The heading would name a layer the
       registry does not declare, and the box would draw nothing that exists. */
    if (!LYR[id]) return;
    out.push(bandHtml({
      layer: id,
      style: p.style,
      tag: p.tag,
      source: p.source,
      count: p.count,
    }));
  });
  return out;
}

/* NO AUTHORED LAYOUT: one full-width band per declared layer, in `position` order. The two
   non-component layers draw their own axes — outcomes and external — detected the way the
   reference detected them, by the ids in `non_component_layers`. */
function placedFromLayers(){
  return ordered(rows("layers").slice())
    .map(l => String(l.id))
    .filter(id => !!LYR[id])
    .map(id => {
      if (id === NON_COMPONENT_LAYERS[0]) return bandHtml({ layer: id, source: "outcomes", style: "value" });
      if (id === NON_COMPONENT_LAYERS[1]) return bandHtml({ layer: id, source: "external", style: "edge" });
      return bandHtml({ layer: id });
    });
}

/* ── a band: one layer, its tag, its counts, its cards ─────────────────────── */

function bandHtml(b){
  const meta = LYR[b.layer] || { name: String(b.layer), description: "" };
  const source = b.source === "outcomes" || b.source === "external" ? b.source : "components";
  const kind = source;
  const members = ordered((source === "components"
    ? rows("components").filter(c => c && String(c.layer) === String(b.layer))
    : rows(source)).slice());
  /* An AXIS WITH NOTHING ON IT IS NOT DRAWN. A business-value band over an empty outcomes
     table would assert a structure that does not exist; a declared COMPONENT layer with no
     rows yet is still structure, and renders as an empty band with its description. */
  if (source !== "components" && !members.length) return "";
  const style = styleClasses(b.style);
  const tag = b.tag != null && String(b.tag) !== ""
    ? `<span class="arch-tag">${Board.esc(String(b.tag))}</span>` : "";
  const count = b.count != null && String(b.count) !== ""
    ? Board.esc(String(b.count)) : counts(members, source);
  return `<section class="arch-l${style}">` +
    `<div class="arch-lh"><h3>${Board.esc(meta.name)}</h3>${tag}<span class="arch-n">${count}</span></div>` +
    (meta.description ? `<p class="arch-ld">${Board.esc(meta.description)}</p>` : "") +
    `<div class="arch-cards">${members.map(m => cardHtml(m, kind)).join("")}</div>` +
    `</section>`;
}

function duoHtml(duo){
  const cols = ((duo && Array.isArray(duo.columns)) ? duo.columns : []).map(col => {
    if (!col || typeof col !== "object") return "";
    /* A row keeps its KNOWN members and loses the rest; a column whose every row degraded away
       is dropped whole. What is left is still the pairing the file drew. */
    const kept = (Array.isArray(col.rows) ? col.rows : [])
      .map(row => (Array.isArray(row) ? row : []).map(String).filter(id => !!LYR[id]))
      .filter(row => row.length);
    if (!kept.length) return "";
    const accent = col.accent != null && STYLES.has(String(col.accent)) ? String(col.accent) : "";
    const body = kept.map(row => row.length > 1
      ? `<div class="arch-pair">${row.map(id => bandHtml({ layer: id, style: accent })).join("")}</div>`
      : bandHtml({ layer: row[0], style: accent })).join("");
    return `<div class="arch-col">` +
      `<p class="arch-cap${accent ? " arch-" + accent : ""}"><i></i>${Board.esc(String(col.caption || ""))}</p>` +
      body + `</div>`;
  }).filter(Boolean);
  if (!cols.length) return "";
  return `<div class="arch-duo">${cols.join("")}</div>`;
}

function railHtml(authored){
  if (!authored) return "";
  const ids = (Array.isArray(authored.diagram.rail_layers) ? authored.diagram.rail_layers : [])
    .map(String).filter(id => !!LYR[id]);
  if (!ids.length) return "";
  const cap = authored.diagram.rail_caption != null ? String(authored.diagram.rail_caption) : "";
  return `<aside class="arch-rail">` +
    (cap ? `<p class="arch-railcap">${Board.esc(cap)}</p>` : "") +
    ids.map(id => bandHtml({ layer: id })).join("") +
    `</aside>`;
}

/* Authored style words to classes — allow-listed at the read, so this is only the spelling. */
function styleClasses(raw){
  return String(raw || "").split(/\s+/).filter(w => STYLES.has(w)).map(w => " arch-" + w).join("");
}

/* ── cards, counts, and the three coverage states ──────────────────────────── */

/* Built / planned-not-built / proposed — the reference generator's `state_of()`, one branch
   lighter: its exception for the two non-component layers does not port because those axes
   render from their own arrays here and the validator refuses components that sit in them.
   A component with NO owned paths is planned — the registry describing work, with nothing
   to point at in the tree. */
function stateOf(c){
  if (c.proposed) return "new";
  const owns = c.owns || [];
  if (!owns.length || !(c.present || []).length) return "t";
  return "";
}

function counts(members, source){
  if (source !== "components"){
    return members.length === 1 ? "1 item" : members.length + " items";
  }
  let built = 0, planned = 0, proposed = 0;
  members.forEach(m => {
    const s = stateOf(m);
    if (s === "new") proposed += 1;
    else if (s === "t") planned += 1;
    else built += 1;
  });
  const bits = [];
  if (built) bits.push(built + " built");
  if (planned) bits.push(planned + " planned");
  if (proposed) bits.push(proposed + " proposed");
  return bits.join(" &middot; ") || (members.length === 1 ? "1 item" : members.length + " items");
}

function cardHtml(c, axis){
  const comp = axis === "components";
  const st = comp ? stateOf(c) : "";
  const name = c.name != null && String(c.name) !== "" ? String(c.name) : String(c.id);
  /* THE SOURCE LINE IS THE TOGGLE'S SUBJECT — hidden until asked for, and only for components,
     whose owns paths are the thing it exists to show. */
  const src = comp && SRC && (c.owns || []).length
    ? `<p class="arch-src"><b>${Board.esc(String(c.id))}</b> &middot; ` +
      c.owns.map(p => Board.esc(String(p))).join(" &middot; ") + `</p>`
    : "";
  return `<article class="arch-c${st ? " arch-" + st : ""}">` +
    `<h4><span class="arch-d"></span><span class="arch-nm">${Board.esc(name)}</span>` +
    `<button class="arch-i" data-arch="${Board.esc(String(c.id))}" ` +
    `aria-label="About ${Board.esc(name)}">${INFO_SVG}</button></h4>` +
    (c.description ? `<p class="arch-cd">${Board.esc(String(c.description))}</p>` : "") +
    src + `</article>`;
}

/* ── the page's own record: what this reading is, and what its coverage is ─── */

function footHtml(){
  const comps = rows("components");
  const proposed = comps.filter(c => c && c.proposed).length;
  const built = comps.filter(c => c && !c.proposed && (c.present || []).length).length;
  return `<footer class="arch-foot">Drawn from the component registry at commit ` +
    `<code>${Board.esc(String(DATA.commit || "unknown"))}</code>. ` +
    `${comps.length - proposed} components (${built} owning code today) plus ${proposed} proposed. ` +
    `Coverage is <b>derived, never stored</b> &mdash; a point-in-time reading of which owned paths ` +
    `resolve in the tree, and never ship-state. A component is durable and can never be finished; ` +
    `only a project ships.</footer>`;
}

/* ── the info modal ────────────────────────────────────────────────────────── */

/* ONE LOOKUP FOR THE MODAL, ACROSS ALL THREE AXES. The card names only its id — which array
   held it is this file's own fact, derived here rather than spelled a second time onto every
   card. Component ids come first: they are the axis the prose read hangs on, and the one a
   collision would be ambiguous about. */
const KIND_OF_AXIS = { components: "component", outcomes: "outcome", external: "external" };

function findCard(id){
  const axis = ["components", "outcomes", "external"].find(name =>
    rows(name).some(c => c && String(c.id) === String(id)));
  return axis ? { card: rows(axis).find(c => c && String(c.id) === String(id)), kind: KIND_OF_AXIS[axis] } : null;
}

function modalHtml(){
  if (!OPEN) return "";
  const found = findCard(OPEN.id);
  if (!found) return "";   /* the reading moved under an open modal; the next read closes it */
  const c = found.card;
  /* The axis is WRITTEN BACK, not just read: the helpers below read `OPEN.kind`, and after a
     payload swap under an open modal the current reading, not the click's, is the truth. */
  OPEN.kind = found.kind;
  const name = c.name != null && String(c.name) !== "" ? String(c.name) : String(c.id);
  const layer = found.kind === "outcome" ? "Outcome"
    : found.kind === "external" ? "External"
    : (LYR[String(c.layer)] ? LYR[String(c.layer)].name : String(c.layer || ""));
  return `<div class="arch-modal" role="dialog" aria-modal="true" aria-label="About ${Board.esc(name)}">` +
    `<div class="arch-modal-back" data-arch-close></div>` +
    `<div class="arch-modal-card">` +
    `<div class="arch-m-head"><div>` +
    `<p class="arch-m-layer">${Board.esc(layer)}</p>` +
    `<h2 class="arch-m-name">${Board.esc(name)}</h2></div>` +
    `<button class="ipx" data-arch-close aria-label="Close">&times;</button></div>` +
    `<p class="arch-m-one">${Board.esc(String(c.description || ""))}</p>` +
    `<div class="arch-m-long">${modalLong(c)}</div>` +
    modalPaths(c) +
    modalSource(c) +
    `</div></div>`;
}

/* THE LONG-FORM, fetched after the modal is on screen. An outcome's or an external system's
   one-liner IS its text — there is no detail tier behind those axes, so nothing is asked. */
function modalLong(c){
  if (OPEN.kind !== "component") return "";
  const got = PROSE_CACHE.get(proseKey(Board.repo(), String(c.id)));
  if (!got || got.phase === "loading"){
    return `<p class="arch-m-wait">Reading the long-form description&hellip;</p>`;
  }
  if (got.phase === "failed"){
    return `<p class="arch-m-wait arch-m-bad">The long-form description could not be read: ${Board.esc(got.error)}</p>`;
  }
  return (got.blocks || []).map(b =>
    `<p class="arch-m-lab">${Board.esc(String(b && b.title || ""))}</p>${mdProse(b && b.body)}`
  ).join("");
}

/* THE PORT OF `md_prose` — with the escaping borrowed from the house instead of re-written.
   Blank lines split paragraphs; `code`, `**bold**` and `*em*` are read inline; everything else
   is text. Board.mdown escapes FIRST and reads the marks second, and it resolves an id in
   prose to the destination the corpus's lists already link — the same rule the knowledge
   narrative keeps. */
function mdProse(s){
  return String(s == null ? "" : s)
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => `<p>${Board.mdown(p)}</p>`)
    .join("");
}

function modalPaths(c){
  if (OPEN.kind === "outcome"){
    const by = Array.isArray(c.realized_by) ? c.realized_by
      : c.realized_by != null && String(c.realized_by) !== "" ? [c.realized_by] : [];
    if (!by.length) return "";
    return `<p class="arch-m-lab">Realized by</p>` +
      `<p class="arch-m-paths">${by.map(x => Board.esc(String(x))).join(" &middot; ")}</p>`;
  }
  if (OPEN.kind !== "component" || !(c.owns || []).length) return "";
  const present = c.present || [];
  return `<p class="arch-m-lab">Owns${c.proposed ? " (proposed)" : ""}</p><ul class="arch-m-paths">` +
    c.owns.map(p => `<li class="${present.includes(p) ? "ok" : "missing"}">${Board.esc(String(p))}</li>`).join("") +
    `</ul>`;
}

function modalSource(c){
  if (OPEN.kind !== "component") return "";
  const got = PROSE_CACHE.get(proseKey(Board.repo(), String(c.id)));
  if (!got || got.phase !== "ready") return "";
  const source = got.source || "";
  const fallback = !(got.blocks || []).length;
  const label = fallback ? PROV_REGISTRY : provOf(source);
  return `<p class="arch-m-src${fallback ? " arch-m-registry" : ""}">` +
    (label ? Board.esc(label) + (source ? " &middot; " : "") : "") +
    Board.esc(source) + `</p>`;
}

function provOf(source){
  const s = String(source || "");
  if (/(^|\/)components\/[^/]+\.md$/.test(s)) return PROV_COMPONENT;
  if (/(^|\/)features\//.test(s)) return PROV_FEATURE;
  if (/(^|\/)components\.md$/.test(s)) return PROV_REGISTRY;
  return "";
}

/* ── the prose read ────────────────────────────────────────────────────────── */

function proseKey(repo, id){
  return String(repo) + "\u001f" + String(id);
}

function wantProse(id){
  const key = proseKey(Board.repo(), id);
  if (PROSE_CACHE.has(key)) return;   /* asked, answered, or failed — a modal re-open is free */
  if (!PROSE){
    PROSE_CACHE.set(key, { phase: "failed", error: "no server to read the long-form description from" });
    repaintIfOpen(id);
    return;
  }
  PROSE_CACHE.set(key, { phase: "loading" });
  PROSE(id).then(
    v => {
      PROSE_CACHE.set(key, {
        phase: "ready",
        blocks: v && Array.isArray(v.blocks) ? v.blocks : [],
        source: v && v.source != null ? String(v.source) : "",
      });
      repaintIfOpen(id);
    },
    err => {
      PROSE_CACHE.set(key, { phase: "failed", error: err && err.message ? String(err.message) : String(err) });
      repaintIfOpen(id);
    });
}

/* ── painting, and the controls ────────────────────────────────────────────── */

/* The same repaint `app.js` gives its polled views: nothing moves unless this route is on
   screen, and a focused control with a `data-keep` gets the caret back after the markup it
   was focused in is replaced. */
function paint(){
  if ((location.hash.slice(1).split(":")[0] || "") !== ROUTE) return;
  const main = Board.main();
  if (!main) return;
  const keep = document.activeElement && main.contains(document.activeElement)
    ? document.activeElement.getAttribute("data-keep") : null;
  main.innerHTML = view();
  if (!keep) return;
  const again = main.querySelector(`[data-keep="${keep}"]`);
  if (again) again.focus({ preventScroll: true });
}

function repaintIfOpen(id){
  if (OPEN && OPEN.id === String(id)) paint();
}

function onClick(e){
  const card = e.target.closest("[data-arch]");
  if (card){
    const id = card.getAttribute("data-arch") || "";
    const found = findCard(id);
    if (found){
      OPEN = { id: id, kind: found.kind };
      paint();
      /* THE PROSE IS ASKED AFTER THE MODAL IS ON SCREEN, never with the page — and only for a
         component, the one axis with a long-form behind it. */
      if (found.kind === "component") wantProse(id);
    }
    return;
  }
  if (e.target.closest("[data-arch-close]")){ OPEN = null; paint(); return; }
  if (e.target.closest("[data-arch-src]")){ SRC = !SRC; paint(); return; }
  if (e.target.closest("[data-arch-retry]")){
    /* THE MARK MOVES WITH THE RETRY, not to empty: `read()`'s own guard compares the read in
       flight against `SEEN`, and a retry that blanked it would make the arrival after the next
       navigation look like an unanswered question and re-read what this read just answered. */
    SEEN = Board.repo() + "|" + ROUTE;
    read();
    return;
  }
}

function onKey(e){
  if (!OPEN || e.key !== "Escape") return;
  if ((location.hash.slice(1).split(":")[0] || "") !== ROUTE) return;
  OPEN = null;
  paint();
}

return { start: start, pace: pace, view: view };
})();

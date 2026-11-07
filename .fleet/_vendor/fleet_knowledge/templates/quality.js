/* The Quality desk page — Promises, Scenarios and Environments, read from `/api/quality/*`.
 *
 * A host page module beside `architecture.js`, keeping the same seam: this file spells no URL.
 * `Quality.start({route, load, loadBriefing, brief})` is handed the reads and the one write,
 * `Quality.view()` returns the markup, and `Quality.pace(route)` re-reads on navigation, keyed on
 * the repository plus the route so a repository switch re-reads and walking away and back does not.
 *
 * THREE VIEWS, ONE PER TAB. Promises (the default) opens on one calm line per feature, grouped by
 * importance tier, worst first inside each tier; a line unfolds in place to its promises. Scenarios
 * lists the checks the QA agent wrote, each opening its own page; Environments lists where those
 * checks run. The page draws what the server decided and never re-derives a state.
 *
 * CALM BY RULE (the owner's): one line per feature, unfolds in place, no figure tiles and no
 * charts. The head is three sentences — the release, what is checked, tonight — and anything else
 * waits behind one "more". The narrowing is the shared `Board.filterBar`; the words on a line are
 * counts of states, never a score.
 */

window.Quality = (function(){
"use strict";

var ROUTE = "quality";
var LOAD = null;
var LOADBRIEFING = null;
var LOADPLAN = null;
var LOADWAITING = null;
var SEND = null;
/* THE ENVIRONMENTS PAGE'S ONE WRITE (FLT-1277): the host hands it `(environment id, paused)`.
 * Absent, the page draws the safety evidence and no control rather than a button that cannot act. */
var PAUSE = null;
var PAUSING = "";
var PAUSE_ERR = "";

/* cold | loading | ready | failed */
var STATE = "cold";
var DETAIL = "";
var DATA = null;
var CURRENT = "";
var SEEN = "";

/* the night's cap and the briefs it holds (ENG-16948): its own no-store read, because the desk is
 * a generation reading and this is per-install state that moves through the day. */
var BRIEFING = null;
var BRIEF_STATE = "cold";

/* TONIGHT'S QA PLAN (FLT-1226/1228): `GET /api/quality/plan`, its own no-store read beside the
 * cap — what the QA agent will re-check and newly cover tonight, and what the guard refused. */
var PLAN = null;
var PLAN_STATE = "cold";

/* THE NEWER RESULTS WAITING IN OPEN PULL REQUESTS (AC-6): `GET /api/quality/waiting`, read
 * beside the cap and the plan. It is a separate read on purpose: a waiting result never moves a
 * promise's state or a header count, so nothing here may reach `counts()`. */
var WAITING = null;
var WAIT_STATE = "cold";

/* the ask dialog: "" closed | "form" | "confirm" | "queued" | "error" */
var ASK = "";
var ASK_ERR = "";
var ASK_RESULT = null;
var TOKEN = "";
var PICK = { id: "", area: "", kind: "", note: "" };

/* what the reader has narrowed, opened and unfolded — page state, never sent anywhere */
var F = { state: "", mode: "", reg: "", text: "", area: "" };
/* Where the list's page starts, in matches. Every filter change sets it back to the first page. */
var OFFSET = 0;
var OPEN = "";
/* THE ONE FEATURE LINE OPEN ON THE FIRST SCREEN. The filtered view draws its lines open from the
 * answer's own `view.area`, so this only has to carry the line while the read is in flight. */
var OPENF = "";
var MORE = false;
/* THE NINE STATE WORDS, explained once behind the section label's link. Closed until pressed. */
var SHOW_WORDS = false;
/* A filter asks the SERVER for its rows (the reading is thousands of rows; one screen is a few
 * dozen). `REFINING` numbers the asks so an answer that lost the race is dropped. */
var REFINING = 0;
var REFINE_ERR = "";

var DASH = "—";

/* -- the state vocabulary ------------------------------------------------------ */

var STATES = ["failing", "flaky", "disputed", "quarantined", "unfinished", "out-of-date", "cant-run", "no-check", "passing"];
var WORD = {
  "passing": "passing",
  "failing": "failing",
  "flaky": "flaky",
  "disputed": "disputed",
  "unfinished": "unfinished",
  "out-of-date": "out of date",
  "cant-run": "can’t run",
  "quarantined": "quarantined",
  "no-check": "not checked yet",
  "not-run": "not run"
};
var TIP = {
  "passing": "passing — a live check passed it, with evidence, inside its window",
  "failing": "failing — a check that proves it failed",
  "flaky": "flaky — one check gave different verdicts on the same release",
  "disputed": "disputed — the verifier disagreed with the check’s verdict",
  "unfinished": "unfinished — it ran and passed with evidence, but cannot count yet",
  "out-of-date": "out of date — no live pass inside its window",
  "cant-run": "can’t run — the check was blocked where it was sent",
  "quarantined": "quarantined — counts nowhere and files no findings",
  "no-check": "no check yet — nothing proves it",
  "not-run": "not run — nothing on the record counts"
};
var MARK = {
  "passing": "pass", "failing": "fail", "flaky": "flaky", "disputed": "disputed",
  "unfinished": "unfinished", "out-of-date": "outofdate", "cant-run": "cantrun", "quarantined": "quarantined",
  "no-check": "nocheck", "not-run": "norun"
};
/* THE NINE STATES, EACH IN ONE SHORT SENTENCE (AC-4). This is the only place the Promises view
 * explains a state; a row carries the word and no tooltip. */
var EXPLAIN = [
  ["failing", "A check proved that it does not hold."],
  ["flaky", "One check gave different verdicts on the same release."],
  ["disputed", "The verifier disagreed with the check’s verdict."],
  ["quarantined", "Its checks are on hold. It counts nowhere."],
  ["unfinished", "It passed with evidence, but the result cannot count yet."],
  ["out-of-date", "It has no live pass inside its time window."],
  ["cant-run", "The check was blocked where it was sent."],
  ["no-check", "Nothing proves it yet."],
  ["passing", "A live check passed it, with evidence, inside its time window."]
];
var CAUSE = {
  "product": "product", "agent": "agent couldn’t run it",
  "environment": "environment", "inconclusive": "inconclusive"
};
/* A feature line's states in the order the desk says them. Failing, not checked yet and passing
 * are said even at zero; every other state only when it is above zero. */
var WORD_ORDER = ["failing", "flaky", "disputed", "quarantined", "unfinished", "out-of-date", "cant-run", "no-check", "passing"];
var ALWAYS_STATED = { "failing": true, "no-check": true, "passing": true };
var LOUD_STATES = { "failing": true, "flaky": true, "disputed": true };
/* A WAITING RESULT'S WORDS (AC-6): the four verdicts and the three reasons a verdict cannot count
 * yet. The backend answers the verdict id and the qualifier id; this is the one place they become
 * words. */
var WAIT_WORD = {
  "pass": "passed",
  "fail": "failed",
  "blocked": "was blocked",
  "not-applicable": "was not applicable"
};
var WAIT_QUALIFIER = {
  "code-only": "read the code only",
  "unfinished": "did not finish",
  "no-evidence": "no evidence"
};

function stateTone(s){
  return s === "failing" || s === "flaky" || s === "disputed" ? "attn"
    : s === "out-of-date" ? "brass"
    : s === "passing" ? "proven" : "";
}

function esc(s){ return Board.esc(String(s == null ? "" : s)); }

function stateOf(raw){
  var s = String(raw || "");
  return WORD[s] ? s : "no-check";
}

function mark(state){
  var s = WORD[state] ? state : "not-run";
  return '<span class="qdm ' + MARK[s] + '" role="img" title="' + esc(TIP[s]) + '" aria-label="' +
    esc(TIP[s]) + '"></span>';
}

/* -- the seam ------------------------------------------------------------------ */

function start(opts){
  var o = opts || {};
  ROUTE = String(o.route || ROUTE);
  LOAD = o.load || null;
  LOADBRIEFING = o.loadBriefing || null;
  LOADPLAN = o.loadPlan || null;
  LOADWAITING = o.loadWaiting || null;
  SEND = o.brief || null;
  PAUSE = o.pause || null;
  document.addEventListener("click", onClick);
  document.addEventListener("change", onChange);
  document.addEventListener("input", onInput);
  document.addEventListener("keydown", onKey);
}

function pace(route){
  var r = String(route || "");
  if (r.split(":")[0] !== ROUTE) return;
  var mark_ = Board.repo() + "|" + r;
  if (mark_ === SEEN && STATE !== "cold") return;
  SEEN = mark_;
  read(r);
  /* The Promises head says what tonight's limit leaves; only that view reads it. */
  if (viewOf(r) === "promises"){ readBriefing(); readPlan(); readWaiting(); }
}

/* PRESS THE CONTROL. The host's write resolves, then the desk re-reads so the row shows what the
 * server now holds rather than what the press hoped; a refusal is said in the unfold and the
 * button stays available. */
function pauseEnv(id, paused){
  if (!PAUSE || PAUSING) return;
  PAUSING = String(id);
  PAUSE_ERR = "";
  paint();
  var sent;
  try { sent = PAUSE(String(id), paused); }
  catch (e) { sent = Promise.reject(e); }
  Promise.resolve(sent).then(
    function(){
      PAUSING = "";
      SEEN = Board.repo() + "|" + CURRENT;
      read(CURRENT);
    },
    function(err){
      PAUSING = "";
      PAUSE_ERR = err && err.message ? String(err.message) : String(err);
      paint();
    }
  );
}

function read(route){
  if (!LOAD) return;
  var atSend = SEEN;
  STATE = "loading";
  CURRENT = String(route || ROUTE);
  DETAIL = "";
  paint();
  var sent;
  REFINING++;
  REFINE_ERR = "";
  try { sent = LOAD(Board.repo(), CURRENT, query()); }
  catch (e) { sent = Promise.reject(e); }
  Promise.resolve(sent).then(
    function(payload){
      if (atSend !== SEEN) return;
      DATA = payload && typeof payload === "object" ? payload : {};
      STATE = "ready";
      paint();
    },
    function(err){
      if (atSend !== SEEN) return;
      STATE = "failed";
      DETAIL = err && err.message ? String(err.message) : String(err);
      paint();
    }
  );
}

/* WHAT THE FILTERS ASK THE SERVER FOR. Only the Promises view narrows; the other tabs read
 * their whole (small) payloads. The feature desk is always asked for (`view=features`); empty
 * values are left off. */
function query(){
  if (viewOf(CURRENT || ROUTE) !== "promises") return {};
  var q = {view: "features"};
  if (F.state) q.state = F.state;
  if (F.area) q.area = F.area;
  if (F.reg) q.register = F.reg;
  if (F.text && F.text.length >= 2) q.q = F.text;
  if (F.mode) q.mode = F.mode;
  if (OFFSET > 0) q.offset = OFFSET;
  return q;
}

/* A FILTER CHANGED: re-ask, keeping the page as it is until the answer lands — no "reading"
 * flash, the search box keeps its caret — and drop any answer a later ask overtook. */
function refine(){
  if (!LOAD || STATE !== "ready"){ paint(); return; }
  REFINE_ERR = "";
  paint();
  var mine = ++REFINING;
  var atSend = SEEN;
  var sent;
  try { sent = LOAD(Board.repo(), CURRENT, query()); }
  catch (e) { sent = Promise.reject(e); }
  Promise.resolve(sent).then(
    function(payload){
      if (mine !== REFINING || atSend !== SEEN) return;
      DATA = payload && typeof payload === "object" ? payload : DATA;
      REFINE_ERR = "";
      paint();
    },
    function(err){
      if (mine !== REFINING || atSend !== SEEN) return;
      REFINE_ERR = err && err.message ? String(err.message) : String(err);
      paint();
    }
  );
}

function readBriefing(){
  if (!LOADBRIEFING) return;
  var atSend = SEEN;
  BRIEF_STATE = "loading";
  var sent;
  try { sent = LOADBRIEFING(Board.repo()); }
  catch (e) { sent = Promise.reject(e); }
  Promise.resolve(sent).then(
    function(payload){
      if (atSend !== SEEN) return;
      BRIEFING = payload && typeof payload === "object" ? payload : {};
      BRIEF_STATE = "ready";
      paint();
    },
    function(){
      if (atSend !== SEEN) return;
      BRIEFING = null;
      BRIEF_STATE = "failed";
      paint();
    }
  );
}

function readPlan(){
  if (!LOADPLAN) return;
  var atSend = SEEN;
  PLAN_STATE = "loading";
  var sent;
  try { sent = LOADPLAN(Board.repo()); }
  catch (e) { sent = Promise.reject(e); }
  Promise.resolve(sent).then(
    function(payload){
      if (atSend !== SEEN) return;
      PLAN = payload && typeof payload === "object" ? payload : {};
      PLAN_STATE = "ready";
      paint();
    },
    function(){
      if (atSend !== SEEN) return;
      PLAN = null;
      PLAN_STATE = "failed";
      paint();
    }
  );
}

/* THE WAITING RESULTS (AC-6/AC-7): a third no-store read beside the cap and the plan. It only
 * ever draws a line under a promise; it never enters `DATA`, `counts()` or a state word. */
function readWaiting(){
  if (!LOADWAITING) return;
  var atSend = SEEN;
  WAIT_STATE = "loading";
  var sent;
  try { sent = LOADWAITING(Board.repo()); }
  catch (e) { sent = Promise.reject(e); }
  Promise.resolve(sent).then(
    function(payload){
      if (atSend !== SEEN) return;
      WAITING = payload && typeof payload === "object" ? payload : {};
      WAIT_STATE = "ready";
      paint();
    },
    function(){
      if (atSend !== SEEN) return;
      WAITING = null;
      WAIT_STATE = "failed";
      paint();
    }
  );
}

function paint(){
  if ((location.hash.slice(1).split(":")[0] || "") !== ROUTE) return;
  var main = Board.main();
  if (!main) return;
  var focused = document.activeElement;
  var searching = focused && focused.getAttribute && focused.getAttribute("data-fb-search") === "quality";
  var caret = searching ? focused.selectionStart : null;
  main.innerHTML = view();
  /* THE SHARED SEARCH BOX KEEPS ITS CARET across the repaint an Enter causes. */
  if (searching){
    var box = main.querySelector('[data-fb-search="quality"]');
    if (box && box.focus){
      box.focus();
      if (caret != null && box.setSelectionRange) box.setSelectionRange(caret, caret);
    }
  }
}

/* -- events -------------------------------------------------------------------- */

function onClick(e){
  var t = e.target;
  if (!t || !t.closest) return;
  var hit;
  if (t.closest("[data-q-retry]")){
    SEEN = Board.repo() + "|" + CURRENT;
    read(CURRENT);
    return;
  }
  if ((hit = t.closest("[data-q-ask]"))){ openAsk(hit.getAttribute("data-q-ask")); return; }
  if (t.closest("[data-q-cancel]")){ closeAsk(); return; }
  /* A press on the dimmed page around the dialog closes it, as Escape does. */
  if (t.classList && t.classList.contains("scrim") && (ASK === "form" || ASK === "error")){ closeAsk(); return; }
  if (t.closest("[data-q-file]")){ fileAsk(); return; }
  if (t.closest("[data-q-dismiss]")){ ASK = ""; ASK_RESULT = null; paint(); return; }
  if (t.closest("[data-q-more]")){ MORE = !MORE; paint(); return; }
  if (t.closest("[data-q-words]")){ SHOW_WORDS = !SHOW_WORDS; paint(); return; }
  if ((hit = t.closest("[data-q-fretry]"))){
    REFINE_ERR = "";
    refine();
    return;
  }
  if ((hit = t.closest("[data-q-fopen]"))){
    toggleFeature(hit.getAttribute("data-q-fopen"));
    return;
  }
  if ((hit = t.closest("[data-q-page]"))){
    OFFSET = Math.max(0, num(hit.getAttribute("data-q-page")));
    OPEN = "";
    refine();
    return;
  }
  if ((hit = t.closest("[data-q-pause]"))){
    pauseEnv(hit.getAttribute("data-q-pause"), hit.getAttribute("data-q-paused") === "true");
    return;
  }
  if ((hit = t.closest("[data-q-open]"))){
    /* A link inside an unfolded row is its own; only the row itself toggles. */
    if (t.closest("a[href]") && !t.closest("a[href]").hasAttribute("data-q-open")) return;
    var id = hit.getAttribute("data-q-open");
    OPEN = OPEN === id ? "" : id;
    paint();
  }
}

/* OPENING A FEATURE LINE asks the server for that feature's rows. The answer replaces `DATA`, so
 * there is one home of rows; the line carries the in-flight state until it lands. */
function toggleFeature(key){
  var opening = OPENF !== key;
  OPENF = opening ? key : "";
  F.area = opening ? key : "";
  OPEN = "";
  OFFSET = 0;
  refine();
}

/* A DISCLOSURE ROW OPENS FROM THE KEYBOARD (ENG-17326's rule for every row on this desk): Enter
 * and Space on a focused row act as its click. A row that opens a PAGE is an anchor and the
 * browser already does this for it. */
function onKey(e){
  if (e.key === "Escape" && (ASK === "form" || ASK === "error")){ closeAsk(); return; }
  if (e.key !== "Enter" && e.key !== " ") return;
  var t = e.target;
  if (!t || !t.getAttribute) return;
  var feature = t.getAttribute("data-q-fopen");
  if (feature !== null){
    if (e.preventDefault) e.preventDefault();
    toggleFeature(feature);
    return;
  }
  if (t.getAttribute("data-q-open") === null) return;
  if (e.preventDefault) e.preventDefault();
  var id = t.getAttribute("data-q-open");
  OPEN = OPEN === id ? "" : id;
  paint();
  var again = document.querySelector('[data-q-open="' + String(id).replace(/"/g, '\\"') + '"]');
  if (again && again.focus) again.focus();
}

function onChange(e){
  var t = e.target;
  if (!t || !t.getAttribute) return;
  var field = t.getAttribute("data-q-field");
  if (field){ PICK[field] = String(t.value || ""); paint(); return; }
}

function onInput(e){
  var t = e.target;
  if (!t || !t.getAttribute) return;
  if (t.getAttribute("data-q-field") === "note"){
    /* No repaint on a keystroke in the note: it would steal the caret. Read again on submit. */
    PICK.note = String(t.value || "");
    return;
  }
}

/* -- routes -------------------------------------------------------------------- */

function viewOf(route){
  var parts = String(route || ROUTE).split(":");
  if (parts[1] === "scenarios") return "scenarios";
  if (parts[1] === "scenario" && parts.length >= 3) return "scenario";
  if (parts[1] === "environments") return "environments";
  return "promises";
}

function here(){ return location.hash.slice(1) || ROUTE; }

function scenarioRoute(id){ return ROUTE + ":scenario:" + encodeURIComponent(String(id)); }

function link(go, inner, cls, extra){
  return '<a class="' + (cls || "qdl") + '" href="' + esc(Board.href(go)) + '" data-go="' + esc(go) + '"' +
    (extra || "") + ">" + inner + "</a>";
}

function tabs(active){
  var all = [["promises", ROUTE, "Promises"], ["scenarios", ROUTE + ":scenarios", "Scenarios"],
    ["environments", ROUTE + ":environments", "Environments"]];
  return '<nav class="qd-tabs" aria-label="Quality desk views">' + all.map(function(t){
    var on = t[0] === active;
    return '<a class="qd-tab" href="' + esc(Board.href(t[1])) + '" data-go="' + esc(t[1]) + '"' +
      (on ? ' aria-current="page"' : "") + ">" + t[2] + "</a>";
  }).join("") + "</nav>";
}

/* -- the page ------------------------------------------------------------------ */

function view(){
  var v = viewOf(here());
  var head = Board.pageHead("Quality desk") + tabs(v === "scenario" ? "scenarios" : v);
  if (STATE !== "ready"){
    return head + (STATE === "failed"
      ? '<div class="banner qd-blk"><b>Could not read the desk.</b> The last read of this ' +
        "repository’s checks did not finish, so the desk shows nothing rather than a stale " +
        "picture.</div>" + '<div class="qd-cta"><button class="act" type="button" data-q-retry>Try again</button></div>'
      : '<p class="empty-note">Reading the checks&hellip;</p>');
  }
  if (v === "scenario") return head + scenarioPage();
  if (v === "scenarios") return head + scenariosPage();
  if (v === "environments") return head + environmentsPage();
  return head + promisesPage();
}

function list(name){ return Array.isArray(DATA && DATA[name]) ? DATA[name] : []; }

function num(v){ var n = Number(v); return isFinite(n) ? n : 0; }

/* An age against the SERVER's clock (`now` on the payload), so a page reads the same in every
 * browser and a test is deterministic. */
function ago(iso){
  if (!iso) return "";
  var now = Date.parse(String((DATA && DATA.now) || ""));
  var t = Date.parse(String(iso));
  if (!isFinite(t)) return "";
  if (!isFinite(now)) now = Date.now();
  var h = Math.max(0, Math.round((now - t) / 3600000));
  if (h < 1) return "now";
  if (h < 48) return h + "h";
  return Math.round(h / 24) + "d";
}

var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
function pad2(n){ return (n < 10 ? "0" : "") + n; }
function when(iso){
  if (!iso) return "";
  var t = Date.parse(String(iso));
  if (!isFinite(t)) return "";
  var d = new Date(t);
  return DAYS[d.getUTCDay()] + " " + pad2(d.getUTCHours()) + ":" + pad2(d.getUTCMinutes());
}
function stamp(iso){
  var t = Date.parse(String(iso || ""));
  if (!isFinite(t)) return String(iso || "");
  var d = new Date(t);
  return d.getUTCFullYear() + "-" + pad2(d.getUTCMonth() + 1) + "-" + pad2(d.getUTCDate()) + " " +
    pad2(d.getUTCHours()) + ":" + pad2(d.getUTCMinutes());
}

/* -- Promises ------------------------------------------------------------------ */

function promisesPage(){
  var all = list("promises");
  var page = askBanner() + headLines();
  if (!all.length && !num(DATA && DATA.total)){
    return page + '<div class="box"><div class="empty-note">No promise to check yet.' +
      '<span class="sub">Promises come from the requirement registers, the shipped capabilities and ' +
      "the journeys; this repository’s corpus has none a check could prove.</span></div></div>" +
      askDialog();
  }
  return page + filterRow() + testsNote() + promisesBody(all) + askDialog();
}

/* WHAT THE ANSWER DRAWS. The first screen is the feature list; a narrowed answer draws the
 * matching promises under their feature lines. The choice is read off `DATA.view`, never `F`. */
function promisesBody(all){
  if (showingFeatures()) return featureList();
  return promiseList(all);
}

/* The feature desk is the answer's own statement (`view.features`) with no narrowing on it. A
 * payload that does not say it is the feature desk is drawn as the list it always was. */
function showingFeatures(){
  var v = DATA && DATA.view;
  if (!v || !v.features) return false;
  return !(v.state || v.register || v.text || v.mode || v.area);
}

function counts(){ return (DATA && DATA.counts) || {}; }

function headLines(){
  var c = counts();
  var rel = DATA && DATA.release;
  var lines = [];
  if (rel && rel.current){
    lines.push('<p class="qd-line"><span class="k">Release</span><b>' + esc(rel.current) + "</b> is what " +
      (rel.environment ? esc(rel.environment) + " (production)" : "production") + " runs" +
      ' <span class="sep">·</span> <span class="attn"><b>' + num(rel.worse) + "</b> got worse in any environment</span>" +
      ' <span class="sep">·</span> <span class="proven"><b>' + num(rel.fixed) + "</b> fixed</span>" +
      ' <span class="sep">·</span> <b>' + num(rel.unchecked) + "</b> not yet checked on it</p>");
  } else {
    /* THE ONE CONDITION THAT IS MISSING, as the reader computed it — never both halves of the rule
     * for the reader to check by hand. */
    var missing = DATA && DATA.release_missing;
    lines.push('<p class="qd-line"><span class="k">Release</span>No release line: ' +
      (missing ? esc(missing) + "." : "it needs exactly one environment marked production and a counted run " +
        "there that names its release.") + "</p>");
  }
  var parts = [
    '<span class="proven"><b>' + num(c["passing"]) + "</b> passing</span>",
    '<span class="attn"><b>' + num(c["failing"]) + "</b> failing</span>",
    '<span class="attn"><b>' + num(c["flaky"]) + "</b> flaky</span>",
    '<span class="brass"><b>' + num(c["out-of-date"]) + "</b> out of date</span>"
  ];
  if (num(c["disputed"])) parts.push('<span class="attn"><b>' + num(c["disputed"]) + "</b> disputed</span>");
  if (num(c["unfinished"])) parts.push("<b>" + num(c["unfinished"]) + "</b> unfinished");
  if (num(c["cant-run"])) parts.push("<b>" + num(c["cant-run"]) + "</b> can’t run");
  if (num(c["quarantined"])) parts.push("<b>" + num(c["quarantined"]) + "</b> quarantined");
  /* The never-checked count hangs off the TOTAL, never off "checked": checked = total - no-check
   * (quality.py), so the count is said beside the total rather than inside the checked set. */
  lines.push('<p class="qd-line"><span class="k">Checked</span><b>' + num(DATA.total) + "</b> promise" +
    (num(DATA.total) === 1 ? "" : "s") + ' <span class="sep">·</span> <b>' + num(c["no-check"]) +
    "</b> not checked yet" + ' <span class="sep">·</span> <b>' + num(DATA.checked) + "</b> checked: " +
    parts.join(' <span class="sep">·</span> ') + "</p>");
  lines.push('<p class="qd-line"><span class="k">Tonight</span>' + tonight() + planSentence() +
    ' <button class="qdl" type="button" data-q-more aria-expanded="' + (MORE ? "true" : "false") + '">' +
    (MORE ? "less" : "more") + "</button></p>");
  var tests = testsLine();
  var more = MORE ? moreLines() : "";
  return '<div class="qd-lines">' + lines.join("") + tests + more + "</div>";
}

/* TONIGHT IS THE NIGHT'S CAP, which is the one plan this desk can read: how many more checks Fleet
 * may file tonight, and what is already waiting for room. */
function tonight(){
  if (BRIEF_STATE !== "ready" || !BRIEFING){
    return BRIEF_STATE === "failed" ? "Tonight’s limit could not be read." : "Reading tonight’s limit…";
  }
  var waiting = Array.isArray(BRIEFING.waiting) ? BRIEFING.waiting.length : 0;
  /* A brief the cap held is said HERE, on the desk itself, so it survives a reload (ENG-16948):
   * how many wait and when the hold lifts. Which ones they are sits behind "more". */
  var until = when(BRIEFING.heldUntil);
  var tail = waiting ? ' <span class="sep">·</span> <b>' + waiting + "</b> asked check" +
    (waiting === 1 ? "" : "s") + " queued, waiting for room" + (until ? ", held until " + esc(until) : "") : "";
  if (BRIEFING.limit == null){
    return "No nightly limit is set, so an asked check is held until an operator sets one" + tail + ".";
  }
  return "<b>" + num(BRIEFING.remaining) + "</b> of <b>" + num(BRIEFING.limit) + "</b> checks left tonight" + tail;
}

/* The lines behind "more": the core areas' reading and how the promises split by kind. Nothing
 * here is a figure the head above has not already earned. */
function moreLines(){
  var sum = (DATA && DATA.summary) || {};
  var core = sum.core || {};
  var kinds = sum.kinds || {};
  return trendLine() + outcomeLine() +
    '<p class="qd-line"><span class="k">Core features</span>' +
    (num(core.total)
      ? "<b>" + num(core.passing) + "</b> of <b>" + num(core.total) + "</b> promises in core-tier features are passing"
      : "No feature is tiered core yet, so there is no core reading.") + riskWeighted() + "</p>" +
    '<p class="qd-line"><span class="k">By kind</span><b>' + num(kinds.requirement) + "</b> register rules " +
    '<span class="sep">·</span> <b>' + num(kinds.capability) + "</b> shipped capabilities " +
    '<span class="sep">·</span> <b>' + num(kinds.criterion) + "</b> journey criteria across <b>" +
    num(sum.journeys) + "</b> journeys" +
    (sum.current_line ? ' <span class="sep">·</span> release line <b>' + esc(sum.current_line) + "</b>" : "") +
    "</p>" + unplacedLine() + heldLine() + planLines();
}

/* THE TREND (BUG-1163, FLT-1224): this week's failing promises against last week's, so the desk
 * says which way the product moves, not only where it stands. Absent until the reading carries it. */
function trendLine(){
  var week = DATA && DATA.outcomes && DATA.outcomes.week;
  if (!week || week["this"] == null) return "";
  var now = num(week["this"]), before = num(week["prev"]);
  var diff = now - before;
  var move = diff > 0 ? "up <b>" + diff + "</b> on" : diff < 0 ? "down <b>" + (-diff) + "</b> on" : "the same as";
  return '<p class="qd-line"><span class="k">Trend</span><b>' + now + "</b> promise" + (now === 1 ? "" : "s") +
    " failed in the last 7 days, " + move + " the week before (<b>" + before + "</b>)</p>";
}

/* THE OUTCOME LINE (BUG-1163, FLT-1224): what the desk actually measured — escaped defects, the
 * share of findings the verifier confirmed real, the median fail→pass and the flake rate. */
function outcomeLine(){
  var o = (DATA && DATA.outcomes) || {};
  var f = o.findings || {};
  var fl = o.flaky || {};
  var med = o.median_fail_to_pass_days;
  var checked = num(fl.checked);
  var bits = [
    "<b>" + num(o.escaped) + "</b> escaped into the current release",
    num(f.total)
      ? "<b>" + Math.round(100 * num(f.confirmed) / num(f.total)) + "%</b> of <b>" + num(f.total) + "</b> findings confirmed real"
      : "no findings on record",
    med == null ? "no fail→pass recovery yet" : "median fail→pass <b>" + days(med) + "</b>",
    "<b>" + num(fl.count) + "</b> of <b>" + checked + "</b> checked promise" + (checked === 1 ? "" : "s") + " are flaky"
  ];
  return '<p class="qd-line"><span class="k">Outcomes</span>' + bits.join(' <span class="sep">·</span> ') + "</p>";
}

/* A fail→pass interval in days, to a tenth — it is rarely a whole number. */
function days(value){
  var d = Math.round((Number(value) || 0) * 10) / 10;
  return d + " day" + (d === 1 ? "" : "s");
}

/* FLT-1222: coverage weighted by authored risk — a core-tier promise counts three times one in a
 * rotation area, so the figure says what a row-by-row count cannot. */
function riskWeighted(){
  var rw = DATA && DATA.risk_weighted;
  if (!rw || rw.percent == null) return "";
  return ' <span class="sep">·</span> risk-weighted coverage <b>' + num(rw.percent) + "%</b>" +
    (num(rw.core_weight) > 1 ? " (core features weigh " + num(rw.core_weight) + "×)" : "");
}

/* BUG-1151: a result row that names a promise the desk does not hold counts toward nothing, so it
 * is counted here, behind "more", never dropped in silence — a few named, the rest counted. Absent
 * when there is none, so the lines behind "more" stay short (FLT-1228). */
function unplacedLine(){
  var n = num(((DATA && DATA.summary) || {}).unplaced);
  if (!n) return "";
  /* `unplaced` is capped server-side (UNPLACED_SHOWN); `summary.unplaced` is the total said here. */
  var rows = Array.isArray(DATA.unplaced) ? DATA.unplaced : [];
  var named = rows.slice(0, 3).map(function(u){
    return '<span class="mono" title="' + esc(u.file) + '">' + esc(u.row) + " → " + (u.promise ? esc(u.promise) : "no promise") + "</span>";
  });
  /* `n` counts (row, unknown id) pairs, deduplicated across runs — not result rows. */
  return '<p class="qd-line"><span class="k">Unplaced</span><span class="attn"><b>' + n + "</b> unplaced row" +
    (n === 1 ? "" : "s") + "</span> count" + (n === 1 ? "s" : "") + " toward nothing, naming no promise the desk holds" +
    (named.length ? ": " + named.join(' <span class="sep">·</span> ') : "") +
    (n > named.length ? " and " + (n - named.length) + " more" : "") + "</p>";
}

/* The QA agent's night in one clause on the Tonight line: how many re-checks, new checks and
 * tests to write it holds. Which ones, and what the guard refused, sit behind "more" (FLT-1228).
 * The test count is tonight's work, never a measure of quality (PRD 0997, FLT-1225). */
function planSentence(){
  if (!LOADPLAN) return "";
  var sep = ' <span class="sep">·</span> ';
  if (PLAN_STATE === "failed") return sep + "tonight’s QA plan could not be read";
  if (PLAN_STATE !== "ready" || !PLAN) return "";
  if (!PLAN.configured) return sep + "QA is off for this repository";
  var items = Array.isArray(PLAN.items) ? PLAN.items : [];
  var re = items.filter(function(i){ return i && i.reason === "recheck"; }).length;
  var fresh = items.filter(function(i){ return i && i.reason === "new"; }).length;
  var tests = items.filter(function(i){ return i && i.reason === "test"; }).length;
  var refused = Array.isArray(PLAN.refused) ? PLAN.refused.length : 0;
  var said = "QA: <b>" + re + "</b> re-check" + (re === 1 ? "" : "s");
  if (tests){
    said += ", <b>" + fresh + "</b> new check" + (fresh === 1 ? "" : "s") +
      " and <b>" + tests + "</b> test" + (tests === 1 ? "" : "s") + " to write";
  } else {
    said += " and <b>" + fresh + "</b> new check" + (fresh === 1 ? "" : "s");
  }
  return sep + said + " tonight" + (refused ? ", <b>" + refused + "</b> refused" : "");
}

/* THE PLAN ROW'S THREE REASONS (PRD 0997): a re-check, a test to write, or new coverage. A test
 * is never drawn as "new", because it is work of a different shape — no environment, a version. */
function planReason(reason){
  if (reason === "recheck") return "re-check";
  if (reason === "test") return "test to write";
  return "new";
}

/* WHAT THE REPOSITORY HAS NOT SET UP (PRD 0997, AC-4): with no `suites`/`tests` declaration the
 * QA agent writes no tests, and a silent absence is the failure this line names. It sits directly
 * under Tonight, outside "more", and shows only on a read plan that reports tests undeclared. */
function testsLine(){
  if (PLAN_STATE !== "ready" || !PLAN || !PLAN.configured) return "";
  var t = PLAN.tests;
  if (!t || t.declared !== false) return "";
  return '<p class="qd-line"><span class="k">Tests</span>The QA agent writes no tests here: this ' +
    "repository has not said where tests go or how to run them. Set both in the qa table of " +
    "<code>" + esc(".fleet/fleet.toml") + "</code>.</p>";
}

/* THE STEPS THAT RIDE A JOURNEY'S RUN (PRD 0996): a journey folds into one run, so its row names
 * the riders — three at most, the rest counted, like the Spent line. Absent when there are none. */
function alsoClause(i){
  var also = Array.isArray(i && i.also) ? i.also : [];
  if (!also.length) return "";
  var named = also.slice(0, 3).map(function(id){ return esc(id); });
  var rest = also.length - named.length;
  return ' <span class="sep">·</span> ' + also.length + " more step" + (also.length === 1 ? " rides" : "s ride") +
    " this run: " + named.join(", ") + (rest ? " and " + rest + " more" : "");
}

/* Behind "more": one short line per run on tonight's plan, then one per refusal with its reason —
 * the guard's before filing, or the run's own at start (`by: "run"`, FLT-1204). */
function planLines(){
  if (PLAN_STATE !== "ready" || !PLAN || !PLAN.configured) return "";
  var sep = ' <span class="sep">·</span> ';
  var items = Array.isArray(PLAN.items) ? PLAN.items : [];
  var refused = Array.isArray(PLAN.refused) ? PLAN.refused : [];
  var spent = spentLine();
  if (!items.length && !refused.length){
    return spent + '<p class="qd-line"><span class="k">QA</span>Nothing is planned for the QA agent tonight.</p>';
  }
  var rows = items.map(function(i){
    i = i || {};
    /* A test names no environment — writing one drives none — but does name the version it keeps. */
    var tail = i.reason === "test"
      ? (i.scenario ? esc(i.scenario) : "new scenario") + ", version " + esc(i.version == null ? 0 : i.version) +
        sep + (i.filed ? "filed" : "planned")
      : (i.scenario ? esc(i.scenario) : "new scenario") + sep + esc(i.environment || "no environment") + sep +
        (i.filed ? "filed" : "planned");
    return '<p class="qd-line"><span class="k">QA</span><b>' + esc(i.promise) + "</b>" + sep +
      planReason(i.reason) + sep + tail + alsoClause(i) + "</p>";
  });
  refused.forEach(function(r){
    r = r || {};
    rows.push('<p class="qd-line"><span class="k">Refused</span><b>' + esc(r.promise) + "</b>" + sep +
      planReason(r.reason) + sep + (r.by === "run" ? "its run refused" + sep : "") +
      esc(r.why) + refusedTicket(r) + "</p>");
  });
  return spent + rows.join("");
}

/* THE TICKET A REFUSAL'S FILING LEFT (BUG-1163, FLT-1204): a link, never just its key, so a reader
 * can follow the refusal to the work it filed. Absent when the ledger holds no key. */
function refusedTicket(r){
  if (!r || !r.issueKey) return "";
  return ' <span class="sep">·</span> filed <a class="qdl" href="' + esc(Board.href("issue:" + r.issueKey)) +
    '" data-go="issue:' + esc(r.issueKey) + '"><b>' + esc(r.issueKey) + "</b></a>";
}

/* WHAT SPENT TONIGHT'S CHECKS, by name, in one line: the due audits, the asked briefs and the QA
 * runs the cap counted — so "0 of 6 left" is never a number nobody can account for. */
function spentLine(){
  var spent = Array.isArray(PLAN && PLAN.spent) ? PLAN.spent : [];
  if (!spent.length) return "";
  /* FIVE NAMES AT MOST across the line, the rest counted — a cap of forty is still one line. */
  var room = 5;
  var named = function(source, label, fmt){
    var rows = spent.filter(function(x){ return x && x.source === source; });
    if (!rows.length) return "";
    var shown = rows.slice(0, Math.max(0, room));
    room -= shown.length;
    var rest = rows.length - shown.length;
    var names = shown.map(fmt).concat(rest ? ["+" + rest + " more"] : []);
    return "<b>" + rows.length + "</b> " + label + (rows.length === 1 ? "" : "s") + " (" + names.join(", ") + ")";
  };
  var parts = [
    named("audit", "audit", function(x){ return esc(x.name); }),
    named("brief", "brief", function(x){ return esc(x.name) + " on " + esc(areaName(x.area)); }),
    named("qa", "QA run", function(x){ return esc(x.name); })
  ].filter(Boolean);
  return '<p class="qd-line"><span class="k">Spent</span>' + parts.join(' <span class="sep">·</span> ') + "</p>";
}

/* A brief the cap held is named on the desk itself, so it survives a reload (ENG-16948). */
function heldLine(){
  if (BRIEF_STATE !== "ready" || !BRIEFING) return "";
  var waiting = Array.isArray(BRIEFING.waiting) ? BRIEFING.waiting : [];
  if (!waiting.length) return "";
  var until = when(BRIEFING.heldUntil);
  var rows = waiting.map(function(w){
    w = w || {};
    return "<b>" + esc(w.kind) + "</b> on <b>" + esc(areaName(w.area)) + "</b>";
  }).join(", ");
  return '<p class="qd-line"><span class="k">Held</span>' + rows + " — " +
    (until ? "held until " + esc(until) + "." : "held until an operator sets tonight’s limit.") + "</p>";
}

/* THE SHARED FILTER BAR (`Board.filterBar`): a search and one Filter button, with Feature, State,
 * Register and Release as single-choice fields. Nothing carries a count. A release value is offered
 * only while the reading has a release line. The page owns the values; the bar owns only its menu. */
function filterRow(){
  var facets = (DATA && DATA.facets) || {};
  var features = list("groups").map(function(g){
    g = g || {};
    var aid = String(g.area || "");
    return {v: aid || "-", t: aid ? String(g.name || aid) : "Not in a feature"};
  });
  var fields = [
    {id: "area", label: "Feature", multi: false, value: F.area ? [F.area] : [], values: features},
    {id: "state", label: "State", multi: false, value: F.state ? [F.state] : [],
      values: STATES.map(function(s){ return {v: s, t: WORD[s]}; })},
    {id: "register", label: "Register", multi: false, value: F.reg ? [F.reg] : [],
      values: (Array.isArray(facets.registers) ? facets.registers : []).map(function(r){ return {v: r, t: r}; })}
  ];
  if (DATA && DATA.release){
    fields.push({id: "mode", label: "Release", multi: false, value: F.mode ? [F.mode] : [],
      values: [{v: "release", t: "Changed on this release"}]});
  }
  /* THE APPROVED MOCKUP'S BAR IS THE SHARED `.fb` ONE, not the New UI's segmented bar. A field
   * with `flag` and `menu:false` opts this page into the `.fb` renderer without drawing a control;
   * the desk's four real fields are the whole menu. */
  fields.push({id: "__surface", label: "", flag: true, menu: false, value: []});
  return Board.filterBar({
    id: "quality",
    noun: ["promise", "promises"],
    search: {value: F.text, placeholder: "Search id or words", label: "Search promises", said: "Matching"},
    fields: fields,
    on: {
      set: function(field, vals){
        var v = (vals && vals[0]) || "";
        if (field === "area"){ F.area = v; OPENF = v; }
        else if (field === "state") F.state = v;
        else if (field === "register") F.reg = v;
        else if (field === "mode") F.mode = v;
        OPEN = "";
        OFFSET = 0;
        refine();
      },
      search: function(text){ F.text = String(text || ""); OPEN = ""; OFFSET = 0; refine(); },
      clear: function(){
        F.state = ""; F.mode = ""; F.reg = ""; F.text = ""; F.area = "";
        OPENF = ""; OPEN = ""; OFFSET = 0;
        refine();
      },
      paint: paint
    }
  });
}

/* A FEATURE LINE'S WORDS: the counts the fleet measured, never a score. Failing, not checked yet
 * and passing are always said; every other state only when it is above zero. A loud state above
 * zero is in the attention colour, and out of date is in brass. */
function words(c){
  c = c || {};
  return WORD_ORDER.filter(function(k){
    return num(c[k]) > 0 || ALWAYS_STATED[k];
  }).map(function(k){
    var n = num(c[k]);
    var cls = n > 0 && LOUD_STATES[k] ? "attn" : n > 0 && k === "out-of-date" ? "brass" : "";
    return (cls ? '<span class="' + cls + '">' : "") + n + " " + WORD[k] + (cls ? "</span>" : "");
  }).join(" · ");
}

function tierRank(tier){
  var t = String(tier || "");
  return t === "core" ? 0 : t === "rotation" ? 1 : t === "parked" ? 2 : 3;
}
var TIER_WORD = ["Core features", "Rotation features", "Parked features", "No tier"];
function featureKey(g){ return String((g && g.area) || "") || "-"; }
function featureName(g){
  var aid = String((g && g.area) || "");
  return aid ? String(g.name || aid) : "Not in a feature";
}

function featureLine(g){
  var key = featureKey(g);
  var open = OPENF === key;
  var orphan = !String(g.area || "");
  return '<button class="qd-f gapcol' + (orphan ? " orphan" : "") + '" type="button" aria-expanded="' +
    (open ? "true" : "false") + '" data-q-fopen="' + esc(key) + '">' +
    '<span class="tw">▸</span><span class="nm">' + esc(featureName(g)) + '</span>' +
    '<span class="wd">' + words(g.counts) + '</span>' +
    '<span class="gp">' + esc(gapWords(g)) + "</span></button>";
}

/* THE GAP, IN WORDS (PRD 0998, AC-4): the test types this feature's promises lack, never a total
 * of tests. Types join only when the same promises lack them, and the server sends the clauses
 * largest first. A feature that lacks nothing adds nothing. */
var TEST_TYPE_WORD = {"unit": "unit", "integration": "integration", "end-to-end": "end-to-end"};
function gapWords(g){
  var d = DATA && DATA.tests;
  if (!d || d.state !== "read" || !d.suites) return "";
  var clauses = Array.isArray(g && g.missing) ? g.missing : [];
  return clauses.map(function(c){
    var types = (Array.isArray(c.types) ? c.types : []).map(function(t){ return TEST_TYPE_WORD[t] || String(t); });
    if (!types.length) return "";
    var list = types.length === 1 ? types[0] :
      types.length === 2 ? types[0] + " or " + types[1] :
      types.slice(0, -1).join(", ") + " or " + types[types.length - 1];
    var n = num(c.promises);
    return "no " + list + " test for " + n + " promise" + (n === 1 ? "" : "s");
  }).filter(Boolean).join(" · ");
}

/* HOW A TEST IS LINKED (PRD 0998, AC-2): the three ways, in the order the design says them. A test
 * linked two ways says both, once. */
function testHow(how){
  var words = [];
  if (how.indexOf("proved") >= 0) words.push("proved by a verify run");
  if (how.indexOf("qa") >= 0) words.push("written by the QA agent");
  if (how.indexOf("named") >= 0) words.push("names this promise");
  return words.join(", ");
}
function testItem(t){
  t = t || {};
  return '<span class="qd-t"><code>' + esc(t.test || "") + '</code><span class="how">' +
    esc(testHow(Array.isArray(t.how) ? t.how : [])) + "</span></span>";
}

/* THE TESTS THAT GUARD AN OPENED PROMISE (PRD 0998, AC-3): Unit, Integration and End-to-end always
 * show, in that order, and say *none* under an empty one. *Type not stated* is a fourth group, only
 * when it holds a test. With no suites declared the block shows only that fourth group, and
 * nothing when it is empty: *none* would claim something Fleet cannot know. */
function testsBlock(p){
  var d = DATA && DATA.tests;
  if (!d || d.state !== "read") return "";
  var t = (p && p.tests) || {};
  var groups;
  if (!d.suites){
    var all = Array.isArray(t.unstated) ? t.unstated : [];
    if (!all.length) return "";
    return '<div class="qd-tests"><h4>Tests that guard this promise</h4>' +
      '<div class="qd-tg unstated"><span class="ty">Type not stated</span><span>' +
      all.map(testItem).join("") + "</span></div></div>";
  }
  groups = [["Unit", t.unit], ["Integration", t.integration], ["End-to-end", t["end-to-end"]]];
  if (Array.isArray(t.unstated) && t.unstated.length) groups.push(["Type not stated", t.unstated]);
  var inner = groups.map(function(g){
    var items = Array.isArray(g[1]) ? g[1] : [];
    return '<div class="qd-tg' + (g[0] === "Type not stated" ? " unstated" : "") + '"><span class="ty">' +
      g[0] + "</span><span>" + (items.length ? items.map(testItem).join("") : '<span class="none">none</span>') +
      "</span></div>";
  }).join("");
  return '<div class="qd-tests"><h4>Tests that guard this promise</h4>' + inner + "</div>";
}

/* THE ONE PLAIN NOTE (PRD 0998, AC-6): no suites, could not read, or too many. It sits between the
 * filter bar and the list. It names the file only when PRD 0997's line does not, so two notes never
 * say nearly the same thing. */
function testsNote(){
  var d = DATA && DATA.tests;
  if (!d) return "";
  if (d.state === "unread") {
    return '<p class="qd-note">Could not read the tests at this commit, so no test shows here.</p>';
  }
  if (d.state === "cut") {
    return '<p class="qd-note">This repository names too many tests to read them all, so no test shows here.</p>';
  }
  if (d.suites) return "";
  var base = "This repository lists no test suites, so the desk cannot say which test types are missing.";
  if (testsLine()) return '<p class="qd-note">' + base + "</p>";
  return '<p class="qd-note">' + base + " List them in the qa table of <code>.fleet/fleet.toml</code>, " +
    "with <code>rechecks = 0</code> and <code>new = 0</code> to keep nightly QA off.</p>";
}

/* THE LINE'S OWN READING STATE, drawn only while the answer has not landed. Once it has, the
 * filtered view draws the open line and its rows. */
function featureOpen(g){
  var key = featureKey(g);
  if (REFINE_ERR){
    return '<div class="qd-fopen"><div class="banner"><b>Could not read this feature’s promises.</b> ' +
      '<button class="act" type="button" data-q-fretry="' + esc(key) + '">Try again</button></div></div>';
  }
  return '<div class="qd-fopen"><p class="empty-note">Reading this feature’s promises&hellip;</p></div>';
}

/* THE NINE STATE WORDS, each with its one short sentence, in the order a feature line says them.
 * Behind the section label's link, closed until a person presses it (AC-4). */
function statesList(){
  return '<dl class="qd-states">' + EXPLAIN.map(function(e){
    return "<dt>" + esc(WORD[e[0]]) + "</dt><dd>" + esc(e[1]) + "</dd>";
  }).join("") + "</dl>";
}

/* THE FIRST SCREEN: one line per feature, in tier order, the unplaced group last under a heavier
 * rule. The server sends the groups in worst-first order; this only groups them under their tier
 * labels and keeps that order inside each one. */
function featureList(){
  var byRank = [[], [], [], []];
  var unplaced = [];
  list("groups").forEach(function(g){
    g = g || {};
    if (!String(g.area || "")){ unplaced.push(g); return; }
    byRank[tierRank(g.tier)].push(g);
  });
  var body = "";
  var line = function(g){
    body += featureLine(g);
    if (OPENF === featureKey(g)) body += featureOpen(g);
  };
  [0, 1, 2, 3].forEach(function(rank){
    if (!byRank[rank].length) return;
    body += '<div class="qd-tier">' + esc(TIER_WORD[rank]) + "</div>";
    byRank[rank].forEach(line);
  });
  unplaced.forEach(line);
  var wordsLink = '<button class="qdl" type="button" data-q-words aria-expanded="' +
    (SHOW_WORDS ? "true" : "false") + '">' +
    (SHOW_WORDS ? "hide what the words mean" : "what the words mean") + "</button>";
  var title = '<div class="qd-secrow"><div class="qd-sec">Features, worst first in each tier</div>' +
    wordsLink + "</div>";
  if (!body){
    return title + '<div class="box"><div class="empty-note">No promise to check yet.</div></div>';
  }
  return title + (SHOW_WORDS ? statesList() : "") +
    '<div class="box"><div class="qd-list rows">' + body + "</div></div>";
}

/* A NARROWED ANSWER: each group that has rows is an open feature line with its promises under it.
 * A journey's criteria sit together under the journey's name, as they always did. The pager is the
 * existing one; no group hides rows behind "show all" any more. */
function promiseList(all){
  var byId = {};
  all.forEach(function(p){ if (p) byId[String(p.id)] = p; });
  var blocks = "";
  list("groups").forEach(function(g){
    g = g || {};
    var rows = (g.ids || []).map(function(id){ return byId[String(id)]; }).filter(Boolean);
    if (!rows.length) return;
    var body = '<button class="qd-f gapcol" type="button" aria-expanded="true">' +
      '<span class="tw">▸</span><span class="nm">' + esc(featureName(g)) + '</span>' +
      '<span class="wd">' + words(g.counts) + '</span>' +
      '<span class="gp">' + esc(gapWords(g)) + "</span></button>";
    body += '<div class="qd-fopen">';
    body += waitingNote();
    /* A JOURNEY'S CRITERIA SIT TOGETHER under the journey's name, drawn once above them. */
    var journey = "";
    rows.forEach(function(p){
      if (p.kind === "criterion" && p.journey && p.journey !== journey){
        journey = p.journey;
        body += '<div class="qd-jh">Journey · <b>' + esc(p.journey_title || p.journey) + "</b></div>";
      }
      body += promiseRow(p);
    });
    body += "</div>";
    /* THE OPEN FEATURE'S OWN NAME, as the mockup's PAYSLIPS heading above the unfolded line. */
    blocks += '<div class="qd-secrow"><div class="qd-sec">' + esc(featureName(g)) + "</div></div>" +
      '<div class="box"><div class="qd-list rows">' + body + "</div></div>";
  });
  var limit = pager((DATA && DATA.view) || {});
  var failed = REFINE_ERR
    ? '<p class="qd-note">The filter could not be applied: ' + esc(REFINE_ERR) + " The rows below are the last ones read.</p>"
    : "";
  if (!blocks){
    /* The shared empty state names every filter in force and the way out; an unfiltered empty
     * repository is answered before this point, in its own words. */
    var bare = '<div class="box"><div class="empty-note">No promise to check yet.' +
      '<span class="sub">Promises come from the requirement registers, the shipped capabilities and ' +
      "the journeys.</span></div></div>";
    return failed + Board.filterEmpty("quality", {bare: bare}) + limit;
  }
  return failed + blocks + limit;
}

/* THE LIST'S PAGES: a view the server capped says which matches it carries and steps to the rest,
 * so "show all" reaches every row instead of telling the reader to guess a narrower filter. */
function pager(view){
  var matched = num(view.matched), carried = num(view.carried), from = num(view.offset);
  if (view.plain){
    /* The plain view is a taste with no pages; when the limit still cut it, say so in one line. */
    return view.capped ? '<p class="qd-note">The first <b>' + carried + "</b> rows are shown; pick a feature " +
      "or a state to see the rest.</p>" : "";
  }
  if (!from && carried >= matched) return "";
  var size = num(view.limit) || carried || 1;
  var nav = [];
  if (from > 0) nav.push('<button class="qdl" type="button" data-q-page="' + Math.max(0, from - size) + '">previous</button>');
  if (from + carried < matched) nav.push('<button class="qdl" type="button" data-q-page="' + (from + carried) + '">next</button>');
  return '<p class="qd-note">Showing <b>' + (carried ? from + 1 : from) + "–" + (from + carried) + "</b> of <b>" +
    matched + "</b>" + (nav.length ? ' <span class="sep">·</span> ' + nav.join(' <span class="sep">·</span> ') : "") + "</p>";
}

function shortRelease(r){ return String(r || ""); }

function meta(p){
  var ev = p.evidence || {};
  if (p.state === "failing"){
    var bits = [];
    if (ev["new"] === true || p.change === "worse"){
      bits.push('<span class="qd-tag">new' + (p.change_env ? " on " + esc(p.change_env) : "") + "</span>");
    }
    bits.push('<span class="qd-cause' + (ev.cause && ev.cause !== "product" ? " soft" : "") + '">' +
      esc(CAUSE[ev.cause] || (ev.environment === "code-only" ? "read in the code" : "failed")) + "</span>");
    if (ev.ticket) bits.push('<span class="qd-ticket">filed ' + esc(ev.ticket) + "</span>");
    return bits.join("");
  }
  if (p.state === "passing" && p.change === "fixed"){
    return '<span class="qd-tag ok">fixed' + (p.change_env ? " on " + esc(p.change_env) : "") + "</span>re-check passed";
  }
  if (p.state === "disputed") return "the verifier disputes the verdict";
  if (p.state === "flaky") return "verdicts disagree on " + esc(ev.release || "one release");
  if (p.state === "quarantined") return "quarantined · files no findings";
  if (p.state === "cant-run") return "blocked where it ran";
  if (p.state === "unfinished") return "passed · not counted yet";
  if (p.state === "out-of-date") return p.last_pass ? "older than " + num(p.window_days) + " days" : "never passed live";
  if (p.state === "no-check") return "nothing checks it";
  return esc(ev.environment_id || "");
}

function age(p){
  if (p.state === "failing" && p.since) return "since " + shortRelease(p.since).replace(/T.*$/, "");
  if (p.state === "no-check") return DASH;
  if (p.last_pass) return (p.state === "passing" ? "" : "passed ") + ago(p.last_pass);
  if (p.evidence && p.evidence.ran_at) return ago(p.evidence.ran_at);
  return DASH;
}

/* THE READ NOTE (AC-6): the open feature says so when the waiting read failed or answered a state
 * that is not `read`. A `partial` read still draws what it found. Nothing shows while the read is
 * still on its way, so the page paints first and repaints when the answer lands. */
function waitingNote(){
  if (WAIT_STATE === "failed"){
    return '<p class="qd-note">Could not check for waiting results, so a newer result may not show here.</p>';
  }
  if (WAIT_STATE !== "ready") return "";
  if (WAITING && String(WAITING.state || "") === "read") return "";
  return '<p class="qd-note">Could not check for waiting results, so a newer result may not show here.</p>';
}

/* A NEWER RESULT WAITING IN AN OPEN PULL REQUEST (AC-6): one line under its promise, always
 * visible. It is never counted while it waits, so this draws nothing into the state words. */
function waitingLine(p){
  var id = String(p.id);
  var w = WAITING && WAITING.waiting ? WAITING.waiting[id] : null;
  if (!w) return "";
  var verdict = WAIT_WORD[String(w.verdict || "")] || String(w.verdict || "");
  var qualifier = WAIT_QUALIFIER[String(w.qualifier || "")] || "";
  var said = "A newer result " + esc(verdict) +
    (qualifier ? " (" + esc(qualifier) + ")" : "") + " and waits in ";
  var n = num(w.pr);
  var pr = n && w.url
    ? '<a href="' + esc(w.url) + '" target="_blank" rel="noopener">pull request #' + n + "</a>"
    : esc("pull request #" + (w.pr == null ? "" : w.pr));
  return '<div class="qd-wait"><span class="w">waiting</span><span>' + said + pr +
    ". It is not counted while it waits.</span></div>";
}

function promiseRow(p){
  var id = String(p.id);
  var open = OPEN === id;
  var wait = waitingLine(p);
  var tone = stateTone(p.state);
  return '<div class="qd-row pr' + (wait ? " haswait" : "") + '" role="button" tabindex="0" aria-expanded="' +
    (open ? "true" : "false") + '" data-q-open="' + esc(id) + '">' +
    '<span class="st' + (tone ? " " + tone : "") + '">' + esc(WORD[stateOf(p.state)]) + "</span>" +
    '<span class="id">' + esc(id) + "</span>" +
    '<span class="tx">' + esc(p.statement) + "</span>" + '<span class="by">' + meta(p) + "</span>" +
    '<span class="age">' + esc(age(p)) + "</span></div>" + wait + (open ? unfold(p) : "");
}

function shortCommit(c){ return String(c || "").slice(0, 8); }

/* THE DECIDING RESULT'S PLACE, one short line (FLT-1211/1219): the commit it read, the environment
 * by its record id — a result too old to name one says "live" or "code-only" as it recorded —
 * the release, and when it ran. A fail adds its cause, or says the cause is missing (FLT-1221). */
function whereLine(ev){
  if (!ev || !ev.verdict) return "";
  var bits = [];
  if (ev.commit) bits.push("commit <code>" + esc(shortCommit(ev.commit)) + "</code>");
  bits.push(esc(ev.environment_id || ev.environment || "live"));
  bits.push(ev.release ? "release <b>" + esc(ev.release) + "</b>" : "release unknown");
  if (ev.ran_at) bits.push("ran " + esc(stamp(ev.ran_at)));
  if (ev.verdict === "fail"){
    bits.push(ev.cause ? "cause: " + esc(CAUSE[ev.cause] || ev.cause) : '<span class="attn">cause missing</span>');
  }
  return '<div class="qd-ev" title="the result that decided this state">' + bits.join(" · ") + "</div>";
}

/* THE EVIDENCE LINE: what was expected and observed, the platform's own ids, the attempts and the
 * verifier's mark — one line, the facts and nothing else. */
function evidenceLine(ev, quietReview, saidWhy){
  if (!ev) return "";
  var bits = [esc(ev.id)];
  if (ev.expected) bits.push("expected <b>" + esc(ev.expected) + "</b>");
  if (ev.observed) bits.push("observed <b" + (ev.verdict === "fail" ? ' class="x"' : "") + ">" + esc(ev.observed) + "</b>");
  if (!ev.expected && !ev.observed && ev.reason) bits.push(esc(ev.reason));
  var e = ev.evidence || {};
  if (Array.isArray(e.request_ids) && e.request_ids.length) bits.push("req " + esc(e.request_ids.join(", ")));
  if (Array.isArray(e.audit_ids) && e.audit_ids.length) bits.push("audit " + esc(e.audit_ids.join(", ")));
  if (e.snapshot) bits.push("snap " + esc(e.snapshot));
  if (ev.attempts) bits.push(esc(ev.attempts));
  if (ev.not_counted && !saidWhy) bits.push(esc(ev.not_counted));
  var review = ev.review && ev.review.state ? ev.review.state : "";
  if (review && !quietReview) bits.push('<span class="qd-vf ' + esc(review) + '">' + esc(review) + "</span>");
  return '<div class="qd-ev" title="expected against observed, with the platform’s evidence ids">' +
    bits.join(" · ") + "</div>";
}

function whySentence(p){
  var ev = p.evidence || {};
  if (p.state === "out-of-date"){
    return p.last_pass
      ? "Out of date: it last passed " + ago(p.last_pass) + " ago; its feature’s window is " + num(p.window_days) + " days."
      : "Out of date: a check proves it, but no live run of it has passed yet.";
  }
  if (p.state === "cant-run") return "Can’t run: " + (ev.reason || "the check was blocked where it was sent.");
  if (p.state === "unfinished"){
    return "Unfinished: its newest run passed with evidence but does not count yet" +
      (ev.not_counted ? " — " + ev.not_counted + "." : ".");
  }
  if (p.state === "quarantined") return "Quarantined: every check that proves it is held, so it counts nowhere.";
  if (p.state === "disputed") return "Disputed: the verifier re-graded the evidence and disagreed, so it is never green.";
  if (p.state === "flaky") return "Flaky: one check gave different verdicts on " + (ev.release || "the same release") + ".";
  return "";
}

function unfold(p){
  var why = whySentence(p);
  var rels = (p.releases || []).map(function(r){
    return "<span><b>" + esc(r.release) + "</b>" + esc(r.reading === "fail" ? "failed" : "passed") + "</span>";
  }).join("");
  var acts = [];
  if (p.state === "no-check") acts.push('<button class="act" type="button" data-q-ask="' + esc(p.id) + '">Ask the QA agent to cover this</button>');
  if (p.state === "cant-run") acts.push(link(ROUTE + ":environments", "see the environments"));
  var scen = Array.isArray(p.scenarios) ? p.scenarios : [];
  scen.slice(0, 3).forEach(function(s){ acts.push(link(scenarioRoute(s), "open " + esc(s))); });
  var named = Array.isArray(p.checks) ? p.checks : [];
  var total = num(p.check_count) || named.length;
  if (!scen.length && named.length){
    acts.push("<span>checked by " + esc(named.slice(0, 3).join(", ")) +
      (total > 3 ? " and " + (total - 3) + " more" : "") + "</span>");
  }
  /* The reason first: a long statement is clamped to three lines, and the reason must survive it. */
  return '<div class="qd-unf"><p>' + (why ? '<span class="qd-why-s">' + esc(why) + "</span> " : "") + esc(p.statement) + "</p>" +
    (rels ? '<div class="qd-rel">' + rels + "</div>" : "") +
    whereLine(p.evidence) + evidenceLine(p.evidence, false, p.state === "unfinished") +
    testsBlock(p) +
    (acts.length ? '<div class="qd-acts">' + acts.join("") + "</div>" : "") + "</div>";
}

/* -- Scenarios ----------------------------------------------------------------- */

/* A run dot's title says what the run did: a run that passed with evidence but cannot count is
 * "unfinished" and names why, never "not run" (FLT-1212 is for a verdict with no evidence). */
function history(h, why){
  var reasons = Array.isArray(why) ? why.slice(-5) : [];
  var marks = (Array.isArray(h) ? h : []).slice(-5).map(function(s, i){
    var m = mark(s);
    var r = reasons[i];
    if (!r || s === "passing" || s === "failing") return m;
    var tip = esc(TIP[WORD[s] ? s : "not-run"] + ": " + r);
    return m.replace(/title="[^"]*"/, 'title="' + tip + '"').replace(/aria-label="[^"]*"/, 'aria-label="' + tip + '"');
  });
  while (marks.length < 5) marks.unshift('<span class="qdm none"></span>');
  return '<span class="qd-hist" title="the last five runs, oldest first">' + marks.join("") + "</span>";
}

function reviewWord(r){
  r = r || {};
  if (num(r.disputed)) return ['<span class="qd-vf disputed">' + num(r.disputed) + " disputed</span>", "disputed"];
  if (num(r.unverified)) return ['<span class="qd-vf unverified">' + num(r.unverified) + " unverified</span>", "unverified"];
  if (num(r.verified)) return ['<span class="qd-vf verified">verified</span>', "verified"];
  return ['<span class="qd-vf unverified">' + DASH + "</span>", ""];
}

function scenariosPage(){
  var all = list("scenarios");
  var why = '<p class="qd-why">The checks the QA agent wrote and runs. Each walks several parts of the ' +
    "product together, and each expected result proves one promise. A second agent, the verifier, " +
    "re-grades results from the evidence; you only see what it disputes.</p>";
  if (!all.length){
    return why + '<div class="box"><div class="empty-note">No scenario is written yet.<span class="sub">' +
      "A scenario is a record under knowledge/scenarios/ naming the parts it exercises, the promises it " +
      "proves and one row per expected result.</span></div></div>";
  }
  var tally = {};
  var disputed = 0;
  all.forEach(function(s){
    tally[s.state] = (tally[s.state] || 0) + 1;
    disputed += num((s.reviews || {}).disputed);
  });
  /* The verifier's own count of standing disputes, when it recorded any, is the one to say. */
  var vf = (DATA && DATA.verifier) || {};
  if (num(vf.disputed)) disputed = num(vf.disputed);
  var parts = ["<b>" + all.length + "</b> scenario" + (all.length === 1 ? "" : "s")];
  STATES.forEach(function(s){
    if (!tally[s]) return;
    var cls = s === "failing" || s === "flaky" || s === "disputed" ? "attn" : s === "out-of-date" ? "brass" : s === "passing" ? "proven" : "";
    parts.push((cls ? '<span class="' + cls + '">' : "") + "<b>" + tally[s] + "</b> " + WORD[s] + (cls ? "</span>" : ""));
  });
  var rows = all.map(function(s){
    s = s || {};
    var rv = reviewWord(s.reviews);
    return link(scenarioRoute(s.id),
      mark(stateOf(s.state)) + '<span class="nm">' + esc(s.id) + (s.version ? "<i>" + esc(s.version) + "</i>" : "") +
      (s.weak ? ' <span class="qd-tag" title="a planted bug did not turn it red">weak</span>' : "") +
      '<span class="sm">' + esc(s.summary || s.name) + "</span></span>" +
      '<span class="n env">' + esc(s.environment_id || DASH) + "</span>" +
      '<span class="vfc">' + rv[0] + "</span>" + history(s.history, s.history_why) +
      '<span class="age">' + esc(s.latest_run ? ago(s.latest_run) : "never") + "</span>",
      "qd-row sc");
  }).join("");
  return why + '<div class="qd-lines"><p class="qd-line">' + parts.join(' <span class="sep">·</span> ') + "</p>" +
    '<p class="qd-line">Verifier: <b>' + disputed + "</b> disputed verdict" + (disputed === 1 ? "" : "s") + "</p></div>" +
    '<div class="qd-sec">All scenarios</div><div class="box"><div class="qd-list rows">' + rows + "</div></div>";
}

/* -- one scenario -------------------------------------------------------------- */

function verdictWord(a){
  var ev = a.evidence || {};
  if (!ev.verdict) return '<span class="v">not run</span>';
  if (ev.not_counted) return '<span class="v">' + esc(ev.verdict) + " · not counted</span>";
  if (a.state === "flaky") return '<span class="v fail">flaky</span>';
  return '<span class="v ' + (ev.verdict === "fail" ? "fail" : ev.verdict === "pass" ? "pass" : "") + '">' + esc(ev.verdict) + "</span>";
}

function assertionRow(a){
  a = a || {};
  var ev = a.evidence || {};
  var review = ev.review && ev.review.state ? '<span class="qd-vf ' + esc(ev.review.state) + '">' + esc(ev.review.state) + "</span>" : "";
  var st = a.state === "unfinished" ? "unfinished" : !ev.verdict || ev.not_counted ? "not-run" : stateOf(a.state);
  var promise = a.promise || (a.promises || []).join(", ");
  return '<div class="qd-as">' + mark(st) + '<span class="no">#' + esc(a.n) + "</span>" +
    '<span class="pr">' + esc(promise || DASH) + "</span>" + '<span class="tx">' + esc(a.text) + "</span>" +
    '<span class="vd">' + verdictWord(a) + review + "</span>" +
    (ev.verdict ? evidenceLine(ev, true).replace('class="qd-ev"', 'class="qd-ev qd-asev"') : "") + "</div>";
}

function runRow(r){
  r = r || {};
  var t = r.tally || {};
  var said = [];
  if (num(t.pass)) said.push(num(t.pass) + " pass");
  if (num(t.fail)) said.push(num(t.fail) + " fail");
  if (num(t.blocked)) said.push(num(t.blocked) + " blocked");
  if (!r.finished) said.push("unfinished");
  var why = (r.causes || []).map(function(c){ return CAUSE[c] || c; });
  if (r.environment === "code-only") why.push("read the code only");
  return '<div class="qd-run"><span class="d">' + esc(stamp(r.ran_at)) + '</span><span class="ver">' +
    esc(r.scenario_version || DASH) + '</span><span class="r">' + esc(r.release || DASH) + "</span>" +
    '<span class="c' + (num(t.fail) ? " fail" : "") + '">' + esc(said.join(" · ") || "no verdicts") + "</span>" +
    '<span class="why">' + esc(why.join(" · ")) + "</span></div>";
}

function scenarioPage(){
  var d = DATA || {};
  var id = d.id || decodeURIComponent(here().split(":").slice(2).join(":"));
  var crumbs = '<div class="crumbs">' + link(ROUTE + ":scenarios", "Scenarios", "lnk") +
    '<span class="sep">/</span><span class="here">' + esc(id) + "</span></div>";
  if (d.found === false || !d.found){
    return crumbs + '<div class="box"><div class="empty-note">No scenario by this name in this repository.' +
      '<span class="sub">It may have been renamed or removed; the Scenarios tab lists the ones there are.</span></div></div>';
  }
  var runs = Array.isArray(d.runs) ? d.runs : [];
  var latest = runs[0] || null;
  var metaBits = [];
  if (latest && latest.scenario_version) metaBits.push("<b>" + esc(latest.scenario_version) + "</b>");
  if (latest && latest.environment_id) metaBits.push("on " + esc(latest.environment_id));
  metaBits.push(latest ? "last run " + esc(stamp(latest.ran_at)) + (latest.release ? " against <b>" + esc(latest.release) + "</b>" : "") : "never run");
  var banners = "";
  if (d.quarantine){
    banners += '<div class="banner quiet qd-blk"><b>Quarantined until ' + esc(d.quarantine.until) + ".</b> " +
      esc(d.quarantine.reason || "No reason was written.") + " It counts nowhere and files no findings.</div>";
  } else if (d.state === "flaky"){
    banners += '<div class="banner qd-blk"><b>Flaky.</b> The same release gave different verdicts, so it counts ' +
      "nowhere until it agrees with itself.</div>";
  }
  /* THE VERIFIER'S TWO WORDS ON THE SCENARIO ITSELF (FLT-1214, FLT-1215): whether the expected
   * results its latest run was graded against are approved, and whether it let a planted bug
   * through. Either one means a green here proves less than it looks. */
  var oracle = d.oracle || null;
  if (oracle && oracle.state === "pending" && !oracle.version){
    banners += '<div class="banner quiet qd-blk"><b>Its latest run names no version of the expected results.</b> ' +
      "No approved expected result covers it, so a pass is not counted.</div>";
  } else if (oracle && oracle.state === "pending"){
    banners += '<div class="banner quiet qd-blk"><b>Expected results ' + esc(oracle.version) +
      " await the verifier’s approval.</b> Until they are approved, a pass on this version is not counted.</div>";
  } else if (oracle && oracle.state === "changed"){
    banners += '<div class="banner quiet qd-blk"><b>Expected results ' + esc(oracle.version) +
      " changed since the verifier approved them.</b> A pass on this version is not counted until they are approved again.</div>";
  } else if (oracle && oracle.state === "rejected"){
    banners += '<div class="banner qd-blk"><b>The verifier rejected expected results ' + esc(oracle.version) +
      ".</b> A pass on this version is not counted; the QA agent rewrites them.</div>";
  }
  if (d.weak){
    banners += '<div class="banner qd-blk"><b>Weak.</b> A bug planted ' + (d.weak.at ? "on " + esc(d.weak.at) + " " : "") +
      "did not turn this scenario red" + (d.weak.mutation ? " (" + esc(d.weak.mutation) + ")" : "") +
      ", so its passes prove less than they look until a later planted bug is caught.</div>";
  }
  var kv = (d.setup || []).map(function(pair){
    return "<span>" + esc(pair[0] || "") + "</span><code>" + esc(pair[1] || "") + "</code>";
  }).join("");
  var steps = (d.steps || []).map(function(s){ return "<li>" + esc(s) + "</li>"; }).join("");
  var asserts = (d.assertions || []).map(assertionRow).join("");
  var dl = "";
  if (kv) dl += '<dt>Setup</dt><dd><div class="qd-kv">' + kv + "</div></dd>";
  if (steps) dl += "<dt>Steps</dt><dd><ol>" + steps + "</ol></dd>";
  dl += "<dt>Expected</dt><dd>" + (asserts || '<span class="qd-quiet">The record names no expected result.</span>') + "</dd>";
  dl += "<dt>Runs</dt><dd>" + (runs.length ? runs.slice(0, 10).map(runRow).join("") : '<span class="qd-quiet">No run yet.</span>') + "</dd>";
  var proves = (d.proves || []).length ? "Proves " + esc(d.proves.join(", ")) : "";
  var exercises = (d.references || []).length ? "exercises " + esc(d.references.join(", ")) : "";
  return crumbs + '<div class="qd-head">' + mark(stateOf(d.state)) + '<span class="nm">' + esc(id) + "</span>" +
    '<span class="meta">' + metaBits.join(" · ") + "</span></div>" +
    (d.summary ? '<p class="qd-why">' + esc(d.summary) + "</p>" : "") + banners +
    ((proves || exercises) ? '<p class="qd-note">' + [proves, exercises].filter(Boolean).join(" · ") + "</p>" : "") +
    '<div class="box qd-box"><dl class="qd-dl">' + dl + "</dl></div>";
}

/* -- Environments -------------------------------------------------------------- */

function refText(v){
  if (v && typeof v === "object" && !Array.isArray(v)){
    if (v.ref) return "secret " + String(v.ref);
    if (v.withheld) return "withheld — not a secret-store reference";
    return Object.keys(v).map(function(k){ return k + ": " + refText(v[k]); }).join(", ");
  }
  if (Array.isArray(v)) return v.map(refText).join(", ");
  if (v === true) return "yes";
  if (v === false) return "no";
  return String(v == null ? "" : v);
}

function environmentsPage(){
  var all = list("environments");
  var why = '<p class="qd-why">Where the QA agent’s checks run. An environment that cannot run a check ' +
    "makes that check read “can’t run”, never green. Credentials appear only as the names of " +
    "their secret-store references.</p>";
  if (!all.length){
    return why + '<div class="box"><div class="empty-note">No environment is described yet.' +
      '<span class="sub">An environment record (knowledge/environments/&lt;id&gt;.json) says what kind of place ' +
      "a check runs in, who signs in there and with which grants, what a run may write and how it is cleaned " +
      "up — so a check is only ever sent where it can run safely.</span></div></div>";
  }
  var prod = all.filter(function(e){ return e && e.production === true; }).length;
  var rows = all.map(function(e){
    e = e || {};
    var id = "env:" + String(e.id);
    var open = OPEN === id;
    var n = num(e.scenarios);
    return '<div class="qd-row en" role="button" tabindex="0" aria-expanded="' + (open ? "true" : "false") +
      '" data-q-open="' + esc(id) + '"><span class="qdm ' + (e.production === true ? "fail" : "none") + '"' +
      (e.production === true ? ' role="img" aria-label="production" title="production"' : "") + "></span>" +
      '<span class="id">' + esc(e.id) + '</span><span class="n kd">' + esc(refText(e.kind) || DASH) + "</span>" +
      '<span class="n sw">' + esc(refText(e.cleanup) || DASH) + '</span><span class="n mono">' +
      esc(refText(e.harness) || DASH) + "</span>" + '<span class="n qd-r">' + n + " scenario" + (n === 1 ? "" : "s") +
      "</span></div>" + (open ? envUnfold(e) : "");
  }).join("");
  return why + '<div class="qd-lines"><p class="qd-line"><b>' + all.length + "</b> environment" +
    (all.length === 1 ? "" : "s") + ' <span class="sep">·</span> <b>' + prod + "</b> marked production</p></div>" +
    '<div class="qd-sec">Environments</div><div class="box"><div class="qd-list rows">' + rows + "</div></div>";
}

/* THE SAFETY THE DESK MUST PROVE (FLT-1277), not assert: the latest cross-tenant write check
 * reported for the environment, each login's scope and expiry, and one control that pauses every
 * run there. The record's own `paused` and the install's page pause both arrive as `paused`; the
 * page never re-derives which half set it. */
var CROSS_WORD = { pass: "passed", fail: "failed", blocked: "blocked", unfinished: "did not finish" };

function crossTenantLine(e){
  var c = e && e.cross_tenant;
  if (!c || !c.state || c.state === "never"){
    return '<p><span class="qdm nocheck" role="img" aria-label="cross-tenant check never run" ' +
      'title="no cross-tenant write check has been reported"></span>Cross-tenant write check: ' +
      "<b>never run</b> — no result has been reported for this environment.</p>";
  }
  var word = CROSS_WORD[c.state] || c.state;
  var cls = c.state === "pass" ? "pass" : c.state === "fail" ? "fail" : "nocheck";
  return '<p><span class="qdm ' + cls + '" role="img" aria-label="cross-tenant check ' + esc(word) +
    '" title="the repository\'s cross-tenant write check"></span>Cross-tenant write check: <b>' + esc(word) +
    "</b>" + (c.at ? " on " + esc(stamp(c.at)) : "") +
    (c.detail ? " — " + esc(c.detail) : "") + "</p>";
}

function principalLine(p){
  p = p || {};
  var scope = p.scope != null ? p.scope : p.grants;
  var expires = p.expires != null ? refText(p.expires) : "";
  return "<b>" + esc(refText(p.role) || "someone") + "</b>" +
    (scope != null ? " (scope " + esc(refText(scope)) + ")" : "") +
    (p.login ? ", login " + esc(refText(p.login)) : "") +
    (p.password ? ", password " + esc(refText(p.password)) : "") +
    (expires ? ", expires " + esc(expires) : ", expiry not recorded");
}

function pauseControl(e){
  var id = String(e && e.id || "");
  if (!id) return "";
  if (e.record_paused === true){
    return '<p><span class="qdm fail" role="img" aria-label="paused" title="paused by the record"></span>' +
      "<b>Paused by the environment record.</b> No run starts here; the record itself must change " +
      "to lift it.</p>";
  }
  if (e.paused === true){
    var who = e.paused_by ? " by <b>" + esc(e.paused_by) + "</b>" : "";
    var when = e.paused_at ? " on " + esc(stamp(e.paused_at)) : "";
    return '<p><span class="qdm fail" role="img" aria-label="paused" title="paused from this page"></span>' +
      "<b>Paused" + who + when + ".</b> No run starts here.</p>" +
      (PAUSE ? '<div class="qd-cta"><button class="act" type="button" data-q-pause="' + esc(id) +
        '" data-q-paused="false">' + (PAUSING === id ? "Resuming…" : "Resume runs") + "</button></div>" : "");
  }
  return '<p><span class="qdm pass" role="img" aria-label="runs allowed" title="no pause is set"></span>' +
    "Runs are allowed here.</p>" +
    (PAUSE ? '<div class="qd-cta"><button class="act" type="button" data-q-pause="' + esc(id) +
      '" data-q-paused="true">' + (PAUSING === id ? "Pausing…" : "Pause all runs") + "</button></div>" : "");
}

function envUnfold(e){
  var lines = [];
  var where = [e.base_url ? "at " + refText(e.base_url) : "", e.org ? "org " + refText(e.org) : ""].filter(Boolean);
  if (where.length) lines.push(esc(where.join(" · ")));
  var principals = Array.isArray(e.principals) ? e.principals : [];
  if (principals.length) lines.push("Signs in as " + principals.map(principalLine).join("; "));
  if (e.writes != null) lines.push("May write: " + esc(refText(e.writes)));
  var rest = [e.version_probe != null ? "version from " + refText(e.version_probe) : "",
    e.fixtures != null ? "fixtures " + refText(e.fixtures) : ""].filter(Boolean);
  if (rest.length) lines.push(esc(rest.join(" · ")));
  var body = lines.map(function(l){ return "<p>" + l + "</p>"; }).join("") +
    crossTenantLine(e) + pauseControl(e);
  if (PAUSE_ERR) body += '<p class="qd-note">Could not change the pause: ' + esc(PAUSE_ERR) + "</p>";
  return '<div class="qd-unf">' + body + "</div>";
}

/* -- the ask dialog (PRD 0777's brief, opened from one promise) -------------------- */

function newToken(){
  try {
    if (window.crypto && window.crypto.getRandomValues){
      var raw = new Uint8Array(16);
      window.crypto.getRandomValues(raw);
      return Array.prototype.map.call(raw, function(b){ return ("0" + b.toString(16)).slice(-2); }).join("");
    }
  } catch (e) { /* fall through to the plain mint below */ }
  return "t" + Date.now().toString(16) + Math.floor(Math.random() * 1e9).toString(16);
}

function areaName(id){
  var found = list("areas").filter(function(a){ return a && String(a.id) === String(id); });
  return found.length && found[0].name ? String(found[0].name) : String(id || "");
}

function promiseById(id){
  var found = list("promises").filter(function(p){ return p && String(p.id) === String(id); });
  return found.length ? found[0] : null;
}

function openAsk(id){
  var p = promiseById(id);
  var kinds = list("kinds");
  var areas = list("areas");
  var hasArea = p && p.area && areas.some(function(a){ return a && String(a.id) === String(p.area); });
  var kind = kinds.filter(function(k){ return k && k.id === "scenario"; })[0] || kinds[0];
  ASK = "form";
  ASK_ERR = "";
  ASK_RESULT = null;
  PICK = {
    id: String(id || ""),
    area: hasArea ? String(p.area) : (areas.length ? String(areas[0].id) : ""),
    kind: kind ? String(kind.id) : "",
    note: ""
  };
  TOKEN = newToken();
  paint();
}

function closeAsk(){ ASK = ""; ASK_ERR = ""; ASK_RESULT = null; paint(); }

/* THE NOTE CARRIES THE PROMISE. The brief route files an area and a kind; which promise the check
 * is for rides in its note, so the QA agent reads it where it reads every brief. */
function briefNote(){
  var p = promiseById(PICK.id);
  var head = "Cover " + PICK.id + (p && p.statement ? ": " + String(p.statement) : "");
  var note = head.slice(0, 600) + (PICK.note ? "\n\n" + PICK.note : "");
  return note.slice(0, 4000);
}

function fileAsk(){
  if (ASK !== "form" && ASK !== "error") return;
  if (!SEND) return;
  var payload = { token: TOKEN, area: PICK.area, kind: PICK.kind, note: briefNote() };
  var sent;
  try { sent = SEND(payload); }
  catch (e) { sent = Promise.reject(e); }
  Promise.resolve(sent).then(
    function(res){
      ASK_RESULT = res && typeof res === "object" ? res : {};
      ASK = String(ASK_RESULT.state || "filed") === "waiting" ? "queued" : "confirm";
      ASK_ERR = "";
      paint();
      readBriefing();
    },
    function(err){
      ASK = "error";
      ASK_ERR = err && err.message ? String(err.message) : String(err);
      paint();
    }
  );
}

function askBanner(){
  if (ASK !== "confirm" && ASK !== "queued") return "";
  var r = ASK_RESULT || {};
  var kind = esc(r.kind || PICK.kind);
  var name = esc(areaName(r.area || PICK.area));
  var close = ' <button class="qdl quiet" type="button" data-q-dismiss>dismiss</button>';
  if (ASK === "queued"){
    var until = when(r.heldUntil);
    return '<div class="brief-banner wait"><span class="dot"></span><span>Tonight’s limit is full. Your <b>' +
      kind + "</b> check on <b>" + name + "</b> for <b>" + esc(PICK.id) + "</b> is <b>queued</b> — Fleet " +
      "files it on its next pass, as the night’s limit allows. " +
      (until ? "It is held until " + esc(until) + "." : "It is held until an operator sets tonight’s limit.") +
      " Nothing was dropped." + close + "</span></div>";
  }
  return '<div class="brief-banner"><span class="dot"></span><span>One <b>' + kind + "</b> check on <b>" + name +
    "</b> for <b>" + esc(PICK.id) + "</b> is filed. Fleet files it under its own name; the promise turns once " +
    "the run writes its result." + close + "</span></div>";
}

function headroom(){
  if (BRIEF_STATE !== "ready" || !BRIEFING) return "";
  if (BRIEFING.limit == null){
    return "No nightly limit is set, so this is held until an operator sets one.";
  }
  if (num(BRIEFING.remaining) > 0){
    return "<b>" + num(BRIEFING.remaining) + "</b> of <b>" + num(BRIEFING.limit) + "</b> left tonight — this takes one of them.";
  }
  var until = when(BRIEFING.heldUntil);
  return "Tonight’s limit is full, so this is held until " + (until ? esc(until) : "the night resets") + ".";
}

function picker(which, label, hint, options, bad, errText){
  var opts = options.map(function(o){
    var value = String(o.id != null ? o.id : o);
    var text = o.name ? String(o.name) : value;
    return '<option value="' + esc(value) + '"' + (String(PICK[which]) === value ? " selected" : "") + ">" + esc(text) + "</option>";
  }).join("");
  return '<div class="fld' + (bad ? " bad" : "") + '"><label for="qd-pick-' + which + '">' + esc(label) + "</label>" +
    '<select id="qd-pick-' + which + '" data-q-field="' + which + '">' + opts + "</select>" +
    (bad && errText ? '<span class="err"><span class="dot"></span>' + esc(errText) + "</span>"
      : '<span class="hint">' + esc(hint) + "</span>") + "</div>";
}

function askDialog(){
  if (ASK !== "form" && ASK !== "error") return "";
  var p = promiseById(PICK.id) || { id: PICK.id, statement: "" };
  var kinds = list("kinds");
  var areas = list("areas");
  var known = p.area && areas.some(function(a){ return a && String(a.id) === String(p.area); });
  var where = known ? " in " + esc(areaName(p.area)) : "";
  var headOf = '<div class="dlg-h"><h3 id="qd-dlg-t">Ask the QA agent to cover <span class="mono">' + esc(p.id) +
    "</span>" + where + "</h3><p>This promise has no check yet. Fleet files one check for it, under its own name; it counts " +
    "against tonight’s limit.</p></div>";
  var foot = function(withAct){
    return '<div class="dlg-f"><span class="quiet">One check is filed, once — pressing twice or a retry files no ' +
      'second issue.</span><button class="act ghost" type="button" data-q-cancel>' + (withAct ? "Cancel" : "Close") +
      "</button>" + (withAct ? '<button class="act primary" type="button" data-q-file>Ask</button>' : "") + "</div>";
  };
  var shell = function(body, withAct){
    return '<div class="scrim"><div class="dlg qd-dlg" role="dialog" aria-modal="true" aria-labelledby="qd-dlg-t">' +
      headOf + '<div class="dlg-b">' + body + "</div>" + foot(withAct) + "</div></div>";
  };
  if (!areas.length || !kinds.length){
    return shell('<p class="empty-note">This installation defines no features or no kinds of check yet, so there is ' +
      "nothing to ask for. A repository declares both: its feature maps and its audit profile’s kinds.</p>", false);
  }
  var badKind = ASK === "error" && /kind/i.test(ASK_ERR);
  var badArea = ASK === "error" && !badKind && /feature|area/i.test(ASK_ERR);
  var errText = ASK_ERR || "Something was refused; nothing was filed.";
  var body = (p.statement ? '<p class="qd-stmt">' + esc(p.statement) + "</p>" : "") +
    (known && !badArea ? "" : picker("area", "Feature", "The promise names no feature of its own; pick the one to check.", areas, badArea, errText)) +
    picker("kind", "Kind of check", "The kinds written in this installation’s audit profile.", kinds, badKind, errText) +
    '<div class="fld"><label for="qd-note">Note for the QA agent <span class="hint">(optional)</span></label>' +
    '<textarea id="qd-note" data-q-field="note" maxlength="3000" placeholder="For example: try it with a second workspace">' +
    esc(PICK.note) + "</textarea></div>" +
    (headroom() ? '<p class="qd-lim">' + headroom() + "</p>" : "") +
    (ASK === "error" && !badKind && !badArea ? '<p class="dlg-err">' + esc(errText) + "</p>" : "");
  return shell(body, true);
}

return { start: start, pace: pace, view: view };
})();

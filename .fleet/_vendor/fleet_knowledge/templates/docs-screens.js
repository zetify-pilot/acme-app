/* The screens a docs page can show with `::screen{route focus pins}` — framed crops of real Fleet pages.
 *
 * ONE ENTRY PER ROW OF THE CONTRACT'S TABLE (`productdocs/README.md`, "Screens and their anchors"),
 * and nothing else. Adding a screen or an anchor is a change to that table and to this file in the
 * same commit; `docs.js` refuses a route or an anchor this file does not register, and the CI check
 * reads the same names.
 *
 * A CROP, NOT A SCREENSHOT, AND NOT THE PAGE ITSELF. A screenshot is a picture of last month's app
 * and of somebody's data; mounting the real view would drag its reads, its timers and its
 * keyboard into an article. So each screen is a small, believable drawing of the page, written
 * with the labels the app actually puts on screen (`app.html`, `app.js`, `areas.js`, `board.js`,
 * `quality.js` — the words are copied, not paraphrased, so a reader finds what the page told them
 * to look for). Nothing in a crop is a control: buttons are spans, and the whole crop is
 * `aria-hidden`, because the numbered legend under it is what a screen reader reads.
 *
 * `focus` IS REAL DATA. When the block names an item the screen can read (an area, a program, a
 * slice), `docs.js` asks `ctx.live` for it and draws the screen again with `item` set — the
 * reader's own area name in the highlighted row, not an example's.
 *
 * THE SHAPE: `{ title, anchors, draw(s) }`, where `draw` gets
 *   s.focus  the block's `focus` id, or ""        s.item  the live answer for it, or null
 *   s.pin(a) the numbered pin for anchor `a`, or "" when the block did not pin it
 *   s.esc    the page's escaper                     s.mode  "programs" | "areas"
 * and returns the crop's markup. EVERY ANCHOR IN `anchors` MUST BE PLACED by `draw` (through
 * `s.pin`) on every call, whatever `item` is — `docs.js` reports a pin the drawing lost as an error,
 * and the tests pin every anchor of every screen at once.
 */
(function(){
"use strict";

var D = window.FleetDocs || (window.FleetDocs = {});
D.screens = D.screens || {};

/* -- the drawing kit: a handful of shapes every crop is made of ------------------------------ */

/* AN ANCHOR CARRIES ITS PIN IN A GUTTER OF ITS OWN, never on top of what it marks. A pinned anchor
   (`dx-anc-pinned`) opens a left gutter the pin's width and the pin sits in it, so the pin is beside
   the label, inside the anchor's own box — no `overflow:hidden` frame around it can clip it, and no
   word under it is hidden. An anchor the block did not pin opens no gutter and draws as plain text. */
function at(s, name, html, cls){
  var p = s.pin(name);
  return '<span class="dx-anc' + (cls ? " " + cls : "") + (p ? " dx-anc-pinned" : "") + '">' + p + html + "</span>";
}
function head(s, eyebrow, title){
  return '<div class="dx-s-head">' + (eyebrow ? '<span class="dx-s-eye">' + s.esc(eyebrow) + "</span>" : "") + '<span class="dx-s-title">' + s.esc(title) + "</span></div>";
}
function chip(s, text, tone){ return '<span class="dx-s-chip' + (tone ? " dx-s-" + tone : "") + '">' + s.esc(text) + "</span>"; }
function btn(s, text, primary){ return '<span class="dx-s-btn' + (primary ? " dx-s-primary" : "") + '">' + s.esc(text) + "</span>"; }
function tabs(s, list, on){
  return '<span class="dx-s-tabs">' + list.map(function(t, i){ return '<span class="dx-s-tab' + (i === on ? " dx-s-on" : "") + '">' + s.esc(t) + "</span>"; }).join("") + "</span>";
}
function sec(s, text){ return '<div class="dx-s-sec">' + s.esc(text) + "</div>"; }
function muted(s, text){ return '<span class="dx-s-muted">' + s.esc(text) + "</span>"; }
function field(item, re){
  var hit = (item && item.fields || []).filter(function(f){ return re.test(String(f[0])); })[0];
  return hit ? String(hit[1]) : "";
}
function shortQuote(item, fallback){
  var q = item && item.quote ? String(item.quote) : fallback;
  return q.length > 110 ? q.slice(0, 107).replace(/\s+\S*$/, "") + "…" : q;
}

/* -- the twelve screens --------------------------------------------------------------------- */

D.screens.areas = {
  title: "Features", anchors: ["area", "slices", "prds", "next"],
  draw: function(s){
    var focusName = s.item ? s.item.title : s.focus || "Quality Desk";
    var focusDesc = shortQuote(s.item, "What checks found, and what has been checked");
    var nS = field(s.item, /slice/i) || "4", nP = field(s.item, /prd/i) || "6";
    var row = function(slug, name, desc, sl, pr, hl, pins){
      return '<div class="dx-s-row' + (hl ? " dx-s-hl" : "") + '">' +
        '<div class="dx-s-main">' + (pins ? at(s, "area", chip(s, slug) + " <b>" + s.esc(name) + "</b>") : chip(s, slug) + " <b>" + s.esc(name) + "</b>") +
        "<small>" + s.esc(desc) + "</small></div>" +
        '<div class="dx-s-counts">' + (pins ? at(s, "slices", "<b>" + s.esc(sl) + "</b> slices") : "<b>" + s.esc(sl) + "</b> slices") +
        " · " + (pins ? at(s, "prds", "<b>" + s.esc(pr) + "</b> PRDs") : "<b>" + s.esc(pr) + "</b> PRDs") + " · <b>1</b> tasks · " + muted(s, "0 bugs") + "</div></div>";
    };
    return head(s, "", "Features") +
      row(s.focus || "fleet-quality-desk", focusName, focusDesc, nS, nP, true, true) +
      row("fleet-recurring-work", "Recurring work", "Work Fleet files on a schedule", "2", "3", false, false) +
      row("fleet-delivery", "Delivery", "Running Fleet on your own machines", "5", "9", false, false) +
      '<div class="dx-s-fold">' + at(s, "next", "Finished") + "</div>" +
      row("fleet-setup", "Setup", "Installing Fleet and connecting a repository", "0", "0", false, false);
  }
};

D.screens.cockpit = {
  title: "Cockpit", anchors: ["tabs", "views", "filter", "row"],
  draw: function(s){
    var tr = function(prio, title, asks, area, who, age, pinIt){
      var main = "<span>" + chip(s, prio) + " <b>" + s.esc(title) + "</b><small>" + s.esc(asks) + "</small></span>";
      return '<div class="dx-s-tr">' + (pinIt ? at(s, "row", main) : main) +
        "<span>" + s.esc(area) + "</span><span>" + s.esc(who) + "</span><span>" + s.esc(age) + "</span></div>";
    };
    return '<div class="dx-s-toolbar">' + head(s, "", "Cockpit") + '<span class="dx-s-sp"></span>' +
        at(s, "tabs", tabs(s, ["Waiting", "All items"], 0)) + at(s, "views", tabs(s, ["Views"], -1)) + "</div>" +
      '<div class="dx-s-toolbar">' + at(s, "filter", btn(s, "Filter") + " " + chip(s, "Assignee is Me", "on")) +
        '<span class="dx-s-input">Search…</span>' + btn(s, "Display") + "</div>" +
      '<div class="dx-s-table"><div class="dx-s-th"><span>Item</span><span>Feature</span><span>Assignee</span><span>Waiting</span></div>' +
        tr("High", s.focus ? "Which repository should " + s.focus + " land in?" : "Should the nightly check run on both environments?", "Decide", "Quality Desk", "you", "2h", true) +
        tr("Medium", "Plan: Retry a failed run", "Approve", "Delivery", "you", "1d", false) +
        tr("Low", "Rotate the deploy key", "By hand", "Delivery", "you", "3d", false) + "</div>";
  }
};

D.screens.terminals = {
  title: "Terminals", anchors: ["new", "tile", "layouts", "composer", "dock"],
  draw: function(s){
    var tile = function(n, title, state, tone, pinIt){
      var t = '<div class="dx-s-tile"><div class="dx-s-tileh">' + muted(s, "⌘" + n) + " <b>" + s.esc(title) + "</b> " + chip(s, state, tone) + "</div>" +
        '<div class="dx-s-term"><span>$ fleet run</span><span>reading slices.md…</span></div></div>';
      /* the pin marks the whole tile from outside its border: the tile clips its own corners */
      return pinIt ? at(s, "tile", t, "dx-anc-block") : t;
    };
    return '<div class="dx-s-toolbar">' + head(s, "", "Terminals") + '<span class="dx-s-sp"></span>' +
        at(s, "layouts", tabs(s, ["Grid", "Focus", "List", "Board"], 1)) + at(s, "new", btn(s, "+ New session", true)) + "</div>" +
      '<div class="dx-s-split"><div class="dx-s-col">' + tile(1, s.focus || "Fix the flaky queue test", "Working", "flight", true) +
        '<div class="dx-s-composer">' + at(s, "composer", '<span class="dx-s-input">Tell the agent something — it reads it at its next step</span>', "dx-anc-grow") + btn(s, "Send", true) + "</div></div>" +
        '<div class="dx-s-dock">' + at(s, "dock", '<b class="dx-s-docktitle">Machine</b>', "") +
          '<span class="dx-s-spark">CPU</span><span class="dx-s-spark">MEM</span><span class="dx-s-spark">NET</span>' +
          tabs(s, ["Terminal", "Changes", "Ports", "Files", "Secrets"], 1) + "</div></div>";
  }
};

D.screens.program = {
  title: "Program", anchors: ["slices", "proof", "levers"],
  draw: function(s){
    var id = s.focus || "PG-40";
    var name = s.item ? s.item.title : "Agent sessions in boxes of their own";
    return '<div class="dx-s-head"><span class="dx-s-eye">' + s.esc(id) + '</span><span class="dx-s-title">' + s.esc(name) + "</span> " + chip(s, "in flight", "flight") + "</div>" +
      '<p class="dx-s-lead">' + s.esc(field(s.item, /slice/i) ? field(s.item, /slice/i) + " slices" : "3 of 5 slices done") + " · proof 0641 not shipped</p>" +
      sec(s, "To do") + at(s, "levers", '<div class="dx-s-row">' + chip(s, "You", "brass") + " <b>Name the composed proof</b></div>", "dx-anc-block") +
      sec(s, "What must ship to prove this") + at(s, "proof", '<div class="dx-s-row"><b>PRD 0641</b> ' + chip(s, "designed") + "</div>", "dx-anc-block") +
      sec(s, "Slices") + at(s, "slices", '<div class="dx-s-row"><div class="dx-s-main"><b>SL-267 Agent sessions in their own box</b><small>Done when each dispatch run and each session runs in a box of its own.</small></div>' +
        '<span class="dx-s-steps"><i class="on"></i><i class="on"></i><i></i><i></i></span>' + muted(s, "2/4") + "</div>", "dx-anc-block");
  }
};

D.screens.slice = {
  title: "Slice", anchors: ["done-when", "prds", "levers"],
  draw: function(s){
    var id = s.focus || "SL-250";
    var name = s.item ? s.item.title : "Check results kept as files";
    var done = shortQuote(s.item, "A run of any kind of check writes a result file with a verdict for each criterion.");
    var prd = field(s.item, /prd|proven/i) || "0774";
    return '<div class="dx-s-head"><span class="dx-s-eye">' + s.esc(id) + '</span><span class="dx-s-title">' + s.esc(name) + "</span> " + chip(s, "in flight", "flight") + "</div>" +
      at(s, "done-when", '<p class="dx-s-promise">' + s.esc(done) + "</p>", "dx-anc-block") +
      at(s, "levers", '<p class="dx-s-lead">1 of 2 PRDs shipped · proof ' + s.esc(prd.replace(/^PRD\s*/i, "")) + " not shipped</p>", "dx-anc-block") +
      sec(s, "PRDs in this slice") + at(s, "prds", '<div class="dx-s-row"><b>' + s.esc(prd.replace(/^PRD\s*/i, "")) + "</b> Result files for every check " +
        '<span class="dx-s-steps"><i class="on"></i><i class="on"></i><i class="on"></i><i></i></span>' + chip(s, "planned") + " " + muted(s, "your move") + "</div>", "dx-anc-block");
  }
};

D.screens.issue = {
  title: "Issue", anchors: ["position", "actions", "blockers"],
  draw: function(s){
    var key = s.focus || "ENG-123";
    return '<div class="dx-s-head"><span class="dx-s-eye">Issue</span><span class="dx-s-title">' + s.esc(key) + "</span> " + chip(s, "fleet") + "</div>" +
      '<p class="dx-s-lead">The retry test waits on a fixed sleep</p>' +
      '<div class="dx-s-card">' + at(s, "position", "<b>Waiting on you</b> " + chip(s, "waiting on a decision", "brass"), "dx-anc-block") +
        '<div class="dx-s-foot">' + at(s, "actions", '<span class="dx-s-menu">' + btn(s, "Open a terminal…") + btn(s, "Take it by hand") + btn(s, "Park") + btn(s, "Hand back") + "</span>") + "</div></div>" +
      at(s, "blockers", '<p class="dx-s-lead">Holding up <b>ENG-118</b></p>', "dx-anc-block") +
      sec(s, "The record") + '<div class="dx-s-row">' + muted(s, "4 steps") + "</div>";
  }
};

D.screens.queue = {
  title: "Queue", anchors: ["views", "next", "held"],
  draw: function(s){
    return head(s, "", "Queue") +
      '<p class="dx-s-lead"><b>4</b> running of <b>6</b> machines · <b>2</b> waiting on CI · <b>1</b> waiting on merge · <b>3</b> machines free</p>' +
      at(s, "views", '<span class="dx-s-tabs"><span class="dx-s-tab dx-s-on">Everything 9</span>' + at(s, "next", '<span class="dx-s-tab">Next up 3</span>') +
        at(s, "held", '<span class="dx-s-tab">Held back 1</span>') + '<span class="dx-s-tab">Running 4</span></span>') +
      '<div class="dx-s-row">' + muted(s, "1") + " <b>" + s.esc(s.focus || "ENG-204") + "</b> " + chip(s, "bug") + " Retry a reload aborted by network churn " + chip(s, "running", "flight") + "</div>" +
      '<div class="dx-s-row">' + muted(s, "2") + " <b>ENG-211</b> " + chip(s, "task") + " Split the coverage lane " + chip(s, "waiting on CI") + "</div>";
  }
};

D.screens.quality = {
  title: "Quality desk", anchors: ["line", "waiting", "ask"],
  draw: function(s){
    var feature = function(name, said, pin){
      var row = '<div class="dx-s-row"><div class="dx-s-main"><b>' + s.esc(name) + "</b> " +
        muted(s, said) + "</div></div>";
      return pin ? at(s, "line", row, "dx-anc-block") : row;
    };
    return head(s, "", "Quality desk") + tabs(s, ["Promises", "Scenarios", "Environments"], 0) +
      '<p class="dx-s-lead"><b>Release</b> <b>v2.14.0</b> is what production runs · <b>3</b> got worse · <b>2</b> fixed · <b>41</b> not yet checked on it</p>' +
      '<p class="dx-s-lead"><b>Checked</b> <b>147</b> promises · <b>50</b> not checked yet · <b>97</b> checked: <b>68</b> passing · <b>4</b> failing · <b>1</b> flaky · <b>13</b> out of date · <b>1</b> disputed · <b>2</b> can’t run</p>' +
      '<p class="dx-s-lead"><b>Tonight</b> <b>4</b> of <b>6</b> checks left tonight · QA: <b>2</b> re-checks and <b>3</b> new checks tonight</p>' +
      '<div class="dx-s-toolbar"><span class="dx-s-input">Search id or words</span>' + btn(s, "Filter") + "</div>" +
      '<p class="dx-s-lead">' + muted(s, "Feature · State · Register · Release") + "</p>" +
      '<div class="dx-s-toolbar">' + sec(s, "Features, worst first in each tier") + '<span class="dx-s-sp"></span>' + muted(s, "what the words mean") + "</div>" +
      '<div class="dx-s-fold">Core features</div>' +
      feature("Payslips", "2 failing · 5 not checked yet · 11 passing", true) +
      '<div class="dx-s-row"><b>PAY-012</b> failing · A corrected payslip keeps the first version on record.</div>' +
      at(s, "waiting", '<div class="dx-s-row"><b>waiting</b> A newer result passed and waits in pull request #412. It is not counted while it waits.</div>', "dx-anc-block") +
      '<div class="dx-s-row"><b>run-payroll#3</b> not checked yet · An HR admin approves the run before payslips go out.</div>' +
      '<div class="dx-s-row">' + at(s, "ask", btn(s, "Ask the QA agent to cover this", true)) + "</div>" +
      feature("Reports", "1 failing · 1 disputed · 12 not checked yet · 3 passing", false) +
      '<div class="dx-s-fold">Parked features</div>' +
      feature("Old payroll import", "0 failing · 3 not checked yet · 0 passing", false) +
      feature("Not in a feature", "0 failing · 3 not checked yet · 1 passing", false);
  }
};

D.screens["settings:my-mcp"] = {
  title: "Settings · You", anchors: ["editor", "save"],
  draw: function(s){
    return head(s, "Settings · You", "My MCP config") +
      '<div class="dx-s-card"><b>Servers</b><p class="dx-s-lead">Changes apply to sessions you open after saving.</p>' +
      at(s, "editor", '<div class="dx-s-code"><div class="dx-s-codeh">mcp · OpenCode format <span class="dx-s-ok">valid · 2 servers · 1 secret found</span></div>' +
        "<pre>{\n  \"mcp\": {\n    \"" + s.esc(s.focus || "linear") + "\": { \"type\": \"remote\", … }\n  }\n}</pre></div>", "dx-anc-block") +
      '<div class="dx-s-foot"><span class="dx-s-sp"></span>' + at(s, "save", btn(s, "Save", true)) + "</div></div>";
  }
};

D.screens["settings:secrets"] = {
  title: "Settings · Secrets", anchors: ["add", "list"],
  draw: function(s){
    return '<div class="dx-s-toolbar">' + head(s, "Settings · Secrets", "Secrets") + '<span class="dx-s-sp"></span>' + at(s, "add", btn(s, "Add a secret", true)) + "</div>" +
      at(s, "list", '<div class="dx-s-table"><div class="dx-s-th"><span>Name</span><span>Value</span><span>Used by</span><span>Added</span></div>' +
        '<div class="dx-s-tr"><span><code>' + s.esc(s.focus || "LINEAR_API_KEY") + "</code><small>Read by the tracker sync</small></span><span>…a1b2</span><span>2 sessions</span><span>you · 3d</span></div>" +
        '<div class="dx-s-tr"><span><code>NPM_TOKEN</code><small>No description — add one</small></span><span>…9f0c</span><span>—</span><span>you · 1w</span></div></div>', "dx-anc-block") +
      '<p class="dx-s-hint">2 secrets · values are encrypted at rest</p>';
  }
};

D.screens["settings:machines"] = {
  title: "Settings · Machines", anchors: ["machine", "seats", "drain", "add"],
  draw: function(s){
    return '<div class="dx-s-toolbar">' + head(s, "Settings · Machines", "Machines") + '<span class="dx-s-sp"></span>' + at(s, "add", btn(s, "Add machine", true)) + "</div>" +
      '<div class="dx-s-card">' + at(s, "machine", "<b>" + s.esc(s.focus || "fleet-box-1") + "</b> " + chip(s, "Online", "proven"), "dx-anc-block") +
        '<p class="dx-s-lead">Fleet 0.7.500 · last seen just now · 6 seats</p>' +
        at(s, "seats", '<span class="dx-s-step">Dispatch seats <b>4</b></span><span class="dx-s-step">Interactive seats <b>2</b></span>', "dx-anc-block") +
        '<div class="dx-s-foot"><span class="dx-s-sp"></span>' + at(s, "drain", btn(s, "Drain")) + btn(s, "Remove…") + "</div></div>";
  }
};

D.screens["settings:repositories"] = {
  title: "Settings · Repositories", anchors: ["repo", "merge", "verify", "add"],
  draw: function(s){
    return '<div class="dx-s-toolbar">' + head(s, "Settings · Repositories", "Repositories") + '<span class="dx-s-sp"></span>' + at(s, "add", btn(s, "Add a repository", true)) + "</div>" +
      sec(s, "Fleet works here — Issues, plans and pull requests") +
      '<div class="dx-s-card">' + at(s, "repo", "<b>" + s.esc(s.focus || "acme/product") + "</b> " + chip(s, "Fleet project", "brass") + " " + chip(s, "Ready", "proven"), "dx-anc-block") +
        /* the anchor is the TERM, inside its `<dt>`: an anchor around a dt/dd pair would have to be
           `display:contents` to keep the grid, and a box that is not drawn cannot hold a pin */
        '<dl class="dx-s-facts"><dt>' + at(s, "merge", "Merging") + "</dt><dd>agents, on green checks</dd>" +
          "<dt>" + at(s, "verify", "Verify check") + "</dt><dd>on</dd><dt>Issues</dt><dd>without a repo label</dd></dl>" +
        '<div class="dx-s-foot"><span class="dx-s-sp"></span>' + btn(s, "Settings") + btn(s, "⋯") + "</div></div>";
  }
};
})();

/* The one-off designed visuals a docs page may name with `::figure{name alt}` — EMPTY, ON PURPOSE.
 *
 * THE CONTRACT (`productdocs/README.md`, "Figures") RESERVES THE BLOCK: no figure is registered
 * yet, so `::figure` is an error on every page until one is drawn here. A registry that held a
 * placeholder would make the block legal for a visual nobody designed, and the page would render
 * the placeholder to a customer. Adding one is a change to THIS file and to the contract's
 * table, in the same commit, and `fleet check --only product-docs` reads the names from here.
 *
 * THE SHAPE A FIGURE TAKES, for whoever adds the first one:
 *
 *   FleetDocs.figures["the-name"] = { draw: function(ctx){ return "<svg …>…</svg>"; } };
 *
 * `draw` returns markup built only from `fleet.css` tokens (`var(--brass)` and its siblings, never a
 * literal colour, so it is right in both themes); `docs.js` wraps it in the page's figure frame and
 * puts the block's `alt` text beside it for a screen reader, which is the same sentence an agent
 * reads in place of the picture.
 *
 * LOAD-ORDER FREE: this file and `docs.js` each make `window.FleetDocs` if the other has not yet,
 * and neither replaces what the other registered.
 */
(function(){
  "use strict";
  var D = window.FleetDocs || (window.FleetDocs = {});
  D.figures = D.figures || {};
})();

# TimeMachine — Implementation Contract (SPEC)

This is the **single source of truth** every implementation agent builds against. Modules are
authored in parallel; they only integrate if everyone obeys the names, shapes and signatures here.
**Do not invent new globals, rename DOM ids, or change the data shape.**

## 0. Stack & hard constraints

- **Vanilla JS, no build step, no framework, no bundler.** Each script is a *classic* `<script>`
  (NOT an ES module) loaded in the order in `index.html`. Define one global per module.
- Must run by **double-clicking `index.html` (`file://`)** — so **no `fetch`, no `import`, no
  top-level `await`**. All data is already on `window.BIRD_DATA`.
- Map engine is **Leaflet 1.9.4** loaded from CDN (global `L`). Basemaps need **no API key**.
- Target modern evergreen browsers. Mobile must work at **375 / 390 / 428 px** widths.
- **No secrets in code.** The only network calls are Leaflet tiles and (optionally) the Anthropic
  API in `claude.js`, which reads a key from `localStorage`/prompt — never hardcoded.
- Dark theme. Accent gold `#f4a23b`, secondary teal `#38bdf8`. Status colors:
  `transmitting #46d39a`, `complete #8b97a7`, `lost #f0663f`. Per-animal track color is `animal.color`.

## 1. Data global (already produced — read only)

```js
window.BIRD_DATA = {
  generatedAt: "2026-06-13",
  venue: { name:"SHACK15", address:"1 Ferry Building, Suite 201, San Francisco, CA 94111",
           lat:37.7955, lng:-122.3937 },
  disclaimer: "…",
  animals: [{
    id, name, commonName, scientificName, family,
    sex, lifeStage, lengthCm, weightKg,
    tagger, taggedLocation, taggedDate,         // taggedDate = "YYYY-MM-DD"
    status,        // "Transmitting" | "Track complete" | "Signal lost"
    color,         // hex, the track color
    bio,           // ~2 sentence description
    note,          // canned Claude "field note" fallback (used when no API key)
    distanceKm,    // precomputed total
    homeRange,     // human label, e.g. "Mountain Lake"
    pings: [ { lat, lng, t, place? } ]   // t = "YYYY-MM-DDThh:mmZ"; place only on named stops
  }, …]   // 5 animals
};
```

## 2. `scripts/util.js` — global `TM` (build FIRST; everything depends on it)

```js
window.TM = {
  STATUS: { "Transmitting":"live", "Track complete":"done", "Signal lost":"lost" }, // -> css class
  parseT(t),                 // -> ms (Date.parse; "…Z" form parses fine)
  el(tag, props, children),  // tiny hyperscript: props.class/dataset/onclick/html/text supported
  fmtDate(ms), fmtDateTime(ms), timeAgo(ms),   // "Jun 13, 2026" / "Jun 13, 04:27" / "6h ago"
  fmtInt(n),                 // 803521 -> "803,521"
  metrics(pings)             // SEE BELOW — the avg-speed + feet-walked engine
};
```

### `TM.metrics(pings)` — REQUIRED, exact semantics

Returns the movement metrics shown in every profile and the live readout. Pings are assumed sorted
ascending by time. Use great-circle (haversine) distance between consecutive fixes.

```
const M2FT = 3.28084, M2MI = 1/1609.34, SPEED_CAP_MPH = 45, MOVING_MIN_MPH = 0.3;
for each consecutive pair (a,b):
  d_m  = haversine_m(a,b);                 totalMeters += d_m
  dt_h = (parseT(b.t) - parseT(a.t)) / 3.6e6
  if dt_h > 0:
     mph = (d_m * M2MI) / dt_h
     if mph < SPEED_CAP_MPH: keep as a segment   // filter GPS outliers
returns {
  feet:  round(totalMeters * M2FT),
  miles: totalMeters * M2MI,                          // number, round at display
  km:    totalMeters / 1000,
  avgMph: mean(segment mph where mph >= MOVING_MIN_MPH),   // "average speed on the move"
  topMph: max(segment mph),                                // after the <45 filter
  lastDistFeet: feet within the last 14h before the final fix,
  currentSpeedMph: mph of the final segment (0 if last gap > 6h),  // for the LIVE readout
  days: (lastT - firstT) / 86.4e6,
  fixes: pings.length
}
```
Guard against empty/length-1 ping arrays (return zeros, never NaN/Infinity).

## 3. `scripts/map.js` — global class `TMMap`

`new TMMap(elId, venue)` builds the Leaflet map.

- Basemaps via `L.control.layers`: **"Dark" (CARTO dark_all, default)**, "Terrain" (OpenTopoMap),
  "Satellite" (Esri WorldImagery). All keyless; include attributions.
- Drops a distinct **SHACK15 marker** at `venue.lat/lng` (labeled pin / popup with the address).
- Per animal: a **trail polyline** (`animal.color`), small **named-stop dots** (tooltip = `place`),
  and a **head marker** (colored dot). Head **pulses** (CSS class `tm-head--live`) when the animal
  is `Transmitting` and sitting at its latest fix.
- Methods (all must exist):
  - `setAnimals(animals)` — (re)build layers; `animals` carry a precomputed `_pts` (see app.js).
  - `setVisible(idSet)` — show only these ids.
  - `setTime(ms, focusId=null)` — for each visible animal draw trail from first fix → `ms` and place
    the head at the interpolated position; hide animals not yet started by `ms`. If `focusId` set and
    playing/live, gently `panTo` that head.
  - `focus(id)` — `fitBounds` to that animal's full track (padding) and `emphasize(id)`.
  - `emphasize(id|null)` — dim non-selected trails; null = all full opacity.
  - `fitAll(idSet?)` — fit bounds to visible animals (used on load → frames SHACK15 + all 5).
  - `onSelect(cb)` — fire `cb(id)` when a head marker / trail is clicked.
- Interpolation: linear lat/lng between the two fixes bracketing `ms`. Before first fix → hidden;
  after last → head at last fix, full trail.

## 4. `scripts/timeline.js` — global class `TMTimeline`

`new TMTimeline({ minMs, maxMs, onChange })`. Drives `#tl-range #tl-play #tl-current #tl-start
#tl-end #tl-speed`.

- Range slider value 0..1000 maps linearly to `[minMs, maxMs]`. Default at 1000 (= "now", full tracks).
- `#tl-current` shows `TM.fmtDateTime(currentMs)`; `#tl-start`/`#tl-end` show the bounds (`end`="now").
- **Play**: if at end, jump to start, then advance via `requestAnimationFrame`; full span ≈ **28 s at
  1×**, scaled by the active speed button (0.5/1/2/4). Toggle the play/pause SVGs. Stop at end.
- `onChange(ms)` fires on drag and each play frame.
- Public: `value()`→ms, `setValueMs(ms)`, `isPlaying`, `pause()`, `setEnabled(bool)` (LIVE mode
  disables the scrubber).

## 5. `scripts/live.js` — global class `TMLive`

`new TMLive({ animals, onTick, onFix })`. Simulated real-time fix stream for the demo.

- `start()`: every **~2500 ms**, for each `Transmitting` animal append a new fix: a small random
  step from its last position (≈ a believable walking move, biased to wander, scaled to ~tens of
  meters), timestamped `Date.now()`; push to the animal's `_pts`. Call `onFix(animal)` and
  `onTick(Date.now())`.
- `stop()`: clear the interval. `active` boolean. Keep appended fixes so toggling off leaves history.
- Must NOT mutate non-transmitting animals.

## 6. `scripts/claude.js` — global `TMClaude`

`TMClaude.fieldNotes(animal, metrics) -> Promise<string>` — plain-English naturalist note.

- If an Anthropic key exists (`localStorage['tm_anthropic_key']`, else `prompt()` once and store):
  call the **Anthropic Messages API** from the browser with header
  `anthropic-dangerous-direct-browser-access: true`, a compact prompt summarizing species/status/
  recent places/`metrics` (feet, avg & top speed, last-night distance). Model:
  **`claude-haiku-4-5-20251001`** (fast/cheap). *(Implementer: confirm endpoint/headers/model via the
  `claude-api` skill.)*
- **On ANY error or no key → resolve with `animal.note`** (the canned fallback). Never throw to the UI.
- `TMClaude.hasKey()` -> bool; `TMClaude.clearKey()`.

## 7. `scripts/sidebar.js` — global class `TMSidebar`

`new TMSidebar({ data, onSelect, onFilterChange })`. Owns `#search #filters #list #list-count
#btn-reset` and renders `#profile`.

- **Filters** built from the data: Species (commonName), Sex, Life stage, Status. Plus the `#search`
  box (matches name / commonName / scientificName). `getVisibleIds()` returns the filtered set;
  changes call `onFilterChange(idSet)`. `#btn-reset` clears filters (shown only when a filter is active).
- **List**: one card per visible animal — color stripe, name, commonName, a status dot
  (`TM.STATUS`), last-fix `timeAgo`, and distance in **miles**. Click → `onSelect(id)`; highlight
  the selected card.
- **Profile** `renderProfile(animal, metrics)` into `#profile` (slide in; set `aria-hidden=false`):
  - Header: name, commonName + scientificName, status chip.
  - **Metrics block (REQUIRED, prominent):** **Feet walked** (`TM.fmtInt(metrics.feet)` ft + miles),
    **Avg speed** (`metrics.avgMph` mph, labeled "on the move"), **Top speed** (`metrics.topMph` mph),
    **Last night** (`metrics.lastDistFeet` ft). In LIVE mode also show **Current speed**
    (`metrics.currentSpeedMph`).
  - Vitals: sex, life stage, length, weight, tagged date, tagged location, home range, tagger.
  - Bio paragraph.
  - **"Ask Claude → Field Notes"** button → calls `TMClaude.fieldNotes`, shows a loading state, then
    renders the returned text in a notes panel. Close button (×) → hide profile, `onSelect(null)`.
- `select(id|null)` to drive selection from outside; `update(animal, metrics)` to refresh live numbers.

## 8. `scripts/app.js` — orchestrator (global IIFE, no class needed)

1. Read `window.BIRD_DATA`. For each animal precompute `animal._pts = pings.map(p => ({lat,lng,
   ms:TM.parseT(p.t), place:p.place}))` sorted ascending. Compute global `minMs`/`maxMs`.
2. Instantiate `TMMap('map', venue)` → `setAnimals(animals)` → `fitAll()`. Set header stats
   (`#stat-animals` = count, `#stat-active` = # Transmitting). Set `#about-repo` href to the repo URL.
3. `TMTimeline({minMs,maxMs,onChange:ms => map.setTime(ms, selectedId)})`.
4. `TMSidebar({data, onSelect, onFilterChange})`:
   - `onFilterChange(idSet)` → `map.setVisible(idSet)`, refresh list, redraw at current time; if the
     selected animal is filtered out, clear selection.
   - `onSelect(id)` → set selectedId; if id: `map.focus(id)`, `map.emphasize(id)`,
     `sidebar.renderProfile(animal, TM.metrics(animal.pings))`, show `#btn-clear`; if null: hide
     profile, `map.emphasize(null)`, hide `#btn-clear`.
5. `map.onSelect(id => sidebar.select(id))` (clicking the map selects in the list).
6. `TMLive({animals, onTick:nowMs => { timeline.setEnabled(false); map.setTime(nowMs, selectedId);
   if(selectedId) sidebar.update(animal, TM.metrics(animal.pings)); }})`. `#tl-live` toggles
   `live.start()/stop()`; on stop re-enable the timeline at `maxMs`. `#tl-live` reflects pressed state.
7. Wire `#btn-about`/`#about-close` (modal), `#btn-menu` (toggle `.tm-sidebar--open` on mobile),
   `#btn-clear` (deselect), `#btn-reset` (sidebar.reset()).
8. Initial draw at `maxMs` (full tracks, heads at latest, transmitting heads pulsing).

## 9. `styles/main.css`

Implements the dark theme for the structure in `index.html`: fixed header, left sidebar (340px;
collapses to an overlay drawer under 820px via `.tm-sidebar--open`), full-bleed `#map`, the
bottom-center floating **timeline** (`.tm-timeline`) with the LIVE pill (`#tl-live`, pulsing red when
`aria-pressed=true`), the bottom-left `.tm-legend`, the right **profile** slide-in (`.tm-profile`,
380px; full-width sheet on mobile), the about `.tm-modal`. Style Leaflet popups/controls to match
dark. Provide `.tm-head` / `.tm-head--live` (pulsing keyframe) for map head markers and `.dot.live/.done/.lost`.
Respect `prefers-reduced-motion`. Never change animation rates elsewhere; keep it smooth at 60fps.

## 10. Acceptance / validation rubric (every module is graded; emit "VALIDATION x/7")

1. **Runs clean** from `file://` AND a static server — zero console errors/warnings on load.
2. **Contract exact** — global name, methods/signatures, DOM ids, data shape all match this SPEC.
3. **All 5 animals** render (trails + heads + SHACK15 marker); map opens framed on the venue.
4. **Metrics correct** — feet/avg/top match `TM.metrics`; shown prominently in the profile.
5. **Timeline replays** (drag + play) and **LIVE** appends fresh fixes; head pulses for transmitting.
6. **Claude Field Notes** returns text WITH a key and **falls back to `animal.note` WITHOUT** one
   (never throws).
7. **Responsive & clean** at 375/390/428px; no secrets in code; reduced-motion respected.

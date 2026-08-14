"""Assemble the single self-contained HTML file.

Nothing is fetched at runtime and nothing is bundled: the whole page is this
string plus the SVG. Two colours, one family, hierarchy by tracking and case.
Emphasis is inversion — a black chip with sand text — because introducing a
third value would break the thing the design is made of.
"""

from __future__ import annotations

import html
import json

from .model import Scene
from .render import EDGE_SEP, PATTERNS, key

HINT = (
    "→ GO INSIDE · ← COME BACK OUT · ↓↑ MOVE · "
    "HOVER TO READ · DRAG TO PAN · SCROLL TO ZOOM"
)

CSS = """
:root {
  --ground: #CDC499;
  --ink: #000000;
  --muted: rgba(0,0,0,0.42);
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: "DejaVu Sans Mono", ui-monospace, Menlo, Consolas, monospace;
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
#app { display: flex; flex-direction: column; height: 100vh; }

/* the tracked uppercase label used for every heading in the system */
.label {
  font-size: 11px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted);
  display: block;
}

/* ---- top bar ---------------------------------------------------------- */
.topbar {
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid var(--ink);
  flex: 0 0 auto;
}
.topbar .cell {
  padding: 4px 16px 6px;
  border-right: 1px solid var(--ink);
  display: flex;
  flex-direction: column;
  justify-content: center;
  white-space: nowrap;
}
.topbar .cell:last-child { border-right: 0; }
.topbar .value { font-size: 17px; letter-spacing: 0.02em; }
.topbar .identity .value { font-size: 18px; }
.topbar .spacer { flex: 1 1 auto; border-right: 1px solid var(--ink); }
.controls { display: flex; align-items: center; gap: 8px; padding: 0 14px; }
button {
  font: inherit;
  font-size: 11.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--ink);
  padding: 5px 12px;
  cursor: pointer;
}
button[aria-pressed="true"], button:active { background: var(--ink); color: var(--ground); }

/* ---- middle ----------------------------------------------------------- */
main { display: flex; flex: 1 1 auto; min-height: 0; }

/* the panels are separated by hairlines, not by fills: sampling the reference
   gives the sidebar exactly the ground colour, the same as everything else */
.sidebar {
  flex: 0 0 200px;
  border-right: 1px solid var(--ink);
  overflow-y: auto;
  padding: 10px 8px 24px;
}
.sidebar .group { margin: 12px 2px 6px; }
.entry {
  display: grid;
  grid-template-columns: 20px 1fr auto;
  gap: 6px;
  align-items: start;
  border: 1px solid var(--ink);
  padding: 3px 6px 4px;
  margin: 0 0 5px 0;
  font-size: 13px;
  letter-spacing: 0.04em;
  cursor: pointer;
}
.entry[data-depth="1"] { margin-left: 16px; border-color: rgba(0,0,0,0.5); }
.entry .k { color: var(--muted); font-size: 11px; padding-top: 2px; }
.entry .n { text-transform: uppercase; }
.entry .c { color: var(--muted); font-size: 11px; padding-top: 2px; }
.entry.on { background: var(--ink); color: var(--ground); }
.entry.on .k, .entry.on .c { color: var(--ground); }

.canvas { position: relative; flex: 1 1 auto; min-width: 0; overflow: hidden; }
.canvas svg { width: 100%; height: 100%; display: block; touch-action: none; cursor: grab; }
.canvas svg.drag { cursor: grabbing; }
.zoom { position: absolute; top: 10px; right: 12px; display: flex; flex-direction: column; gap: 4px; }
.zoom button { width: 22px; height: 20px; padding: 0; letter-spacing: 0; font-size: 13px; }
.hint {
  position: absolute;
  left: 16px;
  bottom: 8px;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: var(--muted);
}

/* ---- prose panel ------------------------------------------------------ */
.panel {
  flex: 0 0 475px;
  border-left: 1px solid var(--ink);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.tabs { display: flex; flex: 0 0 auto; }
.tab {
  flex: 1;
  text-align: center;
  padding: 7px 0 8px;
  font-size: 11.5px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  cursor: pointer;
  border-bottom: 1px solid var(--ink);
}
.tab.on { background: var(--ink); color: var(--ground); border-bottom-color: var(--ink); }
.panel-body { overflow-y: auto; padding: 16px 22px 40px; }
.eyebrow { font-size: 11px; letter-spacing: 0.2em; color: var(--muted); }
h1 { font-size: 30px; font-weight: 400; letter-spacing: -0.01em; margin: 6px 0 2px; }
.subtitle { font-size: 14px; margin: 0 0 22px; }
.section h2 {
  font-size: 11px;
  letter-spacing: 0.2em;
  font-weight: 400;
  color: var(--muted);
  text-transform: uppercase;
  margin: 24px 0 0;
}
.section .rule { border-top: 1px solid var(--ink); margin: 5px 0 12px; }
.section p { margin: 0 0 14px; }
mark { background: var(--ink); color: var(--ground); padding: 0 3px; }

/* ---- the plane -------------------------------------------------------- */
.ground line { stroke: rgba(0,0,0,0.11); stroke-width: 1; }
.f { stroke: var(--ink); stroke-width: 1; stroke-linejoin: miter; }
.link { stroke: var(--ink); stroke-width: 1.4; fill: none; }
.marker { fill: var(--ink); }
.runner { fill: var(--ink); }
.key {
  font-size: 13px;
  letter-spacing: 0.08em;
  text-anchor: middle;
  fill: var(--ink);
  pointer-events: none;
}
.hit { fill: transparent; stroke: none; cursor: pointer; }
.block.sel .f:last-of-type { fill: var(--ink); }
.block.sel .key { fill: var(--ground); }
"""

SCRIPT = r"""
const D = window.__MAP__;
const svg = document.getElementById('plane');
const stage = document.getElementById('stage');
const panel = document.getElementById('panel-body');
const sidebar = document.getElementById('sidebar');

let level = '';
let stack = [];
let sel = null;
let cam = { x: 0, y: 0, k: 1 };
let home = { x: 0, y: 0, k: 1 };
let tab = 'what';
let running = false;
let hop = 0;
let timer = null;
let anim = null;

/* ---- camera ---------------------------------------------------------- */
function applyCam() {
  stage.setAttribute('transform',
    `translate(${cam.x.toFixed(2)} ${cam.y.toFixed(2)}) scale(${cam.k.toFixed(4)})`);
}

function fit() {
  const box = D.levels[level].box;
  const r = svg.getBoundingClientRect();
  const k = Math.min(r.width / box[2], r.height / box[3]) * 0.95;
  cam = { k: k, x: r.width / 2 - (box[0] + box[2] / 2) * k, y: r.height / 2 - (box[1] + box[3] / 2) * k };
  home = Object.assign({}, cam);
  applyCam();
}

/* ---- levels ---------------------------------------------------------- */
function showLevel(id) {
  level = id;
  for (const g of stage.querySelectorAll('.level')) {
    g.style.display = g.dataset.level === id ? '' : 'none';
  }
  hop = 0;
  clearFlow();
  fit();
  // the root map opens on the system's own prose; a level you descended into
  // opens on its first part, because that is what you asked to look at
  select(id === '' ? null : D.levels[id].order[0] || null, false);
  paintSidebar();
}

function goInside() {
  if (!sel || !D.levels[sel]) return;
  stack.push(level);
  showLevel(sel);
}

function comeOut() {
  if (!stack.length) return;
  const back = stack.pop();
  const was = level;
  showLevel(back);
  select(was, false);
}

/* ---- selection and reading ------------------------------------------- */
function select(id, scrollTo) {
  sel = id;
  for (const b of stage.querySelectorAll('.block')) {
    b.classList.toggle('sel', b.dataset.id === id);
  }
  paintSidebar();
  read(id);
  if (scrollTo) {
    const e = sidebar.querySelector(`[data-id="${CSS.escape(id)}"]`);
    if (e) e.scrollIntoView({ block: 'nearest' });
  }
}

function move(step) {
  const order = D.levels[level].order;
  if (!order.length) return;
  const at = order.indexOf(sel);
  select(order[(at + step + order.length) % order.length], true);
}

function markup(text) {
  const escaped = text.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  return escaped.replace(/\[\[(.+?)\]\]/g, '<mark>$1</mark>');
}

function read(id) {
  const meta = D.nodes[id];
  if (!meta) { paintPanel(); return; }
  const body = tab === 'what' ? meta.what : meta.built;
  const facts = [
    meta.lines + ' lines',
    meta.fan_in ? 'fan-in ' + meta.fan_in : null,
    D.traced && meta.calls ? meta.calls.toLocaleString() + ' calls recorded' : null
  ].filter(Boolean).join(' · ');
  panel.innerHTML =
    `<div class="eyebrow">${meta.group || D.eyebrow}</div>` +
    `<h1>${meta.name}</h1>` +
    `<p class="subtitle">${meta.where}</p>` +
    `<div class="section"><h2>${tab === 'what' ? 'WHAT IT DOES' : "HOW IT'S BUILT"}</h2>` +
    `<div class="rule"></div><p>${markup(body || 'Undescribed.')}</p></div>` +
    `<div class="section"><h2>MEASURED</h2><div class="rule"></div><p>${facts}</p></div>` +
    (D.levels[id] ? `<div class="section"><h2>OPENS</h2><div class="rule"></div>` +
      `<p>${D.levels[id].order.length} parts inside · press → to go inside</p></div>` : '');
}

function paintPanel() {
  const sections = tab === 'what' ? D.what : D.built;
  panel.innerHTML =
    `<div class="eyebrow">${D.eyebrow}</div><h1>${D.title}</h1>` +
    `<p class="subtitle">${D.subtitle}</p>` +
    sections.map(s =>
      `<div class="section"><h2>${s.heading}</h2><div class="rule"></div>` +
      s.body.split('\n\n').map(p => `<p>${markup(p)}</p>`).join('') + `</div>`).join('');
}

/* ---- sidebar ---------------------------------------------------------- */
function entryHtml(id) {
  const n = D.nodes[id];
  if (!n) return '';
  return `<div class="entry${id === sel ? ' on' : ''}" data-id="${id}" data-depth="${n.depth}">` +
    `<span class="k">${n.key}</span><span class="n">${n.name}</span>` +
    `<span class="c">${n.count}</span></div>`;
}

function paintSidebar() {
  // the index is an index of the map you are looking at, so it descends with
  // you: inside a block it lists that block's parts under its own name
  const html = [];
  if (level === '') {
    for (const g of D.groups) {
      html.push(`<div class="group label">${g.title}</div>`);
      for (const id of g.nodes) html.push(entryHtml(id));
    }
  } else {
    const parent = D.nodes[level];
    html.push(`<div class="group label">INSIDE ${parent ? parent.name : level}</div>`);
    for (const id of D.levels[level].order) html.push(entryHtml(id));
  }
  sidebar.innerHTML = html.join('');
}

/* ---- the flow ---------------------------------------------------------- */
function clearFlow() {
  if (anim) { cancelAnimationFrame(anim); anim = null; }
  for (const g of stage.querySelectorAll('.flow')) g.innerHTML = '';
}

function hopsHere() {
  return D.levels[level].hops;
}

function walk(done) {
  const hops = hopsHere();
  if (!hops.length) return;
  const step = hops[hop % hops.length];
  hop = (hop + 1) % hops.length;
  const path = D.levels[level].paths[step[0] + D.sep + step[1]];
  select(step[1], true);
  if (!path || path.length < 2) { done(); return; }

  const flow = stage.querySelector(`.level[data-level="${CSS.escape(level)}"] .flow`);
  const mark = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
  mark.setAttribute('class', 'runner');
  flow.appendChild(mark);

  const lengths = [];
  let total = 0;
  for (let i = 0; i < path.length - 1; i++) {
    const d = Math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]);
    lengths.push(d); total += d;
  }
  const start = performance.now();
  const ms = Math.max(320, Math.min(900, total * 1.6));

  function frame(now) {
    const t = Math.min(1, (now - start) / ms);
    let want = t * total, i = 0;
    while (i < lengths.length - 1 && want > lengths[i]) { want -= lengths[i]; i++; }
    const f = lengths[i] ? want / lengths[i] : 0;
    const x = path[i][0] + (path[i + 1][0] - path[i][0]) * f;
    const y = path[i][1] + (path[i + 1][1] - path[i][1]) * f;
    const r = 5;
    mark.setAttribute('points', `${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`);
    if (t < 1) { anim = requestAnimationFrame(frame); }
    else { mark.remove(); anim = null; done(); }
  }
  anim = requestAnimationFrame(frame);
}

function resume(on) {
  running = on === undefined ? !running : on;
  document.getElementById('run').setAttribute('aria-pressed', running);
  document.getElementById('run').textContent = running ? '■ HOLD THE FLOW' : '▶ RESUME THE FLOW';
  if (running) loop(); else { clearTimeout(timer); clearFlow(); }
}

function loop() {
  if (!running) return;
  walk(() => { timer = setTimeout(loop, 120); });
}

/* ---- wiring ------------------------------------------------------------ */
svg.addEventListener('mouseover', e => {
  const b = e.target.closest('.block');
  if (b) read(b.dataset.id);
});
svg.addEventListener('mouseleave', () => read(sel));
svg.addEventListener('click', e => {
  const b = e.target.closest('.block');
  if (b) select(b.dataset.id, true);
});
svg.addEventListener('dblclick', e => {
  const b = e.target.closest('.block');
  if (b) { select(b.dataset.id, true); goInside(); }
});

let drag = null;
svg.addEventListener('pointerdown', e => {
  drag = { x: e.clientX, y: e.clientY, cx: cam.x, cy: cam.y };
  svg.classList.add('drag');
  svg.setPointerCapture(e.pointerId);
});
svg.addEventListener('pointermove', e => {
  if (!drag) return;
  cam.x = drag.cx + (e.clientX - drag.x);
  cam.y = drag.cy + (e.clientY - drag.y);
  applyCam();
});
svg.addEventListener('pointerup', e => { drag = null; svg.classList.remove('drag'); });
svg.addEventListener('wheel', e => {
  e.preventDefault();
  zoom(Math.exp(-e.deltaY * 0.0016), e.clientX, e.clientY);
}, { passive: false });

function zoom(factor, px, py) {
  const r = svg.getBoundingClientRect();
  const x = (px === undefined ? r.width / 2 : px - r.left);
  const y = (py === undefined ? r.height / 2 : py - r.top);
  const k = Math.max(0.15, Math.min(6, cam.k * factor));
  const s = k / cam.k;
  cam.x = x - (x - cam.x) * s;
  cam.y = y - (y - cam.y) * s;
  cam.k = k;
  applyCam();
}

sidebar.addEventListener('click', e => {
  const entry = e.target.closest('.entry');
  if (entry) select(entry.dataset.id, false);
});
sidebar.addEventListener('mouseover', e => {
  const entry = e.target.closest('.entry');
  if (entry) read(entry.dataset.id);
});

document.getElementById('run').addEventListener('click', () => resume());
document.getElementById('step').addEventListener('click', () => { resume(false); walk(() => {}); });
document.getElementById('reset').addEventListener('click', () => {
  stack = []; showLevel(''); cam = Object.assign({}, home); applyCam();
});
document.getElementById('zin').addEventListener('click', () => zoom(1.25));
document.getElementById('zout').addEventListener('click', () => zoom(0.8));

for (const t of document.querySelectorAll('.tab')) {
  t.addEventListener('click', () => {
    tab = t.dataset.tab;
    for (const o of document.querySelectorAll('.tab')) o.classList.toggle('on', o === t);
    read(sel);
  });
}

window.addEventListener('keydown', e => {
  const keys = { ArrowRight: goInside, ArrowLeft: comeOut,
                 ArrowDown: () => move(1), ArrowUp: () => move(-1) };
  if (keys[e.key]) { e.preventDefault(); keys[e.key](); }
  else if (e.key === ' ') { e.preventDefault(); resume(); }
  else if (e.key === '.') { resume(false); walk(() => {}); }
});
window.addEventListener('resize', fit);

paintSidebar();
showLevel('');
"""


def _sections(sections) -> list[dict]:
    return [{"heading": s.heading, "body": s.body} for s in sections]


def _node_meta(scene: Scene) -> dict:
    depth = {}
    for node in scene.nodes:
        depth[node.id] = 1 if node.parent else 0
    return {
        n.id: {
            "id": n.id,
            "key": n.key,
            "name": n.name,
            "group": n.group,
            "count": n.count,
            "lines": n.lines,
            "fan_in": n.fan_in,
            "calls": n.calls,
            "what": n.what,
            "built": n.built or f"{n.lines} lines of code.",
            "depth": depth[n.id],
            "where": n.id,
        }
        for n in scene.nodes
    }


def build(scene: Scene, levels: dict[str, dict]) -> str:
    meta = _node_meta(scene)

    payload = {
        "eyebrow": scene.eyebrow or scene.repo.upper(),
        "title": scene.title,
        "subtitle": scene.subtitle,
        "traced": scene.traced,
        "sep": EDGE_SEP,
        "what": _sections(scene.what),
        "built": _sections(scene.built),
        "groups": [{"title": g.title, "nodes": g.nodes} for g in scene.groups],
        "nodes": meta,
        "levels": {},
    }

    for name, rendered in levels.items():
        if name == "":
            order = list(dict.fromkeys(nid for g in scene.groups for nid in g.nodes))
            order = order or [n.id for n in scene.nodes]
            hops = [list(h) for h in scene.hops]
            inner_meta = {}
        else:
            node = scene.node(name)
            order = [n.id for n in node.inside]
            hops = [[e.src, e.dst] for e in node.inside_edges]
            inner_meta = {
                n.id: {
                    "id": n.id, "key": n.key, "name": n.name, "group": node.name,
                    "count": n.count, "lines": n.lines, "fan_in": n.fan_in,
                    "calls": n.calls, "what": n.what, "built": n.built, "depth": 0,
                    "where": f"{name} · {n.id.rsplit('::', 1)[-1]}",
                }
                for n in node.inside
            }
        payload["nodes"].update(inner_meta)
        payload["levels"][name] = {
            "box": rendered["box"],
            "paths": rendered["paths"],
            "hops": [h for h in hops if key(h[0], h[1]) in rendered["paths"]],
            "order": order,
        }

    svg_body = "".join(rendered["svg"] for rendered in levels.values())

    cells = [
        '<div class="cell identity"><span class="label">REPOSITORY</span>'
        f'<span class="value">{html.escape(scene.repo)} · {html.escape(scene.variant)}</span></div>'
    ]
    for stat in scene.stats:
        cells.append(
            f'<div class="cell"><span class="label">{html.escape(stat.label)}</span>'
            f'<span class="value">{html.escape(stat.value)}</span></div>'
        )
    cells.append('<div class="spacer"></div>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(scene.repo)} — {html.escape(scene.title)}</title>
<style>{CSS}</style>
</head>
<body>
<div id="app">
  <header class="topbar">
    {''.join(cells)}
    <div class="controls">
      <button id="run" aria-pressed="false">▶ RESUME THE FLOW</button>
      <button id="step">TRACE ONE STEP</button>
      <button id="reset">RESET VIEW</button>
    </div>
  </header>
  <main>
    <nav class="sidebar" id="sidebar"></nav>
    <section class="canvas">
      <svg id="plane" xmlns="http://www.w3.org/2000/svg">
        <defs>{PATTERNS}</defs>
        <g id="stage">{svg_body}</g>
      </svg>
      <div class="zoom">
        <button id="zin">+</button><button id="zout">−</button>
      </div>
      <div class="hint">{HINT}</div>
    </section>
    <aside class="panel">
      <div class="tabs">
        <div class="tab on" data-tab="what">What it does</div>
        <div class="tab" data-tab="built">How it's built</div>
      </div>
      <div class="panel-body" id="panel-body"></div>
    </aside>
  </main>
</div>
<script>window.__MAP__ = {json.dumps(payload)};</script>
<script>{SCRIPT}</script>
</body>
</html>
"""

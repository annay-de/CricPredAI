"""Cricket particle morph — the signature hero animation.

A canvas-2D constellation of ~2,000 particles in the Dala spectrum that
morphs between three silhouettes: a seamed cricket ball (the seam is a
dense double-stitched band), a bat, and a batsman in follow-through.
Continuous simplex-style drift, breathing scale, cursor repulsion, a
sparse ambient layer, reduced-motion and offscreen handling. No
dependencies; rendered via components.html.
"""

from __future__ import annotations


def particles_html() -> str:
    return _HTML


_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:transparent;height:100%;overflow:hidden}
  #wrap{position:relative;width:100%;height:100vh}
  canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
</style>
</head>
<body>
<div id="wrap"><canvas id="cv"></canvas></div>
<script>
(function(){
"use strict";
const cv = document.getElementById("cv");
const ctx = cv.getContext("2d");
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- spectrum: violet dominant ---------- */
const SPECTRUM = [
  ["#8052ff", 0.46],
  ["#9d7bff", 0.12],
  ["#6a5cff", 0.08],
  ["#c26bff", 0.06],
  ["#5285ff", 0.06],
  ["#e254d8", 0.05],
  ["#ffb829", 0.07],
  ["#15846e", 0.06],
  ["#bdbdbd", 0.04],
];
function pickColor(){
  let r = Math.random(), acc = 0;
  for (const [c, w] of SPECTRUM){ acc += w; if (r <= acc) return c; }
  return "#8052ff";
}

/* ---------- silhouettes ---------- */
/* helpers: build silhouettes from primitives so anatomy stays clean */
function quad(x1, y1, x2, y2, w){
  const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1;
  const nx = -dy / L * w / 2, ny = dx / L * w / 2;
  return `M ${x1+nx} ${y1+ny} L ${x2+nx} ${y2+ny} L ${x2-nx} ${y2-ny} L ${x1-nx} ${y1-ny} Z`;
}
function circlePath(cx, cy, r){
  return `M ${cx} ${cy} m ${-r} 0 a ${r} ${r} 0 1 0 ${2*r} 0 a ${r} ${r} 0 1 0 ${-2*r} 0 Z`;
}

/* bat: real proportions — short round handle, hard shoulders, straight
   blade, rounded toe. The V-splice is cut out as a particle void. */
const BAT_D =
  "M90.5 14 Q90.5 6 100 6 Q109.5 6 109.5 14 L109.5 122 " +
  "L136 127 L139 138 L139 350 Q139 388 100 388 Q61 388 61 350 L61 138 L64 127 L90.5 122 Z";
const BAT_SPLICE_D = "M86 130 L114 130 L100 196 Z";

/* batsman: side-on lofted-drive follow-through, built as a limb skeleton —
   torso leaning into the shot, front leg striding, both arms extended
   up and through, bat finishing high */
const MAN_SEGS = [
  [172,  84, 181, 148, 36],   /* upper torso */
  [181, 148, 189, 206, 32],   /* lower torso */
  [193, 206, 250, 268, 25],   /* front thigh */
  [250, 268, 269, 348, 18],   /* front shin */
  [266, 350, 302, 360, 13],   /* front foot */
  [173, 208, 142, 282, 24],   /* back thigh */
  [142, 282, 128, 356, 17],   /* back shin */
  [130, 358,  94, 368, 12],   /* back foot */
  [180, 102, 240,  74, 17],   /* lead upper arm */
  [240,  74, 294,  46, 14],   /* lead forearm */
  [166, 112, 224,  96, 15],   /* trail upper arm */
  [224,  96, 286,  60, 13],   /* trail forearm */
  [294,  44, 320,  18, 10],   /* bat handle */
  [320,  18, 374, -34, 26],   /* bat blade, finishing high */
];
const MAN_D =
  MAN_SEGS.map(s => quad(...s)).join(" ") + " " + circlePath(174, 56, 21);

function sampleSvgPath(d, vw, vh, n, edgeFrac, holeD, yMin){
  yMin = yMin === undefined ? 0 : yMin;
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("width", "0"); svg.setAttribute("height", "0");
  svg.style.position = "absolute";
  const p = document.createElementNS(NS, "path");
  p.setAttribute("d", d);
  svg.appendChild(p);
  let pHole = null;
  if (holeD){
    pHole = document.createElementNS(NS, "path");
    pHole.setAttribute("d", holeD);
    svg.appendChild(pHole);
  }
  document.body.appendChild(svg);
  const path2d = new Path2D(d);
  const hole2d = holeD ? new Path2D(holeD) : null;
  const mctx = document.createElement("canvas").getContext("2d");
  const pts = [];
  const L = p.getTotalLength();
  const nEdgeTotal = Math.floor(n * edgeFrac);
  const nHoleEdge = pHole ? Math.floor(nEdgeTotal * 0.35) : 0;
  for (let i = 0; i < nEdgeTotal - nHoleEdge; i++){
    const pt = p.getPointAtLength(Math.random() * L);
    pts.push([pt.x + (Math.random() - .5) * 3, pt.y + (Math.random() - .5) * 3]);
  }
  if (pHole){
    const LH = pHole.getTotalLength();
    for (let i = 0; i < nHoleEdge; i++){
      const pt = pHole.getPointAtLength(Math.random() * LH);
      pts.push([pt.x + (Math.random() - .5) * 2, pt.y + (Math.random() - .5) * 2]);
    }
  }
  let guard = 0;
  while (pts.length < n && guard < n * 400){
    guard++;
    const x = Math.random() * vw;
    const y = yMin + Math.random() * (vh - yMin);
    if (!mctx.isPointInPath(path2d, x, y)) continue;
    if (hole2d && mctx.isPointInPath(hole2d, x, y)) continue;
    pts.push([x, y]);
  }
  while (pts.length < n) pts.push(pts[(Math.random() * pts.length) | 0].slice());
  document.body.removeChild(svg);
  return pts;
}

/* seamed ball: procedural. Circle + a dense tilted seam band with two
   stitching rows and cross ticks — the seam must read instantly. */
function sampleBall(n){
  const pts = [];
  const R = 1;
  const nEdge  = Math.floor(n * 0.17);
  const nFill  = Math.floor(n * 0.53);
  const nSeam  = n - nEdge - nFill;
  for (let i = 0; i < nEdge; i++){
    const a = Math.random() * Math.PI * 2;
    const r = R * (0.985 + Math.random() * 0.03);
    pts.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  for (let i = 0; i < nFill; i++){
    const a = Math.random() * Math.PI * 2;
    const r = R * Math.sqrt(Math.random()) * 0.985;
    pts.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  /* seam: the visible half of a great circle tilted toward the viewer —
     one bowed band running pole to pole, with two stitching rows and
     cross ticks. This is the "cricket ball" tell. */
  const bow = 0.30;                       /* how far the band bulges */
  const rows = [-0.05, 0.05];             /* stitching rows, offset in x */
  let i = 0;
  while (i < nSeam){
    const th = (Math.random() * 2 - 1) * (Math.PI / 2) * 0.97;  /* front half */
    const row = rows[i % 2];
    let x = bow * Math.sin(th) + row;
    let y = Math.sin(th) * 0.0 + Math.cos(th) * 0;              /* placeholder */
    y = Math.sign(th) * (1 - Math.cos(th)) ; /* not used */
    /* param along the band: y goes pole to pole */
    y = Math.sin(th) >= 0 ? 0 : 0;
    y = th / (Math.PI / 2) * 0.95;          /* linear pole-to-pole */
    x = bow * Math.cos(y * (Math.PI / 2) / 0.95) + row;
    /* cross-stitch ticks every so often */
    if (i % 8 === 0) x += (Math.random() < .5 ? 1 : -1) * 0.035;
    x += (Math.random() - .5) * 0.012;
    y += (Math.random() - .5) * 0.012;
    if (x * x + y * y <= R * R * 0.98){ pts.push([x, y]); }
    else { pts.push([x * 0.95, y * 0.95]); }
    i++;
  }
  return pts;
}

function rotated(pts, angle){
  const c = Math.cos(angle), s = Math.sin(angle);
  let mx = 0, my = 0;
  for (const [x, y] of pts){ mx += x; my += y; }
  mx /= pts.length; my /= pts.length;
  return pts.map(([x, y]) => {
    const dx = x - mx, dy = y - my;
    return [mx + dx * c - dy * s, my + dx * s + dy * c];
  });
}

/* fit a point cloud into a centered box */
function fit(pts, cw, ch, scaleFactor){
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  for (const [x, y] of pts){
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
  }
  const w = maxX - minX, h = maxY - minY;
  const s = Math.min(cw / w, ch / h) * scaleFactor;
  const ox = cw / 2 - (minX + w / 2) * s;
  const oy = ch / 2 - (minY + h / 2) * s;
  return pts.map(([x, y]) => [x * s + ox, y * s + oy]);
}

/* ---------- particle field ---------- */
let W = 0, H = 0, dpr = 1;
let parts = [], ambient = [];
let shapes = [];               /* [ball, bat, man] target arrays */
let N = 0;

function shuffled(arr){
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--){
    const j = (Math.random() * (i + 1)) | 0;
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function build(){
  const rect = cv.parentElement.getBoundingClientRect();
  W = Math.max(300, rect.width); H = Math.max(300, rect.height);
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  cv.width = W * dpr; cv.height = H * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const mobile = W < 520;
  N = mobile ? 760 : 1900;

  const ball = fit(sampleBall(N), W, H, 0.74);
  const bat  = fit(rotated(sampleSvgPath(BAT_D, 200, 400, N, 0.36, BAT_SPLICE_D), 0.16), W, H, 0.8);
  const man  = fit(sampleSvgPath(MAN_D, 400, 440, N, 0.30, null, -60), W, H, 0.86);
  /* shuffle assignment per shape so morphs cross-fade organically */
  shapes = [ball, shuffled(bat), shuffled(man)];

  parts = [];
  for (let i = 0; i < N; i++){
    parts.push({
      x: shapes[0][i][0], y: shapes[0][i][1],
      sx: 0, sy: 0,
      color: pickColor(),
      size: 1.4 + Math.random() * 1.8,
      tri: Math.random() < 0.10,
      p1: Math.random() * 6.28, p2: Math.random() * 6.28,
      f1: 0.25 + Math.random() * 0.35, f2: 0.18 + Math.random() * 0.3,
      amp: 3 + Math.random() * 3,
      stag: Math.random() * 400,
    });
  }
  const nAmb = Math.floor(N * 0.10);
  ambient = [];
  for (let i = 0; i < nAmb; i++){
    ambient.push({
      x: Math.random() * W, y: Math.random() * H,
      color: pickColor(),
      size: 0.9 + Math.random() * 1.4,
      p1: Math.random() * 6.28, p2: Math.random() * 6.28,
      f1: 0.1 + Math.random() * 0.2, f2: 0.08 + Math.random() * 0.15,
      amp: 8 + Math.random() * 14,
    });
  }
}

/* ---------- choreography ---------- */
const HOLD = 8500, MORPH = 2500, STAGMAX = 400;
let shapeIdx = 0, nextIdx = 1, morphStart = -1, holdStart = 0;
const cubic = t => t < .5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3) / 2;

let mouseX = -1e5, mouseY = -1e5;
cv.addEventListener("pointermove", e => {
  const r = cv.getBoundingClientRect();
  mouseX = e.clientX - r.left; mouseY = e.clientY - r.top;
});
cv.addEventListener("pointerleave", () => { mouseX = -1e5; mouseY = -1e5; });

let running = true, visible = true;
document.addEventListener("visibilitychange", () => {
  running = !document.hidden && visible;
  if (running) requestAnimationFrame(frame);
});
new IntersectionObserver(entries => {
  visible = entries[0].isIntersecting;
  const was = running;
  running = visible && !document.hidden;
  if (running && !was) requestAnimationFrame(frame);
}).observe(cv);

function drawStatic(){
  ctx.clearRect(0, 0, W, H);
  const buckets = new Map();
  for (const p of parts){
    if (!buckets.has(p.color)) buckets.set(p.color, []);
    buckets.get(p.color).push(p);
  }
  for (const [color, list] of buckets){
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.9;
    ctx.beginPath();
    for (const p of list) ctx.rect(p.x - p.size/2, p.y - p.size/2, p.size, p.size);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

let last = performance.now();
function frame(now){
  if (!running) return;
  const t = now / 1000;
  last = now;

  /* state machine */
  if (morphStart < 0 && now - holdStart > HOLD){
    morphStart = now;
    nextIdx = (shapeIdx + 1) % 3;
    for (let i = 0; i < N; i++){
      parts[i].sx = shapes[shapeIdx][i][0];
      parts[i].sy = shapes[shapeIdx][i][1];
    }
  }
  let morphing = morphStart >= 0;
  if (morphing && now - morphStart > MORPH + STAGMAX){
    shapeIdx = nextIdx; morphStart = -1; holdStart = now; morphing = false;
  }

  const breathe = 1 + 0.014 * Math.sin(t * 0.5);
  const cx = W / 2, cy = H / 2;

  ctx.clearRect(0, 0, W, H);

  /* ambient layer */
  ctx.globalAlpha = 0.28;
  for (const a of ambient){
    const dx = Math.sin(t * a.f1 + a.p1) * a.amp;
    const dy = Math.cos(t * a.f2 + a.p2) * a.amp;
    ctx.fillStyle = a.color;
    ctx.fillRect(a.x + dx, a.y + dy, a.size, a.size);
  }
  ctx.globalAlpha = 1;

  /* shape field, batched by color; dots filled, triangles stroked */
  const dotB = new Map(), triB = new Map();
  for (let i = 0; i < N; i++){
    const p = parts[i];
    let lx, ly;
    if (morphing){
      const prog = Math.min(1, Math.max(0, (now - morphStart - p.stag) / MORPH));
      const e = cubic(prog);
      const tgt = shapes[nextIdx][i];
      lx = p.sx + (tgt[0] - p.sx) * e;
      ly = p.sy + (tgt[1] - p.sy) * e;
    } else {
      lx = shapes[shapeIdx][i][0];
      ly = shapes[shapeIdx][i][1];
    }
    /* perpetual drift */
    lx += Math.sin(t * p.f1 * 6.28 + p.p1) * p.amp * 0.5
        + Math.sin(t * p.f2 * 3.1 + p.p2) * p.amp * 0.3;
    ly += Math.cos(t * p.f2 * 6.28 + p.p2) * p.amp * 0.5
        + Math.cos(t * p.f1 * 2.7 + p.p1) * p.amp * 0.3;
    /* breathing about center */
    lx = cx + (lx - cx) * breathe;
    ly = cy + (ly - cy) * breathe;
    /* cursor repulsion */
    const mdx = lx - mouseX, mdy = ly - mouseY;
    const md2 = mdx * mdx + mdy * mdy;
    if (md2 < 4900){
      const md = Math.sqrt(md2) || 1;
      const push = (70 - md) / 70 * 22;
      lx += (mdx / md) * push; ly += (mdy / md) * push;
    }
    p.x = lx; p.y = ly;
    const B = p.tri ? triB : dotB;
    if (!B.has(p.color)) B.set(p.color, []);
    B.get(p.color).push(p);
  }
  for (const [color, list] of dotB){
    ctx.fillStyle = color;
    ctx.beginPath();
    for (const p of list) ctx.rect(p.x - p.size/2, p.y - p.size/2, p.size, p.size);
    ctx.fill();
  }
  ctx.lineWidth = 0.8;
  for (const [color, list] of triB){
    ctx.strokeStyle = color;
    ctx.beginPath();
    for (const p of list){
      const s = p.size * 1.6;
      ctx.moveTo(p.x, p.y - s);
      ctx.lineTo(p.x + s * 0.87, p.y + s * 0.5);
      ctx.lineTo(p.x - s * 0.87, p.y + s * 0.5);
      ctx.closePath();
    }
    ctx.stroke();
  }
  requestAnimationFrame(frame);
}

let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { build(); if (reduced) drawStatic(); }, 180);
});

/* test hook */
window.__jump = i => { shapeIdx = i; nextIdx = (i + 1) % 3; morphStart = -1; holdStart = performance.now(); };

build();
if (reduced){
  drawStatic();           /* static seamed ball, no motion */
} else {
  holdStart = performance.now();
  requestAnimationFrame(frame);
}
})();
</script>
</body>
</html>
"""

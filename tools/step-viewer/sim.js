// The layout viewer's simulation layer (tools/step-viewer/layout.html): sim.json's circuit (sim/multiplier_waveforms.py)
// laid on the model's parts (sim/tube_geometry.py --layout, their nets). Potential: every conductor takes its net's
// voltage on one diverging scale (blue negative, grey REF, red positive); the parts a voltage grades along (the sticks,
// the surge resistors, the capacitors, the clamp strings) are shaded along their length; insulators fade. Conduction:
// each diode and clamp is lit while it passes current. Two clocks: the steady cycle (1 / 120 s, the vanes' 60 degrees
// of relative rotation, 360 points) and the start-up (every cycle's mean, from the 1 kV seed to the rings settled).
import * as THREE from "three";

// ---------------------------------------------------------------- the diverging scale, interpolated in OKLab
const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const gam = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);
function hexRGB(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]; }
function toLab([r, g, b]) {
  const R = lin(r), G = lin(g), B = lin(b);
  const l = Math.cbrt(0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B);
  const m = Math.cbrt(0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B);
  const s = Math.cbrt(0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B);
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
          0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}
function fromLab([L, a, b]) {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const rgb = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
               -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
  return rgb.map((c) => Math.min(1, Math.max(0, gam(Math.max(0, c)))));
}
// n steps from neg through mid to pos (sRGB 0..1); equal steps per arm
export function divergingLUT(neg, mid, pos, n = 129) {
  const A = toLab(hexRGB(neg)), M = toLab(hexRGB(mid)), P = toLab(hexRGB(pos));
  const out = [];
  for (let i = 0; i < n; i++) {
    const u = (i / (n - 1)) * 2 - 1, w = Math.abs(u), E = u < 0 ? A : P;
    out.push(fromLab([0, 1, 2].map((k) => M[k] + (E[k] - M[k]) * w)));
  }
  return out;
}
export const lutAt = (lut, v, vmax) => lut[Math.round(((Math.max(-vmax, Math.min(vmax, v)) / vmax) + 1) / 2 * (lut.length - 1))];
export const cssOf = (c) => `rgb(${c.map((x) => Math.round(x * 255)).join(",")})`;

// ---------------------------------------------------------------- the clocks
// the voltages and currents at a phase of the steady cycle (0..1, linear between the 360 points, wrapping)
export function atPhase(D, ph) {
  const n = D.cycle.theta.length, x = ((ph % 1) + 1) % 1 * n, i = Math.floor(x) % n, j = (i + 1) % n, f = x - Math.floor(x);
  const V = { "0": 0 }, I = {};
  for (const [nd, y] of Object.entries(D.cycle.V)) V[nd] = y[i] + (y[j] - y[i]) * f;
  for (const [nm, y] of Object.entries(D.cycle.I)) I[nm] = y[i];              // bin means: held over their bin
  return { V, I };
}
// each node's mean at a point of the start-up (a cycle index, fractional)
export function atCycle(D, c) {
  const m = D.startup.mean, n = m["1"].length, x = Math.max(0, Math.min(n - 1, c)), i = Math.floor(x), j = Math.min(n - 1, i + 1);
  const f = x - i, V = { "0": 0 };
  for (const [nd, y] of Object.entries(m)) V[nd] = y[i] + (y[j] - y[i]) * f;
  return { V, I: null };
}

// ---------------------------------------------------------------- the parts
export function initSim(S, D) {
  const nets = D.nets, single = [], graded = [], devices = [], faded = [];
  const peak = {};
  for (const [nm, d] of Object.entries(D.devices)) peak[nm] = Math.max(1e-9, d.I_peak_mA * 1000);   // uA
  S.root.updateMatrixWorld(true);
  const w = new THREE.Vector3();
  for (const p of S.parts) {
    const n = nets[p.part];
    const m = p.mesh.material;
    p.baseMetal = m.metalness; p.baseRough = m.roughness;
    if (!n) { faded.push(p); continue; }
    if (n.net) { single.push({ p, net: n.net }); }
    else {
      // per vertex, the fraction along the part from its first net to its second (at rotor angle 0; the spin is rigid)
      p.mesh.geometry = p.mesh.geometry.clone();
      const pos = p.mesh.geometry.attributes.position, f = new Float32Array(pos.count);
      for (let k = 0; k < pos.count; k++) {
        w.fromBufferAttribute(pos, k).applyMatrix4(p.mesh.matrixWorld).multiplyScalar(1000);       // mm
        if (n.axis) {
          const [a, b] = n.axis, d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
          const L2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
          f[k] = Math.min(1, Math.max(0, ((w.x - a[0]) * d[0] + (w.y - a[1]) * d[1] + (w.z - a[2]) * d[2]) / L2));
        } else {
          const [t0, t1] = n.arc.th, span = ((t1 - t0 + 540) % 360) - 180;
          const t = ((Math.atan2(w.y, w.x) * 180 / Math.PI - t0 + 540) % 360) - 180;
          f[k] = Math.min(1, Math.max(0, t / span));
        }
      }
      p.mesh.geometry.setAttribute("color", new THREE.BufferAttribute(new Float32Array(pos.count * 3), 3));
      graded.push({ p, nets: n.nets, f });
    }
    if (n.device) {                                                // the clamp strings' parts are Z1 / Z4, their devices z1 / z4
      const dev = D.devices[n.device] ? n.device : n.device.toLowerCase();
      if (D.devices[dev]) devices.push({ p, dev });
    }
  }
  let mode = "materials";
  const glow = new THREE.Color(1.0, 0.66, 0.08);
  const col = new THREE.Color();
  return {
    devices, single, graded, faded,
    get mode() { return mode; },
    setMode(m, lutRef) {
      mode = m;
      const pot = m === "potential";
      for (const p of S.parts) {
        const mt = p.mesh.material;
        mt.color.copy(p.base); mt.opacity = p.baseOpacity; mt.transparent = p.potted; mt.depthWrite = !p.potted;
        mt.metalness = p.baseMetal; mt.roughness = p.baseRough; mt.emissive.setRGB(0, 0, 0); mt.vertexColors = false;
        p.mesh.renderOrder = p.potted ? 2 : 0;
      }
      if (pot) {
        for (const p of faded) {                                   // insulators and the LV parts: a pale ghost
          const mt = p.mesh.material;
          mt.color.setRGB(0.80, 0.81, 0.80, THREE.SRGBColorSpace); mt.transparent = true; mt.opacity = p.potted ? 0.10 : 0.16;
          mt.depthWrite = false; mt.metalness = 0.0; p.mesh.renderOrder = 3;
        }
        for (const g of graded) { g.p.mesh.material.vertexColors = true; g.p.mesh.material.color.setRGB(1, 1, 1); }
        for (const s of single) { s.p.mesh.material.metalness = 0.15; s.p.mesh.material.roughness = 0.55; }
        for (const g of graded) { g.p.mesh.material.metalness = 0.1; g.p.mesh.material.roughness = 0.6; }
      }
      for (const p of S.parts) p.mesh.material.needsUpdate = true;
    },
    // paint the parts for one instant: V {net: volts}, I {device: uA} or null
    apply(st, lut, vmax) {
      if (mode !== "potential") return;
      for (const { p, net } of single) {
        const c = lutAt(lut, st.V[net] ?? 0, vmax);
        p.mesh.material.color.setRGB(c[0], c[1], c[2], THREE.SRGBColorSpace);
      }
      for (const { p, nets: [a, b], f } of graded) {
        const va = st.V[a] ?? 0, vb = st.V[b] ?? 0, arr = p.mesh.geometry.attributes.color;
        for (let k = 0; k < f.length; k++) {
          const c = lutAt(lut, va + (vb - va) * f[k], vmax);
          arr.array[3 * k] = lin(c[0]); arr.array[3 * k + 1] = lin(c[1]); arr.array[3 * k + 2] = lin(c[2]);
        }
        arr.needsUpdate = true;
      }
      for (const { p, dev } of devices) {
        const i = st.I ? Math.max(0, st.I[dev] || 0) / peak[dev] : 0;
        p.mesh.material.emissive.copy(col.copy(glow).multiplyScalar(i > 0.01 ? 0.35 + 0.9 * Math.min(1, i) : 0));
      }
    },
  };
}

// ---------------------------------------------------------------- the charts (SVG, drawn from the theme's tokens)
const NS = "http://www.w3.org/2000/svg";
const el = (tag, at = {}, parent) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(at)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
};

// every node's voltage through one cycle, one row each on a shared scale, filled by sign as the 3-D paints it
export function nodeStrips(host, D, rows, vmax, onHover) {
  host.textContent = "";
  const W = 300, LBL = 54, VAL = 58, H = 20, GAP = 3, PW = W - LBL - VAL, n = D.cycle.theta.length;
  const svg = el("svg", { viewBox: `0 0 ${W} ${rows.length * (H + GAP) + 18}`, class: "strips", role: "img",
                          "aria-label": "Every node's voltage through one steady cycle" }, host);
  const x = (i) => LBL + (i / n) * PW;
  const vals = [];
  rows.forEach(([nd, name], r) => {
    const y0 = r * (H + GAP), mid = y0 + H / 2, yv = (v) => mid - (v / vmax) * (H / 2);
    el("line", { x1: LBL, x2: LBL + PW, y1: mid, y2: mid, class: "zero" }, svg);
    const ys = D.cycle.V[nd];
    let line = "", area = `M${x(0)},${mid}`;
    ys.forEach((v, i) => { line += `${i ? "L" : "M"}${x(i).toFixed(1)},${yv(v).toFixed(2)}`; area += `L${x(i).toFixed(1)},${yv(v).toFixed(2)}`; });
    area += `L${x(n)},${yv(ys[0])}L${x(n)},${mid}Z`;
    const id = `clip-${nd}`;
    const defs = el("defs", {}, svg);
    const ca = el("clipPath", { id: id + "-p" }, defs); el("rect", { x: LBL, y: y0, width: PW, height: H / 2 }, ca);
    const cb = el("clipPath", { id: id + "-n" }, defs); el("rect", { x: LBL, y: mid, width: PW, height: H / 2 }, cb);
    el("path", { d: area, class: "fill-pos", "clip-path": `url(#${id}-p)` }, svg);
    el("path", { d: area, class: "fill-neg", "clip-path": `url(#${id}-n)` }, svg);
    el("path", { d: line, class: "wave" }, svg);
    const t = el("text", { x: 0, y: mid + 4, class: "row-label" }, svg); t.textContent = name;
    const v = el("text", { x: W, y: mid + 4, class: "row-value", "text-anchor": "end" }, svg);
    vals.push([nd, v]);
  });
  const axisY = rows.length * (H + GAP) + 12;
  for (const deg of [0, 15, 30, 45, 60]) {
    const t = el("text", { x: LBL + (deg / 60) * PW, y: axisY, class: "tick", "text-anchor": deg === 0 ? "start" : deg === 60 ? "end" : "middle" }, svg);
    t.textContent = `${deg}°`;
  }
  const cur = el("line", { y1: 0, y2: rows.length * (H + GAP) - GAP, class: "cursor" }, svg);
  const hov = el("line", { y1: 0, y2: rows.length * (H + GAP) - GAP, class: "hover", visibility: "hidden" }, svg);
  const hit = el("rect", { x: LBL, y: 0, width: PW, height: rows.length * (H + GAP), fill: "transparent" }, svg);
  const toPh = (ev) => { const b = svg.getBoundingClientRect(); return Math.min(0.9999, Math.max(0, ((ev.clientX - b.left) / b.width * W - LBL) / PW)); };
  hit.addEventListener("pointermove", (ev) => onHover && onHover(toPh(ev)));
  hit.addEventListener("pointerleave", () => onHover && onHover(null));
  return {
    set(ph, st, hoverPh) {
      const xx = LBL + ph * PW;
      cur.setAttribute("x1", xx); cur.setAttribute("x2", xx);
      if (hoverPh == null) hov.setAttribute("visibility", "hidden");
      else { const hx = LBL + hoverPh * PW; hov.setAttribute("x1", hx); hov.setAttribute("x2", hx); hov.setAttribute("visibility", "visible"); }
      for (const [nd, t] of vals) { const v = st.V[nd] / 1000; t.textContent = `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2)}`; }
    },
  };
}

// each diode's and clamp's current through one cycle, each row on its own peak, lit where it conducts
export function deviceStrips(host, D, rows, onHover) {
  host.textContent = "";
  const W = 300, LBL = 54, VAL = 58, H = 14, GAP = 3, PW = W - LBL - VAL, n = D.cycle.theta.length;
  const svg = el("svg", { viewBox: `0 0 ${W} ${rows.length * (H + GAP) + 18}`, class: "strips", role: "img",
                          "aria-label": "When each diode and clamp conducts through one steady cycle" }, host);
  const x = (i) => LBL + (i / n) * PW;
  const dots = [];
  rows.forEach(([nm, name], r) => {
    const y0 = r * (H + GAP), base = y0 + H, ys = D.cycle.I[nm], pk = Math.max(...ys.map((v) => Math.max(0, v))) || 1;
    el("line", { x1: LBL, x2: LBL + PW, y1: base, y2: base, class: "zero" }, svg);
    let area = `M${x(0)},${base}`;
    ys.forEach((v, i) => { const y = base - Math.max(0, v) / pk * (H - 1); area += `L${x(i).toFixed(1)},${y.toFixed(2)}L${x(i + 1).toFixed(1)},${y.toFixed(2)}`; });
    area += `L${x(n)},${base}Z`;
    el("path", { d: area, class: "fill-cond" }, svg);
    const t = el("text", { x: 0, y: base - 2, class: "row-label" }, svg); t.textContent = name;
    const pkmA = D.devices[nm].I_peak_mA;
    const v = el("text", { x: W - 10, y: base - 2, class: "row-value", "text-anchor": "end" }, svg);
    v.textContent = pkmA >= 0.1 ? `${pkmA.toFixed(2)} mA` : `${(pkmA * 1000).toFixed(0)} µA`;
    const d = el("circle", { cx: W - 4, cy: base - H / 2 + 1, r: 3.2, class: "lamp" }, svg);
    dots.push([nm, d, ys, pk]);
  });
  const axisY = rows.length * (H + GAP) + 12;
  for (const deg of [0, 15, 30, 45, 60]) {
    const t = el("text", { x: LBL + (deg / 60) * PW, y: axisY, class: "tick", "text-anchor": deg === 0 ? "start" : deg === 60 ? "end" : "middle" }, svg);
    t.textContent = `${deg}°`;
  }
  const cur = el("line", { y1: 0, y2: rows.length * (H + GAP) - GAP, class: "cursor" }, svg);
  const hov = el("line", { y1: 0, y2: rows.length * (H + GAP) - GAP, class: "hover", visibility: "hidden" }, svg);
  const hit = el("rect", { x: LBL, y: 0, width: PW, height: rows.length * (H + GAP), fill: "transparent" }, svg);
  const toPh = (ev) => { const b = svg.getBoundingClientRect(); return Math.min(0.9999, Math.max(0, ((ev.clientX - b.left) / b.width * W - LBL) / PW)); };
  hit.addEventListener("pointermove", (ev) => onHover && onHover(toPh(ev)));
  hit.addEventListener("pointerleave", () => onHover && onHover(null));
  return {
    set(ph, hoverPh) {
      const xx = LBL + ph * PW;
      cur.setAttribute("x1", xx); cur.setAttribute("x2", xx);
      if (hoverPh == null) hov.setAttribute("visibility", "hidden");
      else { const hx = LBL + hoverPh * PW; hov.setAttribute("x1", hx); hov.setAttribute("x2", hx); hov.setAttribute("visibility", "visible"); }
      const i = Math.floor((hoverPh ?? ph) * n) % n;
      for (const [, d, ys, pk] of dots) d.setAttribute("class", ys[i] > 0.01 * pk ? "lamp on" : "lamp");
    },
  };
}

// the start-up: each ring's mean per cycle, and nodes 1 / 4's swing, against time
export function startupChart(host, D, onHover) {
  host.textContent = "";
  const W = 300, H = 150, L = 34, R = 78, T = 8, B = 20, PW = W - L - R, PH = H - T - B;
  const m = D.startup.mean, n = m.ea.length, Tc = D.circuit.period_ms / 1000, tmax = n * Tc, vmax = 16000;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img",
                          "aria-label": "The rings' charge-up from the seed" }, host);
  const x = (i) => L + (i / (n - 1)) * PW, y = (v) => T + (1 - (v + vmax) / (2 * vmax)) * PH;
  for (const kv of [-15, -10, -5, 0, 5, 10, 15]) {
    el("line", { x1: L, x2: L + PW, y1: y(kv * 1000), y2: y(kv * 1000), class: kv === 0 ? "axis" : "grid" }, svg);
    if (kv % 5 === 0) { const t = el("text", { x: L - 4, y: y(kv * 1000) + 3.5, class: "tick", "text-anchor": "end" }, svg); t.textContent = `${kv > 0 ? "+" : kv < 0 ? "−" : ""}${Math.abs(kv)}`; }
  }
  for (const s of [0, 1, 2, 3, 4]) {
    if (s > tmax) continue;
    const t = el("text", { x: L + s / tmax * PW, y: H - 6, class: "tick", "text-anchor": "middle" }, svg); t.textContent = `${s} s`;
  }
  const band = (nd, cls) => {
    let d = "";
    D.startup.max[nd].forEach((v, i) => { d += `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`; });
    for (let i = n - 1; i >= 0; i--) d += `L${x(i).toFixed(1)},${y(D.startup.min[nd][i]).toFixed(1)}`;
    el("path", { d: d + "Z", class: cls }, svg);
  };
  band("4", "band-pos"); band("1", "band-neg");
  const ln = (nd, cls) => { let d = ""; m[nd].forEach((v, i) => { d += `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`; }); el("path", { d, class: cls }, svg); };
  ln("eb", "line-pos"); ln("ea", "line-neg");
  const lab = (v, text) => { const t = el("text", { x: L + PW + 6, y: y(v) + 3.5, class: "end-label" }, svg); t.textContent = text; };
  lab(m.eb[n - 1], `ring B ${(m.eb[n - 1] / 1000).toFixed(2)}`); lab(m.ea[n - 1], `ring A ${(m.ea[n - 1] / 1000).toFixed(2)}`);
  lab(D.startup.max["4"][n - 1] - 2600, "node 4"); lab(D.startup.min["1"][n - 1] + 2600, "node 1");
  const cur = el("line", { y1: T, y2: T + PH, class: "cursor", visibility: "hidden" }, svg);
  const hov = el("line", { y1: T, y2: T + PH, class: "hover", visibility: "hidden" }, svg);
  const hit = el("rect", { x: L, y: T, width: PW, height: PH, fill: "transparent" }, svg);
  const toC = (ev) => { const b = svg.getBoundingClientRect(); return Math.min(n - 1, Math.max(0, ((ev.clientX - b.left) / b.width * W - L) / PW * (n - 1))); };
  hit.addEventListener("pointermove", (ev) => onHover && onHover(toC(ev)));
  hit.addEventListener("pointerleave", () => onHover && onHover(null));
  return {
    set(c, hoverC) {
      if (c == null) cur.setAttribute("visibility", "hidden");
      else { const xx = x(c); cur.setAttribute("x1", xx); cur.setAttribute("x2", xx); cur.setAttribute("visibility", "visible"); }
      if (hoverC == null) hov.setAttribute("visibility", "hidden");
      else { const hx = x(hoverC); hov.setAttribute("x1", hx); hov.setAttribute("x2", hx); hov.setAttribute("visibility", "visible"); }
    },
  };
}

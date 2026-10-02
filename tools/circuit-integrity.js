/* tools/circuit-integrity.js — the JS mirror of sim/circuit_integrity.py (the circuit integrity tool for the DCCREG
 * electrostatic machine). Rebuilds the circuit from a pump-geometry bill of solids — copper that touches is one net,
 * facing foils are a capacitor (fixed / rotating / modulated), spheres across a band are a spark gap — and holds it
 * against the netlist of record (topology_edge_list.csv). Rules I1–I9 as in the Python; gate G-CI holds this file
 * to the Python report (every number and every string). Browser: window.CircuitIntegrity; Node: module.exports.
 */
(function (root) {
  "use strict";
  const TOOL = "circuit-integrity/1";
  const EPS0 = 8.8541878128e-12, EPS_AIR = 1.0006, CONTACT_TOL = 0.01, GAP_NEAR = 15.0, STRAY_MIN_PF = 1.0, DELTA_STEP = 1.0;
  const DRAWN_CAPS = ["C1", "C2", "Ca1", "Cb1", "Cx3", "Cx4", "C_R1"];
  const VARIABLE_CAPS = ["C1", "C2", "Cx3", "Cx4"];
  const CAP_PREFIX = {C1: "C1", C2: "C2", Ca: "Ca1", Cb: "Cb1", Cx3: "Cx3", Cx4: "Cx4", CR: "C_R1"};
  const ALIAS = {"5": "R-A", "6": "R-B", "9": "n18", "10": "n00"};
  const NODE_INFO = {
    "1": "ND1 - A-rail: C1 stator plate + Ca counter-electrode", "2": "ND2 - AR bank: Ca electrode",
    "3": "ND3 - BR bank: Cb electrode", "4": "ND4 - B-rail: C2 stator plate + Cb counter-electrode",
    "R-A": "ND5 - resonator end A: rotor A (C1 rotor face)", "R-B": "ND6 - resonator end B: rotor B (C2 rotor face)",
    "7": "ND7 - island on rotor B (Cx3 bars)", "8": "ND8 - island on rotor A (Cx4 bars)",
    "n18": "ND9 - C_R plate on rotor A (L_R1 to R-A)", "n00": "ND10 - C_R plate on rotor B (L_R2 to R-B)",
    "n17": "Cx3 pickup on ND3 (Lx3 to node 3)", "n23": "Cx4 pickup on ND2 (Lx4 to node 2)"};
  const CONDUCTORS = ["Al foil", "Cu lead", "Cu link", "Cu stem", "Cu bus", "W-Cu sphere", "polished sphere"];
  const EPS_TABLE = [["mica", 5.4], ["garolite", 4.7], ["G10", 4.7], ["kapton", 3.4], ["mylar", 3.2], ["pp_film", 2.2], ["PP film", 2.2]];
  const NODE_TOKEN = /\bnode (R-[AB]|n\d+|\d+)\b/, GROUP_NODE = /\(node (R-[AB]|n\d+|\d+)[,):]/;
  const LEGACY_BODY = {"A-disc": "rotor A", "A-flange": "rotor A", "B-disc": "rotor B", "B-flange": "rotor B"};
  const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI;
  const cmpStr = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  const _f = (x, n) => { const s = x.toFixed(n); return /^-0\.?0*$/.test(s) ? s.slice(1) : s; };

  /* ---- the netlist of record ---- */
  function comp_kind(name){
    if (name.startsWith("SG") || name.startsWith("BS")) return "gap";
    if (name.startsWith("C")) return "capacitor";
    if (name.startsWith("L")) return "inductor";
    return "other";
  }
  function parse_netlist(text){
    const rows = [];
    for (const line of text.split(/\r?\n/)){
      if (!line || line.startsWith("#")) continue;
      const r = []; let cur = "", q = false;
      for (const ch of line){ if (ch === '"') q = !q; else if (ch === "," && !q){ r.push(cur); cur = ""; } else cur += ch; }
      r.push(cur);
      if (r[0] === "component" || r.length < 3) continue;
      rows.push({name: r[0], a: r[1], b: r[2], kind: comp_kind(r[0])});
    }
    return rows;
  }
  function canon(n){
    if (n == null || n === "") return null;
    const s = String(n).split(" ")[0];
    return ALIAS[s] || s;
  }
  const is_conductor = m => CONDUCTORS.some(k => (m || "").includes(k));
  function eps_of(m){
    for (const [k, e] of EPS_TABLE) if ((m || "").includes(k)) return [e, true];
    return [4.7, false];
  }
  const frame_of = body => String(body).startsWith("rotor") ? "rotor" : "stator";

  function parts_from_design(design){
    const glabel = {};
    for (const a of design.assemblies || []) glabel[a.key] = a.label;
    const out = [];
    for (const p of design.parts){
      const mat = p.material || "";
      const body = p.body || LEGACY_BODY[p.carrier || ""] || (p.name.startsWith("septum") ? "rotor AB" : "stator");
      const cond = is_conductor(mat), sh = p.shape || "sector";
      const q = {name: p.name, label: p.label || p.name, group: p.assembly || "", group_label: glabel[p.assembly || ""] || "",
        material: mat, body, frame: frame_of(body), node_raw: cond ? String(p.node != null ? p.node : "") : "",
        node: cond ? canon(p.node) : null};
      if (!cond){ q.kind = "insulator"; [q.eps, q.eps_known] = eps_of(mat); }
      else q.kind = {sector: "foil", sphere: "sphere", rod: "rod"}[sh];
      if (sh === "sector") Object.assign(q, {r_in: p.r_in, r_out: p.r_out, a0: p.start_deg, w: p.w_deg, z0: p.z0, z1: p.z1});
      else if (sh === "sphere") Object.assign(q, {c: p.c.slice(), r: p.r});
      else Object.assign(q, {p0: p.p0.slice(), p1: p.p1.slice(), r: p.r});
      out.push(q);
    }
    return out;
  }

  /* ---- geometry ---- */
  const _sdeg = x => x - 360.0 * Math.floor((x + 180.0) / 360.0);
  const _dist = (p, q) => Math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2);
  const _lerp = (p, q, t) => [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t];
  function _d_pt_sector(pt, s){
    const r = Math.hypot(pt[0], pt[1]), dz = Math.max(0.0, s.z0 - pt[2], pt[2] - s.z1);
    let inside;
    if (s.w >= 360.0 - 1e-9 || r < 1e-12) inside = true;
    else inside = Math.abs(_sdeg(deg(Math.atan2(pt[1], pt[0])) - (s.a0 + s.w / 2))) <= s.w / 2;
    let dp;
    if (inside) dp = Math.max(0.0, s.r_in - r, r - s.r_out);
    else {
      dp = Infinity;
      for (const e of [s.a0, s.a0 + s.w]){
        const ex = Math.cos(rad(e)), ey = Math.sin(rad(e));
        const t = Math.min(s.r_out, Math.max(s.r_in, pt[0] * ex + pt[1] * ey));
        dp = Math.min(dp, Math.hypot(pt[0] - t * ex, pt[1] - t * ey));
      }
    }
    return Math.hypot(dp, dz);
  }
  function _d_seg_sector(p0, p1, s){
    const n = Math.max(1, Math.ceil(_dist(p0, p1) / 1.0 - 1e-9));
    const vals = [];
    for (let i = 0; i <= n; i++) vals.push(_d_pt_sector(_lerp(p0, p1, i / n), s));
    let i = 0;
    for (let k = 1; k <= n; k++) if (vals[k] < vals[i]) i = k;
    let lo = Math.max(0.0, (i - 1) / n), hi = Math.min(1.0, (i + 1) / n);
    for (let it = 0; it < 40; it++){
      const m1 = lo + (hi - lo) / 3, m2 = hi - (hi - lo) / 3;
      if (_d_pt_sector(_lerp(p0, p1, m1), s) < _d_pt_sector(_lerp(p0, p1, m2), s)) hi = m2; else lo = m1;
    }
    return Math.min(vals[i], _d_pt_sector(_lerp(p0, p1, 0.5 * (lo + hi)), s));
  }
  function _d_pt_seg(c, p, q){
    const d = [q[0] - p[0], q[1] - p[1], q[2] - p[2]], L2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
    const t = L2 < 1e-18 ? 0.0 : Math.min(1.0, Math.max(0.0, ((c[0] - p[0]) * d[0] + (c[1] - p[1]) * d[1] + (c[2] - p[2]) * d[2]) / L2));
    return _dist(c, [p[0] + d[0] * t, p[1] + d[1] * t, p[2] + d[2] * t]);
  }
  function _seg_seg(p, q, r, s){
    const d1 = [0, 1, 2].map(i => q[i] - p[i]), d2 = [0, 1, 2].map(i => s[i] - r[i]), w = [0, 1, 2].map(i => p[i] - r[i]);
    const dot = (x, y) => x[0] * y[0] + x[1] * y[1] + x[2] * y[2];
    const a = dot(d1, d1), e = dot(d2, d2), f_ = dot(d2, w), cl = x => Math.min(1.0, Math.max(0.0, x));
    let t, u;
    if (a < 1e-18 && e < 1e-18) return _dist(p, r);
    if (a < 1e-18){ t = 0.0; u = cl(f_ / e); }
    else {
      const c = dot(d1, w);
      if (e < 1e-18){ t = cl(-c / a); u = 0.0; }
      else {
        const bb = dot(d1, d2), den = a * e - bb * bb;
        t = den > 1e-12 ? cl((bb * f_ - c * e) / den) : 0.0;
        u = (bb * t + f_) / e;
        if (u < 0.0){ t = cl(-c / a); u = 0.0; }
        else if (u > 1.0){ t = cl((bb - c) / a); u = 1.0; }
      }
    }
    return _dist([0, 1, 2].map(i => p[i] + d1[i] * t), [0, 1, 2].map(i => r[i] + d2[i] * u));
  }
  function _seg_rminmax(p, q){
    const dx = q[0] - p[0], dy = q[1] - p[1], L2 = dx * dx + dy * dy;
    const t = L2 < 1e-18 ? 0.0 : Math.min(1.0, Math.max(0.0, -(p[0] * dx + p[1] * dy) / L2));
    return [Math.hypot(p[0] + t * dx, p[1] + t * dy), Math.max(Math.hypot(p[0], p[1]), Math.hypot(q[0], q[1]))];
  }
  function _iv(a0, w){
    if (w >= 360.0 - 1e-9) return [[0.0, 360.0]];
    const s = a0 - 360.0 * Math.floor(a0 / 360.0), e = s + w;
    return e <= 360.0 ? [[s, e]] : [[s, 360.0], [0.0, e - 360.0]];
  }
  function _merge(ivs){
    const out = [];
    for (const [s, e] of ivs.slice().sort((x, y) => x[0] - y[0] || x[1] - y[1])){
      if (out.length && s <= out[out.length - 1][1] + 1e-12){ if (e > out[out.length - 1][1]) out[out.length - 1] = [out[out.length - 1][0], e]; }
      else out.push([s, e]);
    }
    return out;
  }
  function _inter(A, B){
    const out = []; let i = 0, j = 0;
    while (i < A.length && j < B.length){
      const lo = Math.max(A[i][0], B[j][0]), hi = Math.min(A[i][1], B[j][1]);
      if (hi > lo) out.push([lo, hi]);
      if (A[i][1] < B[j][1]) i++; else j++;
    }
    return out;
  }
  const _meas = A => A.reduce((t, [s, e]) => t + (e - s), 0);
  function _shift(src, d){ let out = []; for (const [a0, w] of src) out = out.concat(_iv(a0 + d, w)); return _merge(out); }
  function _bbox(p){
    if (p.kind === "sphere"){ const c = p.c, r = p.r; return [c[0] - r, c[1] - r, c[2] - r, c[0] + r, c[1] + r, c[2] + r]; }
    if (p.kind === "rod"){ const a = p.p0, b = p.p1, r = p.r;
      return [Math.min(a[0], b[0]) - r, Math.min(a[1], b[1]) - r, Math.min(a[2], b[2]) - r, Math.max(a[0], b[0]) + r, Math.max(a[1], b[1]) + r, Math.max(a[2], b[2]) + r]; }
    const R = p.r_out;
    if (p.w >= 360.0 - 1e-9) return [-R, -R, p.z0, R, R, p.z1];
    const angs = [p.a0, p.a0 + p.w];
    for (let k = -8; k <= 8; k++) if (p.a0 < 90.0 * k && 90.0 * k < p.a0 + p.w) angs.push(90.0 * k);
    const xs = [], ys = [];
    for (const a of angs) for (const rr of [p.r_in, p.r_out]){ xs.push(rr * Math.cos(rad(a))); ys.push(rr * Math.sin(rad(a))); }
    return [Math.min(...xs), Math.min(...ys), p.z0, Math.max(...xs), Math.max(...ys), p.z1];
  }
  function _gap(p, q){
    const kp = p.kind, kq = q.kind;
    if (kp === "foil" && kq === "foil"){
      const zg = Math.max(p.z0 - q.z1, q.z0 - p.z1, 0.0);
      const rg = Math.max(Math.max(p.r_in, q.r_in) - Math.min(p.r_out, q.r_out), 0.0);
      const A = _merge(_iv(p.a0, p.w)), B = _merge(_iv(q.a0, q.w));
      let ag = 0.0;
      if (_meas(_inter(A, B)) <= 1e-12 && p.w < 360.0 - 1e-9 && q.w < 360.0 - 1e-9){
        const e1 = p.a0 + p.w, e2 = q.a0 + q.w;
        ag = Math.min(Math.abs(_sdeg(q.a0 - e1)), Math.abs(_sdeg(p.a0 - e2)));
        ag = rad(ag) * Math.min(p.r_out, q.r_out);
      }
      return Math.sqrt(zg * zg + rg * rg + ag * ag);
    }
    if (kp === "foil" || kq === "foil"){
      const [s, o] = kp === "foil" ? [p, q] : [q, p];
      if (o.kind === "sphere") return _d_pt_sector(o.c, s) - o.r;
      const lo = Math.min(o.p0[2], o.p1[2]), hi = Math.max(o.p0[2], o.p1[2]);
      const zg = Math.max(s.z0 - hi, lo - s.z1), [rmin, rmax] = _seg_rminmax(o.p0, o.p1);
      const rg = Math.max(s.r_in - rmax, rmin - s.r_out);
      if (zg > o.r + CONTACT_TOL || rg > o.r + CONTACT_TOL) return Math.max(zg, rg) - o.r;
      return _d_seg_sector(o.p0, o.p1, s) - o.r;
    }
    if (kp === "sphere" && kq === "sphere") return _dist(p.c, q.c) - p.r - q.r;
    if (kp === "sphere" || kq === "sphere"){ const [s, o] = kp === "sphere" ? [p, q] : [q, p]; return _d_pt_seg(s.c, o.p0, o.p1) - s.r - o.r; }
    return _seg_seg(p.p0, p.p1, q.p0, q.p1) - p.r - q.r;
  }

  /* ---- the analysis ---- */
  function nets_of(parts){
    const cond = []; parts.forEach((p, i) => { if (p.kind !== "insulator") cond.push(i); });
    const boxes = {}, par = {};
    for (const i of cond){ boxes[i] = _bbox(parts[i]); par[i] = i; }
    const find = i => { while (par[i] !== i){ par[i] = par[par[i]]; i = par[i]; } return i; };
    const edges = [];
    const order = cond.slice().sort((a, b) => boxes[a][0] - boxes[b][0] || a - b);
    for (let x = 0; x < order.length; x++){
      const i = order[x], bi = boxes[i];
      for (let y = x + 1; y < order.length; y++){
        const j = order[y], bj = boxes[j];
        if (bj[0] > bi[3] + CONTACT_TOL) break;
        if (bj[1] > bi[4] + CONTACT_TOL || bi[1] > bj[4] + CONTACT_TOL || bj[2] > bi[5] + CONTACT_TOL || bi[2] > bj[5] + CONTACT_TOL) continue;
        if (_gap(parts[i], parts[j]) <= CONTACT_TOL){
          const [a, b] = i < j ? [i, j] : [j, i];
          edges.push([a, b]);
          const ra = find(a), rb = find(b);
          if (ra !== rb) par[Math.max(ra, rb)] = Math.min(ra, rb);
        }
      }
    }
    edges.sort((p, q) => p[0] - q[0] || p[1] - q[1]);
    const groups = new Map();
    for (const i of cond){ const r = find(i); if (!groups.has(r)) groups.set(r, []); groups.get(r).push(i); }
    const nets = [...groups.values()].map(v => v.slice().sort((a, b) => a - b));
    nets.sort((a, b) => a[0] - b[0]);
    return [nets, edges];
  }

  function couplings(parts, nets){
    const net_of = {};
    nets.forEach((v, k) => { for (const i of v) net_of[i] = k; });
    const r6 = x => Math.round(x * 1e6) / 1e6;
    const plates = new Map();
    parts.forEach((p, i) => {
      if (p.kind !== "foil") return;
      const kk = [net_of[i], p.frame, r6(p.z0), r6(p.z1), r6(p.r_in), r6(p.r_out)], key = JSON.stringify(kk);
      if (!plates.has(key)) plates.set(key, {k: kk, net: net_of[i], frame: p.frame, z0: p.z0, z1: p.z1, r_in: p.r_in, r_out: p.r_out, arcs: [], names: []});
      plates.get(key).arcs.push([p.a0, p.w]); plates.get(key).names.push(p.name);
    });
    const P = [...plates.values()].sort((a, b) => a.k[2] - b.k[2] || a.k[4] - b.k[4] || a.k[0] - b.k[0] || cmpStr(a.k[1], b.k[1])
      || a.k[3] - b.k[3] || a.k[5] - b.k[5]);
    const ins = parts.filter(p => p.kind === "insulator" && p.r_in != null);
    const nD = Math.round(360.0 / DELTA_STEP), deltas = [];
    for (let k = 0; k < nD; k++) deltas.push(k * DELTA_STEP);
    const out = new Map();
    for (let x = 0; x < P.length; x++){
      for (let y = x + 1; y < P.length; y++){
        const A = P[x], B = P[y];
        if (A.net === B.net) continue;
        const ra = Math.max(A.r_in, B.r_in), rb = Math.min(A.r_out, B.r_out);
        if (rb - ra <= 1e-9) continue;
        let zlo, zhi;
        if (A.z1 <= B.z0 + 1e-9){ zlo = A.z1; zhi = B.z0; }
        else if (B.z1 <= A.z0 + 1e-9){ zlo = B.z1; zhi = A.z0; }
        else continue;
        const d = zhi - zlo;
        if (d <= CONTACT_TOL) continue;
        const sh = P.filter(S => S !== A && S !== B && S.z0 >= zlo - 1e-9 && S.z1 <= zhi + 1e-9 && Math.min(S.r_out, rb) - Math.max(S.r_in, ra) > 1e-9);
        const lay = ins.filter(I => Math.min(I.z1, zhi) - Math.max(I.z0, zlo) > 1e-9 && Math.min(I.r_out, rb) - Math.max(I.r_in, ra) > 1e-9);
        const bset = new Set([ra, rb]);
        for (const S of sh) for (const v of [S.r_in, S.r_out]) if (ra < v && v < rb) bset.add(v);
        for (const I of lay) for (const v of [I.r_in, I.r_out]) if (ra < v && v < rb) bset.add(v);
        const bounds = [...bset].sort((p, q) => p - q);
        const rot = A.frame !== B.frame || sh.some(S => S.frame !== A.frame);
        const ds = rot ? deltas : [0.0], C = new Array(ds.length).fill(0.0), a_ = _shift(A.arcs, 0.0);
        for (let bi = 0; bi + 1 < bounds.length; bi++){
          const b0 = bounds[bi], b1 = bounds[bi + 1];
          if (b1 - b0 <= 1e-9) continue;
          const layers = new Map();
          for (const I of lay){
            if (I.r_in <= b0 + 1e-9 && I.r_out >= b1 - 1e-9){
              const z0 = Math.max(I.z0, zlo), z1 = Math.min(I.z1, zhi);
              layers.set(JSON.stringify([r6(z0), r6(z1)]), [z1 - z0, I.eps]);
            }
          }
          let tt = 0.0, t_eff = 0.0;
          for (const [t] of layers.values()) tt += t;
          for (const [t, e] of layers.values()) t_eff += t / e;
          t_eff += Math.max(0.0, d - tt) / EPS_AIR;
          const shb = sh.filter(S => S.r_in <= b0 + 1e-9 && S.r_out >= b1 - 1e-9);
          if (new Set(shb.map(S => JSON.stringify([r6(S.z0), r6(S.z1)]))).size > 1) continue;
          const k_area = 0.5 * Math.PI / 180.0 * (b1 * b1 - b0 * b0);
          ds.forEach((dl, n_) => {
            const b_ = _shift(B.arcs, B.frame !== A.frame ? dl : 0.0), ov = _inter(a_, b_);
            if (!ov.length) return;
            let u = [];
            for (const S of shb) u = u.concat(_shift(S.arcs, S.frame !== A.frame ? dl : 0.0));
            const L = _meas(ov) - (u.length ? _meas(_inter(ov, _merge(u))) : 0.0);
            if (L > 1e-12) C[n_] += EPS0 * k_area * L * 1e-6 / (t_eff * 1e-3) * 1e12;
          });
        }
        if (Math.max(...C) <= 0.0) continue;
        const [i, j] = [A.net, B.net].sort((p, q) => p - q);
        const rel = A.frame !== B.frame ? "rotating" : (rot ? "modulated" : "fixed"), key = JSON.stringify([i, j, rel]);
        if (out.has(key)) out.set(key, out.get(key).map((v, k) => v + C[k])); else out.set(key, C);
      }
    }
    return out;
  }

  function sphere_gaps(parts, nets){
    const net_of = {};
    nets.forEach((v, k) => { for (const i of v) net_of[i] = k; });
    const sph = []; parts.forEach((p, i) => { if (p.kind === "sphere") sph.push(i); });
    const st = sph.filter(i => parts[i].frame === "stator"), ro = sph.filter(i => parts[i].frame === "rotor");
    const out = [];
    for (const i of st){
      const s = parts[i], rs = Math.hypot(s.c[0], s.c[1]), best = new Map();
      for (const j of ro){
        const t = parts[j], g = Math.hypot(rs - Math.hypot(t.c[0], t.c[1]), s.c[2] - t.c[2]) - s.r - t.r;
        if (g < GAP_NEAR){ const k = net_of[j]; if (!best.has(k) || g < best.get(k)[0] - 1e-12) best.set(k, [g, j]); }
      }
      out.push({stator: i, partners: [...best.entries()].sort((a, b) => a[0] - b[0])});
    }
    return out;
  }

  function analyze(parts, netlist, source){
    const nl_nodes = [...new Set(netlist.flatMap(c => [c.a, c.b]))].sort(cmpStr);
    const find = [], add = (rule, level, text) => find.push({rule, level, text});
    const has = (rule, levels) => find.some(f => f.rule === rule && (!levels || levels.includes(f.level)));
    for (const p of parts) if (p.kind === "unrecognized") add("I0", "FAIL", `solid ${p.name} is not recognized as a sector slab, sphere or rod: not analyzed`);
    parts = parts.filter(p => p.kind !== "unrecognized");
    const [nets, edges] = nets_of(parts);
    const tags = nets.map(v => [...new Set(v.map(i => parts[i].node).filter(n => n))].sort(cmpStr));
    const node_of_net = tags.map(t => t.length === 1 ? t[0] : null);
    // I1
    nets.forEach((v, k) => {
      if (tags[k].length > 1){
        const vs = new Set(v), br = edges.filter(([a, b]) => vs.has(a) && parts[a].node !== parts[b].node);
        const via = br.slice(0, 3).map(([a, b]) => `${parts[a].name} (node ${parts[a].node}) touches ${parts[b].name} (node ${parts[b].node})`).join("; ");
        add("I1", "FAIL", `SHORT: one net joins nodes ${tags[k].join(", ")} -- ${via}`);
      }
    });
    if (!has("I1")) add("I1", "PASS", `${nets.length} galvanic nets, each on one node`);
    // I2
    const by_node = {};
    tags.forEach((t, k) => { for (const n of t) (by_node[n] = by_node[n] || []).push(k); });
    const nodes_sorted = Object.keys(by_node).sort(cmpStr);
    for (const n of nodes_sorted){
      const ks = by_node[n];
      if (ks.length > 1){
        const frag = ks.slice(0, 4).map(k => `${nets[k].length} parts from ${parts[nets[k][0]].name}`).join("; ");
        add("I2", "FAIL", `OPEN: node ${n} is split into ${ks.length} nets (${frag})`);
      }
    }
    if (!has("I2")) add("I2", "PASS", `every node is one net (${nodes_sorted.length} nodes)`);
    // I3
    const ra_set = new Map();
    for (const p of parts){
      if (p.node && p.node_raw && p.node_raw.split(" ")[0] !== p.node){ const a = p.node_raw.split(" ")[0]; ra_set.set(JSON.stringify([a, p.node]), [a, p.node]); }
    }
    const raw_alias = [...ra_set.values()].sort((x, y) => cmpStr(x[0], y[0]) || cmpStr(x[1], y[1]));
    for (const [a, b] of raw_alias) add("I3", "WARN", `node id '${a}' is an old alias: the netlist of record calls it ${b}`);
    for (const n of nodes_sorted) if (!nl_nodes.includes(n)) add("I3", "FAIL", `node ${n} is drawn but is not in the netlist of record`);
    const undrawn = nl_nodes.filter(n => !(n in by_node));
    add("I3", has("I3", ["FAIL"]) ? "INFO" : "PASS",
      `drawn nodes ${nodes_sorted.join(", ")}; netlist nodes with nothing drawn (off-model): ${undrawn.join(", ") || "none"}`);
    // I4
    nets.forEach((v, k) => {
      const fr = new Set(v.map(i => parts[i].frame));
      if (fr.size > 1) add("I4", "FAIL", `the net of node ${tags[k].join(", ") || "?"} has copper on the rotor and on the stator (e.g. ${parts[v[0]].name}): ` +
        "it would be torn off -- rotor and stator meet only across spark gaps");
    });
    if (!has("I4")) add("I4", "PASS", "no net crosses the rotating joint");
    // I5
    nets.forEach(v => { if (!v.some(i => parts[i].kind === "foil")) add("I5", "FAIL", `ORPHAN: ${v.length} conductor(s) on no electrode, e.g. ${parts[v[0]].name} (node ${parts[v[0]].node})`); });
    if (!has("I5")) add("I5", "PASS", "every net holds a foil electrode");
    // I6
    const cp_net = couplings(parts, nets);
    const cpk = [...cp_net.keys()].map(k => JSON.parse(k)).sort((p, q) => p[0] - q[0] || p[1] - q[1] || cmpStr(p[2], q[2]));
    const cp = new Map();
    for (const [i, j, rel] of cpk){
      const val = cp_net.get(JSON.stringify([i, j, rel]));
      const [a, b] = [node_of_net[i] || tags[i].join("+"), node_of_net[j] || tags[j].join("+")].sort(cmpStr);
      const k = JSON.stringify([a, b, rel]);
      cp.set(k, cp.has(k) ? cp.get(k).map((x, n) => x + val[n]) : val.slice());
    }
    const cps = [...cp.keys()].map(k => JSON.parse(k)).sort((p, q) => cmpStr(p[0], q[0]) || cmpStr(p[1], q[1]) || cmpStr(p[2], q[2]));
    const caps = [], strays = [], used = new Set();
    for (const c of netlist){
      if (!DRAWN_CAPS.includes(c.name)) continue;
      const hit = cps.filter(k => (k[0] === c.a && k[1] === c.b) || (k[0] === c.b && k[1] === c.a));
      if (!hit.length){
        add("I6", "FAIL", `${c.name} (${c.a}-${c.b}) is not realized: no foils of these two nodes face each other`);
        caps.push({name: c.name, nodes: [c.a, c.b], realized: false});
        continue;
      }
      for (const key of hit){
        const val = cp.get(JSON.stringify(key));
        used.add(JSON.stringify(key));
        const rot = key[2] === "rotating";
        caps.push({name: c.name, nodes: [c.a, c.b], realized: true, relation: key[2], C_max_pF: Math.max(...val), C_min_pF: Math.min(...val)});
        if (rot !== VARIABLE_CAPS.includes(c.name) && key[2] !== "modulated")
          add("I6", "FAIL", `${c.name} is drawn ${key[2]} but the machine needs it ${VARIABLE_CAPS.includes(c.name) ? "rotating (a rotor plate against a stator plate)" : "fixed"}`);
      }
    }
    for (const key of cps){
      const val = cp.get(JSON.stringify(key));
      if (used.has(JSON.stringify(key)) || Math.max(...val) < STRAY_MIN_PF) continue;
      const [a, b] = key, across = netlist.filter(c => (c.a === a && c.b === b) || (c.a === b && c.b === a)).map(c => c.name);
      strays.push({nodes: [a, b], relation: key[2], C_max_pF: Math.max(...val), C_min_pF: Math.min(...val), across});
      let val_s = key[2] === "fixed" ? `${_f(Math.max(...val), 1)} pF` : `${_f(Math.min(...val), 1)}-${_f(Math.max(...val), 1)} pF over a turn`;
      if (key[2] === "modulated") val_s += " (fixed plates, rotating copper between)";
      add("I6", "WARN", `STRAY capacitor ${a}-${b} (${key[2]}): ${val_s}` + (across.length ? `, across ${across.join(", ")}` : ""));
    }
    if (!has("I6", ["FAIL"])) add("I6", "PASS", `all ${caps.filter(c => c.realized).length} drawn netlist capacitors realized on their nodes`);
    // I7
    const nl_gaps = {};
    for (const c of netlist) if (c.kind === "gap") nl_gaps[c.name] = c;
    const gaps = {};
    for (const g of sphere_gaps(parts, nets)){
      const s = parts[g.stator], pre = s.name.split("_")[0], gname = pre in nl_gaps ? pre : null;
      if (!g.partners.length){ add("I7", "WARN", `stator sphere ${s.name} faces no rotor sphere`); continue; }
      for (const [k, [dist, j]] of g.partners){
        const pa = new Set([s.node, parts[j].node]);
        const ok = Object.keys(nl_gaps).filter(n => { const c = nl_gaps[n], q = new Set([c.a, c.b]); return q.size === pa.size && [...q].every(x => pa.has(x)); });
        if (!ok.length){
          add("I7", "FAIL", `PARASITIC GAP: ${s.name} (node ${s.node}) meets ${parts[j].name} (node ${parts[j].node}) at ${_f(dist, 2)} mm -- no gap joins these nodes in the netlist`);
          continue;
        }
        const name = ok.includes(gname) ? gname : (ok.length === 1 && gname === null ? ok[0] : null);
        if (name === null){
          add("I7", "FAIL", `${s.name} is named ${gname || "(no gap)"} but joins nodes ${[...pa].sort(cmpStr).join(", ")}, which the netlist gives to ${ok.join(", ")}`);
          continue;
        }
        if (!(name in gaps)) gaps[name] = {name, nodes: [nl_gaps[name].a, nl_gaps[name].b], spheres: 0, s_min: dist, s_max: dist,
          d_stator: 2 * s.r, d_rotor: 2 * parts[j].r, _seen: []};
        const e = gaps[name];
        if (!e._seen.includes(s.name)){ e._seen.push(s.name); e.spheres += 1; }
        e.s_min = Math.min(e.s_min, dist); e.s_max = Math.max(e.s_max, dist);
      }
    }
    for (const n of Object.keys(nl_gaps)) if (!(n in gaps)) add("I7", "FAIL", `${n} (${nl_gaps[n].a}-${nl_gaps[n].b}) is not realized by any sphere pair`);
    for (const e of Object.values(gaps)) if (e.s_max - e.s_min > 1e-6) add("I7", "WARN", `${e.name}: its spokes differ in spacing (${_f(e.s_min, 3)}-${_f(e.s_max, 3)} mm)`);
    if (!has("I7", ["FAIL"])) add("I7", "PASS", `all ${Object.keys(gaps).length} netlist gaps realized on their nodes, no parasitic gap`);
    const gapsOut = Object.keys(gaps).sort(cmpStr).map(n => { const o = Object.assign({}, gaps[n]); delete o._seen; return o; });
    // I8
    const nl_by = {}; for (const c of netlist) nl_by[c.name] = c;
    const seen = {}; for (const p of parts) seen[p.name] = (seen[p.name] || 0) + 1;
    for (const n of Object.keys(seen).filter(k => seen[k] > 1).sort(cmpStr)) add("I8", "FAIL", `name ${n} is used ${seen[n]} times`);
    for (const p of parts){
      const lab = p.label, idx = lab.indexOf(" - "), desc = idx >= 0 ? lab.slice(idx + 3) : lab, m = desc.match(NODE_TOKEN);
      if (p.kind === "insulator"){ if (m) add("I8", "WARN", `insulator ${p.name} is labelled 'node ${m[1]}' -- an insulator is on no node`); continue; }
      if (m && canon(m[1]) !== p.node) add("I8", "FAIL", `${p.name}: its label says node ${m[1]}, its copper is on node ${p.node}`);
      let dec = p.group.startsWith("node-") ? canon(p.group.slice(5)) : null;
      if (dec === null){ const mg = p.group_label.match(GROUP_NODE); dec = mg ? canon(mg[1]) : null; }
      if (dec !== null && dec !== p.node) add("I8", "FAIL", `${p.name} (node ${p.node}) sits in group '${p.group}', which declares node ${dec}`);
      const pre = p.name.split("_")[0], comp = nl_gaps[pre] || (pre in CAP_PREFIX ? nl_by[CAP_PREFIX[pre]] : null);
      if (comp && p.node !== comp.a && p.node !== comp.b) add("I8", "FAIL", `${p.name} belongs to ${comp.name} (${comp.a}-${comp.b}) by name, but its copper is on node ${p.node}`);
    }
    if (!has("I8", ["FAIL", "WARN"])) add("I8", "PASS", `${parts.length} parts: every label, group and gap / capacitor name states the node its copper is on`);
    // I9
    const off = [];
    for (const c of netlist){
      if (DRAWN_CAPS.includes(c.name) || c.kind === "gap") continue;
      off.push({name: c.name, kind: c.kind, nodes: [c.a, c.b], drawn: [c.a, c.b].filter(n => n in by_node)});
    }
    const both = off.filter(o => o.drawn.length === 2).map(o => o.name);
    add("I9", "INFO", `${off.length} netlist components are off-model; ${both.length} join two drawn nets and need a connection there: ${both.join(", ") || "none"}`);
    // the nets table
    const nt = nets.map((v, k) => {
      const kinds = {}; for (const i of v) kinds[parts[i].kind] = (kinds[parts[i].kind] || 0) + 1;
      const ks = {}; for (const x of Object.keys(kinds).sort(cmpStr)) ks[x] = kinds[x];
      const node = node_of_net[k];
      return {net: k, node: node ? node : (tags[k].join("+") || "?"), info: NODE_INFO[node] || "", parts: v.length, kinds: ks,
        frame: [...new Set(v.map(i => parts[i].frame))].sort(cmpStr).join("+")};
    });
    nt.sort((a, b) => cmpStr(a.node, b.node) || a.net - b.net);
    const lv = find.map(f => f.level), cnt = l => lv.filter(x => x === l).length;
    return {tool: TOOL, source: source || "", verdict: lv.includes("FAIL") ? "FAIL" : "PASS",
      counts: {FAIL: cnt("FAIL"), WARN: cnt("WARN"), PASS: cnt("PASS"), INFO: cnt("INFO")},
      nets: nt, capacitors: caps, strays, gaps: gapsOut, offmodel: off, findings: find,
      parts: parts.length, conductors: parts.filter(p => p.kind !== "insulator").length};
  }

  /* ---- on-load self-test (the Python's synthetic machine) ---- */
  function selftest(){
    const foil = (name, node, body, z0, grp) => ({name, label: `${grp} / ${name} - plate, node ${node} [Al foil, ${body}]`, group: grp, group_label: "",
      material: "Al foil", body, frame: frame_of(body), node_raw: node, node, kind: "foil", r_in: 100.0, r_out: 200.0, a0: 0.0, w: 30.0, z0, z1: z0 + 1.0});
    const st = foil("C1_stator_1", "1", "stator", 0.0, "node-1"), ro = foil("C1_rotor_1", "R-A", "rotor A", 8.0, "node-R-A");
    const s1 = {name: "SG1_sph_1", label: "node-2 / SG1_sph_1 - sphere, node 2 [W-Cu sphere, stator]", group: "node-2", group_label: "",
      material: "W-Cu sphere", body: "stator", frame: "stator", node_raw: "2", node: "2", kind: "sphere", c: [300.0, 0.0, 0.0], r: 6.0};
    const s2 = Object.assign({}, s1, {name: "rt_1", label: "node-R-A / rt_1 - tip, node R-A [W-Cu sphere, rotor A]", group: "node-R-A", body: "rotor A",
      frame: "rotor", node_raw: "R-A", node: "R-A", c: [300.0, 0.0, 17.5]});
    const f2 = Object.assign(foil("Ca_el_1", "2", "stator", -10.0, "node-2"), {r_in: 290.0, r_out: 310.0});
    const lead = {name: "SG1_lead_1a", label: "node-2 / SG1_lead_1a - lead, node 2 [Cu lead, stator]", group: "node-2", group_label: "",
      material: "Cu lead", body: "stator", frame: "stator", node_raw: "2", node: "2", kind: "rod", p0: [300.0, 0.0, 0.0], p1: [300.0, 0.0, -9.5], r: 1.5};
    const tie = Object.assign({}, lead, {name: "rt_lead_1a", label: "node-R-A / rt_lead_1a - lead, node R-A [Cu lead, rotor A]", group: "node-R-A",
      body: "rotor A", frame: "rotor", node_raw: "R-A", node: "R-A", p0: [300.0, 0.0, 17.5], p1: [190.0, 0.0, 8.5]});
    const nl = [{name: "C1", a: "R-A", b: "1", kind: "capacitor"}, {name: "SG1", a: "2", b: "R-A", kind: "gap"}];
    const base = [st, ro, s1, s2, f2, lead, tie], cp = () => base.map(p => Object.assign({}, p));
    const lv = (rep, rule) => new Set(rep.findings.filter(f => f.rule === rule).map(f => f.level));
    const r0 = analyze(cp(), nl, "selftest");
    let ok = [...lv(r0, "I1")].join() === "PASS" && [...lv(r0, "I2")].join() === "PASS" && [...lv(r0, "I7")].join() === "PASS";
    const c1 = r0.capacitors.find(c => c.name === "C1"), want = EPS0 * EPS_AIR * (0.5 * rad(30.0) * (200.0 ** 2 - 100.0 ** 2)) * 1e-6 / 7e-3 * 1e12;
    ok = ok && c1.relation === "rotating" && Math.abs(c1.C_max_pF - want) < 1e-9 * want;
    const mis = cp(); mis[2] = Object.assign({}, mis[2], {group: "ND1", group_label: "ND1 - stator carrier ND1 (node 1): C1 stator plate"});
    ok = ok && lv(analyze(mis, nl), "I8").has("FAIL");
    const op = cp().concat([Object.assign({}, st, {name: "C1_stator_2", a0: 180.0})]);
    ok = ok && lv(analyze(op, nl), "I2").has("FAIL");
    return {pass: ok};
  }

  const API = {TOOL, parse_netlist, parts_from_design, analyze, selftest, NODE_INFO, canon};
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.CircuitIntegrity = API;
})(typeof self !== "undefined" ? self : this);

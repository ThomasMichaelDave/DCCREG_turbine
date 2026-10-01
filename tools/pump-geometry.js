/* tools/pump-geometry.js — the JS mirror of sim/pump_geometry.py (PUMP-SYNTH stage 2: plate geometry).
 *
 * 1:1 port so the page can redraw the plate distribution instantly; gate G-JS (sim/pump_geometry_gates.py)
 * holds this file to the Python to 1e-12 on randomized inputs (every number and every check string).
 * Browser: window.PumpGeometry; Node: module.exports. Tags [OC]/[IR]/[ME] as in the Python.
 */
(function (root) {
  "use strict";
  const EPS0 = 8.8541878128e-12;
  const SCHEMA = "pump-geometry/1";
  const DIELECTRICS = { mica: 5.4, mylar: 3.2, kapton: 3.4, pp_film: 2.2, garolite: 4.7, air: 1.0006 };
  const GEOM_DEFAULTS = { ca_diel: "mica", ca_t: 4.5, ca_w: 30.0, ca_mode: "r_out", ca_rin: 110.0, ca_rout: 175.0,
    ca_round: 0.0, ca_margin: 5.0, t_foil: 1.0, t_carrier: 3.0, t_rotor: 10.0, t_flange: 6.0, t_septum: 12.0,
    cx_air: 3.0, cx_mica: 0.3, r_bore: 50.0, rotor_in_off: 20.0 };
  const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI;
  const g6 = x => String(+(+x).toPrecision(6));                       // Python :g
  const f = (x, n) => x.toFixed(n);
  const fs = (x, n) => (x >= 0 ? "+" : "") + x.toFixed(n);            // Python :+.nf
  const pct = x => { const v = x * 100; return Math.abs(v) < 5e-5 ? 0.0 : v; };
  const pylist = a => "[" + a.map(s => "'" + s + "'").join(", ") + "]";

  function _round(x, step){ return !step ? x : Math.floor(x / step + 0.5) * step; }
  function sector_area(rin, rout, w, n){ return 0.5 * rad(w) * Math.max(0.0, rout * rout - rin * rin) * n; }
  function cap_pF(A, t, er){ return EPS0 * er * A * 1e-6 / (t * 1e-3) * 1e12; }

  function solve_transfer(C_pF, g, n){
    const er = DIELECTRICS[g.ca_diel];
    const A = C_pF * 1e-12 * g.ca_t * 1e-3 / (EPS0 * er) * 1e6;
    let w = g.ca_w, rin = g.ca_rin, rout = g.ca_rout;
    const k = 0.5 * rad(w) * n;
    const mode = g.ca_mode; let note = "";
    if (mode === "r_out") rout = _round(Math.sqrt(rin * rin + A / k), g.ca_round);
    else if (mode === "r_in"){
      const d = rout * rout - A / k;
      if (d < 0){ rin = 0.0; note = "target area exceeds the full disc inside r_out: r_in clamped to 0"; }
      else rin = _round(Math.sqrt(d), g.ca_round);
    } else if (mode === "width") w = _round(deg(A / (0.5 * n * (rout * rout - rin * rin))), g.ca_round);
    else if (mode !== "forward") throw new Error(mode);
    const area = sector_area(rin, rout, w, n);
    const C = cap_pF(area, g.ca_t, er);
    return { C_target_pF: C_pF, C_pF: C, dC_rel: (C - C_pF) / C_pF, area_mm2: area, area_needed_mm2: A,
      r_in: rin, r_out: rout, w_deg: w, n, t: g.ca_t, diel: g.ca_diel, eps_r: er, mode, note };
  }
  const _fp = (name, node, cap, r_in, r_out, starts, w_deg) => ({ name, node, cap, r_in, r_out, starts: starts.slice(), w_deg });

  function build(locked, geom){
    const g = Object.assign({}, GEOM_DEFAULTS, geom || {});
    const L = locked.ladder, P = locked.plates;
    const nk = Math.trunc(P.n_kept);
    const ca = solve_transfer(L.Ca, g, nk), cb = solve_transfer(L.Cb, g, nk);
    const ri = P.r_inMm, ro = P.r_outMm;
    const rr_in = Math.max(0.0, ri - g.rotor_in_off);
    const r_edge = ro * 500.0 / 387.0;
    const cx_rin = ro * 58.0 / 387.0, cx_rout = ro * 350.0 / 387.0, bar_rin = ro * 75.0 / 387.0;
    const sb = P.N_sec, w_sec = 360.0 / sb, nh = Math.floor(sb / 2);
    const odd = [], even = [];
    for (let k = 0; k < nh; k++){ odd.push(w_sec + 2 * w_sec * k); even.push(2 * w_sec * k); }
    const ca_starts = odd.map(s => s + (w_sec - ca.w_deg) / 2), cb_starts = even.map(s => s + (w_sec - cb.w_deg) / 2);
    const fp = {
      C1_stator: _fp("C1 stator plate", "1", "C1", ri, ro, odd, w_sec),
      C1_rotor: _fp("C1 rotor face", "5", "C1", rr_in, ro, odd, w_sec),
      C2_stator: _fp("C2 stator plate", "4", "C2", ri, ro, even, w_sec),
      C2_rotor: _fp("C2 rotor face", "6", "C2", rr_in, ro, odd, w_sec),
      Ca_el: _fp("Ca electrode", "2", "Ca", ca.r_in, ca.r_out, ca_starts, ca.w_deg),
      Ca_counter: _fp("Ca counter (ND1 back face)", "1", "Ca", ri, ro, odd, w_sec),
      Cb_el: _fp("Cb electrode", "3", "Cb", cb.r_in, cb.r_out, cb_starts, cb.w_deg),
      Cb_counter: _fp("Cb counter (ND4 back face)", "4", "Cb", ri, ro, even, w_sec),
      Cx4_pickup: _fp("Cx4 pickup", "2", "Cx4", cx_rin, cx_rout, even, w_sec),
      Cx4_bars: _fp("island bars on A", "8", "Cx4", bar_rin, cx_rout, even, w_sec),
      Cx3_pickup: _fp("Cx3 pickup", "3", "Cx3", cx_rin, cx_rout, odd, w_sec),
      Cx3_bars: _fp("island bars on B", "7", "Cx3", bar_rin, cx_rout, odd, w_sec),
      CR_A: _fp("C_R face (rotor A)", "5", "C_R", rr_in, ro, [0.0], 360.0),
      CR_B: _fp("C_R face (rotor B)", "6", "C_R", rr_in, ro, [0.0], 360.0),
    };
    const tf = g.t_foil, tc = g.t_carrier, gv = P.g_vMm, tcx = g.cx_air + 2 * g.cx_mica;
    const cxm = `air ${g6(g.cx_air)} + mica ${g6(g.cx_mica)}/face`;
    const C = (id, kind, node, t, r_in) => ({ id, kind, node, t, r_in, r_out: r_edge });
    const F = key => ({ id: key, kind: "foil", key, t: tf });
    const G = (id, cap, t, medium, footprint = null, margin = 0.0) => ({ id, kind: "gap", cap, t, medium, footprint, margin });
    const seqA = [F("CR_A"), C("A-disc", "rotor", "5", g.t_rotor, 0.0), F("C1_rotor"), G("C1-gap", "C1", gv, "air"),
      F("C1_stator"), C("ND1", "stator", "1", tc, g.r_bore), F("Ca_counter"),
      G("Ca-diel", "Ca", ca.t, ca.diel, "Ca_el", g.ca_margin), F("Ca_el"),
      C("ND2", "stator", "2", tc, g.r_bore), F("Cx4_pickup"), G("Cx4-gap", "Cx4", tcx, cxm),
      F("Cx4_bars"), C("A-flange", "rotor-flange", "8 (floating on A)", g.t_flange, 0.0)];
    const seqB = [F("CR_B"), C("B-disc", "rotor", "6", g.t_rotor, 0.0), F("C2_rotor"), G("C2-gap", "C2", gv, "air"),
      F("C2_stator"), C("ND4", "stator", "4", tc, g.r_bore), F("Cb_counter"),
      G("Cb-diel", "Cb", cb.t, cb.diel, "Cb_el", g.ca_margin), F("Cb_el"),
      C("ND3", "stator", "3", tc, g.r_bore), F("Cx3_pickup"), G("Cx3-gap", "Cx3", tcx, cxm),
      F("Cx3_bars"), C("B-flange", "rotor-flange", "7 (floating on B)", g.t_flange, 0.0)];
    const h = g.t_septum / 2;
    const stack = [Object.assign(G("septum", "C_R", g.t_septum, "garolite"), { z0: -h, z1: h, side: "mid", r_in: 0.0, r_out: r_edge })];
    for (const [side, seq, sgn] of [["A", seqA, -1], ["B", seqB, +1]]){
      let zz = h;
      for (const it0 of seq){
        const it = Object.assign({}, it0), a = sgn * zz, b = sgn * (zz + it.t);
        Object.assign(it, { z0: Math.min(a, b), z1: Math.max(a, b), side });
        if (it.kind === "foil") Object.assign(it, fp[it.key]);
        stack.push(it); zz += it.t;
      }
    }
    stack.sort((p, q) => p.z0 - q.z0);
    const foils = stack.filter(it => it.kind === "foil");
    const design = { schema: SCHEMA, units: "mm", lock: Object.assign({}, locked), geom: g, Ca: ca, Cb: cb, footprints: fp,
      stack, foils, z_total: stack[stack.length - 1].z1 - stack[0].z0, r_edge };
    design.checks = checks(design);
    return design;
  }

  function _arc_overlap(a0, w0, a1, w1){
    let tot = 0.0;
    for (const sh of [-360.0, 0.0, 360.0]){ const lo = Math.max(a0, a1 + sh), hi = Math.min(a0 + w0, a1 + w1 + sh); tot += Math.max(0.0, hi - lo); }
    return tot;
  }
  function overlap_area(f1, f2){
    const rin = Math.max(f1.r_in, f2.r_in), rout = Math.min(f1.r_out, f2.r_out);
    if (rout <= rin) return 0.0;
    let ang = 0.0;
    for (const a of f1.starts) for (const b of f2.starts) ang += _arc_overlap(a, f1.w_deg, b, f2.w_deg);
    return 0.5 * rad(ang) * (rout * rout - rin * rin);
  }
  const PAIRS = { C1: ["C1_stator", "C1_rotor"], C2: ["C2_stator", "C2_rotor"], Ca: ["Ca_el", "Ca_counter"],
    Cb: ["Cb_el", "Cb_counter"], Cx4: ["Cx4_pickup", "Cx4_bars"], Cx3: ["Cx3_pickup", "Cx3_bars"], C_R: ["CR_A", "CR_B"] };
  const ROTATING = ["C1", "C2", "Cx3", "Cx4"];

  function adjacency(design){
    const st = design.stack, pos = {};
    st.forEach((it, i) => pos[it.id] = i);
    const out = {};
    for (const cap of Object.keys(PAIRS)){
      const [k1, k2] = PAIRS[cap];
      const [i1, i2] = [pos[k1], pos[k2]].sort((x, y) => x - y);
      const between = st.slice(i1 + 1, i2);
      const a = st[pos[k1]], b = st[pos[k2]];
      const ov0 = overlap_area(a, b), rot = ROTATING.includes(cap);
      let ovm = ov0;
      if (rot){ ovm = -Infinity; for (let d = 0; d <= 60; d++) ovm = Math.max(ovm, overlap_area(a, Object.assign({}, b, { starts: b.starts.map(x => x + d) }))); }
      const ok = between.length === 1 && between[0].kind === "gap" && between[0].cap === cap && ovm > 0;
      out[cap] = [ok, `${k1} <-> ${k2} across ${pylist(between.map(x => x.id))}, plan overlap ` +
        (rot ? `${f(ov0, 0)} at 0 deg / ${f(ovm, 0)} aligned mm^2` : `${f(ov0, 0)} mm^2 (fixed)`)];
    }
    return out;
  }

  function checks(design){
    const fp = design.footprints, g = design.geom, res = {};
    for (const [cap, el, ct] of [["Ca", "Ca_el", "Ca_counter"], ["Cb", "Cb_el", "Cb_counter"]]){
      const e = fp[el], c = fp[ct], geo = design[cap];
      const inside = e.r_in >= c.r_in - 1e-9 && e.r_out <= c.r_out + 1e-9 && e.w_deg <= c.w_deg + 1e-9;
      res[`${cap}: electrode inside its counter-electrode`] = [inside,
        `r${f(e.r_in, 1)}-${f(e.r_out, 1)} x ${f(e.w_deg, 2)} deg within r${f(c.r_in, 0)}-${f(c.r_out, 0)} x ${f(c.w_deg, 0)} deg`];
      const ov = overlap_area(e, c);
      res[`${cap}: overlap area = electrode area`] = [Math.abs(ov - geo.area_mm2) <= 1e-6 * geo.area_mm2, `${f(ov, 1)} vs ${f(geo.area_mm2, 1)} mm^2`];
      res[`${cap}: clears the carrier bore`] = [e.r_in - g.ca_margin >= g.r_bore,
        `r_in ${f(e.r_in, 1)} - margin ${f(g.ca_margin, 0)} >= bore ${f(g.r_bore, 0)}`];
      res[`${cap}: dielectric margin fits the sector pitch`] = [
        e.w_deg + 2 * deg(g.ca_margin / Math.max(e.r_in, 1e-9)) <= 360.0 / (e.starts.length || 1),
        `foil ${f(e.w_deg, 1)} deg + 2 x ${f(g.ca_margin, 0)} mm margin at r_in`];
      res[`${cap}: realized C = locked C`] = [Math.abs(geo.dC_rel) <= 1e-9 || g.ca_round > 0,
        `${f(geo.C_pF, 3)} vs ${f(geo.C_target_pF, 3)} pF (${fs(pct(geo.dC_rel), 4)} %)` +
        (g.ca_round > 0 ? " -- rounding: engine round-trip decides" : "")];
    }
    const P = design.lock.plates;
    res["layout: alternating sectors (n_kept = N_sec / 2, as drawn)"] = [Math.trunc(P.n_kept) * 2 === Math.trunc(P.N_sec),
      `n_kept ${P.n_kept} of N_sec ${P.N_sec}`];
    const adj = adjacency(design);
    for (const cap of Object.keys(adj)) res[`stack: ${cap} electrodes face each other`] = adj[cap];
    const out = {};
    for (const k of Object.keys(res)) out[k] = { pass_: !!res[k][0], detail: res[k][1] };
    return out;
  }

  /** the stage-1 lock (the page's own record; the hash is SHA-256 of the canonical inputs + ladder, async) */
  function lock_record(lad, inputs, z, converged, engine){
    const ladder = {}; for (const k of Object.keys(lad.ladder)) ladder[k] = lad.ladder[k].value;
    const plates = {}; for (const k of ["r_inMm", "r_outMm", "g_vMm", "N_sec", "n_kept"]) plates[k] = lad.plates[k];
    return { inputs, plates, ladder, z, converged, engine: engine || "" };
  }
  function canonical(o){
    if (Array.isArray(o)) return "[" + o.map(canonical).join(",") + "]";
    if (o && typeof o === "object") return "{" + Object.keys(o).sort().map(k => JSON.stringify(k) + ":" + canonical(o[k])).join(",") + "}";
    return JSON.stringify(o);
  }
  async function lock_hash(rec){
    const blob = canonical({ inputs: rec.inputs, ladder: rec.ladder });
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(blob));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 12);
  }
  function selftest(){
    const fwd = solve_transfer(309.0, Object.assign({}, GEOM_DEFAULTS, { ca_mode: "forward" }), 6);
    const ok = Math.abs(fwd.area_mm2 - 29099.002) < 0.01 && Math.abs(fwd.C_pF - 309.18) < 0.01;
    return { pass: ok, rows: [["G-SEED", "DXF seed 6 × 30° r110–175 on 4.5 mm mica → 309.18 pF", 309.18, fwd.C_pF, ok]] };
  }
  const API = { EPS0, SCHEMA, DIELECTRICS, GEOM_DEFAULTS, PAIRS, solve_transfer, build, overlap_area, adjacency, checks,
    lock_record, lock_hash, canonical, selftest };
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.PumpGeometry = API;
})(typeof self !== "undefined" ? self : this);

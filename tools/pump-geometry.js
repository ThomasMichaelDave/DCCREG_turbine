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
  const GEOM_DEFAULTS = { ca_diel: "mica", ca_t: 4.5, ca_w: 30.0, ca_mode: "outer", ca_rin: 110.0, ca_rout: 175.0,
    ca_round: 0.0, ca_margin: 5.0, t_foil: 1.0, t_carrier: 3.0, t_rotor: 10.0, t_flange: 6.0, t_septum: 12.0,
    cx_air: 3.0, cx_mica: 0.3, r_bore: 50.0, rotor_in_off: 20.0,
    sg_rbar: 375.0, sg_rrail: 410.0, sg_d: 12.0, sg_dbs: 25.0, sg_s_ret: 5.5, sg_s_load: 4.75, sg_s_fire: 5.5, sg_s_bs: 5.5,
    sg_glat: 1.0, sg_expose: 0.5, sg_stem: 4.0, sg_wall: 1.0, sg_seat: 3.0, sg_rod: 3.0, sg_cover: 2.0, sg_chord: 15.0, sg_bus: 3.0,
    sg_frame: 60.0, sg_khv: 2.0, sg_layout: "radial", sg_rimgap: 3.0, sg_clear: 2.0, sg_stem_air: 2.0, sg_tip_deg: 0.0, c_s_inset: 0.0, c_ws_deg: 0.0, counter_w_deg: 0.0, cr_w_deg: 0.0, c1_mica: 0.0, c1_mica_m: 1.0, carrier_mat: "G10", counter_trim: 0, c_w_deg: 0.0, cx_w_deg: 0.0, ca_cal: 1.0, zs_mode: "auto" };
  // Z-stretch (TMD 2026-10-02): carrier base thicknesses, same-node links, the fixed gap each carrier faces [IR]
  const CARRIER_BASE = {ND1: "t_carrier", ND2: "t_carrier", ND3: "t_carrier", ND4: "t_carrier", "A-disc": "t_rotor",
    "B-disc": "t_rotor", "A-flange": "t_flange", "B-flange": "t_flange"};
  const FAR_GAP = {ND1: "ca_t", ND2: "ca_t", ND3: "ca_t", ND4: "ca_t", "A-disc": "t_septum", "B-disc": "t_septum"};
  // (the rotor discs hold two DIFFERENT nodes -- R-A / R-B and the C_R plate n18 / n00, joined only through L_R1 / L_R2)
  const LINKS = {ND1: ["C1_stator", "Ca_counter"], ND4: ["C2_stator", "Cb_counter"]};
  // radial bar band (TMD 2026-10-02): the foils of the trimmed carriers; outermost edge + margin + sg_rimgap = the rim [IR]
  const RIM_FOILS = {ND2: ["Ca_el", "Cx4_pickup"], ND3: ["Cb_el", "Cx3_pickup"]};
  const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI;
  const g6 = x => String(+(+x).toPrecision(6));                       // Python :g
  const f = (x, n) => x.toFixed(n);
  const fs = (x, n) => (x >= 0 ? "+" : "") + x.toFixed(n);            // Python :+.nf
  const pct = x => { const v = x * 100; return Math.abs(v) < 5e-5 ? 0.0 : v; };
  const pylist = a => "[" + a.map(s => "'" + s + "'").join(", ") + "]";

  function _round(x, step){ return !step ? x : Math.floor(x / step + 0.5) * step; }
  function sector_area(rin, rout, w, n){ return 0.5 * rad(w) * Math.max(0.0, rout * rout - rin * rin) * n; }
  function cap_pF(A, t, er){ return EPS0 * er * A * 1e-6 / (t * 1e-3) * 1e12; }

  function solve_transfer(C_pF, g, n, r_max){
    const er = DIELECTRICS[g.ca_diel];
    const A = C_pF * 1e-12 * g.ca_t * 1e-3 / (EPS0 * er) * 1e6;
    let w = g.ca_w, rin = g.ca_rin, rout = g.ca_rout;
    const k = 0.5 * rad(w) * n;
    const mode = g.ca_mode; let note = "";
    if (mode === "outer") rout = r_max != null ? r_max : rout;
    if (mode === "r_out") rout = _round(Math.sqrt(rin * rin + A / k), g.ca_round);
    else if (mode === "r_in" || mode === "outer"){
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

  /* the axial room each band needs (independent of the carriers) and the Z-stretch (1:1 with the Python) */
  function band_needs(g, P){
    const D = {bar: g.cx_air + 2 * g.cx_mica + 2 * g.t_foil, return: P.g_vMm + 2 * g.t_foil}, out = {};
    for (const [[side, band]] of BANDS){
      const mine = GAPS.filter(x => x[4] === side && x[5] === band), p_rot = g.sg_expose * g.sg_d;
      if (band === "bar" && g.sg_layout === "radial"){ out[side + "|" + band] = _radial_needs(g, D[band], mine); continue; }
      const need = Math.max(...mine.map(x => g[SPACING_KEY[x[1]]] + p_rot + g.sg_expose * sphere_d(g, x[1])));
      const G = Math.max(D[band], need), p = {};
      for (const x of mine) p[x[0]] = G - g[SPACING_KEY[x[1]]] - p_rot;
      out[side + "|" + band] = {D: D[band], need, G, rec: Math.max(0.0, need - D[band]) / 2, p_rot, p,
        e_st: Math.max(...mine.map(x => Math.max(0.0, sphere_d(g, x[1]) - p[x[0]]))), e_rot: Math.max(0.0, g.sg_d - p_rot), layout: "axial"};
    }
    return out;
  }
  /* the radial bar band along z (1:1 with the Python _radial_needs): zeta = height above the stator's bare Cx face */
  function _radial_needs(g, D, mine){
    const R_t = g.sg_d / 2, load = mine.filter(x => x[1] === "load"), vert = mine.filter(x => x[1] !== "load");
    const R_l = Math.max(...load.map(x => sphere_d(g, x[1]) / 2)), hold = Math.max(g.sg_stem, g.sg_rod) / 2 + g.sg_cover;
    const hv = g.sg_khv * Math.max(g.sg_s_ret, g.sg_s_load, g.sg_s_fire, g.sg_s_bs);
    const z_tip = Math.min(D - (R_l + g.sg_clear), Math.min(...vert.map(x => R_t + g[SPACING_KEY[x[1]]] + sphere_d(g, x[1]) / 2)) - hold);
    const zeta = {}, p = {};
    for (const x of load) zeta[x[0]] = z_tip;
    for (const x of vert) zeta[x[0]] = z_tip - (R_t + g[SPACING_KEY[x[1]]] + sphere_d(g, x[1]) / 2);
    for (const x of mine) p[x[0]] = sphere_d(g, x[1]);
    // the carrier's other leads enter at the deepest rim stem's plane, at least the HV clearance below the tip path
    const lead = Math.min(Math.min(...vert.map(x => zeta[x[0]])), z_tip - R_t - hv - g.sg_rod / 2);
    const depth = Math.max(Math.max(...vert.map(x => Math.max(sphere_d(g, x[1]), g.sg_stem, g.sg_rod) / 2 - zeta[x[0]])), g.sg_rod / 2 - lead);
    return {D, need: D, G: D, rec: 0.0, p_rot: D - z_tip + R_t, p, e_st: 0.0, e_rot: 0.0, layout: "radial", zeta_tip: z_tip, zeta, depth, lead};
  }
  const sphere_d = (g, cls) => cls === "backstop" ? g.sg_dbs : g.sg_d;
  function far_cover(g, c){
    const hv = g.sg_khv * Math.max(g.sg_s_ret, g.sg_s_load, g.sg_s_fire, g.sg_s_bs), fixed = FAR_GAP[c];
    if (fixed == null) return g.sg_cover;
    return Math.max(g.sg_cover, (hv - (g[fixed] + 2 * g.t_foil)) / 2);
  }
  function zstretch(g, P){
    const need = band_needs(g, P), req = {};
    for (const k of Object.keys(CARRIER_BASE)) req[k] = [0.0, ""];
    for (const [[side, band], [rc, , sc]] of BANDS){
      const n = need[side + "|" + band];
      if (n.layout === "radial"){
        for (const [c, r, why] of [[rc, g.sg_seat + g.sg_rod + far_cover(g, rc), `${side} bar band (radial): tip stem seat ${_mm(g.sg_seat)} + lead ${_mm(g.sg_rod)} + cover ${_mm(far_cover(g, rc))}`],
                                   [sc, n.depth + far_cover(g, sc), `${side} bar band (radial): rim spheres hang ${_mm(n.depth)} below the Cx face + cover ${_mm(far_cover(g, sc))}`]])
          if (r > req[c][0] + 1e-9) req[c] = [r, why];
        continue;
      }
      for (const [c, e] of [[rc, n.e_rot], [sc, n.e_st]]){
        const fc = far_cover(g, c), r = n.rec + e + g.sg_seat + g.sg_rod + fc;
        const why = `${side} ${band} band: recess ${_mm(n.rec)} + socket ${_mm(e)} + seat ${_mm(g.sg_seat)} + lead ${_mm(g.sg_rod)} + cover ${_mm(fc)}`;
        if (r > req[c][0] + 1e-9) req[c] = [r, why];
      }
    }
    const mid = g.sg_rod + 2 * g.sg_cover;
    for (const x of GAPS){
      const c = NODE_CARRIER[x[2]];
      if (mid > req[c][0] + 1e-9) req[c] = [mid, `lead at mid-plane: ${_mm(g.sg_rod)} + 2 x cover ${_mm(g.sg_cover)}`];
    }
    const out = {};
    for (const k of Object.keys(CARRIER_BASE)){
      const base = g[CARRIER_BASE[k]], [r, why] = req[k], t = g.zs_mode === "auto" ? Math.max(base, r) : base;
      out[k] = {base, req: r, t, why, stretched: t > base + 1e-9};
    }
    return out;
  }

  function build(locked, geom){
    const g = Object.assign({}, GEOM_DEFAULTS, geom || {});
    const L = locked.ladder, P = locked.plates;
    const nk = Math.trunc(P.n_kept);
    const ri = P.r_inMm, ro = P.r_outMm;
    const ca = solve_transfer(L.Ca * g.ca_cal, g, nk, ro - g.ca_margin), cb = solve_transfer(L.Cb * g.ca_cal, g, nk, ro - g.ca_margin);
    const rr_in = Math.max(0.0, ri - g.rotor_in_off);
    const r_edge = ro * 500.0 / 387.0;
    const cx_rin = ro * 58.0 / 387.0, cx_rout = ro * 350.0 / 387.0, bar_rin = ro * 75.0 / 387.0;
    const sb = P.N_sec, w_sec = 360.0 / sb, nh = Math.floor(sb / 2);
    const odd = [], even = [];
    for (let k = 0; k < nh; k++){ odd.push(w_sec + 2 * w_sec * k); even.push(2 * w_sec * k); }
    const ca_starts = odd.map(s => s + (w_sec - ca.w_deg) / 2), cb_starts = even.map(s => s + (w_sec - cb.w_deg) / 2);
    const w_c = g.c_w_deg || w_sec, w_x = g.cx_w_deg || w_sec;      // C1 / C2 faces, island bars + pickups, on the sector centres
    const c_odd = odd.map(s => s + (w_sec - w_c) / 2), c_even = even.map(s => s + (w_sec - w_c) / 2);
    const w_cs = g.c_ws_deg || w_c, w_ct = g.counter_w_deg || w_sec, w_cr = g.cr_w_deg || w_sec;   // asymmetric faces, hidden backs [IR]
    const s_odd = odd.map(s => s + (w_sec - w_cs) / 2), s_even = even.map(s => s + (w_sec - w_cs) / 2);
    const k_odd = odd.map(s => s + (w_sec - w_ct) / 2), k_even = even.map(s => s + (w_sec - w_ct) / 2);
    const r_odd = odd.map(s => s + (w_sec - w_cr) / 2);
    const x_odd = odd.map(s => s + (w_sec - w_x) / 2), x_even = even.map(s => s + (w_sec - w_x) / 2);
    const ct_ri = g.counter_trim ? (e => Math.max(ri, e.r_in - g.ca_margin)) : (e => ri);   // trimmed counters [IR]
    const fp = {
      C1_stator: _fp("C1 stator plate", "1", "C1", ri, ro - g.c_s_inset, s_odd, w_cs),
      C1_rotor: _fp("C1 rotor face", "R-A", "C1", rr_in, ro, c_odd, w_c),
      C2_stator: _fp("C2 stator plate", "4", "C2", ri, ro - g.c_s_inset, s_even, w_cs),
      C2_rotor: _fp("C2 rotor face", "R-B", "C2", rr_in, ro, c_odd, w_c),
      Ca_el: _fp("Ca electrode", "2", "Ca", ca.r_in, ca.r_out, ca_starts, ca.w_deg),
      Ca_counter: _fp("Ca counter (ND1 back face)", "1", "Ca", ct_ri(ca), ro, k_odd, w_ct),
      Cb_el: _fp("Cb electrode", "3", "Cb", cb.r_in, cb.r_out, cb_starts, cb.w_deg),
      Cb_counter: _fp("Cb counter (ND4 back face)", "4", "Cb", ct_ri(cb), ro, k_even, w_ct),
      Cx4_pickup: _fp("Cx4 pickup", "n23", "Cx4", cx_rin, cx_rout, x_even, w_x),
      Cx4_bars: _fp("island bars on A", "8", "Cx4", bar_rin, cx_rout, x_even, w_x),
      Cx3_pickup: _fp("Cx3 pickup", "n17", "Cx3", cx_rin, cx_rout, x_odd, w_x),
      Cx3_bars: _fp("island bars on B", "7", "Cx3", bar_rin, cx_rout, x_odd, w_x),
      // C_R faces: the rotor-face sectors, aligned on A and B (co-rotating discs: C_R fixed) [OC host]
      CR_A: _fp("C_R plate (rotor A)", "n18", "C_R", rr_in, ro, r_odd, w_cr),
      CR_B: _fp("C_R plate (rotor B)", "n00", "C_R", rr_in, ro, r_odd, w_cr),
    };
    const tf = g.t_foil, gv = P.g_vMm, tcx = g.cx_air + 2 * g.cx_mica;
    const zs = zstretch(g, P), tc = {};
    for (const k of Object.keys(zs)) tc[k] = zs[k].t;
    const cxm = `air ${g6(g.cx_air)} + mica ${g6(g.cx_mica)}/face`;
    const rim = {};   // radial bar band: ND2 / ND3 end at a rim just beyond their outermost foil and its margin [IR]
    if (g.sg_layout === "radial")
      for (const c of Object.keys(RIM_FOILS)) rim[c] = Math.min(r_edge, Math.max(...RIM_FOILS[c].map(k => fp[k].r_out)) + g.ca_margin + g.sg_rimgap);
    const C = (id, kind, node, t, r_in) => ({ id, kind, node, t, r_in, r_out: id in rim ? rim[id] : r_edge });
    const F = key => ({ id: key, kind: "foil", key, t: tf });
    const G = (id, cap, t, medium, footprint = null, margin = 0.0) => ({ id, kind: "gap", cap, t, medium, footprint, margin });
    const seqA = [F("CR_A"), C("A-disc", "rotor", "", tc["A-disc"], 0.0), F("C1_rotor"), G("C1-gap", "C1", gv, "air"),
      F("C1_stator"), C("ND1", "stator", "", tc.ND1, g.r_bore), F("Ca_counter"),
      G("Ca-diel", "Ca", ca.t, ca.diel, "Ca_el", g.ca_margin), F("Ca_el"),
      C("ND2", "stator", "", tc.ND2, g.r_bore), F("Cx4_pickup"), G("Cx4-gap", "Cx4", tcx, cxm),
      F("Cx4_bars"), C("A-flange", "rotor-flange", "", tc["A-flange"], 0.0)];
    const seqB = [F("CR_B"), C("B-disc", "rotor", "", tc["B-disc"], 0.0), F("C2_rotor"), G("C2-gap", "C2", gv, "air"),
      F("C2_stator"), C("ND4", "stator", "", tc.ND4, g.r_bore), F("Cb_counter"),
      G("Cb-diel", "Cb", cb.t, cb.diel, "Cb_el", g.ca_margin), F("Cb_el"),
      C("ND3", "stator", "", tc.ND3, g.r_bore), F("Cx3_pickup"), G("Cx3-gap", "Cx3", tcx, cxm),
      F("Cx3_bars"), C("B-flange", "rotor-flange", "", tc["B-flange"], 0.0)];
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
    let dz = 0.0; for (const k of Object.keys(CARRIER_BASE)) dz += tc[k] - g[CARRIER_BASE[k]];
    const z_base = stack[stack.length - 1].z1 - stack[0].z0 - dz;
    const design = { schema: SCHEMA, units: "mm", lock: Object.assign({}, locked), geom: g, Ca: ca, Cb: cb, footprints: fp,
      stack, foils, z_total: stack[stack.length - 1].z1 - stack[0].z0, r_edge, zstretch: zs, z_base };
    design.sparkgaps = sparkgaps(design);
    design.checks = checks(design);
    for (const k of Object.keys(design.sparkgaps.checks)) design.checks["gaps: " + k] = design.sparkgaps.checks[k];
    const [asm, prt] = parts(design);
    design.assemblies = asm; design.parts = prt;
    design.top_label = `PumpGeometry ${locked.hash != null ? locked.hash : ""} - DCCREG drawn pump, stage 2 plate geometry (Ca/Cb geometrized)`;
    return design;
  }

  /* ---- the bill of solids (1:1 with sim/pump_geometry.py parts()): the CAD builders only build this list ---- */
  const NODE_RGB = {"1": [0.49, 0.82, 1.0], "2": [1.0, 0.71, 0.33], "3": [0.27, 0.77, 0.42], "4": [0.90, 0.28, 0.30],
    "R-A": [0.78, 0.57, 0.92], "R-B": [0.97, 0.46, 0.56], "7": [0.62, 0.81, 0.42], "8": [0.88, 0.69, 0.41],
    "n17": [0.55, 0.90, 0.80], "n23": [1.0, 0.88, 0.55], "n18": [0.55, 0.45, 0.95], "n00": [0.95, 0.55, 0.80]};
  const NODE_DESC = {   // the netlist of record's nodes (= sim/circuit_integrity.py NODE_INFO)
    "1": "ND1 - A-rail: C1 stator plate + Ca counter-electrode", "2": "ND2 - AR bank: Ca electrode",
    "3": "ND3 - BR bank: Cb electrode", "4": "ND4 - B-rail: C2 stator plate + Cb counter-electrode",
    "R-A": "ND5 - resonator end A: rotor A (C1 rotor face)", "R-B": "ND6 - resonator end B: rotor B (C2 rotor face)",
    "7": "ND7 - island on rotor B (Cx3 bars)", "8": "ND8 - island on rotor A (Cx4 bars)",
    "n18": "ND9 - C_R plate on rotor A (L_R1 to R-A)", "n00": "ND10 - C_R plate on rotor B (L_R2 to R-B)",
    "n17": "Cx3 pickup on ND3 (Lx3 to node 3)", "n23": "Cx4 pickup on ND2 (Lx4 to node 2)"};
  const MEDIUM_RGB = {garolite: [0.55, 0.50, 0.30], mica: [0.75, 0.70, 0.55]};
  const CARRIER_RGB = [0.35, 0.40, 0.47];
  const MATERIAL = {"stator": "G10 carrier", "rotor": "G10 rotor disc", "rotor-flange": "G10 rotor flange"};
  const CARRIER_ROLE = {"A-flange": "rotor A outer flange; holds the ND8 island bars",
    "B-flange": "rotor B outer flange; holds the ND7 island bars",
    "A-disc": "rotor A main disc; holds the C1 rotor face (R-A) and, septum side, the C_R plate (n18)",
    "B-disc": "rotor B main disc; holds the C2 rotor face (R-B) and, septum side, the C_R plate (n00)",
    "ND1": "stator carrier ND1; holds the C1 stator plate and the Ca counter-electrode (A-rail, 1)",
    "ND2": "stator carrier ND2; holds the Ca electrode (AR bank, 2) and the Cx4 pickup (n23)",
    "ND3": "stator carrier ND3; holds the Cb electrode (BR bank, 3) and the Cx3 pickup (n17)",
    "ND4": "stator carrier ND4; holds the C2 stator plate and the Cb counter-electrode (B-rail, 4)"};
  const CARRIER_KINDS = ["rotor", "stator", "rotor-flange"];
  const node_rgb = node => NODE_RGB[String(node)] || CARRIER_RGB;
  const _mm = x => { let s = x.toFixed(2); if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, ""); return (s === "-0" || s === "") ? "0" : s; };
  const _m360 = x => ((x % 360.0) + 360.0) % 360.0;
  const _zr = it => `z ${_mm(it.z0)}..${_mm(it.z1)}`;
  function parts(design){
    // CAD groups are ELECTRICAL (1:1 with the Python): conductors in the group of their node, insulators in
    // "carriers" / "dielectrics"; every label is "<group> / <name> - <description> [<material>, <body>]"
    const st = design.stack, fp = design.footprints, asm = [], out = [];
    const assembly = (key, label) => { if (!asm.some(a => a.key === key)) asm.push({key, label}); return key; };
    const node_group = node => assembly(`node-${node}`, `node-${node} - Node ${node}: ${NODE_DESC[node] || ""}`);
    const carrier_of = {}, face_of = {};
    st.forEach((it, i) => {
      if (it.kind !== "foil") return;
      const nb = [i - 1, i + 1].filter(j => j >= 0 && j < st.length && CARRIER_KINDS.includes(st[j].kind)).map(j => st[j]);
      carrier_of[it.id] = nb.length ? nb[0].id : "foils";
      face_of[it.id] = (nb.length && Math.abs(it.z0) < Math.abs(nb[0].z0)) ? "septum side" : "outer side";
    });
    const P = (name, desc, assembly, role, carrier, node, cap, material, body, r_in, r_out, start_deg, w_deg, z0, z1, rgb) =>
      out.push({name, label: `${assembly} / ${name} - ${desc} [${material}, ${body}]`, assembly, role, carrier, node, cap, material, body,
        shape: "sector", chains: [carrier || assembly], r_in, r_out, start_deg, w_deg, z0, z1, rgb: rgb.slice(),
        volume: 0.5 * rad(Math.min(w_deg, 360.0)) * (r_out * r_out - r_in * r_in) * (z1 - z0)});
    const DIEL = "dielectrics - septum (C_R, garolite), the Ca / Cb mica slabs and the Cx mica facings; no node";
    for (const it of st){
      const kind = it.kind;
      if (CARRIER_KINDS.includes(kind)){
        const a = assembly("carriers", "carriers - the insulating carrier discs (G10); no node"), body = ROTOR_BODY[it.id] || "stator";
        const rings = _carrier_rings(it, (design.sparkgaps || {}).recesses || []);
        rings.forEach(([r0, r1, z0, z1], ri) => {
          const thin = Math.abs((z1 - z0) - it.t) > 1e-9;
          P(it.id.replace(/-/g, "_") + "_carrier" + (rings.length > 1 ? `_${ri + 1}` : ""),
            `${it.id} carrier${rings.length > 1 ? " ring " + (ri + 1) + " of " + rings.length : ""}, insulating: ${CARRIER_ROLE[it.id] || kind}; ` +
            `r${_mm(r0)}-${_mm(r1)} mm, ${_mm(z1 - z0)} mm thick${thin ? " (recessed spark-gap band)" : ""}, z ${_mm(z0)}..${_mm(z1)}`,
            a, "carrier", it.id, "", "", MATERIAL[kind].replace("G10", design.geom.carrier_mat), body, r0, r1, 0.0, 360.0, z0, z1, CARRIER_RGB);
        });
      } else if (kind === "foil"){
        const car = carrier_of[it.id], a = node_group(it.node), body = ROTOR_BODY[car] || "stator", n = it.starts.length;
        it.starts.forEach((s0, k) => {
          let ang;
          if (it.w_deg >= 360.0 - 1e-9) ang = "full ring";
          else { const e = _m360(s0 + it.w_deg); ang = `sector ${k + 1} of ${n} (${_mm(_m360(s0))}-${_mm(e !== 0 ? e : 360.0)} deg)`; }
          P(`${it.key}_${k + 1}`,
            `${it.name}, node ${it.node}, ${it.cap}, ${ang}, r${_mm(it.r_in)}-${_mm(it.r_out)} mm, Al foil ${_mm(it.z1 - it.z0)} mm, ` +
            `${face_of[it.id]} of ${car}, ${_zr(it)}`,
            a, "foil", car, it.node, it.cap, "Al foil", body, it.r_in, it.r_out, s0, it.w_deg, it.z0, it.z1, node_rgb(it.node));
        });
      } else if (kind === "gap" && MEDIUM_RGB[it.medium]){
        const a = assembly("dielectrics", DIEL);
        if (it.footprint){
          const e = fp[it.footprint], m = it.margin || 0.0;
          const rin = Math.max(0.0, e.r_in - m), rout = e.r_out + m, dw = deg(m / Math.max(e.r_in, 1e-9)), n = e.starts.length;
          e.starts.forEach((s0, k) => {
            const w = Math.min(e.w_deg + 2 * dw, 360.0), a0 = s0 - dw;
            P(`${it.id.replace(/-/g, "_")}_${k + 1}`,
              `${it.id}_${k + 1}, ${it.medium} dielectric for ${it.cap} (between the ${it.cap} electrode and its counter), slab ${k + 1} of ${n} ` +
              `(${_mm(_m360(a0))}-${_mm(_m360(a0 + w))} deg), r${_mm(rin)}-${_mm(rout)} mm, ${_mm(it.t)} mm thick (foil + ${_mm(m)} mm margin), ${_zr(it)}`,
              a, "dielectric", "", "", it.cap, it.medium, "stator", rin, rout, a0, w, it.z0, it.z1, MEDIUM_RGB[it.medium]);
          });
        } else {
          const rin = it.r_in != null ? it.r_in : 0.0, rout = it.r_out != null ? it.r_out : design.r_edge;
          P(it.id.replace(/-/g, "_"),
            `${it.id}, ${it.medium}, ${it.cap} dielectric between rotor A and rotor B, r${_mm(rin)}-${_mm(rout)} mm, ${_mm(it.t)} mm thick, ${_zr(it)}`,
            a, "dielectric", "", "", it.cap, it.medium, "rotor AB", rin, rout, 0.0, 360.0, it.z0, it.z1, MEDIUM_RGB[it.medium]);
        }
      }
    }
    for (const x of cx_facings(design)){
      const a = assembly("dielectrics", DIEL);
      P(x.name, `${x.cap} mica facing on ${x.foil} (${x.carrier}), r${_mm(x.r_in)}-${_mm(x.r_out)} mm, ${_mm(x.z1 - x.z0)} mm, z ${_mm(x.z0)}..${_mm(x.z1)}`,
        a, "dielectric", x.carrier, "", x.cap, "mica", x.body, x.r_in, x.r_out, x.start_deg, x.w_deg, x.z0, x.z1, MEDIUM_RGB.mica);
    }
    const sgp = design.sparkgaps;
    if (sgp){
      for (const it of sgp.items){
        const akey = node_group(it.node);
        const mat = it.kind === "sector" ? "Cu bus" : it.kind === "sphere" ? (it.r <= 6.0 + 1e-9 ? "W-Cu sphere" : "polished sphere")
          : ({link: "Cu link", "gap-stem": "Cu stem", bus: "Cu bus"}[it.role] || "Cu lead");
        const base = {name: it.name, label: `${akey} / ${it.name} - ${it.desc}, in ${it.carrier} [${mat}, ${it.body}]`, assembly: akey, role: it.role,
          carrier: it.carrier, node: it.node, cap: it.gap, material: mat, body: it.body, rgb: node_rgb(it.node).slice(), chains: it.chains.slice()};
        if (it.kind === "sector")
          Object.assign(base, {shape: "sector", r_in: it.r_in, r_out: it.r_out, start_deg: it.start_deg, w_deg: it.w_deg,
            z0: it.z0, z1: it.z1, volume: 0.5 * rad(it.w_deg) * (it.r_out ** 2 - it.r_in ** 2) * (it.z1 - it.z0)});
        else if (it.kind === "sphere")
          Object.assign(base, {shape: "sphere", c: it.c.slice(), r: it.r, volume: 4.0 / 3.0 * Math.PI * it.r ** 3});
        else {
          const L = dist(it.p0, it.p1);
          Object.assign(base, {shape: "rod", p0: it.p0.slice(), p1: it.p1.slice(), r: it.r, volume: Math.PI * it.r ** 2 * L});
        }
        out.push(base);
      }
    }
    return [asm, out];
  }

  /* ---- spark gaps IN the stack (1:1 with sim/pump_geometry.py sparkgaps / sweep_check / gap_checks) ---- */
  const GAPS = [["SG1", "return", "2", "rotor A (R-A)", "A", "return", 3.00], ["SG4a1", "load", "4", "island bar 8", "A", "bar", 37.20],
    ["SG4b1", "fire", "2", "island bar 8", "A", "bar", 46.05], ["BS4", "backstop", "2", "island bar 8", "A", "bar", 49.00],
    ["SG2", "return", "3", "rotor B (R-B)", "B", "return", 33.00], ["SG3a1", "load", "1", "island bar 7", "B", "bar", 7.20],
    ["SG3b1", "fire", "3", "island bar 7", "B", "bar", 16.05], ["BS3", "backstop", "3", "island bar 7", "B", "bar", 19.00]];
  const NETLIST_GAPS = {SG1: ["2", "R-A"], SG2: ["3", "R-B"], SG3a1: ["1", "7"], SG3b1: ["7", "3"], BS3: ["7", "3"],
    SG4a1: ["4", "8"], SG4b1: ["8", "2"], BS4: ["8", "2"]};
  const ROTOR_NODE = {"rotor A (R-A)": "R-A", "rotor B (R-B)": "R-B", "island bar 7": "7", "island bar 8": "8"};
  const NODE_CARRIER = {"1": "ND1", "2": "ND2", "3": "ND3", "4": "ND4"};
  const SIDE_OF_CARRIER = {ND1: "A", ND2: "A", ND3: "B", ND4: "B"};
  const SPACING_KEY = {return: "sg_s_ret", load: "sg_s_load", fire: "sg_s_fire", backstop: "sg_s_bs"};
  const BANDS = [[["A", "bar"], ["A-flange", "Cx4_bars", "ND2"]], [["A", "return"], ["A-disc", "C1_rotor", "ND1"]],
    [["B", "bar"], ["B-flange", "Cx3_bars", "ND3"]], [["B", "return"], ["B-disc", "C2_rotor", "ND4"]]];
  const BAND = {}; for (const [[sd, bd], v] of BANDS) BAND[sd + "|" + bd] = v;
  const BODY_OF = {stator: "stator", "rotor A": "rotor", "rotor B": "rotor"};
  const ROTOR_BODY = {"A-disc": "rotor A", "A-flange": "rotor A", "B-disc": "rotor B", "B-flange": "rotor B"};
  const SPOKES = 6;
  const _pol = (r, a, z) => [r * Math.cos(rad(a)), r * Math.sin(rad(a)), z];
  const dist = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
  const _face_toward = (c, o) => (o.z0 >= c.z1 - 1e-9 ? c.z1 : c.z0);
  const _sdeg = x => x - 360.0 * Math.floor((x + 180.0) / 360.0);

  function _nearest_inside(a, starts, w, ins){
    const half = Math.max(0.0, w / 2 - ins);
    let best = null;
    for (const s0 of starts){
      const d = _sdeg(a - (s0 + w / 2)), cl = Math.min(half, Math.max(-half, d));
      if (best === null || Math.abs(d - cl) < Math.abs(best) - 1e-9) best = d - cl;
    }
    return best !== null ? a - best : a;
  }
  function _route(r0, a0, z, foil, zf, R_ch, run_starts, w_run, ins_mm){
    const r_t = foil.r_out - Math.min(10.0, (foil.r_out - foil.r_in) / 2), ins = deg(ins_mm / r_t);
    const pts = [[r0, a0, z]], what = [];
    if (foil.r_in + ins_mm <= r0 && r0 <= foil.r_out - ins_mm && Math.abs(_nearest_inside(a0, foil.starts, foil.w_deg, deg(ins_mm / r0)) - a0) < 1e-9){
      pts.push([r0, a0, zf]); what.push(`riser straight to ${foil.id} (node ${foil.node})`);
      return [pts, what];
    }
    const arc = (r, af, at, txt) => { const n = Math.max(1, Math.ceil(Math.abs(at - af) / 10.0 - 1e-9));
      for (let i = 1; i <= n; i++){ pts.push([r, af + (at - af) * i / n, z]); what.push(txt); } };
    const ar = _nearest_inside(a0, run_starts, w_run, ins);
    if (Math.abs(ar - a0) > 1e-9){
      pts.push([R_ch, a0, z]); what.push(`radial to the chord ring R${_mm(R_ch)}`);
      arc(R_ch, a0, ar, `round the chord ring to ${_mm(_m360(ar))} deg`);
    }
    const at = _nearest_inside(ar, foil.starts, foil.w_deg, ins);
    pts.push([r_t, ar, z]); what.push(`radial to r${_mm(r_t)} at ${_mm(_m360(ar))} deg`);
    if (Math.abs(at - ar) > 1e-9) arc(r_t, ar, at, `under ${foil.id} to ${_mm(_m360(at))} deg`);
    pts.push([r_t, at, zf]); what.push(`riser to ${foil.id} (node ${foil.node})`);
    return [pts, what];
  }
  function _route_rim(r0, a0, z, foil, zf, R_ch, run_starts, w_run, ins_mm){
    const r_t = foil.r_out - Math.min(10.0, (foil.r_out - foil.r_in) / 2);
    if (Math.abs(_nearest_inside(a0, foil.starts, foil.w_deg, deg(ins_mm / r_t)) - a0) < 1e-9)
      return [[[r0, a0, z], [r_t, a0, z], [r_t, a0, zf]], [`radial in to r${_mm(r_t)} under ${foil.id}`, `riser to ${foil.id} (node ${foil.node})`]];
    return _route(r0, a0, z, foil, zf, R_ch, run_starts, w_run, ins_mm);
  }
  function _foil_carriers(st){
    const out = {};
    st.forEach((it, i) => {
      if (it.kind !== "foil") return;
      const nb = [i - 1, i + 1].filter(j => j >= 0 && j < st.length && CARRIER_KINDS.includes(st[j].kind)).map(j => st[j]);
      out[it.id] = nb.length ? nb[0].id : "";
    });
    return out;
  }

  function sparkgaps(design){
    const g = design.geom, st = design.stack, fp = design.footprints, byid = {};
    st.forEach(it => byid[it.id] = it);
    const on = _foil_carriers(st), R_e = design.r_edge, R_frame = R_e + g.sg_frame, R_ch = R_e - g.sg_chord;
    const rim = {}, chord = {};
    for (const c of Object.keys(CARRIER_BASE)){ rim[c] = byid[c].r_out; chord[c] = rim[c] - g.sg_chord; }
    const rod = g.sg_rod / 2, ins_mm = rod + g.sg_cover, smap = {};
    for (const cls of Object.keys(SPACING_KEY)) smap[cls] = g[SPACING_KEY[cls]];
    const NS = design.lock.plates.N_sec, w_sec = 360.0 / NS, grid = {odd: [], even: []};
    for (let k = 0; k < Math.trunc(NS) / 2 >> 0; k++){ grid.odd.push(w_sec + 2 * w_sec * k); grid.even.push(2 * w_sec * k); }
    const run_of = foil => { const c = foil.starts[0] + foil.w_deg / 2; return Math.floor(_m360(c) / w_sec + 1e-9) % 2 ? grid.even : grid.odd; };
    const needs = band_needs(g, design.lock.plates);
    const bands = {}, recesses = [], lead_z = {};
    for (const [[side, band], [rc, rfoil, sc]] of BANDS){
      const rcar = byid[rc], scar = byid[sc], zr = _face_toward(rcar, scar), zs = _face_toward(scar, rcar);
      const D = Math.abs(zs - zr), mine = GAPS.filter(x => x[4] === side && x[5] === band);
      const nb = needs[side + "|" + band], sgn = zs > zr ? 1.0 : -1.0, R_t = g.sg_d / 2;
      if (nb.layout === "radial"){
        const ld = mine.find(x => x[1] === "load"), R_v = Math.max(...mine.filter(x => x[1] !== "load").map(x => sphere_d(g, x[1]) / 2));
        const r_c = Math.max(g.sg_rbar, rim[sc] + Math.max(g.sg_stem_air + R_v, R_t + g.sg_clear));
        const r_l = r_c + R_t + smap[ld[1]] + sphere_d(g, ld[1]) / 2, z_st = {};
        for (const k of Object.keys(nb.zeta)) z_st[k] = zs - sgn * nb.zeta[k];
        bands[side + "|" + band] = {side, band, rotor_carrier: rc, stator_carrier: sc, r: r_c, r0: rim[sc], r1: r_l + sphere_d(g, ld[1]) / 2 + 2.0,
          D, G: D, recess: 0.0, Fr: zr, Fs: zs, sgn, rotor_node: fp[rfoil].node, p_rot: nb.p_rot, e_st: 0.0, e_rot: 0.0,
          layout: "radial", r_rim: rim[sc], r_load: r_l, z_tip: zs - sgn * nb.zeta_tip, z_st};
        lead_z[sc] = zs - sgn * nb.lead;
        lead_z[rc] = zr - sgn * (g.sg_seat + rod);
        continue;
      }
      const rec = Math.max(0.0, nb.need - D) / 2;
      const Fr = zr - sgn * rec, Fs = zs + sgn * rec, G = Math.abs(Fs - Fr);
      const r_c = band === "bar" ? g.sg_rbar : g.sg_rrail;
      const dmax = Math.max(...mine.map(x => sphere_d(g, x[1])));
      const r0 = r_c - dmax / 2 - 2.0, r1 = r_c + dmax / 2 + 2.0, z_st = {};
      for (const x of mine) z_st[x[0]] = Fs - sgn * ((G - smap[x[1]] - nb.p_rot) - sphere_d(g, x[1]) / 2);
      bands[side + "|" + band] = {side, band, rotor_carrier: rc, stator_carrier: sc, r: r_c, r0, r1, D, G, recess: rec, Fr, Fs, sgn, rotor_node: fp[rfoil].node,
        p_rot: nb.p_rot, e_st: nb.e_st, e_rot: nb.e_rot, layout: "axial", r_rim: rim[sc], r_load: r_c, z_tip: Fr + sgn * (nb.p_rot - R_t), z_st};
      lead_z[sc] = Fs + sgn * (nb.e_st + g.sg_seat + rod);
      lead_z[rc] = Fr - sgn * (nb.e_rot + g.sg_seat + rod);
      if (rec > 0){
        recesses.push({carrier: rc, r0, r1, depth: rec, face: sgn > 0 ? "z1" : "z0"});
        recesses.push({carrier: sc, r0, r1, depth: rec, face: sgn > 0 ? "z0" : "z1"});
      }
    }
    for (const c of Object.keys(CARRIER_BASE)) if (!(c in lead_z)) lead_z[c] = 0.5 * (byid[c].z0 + byid[c].z1);
    const target = (carrier, node, z) => {
      let best = null;
      for (const it of st)
        if (it.kind === "foil" && on[it.id] === carrier && it.node === node){
          const d = Math.abs(0.5 * (it.z0 + it.z1) - z);
          if (best === null || d < best[0] - 1e-9) best = [d, it];
        }
      return best[1];
    };
    const gaps = [], items = [], routes = [];
    const polyline = (pts, name, gap, node, chains, side, body, carrier, what, embedded) => {
      const out = [];
      for (let i = 0; i < pts.length - 1; i++){
        const p0 = _pol(...pts[i]), p1 = _pol(...pts[i + 1]);
        if (dist(p0, p1) < 1e-9) continue;
        out.push({kind: "rod", name: `${name}${String.fromCharCode(97 + out.length)}`, gap, node, role: "gap-lead", p0, p1, r: rod, chains, side, body,
          carrier: Array.isArray(carrier) ? carrier[i] : carrier, embedded: Array.isArray(embedded) ? embedded[i] : embedded,
          riser: i === pts.length - 2, desc: Array.isArray(what) ? what[i] : what});
      }
      return out;
    };
    for (const [name, cls, snode, rot, side, band, stn] of GAPS){
      const b = bands[side + "|" + band], s_ = smap[cls], d_st = sphere_d(g, cls), R_ = d_st / 2;
      const car = NODE_CARRIER[snode], host = b.stator_carrier, foreign = car !== host, crossover = foreign && SIDE_OF_CARRIER[car] !== side;
      const hz = lead_z[host], cz = lead_z[car], z_st = b.z_st[name];
      let mount, p_st, e_, r_st;
      if (b.layout === "radial"){ mount = cls === "load" ? "arm" : "rim"; p_st = d_st; e_ = 0.0; r_st = mount === "arm" ? b.r_load : b.r; }
      else { mount = "socket"; p_st = b.G - s_ - b.p_rot; e_ = d_st - p_st; r_st = b.r; }
      const s_car = mount === "arm" ? "stator frame" : host, bk = `${side}-${band}`;
      let lead_len = 0.0, arm_len = 0.0;
      for (let k = 0; k < SPOKES; k++){
        const a = stn + 60.0 * k, ch = [`btn-${name}-${k + 1}`, host].concat(foreign ? [car] : []);
        const cen = _pol(r_st, a, z_st);
        let where, s_end, s_what;
        if (mount === "socket"){
          where = `on ${host} at r${_mm(r_st)} ${_mm(_m360(a))} deg, apex ${_mm(p_st)} mm proud, ` + (e_ >= 0 ? `${_mm(e_)} mm in its socket` : `on its stem ${_mm(-e_)} mm above the face`);
          s_end = [r_st, a, hz]; s_what = `sphere centre to the lead plane in ${host}`;
        } else if (mount === "rim"){
          where = `at r${_mm(r_st)} ${_mm(_m360(a))} deg on a radial stem out of the ${host} rim r${_mm(b.r_rim)}, centre ${_mm(Math.abs(z_st - b.Fs))} mm below its Cx face, under the tip path (vertical gap)`;
          s_end = [b.r_rim - g.sg_seat, a, z_st]; s_what = `radial, sphere centre into the ${host} rim (seated ${_mm(g.sg_seat)} mm)`;
        } else {
          where = `at r${_mm(r_st)} ${_mm(_m360(a))} deg on a radial arm in from the stator frame R${_mm(R_frame)}, at the tip height beside its path (horizontal gap)`;
          s_end = [R_frame, a, z_st]; s_what = `radial, sphere centre out to the stator frame R${_mm(R_frame)}`;
        }
        items.push({kind: "sphere", name: `${name}_sph_${k + 1}`, gap: name, node: snode, role: "gap-stator",
          c: cen, r: R_, chains: ch, side, body: "stator", carrier: s_car, band: bk,
          desc: `${name} stator sphere ${k + 1} of ${SPOKES} (${cls}), node ${snode}, ${_mm(d_st)} mm ${cls === "backstop" ? "polished" : "W-Cu"} ${where}, gap ${_mm(s_)} mm to the ${rot} tip` +
            (foreign ? ` - fed from ${car}` + (crossover ? " by a CROSSOVER over the stator" : "") : "")});
        items.push({kind: "rod", name: `${name}_stem_${k + 1}`, gap: name, node: snode, role: "gap-stem", p0: cen.slice(), p1: _pol(...s_end),
          r: g.sg_stem / 2, chains: ch, side, body: "stator", carrier: s_car, embedded: false, band: bk,
          desc: `${name} ${mount === "arm" ? "arm" : "stem"} ${k + 1} (node ${snode}): ${s_what}`});
        const f = target(car, snode, mount === "rim" ? z_st : cz), zf = 0.5 * (f.z0 + f.z1), nm = `${name}_lead_${k + 1}`;
        let pts, carriers, emb, what;
        if (mount === "rim"){
          const [p_, w_in] = _route_rim(s_end[0], a, z_st, f, zf, chord[car], run_of(f), w_sec, ins_mm);
          pts = p_; carriers = car; emb = Array(pts.length - 2).fill(true).concat([false]); what = w_in.map(x => `in ${car}: ${x}`);
        } else if (mount === "arm"){
          const [inner, w_in] = _route(rim[car], a, cz, f, zf, chord[car], run_of(f), w_sec, ins_mm), n_in = inner.length - 1;
          pts = [s_end, [R_frame, a, cz]].concat(inner);
          carriers = ["stator frame", car].concat(Array(n_in).fill(car));
          emb = [false, false].concat(Array(n_in - 1).fill(true), [false]);
          what = [`along the frame R${_mm(R_frame)} to ${car}` + (crossover ? " - CROSSOVER over the stator" : ""), `into the ${car} rim`].concat(w_in.map(x => `in ${car}: ${x}`));
        } else if (foreign){
          const [inner, w_in] = _route(rim[car], a, cz, f, zf, chord[car], run_of(f), w_sec, ins_mm), n_in = inner.length - 1;
          pts = [[r_st, a, hz], [rim[host], a, hz], [R_frame, a, hz], [R_frame, a, cz]].concat(inner);
          carriers = [host, host, host].concat(Array(n_in + 1).fill(car));
          emb = [true, false, false, false].concat(Array(n_in - 1).fill(true), [false]);
          what = [`embedded in ${host}, radial to its rim`, "out to the stator frame",
            `along the frame R${_mm(R_frame)} to ${car}` + (crossover ? " - CROSSOVER over the stator" : ""), `into the ${car} rim`].concat(w_in.map(x => `in ${car}: ${x}`));
        } else {
          const [p_, w_in] = _route(r_st, a, hz, f, zf, chord[host], run_of(f), w_sec, ins_mm);
          pts = p_; carriers = host; emb = Array(pts.length - 2).fill(true).concat([false]); what = w_in.map(x => `in ${host}: ${x}`);
        }
        const segs = polyline(pts, nm, name, snode, ch, side, "stator", carriers, what, emb);
        for (const sg_ of segs) sg_.desc = `${name} lead ${k + 1} (node ${snode}): ` + sg_.desc;
        items.push(...segs);
        routes.push({electrode: `${name}_sph_${k + 1}`, node: snode, foil: f.id, carrier: car, end: pts[pts.length - 1].slice()});
        if (k === 0){
          lead_len = 0.0; for (const x of segs) lead_len += dist(x.p0, x.p1);
          arm_len = mount === "arm" ? dist(cen, _pol(...s_end)) : 0.0;
        }
      }
      gaps.push({name, cls, stator_node: snode, rotor: rot, side, band, station: stn, spacing: s_, d_stator: d_st, d_rotor: g.sg_d, r: r_st,
        p_stator: p_st, p_rotor: b.p_rot, socket: e_, host, carrier: car, foreign, crossover, lead_len, mount,
        gap_axis: mount === "arm" ? "horizontal" : "vertical", z_stator: z_st, r_tip: b.r, z_tip: b.z_tip, arm_len});
    }
    for (const key of Object.keys(bands)){
      const b = bands[key], side = b.side, band = b.band, rc = b.rotor_carrier, bar = band === "bar", radial = b.layout === "radial", rfoil = BAND[side + "|" + band][1];
      const tipn = bar ? "bartip" : "rotortip", kind_t = bar ? "island bar" : "rotor face", f = target(rc, b.rotor_node, lead_z[rc]), zf = 0.5 * (f.z0 + f.z1);
      for (let k = 0; k < SPOKES; k++){
        const a = 60.0 * k + g.sg_tip_deg, ch = [`tip-${side}-${band}`, rc, rfoil];
        const cen = _pol(b.r, a, b.z_tip);
        const where = radial ? `hanging from ${rc} at r${_mm(b.r)} ${_mm(a)} deg outside the ${b.stator_carrier} rim r${_mm(b.r_rim)}, its bottom ${_mm(b.p_rot)} mm below the face`
          : `on ${rc} at r${_mm(b.r)} ${_mm(a)} deg, apex ${_mm(b.p_rot)} mm proud, ${_mm(g.sg_d - b.p_rot)} mm in its socket`;
        items.push({kind: "sphere", name: `${tipn}_${side}_${k + 1}`, gap: "", node: b.rotor_node, role: "gap-rotor",
          c: cen, r: g.sg_d / 2, chains: ch, side, body: ROTOR_BODY[rc], carrier: rc, band: `${side}-${band}`,
          desc: `${kind_t} tip ${k + 1} of ${SPOKES} (node ${b.rotor_node}, ${ROTOR_BODY[rc]}), ${_mm(g.sg_d)} mm W-Cu sphere ${where}`});
        items.push({kind: "rod", name: `${tipn}_${side}_stem_${k + 1}`, gap: "", node: b.rotor_node, role: "gap-stem", p0: cen.slice(), p1: _pol(b.r, a, lead_z[rc]),
          r: g.sg_stem / 2, chains: ch, side, body: ROTOR_BODY[rc], carrier: rc, embedded: false, band: `${side}-${band}`,
          desc: `${kind_t} tip ${k + 1} stem (node ${b.rotor_node}): sphere centre to the lead plane in ${rc}`});
        const [pts, w_in] = _route(b.r, a, lead_z[rc], f, zf, radial ? b.r : chord[rc], run_of(f), w_sec, ins_mm);
        const segs = polyline(pts, `${tipn}_${side}_lead_${k + 1}`, "", b.rotor_node, ch, side, ROTOR_BODY[rc], rc, w_in.map(x => `in ${rc}: ${x}`),
          Array(pts.length - 2).fill(true).concat([false]));
        for (const sg_ of segs) sg_.desc = `${kind_t} tip ${k + 1} lead (node ${b.rotor_node}): ` + sg_.desc;
        items.push(...segs);
        routes.push({electrode: `${tipn}_${side}_${k + 1}`, node: b.rotor_node, foil: f.id, carrier: rc, end: pts[pts.length - 1].slice()});
      }
    }
    for (const c of Object.keys(LINKS)){
      const [k1, k2] = LINKS[c], f1 = byid[k1], f2 = byid[k2], cc = byid[c];
      const rr = 0.5 * (Math.max(f1.r_in, f2.r_in) + Math.min(f1.r_out, f2.r_out));
      f1.starts.forEach((s0, k) => {
        const a = s0 + f1.w_deg / 2;
        items.push({kind: "rod", name: `${c.replace("-", "_")}_link_${k + 1}`, gap: "", node: f1.node, role: "link",
          p0: _pol(rr, a, 0.5 * (f1.z0 + f1.z1)), p1: _pol(rr, a, 0.5 * (f2.z0 + f2.z1)), r: rod, chains: [`link-${c}`, c], side: cc.side,
          body: ROTOR_BODY[c] || "stator", carrier: c, embedded: false,
          desc: `${c} equipotential link ${k + 1} of ${f1.starts.length} (node ${f1.node}): ${k1} <-> ${k2} through ${c} at r${_mm(rr)} ${_mm(_m360(a))} deg, ${_mm(Math.abs(cc.z1 - cc.z0))} mm`});
      });
    }
    // bus rings (1:1 with the Python): one per node per carrier, joining that electrode's sectors [IR]
    const hv = g.sg_khv * Math.max(g.sg_s_ret, g.sg_s_load, g.sg_s_fire, g.sg_s_bs), bw = g.sg_bus;
    for (const c of Object.keys(CARRIER_BASE)){
      const cc = byid[c];
      let mine = st.filter(it => it.kind === "foil" && on[it.id] === c);
      mine = mine.filter(it => ROTATING.includes(it.cap)).concat(mine.filter(it => !ROTATING.includes(it.cap)));
      const nodes = [];
      for (const it of mine) if (!nodes.includes(it.node)) nodes.push(it.node);
      const placed = [];
      for (const nd of nodes){
        const fs = mine.filter(it => it.node === nd), f = fs.find(it => !ROTATING.includes(it.cap)) || fs[0];
        const up = f.z0 >= cc.z1 - 1e-9, fc = far_cover(g, c);
        const zc = up ? (cc.z1 - fc - bw / 2) : (cc.z0 + fc + bw / 2);
        let r = f.r_in + bw / 2;
        for (const [rp, zp] of placed){
          const dzs = Math.max(0.0, Math.abs(zc - zp) - bw);
          if (dzs < hv) r = Math.max(r, rp + bw + Math.sqrt(hv * hv - dzs * dzs));
        }
        placed.push([r, zc]);
        const nk = nd.replace("-", ""), ch = [`bus-${c}-${nd}`, c], body = ROTOR_BODY[c] || "stator", cn = c.replace("-", "_");
        items.push({kind: "sector", name: `bus_${cn}_${nk}`, gap: "", node: nd, role: "bus", r_in: r - bw / 2, r_out: r + bw / 2,
          start_deg: 0.0, w_deg: 360.0, z0: zc - bw / 2, z1: zc + bw / 2, chains: ch, side: cc.side, body, carrier: c, embedded: true,
          desc: `${c} bus ring (node ${nd}): joins the ${f.starts.length} sectors of ${f.id}, r${_mm(r)}, ${_mm(bw)} x ${_mm(bw)} mm, embedded ${_mm(fc)} mm under its face`});
        f.starts.forEach((s0, k) => {
          const a = s0 + f.w_deg / 2;
          items.push({kind: "rod", name: `bus_${cn}_${nk}_riser_${k + 1}`, gap: "", node: nd, role: "bus",
            p0: _pol(r, a, zc), p1: _pol(r, a, 0.5 * (f.z0 + f.z1)), r: rod, chains: ch, side: cc.side, body, carrier: c, embedded: false, riser: true,
            desc: `${c} bus riser ${k + 1} of ${f.starts.length} (node ${nd}): bus ring to ${f.id} at ${_mm(_m360(a))} deg`});
        });
      }
    }
    const bandsOut = {}; for (const key of Object.keys(bands)) bandsOut[key.replace("|", "-")] = bands[key];
    const out = {R_frame, R_chord: R_ch, bands: bandsOut, recesses, lead_z, gaps, routes, items};
    out.checks = gap_checks(design, out);
    return out;
  }

  function _seg_rmin(a, b){
    const dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy;
    const t = L2 < 1e-18 ? 0.0 : Math.min(1.0, Math.max(0.0, -(a[0] * dx + a[1] * dy) / L2));
    return Math.hypot(a[0] + t * dx, a[1] + t * dy);
  }
  function _seg_dist(p, q, r, s){
    const d1 = [0, 1, 2].map(i => q[i] - p[i]), d2 = [0, 1, 2].map(i => s[i] - r[i]), w = [0, 1, 2].map(i => p[i] - r[i]);
    const dot = (x, y) => x[0] * y[0] + x[1] * y[1] + x[2] * y[2];
    const a = dot(d1, d1), e = dot(d2, d2), f_ = dot(d2, w);
    const cl = x => Math.min(1.0, Math.max(0.0, x));
    let t, u;
    if (a < 1e-18 && e < 1e-18) return dist(p, r);
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
    return dist([0, 1, 2].map(i => p[i] + d1[i] * t), [0, 1, 2].map(i => r[i] + d2[i] * u));
  }
  function _foil_dist(pt, f, lat = 0.0){
    const r = Math.hypot(pt[0], pt[1]), a = deg(Math.atan2(pt[1], pt[0]));
    const dz = Math.max(0.0, f.z0 - pt[2], pt[2] - f.z1);
    let best = Infinity;
    for (const s0 of f.starts){
      const d = _sdeg(a - (s0 + f.w_deg / 2));
      let dp;
      if (Math.abs(d) <= f.w_deg / 2 || f.w_deg >= 360.0 - 1e-9) dp = Math.max(0.0, f.r_in - r, r - f.r_out);
      else {
        dp = Infinity;
        for (const e_ of [s0, s0 + f.w_deg]){
          const ex = Math.cos(rad(e_)), ey = Math.sin(rad(e_));
          const t = Math.min(f.r_out, Math.max(f.r_in, pt[0] * ex + pt[1] * ey));
          dp = Math.min(dp, Math.hypot(pt[0] - t * ex, pt[1] - t * ey));
        }
      }
      best = Math.min(best, Math.hypot(Math.max(0.0, dp - lat), dz));
    }
    return best;
  }

  function _carrier_rings(c, recesses){
    const cuts = recesses.filter(r => r.carrier === c.id).sort((p, q) => p.r0 - q.r0);
    const rings = []; let r = c.r_in;
    for (const cut of cuts){
      if (cut.r0 > r) rings.push([r, cut.r0, c.z0, c.z1]);
      let z0 = c.z0, z1 = c.z1;
      if (cut.face === "z1") z1 -= cut.depth; else z0 += cut.depth;
      rings.push([cut.r0, cut.r1, z0, z1]); r = cut.r1;
    }
    if (r < c.r_out) rings.push([r, c.r_out, c.z0, c.z1]);
    return rings;
  }

  function cx_facings(design){
    const g = design.geom, st = design.stack, fp = design.footprints, on = _foil_carriers(st), out = [];
    const caps = (g.cx_mica > 0 ? ["Cx3", "Cx4"] : []).concat(g.c1_mica > 0 ? ["C1", "C2"] : []);
    st.forEach((it, i) => {
      if (it.kind !== "gap" || !caps.includes(it.cap)) return;
      const cx = it.cap.slice(0, 2) === "Cx", m = cx ? g.ca_margin : g.c1_mica_m, t = cx ? g.cx_mica : g.c1_mica;
      for (const [j, low] of [[i - 1, true], [i + 1, false]]){
        const f = st[j], e = fp[f.key];
        const z0 = low ? it.z0 : it.z1 - t, z1 = low ? it.z0 + t : it.z1;
        const rin = Math.max(0.0, e.r_in - m), rout = e.r_out + m, dw = deg(m / Math.max(e.r_in, 1e-9));
        const body = ROTOR_BODY[on[f.id]] || "stator";
        e.starts.forEach((s0, k) => out.push({name: `${it.cap}_mica_${body !== "stator" ? (cx ? "bars" : "rotor") : (cx ? "pickup" : "stator")}_${k + 1}`, cap: it.cap, foil: f.id,
          r_in: rin, r_out: rout, start_deg: s0 - dw, w_deg: Math.min(e.w_deg + 2 * dw, 360.0), z0, z1, body, carrier: on[f.id]}));
      }
    });
    return out;
  }

  function sweep_check(design, sg){
    const st = design.stack, carrier_of = {}, env = [];
    st.forEach((it, i) => {
      if (it.kind !== "foil") return;
      const nb = [i - 1, i + 1].filter(j => j >= 0 && j < st.length && CARRIER_KINDS.includes(st[j].kind)).map(j => st[j]);
      carrier_of[it.id] = nb.length ? nb[0].id : "";
    });
    for (const it of st){
      if (CARRIER_KINDS.includes(it.kind)){ const b = ROTOR_BODY[it.id] || "stator"; for (const ring of _carrier_rings(it, sg.recesses)) env.push([b, it.id, ring]); }
      else if (it.kind === "foil") env.push([ROTOR_BODY[carrier_of[it.id]] || "stator", it.id, [it.r_in, it.r_out, it.z0, it.z1]]);
      else if (it.kind === "gap" && MEDIUM_RGB[it.medium] && it.footprint){
        const e = design.footprints[it.footprint], m = it.margin || 0.0;
        env.push(["stator", it.id, [Math.max(0.0, e.r_in - m), e.r_out + m, it.z0, it.z1]]);
      } else if (it.kind === "gap" && MEDIUM_RGB[it.medium])
        env.push(["rotor AB", it.id, [it.r_in != null ? it.r_in : 0.0, it.r_out != null ? it.r_out : design.r_edge, it.z0, it.z1]]);
    }
    for (const x of cx_facings(design)) env.push([x.body, x.name, [x.r_in, x.r_out, x.z0, x.z1]]);
    for (const it of sg.items){
      let e;
      if (it.kind === "sector") e = [it.r_in, it.r_out, it.z0, it.z1];
      else if (it.kind === "sphere"){ const rc_ = Math.hypot(it.c[0], it.c[1]); e = [rc_ - it.r, rc_ + it.r, it.c[2] - it.r, it.c[2] + it.r]; }
      else {
        const a = it.p0, b = it.p1, ra = Math.hypot(a[0], a[1]), rb = Math.hypot(b[0], b[1]), rr = it.r;
        e = Math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-9 ? [ra - rr, ra + rr, Math.min(a[2], b[2]), Math.max(a[2], b[2])]
          : [_seg_rmin(a, b) - rr, Math.max(ra, rb) + rr, Math.min(a[2], b[2]) - rr, Math.max(a[2], b[2]) + rr];
      }
      env.push([it.body, it.name, e]);
    }
    const rot = env.filter(x => ["rotor A", "rotor B", "rotor AB"].includes(x[0])), sta = env.filter(x => x[0] === "stator"), hits = [];
    for (const [, n1, e] of rot) for (const [, n2, f] of sta)
      if (e[0] < f[1] - 1e-9 && f[0] < e[1] - 1e-9 && e[2] < f[3] - 1e-9 && f[2] < e[3] - 1e-9) hits.push([n1, n2]);
    return [rot.length, sta.length, hits];
  }

  function gap_checks(design, sg){
    const g = design.geom, fp = design.footprints, byid = {}, res = {};
    design.stack.forEach(it => byid[it.id] = it);
    const smax = Math.max(g.sg_s_ret, g.sg_s_load, g.sg_s_fire, g.sg_s_bs), need = g.sg_khv * smax;
    const setEq = (a, b) => a.every(x => b.includes(x)) && b.every(x => a.includes(x));
    const bad = sg.gaps.filter(x => !setEq(NETLIST_GAPS[x.name], [x.stator_node, ROTOR_NODE[x.rotor]])).map(x => x.name);
    res["nodes = netlist of record (topology_edge_list.csv)"] = [!bad.length, !bad.length ? "all 8 gaps" : "mismatch: " + bad.join(", ")];
    let worst = 0.0;
    for (const x of sg.gaps){
      const cc = Math.hypot(x.r - x.r_tip, x.z_stator - x.z_tip);
      worst = Math.max(worst, Math.abs(cc - x.d_stator / 2 - x.d_rotor / 2 - x.spacing));
    }
    const hor = sg.gaps.filter(x => x.gap_axis === "horizontal").map(x => x.name);
    res["spacing at alignment = the freeze table"] = [worst < 1e-9, sg.gaps.map(x => `${x.name} ${_mm(x.spacing)}`).join("; ") + " mm" +
      (hor.length ? ` (${hor.join(", ")} horizontal, the rest vertical)` : "")];
    const ex = sg.gaps.filter(x => x.mount === "socket").map(x => [x.p_stator / x.d_stator, `${x.name} ${_mm(x.p_stator)} of ${_mm(x.d_stator)} mm`]).sort((p, q) => p[0] - q[0])[0];
    const exr = Math.min(...Object.values(sg.bands).filter(b => b.layout === "axial").map(b => b.p_rot / g.sg_d));
    const free = sg.gaps.filter(x => x.mount !== "socket").map(x => x.name);
    res["every sphere shows at least its exposure above the face"] = [Math.min(ex[0], exr) >= g.sg_expose - 1e-9,
      `stator: least ${ex[1]} (${_mm(100 * ex[0])} %), rotor tips ${_mm(100 * exr)} % (>= ${_mm(100 * g.sg_expose)} %)` +
      (free.length ? `; ${free.join(", ")} and the bar tips stand clear on their stems (radial bar band)` : "")];
    let wr = 0.0, wn = "";
    for (const x of sg.gaps){ const q = x.spacing / Math.min(x.d_stator, x.d_rotor); if (q > wr + 1e-9){ wr = q; wn = x.name; } }
    res["sphere gaps in the uniform-field range (s <= 0.5 D, IEC 60052)"] = [wr <= 0.5 + 1e-9, `largest s/D ${_mm(wr)} (${wn})`];
    const inp = design.lock.inputs || {}, db = +(inp.d_ballMm != null ? inp.d_ballMm : 12.0);
    res["switching sphere = the stage-1 sphere-gap ball d_ball"] = [Math.abs(g.sg_d - db) < 1e-9, `${_mm(g.sg_d)} vs d_ball ${_mm(db)} mm`];
    let w = Infinity, det = "no recess needed";
    for (const rc of sg.recesses){
      const c = byid[rc.carrier], left = (c.z1 - c.z0) - rc.depth;
      if (left < w){ w = left; det = `${rc.carrier} keeps ${_mm(left)} mm under a ${_mm(rc.depth)} mm recess`; }
    }
    res["recessed bands leave a carrier wall"] = [w >= g.sg_wall - 1e-9, det];
    for (const [[side, band], [rc, rfoil, sc]] of BANDS){
      const b = sg.bands[`${side}-${band}`];
      let outer, what;
      if (band === "bar"){ outer = Math.max(fp[rfoil].r_out, fp[side === "A" ? "Cx4_pickup" : "Cx3_pickup"].r_out); what = "bars / pickups"; }
      else { outer = Math.max(fp[side === "A" ? "C1_stator" : "C2_stator"].r_out, fp[rfoil].r_out); what = "C1 / C2 plates"; }
      const cl = (b.r - Math.max(g.sg_d, band === "bar" ? g.sg_dbs : g.sg_d) / 2) - outer;
      res[`${side} ${band} band clears the ${what} (HV)`] = [cl >= need, `r${_mm(b.r)} band: ${_mm(cl)} mm beyond r${_mm(outer)} (>= ${_mm(need)})`];
      res[`${side} ${band} band inside the carriers`] = [b.r1 <= design.r_edge - 1e-9, `band r${_mm(b.r0)}-${_mm(b.r1)} within R${_mm(design.r_edge)}` +
        (b.layout === "radial" ? `, under the ${rc} (the ${sc} rim trimmed to r${_mm(b.r_rim)})` : "")];
    }
    for (const b of Object.values(sg.bands)){
      if (b.layout !== "radial") continue;
      const mine = sg.gaps.filter(x => x.side === b.side && x.band === b.band);
      const cl_rim = b.r - g.sg_d / 2 - b.r_rim;
      const bare = Math.min(...mine.filter(x => x.mount === "rim").map(x => x.r - x.d_stator / 2 - b.r_rim));
      const cl_fl = Math.min(...mine.filter(x => x.mount === "arm").map(x => Math.abs(b.Fr - x.z_stator) - x.d_stator / 2));
      res[`${b.side} bar band beside the trimmed ${b.stator_carrier} rim (radial)`] = [
        cl_rim >= g.sg_clear - 1e-9 && bare >= g.sg_stem_air - 1e-9 && cl_fl >= g.sg_clear - 1e-9,
        `${b.stator_carrier} trimmed to r${_mm(b.r_rim)}; tips at r${_mm(b.r)} clear it by ${_mm(cl_rim)} mm, rim stems ` +
        `${_mm(bare)} mm bare, the load sphere at r${_mm(b.r_load)} ${_mm(cl_fl)} mm under the ${b.rotor_carrier} face (>= ${_mm(g.sg_clear)})`];
    }
    let worst_xf = Infinity; det = "";
    for (const x of sg.gaps){
      const tip = _pol(x.r_tip, x.station, x.z_tip);
      for (const y of sg.gaps){
        if (y === x || y.side !== x.side || y.band !== x.band || y.stator_node === x.stator_node) continue;
        for (let k = 0; k < SPOKES; k++){
          const c = _pol(y.r, y.station + 60.0 * k, y.z_stator);
          const surf = dist(tip, c) - x.d_rotor / 2 - y.d_stator / 2;
          const margin = surf - Math.max(x.spacing, y.spacing);
          if (margin < worst_xf - 1e-9){ worst_xf = margin; det = `${x.name} tip vs ${y.name} sphere: ${_mm(surf)} mm`; }
        }
      }
    }
    res["no cross-firing to a different-node station"] = [worst_xf >= 0.5 * Math.max(g.sg_s_load, g.sg_s_fire), `tightest ${det} (margin ${_mm(worst_xf)} mm over its spacing)`];
    const r_i = Math.min(...Object.values(sg.bands).filter(b => b.band === "bar").map(b => b.r));
    const ov = deg((g.sg_d + 2 * g.sg_glat) / r_i);
    res["I11 cross-fire at the placed bar radius"] = [ov < 2.95, `overlap ${_mm(ov)} deg < SG3b-BS3 2.95 deg at r${_mm(r_i)}`];
    const clf = sg.R_frame - g.sg_rod / 2 - design.r_edge;
    res["lead frame clears the rotor rims (HV)"] = [clf >= need, `R${_mm(sg.R_frame)}: ${_mm(clf)} mm over the R${_mm(design.r_edge)} rims`];
    // ---- Z-stretch and wiring (TMD 2026-10-02) ----
    const zs = design.zstretch, zk = Object.keys(zs);
    const short = zk.filter(k => zs[k].t < zs[k].req - 1e-9);
    const grown = zk.filter(k => zs[k].stretched).map(k => `${k} ${_mm(zs[k].base)}->${_mm(zs[k].t)}`).join(", ");
    res["Z-stretch: every carrier holds its gap seats and leads"] = [!short.length, short.length
      ? "short: " + short.map(k => `${k} ${_mm(zs[k].t)} < ${_mm(zs[k].req)} mm`).join(", ")
      : (grown ? `stretched ${grown}; stack ${_mm(design.z_base)} -> ${_mm(design.z_total)} mm` : `no stretch needed; stack ${_mm(design.z_total)} mm`)];
    const unw = [];
    for (const rt of sg.routes){
      const f = byid[rt.foil], [r, a, z] = rt.end;
      const ok = f.node === rt.node && f.z0 - 1e-9 <= z && z <= f.z1 + 1e-9 && f.r_in - 1e-9 <= r && r <= f.r_out + 1e-9 &&
        f.starts.some(s0 => Math.abs(_sdeg(a - (s0 + f.w_deg / 2))) <= f.w_deg / 2 + 1e-9);
      if (!ok) unw.push(rt.electrode);
    }
    res["every gap electrode is wired to its node's foil"] = [!unw.length, !unw.length
      ? `${sg.routes.length} electrodes, each lead ends on a foil of its own node` : "unwired: " + unw.slice(0, 4).join(", ")];
    const rec_by = {};
    for (const rc of sg.recesses) (rec_by[rc.carrier] = rec_by[rc.carrier] || []).push(rc);
    const on = _foil_carriers(design.stack), rings = sg.items.filter(it => it.role === "bus" && it.kind === "sector");
    const foils = design.stack.filter(it => it.kind === "foil").concat(rings.map(x => ({id: x.name, node: x.node, r_in: x.r_in, r_out: x.r_out,
      z0: x.z0, z1: x.z1, starts: [0.0], w_deg: 360.0})));
    for (const x of rings) on[x.name] = x.carrier;
    let w_cov = Infinity, d_cov = "none", w_own = Infinity, d_own = "none", w_oth = Infinity, d_oth = "none";
    const faces = (cid, ra, rb) => {
      const c = byid[cid];
      let lo = c.z0, hi = c.z1;
      for (const rc of (rec_by[cid] || [])){
        if (ra != null && (rb <= rc.r0 || ra >= rc.r1)) continue;
        if (rc.face === "z1") hi = Math.min(hi, c.z1 - rc.depth); else lo = Math.max(lo, c.z0 + rc.depth);
      }
      return [lo, hi];
    };
    for (const x of rings){
      const [lo, hi] = faces(x.carrier, x.r_in, x.r_out), cov = Math.min(x.z0 - lo, hi - x.z1);
      if (cov < w_cov - 1e-9){ w_cov = cov; d_cov = `${x.name} in ${x.carrier}: ${_mm(cov)} mm`; }
    }
    for (const it of sg.items){
      if (it.kind !== "rod" || (it.role !== "gap-lead" && it.role !== "gap-stem")) continue;
      const stem = it.role === "gap-stem", p0 = it.p0, p1 = it.p1, rr = it.r, zlo = Math.min(p0[2], p1[2]) - rr, zhi = Math.max(p0[2], p1[2]) + rr;
      if (it.embedded){
        const [lo, hi] = faces(it.carrier), cov = Math.min(zlo - lo, hi - zhi);
        if (cov < w_cov - 1e-9){ w_cov = cov; d_cov = `${it.name} in ${it.carrier}: ${_mm(cov)} mm`; }
      }
      const n = Math.max(1, Math.ceil(dist(p0, p1) / 2.0 - 1e-9)), pts = [];
      for (let j = 0; j <= n; j++) pts.push([0, 1, 2].map(i => p0[i] + (p1[i] - p0[i]) * j / n));
      for (const f of foils){
        if (f.node === it.node || f.z0 > zhi + 20.0 || f.z1 < zlo - 20.0) continue;
        let dd = Infinity; for (const q of pts) dd = Math.min(dd, stem ? _foil_dist(q, f, rr) : _foil_dist(q, f)); if (!stem) dd -= rr;
        if (on[f.id] === it.carrier){
          if (dd < w_own - 1e-9){ w_own = dd; d_own = `${it.name} (node ${it.node}) to ${f.id} (node ${f.node}) on ${it.carrier}: ${_mm(dd)} mm`; }
        } else if (it.embedded && dd < w_oth - 1e-9){ w_oth = dd; d_oth = `${it.name} (node ${it.node}) to ${f.id} (node ${f.node}) on ${on[f.id]}: ${_mm(dd)} mm`; }
      }
    }
    res["embedded leads and bus rings keep their cover inside the carrier"] = [w_cov >= g.sg_cover - 1e-9, `tightest ${d_cov} (>= ${_mm(g.sg_cover)})`];
    res["leads clear different-node foils on their carrier"] = [w_own >= g.sg_cover - 1e-9, `tightest ${d_own} (>= ${_mm(g.sg_cover)})`];
    const cond = sg.items.filter(it => (it.kind === "rod" || it.kind === "sphere") && it.role !== "link" && !it.riser)
      .map(it => it.kind === "sphere" ? Object.assign({}, it, {p0: it.c, p1: it.c}) : it);
    const box = cond.map(it => [0, 1, 2].map(i => [Math.min(it.p0[i], it.p1[i]) - it.r, Math.max(it.p0[i], it.p1[i]) + it.r]));
    let w_hv = Infinity, d_hv = "none";
    for (let i = 0; i < cond.length; i++){
      const x = cond[i], bx = box[i];
      for (let j = i + 1; j < cond.length; j++){
        const y = cond[j];
        if (BODY_OF[y.body] !== BODY_OF[x.body] || y.node === x.node) continue;
        const by = box[j];
        if ([0, 1, 2].some(k => bx[k][0] - by[k][1] > need || by[k][0] - bx[k][1] > need)) continue;
        const dd = _seg_dist(x.p0, x.p1, y.p0, y.p1) - x.r - y.r;
        if (dd < w_hv - 1e-9){ w_hv = dd; d_hv = `${x.name} (node ${x.node}) / ${y.name} (node ${y.node}): ${_mm(dd)} mm`; }
      }
    }
    rings.forEach((R, ri) => {
      const Rf = Object.assign({}, R, {starts: [0.0], w_deg: 360.0});
      for (const y of cond){
        if (BODY_OF[y.body] !== BODY_OF[R.body] || y.node === R.node) continue;
        const zl = Math.min(y.p0[2], y.p1[2]) - y.r, zh = Math.max(y.p0[2], y.p1[2]) + y.r;
        const rmin = _seg_rmin(y.p0, y.p1), rmax = Math.max(Math.hypot(y.p0[0], y.p0[1]), Math.hypot(y.p1[0], y.p1[1]));
        if (Math.max(R.z0 - zh, zl - R.z1, R.r_in - rmax - y.r, rmin - y.r - R.r_out) > need) continue;
        const n = Math.max(1, Math.ceil(dist(y.p0, y.p1) / 2.0 - 1e-9));
        let dd = Infinity;
        for (let j = 0; j <= n; j++) dd = Math.min(dd, _foil_dist([0, 1, 2].map(i => y.p0[i] + (y.p1[i] - y.p0[i]) * j / n), Rf));
        dd -= y.r;
        if (dd < w_hv - 1e-9){ w_hv = dd; d_hv = `${R.name} (node ${R.node}) / ${y.name} (node ${y.node}): ${_mm(dd)} mm`; }
      }
      for (const Q of rings.slice(ri + 1)){
        if (BODY_OF[Q.body] !== BODY_OF[R.body] || Q.node === R.node) continue;
        const dd = Math.hypot(Math.max(0.0, R.r_in - Q.r_out, Q.r_in - R.r_out), Math.max(0.0, R.z0 - Q.z1, Q.z0 - R.z1));
        if (dd < w_hv - 1e-9){ w_hv = dd; d_hv = `${R.name} (node ${R.node}) / ${Q.name} (node ${Q.node}): ${_mm(dd)} mm`; }
      }
    });
    res["different-node leads, spheres and bus rings on one body keep the HV clearance"] = [w_hv >= need - 1e-9, `tightest ${d_hv} (>= ${_mm(need)})`];
    const fbody = {};
    for (const it of design.stack) if (it.kind === "foil") fbody[it.id] = BODY_OF[ROTOR_BODY[on[it.id]] || "stator"];
    let w_sf = Infinity, d_sf = "none";
    for (const it of sg.items){
      if (it.kind !== "sphere") continue;
      for (const f of design.stack){
        if (f.kind !== "foil" || f.node === it.node || fbody[f.id] !== BODY_OF[it.body]) continue;
        const dd = _foil_dist(it.c, f) - it.r;
        if (dd < w_sf - 1e-9){ w_sf = dd; d_sf = `${it.name} (node ${it.node}) / ${f.id} (node ${f.node}): ${_mm(dd)} mm`; }
      }
    }
    res["spheres keep the HV clearance to different-node foils of their own body"] = [w_sf >= need - 1e-9, `tightest ${d_sf} (>= ${_mm(need)})`];
    const [w_rv, d_rv] = _revolved_hv(design, sg, need, on);
    res["counter-rotating copper keeps the HV clearance (revolved, gap pairs aside)"] = [w_rv >= need - 1e-9,
      w_rv < Infinity ? `tightest ${d_rv} (>= ${_mm(need)})` : `no exposed conductor comes within ${_mm(need)} mm of the other body's copper`];
    res["leads near foils of other carriers (info: breakdown model out of scope)"] = [true, `closest ${d_oth}`];
    res["equipotential links and bus rings (info)"] = [true, Object.keys(LINKS).map(c => `${c} ${sg.items.filter(it => it.role === "link" && it.carrier === c).length} x (${LINKS[c][0]} <-> ${LINKS[c][1]})`).join(", ")
      + `; ${rings.length} bus rings, one per node per carrier; ND2 / ND3 hold node 2 / 3 and pickup n23 / n17 (Lx4 / Lx3), the rotor discs R-A / R-B and the C_R plate n18 / n00 (L_R1 / L_R2): off-model`];
    const [nr, ns, hits] = sweep_check(design, sg);
    res["counter-rotation: no rotor/stator collision"] = [!hits.length, `${nr} rotor x ${ns} stator revolved envelopes, ` +
      (hits.length ? `${hits.length} overlap(s): ${hits[0][0]} / ${hits[0][1]}` : "none overlap")];
    const cross = sg.gaps.filter(x => x.crossover);
    res["load-gap crossovers over the stator (info)"] = [true, cross.map(x => `${x.name}: node ${x.stator_node} from ${x.carrier} to ${x.host} (${x.side}), lead ${_mm(x.lead_len)} mm` +
      (x.mount === "arm" ? ` + arm ${_mm(x.arm_len)} mm` : "")).join(", ") || "none"];
    const rpm = +(inp.rpm != null ? inp.rpm : 3000.0);
    const bar = Object.values(sg.bands).filter(b => b.band === "bar"), r_out = Math.max(...bar.map(b => b.r_load));
    const acc = (2 * Math.PI * rpm / 60.0) ** 2 * r_out * 1e-3 / 9.80665;
    res["spin load on the bar-band electrodes (info)"] = [true, `up to ${_mm(acc)} g at r${_mm(r_out)} (${g6(rpm)} rpm, the full relative ` +
      "speed: an upper bound for either body): " + (bar.some(b => b.layout === "radial")
        ? "along the stem for the fire / backstop spheres (rim stems in tension) and the load spheres (arms in compression: the sphere is at the inner end), in bending for the tips on their short vertical stems"
        : "every bar-band sphere and tip stands on a vertical stem: all in bending")];
    const o = {}; for (const k of Object.keys(res)) o[k] = {pass_: !!res[k][0], detail: res[k][1]};
    return o;
  }
  /* the revolved (r, z) image of a part (1:1 with the Python): points + radius (rod, sphere) or its (r, z) box */
  function _rz_img(it){
    if (it.kind === "sphere") return [[[Math.hypot(it.c[0], it.c[1]), it.c[2]]], it.r, null];
    if (it.kind === "rod"){
      const p0 = it.p0, p1 = it.p1, n = Math.max(1, Math.ceil(dist(p0, p1) / 2.0 - 1e-9)), pts = [];
      for (let j = 0; j <= n; j++){ const q = [0, 1, 2].map(i => p0[i] + (p1[i] - p0[i]) * j / n); pts.push([Math.hypot(q[0], q[1]), q[2]]); }
      return [pts, it.r, null];
    }
    return [null, 0.0, [it.r_in, it.r_out, it.z0, it.z1]];
  }
  function _revolved_hv(design, sg, need, on){
    const elec = ["gap-stator", "gap-rotor", "gap-stem"];
    const expo = sg.items.filter(it => it.kind === "sphere" || (it.kind === "rod" && (it.role === "gap-stem" || (it.role === "gap-lead" && !it.embedded && !it.riser))));
    const other = sg.items.concat(design.stack.filter(f => f.kind === "foil").map(f => Object.assign({}, f, {name: f.id, role: "foil", band: "", body: ROTOR_BODY[on[f.id]] || "stator"})));
    const box = (pts, inf_) => [Math.min(...pts.map(p => p[0])) - inf_, Math.max(...pts.map(p => p[0])) + inf_, Math.min(...pts.map(p => p[1])) - inf_, Math.max(...pts.map(p => p[1])) + inf_];
    const img = other.map(y => { const [pts, inf_, bx] = _rz_img(y); return [pts, inf_, bx === null ? box(pts, inf_) : bx]; });
    let w = Infinity, det = "none";
    for (const x of expo){
      const [px, ix] = _rz_img(x), bx = box(px, ix);
      other.forEach((y, j) => {
        if (BODY_OF[y.body] === BODY_OF[x.body] || y.node === x.node) return;
        if (elec.includes(x.role) && elec.includes(y.role) && x.band === y.band) return;
        const [py, iy, by] = img[j];
        if (Math.max(bx[0] - by[1], by[0] - bx[1], bx[2] - by[3], by[2] - bx[3]) > need) return;
        let dd = Infinity;
        if (py === null){ for (const [r, z] of px) dd = Math.min(dd, Math.hypot(Math.max(0.0, by[0] - r, r - by[1]), Math.max(0.0, by[2] - z, z - by[3]))); dd -= ix; }
        else { for (const [r1, z1] of px) for (const [r2, z2] of py) dd = Math.min(dd, Math.hypot(r1 - r2, z1 - z2)); dd -= ix + iy; }
        if (dd < w - 1e-9){ w = dd; det = `${x.name} (node ${x.node}, ${BODY_OF[x.body]}) / ${y.name} (node ${y.node}, ${BODY_OF[y.body]}): ${_mm(dd)} mm`; }
      });
    }
    return [w, det];
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
  const CR_RATIO = 2.82;   // C_R / C_max, = pump_sizing ratio_CR [IR]

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
      res[`${cap}: inset from its counter-electrode edge by the margin`] = [e.r_out <= c.r_out - g.ca_margin + 1e-9 && e.r_in >= c.r_in + g.ca_margin - 1e-9,
        `r${f(e.r_in, 1)}-${f(e.r_out, 1)} within r${f(c.r_in, 0)}-${f(c.r_out, 0)} less ${f(g.ca_margin, 0)} mm`];
      res[`${cap}: clears the carrier bore`] = [e.r_in - g.ca_margin >= g.r_bore,
        `r_in ${f(e.r_in, 1)} - margin ${f(g.ca_margin, 0)} >= bore ${f(g.r_bore, 0)}`];
      res[`${cap}: dielectric margin fits the sector pitch`] = [
        e.w_deg + 2 * deg(g.ca_margin / Math.max(e.r_in, 1e-9)) <= 360.0 / (e.starts.length || 1),
        `foil ${f(e.w_deg, 1)} deg + 2 x ${f(g.ca_margin, 0)} mm margin at r_in`];
      res[`${cap}: realized C = locked C`] = [Math.abs(geo.dC_rel) <= 1e-9 || g.ca_round > 0,
        `${f(geo.C_pF, 3)} vs ${f(geo.C_target_pF, 3)} pF (${fs(pct(geo.dC_rel), 4)} %)` +
        (g.ca_round > 0 ? " -- rounding: engine round-trip decides" : "")];
    }
    // C_R (tank, collapsed in the engine) vs the ladder's 2.82 x C_max; 1 % tolerance [IR]
    const cr_t = CR_RATIO * design.lock.ladder.C_max;
    const cr = cap_pF(overlap_area(fp.CR_A, fp.CR_B), g.t_septum, DIELECTRICS.garolite);
    res["C_R: septum C = 2.82 x C_max (tank, shown only)"] = [Math.abs(cr / cr_t - 1) <= 0.01,
      `${f(cr, 1)} vs ${f(cr_t, 1)} pF (${fs(pct(cr / cr_t - 1), 2)} %), ${fp.CR_A.starts.length} x ${f(fp.CR_A.w_deg, 0)} deg on ${f(g.t_septum, 1)} mm garolite`];
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
  const API = { EPS0, SCHEMA, DIELECTRICS, GEOM_DEFAULTS, PAIRS, solve_transfer, build, parts, overlap_area, adjacency, checks,
    lock_record, lock_hash, canonical, selftest };
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.PumpGeometry = API;
})(typeof self !== "undefined" ? self : this);

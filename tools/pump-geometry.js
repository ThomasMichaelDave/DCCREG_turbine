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
    cx_air: 3.0, cx_mica: 0.3, r_bore: 50.0, rotor_in_off: 20.0,
    sg_rg: 345.0, sg_rret: 285.0, sg_d: 12.0, sg_dbs: 25.0, sg_s_ret: 5.5, sg_s_load: 4.75, sg_s_fire: 5.5, sg_s_bs: 5.5,
    sg_glat: 1.0, sg_clear: 5.0, sg_rod: 6.0, sg_rhub: 35.0, sg_frame: 60.0, sg_khv: 2.0 };
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
      Cx4_pickup: _fp("Cx4 pickup", "n23", "Cx4", cx_rin, cx_rout, even, w_sec),
      Cx4_bars: _fp("island bars on A", "8", "Cx4", bar_rin, cx_rout, even, w_sec),
      Cx3_pickup: _fp("Cx3 pickup", "n17", "Cx3", cx_rin, cx_rout, odd, w_sec),
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
    design.sparkgaps = sparkgaps(design);
    design.z_total = design.sparkgaps.z_max - design.sparkgaps.z_min;
    design.checks = checks(design);
    for (const k of Object.keys(design.sparkgaps.checks)) design.checks["gaps: " + k] = design.sparkgaps.checks[k];
    const [asm, prt] = parts(design);
    design.assemblies = asm; design.parts = prt;
    design.top_label = `PumpGeometry ${locked.hash != null ? locked.hash : ""} - DCCREG drawn pump, stage 2 plate geometry (Ca/Cb geometrized)`;
    return design;
  }

  /* ---- the bill of solids (1:1 with sim/pump_geometry.py parts()): the CAD builders only build this list ---- */
  const NODE_RGB = {"1": [0.49, 0.82, 1.0], "2": [1.0, 0.71, 0.33], "3": [0.27, 0.77, 0.42], "4": [0.90, 0.28, 0.30],
    "5": [0.78, 0.57, 0.92], "6": [0.97, 0.46, 0.56], "7": [0.62, 0.81, 0.42], "8": [0.88, 0.69, 0.41],
    "n17": [0.55, 0.90, 0.80], "n23": [1.0, 0.88, 0.55]};
  const MEDIUM_RGB = {garolite: [0.55, 0.50, 0.30], mica: [0.75, 0.70, 0.55]};
  const CARRIER_RGB = [0.35, 0.40, 0.47];
  const MATERIAL = {"stator": "G10 carrier", "rotor": "rotor disc", "rotor-flange": "rotor flange (insulating)"};
  const CARRIER_ROLE = {"A-flange": "rotor A outer flange, carries the island bars (node 8, floating)",
    "B-flange": "rotor B outer flange, carries the island bars (node 7, floating)",
    "A-disc": "rotor A main disc (node 5): C1 rotor face + C_R face",
    "B-disc": "rotor B main disc (node 6): C2 rotor face + C_R face",
    "ND1": "stator carrier ND1 (node 1): C1 stator plate + Ca counter-electrode",
    "ND2": "stator carrier ND2 (node 2): Ca electrode + Cx4 pickup (node n23, via Lx4)",
    "ND3": "stator carrier ND3 (node 3): Cb electrode + Cx3 pickup (node n17, via Lx3)",
    "ND4": "stator carrier ND4 (node 4): C2 stator plate + Cb counter-electrode"};
  const CARRIER_KINDS = ["rotor", "stator", "rotor-flange"];
  const node_rgb = node => { const n = String(node).split(" ")[0]; return NODE_RGB[n] || NODE_RGB[n[0]] || CARRIER_RGB; };
  const _mm = x => { let s = x.toFixed(2); if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, ""); return (s === "-0" || s === "") ? "0" : s; };
  const _m360 = x => ((x % 360.0) + 360.0) % 360.0;
  const _zr = it => `z ${_mm(it.z0)}..${_mm(it.z1)}`;
  function parts(design){
    const st = design.stack, fp = design.footprints, asm = [], out = [];
    const assembly = (key, label) => { if (!asm.some(a => a.key === key)) asm.push({key, label}); return key; };
    const carrier_of = {}, face_of = {};
    st.forEach((it, i) => {
      if (it.kind !== "foil") return;
      const nb = [i - 1, i + 1].filter(j => j >= 0 && j < st.length && CARRIER_KINDS.includes(st[j].kind)).map(j => st[j]);
      carrier_of[it.id] = nb.length ? nb[0].id : "foils";
      face_of[it.id] = (nb.length && Math.abs(it.z0) < Math.abs(nb[0].z0)) ? "septum side" : "outer side";
    });
    const P = (name, label, assembly, role, carrier, node, cap, material, r_in, r_out, start_deg, w_deg, z0, z1, rgb) =>
      out.push({name, label, assembly, role, carrier, node, cap, material, shape: "sector", chains: [carrier || assembly],
        r_in, r_out, start_deg, w_deg, z0, z1, rgb: rgb.slice(),
        volume: 0.5 * rad(Math.min(w_deg, 360.0)) * (r_out * r_out - r_in * r_in) * (z1 - z0)});
    for (const it of st){
      const kind = it.kind;
      if (CARRIER_KINDS.includes(kind)){
        const a = assembly(it.id, `${it.id} - ${CARRIER_ROLE[it.id] || kind}`);
        P(it.id.replace(/-/g, "_") + "_carrier",
          `${it.id} carrier - ${MATERIAL[kind]}, node ${it.node}, r${_mm(it.r_in)}-${_mm(it.r_out)} mm, ${_mm(it.t)} mm thick, ${_zr(it)}`,
          a, "carrier", it.id, it.node, "", MATERIAL[kind], it.r_in, it.r_out, 0.0, 360.0, it.z0, it.z1, CARRIER_RGB);
      } else if (kind === "foil"){
        const car = carrier_of[it.id];
        const a = assembly(car, `${car} - ${CARRIER_ROLE[car] || ""}`);
        const n = it.starts.length;
        it.starts.forEach((s0, k) => {
          let ang;
          if (it.w_deg >= 360.0 - 1e-9) ang = "full ring";
          else { const e = _m360(s0 + it.w_deg); ang = `sector ${k + 1} of ${n} (${_mm(_m360(s0))}-${_mm(e !== 0 ? e : 360.0)} deg)`; }
          P(`${it.key}_${k + 1}`,
            `${car} / ${it.key}_${k + 1} - ${it.name}, node ${it.node}, ${it.cap}, ${ang}, r${_mm(it.r_in)}-${_mm(it.r_out)} mm, ` +
            `Al foil ${_mm(it.z1 - it.z0)} mm, ${face_of[it.id]}, ${_zr(it)}`,
            a, "foil", car, it.node, it.cap, "Al foil", it.r_in, it.r_out, s0, it.w_deg, it.z0, it.z1, node_rgb(it.node));
        });
      } else if (kind === "gap" && MEDIUM_RGB[it.medium]){
        const a = assembly("dielectrics", "Dielectrics - septum (C_R, garolite) and the Ca/Cb mica slabs");
        if (it.footprint){
          const e = fp[it.footprint], m = it.margin || 0.0;
          const rin = Math.max(0.0, e.r_in - m), rout = e.r_out + m, dw = deg(m / Math.max(e.r_in, 1e-9)), n = e.starts.length;
          e.starts.forEach((s0, k) => {
            const w = Math.min(e.w_deg + 2 * dw, 360.0), a0 = s0 - dw;
            P(`${it.id.replace(/-/g, "_")}_${k + 1}`,
              `${it.id}_${k + 1} - ${it.medium} dielectric for ${it.cap} (between the ${it.cap} electrode and its counter), slab ${k + 1} of ${n} ` +
              `(${_mm(_m360(a0))}-${_mm(_m360(a0 + w))} deg), r${_mm(rin)}-${_mm(rout)} mm, ${_mm(it.t)} mm thick (foil + ${_mm(m)} mm margin), ${_zr(it)}`,
              a, "dielectric", "", "", it.cap, it.medium, rin, rout, a0, w, it.z0, it.z1, MEDIUM_RGB[it.medium]);
          });
        } else {
          const rin = it.r_in != null ? it.r_in : 0.0, rout = it.r_out != null ? it.r_out : design.r_edge;
          P(it.id.replace(/-/g, "_"),
            `${it.id} - ${it.medium}, ${it.cap} dielectric between rotor A and rotor B, r${_mm(rin)}-${_mm(rout)} mm, ${_mm(it.t)} mm thick, ${_zr(it)}`,
            a, "dielectric", "", "", it.cap, it.medium, rin, rout, 0.0, 360.0, it.z0, it.z1, MEDIUM_RGB[it.medium]);
        }
      }
    }
    const sgp = design.sparkgaps;
    if (sgp){
      for (const side of ["A", "B"]){
        for (const [role, lab] of [["gap-rotor", `Spark gaps deck ${side} - rotor tips and arms (rotate with rotor ${side})`],
                                   ["gap-stator", `Spark gaps deck ${side} - stator electrodes, posts and leads`]]){
          const key = `gaps-${side}-${role === "gap-rotor" ? "rotor" : "stator"}`;
          for (const it of sgp.items){
            if (it.side !== side || ((it.role === "gap-rotor") !== (role === "gap-rotor"))) continue;
            const a = assembly(key, lab);
            const base = {name: it.name, label: `${it.name} - ${it.desc}`, assembly: a, role: it.role, carrier: "", node: it.node,
              cap: it.gap, rgb: node_rgb(it.node).slice(), chains: it.chains.slice()};
            if (it.kind === "sphere")
              Object.assign(base, {shape: "sphere", material: it.r <= 6.0 + 1e-9 ? "W-Cu" : "smooth electrode", c: it.c.slice(), r: it.r,
                volume: 4.0 / 3.0 * Math.PI * it.r ** 3});
            else {
              const L = dist(it.p0, it.p1);
              Object.assign(base, {shape: "rod", material: "Cu rod", p0: it.p0.slice(), p1: it.p1.slice(), r: it.r, volume: Math.PI * it.r ** 2 * L});
            }
            out.push(base);
          }
        }
      }
    }
    return [asm, out];
  }

  /* ---- spark gaps (1:1 with sim/pump_geometry.py sparkgaps / gap_checks) ---- */
  const GAPS = [["SG1", "return", "2", "rail A (node 5)", "A", "rail", 3.00], ["SG4a1", "load", "4", "bar 8", "A", "bar", 37.20],
    ["SG4b1", "fire", "2", "bar 8", "A", "bar", 46.05], ["BS4", "backstop", "2", "bar 8", "A", "bar", 49.00],
    ["SG2", "return", "3", "rail B (node 6)", "B", "rail", 33.00], ["SG3a1", "load", "1", "bar 7", "B", "bar", 7.20],
    ["SG3b1", "fire", "3", "bar 7", "B", "bar", 16.05], ["BS3", "backstop", "3", "bar 7", "B", "bar", 19.00]];
  const NETLIST_GAPS = {SG1: ["2", "R-A"], SG2: ["3", "R-B"], SG3a1: ["1", "7"], SG3b1: ["7", "3"], BS3: ["7", "3"],
    SG4a1: ["4", "8"], SG4b1: ["8", "2"], BS4: ["8", "2"]};
  const ROTOR_NODE = {"rail A (node 5)": "R-A", "rail B (node 6)": "R-B", "bar 7": "7", "bar 8": "8"};
  const NODE_CARRIER = {"1": "ND1", "2": "ND2", "3": "ND3", "4": "ND4"};
  const SIDE_OF_CARRIER = {ND1: "A", ND2: "A", ND3: "B", ND4: "B"};
  const SPACING_KEY = {return: "sg_s_ret", load: "sg_s_load", fire: "sg_s_fire", backstop: "sg_s_bs"};
  const SPOKES = 6;
  const _pol = (r, a, z) => [r * Math.cos(rad(a)), r * Math.sin(rad(a)), z];
  const dist = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);

  function sparkgaps(design){
    const g = design.geom, st = design.stack, fp = design.footprints, byid = {};
    st.forEach(it => byid[it.id] = it);
    const zA_out = st[0].z0, zB_out = st[st.length - 1].z1;
    const Rb = Math.max(g.sg_d, g.sg_dbs) / 2, Rr = g.sg_d / 2, planes = {};
    for (const [side, zo, sgn] of [["A", zA_out, -1], ["B", zB_out, +1]]){
      const zb = zo + sgn * (g.sg_clear + Rb), zr = zb + sgn * (Rb + g.sg_clear + Rr);
      planes[side] = {bar: zb, rail: zr};
    }
    const R_frame = design.r_edge + g.sg_frame, rod = g.sg_rod / 2, gaps = [], items = [];
    const carrier_mid = cid => 0.5 * (byid[cid].z0 + byid[cid].z1);
    for (const [name, cls, snode, rot, side, track, stn] of GAPS){
      const s_ = g[SPACING_KEY[cls]], d_rot = g.sg_d, d_st = cls === "backstop" ? g.sg_dbs : g.sg_d;
      const r_track = track === "bar" ? g.sg_rg : g.sg_rret, r_st = r_track + (d_rot + d_st) / 2 + s_;
      const z = planes[side][track], car = NODE_CARRIER[snode], zc = carrier_mid(car), crossover = SIDE_OF_CARRIER[car] !== side;
      const lead_len = (R_frame - r_st) + Math.abs(z - zc) + (R_frame - design.r_edge);
      gaps.push({name, cls, stator_node: snode, rotor: rot, side, track, station: stn, spacing: s_, d_rotor: d_rot, d_stator: d_st,
        r_track, r_stator: r_st, z, carrier: car, crossover, lead_len});
      for (let k = 0; k < SPOKES; k++){
        const a = stn + 60.0 * k, ch = [`lead-${name}-${k + 1}`, car];
        items.push({kind: "sphere", name: `${name}_el_${k + 1}`, gap: name, node: snode, role: "gap-stator", c: _pol(r_st, a, z), r: d_st / 2, chains: ch, side,
          desc: `${name} stator electrode ${k + 1} of ${SPOKES} (${cls}), node ${snode}, ${_mm(d_st)} mm ${cls === "backstop" ? "smooth" : "W-Cu"} sphere at r${_mm(r_st)} ` +
                `${_mm(_m360(a))} deg, deck ${side} ${track} plane z ${_mm(z)}, gap ${_mm(s_)} mm to ${rot}`});
        items.push({kind: "rod", name: `${name}_post_${k + 1}`, gap: name, node: snode, role: "gap-lead", p0: _pol(r_st, a, z), p1: _pol(R_frame, a, z), r: rod, chains: ch, side,
          desc: `${name} post ${k + 1}: electrode to the lead frame R${_mm(R_frame)}, node ${snode}`});
        items.push({kind: "rod", name: `${name}_riser_${k + 1}`, gap: name, node: snode, role: "gap-lead", p0: _pol(R_frame, a, z), p1: _pol(R_frame, a, zc), r: rod, chains: ch, side,
          desc: `${name} lead ${k + 1} along R${_mm(R_frame)} from deck ${side} to ${car} (node ${snode})` + (crossover ? " - CROSSOVER over the stator" : "")});
        items.push({kind: "rod", name: `${name}_stub_${k + 1}`, gap: name, node: snode, role: "gap-lead", p0: _pol(R_frame, a, zc), p1: _pol(design.r_edge, a, zc), r: rod, chains: ch, side,
          desc: `${name} lead ${k + 1} into the ${car} carrier rim, node ${snode}`});
      }
    }
    for (const [side, flange, bars, disc] of [["A", "A-flange", "Cx4_bars", "A-disc"], ["B", "B-flange", "Cx3_bars", "B-disc"]]){
      const zb = planes[side].bar, zr = planes[side].rail, bar = fp[bars], bar_node = bar.node;
      const zf = 0.5 * (byid[bars].z0 + byid[bars].z1), zd = 0.5 * (byid[disc].z0 + byid[disc].z1);
      const rail_node = side === "A" ? "5" : "6";
      for (let k = 0; k < SPOKES; k++){
        const a = 60.0 * k, chb = [`bar-${side}`, flange, bars], chr = [`rail-${side}`, disc, flange];
        items.push({kind: "sphere", name: `bartip_${side}_${k + 1}`, gap: "", node: bar_node, role: "gap-rotor", c: _pol(g.sg_rg, a, zb), r: g.sg_d / 2, chains: chb, side,
          desc: `island bar ${bar_node} tip ${k + 1} of ${SPOKES} (rotor ${side}), ${_mm(g.sg_d)} mm W-Cu sphere at r${_mm(g.sg_rg)} ${_mm(a)} deg, bar plane z ${_mm(zb)}`});
        items.push({kind: "rod", name: `bararm_${side}_${k + 1}`, gap: "", node: bar_node, role: "gap-rotor", p0: _pol(g.sg_rg, a, zf), p1: _pol(g.sg_rg, a, zb), r: rod, chains: chb, side,
          desc: `island bar ${bar_node} arm ${k + 1}: through the ${flange} to its tip (rotates with rotor ${side})`});
        items.push({kind: "sphere", name: `railtip_${side}_${k + 1}`, gap: "", node: rail_node, role: "gap-rotor", c: _pol(g.sg_rret, a, zr), r: g.sg_d / 2, chains: chr, side,
          desc: `rail tip ${k + 1} of ${SPOKES} (rotor ${side}, node ${rail_node}), ${_mm(g.sg_d)} mm W-Cu sphere at r${_mm(g.sg_rret)} ${_mm(a)} deg, rail plane z ${_mm(zr)}`});
        items.push({kind: "rod", name: `railarm_${side}_${k + 1}a`, gap: "", node: rail_node, role: "gap-rotor", p0: _pol(g.sg_rhub, a, zd), p1: _pol(g.sg_rhub, a, zr), r: rod, chains: chr, side,
          desc: `rail arm ${k + 1} (node ${rail_node}): from the ${disc} through the stator bores at r${_mm(g.sg_rhub)} to the rail plane`});
        items.push({kind: "rod", name: `railarm_${side}_${k + 1}b`, gap: "", node: rail_node, role: "gap-rotor", p0: _pol(g.sg_rhub, a, zr), p1: _pol(g.sg_rret, a, zr), r: rod, chains: chr, side,
          desc: `rail arm ${k + 1} (node ${rail_node}): radial in the rail plane to its tip`});
      }
    }
    const zs = [];
    for (const it of items) if (it.kind === "sphere") zs.push(it.c[2] - it.r);
    for (const it of items) if (it.kind === "sphere") zs.push(it.c[2] + it.r);
    const out = {planes, R_frame, gaps, items, z_min: Math.min(...zs, st[0].z0), z_max: Math.max(...zs, st[st.length - 1].z1)};
    out.checks = gap_checks(design, out);
    return out;
  }

  function gap_checks(design, sg){
    const g = design.geom, fp = design.footprints, res = {};
    const smax = Math.max(g.sg_s_ret, g.sg_s_load, g.sg_s_fire, g.sg_s_bs), need = g.sg_khv * smax, rod = g.sg_rod / 2;
    const setEq = (a, b) => a.length === b.length && a.every(x => b.includes(x)) && b.every(x => a.includes(x));
    const bad = sg.gaps.filter(x => !setEq([...new Set(NETLIST_GAPS[x.name])], [...new Set([x.stator_node, ROTOR_NODE[x.rotor]])])).map(x => x.name);
    res["nodes = netlist of record (topology_edge_list.csv)"] = [!bad.length, !bad.length ? "all 8 gaps" : "mismatch: " + bad.join(", ")];
    const worst = Math.max(...sg.gaps.map(x => Math.abs((x.r_stator - x.r_track) - (x.d_rotor + x.d_stator) / 2 - x.spacing)));
    res["spacing at alignment = the freeze table"] = [worst < 1e-9, sg.gaps.map(x => `${x.name} ${_mm(x.spacing)}`).join("; ") + " mm"];
    let worst_xf = Infinity, det = "";
    for (const x of sg.gaps){
      const tip = _pol(x.r_track, x.station, x.z);
      for (const y of sg.gaps){
        if (y === x || y.side !== x.side || y.track !== x.track) continue;
        for (let k = 0; k < SPOKES; k++){
          const c = _pol(y.r_stator, y.station + 60.0 * k, y.z);
          const dd = dist(tip, c) - x.d_rotor / 2 - y.d_stator / 2;
          if (y.stator_node === x.stator_node) continue;
          const margin = dd - Math.max(x.spacing, y.spacing);
          if (margin < worst_xf - 1e-9){ worst_xf = margin; det = `${x.name} tip vs ${y.name} electrode: ${_mm(dd)} mm`; }
        }
      }
    }
    res["no cross-firing to a different-node station"] = [worst_xf >= 0.5 * Math.max(g.sg_s_load, g.sg_s_fire),
      `tightest ${det} (margin ${_mm(worst_xf)} mm over its spacing)`];
    const ov = deg((g.sg_d + 2 * g.sg_glat) / g.sg_rg);
    res["I11 cross-fire at the placed bar radius"] = [ov < 2.95, `overlap ${_mm(ov)} deg < SG3b-BS3 2.95 deg at r${_mm(g.sg_rg)}`];
    const bar = fp.Cx4_bars;
    res["bar tip radius on the island bar"] = [bar.r_in + rod <= g.sg_rg && g.sg_rg <= bar.r_out - rod,
      `r${_mm(g.sg_rg)} within the bar r${_mm(bar.r_in)}-${_mm(bar.r_out)}`];
    const cl = g.r_bore - g.sg_rhub - rod;
    res["rail arms clear the stator bores (HV)"] = [cl >= need, `${_mm(cl)} mm >= ${_mm(need)} mm (${_mm(g.sg_khv)} x ${_mm(smax)})`];
    const cl2 = Math.min(bar.r_in, fp.Cx3_bars.r_in) - g.sg_rhub - rod;
    res["rail arms clear the island bars in the flange (HV)"] = [cl2 >= need, `${_mm(cl2)} mm >= ${_mm(need)} mm`];
    const gap_rr = (g.sg_rg - g.sg_d / 2) - (g.sg_rret + g.sg_d / 2 + Math.max(g.sg_s_ret, 0));
    res["rail track well inboard of the bar track"] = [gap_rr >= need, `${_mm(gap_rr)} mm radial between the tracks`];
    const clf = sg.R_frame - rod - design.r_edge;
    res["lead frame clears the rotor rim (HV)"] = [clf >= need, `R${_mm(sg.R_frame)}: ${_mm(clf)} mm over the R${_mm(design.r_edge)} rims`];
    const st = design.stack;
    const zc = Math.min(...Object.values(sg.planes).map(p => Math.abs(p.bar))) - Math.max(Math.abs(st[0].z0), Math.abs(st[st.length - 1].z1)) - Math.max(g.sg_d, g.sg_dbs) / 2;
    res["gap planes clear the flanges"] = [zc >= g.sg_clear - 1e-9, `${_mm(zc)} mm`];
    let w2 = Infinity, d2 = "";
    for (const x of sg.gaps) for (const y of sg.gaps){
      if (x === y || x.side !== y.side || x.track !== y.track || x.stator_node === y.stator_node) continue;
      for (let k = 0; k < SPOKES; k++){
        const dd = dist(_pol(x.r_stator, x.station, x.z), _pol(y.r_stator, y.station + 60 * k, y.z)) - x.d_stator / 2 - y.d_stator / 2;
        if (dd < w2 - 1e-9){ w2 = dd; d2 = `${x.name} / ${y.name}`; }
      }
    }
    res["different-node stator electrodes keep the HV clearance"] = [w2 >= need, `tightest ${d2}: ${_mm(w2)} mm >= ${_mm(need)} mm`];
    const cr = sg.gaps.filter(x => x.crossover);
    res["load-gap crossovers over the stator (info)"] = [true, cr.map(x => `${x.name}: node ${x.stator_node} from ${x.carrier} to deck ${x.side}, lead ${_mm(x.lead_len)} mm`).join(", ") || "none"];
    const o = {}; for (const k of Object.keys(res)) o[k] = {pass_: !!res[k][0], detail: res[k][1]};
    return o;
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
  const API = { EPS0, SCHEMA, DIELECTRICS, GEOM_DEFAULTS, PAIRS, solve_transfer, build, parts, overlap_area, adjacency, checks,
    lock_record, lock_hash, canonical, selftest };
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.PumpGeometry = API;
})(typeof self !== "undefined" ? self : this);

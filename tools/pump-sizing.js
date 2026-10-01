/* tools/pump-sizing.js — the JS mirror of sim/pump_sizing.py (rotor plates -> C1/C2 -> the ladder).
 *
 * 1:1 port, line for line, so the page can show the ladder instantly while the exact engine runs.
 * Gate S1b (sim/pump_synth_gates.py) holds this file to the Python to 1e-12 on 200 random plate inputs.
 * The formulas come from index.html's Block C-I plate engine (plateGeom / plateCaps / epsAir / epsRof
 * @ 8cd181e), via pump_sizing.py; tags [OC]/[IR] as there. Works in the browser (window.PumpSizing)
 * and in Node (module.exports).
 */
(function (root) {
  "use strict";
  const EPS0 = 8.8541878128e-12;                       // F/m, CODATA 2018 [OC]
  const SW_K1 = 77.6, SW_K2 = 3.73e5;                  // Smith-Weintraub [OC]
  const BUCK_A = 6.1121, BUCK_B = 18.678, BUCK_C = 234.5, BUCK_D = 257.14;   // Buck (1981) [OC]
  const DIELECTRICS = { vacuum: 1.0, air: null, kapton: 3.4, mica: 5.4 };
  const BUS_MARGIN = 0.27;
  const C_FREEZE_PF = 279.6;
  const PLATE_DEFAULTS = { r_inMm: 95.0, r_outMm: 387.0, g_vMm: 7.0, dielectric: "air",
    tempC: 20.0, p_hPa: 1013.0, rh: 50.0, N_sec: 12, n_kept: 6,
    ring_on: true, r_ring_inMm: 25.0, r_ring_outMm: 68.2 };
  const CHOICE_DEFAULTS = { cmin_conv: "active_fringe", C_fringe_pF: 16.0,
    ratio_Ca: 1.10, ratio_Cx: 1.68, ratio_CR: 2.82, cpar_mode: "fixed", Cpar_pF: 20.0,
    cx_min_pF: 8.0, gap_stray_pF: 2.0, pCboss_pF: 6.0, island_stray_pF: 5.0,
    Lx_mH: 1.0, R_lx: 2.0, rpm: 3000.0, L_coil_H: 0.64, R_coil: 40.0, pins: {} };
  const LADDER_KEYS = ["C_max", "C_min", "Ca", "Cb", "cx_max", "cx_min", "Cpar", "gap_stray", "pCboss",
    "island_stray", "Lx_mH", "R_lx", "C_blk_nF"];
  const g6 = x => String(+x.toPrecision(6));            // Python's :g for the rule strings

  function eps_air(tempC, p_hPa, rh) {
    const tK = tempC + 273.15;
    const p_sat = BUCK_A * Math.exp((BUCK_B - tempC / BUCK_C) * (tempC / (BUCK_D + tempC)));
    const p_vap = (rh / 100.0) * p_sat;
    const N = SW_K1 * p_hPa / tK + SW_K2 * p_vap / (tK * tK);
    return 1.0 + 2.0 * N * 1e-6;
  }
  function eps_r(p) {
    if (p.dielectric === "air") return eps_air(p.tempC, p.p_hPa, p.rh);
    return DIELECTRICS[p.dielectric];
  }
  function plate_areas(p) {
    const kept = p.n_kept / p.N_sec;
    const ri = p.r_inMm * 1e-3, ro = p.r_outMm * 1e-3;
    const A_m = ro > ri ? kept * Math.PI * (ro * ro - ri * ri) : 0.0;
    const rri = p.r_ring_inMm * 1e-3, rro = p.r_ring_outMm * 1e-3;
    const A_ring = (p.ring_on && rro > rri) ? Math.PI * (rro * rro - rri * rri) : 0.0;
    return [A_m, A_ring];
  }
  function rotor_caps(p, conv, C_fringe_pF) {
    conv = conv || "active_fringe"; if (C_fringe_pF == null) C_fringe_pF = 16.0;
    const [A_m, A_ring] = plate_areas(p);
    const g = p.g_vMm * 1e-3;
    const k = EPS0 * eps_r(p) / g * 1e12;
    let cmax, cmin;
    if (conv === "ring") { cmax = k * (A_m + A_ring); cmin = k * A_ring; }
    else if (conv === "active_fringe") { cmax = k * A_m; cmin = C_fringe_pF; }
    else throw new Error(conv);
    return [cmax, cmin, cmin > 0 ? cmax / cmin : Infinity];
  }
  function c_blk_nF(rpm, L_coil_H, groups) {
    const prf = groups * rpm / 60.0;
    return [1e9 / ((2.0 * Math.PI * prf) ** 2 * L_coil_H), prf];
  }
  function size(plates, choices) {
    const p = Object.assign({}, PLATE_DEFAULTS, plates || {});
    const c = Object.assign({}, CHOICE_DEFAULTS, choices || {});
    const pins = Object.assign({}, c.pins || {});
    for (const k in pins) if (LADDER_KEYS.indexOf(k) < 0) throw new Error("cannot pin " + k);
    const [cmax, cmin] = rotor_caps(p, c.cmin_conv, c.C_fringe_pF);
    const [cmax_r, cmin_r] = rotor_caps(p, "ring");
    const [cmax_a] = rotor_caps(p, "active_fringe", c.C_fringe_pF);
    const groups = Math.ceil(p.N_sec / 2);
    const [cblk, prf] = c_blk_nF(c.rpm, c.L_coil_H, groups);
    const scale = c.cpar_mode === "scaled" ? cmax / C_FREEZE_PF : 1.0;
    const raw = {
      C_max: [cmax, "forward law Eq. (5)", "[OC] law; D-CMIN convention"],
      C_min: [cmin, c.cmin_conv === "ring" ? "Eq. (6)" : "fixed fringe floor", "[IR] D-CMIN"],
      Ca: [c.ratio_Ca * cmax, `${g6(c.ratio_Ca)} x C_max (index.html cascadeState)`, "[IR] D-CA"],
      Cb: [c.ratio_Ca * cmax, "= Ca", "[IR] D-CA"],
      cx_max: [c.ratio_Cx * cmax, `${g6(c.ratio_Cx)} x C_max (tank dump match)`, "[IR] D-CX"],
      cx_min: [c.cx_min_pF * scale, "island collapsed value (island_charging_cosim.CX_MIN)", "[IR]"],
      Cpar: [c.Cpar_pF * scale, scale === 1.0 ? "fixed floor on nodes 1-4 (I6)" : "floor scaled with C_max", "[IR] D-CPAR"],
      gap_stray: [c.gap_stray_pF * scale, "per-gap stray (shuttle default)", "[IR] D-CPAR"],
      pCboss: [c.pCboss_pF * scale, "boss stray in parallel with Cx", "[IR] D-CPAR"],
      island_stray: [c.island_stray_pF * scale, "7/8/n17/n23 -> reference (r0.2 lock)", "[IR] D-CPAR"],
      Lx_mH: [c.Lx_mH, "series island inductor (0 = direct island)", "[IR]"],
      R_lx: [c.R_lx, "Lx ESR (integrator design point)", "[IR]"],
      C_blk_nF: [cblk, `1/((2 pi ${prf.toFixed(0)} Hz)^2 x ${g6(c.L_coil_H)} H)`, "[OC] law"],
    };
    const lad = {};
    for (const k of Object.keys(raw)) {
      const [v, rule, tag] = raw[k];
      const pv = pins[k];
      const val = pv != null ? +pv : +v;
      const unit = k === "Lx_mH" ? "mH" : k === "R_lx" ? "ohm" : k === "C_blk_nF" ? "nF" : "pF";
      const ratio = (unit === "pF" && cmax > 0) ? val / cmax : ((unit === "nF" && cmax > 0) ? val * 1e3 / cmax : null);
      lad[k] = { value: val, unit, ratio, rule, tag, pinned: pv != null, ladder_value: +v };
    }
    const r_rot = p.r_outMm * (1.0 + BUS_MARGIN);
    const rim = 2.0 * Math.PI * c.rpm / 60.0 * r_rot * 1e-3;
    const [A_m, A_ring] = plate_areas(p);
    const ch = Object.assign({}, c); delete ch.pins;
    return { plates: p, choices: ch, pins, ladder: lad,
      kappa_C: lad.C_min.value > 0 ? lad.C_max.value / lad.C_min.value : null,
      conventions: { active_fringe: { C_max: cmax_a, C_min: c.C_fringe_pF }, ring: { C_max: cmax_r, C_min: cmin_r } },
      eps_r: eps_r(p), A_m, A_ring, PRF_branch: prf, groups,
      C_R_pF: c.ratio_CR * cmax, rotor_dia_mm: 2.0 * r_rot, rotor_outMm: r_rot, rim_mps: rim };
  }
  function selftest() {
    const p = Object.assign({}, PLATE_DEFAULTS, { dielectric: "vacuum" });
    const [a] = rotor_caps(p, "active_fringe");
    const [r, rmin] = rotor_caps(p, "ring");
    const [, A_ring] = plate_areas(p);
    const [cb, prf] = c_blk_nF(3000, 0.64, 6);
    const rows = [
      ["S1", "C_max active-only, vacuum, freeze geometry", 279.6, a, Math.abs(a - 279.6) < 0.05],
      ["S1", "C_max with the ring term (A_ring 0.01265 m²)", 295.6, r, Math.abs(r - 295.6) < 0.06 && Math.abs(A_ring - 0.01265) < 2e-6],
      ["A.10", "dry-air ε_r at 0 °C, 1013 hPa", 1.000576, eps_air(0, 1013, 0), Math.abs(eps_air(0, 1013, 0) - 1.000576) < 2e-6],
      ["S3", "C_blk at 300 Hz, 0.64 H (nF, ±0.5 %)", 440, cb, Math.abs(prf - 300) < 1e-12 && Math.abs(cb - 440) / 440 < 5e-3],
      ["H-GEOM", "rotor diameter at r_out 387 (mm)", 983, size().rotor_dia_mm, Math.abs(size().rotor_dia_mm - 982.98) < 0.01],
    ];
    return { pass: rows.every(x => x[4]), rows };
  }
  const API = { EPS0, BUS_MARGIN, C_FREEZE_PF, DIELECTRICS, PLATE_DEFAULTS, CHOICE_DEFAULTS, LADDER_KEYS,
    eps_air, eps_r, plate_areas, rotor_caps, c_blk_nF, size, selftest };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else root.PumpSizing = API;
})(typeof self !== "undefined" ? self : this);

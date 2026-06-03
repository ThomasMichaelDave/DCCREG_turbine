import React, { useState, useMemo } from "react";

// ---- palette ----
const C = {
  paper: "#FBF6EC",
  ink: "#2A2017",
  inkSoft: "#6E5E4C",
  line: "#D8C7AC",
  cake: "#E7B988",
  cakeEdge: "#C98C4F",
  empty: "#EFE5D2",
  emptyEdge: "#CDBFA4",
  accent: "#B5462E",
  accentSoft: "rgba(181,70,46,0.22)",
};

// polar point, angle measured from top, clockwise
function polar(cx, cy, r, deg) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}
function sectorPath(cx, cy, r, a0, a1) {
  const p0 = polar(cx, cy, r, a0);
  const p1 = polar(cx, cy, r, a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M ${cx} ${cy} L ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${p1.x.toFixed(2)} ${p1.y.toFixed(2)} Z`;
}
function circlePath(cx, cy, r) {
  return `M ${cx - r} ${cy} a ${r} ${r} 0 1 0 ${2 * r} 0 a ${r} ${r} 0 1 0 ${-2 * r} 0`;
}

function NumberField({ label, value, setValue, min = 0, step = 0.5, suffix }) {
  return (
    <label style={{ display: "block", marginBottom: 14 }}>
      <span style={{ fontSize: 12, letterSpacing: "0.06em", textTransform: "uppercase", color: C.inkSoft }}>
        {label}
      </span>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          marginTop: 6,
          border: `1px solid ${C.line}`,
          borderRadius: 10,
          background: C.paper,
          overflow: "hidden",
        }}
      >
        <input
          type="number"
          value={value}
          min={min}
          step={step}
          onChange={(e) => setValue(e.target.value === "" ? "" : Number(e.target.value))}
          style={{
            width: "100%",
            border: "none",
            outline: "none",
            background: "transparent",
            padding: "10px 12px",
            fontSize: 18,
            color: C.ink,
            fontFamily: "'Fraunces', serif",
          }}
        />
        {suffix && (
          <span style={{ padding: "0 12px", color: C.inkSoft, fontSize: 13 }}>{suffix}</span>
        )}
      </div>
    </label>
  );
}

export default function SectoredDiscCalculator() {
  const [n, setN] = useState(12);
  const [outerDia, setOuterDia] = useState(24);
  const [ringOuter, setRingOuter] = useState(12);
  const [ringInner, setRingInner] = useState(5);
  const [subtractOverlap, setSubtractOverlap] = useState(false);
  const [unit, setUnit] = useState("cm");

  const m = useMemo(() => {
    const OD = Number(outerDia) || 0;
    const D = Number(ringOuter) || 0;
    const d = Number(ringInner) || 0;
    const sectors = Math.max(2, Math.round(Number(n) || 2));
    const R = OD / 2;
    const discArea = Math.PI * R * R;
    const keptCount = Math.ceil(sectors / 2); // alternating: even-indexed sectors kept
    const keptArea = (keptCount / sectors) * discArea;
    const ringArea = Math.PI * ((D / 2) ** 2 - (d / 2) ** 2);
    const overlapArea = (keptCount / sectors) * ringArea;
    const total = keptArea + ringArea - (subtractOverlap ? overlapArea : 0);
    return {
      OD, D, d, sectors, R, discArea, keptCount, keptArea,
      ringArea, overlapArea, total,
      ringInvalid: d >= D,
      ringTooBig: D > OD && OD > 0,
    };
  }, [n, outerDia, ringOuter, ringInner, subtractOverlap]);

  // ---- svg geometry ----
  const SIZE = 360, CX = 180, CY = 180, USABLE = 158;
  const scale = m.OD > 0 ? USABLE / (m.OD / 2) : 0;
  const pxR = (m.R || 0) * scale;
  const pxRo = (m.D / 2) * scale;
  const pxRi = (m.d / 2) * scale;
  const step = 360 / m.sectors;

  const sectorEls = [];
  for (let i = 0; i < m.sectors; i++) {
    const kept = i % 2 === 0;
    sectorEls.push(
      <path
        key={i}
        d={sectorPath(CX, CY, pxR, i * step, (i + 1) * step)}
        fill={kept ? C.cake : C.empty}
        stroke={kept ? C.cakeEdge : C.emptyEdge}
        strokeWidth={kept ? 1 : 0.75}
        strokeDasharray={kept ? "0" : "3 3"}
        opacity={kept ? 1 : 0.55}
      />
    );
  }

  const u2 = `${unit}²`;
  const fmt = (x) => (isFinite(x) ? x.toFixed(1) : "—");

  const Row = ({ label, value, strong, color }) => (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        padding: "9px 0",
        borderBottom: `1px solid ${C.line}`,
      }}
    >
      <span style={{ color: C.inkSoft, fontSize: 14 }}>{label}</span>
      <span
        style={{
          fontFamily: "'Fraunces', serif",
          fontSize: strong ? 22 : 16,
          color: color || C.ink,
          fontWeight: strong ? 600 : 500,
        }}
      >
        {value}
      </span>
    </div>
  );

  return (
    <div
      style={{
        minHeight: "100%",
        background: `radial-gradient(circle at 20% 0%, #FBF6EC, ${"#EFE3CE"})`,
        color: C.ink,
        padding: "28px 20px 40px",
        fontFamily: "'Spline Sans', system-ui, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..600&family=Spline+Sans:wght@300;400;500;600&display=swap');
        input[type=range]{ -webkit-appearance:none; appearance:none; height:4px; border-radius:99px; background:${C.line}; outline:none; }
        input[type=range]::-webkit-slider-thumb{ -webkit-appearance:none; appearance:none; width:20px; height:20px; border-radius:50%; background:${C.accent}; border:3px solid ${C.paper}; box-shadow:0 1px 4px rgba(0,0,0,.2); cursor:pointer; }
        input[type=range]::-moz-range-thumb{ width:20px; height:20px; border-radius:50%; background:${C.accent}; border:3px solid ${C.paper}; cursor:pointer; }
        input[type=number]::-webkit-outer-spin-button,input[type=number]::-webkit-inner-spin-button{ -webkit-appearance:none; margin:0; }
      `}</style>

      <div style={{ maxWidth: 920, margin: "0 auto" }}>
        <div style={{ marginBottom: 22 }}>
          <div style={{ fontSize: 12, letterSpacing: "0.22em", textTransform: "uppercase", color: C.accent }}>
            Parametric Geometry
          </div>
          <h1
            style={{
              fontFamily: "'Fraunces', serif",
              fontSize: 38,
              lineHeight: 1.05,
              margin: "6px 0 4px",
              fontWeight: 600,
            }}
          >
            Sectored Disc <span style={{ fontStyle: "italic", color: C.accent }}>+ Ring</span> Area
          </h1>
          <p style={{ color: C.inkSoft, fontSize: 15, margin: 0 }}>
            Slice a round disc into sectors, leave out half, then add a central ring. Live total below.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(260px,1fr) 1.1fr", gap: 22 }} className="grid-wrap">
          <style>{`@media (max-width:680px){ .grid-wrap{ grid-template-columns:1fr !important; } }`}</style>

          {/* ---- controls ---- */}
          <div
            style={{
              background: C.paper,
              borderRadius: 16,
              padding: 20,
              border: `1px solid ${C.line}`,
              boxShadow: "0 10px 30px -18px rgba(60,40,20,0.45)",
            }}
          >
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <span style={{ fontSize: 12, letterSpacing: "0.06em", textTransform: "uppercase", color: C.inkSoft }}>
                  Number of sectors
                </span>
                <span style={{ fontFamily: "'Fraunces', serif", fontSize: 22, color: C.accent }}>{m.sectors}</span>
              </div>
              <input
                type="range"
                min={2}
                max={24}
                step={1}
                value={m.sectors}
                onChange={(e) => setN(Number(e.target.value))}
                style={{ width: "100%", marginTop: 12 }}
              />
              <div style={{ fontSize: 12, color: C.inkSoft, marginTop: 6 }}>
                Keeping {m.keptCount} of {m.sectors} (alternating)
              </div>
            </div>

            <NumberField label="Outer diameter (disc)" value={outerDia} setValue={setOuterDia} suffix={unit} />
            <NumberField label="Ring — outer diameter (D)" value={ringOuter} setValue={setRingOuter} suffix={unit} />
            <NumberField label="Ring — inner diameter (d)" value={ringInner} setValue={setRingInner} suffix={unit} />

            <label style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 4, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={subtractOverlap}
                onChange={(e) => setSubtractOverlap(e.target.checked)}
                style={{ width: 17, height: 17, accentColor: C.accent }}
              />
              <span style={{ fontSize: 13.5, color: C.inkSoft }}>
                Subtract ring overlap with kept sectors
              </span>
            </label>

            <div style={{ display: "flex", gap: 8, marginTop: 18 }}>
              {["cm", "in"].map((u) => (
                <button
                  key={u}
                  onClick={() => setUnit(u)}
                  style={{
                    flex: 1,
                    padding: "8px 0",
                    borderRadius: 9,
                    border: `1px solid ${unit === u ? C.accent : C.line}`,
                    background: unit === u ? C.accent : "transparent",
                    color: unit === u ? C.paper : C.inkSoft,
                    fontSize: 13,
                    cursor: "pointer",
                    fontFamily: "inherit",
                  }}
                >
                  {u}
                </button>
              ))}
            </div>
          </div>

          {/* ---- visual + results ---- */}
          <div>
            <div
              style={{
                background: C.paper,
                borderRadius: 16,
                border: `1px solid ${C.line}`,
                padding: 14,
                display: "flex",
                justifyContent: "center",
                boxShadow: "0 10px 30px -18px rgba(60,40,20,0.45)",
              }}
            >
              <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width="100%" style={{ maxWidth: 320 }}>
                <circle cx={CX} cy={CY} r={pxR + 6} fill="none" stroke={C.line} strokeWidth="1" strokeDasharray="2 4" />
                {sectorEls}
                {m.D > 0 && m.D > m.d && (
                  <path
                    d={`${circlePath(CX, CY, pxRo)} ${circlePath(CX, CY, pxRi)}`}
                    fillRule="evenodd"
                    fill={C.accentSoft}
                    stroke={C.accent}
                    strokeWidth="1.5"
                  />
                )}
                <circle cx={CX} cy={CY} r={2.5} fill={C.ink} />
              </svg>
            </div>

            <div style={{ display: "flex", gap: 14, fontSize: 12, color: C.inkSoft, margin: "10px 2px 18px" }}>
              <span><span style={{ display: "inline-block", width: 10, height: 10, background: C.cake, borderRadius: 2, marginRight: 5 }} />kept sectors</span>
              <span><span style={{ display: "inline-block", width: 10, height: 10, background: C.empty, border: `1px dashed ${C.emptyEdge}`, borderRadius: 2, marginRight: 5 }} />left out</span>
              <span><span style={{ display: "inline-block", width: 10, height: 10, background: C.accentSoft, border: `1px solid ${C.accent}`, borderRadius: 2, marginRight: 5 }} />ring</span>
            </div>

            <div
              style={{
                background: C.paper,
                borderRadius: 16,
                border: `1px solid ${C.line}`,
                padding: "8px 18px 16px",
                boxShadow: "0 10px 30px -18px rgba(60,40,20,0.45)",
              }}
            >
              <Row label={`Full disc area  (π·r²)`} value={`${fmt(m.discArea)} ${u2}`} />
              <Row label={`Kept sectors  (${m.keptCount}/${m.sectors})`} value={`${fmt(m.keptArea)} ${u2}`} />
              <Row label="Ring area  (annulus)" value={`${fmt(m.ringArea)} ${u2}`} color={C.accent} />
              {subtractOverlap && (
                <Row label="− Overlap removed" value={`${fmt(m.overlapArea)} ${u2}`} color={C.inkSoft} />
              )}
              <div style={{ height: 4 }} />
              <Row label="Total area" value={`${fmt(m.total)} ${u2}`} strong color={C.accent} />
            </div>

            {(m.ringInvalid || m.ringTooBig) && (
              <div style={{ marginTop: 12, fontSize: 13, color: C.accent }}>
                {m.ringInvalid && <div>⚠ Ring inner diameter (d) must be smaller than outer (D).</div>}
                {m.ringTooBig && <div>⚠ Ring is wider than the disc — it extends past the cake.</div>}
              </div>
            )}
          </div>
        </div>

        <p style={{ fontSize: 12.5, color: C.inkSoft, marginTop: 22, lineHeight: 1.5 }}>
          Formula: kept sectors = (kept ÷ total) · π·r² with r = disc radius;
          ring = (π/4)·(D² − d²). Overlap option subtracts the fraction of the ring
          sitting over kept sectors, assuming a centered ring that fits within the disc.
        </p>
      </div>
    </div>
  );
}

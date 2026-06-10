/* ============================================================================
   anim-shared.jsx — tokens, palette, and reusable primitives for the
   descent–ascent animation. Exports to window.
   ============================================================================ */
const VT = {
  blue: "#1DA1F2",
  blueDeep: "#0C7ABF",
  blueSoft: "rgba(29,161,242,0.12)",
  ink: "#0F1419",
  neutral: "#536471",
  surface: "#F7F9F9",
  surface2: "#EEF3F5",
  border: "#E1E8EC",
  borderStrong: "#CFD9DE",
  success: "#00BA7C",
  amber: "#F5A623",
  amberSoft: "rgba(245,166,35,0.14)",
  white: "#FFFFFF",
  font: "Inter, system-ui, -apple-system, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace",
};

const lerp = (a, b, t) => a + (b - a) * t;
const lr = (a, b, t) => Math.round(lerp(a, b, t));
// slate -> blue by score 60..95
function scoreCol(score) {
  const t = clamp((score - 60) / 35, 0, 1);
  return `rgb(${lr(83, 29, t)}, ${lr(100, 161, t)}, ${lr(113, 242, t)})`;
}

// Working entities (abstract collège-like rows), drives table/vector/value
const VDATA = [
  { id: "JM", score: 71 }, { id: "HP", score: 88 }, { id: "VH", score: 84 },
  { id: "VC", score: 91 }, { id: "AC", score: 63 }, { id: "DD", score: 86 },
  { id: "RR", score: 80 }, { id: "CV", score: 93 },
];
const VCORE = 81.8;

/* ---------- Cell: rounded data unit ---------- */
function Cell({ x, y, size = 56, label, color = VT.white, fg = VT.ink, border = VT.border, radius = 13, opacity = 1, scale = 1, shadow = false, mono = true, fontSize, rot = 0 }) {
  return (
    <div style={{
      position: "absolute", left: x, top: y, width: size, height: size,
      borderRadius: radius, background: color, border: `1.5px solid ${border}`,
      display: "flex", alignItems: "center", justifyContent: "center",
      color: fg, fontFamily: mono ? VT.mono : VT.font, fontWeight: 700,
      fontSize: fontSize || size * 0.3, letterSpacing: "-0.02em",
      opacity, transform: `translate(-50%,-50%) scale(${scale}) rotate(${rot}deg)`,
      boxShadow: shadow ? "0 10px 30px rgba(15,20,25,0.12)" : "none",
      willChange: "transform, opacity",
    }}>{label}</div>
  );
}

/* ---------- Edge: connecting line between two points ---------- */
function Edge({ x1, y1, x2, y2, color = VT.borderStrong, width = 2, opacity = 1, dash }) {
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  const ang = Math.atan2(dy, dx) * 180 / Math.PI;
  return (
    <div style={{
      position: "absolute", left: x1, top: y1, width: len, height: width,
      background: dash ? "none" : color,
      borderTop: dash ? `${width}px dashed ${color}` : "none",
      transformOrigin: "0 50%", transform: `rotate(${ang}deg)`,
      opacity, willChange: "opacity",
    }} />
  );
}

/* ---------- Caption block (bottom) ---------- */
function Caption({ kicker, text, accent = VT.blue, x = 960, y = 936, width = 1200 }) {
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: "translateX(-50%)", width, textAlign: "center" }}>
      {kicker && <div style={{ fontFamily: VT.mono, fontSize: 18, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: accent, marginBottom: 10 }}>{kicker}</div>}
      <div style={{ fontFamily: VT.font, fontSize: 30, fontWeight: 600, color: VT.ink, lineHeight: 1.3, textWrap: "balance" }}>{text}</div>
    </div>
  );
}

/* ---------- Trade chip: "reduce X → gain Y" ---------- */
function TradeChip({ reduce, gain, x = 960, y = 836 }) {
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: "translateX(-50%)", display: "flex", alignItems: "center", gap: 14 }}>
      <span style={{ fontFamily: VT.font, fontSize: 22, fontWeight: 600, color: VT.neutral, background: VT.surface2, padding: "9px 18px", borderRadius: 999, whiteSpace: "nowrap" }}>− {reduce}</span>
      <svg width="34" height="20" viewBox="0 0 34 20" fill="none"><path d="M2 10h28M24 4l7 6-7 6" stroke={VT.blue} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
      <span style={{ fontFamily: VT.font, fontSize: 22, fontWeight: 700, color: VT.blue, background: VT.blueSoft, padding: "9px 18px", borderRadius: 999, whiteSpace: "nowrap" }}>+ {gain}</span>
    </div>
  );
}

Object.assign(window, { VT, VDATA, VCORE, lerp, lr, scoreCol, Cell, Edge, Caption, TradeChip });

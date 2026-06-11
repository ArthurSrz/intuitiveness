/* ============================================================================
   anim-levels.jsx — the granularity-level visuals (L4 → L0 and the ascent),
   built from the shared primitives. Each reads useSprite() for internal motion.
   Centered on the stage (cx, cy). Exports to window.
   ============================================================================ */
const VCX = 960, VCY = 452;

/* Reveal wrapper — fades/scales a group in on entry, out on exit. */
function Reveal({ inDur = 0.45, outDur = 0.4, from = "up", children }) {
  const { localTime, duration } = useSprite();
  const outStart = Math.max(0, duration - outDur);
  let opacity = 1, ty = 0, scale = 1;
  if (localTime < inDur) {
    const t = Easing.easeOutCubic(clamp(localTime / inDur, 0, 1));
    opacity = t; ty = (1 - t) * (from === "up" ? 26 : -26); scale = 0.97 + 0.03 * t;
  } else if (localTime > outStart) {
    const t = Easing.easeInCubic(clamp((localTime - outStart) / outDur, 0, 1));
    opacity = 1 - t; scale = 1 - 0.05 * t; ty = -t * 18;
  }
  return <div style={{ position: "absolute", inset: 0, opacity, transform: `translateY(${ty}px) scale(${scale})`, transformOrigin: "center", willChange: "transform, opacity" }}>{children}</div>;
}

const stag = (localTime, i, step = 0.05, dur = 0.4) => {
  const p = clamp((localTime - i * step) / dur, 0, 1);
  return { p, e: Easing.easeOutBack(p) };
};

/* ============================ L4 — two unlinked tables ==================== */
function L4Vis() {
  const { localTime } = useSprite();
  const grid = (cx, accent, soft, name, seed) => {
    const cells = [];
    for (let i = 0; i < 9; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const gx = cx + (col - 1) * 70, gy = VCY + (row - 1) * 70 - 4;
      const { p, e } = stag(localTime, i + seed, 0.04, 0.36);
      const filled = i === 0 || i === 4 || i === 8;
      cells.push(
        <Cell key={i} x={gx} y={gy} size={60}
          label={[1, 3, 5, 7].includes(i) ? String(60 + ((i * 7 + seed) % 35)) : ""}
          color={filled ? soft : VT.white} border={filled ? accent : VT.border}
          fg={accent} opacity={p} scale={0.5 + 0.5 * e} fontSize={17} />
      );
    }
    const titleP = clamp((localTime - 0.05) / 0.4, 0, 1);
    return (
      <React.Fragment>
        <div style={{ position: "absolute", left: cx, top: VCY - 150, transform: "translateX(-50%)", opacity: titleP, fontFamily: VT.mono, fontSize: 18, fontWeight: 700, color: accent, letterSpacing: "0.02em" }}>{name}</div>
        {cells}
      </React.Fragment>
    );
  };
  return (
    <Reveal>
      {grid(VCX - 240, VT.blue, VT.blueSoft, "source_A.csv", 0)}
      {grid(VCX + 240, VT.amber, VT.amberSoft, "source_B.csv", 5)}
      {/* the gap between them — unlinkable */}
      <div style={{ position: "absolute", left: VCX, top: VCY, transform: "translate(-50%,-50%)", width: 2, height: 220, background: "repeating-linear-gradient(180deg, " + VT.borderStrong + " 0 6px, transparent 6px 14px)", opacity: clamp((localTime - 0.4) / 0.5, 0, 1) }} />
    </Reveal>
  );
}

/* ============================ L3 — linked graph ========================== */
function L3Vis() {
  const { localTime } = useSprite();
  const R = 168;
  const nodes = VDATA.map((d, i) => {
    const a = (-90 + i * 45) * Math.PI / 180;
    return { ...d, x: VCX + Math.cos(a) * R, y: VCY + Math.sin(a) * R * 0.92 };
  });
  const edges = [];
  for (let i = 0; i < nodes.length; i++) edges.push([i, (i + 1) % nodes.length]);
  edges.push([0, 4], [2, 6], [1, 5]);
  return (
    <Reveal>
      {edges.map(([a, b], i) => {
        const p = clamp((localTime - 0.25 - i * 0.04) / 0.5, 0, 1);
        const n1 = nodes[a], n2 = nodes[b];
        const ex = lerp(n1.x, n2.x, p), ey = lerp(n1.y, n2.y, p);
        return <Edge key={i} x1={n1.x} y1={n1.y} x2={ex} y2={ey} color={VT.borderStrong} width={2} opacity={0.85} />;
      })}
      {nodes.map((n, i) => {
        const { p, e } = stag(localTime, i, 0.045, 0.36);
        const col = scoreCol(n.score);
        return <Cell key={n.id} x={n.x} y={n.y} size={62} radius={999} label={n.id} color={col} fg="#fff" border="#fff" opacity={p} scale={0.4 + 0.6 * e} fontSize={20} shadow />;
      })}
    </Reveal>
  );
}

/* ============================ L2 — single table ========================== */
function L2Vis({ ascent = false }) {
  const { localTime } = useSprite();
  if (ascent) {
    // categorized: above / below median
    const med = 84;
    const groups = [
      { name: "Above median", rows: VDATA.filter((d) => d.score >= med), accent: VT.blue, soft: VT.blueSoft },
      { name: "Below median", rows: VDATA.filter((d) => d.score < med), accent: VT.neutral, soft: VT.surface2 },
    ];
    return (
      <Reveal>
        <div style={{ position: "absolute", left: VCX, top: VCY, transform: "translate(-50%,-50%)", display: "flex", gap: 26 }}>
          {groups.map((g, gi) => (
            <div key={g.name} style={{ width: 300, background: VT.white, border: `1.5px solid ${VT.border}`, borderRadius: 18, padding: 18, boxShadow: "0 12px 34px rgba(15,20,25,0.08)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <span style={{ width: 10, height: 10, borderRadius: 99, background: g.accent }} />
                <span style={{ fontFamily: VT.font, fontWeight: 700, fontSize: 19, color: VT.ink }}>{g.name}</span>
                <span style={{ marginLeft: "auto", fontFamily: VT.mono, fontWeight: 700, color: VT.neutral }}>{g.rows.length}</span>
              </div>
              {g.rows.map((d, i) => {
                const p = clamp((localTime - 0.2 - (gi * 4 + i) * 0.05) / 0.4, 0, 1);
                return (
                  <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "7px 0", opacity: p, transform: `translateX(${(1 - p) * 12}px)` }}>
                    <span style={{ width: 36, height: 36, borderRadius: 99, background: scoreCol(d.score), color: "#fff", fontFamily: VT.mono, fontWeight: 700, fontSize: 13, display: "flex", alignItems: "center", justifyContent: "center" }}>{d.id}</span>
                    <div style={{ flex: 1, height: 8, background: VT.surface2, borderRadius: 99, overflow: "hidden" }}><div style={{ width: `${(d.score - 55) / 40 * 100}%`, height: "100%", background: scoreCol(d.score) }} /></div>
                    <span style={{ fontFamily: VT.mono, fontWeight: 700, color: scoreCol(d.score), width: 30, textAlign: "right" }}>{d.score}</span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </Reveal>
    );
  }
  // descent: one neat table
  const cols = ["entity", "score", "rank"];
  return (
    <Reveal>
      <div style={{ position: "absolute", left: VCX, top: VCY, transform: "translate(-50%,-50%)", width: 460, background: VT.white, border: `1.5px solid ${VT.border}`, borderRadius: 18, overflow: "hidden", boxShadow: "0 14px 38px rgba(15,20,25,0.10)" }}>
        <div style={{ display: "flex", padding: "12px 18px", background: VT.surface, borderBottom: `1.5px solid ${VT.border}` }}>
          {cols.map((c, i) => <span key={c} style={{ flex: i === 0 ? 1.4 : 1, fontFamily: VT.mono, fontSize: 14, fontWeight: 700, color: VT.neutral, textAlign: i ? "right" : "left" }}>{c}</span>)}
        </div>
        {VDATA.map((d, i) => {
          const p = clamp((localTime - 0.2 - i * 0.05) / 0.4, 0, 1);
          return (
            <div key={d.id} style={{ display: "flex", alignItems: "center", padding: "11px 18px", borderBottom: i < VDATA.length - 1 ? `1px solid ${VT.border}` : "none", opacity: p, transform: `translateX(${(1 - p) * 14}px)` }}>
              <span style={{ flex: 1.4, display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 30, height: 30, borderRadius: 99, background: scoreCol(d.score), color: "#fff", fontFamily: VT.mono, fontWeight: 700, fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>{d.id}</span>
              </span>
              <span style={{ flex: 1, textAlign: "right", fontFamily: VT.mono, fontWeight: 700, fontSize: 17, color: scoreCol(d.score) }}>{d.score}</span>
              <span style={{ flex: 1, textAlign: "right", fontFamily: VT.mono, fontSize: 15, color: VT.neutral }}>#{i + 1}</span>
            </div>
          );
        })}
      </div>
    </Reveal>
  );
}

/* ============================ L1 — feature vector ======================== */
function L1Vis({ ascent = false }) {
  const { localTime } = useSprite();
  const med = 84;
  return (
    <Reveal>
      <div style={{ position: "absolute", left: VCX, top: VCY + 30, transform: "translate(-50%,-50%)", display: "flex", alignItems: "flex-end", gap: 16 }}>
        {VDATA.map((d, i) => {
          const p = clamp((localTime - 0.2 - i * 0.06) / 0.5, 0, 1);
          const h = (d.score - 55) / 40 * 210 + 24;
          const dim = ascent && d.score < med;
          return (
            <div key={d.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, opacity: dim ? 0.32 : 1 }}>
              <div style={{ height: 234, display: "flex", alignItems: "flex-end" }}>
                <div style={{ width: 50, height: h * Easing.easeOutCubic(p), borderRadius: 10, background: scoreCol(d.score) }} />
              </div>
              <span style={{ fontFamily: VT.mono, fontWeight: 700, fontSize: 18, color: scoreCol(d.score), opacity: p }}>{d.score}</span>
              <span style={{ fontFamily: VT.mono, fontSize: 13, color: VT.neutral, opacity: p }}>{d.id}</span>
            </div>
          );
        })}
      </div>
      {ascent && (
        <div style={{ position: "absolute", left: VCX, top: VCY + 170, transform: "translateX(-50%)", opacity: clamp((localTime - 0.7) / 0.5, 0, 1), display: "flex", alignItems: "center", gap: 10, fontFamily: VT.font, fontWeight: 600, color: VT.blue }}>
          <span style={{ background: VT.blueSoft, padding: "7px 16px", borderRadius: 999, fontFamily: VT.mono, fontWeight: 700 }}>median {med}</span>
          <span style={{ color: VT.neutral }}>split the vector by your question</span>
        </div>
      )}
    </Reveal>
  );
}

/* ============================ L0 — core datum =========================== */
function L0Vis() {
  const { localTime } = useSprite();
  const p = clamp(localTime / 0.6, 0, 1);
  const e = Easing.easeOutBack(p);
  const glow = 0.5 + 0.5 * Math.sin(localTime * 2.2);
  // count up
  const shown = (VCORE * Easing.easeOutCubic(clamp(localTime / 0.9, 0, 1))).toFixed(1);
  return (
    <div style={{ position: "absolute", left: VCX, top: VCY, transform: `translate(-50%,-50%) scale(${0.5 + 0.5 * e})`, opacity: p }}>
      <div style={{ position: "relative", width: 300, height: 300, borderRadius: 48, background: `linear-gradient(150deg, ${VT.blue}, ${VT.blueDeep})`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", boxShadow: `0 0 ${40 + glow * 50}px rgba(29,161,242,${0.3 + glow * 0.3}), 0 24px 60px rgba(12,122,191,0.3)`, transform: "translate(-50%,-50%)", left: "50%", top: "50%", position: "absolute" }}>
        <div style={{ fontFamily: VT.mono, fontWeight: 700, fontSize: 84, color: "#fff", letterSpacing: "-0.03em", lineHeight: 1 }}>{shown}<span style={{ fontSize: 38, opacity: 0.85 }}>%</span></div>
        <div style={{ fontFamily: VT.font, fontWeight: 600, fontSize: 18, color: "rgba(255,255,255,0.85)", marginTop: 12, letterSpacing: "0.04em" }}>CORE DATUM · L0</div>
      </div>
    </div>
  );
}

/* ============================ Ascent result (L3) ======================== */
function ResultVis() {
  const { localTime } = useSprite();
  const rows = [
    { label: "High results", sub: "≥ median pass", val: 22.5, max: 26, accent: VT.blue },
    { label: "Low results", sub: "< median pass", val: 25.6, max: 26, accent: VT.borderStrong },
  ];
  return (
    <Reveal>
      <div style={{ position: "absolute", left: VCX, top: VCY, transform: "translate(-50%,-50%)", width: 620, background: VT.white, border: `1.5px solid ${VT.border}`, borderRadius: 22, overflow: "hidden", boxShadow: "0 18px 46px rgba(15,20,25,0.12)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "18px 24px", borderBottom: `1.5px solid ${VT.border}` }}>
          <span style={{ width: 12, height: 12, borderRadius: 99, background: VT.blue }} />
          <span style={{ fontFamily: VT.font, fontWeight: 700, fontSize: 22, color: VT.ink }}>Do smaller classes lead to higher results?</span>
        </div>
        <div style={{ padding: "10px 24px 22px" }}>
          {rows.map((r, i) => {
            const p = clamp((localTime - 0.35 - i * 0.18) / 0.6, 0, 1);
            return (
              <div key={r.label} style={{ padding: "16px 0", borderBottom: i === 0 ? `1px solid ${VT.border}` : "none" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 8 }}>
                  <span style={{ fontFamily: VT.font, fontWeight: 700, fontSize: 18, color: VT.ink }}>{r.label}</span>
                  <span style={{ fontFamily: VT.font, fontSize: 15, color: VT.neutral }}>{r.sub}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <div style={{ flex: 1, height: 30, background: VT.surface, borderRadius: 9, overflow: "hidden" }}>
                    <div style={{ width: `${(r.val / r.max) * 100 * Easing.easeOutCubic(p)}%`, height: "100%", background: r.accent, borderRadius: 9 }} />
                  </div>
                  <span style={{ fontFamily: VT.mono, fontWeight: 700, fontSize: 26, color: r.accent === VT.blue ? VT.blue : VT.ink, width: 80, textAlign: "right" }}>{(r.val * Easing.easeOutCubic(p)).toFixed(1)}</span>
                </div>
                <div style={{ textAlign: "right", fontFamily: VT.mono, fontSize: 13, color: VT.neutral, marginTop: 3 }}>students / class</div>
              </div>
            );
          })}
        </div>
      </div>
    </Reveal>
  );
}

Object.assign(window, { VCX, VCY, Reveal, L4Vis, L3Vis, L2Vis, L1Vis, L0Vis, ResultVis });

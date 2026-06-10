/* ============================================================================
   anim-main.jsx — timeline, HUD (level ladder + phase + intent), title &
   closing scenes, and the Stage composition for the descent–ascent video.
   ============================================================================ */
const { useRef: vUseRef } = React;

/* --------------------------------- timeline ------------------------------ */
const TL = {
  title: [0, 5],
  l4: [5, 10],
  d43: [10, 15],
  d32: [15, 19.5],
  d21: [19.5, 24],
  l0: [24, 33],          // L1→L0 landing + core hold (pivot mid-way)
  capD10: [24, 28.6],
  capPivot: [28.8, 33],
  a01: [33, 38],
  a12: [38, 43],
  a23: [43, 48.6],
  closing: [48.6, 55],
};
const VDURATION = 55;
const HUD_IN = 5, HUD_OUT = 48.6;

function levelAt(t) {
  if (t < 10) return 4;
  if (t < 15) return 3;
  if (t < 19.5) return 2;
  if (t < 24) return 1;
  if (t < 33) return 0;
  if (t < 38) return 1;
  if (t < 43) return 2;
  return 3;
}
const phaseAt = (t) => (t < 28.7 ? "descent" : "ascent");

/* --------------------------------- BG ------------------------------------ */
function VBg() {
  return (
    <div style={{ position: "absolute", inset: 0, background: VT.white }}>
      <div style={{ position: "absolute", inset: 0, backgroundImage: `radial-gradient(${VT.border} 1.4px, transparent 1.4px)`, backgroundSize: "44px 44px", opacity: 0.6 }} />
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(120% 80% at 50% 0%, rgba(29,161,242,0.05), transparent 60%)" }} />
    </div>
  );
}

/* ----------------------------- Level ladder HUD -------------------------- */
function LevelLadderHUD() {
  const t = useTime();
  if (t < HUD_IN - 0.4 || t > HUD_OUT + 0.4) return null;
  const appear = clamp((t - (HUD_IN - 0.4)) / 0.5, 0, 1) * (1 - clamp((t - HUD_OUT) / 0.4, 0, 1));
  const active = levelAt(t);
  const phase = phaseAt(t);
  const levels = [4, 3, 2, 1, 0];
  const names = { 4: "Unlinked", 3: "Linked", 2: "Table", 1: "Vector", 0: "Value" };
  const ys = { 4: 300, 3: 415, 2: 530, 1: 645, 0: 760 };
  return (
    <div style={{ position: "absolute", left: 0, top: 0, opacity: appear }}>
      <div style={{ position: "absolute", left: 132, top: 312, width: 3, height: 448, background: VT.border, borderRadius: 3 }} />
      {levels.map((lv) => {
        const isActive = lv === active;
        const done = phase === "descent" ? lv > active : lv < active;
        const col = isActive ? VT.blue : done ? VT.blue : VT.neutral;
        return (
          <div key={lv} style={{ position: "absolute", left: 132, top: ys[lv], transform: "translate(-50%,-50%)", display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{
              width: isActive ? 56 : 40, height: isActive ? 56 : 40, borderRadius: 999, flex: "none",
              display: "flex", alignItems: "center", justifyContent: "center",
              background: isActive ? VT.blue : done ? VT.blueSoft : VT.white,
              border: isActive ? "none" : `2px solid ${done ? "rgba(29,161,242,0.4)" : VT.border}`,
              color: isActive ? "#fff" : col, fontFamily: VT.mono, fontWeight: 700, fontSize: isActive ? 18 : 14,
              boxShadow: isActive ? "0 8px 24px rgba(29,161,242,0.4)" : "none", transition: "none",
            }}>L{lv}</span>
            <span style={{ fontFamily: VT.font, fontWeight: isActive ? 700 : 500, fontSize: isActive ? 19 : 16, color: isActive ? VT.ink : VT.neutral }}>{names[lv]}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------ Phase chip ------------------------------- */
function PhaseChipHUD() {
  const t = useTime();
  if (t < HUD_IN - 0.4 || t > HUD_OUT + 0.4) return null;
  const appear = clamp((t - (HUD_IN - 0.4)) / 0.5, 0, 1) * (1 - clamp((t - HUD_OUT) / 0.4, 0, 1));
  const ascent = phaseAt(t) === "ascent";
  return (
    <div style={{ position: "absolute", left: VCX, top: 78, transform: "translateX(-50%)", opacity: appear, display: "flex", alignItems: "center", gap: 12, padding: "12px 26px", borderRadius: 999, background: ascent ? VT.blueSoft : VT.surface2, border: `1.5px solid ${ascent ? "rgba(29,161,242,0.3)" : VT.border}` }}>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={ascent ? VT.blue : VT.neutral} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        {ascent ? <path d="M12 19V5M6 11l6-6 6 6" /> : <path d="M12 5v14M6 13l6 6 6-6" />}
      </svg>
      <span style={{ fontFamily: VT.font, fontWeight: 700, fontSize: 22, color: ascent ? VT.blue : VT.neutral, letterSpacing: "0.01em" }}>{ascent ? "ASCENT" : "DESCENT"}</span>
      <span style={{ fontFamily: VT.font, fontWeight: 500, fontSize: 19, color: VT.neutral }}>{ascent ? "rebuild with intent" : "reduce complexity"}</span>
    </div>
  );
}

/* ------------------------------ Intent pill ------------------------------ */
function IntentHUD() {
  const t = useTime();
  if (t < 28.8 || t > HUD_OUT + 0.4) return null;
  const appear = clamp((t - 28.8) / 0.6, 0, 1) * (1 - clamp((t - HUD_OUT) / 0.4, 0, 1));
  return (
    <div style={{ position: "absolute", right: 70, top: 150, transform: `translateY(${(1 - appear) * -14}px)`, opacity: appear, display: "flex", alignItems: "center", gap: 12, padding: "14px 22px", borderRadius: 16, background: VT.white, border: `1.5px solid rgba(29,161,242,0.35)`, boxShadow: "0 10px 30px rgba(15,20,25,0.08)", maxWidth: 420 }}>
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={VT.blue} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" /><circle cx="12" cy="12" r="3.2" /></svg>
      <div>
        <div style={{ fontFamily: VT.mono, fontSize: 13, fontWeight: 700, color: VT.blue, letterSpacing: "0.06em" }}>YOUR INTENT</div>
        <div style={{ fontFamily: VT.font, fontSize: 17, fontWeight: 600, color: VT.ink }}>Do smaller classes lead to higher results?</div>
      </div>
    </div>
  );
}

/* ------------------------------ Title scene ------------------------------ */
function TitleScene() {
  const { localTime, duration } = useSprite();
  const out = clamp((localTime - (duration - 0.6)) / 0.6, 0, 1);
  const markP = Easing.easeOutBack(clamp(localTime / 0.7, 0, 1));
  const t1 = clamp((localTime - 0.4) / 0.6, 0, 1);
  const t2 = clamp((localTime - 0.9) / 0.6, 0, 1);
  const t3 = clamp((localTime - 1.4) / 0.6, 0, 1);
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", opacity: 1 - out, transform: `scale(${1 - out * 0.04})` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 30, transform: `scale(${markP})` }}>
        <div style={{ width: 96, height: 96, borderRadius: 26, background: `linear-gradient(135deg, #2BA8F4, ${VT.blueDeep})`, position: "relative", boxShadow: "0 16px 40px rgba(12,122,191,0.35)" }}>
          <div style={{ position: "absolute", inset: 18, borderRadius: 16, border: "3px solid rgba(255,255,255,0.45)" }} />
          <div style={{ position: "absolute", inset: 32, borderRadius: 9, border: "3px solid rgba(255,255,255,0.85)" }} />
          <div style={{ position: "absolute", left: "50%", top: "50%", width: 16, height: 16, marginLeft: -8, marginTop: -8, borderRadius: 99, background: "#fff" }} />
        </div>
      </div>
      <div style={{ fontFamily: VT.font, fontSize: 84, fontWeight: 800, letterSpacing: "-0.03em", color: VT.ink, opacity: t1, transform: `translateY(${(1 - t1) * 18}px)` }}>Intuitiveness</div>
      <div style={{ fontFamily: VT.font, fontSize: 38, fontWeight: 600, color: VT.blue, marginTop: 8, opacity: t2, transform: `translateY(${(1 - t2) * 14}px)` }}>The descent–ascent cycle</div>
      <div style={{ fontFamily: VT.mono, fontSize: 20, color: VT.neutral, marginTop: 18, letterSpacing: "0.04em", opacity: t3 }}>granularity &amp; complexity for tabular data</div>
    </div>
  );
}

/* ----------------------------- Closing scene ----------------------------- */
function ClosingScene() {
  const { localTime } = useSprite();
  const t1 = clamp(localTime / 0.7, 0, 1);
  const t2 = clamp((localTime - 0.6) / 0.7, 0, 1);
  const t3 = clamp((localTime - 1.4) / 0.7, 0, 1);
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18, opacity: t1, transform: `scale(${0.9 + 0.1 * Easing.easeOutBack(t1)})` }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={VT.neutral} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M6 13l6 6 6-6" /></svg>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={VT.blue} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5M6 11l6-6 6 6" /></svg>
      </div>
      <div style={{ fontFamily: VT.font, fontSize: 52, fontWeight: 800, letterSpacing: "-0.02em", color: VT.ink, textAlign: "center", maxWidth: 1200, lineHeight: 1.2, marginTop: 34, opacity: t2, transform: `translateY(${(1 - t2) * 18}px)`, textWrap: "balance" }}>
        Nothing wasted, nothing lost — <span style={{ color: VT.neutral }}>the same data,</span> rebuilt for the question you had.
      </div>
      <div style={{ fontFamily: VT.font, fontSize: 24, fontWeight: 600, color: VT.neutral, marginTop: 24, opacity: t3 }}>
        Strip to the core · rebuild with intent · <span style={{ color: VT.blue, fontWeight: 700 }}>Intuitiveness</span>
      </div>
    </div>
  );
}

/* ------------------------------ scene caption ---------------------------- */
function SceneCap({ kicker, text, reduce, gain }) {
  return (
    <React.Fragment>
      {reduce && <TradeChip reduce={reduce} gain={gain} />}
      <Caption kicker={kicker} text={text} y={reduce ? 924 : 880} />
    </React.Fragment>
  );
}

/* --------------------------------- App ----------------------------------- */
function VideoApp() {
  return (
    <Stage width={1920} height={1080} duration={VDURATION} background={VT.white} persistKey="descent-ascent">
      <VBg />

      <Sprite start={TL.title[0]} end={TL.title[1]}><TitleScene /></Sprite>

      {/* HUD */}
      <LevelLadderHUD />
      <PhaseChipHUD />
      <IntentHUD />

      {/* descent */}
      <Sprite start={TL.l4[0]} end={TL.l4[1]}><L4Vis /></Sprite>
      <Sprite start={TL.l4[0]} end={TL.l4[1]}><SceneCap kicker="Level 4 · Unlinked" text="Every data endeavour begins with a pile of unlinkable datasets…" /></Sprite>

      <Sprite start={TL.d43[0]} end={TL.d43[1]}><L3Vis /></Sprite>
      <Sprite start={TL.d43[0]} end={TL.d43[1]}><SceneCap kicker="L4 → L3 · Linked" text="…but there are always deeper links waiting to be discovered." reduce="artefactual heterogeneity" gain="relational structure" /></Sprite>

      <Sprite start={TL.d32[0]} end={TL.d32[1]}><L2Vis /></Sprite>
      <Sprite start={TL.d32[0]} end={TL.d32[1]}><SceneCap kicker="L3 → L2 · Table" text="Follow them, and the noise resolves into a single, coherent picture." reduce="domain breadth" gain="domain coherence" /></Sprite>

      <Sprite start={TL.d21[0]} end={TL.d21[1]}><L1Vis /></Sprite>
      <Sprite start={TL.d21[0]} end={TL.d21[1]}><SceneCap kicker="L2 → L1 · Vector" text="Keep only what matters, and each entity becomes one clear number." reduce="attribute dimensionality" gain="feature legibility" /></Sprite>

      <Sprite start={TL.l0[0]} end={TL.l0[1]}><L0Vis /></Sprite>
      <Sprite start={TL.capD10[0]} end={TL.capD10[1]}><SceneCap kicker="L1 → L0 · Value" text="Until everything you were holding collapses to one certain truth." reduce="observational extent" gain="atomic certainty" /></Sprite>
      <Sprite start={TL.capPivot[0]} end={TL.capPivot[1]}><Caption kicker="The core datum" text="The quietest the data will ever be. But a truth, alone, answers nothing…" y={880} /></Sprite>

      {/* ascent */}
      <Sprite start={TL.a01[0]} end={TL.a01[1]}><L1Vis ascent={true} /></Sprite>
      <Sprite start={TL.a01[0]} end={TL.a01[1]}><SceneCap kicker="L0 → L1 · Vector" text="…so you bring a question — and it pulls the data back to life." reduce="atomic isolation" gain="variation along a dimension" /></Sprite>

      <Sprite start={TL.a12[0]} end={TL.a12[1]}><L2Vis ascent={true} /></Sprite>
      <Sprite start={TL.a12[0]} end={TL.a12[1]}><SceneCap kicker="L1 → L2 · Table" text="Draw the one line your question actually cares about." reduce="feature isolation" gain="attribute coverage" /></Sprite>

      <Sprite start={TL.a23[0]} end={TL.a23[1]}><ResultVis /></Sprite>
      <Sprite start={TL.a23[0]} end={TL.a23[1]}><SceneCap kicker="L2 → L3 · Linked" text="Add back the single link that answers it — and nothing else." reduce="domain isolation" gain="inter-domain linkage" /></Sprite>

      <Sprite start={TL.closing[0]} end={TL.closing[1]}><ClosingScene /></Sprite>

      <Clock />
    </Stage>
  );
}

/* timestamp label for comment context */
function Clock() {
  const t = useTime();
  vUseRef();
  const root = document.getElementById("vroot");
  if (root) root.setAttribute("data-screen-label", "t=" + t.toFixed(1) + "s · " + phaseAt(t) + " · L" + levelAt(t));
  return null;
}

ReactDOM.createRoot(document.getElementById("vroot")).render(<VideoApp />);

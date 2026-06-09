"use client";

import { Icon } from "@/components/ui/Icon";
import { NAV_LEVELS, type Phase } from "@/lib/design";

/*
 * Free-navigation explorer chrome from the Blue Pulse design (shell.jsx):
 * the Current Level / Steps Taken / State metric tiles and the two-column
 * Descend / Ascend option cards (one level at a time; L4 is entry-only).
 * Descend/Ascend call the real backend transitions.
 */

export function ExploreMetrics({
  level,
  stepsTaken,
  navState,
}: {
  level: number;
  stepsTaken: number;
  navState: "entry" | "exploring";
}) {
  const lv = NAV_LEVELS[level];
  const stateLabel = navState === "entry" ? "Entry" : "Exploring";
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1.6fr 1fr 1fr",
        gap: "var(--gap)",
        marginBottom: "var(--gap)",
      }}
    >
      <div className="card" style={{ display: "flex", alignItems: "center", gap: 13 }}>
        <span
          style={{
            width: 46,
            height: 46,
            borderRadius: 12,
            flex: "none",
            background: "var(--blue)",
            color: "#fff",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon name={lv.glyph} size={23} stroke={1.9} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div className="t-label" style={{ color: "var(--text-2)", marginBottom: 2 }}>
            CURRENT LEVEL
          </div>
          <div className="t-name" style={{ fontSize: 15 }}>
            <span className="mono" style={{ color: "var(--blue)" }}>
              {lv.code}
            </span>{" "}
            · {lv.name}
          </div>
          <div className="t-meta" style={{ fontSize: 11.5 }}>
            {lv.desc}
          </div>
        </div>
      </div>
      <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div className="t-label" style={{ color: "var(--text-2)", marginBottom: 4 }}>
          STEPS TAKEN
        </div>
        <div className="mono" style={{ fontSize: 30, fontWeight: 700, lineHeight: 1 }}>
          {stepsTaken}
        </div>
      </div>
      <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div className="t-label" style={{ color: "var(--text-2)", marginBottom: 6 }}>
          STATE
        </div>
        <span
          className="chip"
          style={{
            alignSelf: "flex-start",
            background: navState === "entry" ? "var(--neutral-soft)" : "var(--blue-soft)",
            color: navState === "entry" ? "var(--neutral)" : "var(--blue)",
          }}
        >
          <Icon name={navState === "entry" ? "info" : "search"} size={13} stroke={2} />
          {stateLabel}
        </span>
      </div>
    </div>
  );
}

export function ExploreNavOptions({
  level,
  canDescend,
  canAscend,
  onDescend,
  onAscend,
  pending,
}: {
  level: number;
  canDescend: boolean;
  canAscend: boolean;
  onDescend: () => void;
  onAscend: () => void;
  pending?: boolean;
}) {
  const down = canDescend ? NAV_LEVELS[level - 1] : null;
  const up = canAscend ? NAV_LEVELS[level + 1] : null;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 12 }}>
        <Icon name="graph" size={17} style={{ color: "var(--text-2)" }} />
        <span className="t-section" style={{ fontSize: 16 }}>
          Navigation options
        </span>
        <span className="t-meta" style={{ marginLeft: "auto" }}>
          one level at a time · L4 is entry-only
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--gap)" }}>
        <OptionCard
          dir="descend"
          target={down}
          can={canDescend}
          onClick={onDescend}
          pending={pending}
          note="You've reached L0 — the ground-truth datum. Nowhere lower to go."
        />
        <OptionCard
          dir="ascend"
          target={up}
          can={canAscend}
          onClick={onAscend}
          pending={pending}
          note={level >= 3 ? "L4 is entry-only. You can't return to raw sources." : "Ascent not available here."}
        />
      </div>
    </div>
  );
}

function OptionCard({
  dir,
  target,
  can,
  note,
  onClick,
  pending,
}: {
  dir: "descend" | "ascend";
  target: { code: string; name: string } | null;
  can: boolean;
  note: string;
  onClick: () => void;
  pending?: boolean;
}) {
  const isDown = dir === "descend";
  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        borderColor: can ? (isDown ? "var(--border)" : "var(--blue-ring)") : "var(--border)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
        <span
          style={{
            width: 30,
            height: 30,
            borderRadius: 9,
            flex: "none",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            background: isDown ? "var(--neutral-soft)" : "var(--blue-soft)",
            color: isDown ? "var(--neutral)" : "var(--blue)",
          }}
        >
          <Icon name={isDown ? "down" : "up"} size={17} stroke={2.2} />
        </span>
        <div>
          <div className="t-name" style={{ fontSize: 14.5 }}>
            {isDown ? "Descend" : "Ascend"}
          </div>
          <div className="t-meta" style={{ fontSize: 11.5 }}>
            {isDown ? "Reduce complexity" : "Rebuild with intent"}
          </div>
        </div>
      </div>
      {can && target ? (
        <button
          className={`pill-btn ${isDown ? "primary" : "ghost"}`}
          onClick={onClick}
          disabled={pending}
          style={{ width: "100%", height: 42 }}
        >
          <Icon name={isDown ? "down" : "up"} size={16} stroke={2.2} />
          {isDown ? "Descend to" : "Ascend to"} <span className="mono">{target.code}</span> · {target.name}
        </button>
      ) : (
        <div className="card surface" style={{ padding: "11px 12px", display: "flex", alignItems: "center", gap: 9 }}>
          <Icon name={isDown ? "core" : "info"} size={16} style={{ color: "var(--text-2)", flex: "none" }} />
          <span className="t-meta">{note}</span>
        </div>
      )}
    </div>
  );
}

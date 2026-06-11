"use client";

import type { CSSProperties } from "react";
import { Icon } from "@/components/ui/Icon";
import { LEVELS, STEPS, type Phase } from "@/lib/design";

/*
 * Left-sidebar chrome from the Blue Pulse design (shell.jsx): brand, the
 * Guided / Explore mode toggle, the guided step checklist with a progress bar,
 * and the granularity ladder used in explore mode.
 *
 * When wired to the live backend, free-jumping to an arbitrary step/level would
 * break the real state machine, so the checklist + ladder are presentational
 * (current / done / todo) and movement happens through Previous/Next (guided)
 * or the descend/ascend option cards (explore).
 */

export function Brand({ onHome }: { onHome: () => void }) {
  return (
    <button
      onClick={onHome}
      title="Back to start"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 11,
        padding: "2px 8px",
        textAlign: "left",
        width: "100%",
        border: "none",
        background: "transparent",
        borderRadius: 10,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/intuitiveness_mark.svg"
        alt=""
        width={34}
        height={34}
        style={{ display: "block", flex: "none", borderRadius: 9 }}
      />
      <div style={{ lineHeight: 1 }}>
        <div className="t-name" style={{ fontWeight: 800, letterSpacing: "-0.02em", fontSize: 17 }}>
          Intuitiveness
        </div>
        <div className="t-meta" style={{ fontSize: 11.5, marginTop: 2 }}>
          dataset design · tabular data
        </div>
      </div>
    </button>
  );
}

export function ModeToggle({
  mode,
  onMode,
}: {
  mode: "guided" | "explore";
  onMode: (m: "guided" | "explore") => void;
}) {
  const modes = [
    { id: "guided" as const, label: "Guided", glyph: "sliders", hint: "Step-by-step" },
    { id: "explore" as const, label: "Explore", glyph: "graph", hint: "Free navigation" },
  ];
  return (
    <div style={{ padding: "0 2px" }}>
      <div
        style={{
          display: "flex",
          gap: 4,
          padding: 4,
          background: "var(--surface)",
          borderRadius: 12,
          border: "1px solid var(--border)",
        }}
      >
        {modes.map((m) => {
          const active = mode === m.id;
          return (
            <button
              key={m.id}
              onClick={() => onMode(m.id)}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 2,
                padding: "8px 6px",
                border: "none",
                borderRadius: 9,
                transition: "all .15s",
                background: active ? "var(--bg)" : "transparent",
                boxShadow: active ? "var(--shadow-1)" : "none",
                color: active ? "var(--text)" : "var(--text-2)",
              }}
            >
              <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
                <Icon name={m.glyph} size={15} stroke={active ? 2.1 : 1.8} />
                <span style={{ fontSize: 13.5, fontWeight: active ? 700 : 600 }}>{m.label}</span>
              </span>
              <span style={{ fontSize: 10.5, color: "var(--text-2)" }}>{m.hint}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function WorkflowSidebar({
  stepIndex,
  onReset,
}: {
  stepIndex: number;
  onReset: () => void;
}) {
  const total = STEPS.length;
  const progress = stepIndex / (total - 1);
  const current = STEPS[stepIndex];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* current step callout */}
      <div className="card surface" style={{ padding: "12px 14px", display: "flex", alignItems: "center", gap: 11 }}>
        <span
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            flex: "none",
            background: "var(--blue)",
            color: "#fff",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon name={current.glyph} size={19} stroke={2} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div className="mono" style={{ fontSize: 11, fontWeight: 700, color: "var(--blue)" }}>
            {current.level}
          </div>
          <div
            className="t-name"
            style={{ fontSize: 14.5, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
          >
            {current.title}
          </div>
        </div>
      </div>

      {/* progress bar */}
      <div style={{ padding: "0 2px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span className="t-label" style={{ color: "var(--text-2)" }}>
            Progress
          </span>
          <span className="mono" style={{ fontSize: 11.5, fontWeight: 700, color: "var(--text-2)" }}>
            {stepIndex + 1}/{total}
          </span>
        </div>
        <div style={{ height: 6, borderRadius: 99, background: "var(--surface-2)", overflow: "hidden" }}>
          <div
            style={{
              width: `${progress * 100}%`,
              height: "100%",
              background: "var(--blue)",
              borderRadius: 99,
              transition: "width .35s cubic-bezier(.22,.61,.36,1)",
            }}
          />
        </div>
      </div>

      {/* step checklist, grouped by phase */}
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {STEPS.map((s, i) => {
          const done = i < stepIndex;
          const cur = i === stepIndex;
          const prevPhase = i > 0 ? STEPS[i - 1].phase : null;
          const showHead = s.phase !== prevPhase;
          const headLabel =
            s.phase === "descent"
              ? "Descent · strip to the core"
              : s.phase === "pivot"
                ? "Core · set intent"
                : "Ascent · rebuild with intent";
          const headIcon = s.phase === "descent" ? "down" : s.phase === "pivot" ? "core" : "up";
          return (
            <div key={s.id}>
              {showHead && (
                <div style={{ display: "flex", alignItems: "center", gap: 7, padding: i === 0 ? "0 4px 6px" : "12px 4px 6px" }}>
                  <Icon name={headIcon} size={12} style={{ color: "var(--text-2)" }} stroke={2.2} />
                  <span
                    className="t-label"
                    style={{ color: "var(--text-2)", fontSize: 10.5, letterSpacing: "0.04em", textTransform: "uppercase" }}
                  >
                    {headLabel}
                  </span>
                </div>
              )}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 11,
                  width: "100%",
                  padding: "8px 10px",
                  borderRadius: 10,
                  background: cur ? "var(--surface)" : "transparent",
                }}
              >
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: 99,
                    flex: "none",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: cur ? "var(--blue)" : done ? "var(--blue-soft)" : "var(--bg)",
                    color: cur ? "#fff" : done ? "var(--blue)" : "var(--text-2)",
                    border: cur ? "none" : `1.5px solid ${done ? "var(--blue-ring)" : "var(--border-strong)"}`,
                  }}
                >
                  {done ? <Icon name="check" size={12} stroke={2.6} /> : <Icon name={s.glyph} size={12} stroke={2} />}
                </span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span
                    className="t-body"
                    style={{
                      display: "block",
                      fontWeight: cur ? 700 : 500,
                      color: cur ? "var(--text)" : "var(--text-2)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {s.title}
                  </span>
                </span>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--text-2)", flex: "none" }}>
                  {s.level}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <button className="pill-btn ghost" onClick={onReset} style={{ height: 36, width: "100%" }}>
        <Icon name="reset" size={15} /> Start over
      </button>
    </div>
  );
}

export function LevelLadder({ levelN, phase }: { levelN: number; phase: Phase }) {
  const cur = 4 - levelN; // vertical slot 0..4
  function stateFor(slot: number): "done" | "active" | "todo" | "na" {
    if (phase === "descent") return slot < cur ? "done" : slot === cur ? "active" : "todo";
    if (slot === cur) return "active";
    if (slot > cur) return "done";
    if (slot === 0) return "na";
    return "todo";
  }
  return (
    <nav style={{ position: "relative", padding: "2px 2px" }}>
      <div style={{ position: "absolute", left: 23, top: 30, bottom: 30, width: 2, background: "var(--border)", borderRadius: 2 }} />
      {LEVELS.map((lv, i) => {
        const st = stateFor(i);
        const isActive = st === "active";
        const isPast = st === "done";
        const dim = st === "na";
        const accent = isActive || isPast ? "var(--blue)" : "var(--neutral)";
        return (
          <div
            key={lv.n}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              width: "100%",
              padding: "8px 10px",
              borderRadius: 12,
              position: "relative",
              background: isActive ? "var(--surface)" : "transparent",
              opacity: dim ? 0.4 : 1,
            }}
          >
            <span
              style={{
                width: 34,
                height: 34,
                borderRadius: 999,
                flex: "none",
                zIndex: 1,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                background: isActive ? "var(--blue)" : isPast ? "var(--blue-soft)" : "var(--bg)",
                color: isActive ? "#fff" : accent,
                border: isActive ? "none" : `2px solid ${isPast ? "var(--blue-ring)" : "var(--border)"}`,
              } as CSSProperties}
            >
              <Icon name={lv.glyph} size={17} stroke={isActive ? 2 : 1.8} />
            </span>
            <span style={{ minWidth: 0 }}>
              <span className="mono" style={{ fontSize: 11.5, fontWeight: 700, color: accent }}>
                {lv.code}
              </span>
              <span
                className="t-body"
                style={{
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? "var(--text)" : "var(--text-2)",
                  display: "block",
                  fontSize: 13.5,
                }}
              >
                {lv.name}
              </span>
            </span>
          </div>
        );
      })}
    </nav>
  );
}

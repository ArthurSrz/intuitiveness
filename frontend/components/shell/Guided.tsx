"use client";

import { Icon } from "@/components/ui/Icon";
import { STEPS, type Step } from "@/lib/design";

/*
 * Guided-workflow header (phase chip + title + question + level metric) and the
 * Previous / Next bar, from the Blue Pulse design (shell.jsx). Next runs the
 * real backend transition; at the final step it becomes Export.
 */

export function GuidedHeader({ step }: { step: Step }) {
  const ascent = step.phase === "ascent";
  const pivot = step.phase === "pivot";
  return (
    <div style={{ padding: "22px 4px 18px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <span
          className="chip"
          style={{
            background: ascent ? "var(--blue-soft)" : pivot ? "var(--success-soft)" : "var(--neutral-soft)",
            color: ascent ? "var(--blue)" : pivot ? "var(--success)" : "var(--neutral)",
          }}
        >
          <Icon name={ascent ? "up" : pivot ? "core" : "down"} size={13} stroke={2.2} />
          {ascent ? "Ascending" : pivot ? "Core datum" : "Descending"}
        </span>
        <span className="t-meta mono">{step.level}</span>
      </div>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
        <span
          style={{
            width: 46,
            height: 46,
            borderRadius: 13,
            flex: "none",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--blue)",
          }}
        >
          <Icon name={step.glyph} size={24} stroke={1.9} />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 className="t-display" style={{ margin: "0 0 4px", fontSize: 28 }}>
            {step.title}
          </h1>
          <p className="t-body" style={{ margin: 0, color: "var(--text-2)", fontWeight: 600, textWrap: "pretty" }}>
            {step.question}
          </p>
        </div>
        <div style={{ flex: "none", textAlign: "right", paddingLeft: 8 }}>
          <div className="t-label" style={{ color: "var(--text-2)", marginBottom: 3, fontSize: 11 }}>
            LEVEL
          </div>
          <div className="mono" style={{ fontSize: 20, fontWeight: 700, color: ascent ? "var(--blue)" : "var(--text)" }}>
            {step.level}
          </div>
        </div>
      </div>
    </div>
  );
}

export function WorkflowNav({
  stepIndex,
  total,
  onPrev,
  onNext,
  pending,
  lastAction,
  nextDisabled,
}: {
  stepIndex: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
  pending?: boolean;
  lastAction: { label: string; onClick: () => void };
  nextDisabled?: boolean;
}) {
  const atStart = stepIndex === 0;
  const atEnd = stepIndex === total - 1;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "16px 4px 8px",
        marginTop: 20,
        borderTop: "1px solid var(--border)",
      }}
    >
      <button className="pill-btn ghost" onClick={onPrev} disabled={atStart || pending} style={{ height: 40 }}>
        <Icon name="up" size={16} /> Previous
      </button>
      <div style={{ display: "flex", alignItems: "center", gap: 7, margin: "0 auto" }}>
        {Array.from({ length: total }).map((_, i) => {
          const phase = STEPS[i]?.phase;
          const active = i === stepIndex;
          const visited = i < stepIndex;
          let color: string;
          let dimColor: string;
          if (phase === "pivot") {
            color = "var(--success)";
            dimColor = "var(--success-soft)";
          } else if (phase === "ascent") {
            color = "var(--blue)";
            dimColor = "var(--blue-ring)";
          } else {
            color = "var(--neutral)";
            dimColor = "var(--neutral-soft)";
          }
          return (
            <span
              key={i}
              style={{
                width: active ? 22 : 7,
                height: 7,
                borderRadius: 99,
                background: active ? color : visited ? dimColor : "var(--border-strong)",
                transition: "all .25s",
              }}
            />
          );
        })}
      </div>
      {atEnd ? (
        <button className="pill-btn dark" onClick={lastAction.onClick} disabled={pending} style={{ height: 40 }}>
          {lastAction.label} <Icon name="export" size={16} stroke={2.1} />
        </button>
      ) : (
        <button className="pill-btn primary" onClick={onNext} disabled={pending || nextDisabled} style={{ height: 40 }}>
          {pending ? "Working…" : nextDisabled ? "Use the action above ↑" : "Next"} <Icon name={nextDisabled ? "up" : "down"} size={16} stroke={2.2} />
        </button>
      )}
    </div>
  );
}

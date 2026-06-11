"use client";

import { Icon } from "@/components/ui/Icon";
import { INTENTS } from "@/lib/design";

/*
 * Right-hand context aside from the Blue Pulse design (shell.jsx): the intent
 * picker (drives the ascent narrative), the core-datum card, and the journey /
 * reduction stats. Stats are passed in from the live session summary.
 */

export function IntentCard({
  value,
  onChange,
  active,
}: {
  value: string;
  onChange: (id: string) => void;
  active: boolean;
}) {
  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <Icon name="intent" size={18} style={{ color: active ? "var(--blue)" : "var(--text-2)" }} />
        <span className="t-name" style={{ whiteSpace: "nowrap" }}>
          Your intent
        </span>
        {active && (
          <span
            className="chip"
            style={{
              marginLeft: "auto",
              background: "var(--blue-soft)",
              color: "var(--blue)",
              padding: "3px 8px",
              fontSize: 10.5,
              whiteSpace: "nowrap",
            }}
          >
            shapes the ascent
          </span>
        )}
      </div>
      <p className="t-meta" style={{ margin: "0 0 12px" }}>
        The question you&apos;re rebuilding the data to answer. Switch it any time during the ascent.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {INTENTS.map((it) => {
          const sel = value === it.id;
          return (
            <button
              key={it.id}
              onClick={() => onChange(it.id)}
              style={{
                display: "flex",
                gap: 11,
                alignItems: "flex-start",
                textAlign: "left",
                padding: "11px 12px",
                borderRadius: 12,
                border: `1px solid ${sel ? "var(--blue)" : "var(--border)"}`,
                background: sel ? "var(--blue-soft-2)" : "var(--bg)",
                transition: "all .15s",
              }}
            >
              <span
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: 99,
                  flex: "none",
                  marginTop: 1,
                  border: `2px solid ${sel ? "var(--blue)" : "var(--border-strong)"}`,
                  background: sel ? "var(--blue)" : "transparent",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {sel && <Icon name="check" size={11} style={{ color: "#fff" }} stroke={3} />}
              </span>
              <span>
                <span className="t-body" style={{ fontWeight: 600, display: "block", lineHeight: 1.35 }}>
                  {it.question}
                </span>
                <span className="t-meta mono" style={{ fontSize: 11.5 }}>
                  {it.short}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function CoreCard({ reached, datum }: { reached: boolean; datum?: string }) {
  return (
    <div className="card surface" style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 999,
          flex: "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: reached ? "var(--blue)" : "var(--bg)",
          border: reached ? "none" : "2px dashed var(--border-strong)",
        }}
      >
        {reached && datum ? (
          <span className="mono" style={{ color: "#fff", fontWeight: 700, fontSize: 15 }}>
            {datum}
          </span>
        ) : (
          <Icon name="core" size={24} style={{ color: "var(--text-2)" }} />
        )}
      </div>
      <div>
        <div className="t-label" style={{ color: "var(--text-2)", marginBottom: 3 }}>
          CORE DATUM · L0
        </div>
        <div className="t-name">{reached && datum ? datum : "Not reached yet"}</div>
        <div className="t-meta">{reached ? "The anchor for every ascent" : "Descend to L0 to reveal it"}</div>
      </div>
    </div>
  );
}

export function JourneyCard({ stats }: { stats: { k: string; v: string; accent?: boolean }[] }) {
  return (
    <div className="card">
      <div className="t-name" style={{ marginBottom: 12 }}>
        The reduction
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {stats.map((s, i) => (
          <div
            key={s.k}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "9px 0",
              borderBottom: i < stats.length - 1 ? "1px solid var(--border)" : "none",
            }}
          >
            <span className="t-meta">{s.k}</span>
            <span
              className="mono"
              style={{ fontSize: 13, fontWeight: 700, whiteSpace: "nowrap", color: s.accent ? "var(--blue)" : "var(--text)" }}
            >
              {s.v}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

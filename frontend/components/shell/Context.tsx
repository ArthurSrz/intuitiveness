"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { INTENTS } from "@/lib/design";
import { apiPost } from "@/lib/api/client";

/*
 * Right-hand context aside from the Blue Pulse design (shell.jsx): the intent
 * picker (drives the ascent narrative), the core-datum card, and the journey /
 * reduction stats. Stats are passed in from the live session summary.
 */

interface SuggestedIntent {
  question: string;
  short: string;
}

export function IntentCard({
  value,
  onChange,
  onTextChange,
  active,
  sessionId,
  locked,
}: {
  value: string;
  onChange: (id: string) => void;
  onTextChange?: (text: string) => void;
  active: boolean;
  sessionId?: string;
  locked?: boolean;
}) {
  const [aiIntents, setAiIntents] = useState<SuggestedIntent[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [customText, setCustomText] = useState("");
  const isCustom = value === "custom";
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (!sessionId || fetchedRef.current) return;
    fetchedRef.current = true;
    setLoading(true);
    apiPost<{ intents: SuggestedIntent[] }>(`/sessions/${sessionId}/intent-suggest`, {})
      .then((res) => {
        if (res.intents?.length) setAiIntents(res.intents);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sessionId]);

  const intents: Array<{ id: string; question: string; short: string }> = aiIntents
    ? aiIntents.map((it, i) => ({ id: `ai-${i}`, question: it.question, short: it.short }))
    : [];

  const selectedIntent = intents.find((it) => it.id === value);
  const selectedLabel =
    selectedIntent?.question ?? (value === "custom" && customText ? customText : null);

  if (locked && selectedLabel) {
    return (
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Icon name="intent" size={18} style={{ color: "var(--blue)" }} />
          <span className="t-name" style={{ whiteSpace: "nowrap" }}>Your intent</span>
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
        </div>
        <div
          style={{
            padding: "11px 12px",
            borderRadius: 12,
            border: "1.5px solid var(--blue)",
            background: "var(--blue-soft-2)",
          }}
        >
          <span className="t-body" style={{ fontWeight: 600, display: "block", lineHeight: 1.35 }}>
            {selectedLabel}
          </span>
          {selectedIntent?.short && (
            <span className="t-meta mono" style={{ fontSize: 11.5 }}>{selectedIntent.short}</span>
          )}
        </div>
        <button
          onClick={() => onChange("")}
          style={{
            alignSelf: "flex-start",
            background: "none",
            border: "none",
            color: "var(--text-2)",
            fontSize: 11.5,
            cursor: "pointer",
            padding: 0,
            textDecoration: "underline",
          }}
        >
          Change intent
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <Icon name="intent" size={18} style={{ color: active ? "var(--blue)" : "var(--text-2)" }} />
        <span className="t-name" style={{ whiteSpace: "nowrap" }}>
          Your intent
        </span>
        {loading && (
          <span className="t-meta" style={{ marginLeft: "auto", fontSize: 11 }}>
            AI suggesting...
          </span>
        )}
        {active && !loading && (
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
        {loading && intents.length === 0 && (
          <div style={{ padding: "14px 12px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--bg)", textAlign: "center" }}>
            <span className="t-meta">AI is crafting questions for your data...</span>
          </div>
        )}
        {intents.map((it) => {
          const sel = value === it.id;
          return (
            <button
              key={it.id}
              onClick={() => { onChange(it.id); onTextChange?.(it.question); }}
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

        {/* Custom intent */}
        <button
          onClick={() => onChange("custom")}
          style={{
            display: "flex",
            gap: 11,
            alignItems: "flex-start",
            textAlign: "left",
            padding: "11px 12px",
            borderRadius: 12,
            border: `1px solid ${isCustom ? "var(--blue)" : "var(--border)"}`,
            background: isCustom ? "var(--blue-soft-2)" : "var(--bg)",
            transition: "all .15s",
          }}
        >
          <span
            style={{
              width: 18, height: 18, borderRadius: 99, flex: "none", marginTop: 1,
              border: `2px solid ${isCustom ? "var(--blue)" : "var(--border-strong)"}`,
              background: isCustom ? "var(--blue)" : "transparent",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
            }}
          >
            {isCustom && <Icon name="check" size={11} style={{ color: "#fff" }} stroke={3} />}
          </span>
          <span className="t-body" style={{ fontWeight: 600, lineHeight: 1.35 }}>
            Write your own question
          </span>
        </button>
        {isCustom && (
          <input
            type="text"
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="e.g. Which schools need intervention?"
            autoFocus
            style={{
              width: "100%", height: 36, borderRadius: "var(--radius-md)",
              border: "1px solid var(--blue)", background: "var(--bg)",
              color: "var(--text)", fontFamily: "var(--font)", fontSize: 13,
              padding: "0 12px",
            }}
          />
        )}
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

export function JourneyCard({ stats, phase }: { stats: { k: string; v: string; accent?: boolean }[]; phase?: "descent" | "ascent" }) {
  return (
    <div className="card">
      <div className="t-name" style={{ marginBottom: 12 }}>
        {phase === "ascent" ? "The reconstruction" : "The reduction"}
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

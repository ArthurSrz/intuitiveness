"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

interface AggregationAnalyzeResult {
  proposed_aggregation: string;
  explanation: string;
  confidence: string;
  code: string;
  preview_value: number | null;
  vector_profile: { name?: string; length?: number; min?: number; max?: number; mean?: number; median?: number };
  error?: string;
}

export function AggregateButton({
  sessionId,
  onConfirm,
}: {
  sessionId: string;
  onConfirm?: () => void;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<AggregationAnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [intent, setIntent] = useState("");

  async function analyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await apiPost<AggregationAnalyzeResult>(
        `/sessions/${sessionId}/aggregation-analyze`,
        { intent },
      );
      if (res.error) {
        setError(res.error);
        setAnalyzing(false);
        return;
      }
      setResult(res);
    } catch (e) {
      setError(String(e));
    }
    setAnalyzing(false);
  }

  async function confirm() {
    if (!result?.code) return;
    setConfirming(true);
    try {
      await apiPost(`/sessions/${sessionId}/aggregation-confirm`, {
        code: result.code,
        aggregation: result.proposed_aggregation,
      });
      if (onConfirm) onConfirm();
    } catch (e) {
      setError(String(e));
      setConfirming(false);
    }
  }

  if (!result) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder="What summary do you need? (e.g. average, total, median)"
          style={{
            width: "100%", height: 36, borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-strong)", background: "var(--bg)",
            color: "var(--text)", fontFamily: "var(--font)", fontSize: 13, padding: "0 12px",
          }}
        />
        <button
          className="card"
          onClick={analyze}
          disabled={analyzing}
          style={{
            padding: "14px 16px",
            display: "flex",
            alignItems: "center",
            gap: 10,
            width: "100%",
            border: "1.5px dashed var(--blue)",
            background: analyzing ? "var(--surface)" : "var(--blue-soft)",
            cursor: analyzing ? "wait" : "pointer",
            textAlign: "left",
          }}
        >
          <Icon name="core" size={16} />
          <span style={{ fontWeight: 600, color: "var(--blue)" }}>
            {analyzing ? "Calculating your summary..." : "Calculate the summary number"}
          </span>
          {error && (
            <span style={{ color: "var(--error)", fontSize: 12, marginLeft: "auto" }}>
              {error}
            </span>
          )}
        </button>
      </div>
    );
  }

  const vp = result.vector_profile;

  return (
    <div
      className="card"
      style={{ padding: 0, overflow: "hidden", border: "1.5px solid var(--blue)" }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: 10,
          background: "var(--blue-soft)",
        }}
      >
        <Icon name="core" size={16} />
        <span style={{ fontWeight: 700, fontSize: 14, color: "var(--blue)" }}>
          Aggregation Preview
        </span>
        <span className="chip mono" style={{ fontSize: 11 }}>
          {result.proposed_aggregation}
        </span>
        <button
          className="pill-btn ghost"
          onClick={() => { setResult(null); analyze(); }}
          style={{ marginLeft: "auto", height: 26, fontSize: 11 }}
        >
          Retry
        </button>
        <button
          className="pill-btn ghost"
          onClick={() => setResult(null)}
          style={{ height: 26, fontSize: 11 }}
        >
          Cancel
        </button>
      </div>

      {/* Explanation */}
      {result.explanation && (
        <div
          style={{
            padding: "10px 16px",
            borderBottom: "1px solid var(--border)",
            fontSize: 13,
            lineHeight: 1.5,
            color: "var(--text-2)",
          }}
        >
          {result.explanation}
        </div>
      )}

      {/* Preview value — big number */}
      {result.preview_value != null && (
        <div
          style={{
            padding: "24px 16px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 6,
          }}
        >
          <div
            className="mono"
            style={{ fontSize: 56, fontWeight: 700, color: "var(--ink)", lineHeight: 1 }}
          >
            {result.preview_value}
          </div>
          <span style={{ fontSize: 12, color: "var(--text-2)", fontWeight: 600 }}>
            {result.proposed_aggregation} of {vp.name || "vector"} ({vp.length || "?"} values)
          </span>
        </div>
      )}

      {/* Vector stats context */}
      {vp.min != null && (
        <div
          style={{
            padding: "0 16px 14px",
            display: "flex",
            justifyContent: "center",
            gap: 20,
          }}
        >
          {[
            { label: "Min", value: vp.min },
            { label: "Mean", value: vp.mean },
            { label: "Median", value: vp.median },
            { label: "Max", value: vp.max },
          ]
            .filter((s) => s.value != null)
            .map((s) => (
              <div
                key={s.label}
                style={{ display: "flex", flexDirection: "column", alignItems: "center" }}
              >
                <span className="mono" style={{ fontSize: 14, fontWeight: 600, color: "var(--text-2)" }}>
                  {s.value}
                </span>
                <span style={{ fontSize: 10, color: "var(--text-2)" }}>{s.label}</span>
              </div>
            ))}
        </div>
      )}

      {/* Code toggle */}
      {result.code && (
        <div style={{ padding: "0 16px 12px" }}>
          <button
            className="pill-btn ghost"
            onClick={() => setShowCode((v) => !v)}
            style={{ height: 26, fontSize: 11 }}
          >
            {showCode ? "Hide code" : "Show aggregation code"}
          </button>
          {showCode && (
            <pre
              className="mono"
              style={{
                marginTop: 8, padding: 12, background: "var(--surface)",
                borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                fontSize: 12, lineHeight: 1.5, overflowX: "auto", whiteSpace: "pre-wrap",
              }}
            >
              {result.code}
            </pre>
          )}
        </div>
      )}

      {/* Confirm */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <button
          className="pill-btn primary"
          disabled={confirming || !result.code}
          onClick={confirm}
          style={{ height: 36, fontSize: 13 }}
        >
          {confirming ? "Computing..." : "Confirm and descend to L0"}
        </button>
        {error && (
          <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>
        )}
      </div>
    </div>
  );
}

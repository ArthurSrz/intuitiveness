"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

interface EnrichmentAnalyzeResult {
  code: string;
  explanation: string;
  confidence: string;
  preview_description: string;
  preview_stats: {
    count?: number;
    mean?: number | null;
    min?: number | null;
    max?: number | null;
  };
  error?: string;
}

export function EnrichButton({
  sessionId,
  onConfirm,
  initialIntent,
}: {
  sessionId: string;
  onConfirm?: () => void;
  initialIntent?: string;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<EnrichmentAnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [intent, setIntent] = useState(initialIntent ?? "");

  async function analyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await apiPost<EnrichmentAnalyzeResult>(
        `/sessions/${sessionId}/enrichment-analyze`,
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
    if (!result) return;
    setConfirming(true);
    try {
      await apiPost(`/sessions/${sessionId}/enrichment-confirm`, {
        code: result.code,
      });
      if (onConfirm) await onConfirm();
      setConfirming(false);
      setResult(null);
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
          placeholder={initialIntent ? `Your question: "${initialIntent}" -- edit or keep as is` : "What do you want to explore next?"}
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
          <Icon name="vector" size={16} />
          <span style={{ fontWeight: 600, color: "var(--blue)" }}>
            {analyzing ? "Preparing your next view (this can take 15-30 seconds)..." : "Expand into detailed values"}
          </span>
          <span className="chip" style={{ background: "var(--blue)", color: "#fff", fontSize: 10, padding: "2px 6px" }}>Next step
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

  const stats = result.preview_stats || {};

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
        <Icon name="vector" size={16} />
        <span style={{ fontWeight: 700, fontSize: 14, color: "var(--blue)" }}>
          What you will see next
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

      {/* Preview stats */}
      {(stats.count != null || stats.mean != null) && (
        <div
          style={{
            padding: "10px 16px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            gap: 16,
            fontSize: 12,
            color: "var(--text-2)",
          }}
        >
          {stats.count != null && (
            <span><strong>{stats.count}</strong> values</span>
          )}
          {stats.mean != null && (
            <span>mean: <strong>{stats.mean}</strong></span>
          )}
          {stats.min != null && (
            <span>min: <strong>{stats.min}</strong></span>
          )}
          {stats.max != null && (
            <span>max: <strong>{stats.max}</strong></span>
          )}
        </div>
      )}

      {/* Preview description */}
      <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
        <span className="t-meta" style={{ fontSize: 12 }}>
          {result.preview_description || "Rebuilding datum into a vector"}
        </span>

        {/* Show code toggle */}
        <button
          className="pill-btn ghost"
          onClick={() => setShowCode(!showCode)}
          style={{ height: 24, fontSize: 11, alignSelf: "flex-start" }}
        >
          {showCode ? "Hide code" : "Show code"}
        </button>
        {showCode && (
          <pre
            style={{
              background: "var(--surface)",
              padding: 10,
              borderRadius: "var(--radius-sm)",
              fontSize: 11,
              overflow: "auto",
              maxHeight: 120,
              whiteSpace: "pre-wrap",
              color: "var(--text-2)",
            }}
          >
            {result.code}
          </pre>
        )}
      </div>

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
          disabled={confirming}
          onClick={confirm}
          style={{ height: 36, fontSize: 13 }}
        >
          {confirming ? "Rebuilding..." : "Confirm and ascend to L1"}
        </button>
        {error && (
          <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>
        )}
      </div>
    </div>
  );
}

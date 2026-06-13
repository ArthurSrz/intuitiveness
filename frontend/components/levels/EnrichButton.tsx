"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

interface EnrichmentAnalyzeResult {
  method: string;
  explanation: string;
  confidence: string;
  preview_length: number;
  preview_description: string;
  error?: string;
}

export function EnrichButton({
  sessionId,
  onConfirm,
}: {
  sessionId: string;
  onConfirm?: () => void;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<EnrichmentAnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [intent, setIntent] = useState("");

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
      await apiPost(`/sessions/${sessionId}/ascend`, {
        enrichment_func: "source_expansion",
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
          placeholder="What do you want to understand?"
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
            {analyzing ? "AI is planning the enrichment..." : "Enrich — rebuild the vector"}
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
          Enrichment Preview
        </span>
        <span className="chip mono" style={{ fontSize: 11 }}>
          {result.method}
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

      {/* Preview info */}
      <div style={{ padding: "16px", display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="chip mono" style={{ background: "var(--blue)", color: "#fff", fontSize: 18, padding: "6px 14px" }}>
            1
          </span>
          <Icon name="arrowRight" size={18} style={{ color: "var(--text-2)" }} />
          <span className="chip mono" style={{ background: "var(--blue-soft)", color: "var(--blue)", fontSize: 18, padding: "6px 14px" }}>
            {result.preview_length || "?"}
          </span>
        </div>
        <span className="t-meta" style={{ fontSize: 12 }}>
          {result.preview_description || `Rebuilding 1 datum into ${result.preview_length} values`}
        </span>
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

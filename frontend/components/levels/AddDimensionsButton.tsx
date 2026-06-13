"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

interface DimensionAnalyzeResult {
  explanation: string;
  confidence: string;
  code: string;
  proposed_columns: string[];
  sample_distribution: Record<string, number>;
  error?: string;
}

export function AddDimensionsButton({
  sessionId,
  onConfirm,
}: {
  sessionId: string;
  onConfirm?: () => void;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<DimensionAnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState("");
  const [showCode, setShowCode] = useState(false);

  async function analyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await apiPost<DimensionAnalyzeResult>(
        `/sessions/${sessionId}/dimension-analyze`,
        { intent },
      );
      if (res.error) { setError(res.error); setAnalyzing(false); return; }
      setResult(res);
    } catch (e) { setError(String(e)); }
    setAnalyzing(false);
  }

  async function confirm() {
    if (!result?.code) return;
    setConfirming(true);
    try {
      await apiPost(`/sessions/${sessionId}/dimension-confirm`, {
        code: result.code,
      });
      if (onConfirm) onConfirm();
    } catch (e) { setError(String(e)); setConfirming(false); }
  }

  if (!result) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder="What groups do you want to compare?"
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
            padding: "14px 16px", display: "flex", alignItems: "center", gap: 10,
            width: "100%", border: "1.5px dashed var(--blue)",
            background: analyzing ? "var(--surface)" : "var(--blue-soft)",
            cursor: analyzing ? "wait" : "pointer", textAlign: "left",
          }}
        >
          <Icon name="categories" size={16} />
          <span style={{ fontWeight: 600, color: "var(--blue)" }}>
            {analyzing ? "AI is building dimensions..." : "Add dimensions — split by groups"}
          </span>
          {error && <span style={{ color: "var(--error)", fontSize: 12, marginLeft: "auto" }}>{error}</span>}
        </button>
      </div>
    );
  }

  const maxCount = Math.max(1, ...Object.values(result.sample_distribution));
  const totalRows = Object.values(result.sample_distribution).reduce((a, b) => a + b, 0);

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", border: "1.5px solid var(--blue)" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10, background: "var(--blue-soft)" }}>
        <Icon name="categories" size={16} />
        <span style={{ fontWeight: 700, fontSize: 14, color: "var(--blue)" }}>Dimension Preview</span>
        {result.proposed_columns.length > 0 && (
          <span className="chip mono" style={{ fontSize: 11 }}>
            {result.proposed_columns.join(", ")}
          </span>
        )}
        <button className="pill-btn ghost" onClick={() => { setResult(null); analyze(); }} style={{ marginLeft: "auto", height: 26, fontSize: 11 }}>Retry</button>
        <button className="pill-btn ghost" onClick={() => setResult(null)} style={{ height: 26, fontSize: 11 }}>Cancel</button>
      </div>

      {result.explanation && (
        <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", fontSize: 13, lineHeight: 1.5, color: "var(--text-2)" }}>
          {result.explanation}
        </div>
      )}

      {/* Distribution bars */}
      <div style={{ padding: "12px 16px" }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 10 }}>
          PROPOSED GROUPS
          {totalRows > 0 && <span style={{ fontWeight: 400, marginLeft: 8 }}>({totalRows} sample rows)</span>}
        </span>
        {Object.entries(result.sample_distribution).map(([group, count]) => {
          const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
          return (
            <div key={group} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <span className="mono" style={{ width: 160, fontSize: 13, fontWeight: 600, color: "var(--blue)", flexShrink: 0 }}>
                {group}
              </span>
              <div style={{ flex: 1, height: 22, background: "var(--surface)", borderRadius: 4, overflow: "hidden", position: "relative" }}>
                <div style={{ height: "100%", width: `${pct}%`, background: "var(--blue)", opacity: 0.25, borderRadius: 4 }} />
                {count > 0 && (
                  <span className="mono" style={{ position: "absolute", left: 6, top: 3, fontSize: 11, color: "var(--text-2)" }}>
                    {count} rows
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {totalRows === 0 && (
          <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
            <span className="t-meta" style={{ flex: 1 }}>Preview unavailable. Try again or adjust your intent.</span>
            <button className="pill-btn primary" onClick={() => { setResult(null); analyze(); }} style={{ height: 30, fontSize: 12, flex: "none" }}>Retry with AI</button>
          </div>
        )}
      </div>

      {/* Code toggle */}
      {result.code && (
        <div style={{ padding: "0 16px 12px" }}>
          <button className="pill-btn ghost" onClick={() => setShowCode((v) => !v)} style={{ height: 26, fontSize: 11 }}>
            {showCode ? "Hide code" : "Show dimension code"}
          </button>
          {showCode && (
            <pre className="mono" style={{ marginTop: 8, padding: 12, background: "var(--surface)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", fontSize: 12, lineHeight: 1.5, overflowX: "auto", whiteSpace: "pre-wrap" }}>
              {result.code}
            </pre>
          )}
        </div>
      )}

      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
        <button
          className="pill-btn primary"
          disabled={confirming || !result.code}
          onClick={confirm}
          style={{ height: 36, fontSize: 13 }}
        >
          {confirming ? "Adding dimensions..." : "Confirm and ascend to L2"}
        </button>
        {error && <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>}
      </div>
    </div>
  );
}

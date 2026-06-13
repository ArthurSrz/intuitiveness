"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

interface LinkageAnalyzeResult {
  proposed_dimensions: string[];
  proposed_relationships: string[];
  explanation: string;
  confidence: string;
  graph_description: string;
  available_dimensions: string[];
  error?: string;
}

export function LinkDomainsButton({
  sessionId,
  onConfirm,
}: {
  sessionId: string;
  onConfirm?: () => void;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<LinkageAnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState("");
  const [selectedDims, setSelectedDims] = useState<string[]>([]);

  async function analyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await apiPost<LinkageAnalyzeResult>(
        `/sessions/${sessionId}/linkage-analyze`,
        { intent },
      );
      if (res.error) { setError(res.error); setAnalyzing(false); return; }
      setResult(res);
      setSelectedDims(res.proposed_dimensions);
    } catch (e) { setError(String(e)); }
    setAnalyzing(false);
  }

  async function confirm() {
    setConfirming(true);
    try {
      await apiPost(`/sessions/${sessionId}/ascend`, {
        dimensions: selectedDims,
        relationships: result?.proposed_relationships?.join(", ") || "",
      });
      if (onConfirm) onConfirm();
    } catch (e) { setError(String(e)); setConfirming(false); }
  }

  function toggleDim(name: string) {
    setSelectedDims((prev) =>
      prev.includes(name) ? prev.filter((d) => d !== name) : [...prev, name],
    );
  }

  if (!result) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder="What external factor do you want to test?"
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
          <Icon name="graph" size={16} />
          <span style={{ fontWeight: 600, color: "var(--blue)" }}>
            {analyzing ? "AI is suggesting linkages..." : "Link domains — connect to other data"}
          </span>
          {error && <span style={{ color: "var(--error)", fontSize: 12, marginLeft: "auto" }}>{error}</span>}
        </button>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", border: "1.5px solid var(--blue)" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10, background: "var(--blue-soft)" }}>
        <Icon name="graph" size={16} />
        <span style={{ fontWeight: 700, fontSize: 14, color: "var(--blue)" }}>Linkage Preview</span>
        <button className="pill-btn ghost" onClick={() => { setResult(null); analyze(); }} style={{ marginLeft: "auto", height: 26, fontSize: 11 }}>Retry</button>
        <button className="pill-btn ghost" onClick={() => setResult(null)} style={{ height: 26, fontSize: 11 }}>Cancel</button>
      </div>

      {result.explanation && (
        <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", fontSize: 13, lineHeight: 1.5, color: "var(--text-2)" }}>
          {result.explanation}
        </div>
      )}

      <div style={{ padding: "12px 16px" }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 10 }}>
          DIMENSIONS & RELATIONSHIPS
        </span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {(result.available_dimensions.length ? result.available_dimensions : result.proposed_dimensions).map((dim) => {
            const on = selectedDims.includes(dim);
            return (
              <button
                key={dim}
                onClick={() => toggleDim(dim)}
                className="chip"
                style={{
                  cursor: "pointer",
                  background: on ? "var(--blue)" : "var(--bg)",
                  color: on ? "#fff" : "var(--text)",
                  border: `1px solid ${on ? "var(--blue)" : "var(--border-strong)"}`,
                  padding: "6px 12px", fontSize: 13, fontWeight: 600,
                }}
              >
                {on && <Icon name="check" size={12} stroke={2.6} />}
                {dim}
              </button>
            );
          })}
        </div>
        {result.proposed_relationships.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)" }}>RELATIONSHIPS: </span>
            <span className="t-meta">{result.proposed_relationships.join(", ")}</span>
          </div>
        )}
        {result.graph_description && (
          <p className="t-meta" style={{ marginTop: 10, fontSize: 12 }}>{result.graph_description}</p>
        )}
      </div>

      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
        <button
          className="pill-btn primary"
          disabled={confirming}
          onClick={confirm}
          style={{ height: 36, fontSize: 13 }}
        >
          {confirming ? "Building graph..." : "Confirm and ascend to L3"}
        </button>
        {error && <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>}
      </div>
    </div>
  );
}

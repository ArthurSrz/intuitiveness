"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

interface LinkageAnalyzeResult {
  code: string;
  proposed_columns: string[];
  explanation: string;
  confidence: string;
  graph_description: string;
  sample_distribution: Record<string, Record<string, number>>;
  error?: string;
}

export function LinkDomainsButton({
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
  const [result, setResult] = useState<LinkageAnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState(initialIntent ?? "");
  const [showCode, setShowCode] = useState(false);

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
    } catch (e) { setError(String(e)); }
    setAnalyzing(false);
  }

  async function confirm() {
    if (!result) return;
    setConfirming(true);
    try {
      await apiPost(`/sessions/${sessionId}/linkage-confirm`, {
        code: result.code,
      });
      if (onConfirm) await onConfirm();
      setConfirming(false);
      setResult(null);
    } catch (e) { setError(String(e)); setConfirming(false); }
  }

  const examplePrompts = [
    "Compare GDP across regions",
    "Link to population data",
    "Test against climate indicators",
  ];

  if (!result) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder="What other data would you like to bring in?"
          style={{
            width: "100%", height: 36, borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-strong)", background: "var(--bg)",
            color: "var(--text)", fontFamily: "var(--font)", fontSize: 13, padding: "0 12px",
          }}
        />
        {!intent && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {examplePrompts.map((ex) => (
              <button
                key={ex}
                className="pill-btn ghost"
                style={{ height: 26, fontSize: 11, color: "var(--text-2)" }}
                onClick={() => setIntent(ex)}
              >
                e.g. {ex}
              </button>
            ))}
          </div>
        )}
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
            {analyzing ? "Analyzing your data (this can take 15-30 seconds)..." : "Evaluate from new angles"}
          </span>
          {error && <span style={{ color: "var(--error)", fontSize: 12, marginLeft: "auto" }}>{error}</span>}
        </button>
      </div>
    );
  }

  const distEntries = Object.entries(result.sample_distribution || {});

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", border: "1.5px solid var(--blue)" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10, background: "var(--blue-soft)" }}>
        <Icon name="graph" size={16} />
        <span style={{ fontWeight: 700, fontSize: 14, color: "var(--blue)" }}>Preview: new columns to add</span>
        <button className="pill-btn ghost" onClick={() => { setResult(null); analyze(); }} style={{ marginLeft: "auto", height: 26, fontSize: 11 }}>Retry</button>
        <button className="pill-btn ghost" onClick={() => setResult(null)} style={{ height: 26, fontSize: 11 }}>Cancel</button>
      </div>

      {result.explanation && (
        <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", fontSize: 13, lineHeight: 1.5, color: "var(--text-2)" }}>
          {result.explanation}
        </div>
      )}

      {/* Distribution preview */}
      {distEntries.length > 0 && (
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 8 }}>
            HOW YOUR DATA WILL BE SPLIT (sample)
          </span>
          {distEntries.map(([colName, dist]) => (
            <div key={colName} style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{colName}</span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                {Object.entries(dist).map(([val, count]) => (
                  <span key={val} className="chip" style={{ fontSize: 11, padding: "3px 8px", background: "var(--surface)", border: "1px solid var(--border)" }}>
                    {val}: {count}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Proposed columns */}
      {result.proposed_columns.length > 0 && (
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 8 }}>
            COLUMNS THAT WILL BE ADDED TO YOUR TABLE
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {result.proposed_columns.map((col) => (
              <span key={col} className="chip" style={{ fontSize: 12, padding: "4px 10px", background: "var(--blue-soft)", color: "var(--blue)", fontWeight: 600 }}>
                {col}
              </span>
            ))}
          </div>
        </div>
      )}

      {result.graph_description && (
        <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)" }}>
          <p className="t-meta" style={{ fontSize: 12 }}>{result.graph_description}</p>
        </div>
      )}

      {/* Data provenance notice */}
      <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
        <p style={{ margin: 0, fontSize: 12, lineHeight: 1.5, color: "var(--text-2)" }}>
          <strong>Where does this data come from?</strong> These columns are computed from your existing data (ranks, shares, averages). They do not come from an external source.
          To bring in real external data (e.g., World Bank indicators), go back to the home page and import a second dataset first.
        </p>
      </div>

      {/* Show code toggle */}
      {result.code && (
        <div style={{ padding: "8px 16px", borderBottom: "1px solid var(--border)" }}>
          <button
            className="pill-btn ghost"
            onClick={() => setShowCode(!showCode)}
            style={{ height: 24, fontSize: 11 }}
          >
            {showCode ? "Hide code" : "Show code"}
          </button>
          {showCode && (
            <pre style={{ marginTop: 8, fontSize: 11, lineHeight: 1.4, background: "var(--surface)", padding: 10, borderRadius: "var(--radius-sm)", overflow: "auto", maxHeight: 200 }}>
              {result.code}
            </pre>
          )}
        </div>
      )}

      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
        <button
          className="pill-btn primary"
          disabled={confirming}
          onClick={confirm}
          style={{ height: 36, fontSize: 13 }}
        >
          {confirming ? "Building linked table..." : "Confirm and continue"}
        </button>
        {error && <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>}
      </div>
    </div>
  );
}

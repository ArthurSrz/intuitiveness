"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

interface ColumnAnalyzeResult {
  proposed_column: string;
  proposed_filter: string;
  explanation: string;
  confidence: string;
  code: string;
  columns: string[];
  preview_stats: { count?: number; mean?: number; min?: number; max?: number };
  error?: string;
}

export function SelectFeatureButton({
  sessionId,
  onConfirm,
}: {
  sessionId: string;
  onConfirm?: () => void;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<ColumnAnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedColumn, setSelectedColumn] = useState("");
  const [filterQuery, setFilterQuery] = useState("");
  const [showCode, setShowCode] = useState(false);
  const [intent, setIntent] = useState("");

  async function analyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await apiPost<ColumnAnalyzeResult>(
        `/sessions/${sessionId}/column-analyze`,
        { intent },
      );
      if (res.error) {
        setError(res.error);
        setAnalyzing(false);
        return;
      }
      setResult(res);
      setSelectedColumn(res.proposed_column);
      setFilterQuery(res.proposed_filter);
    } catch (e) {
      setError(String(e));
    }
    setAnalyzing(false);
  }

  async function confirm() {
    if (!result?.code) return;
    setConfirming(true);
    try {
      await apiPost(`/sessions/${sessionId}/column-confirm`, {
        code: result.code,
        column: selectedColumn,
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
          placeholder="What variable matters most?"
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
            {analyzing ? "AI is analyzing your table..." : "Select feature for extraction"}
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

  const stats = result.preview_stats;

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
          Feature Preview
        </span>
        <span className="chip mono" style={{ fontSize: 11 }}>
          {selectedColumn}
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

      {/* Column selector + filter */}
      <div style={{ padding: "12px 16px", display: "flex", gap: 12, flexWrap: "wrap" }}>
        <label style={{ flex: 1, minWidth: 140 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 5 }}>
            COLUMN TO EXTRACT
          </span>
          <select
            style={{
              width: "100%", height: 32, borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-strong)", background: "var(--bg)",
              color: "var(--text)", fontFamily: "var(--font)", fontSize: 13, padding: "0 8px",
            }}
            value={selectedColumn}
            onChange={(e) => setSelectedColumn(e.target.value)}
          >
            {result.columns.map((col) => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
        </label>
        <label style={{ flex: 1, minWidth: 140 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 5 }}>
            FILTER (OPTIONAL)
          </span>
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="e.g. category == 'high'"
            style={{
              width: "100%", height: 32, borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-strong)", background: "var(--bg)",
              color: "var(--text)", fontFamily: "var(--font)", fontSize: 13, padding: "0 8px",
            }}
          />
        </label>
      </div>

      {/* Preview stats */}
      {stats.count != null && (
        <div style={{ padding: "0 16px 12px", display: "flex", gap: 16, flexWrap: "wrap" }}>
          {[
            { label: "Values", value: stats.count },
            { label: "Min", value: stats.min },
            { label: "Mean", value: stats.mean },
            { label: "Max", value: stats.max },
          ]
            .filter((s) => s.value != null)
            .map((s) => (
              <div key={s.label} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <span className="mono" style={{ fontSize: 18, fontWeight: 700, color: "var(--blue)" }}>
                  {s.value}
                </span>
                <span style={{ fontSize: 10, color: "var(--text-2)", fontWeight: 600 }}>
                  {s.label}
                </span>
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
            {showCode ? "Hide code" : "Show extraction code"}
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
          disabled={confirming || !selectedColumn}
          onClick={confirm}
          style={{ height: 36, fontSize: 13 }}
        >
          {confirming ? "Extracting to L1..." : "Confirm and descend to L1"}
        </button>
        {error && (
          <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>
        )}
      </div>
    </div>
  );
}

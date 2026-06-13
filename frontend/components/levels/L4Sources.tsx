"use client";

import { useMemo, useState } from "react";
import type { NodeDetail } from "@/lib/api/types";
import { decodeDataframe, type DecodedTable } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

export function L4Sources({ node, onAddSource, sessionId, onConnect }: { node: NodeDetail; onAddSource?: () => void; sessionId?: string; onConnect?: () => void }) {
  const payload = node.payload;
  const sources = useMemo(() => {
    if (!payload || typeof payload !== "object") return [];
    return Object.entries(payload as Record<string, unknown>).map(([name, enc]) => ({
      name,
      table: typeof enc === "string" ? decodeDataframe(enc) : null,
    }));
  }, [payload]);

  const shapes = (node.summary?.shapes as Record<string, unknown> | undefined) ?? undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div
        className="card"
        style={{ padding: "14px 16px", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}
      >
        <span className="chip">
          <Icon name="dataset" size={15} />
          Raw sources
        </span>
        <span
          className="t-meta mono"
          style={{
            color: sources.length > 1 ? "var(--blue)" : undefined,
            fontWeight: sources.length > 1 ? 700 : undefined,
          }}
        >
          {sources.length} source{sources.length === 1 ? "" : "s"}
        </span>
        {onAddSource && (
          <button
            className="pill-btn ghost"
            onClick={onAddSource}
            style={{ height: 28, fontSize: 12, flex: "none", padding: "0 10px", marginLeft: "auto" }}
          >
            + Add source
          </button>
        )}
      </div>

      {sources.map((s) => (
        <SourceCard
          key={s.name}
          name={s.name}
          table={s.table}
          shape={shapes?.[s.name] != null ? String(shapes[s.name]) : undefined}
          defaultOpen={sources.length <= 2}
        />
      ))}

      {sources.length >= 2 && sessionId && (
        <ConnectSourcesButton sessionId={sessionId} onConnect={onConnect} />
      )}

      {sources.length === 0 && (
        <div className="card" style={{ padding: 16 }}>
          <p className="t-meta">No source files yet — add one to begin.</p>
        </div>
      )}
    </div>
  );
}


interface CatalogEntry {
  concept: string;
  description: string;
  mappings: Array<{ source: string; column: string; notes: string }>;
}

interface AnalyzeResult {
  catalog: CatalogEntry[];
  join_plan: Record<string, unknown>;
  column_transforms: Record<string, string>;
  explanation: string;
  error?: string;
}

interface PreviewResult {
  row_count: number;
  unmatched_count: number;
  sample_rows: Record<string, unknown>[];
  sample_columns: string[];
  warnings: string[];
  error?: string;
}

function ConnectSourcesButton({ sessionId, onConnect }: { sessionId: string; onConnect?: () => void }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [excluded, setExcluded] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  async function analyze() {
    setAnalyzing(true);
    setError(null);
    setExcluded(new Set());
    setPreview(null);
    try {
      const res = await apiPost<AnalyzeResult>(`/sessions/${sessionId}/entity-analyze`, { relationships: [] });
      if (res.error) { setError(res.error); setAnalyzing(false); return; }
      setResult(res);
    } catch (e) {
      setError(String(e));
    }
    setAnalyzing(false);
  }

  function toggleExclude(i: number) {
    setExcluded((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
    setPreview(null); // reset preview when catalog changes
  }

  function activeCatalog() {
    return result!.catalog.filter((_, i) => !excluded.has(i));
  }

  async function previewJoin() {
    if (!result) return;
    setPreviewing(true);
    setPreview(null);
    try {
      const res = await apiPost<PreviewResult>(`/sessions/${sessionId}/entity-preview`, {
        catalog: activeCatalog(),
        join_plan: result.join_plan,
        column_transforms: result.column_transforms,
      });
      setPreview(res);
    } catch (e) {
      setError(String(e));
    }
    setPreviewing(false);
  }

  async function confirm() {
    if (!result) return;
    setConfirming(true);
    try {
      await apiPost(`/sessions/${sessionId}/entity-confirm`, {
        catalog: activeCatalog(),
        join_plan: result.join_plan,
        column_transforms: result.column_transforms,
      });
      if (onConnect) onConnect();
      else window.location.reload();
    } catch (e) {
      setError(String(e));
      setConfirming(false);
    }
  }

  if (!result) {
    return (
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
          {analyzing ? "Analyzing with LLM..." : "Connect these sources"}
        </span>
        {error && <span style={{ color: "var(--error)", fontSize: 12, marginLeft: "auto" }}>{error}</span>}
      </button>
    );
  }

  const activeCount = result.catalog.length - excluded.size;

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", border: "1.5px solid var(--blue)" }}>
      {/* Header */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10, background: "var(--blue-soft)" }}>
        <Icon name="graph" size={16} />
        <span style={{ fontWeight: 700, fontSize: 14, color: "var(--blue)" }}>Schema Preview</span>
        <span className="t-meta">{activeCount} of {result.catalog.length} concepts active</span>
        <button className="pill-btn ghost" onClick={() => { setResult(null); analyze(); }} style={{ marginLeft: "auto", height: 26, fontSize: 11 }}>Retry</button>
        <button className="pill-btn ghost" onClick={() => setResult(null)} style={{ height: 26, fontSize: 11 }}>Cancel</button>
      </div>

      {/* Explanation */}
      {result.explanation && (
        <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", fontSize: 13, lineHeight: 1.5, color: "var(--text-2)" }}>
          {result.explanation}
        </div>
      )}

      {/* Concept rows — editable */}
      {result.catalog.map((c, i) => {
        const isExcluded = excluded.has(i);
        const tierNote = c.mappings?.[0]?.notes ?? "";
        const tierNum = tierNote.includes("tier 1") ? 1 : tierNote.includes("tier 2") ? 2 : tierNote.includes("tier 3") ? 3 : 0;
        const tierLabel = tierNum === 1 ? "name match" : tierNum === 2 ? "value overlap" : tierNum === 3 ? "LLM" : "";
        const confMatch = tierNote.match(/confidence:\s*(\d+%)/);
        const confidence = confMatch ? confMatch[1] : "";
        return (
          <div
            key={i}
            style={{
              display: "flex", alignItems: "center",
              borderBottom: "1px solid var(--border)", padding: "8px 0",
              opacity: isExcluded ? 0.35 : 1,
              transition: "opacity 0.15s",
            }}
          >
            {/* Left column name */}
            <div style={{ flex: 1, padding: "0 16px", textAlign: "right" }}>
              {c.mappings[0] && (
                <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: isExcluded ? "var(--text-2)" : "var(--blue)", textDecoration: isExcluded ? "line-through" : undefined }}>
                  {c.mappings[0].column}
                </span>
              )}
            </div>

            {/* Concept bridge */}
            <div style={{ flex: "0 0 auto", padding: "0 4px", display: "flex", alignItems: "center" }}>
              <span style={{ width: 16, height: 1, background: "var(--blue)", opacity: isExcluded ? 0.15 : 0.3 }} />
              <span style={{
                padding: "4px 12px", background: isExcluded ? "var(--surface)" : "var(--blue-soft)", borderRadius: 16,
                border: `1px solid ${isExcluded ? "var(--border)" : "var(--blue)"}`, fontSize: 11, fontWeight: 700,
                color: isExcluded ? "var(--text-2)" : "var(--blue)", whiteSpace: "nowrap",
                display: "flex", flexDirection: "column", alignItems: "center", gap: 1,
              }}>
                {c.concept}
                {c.description && (
                  <span style={{ fontSize: 9, fontWeight: 400, color: "var(--text-2)", whiteSpace: "normal", textAlign: "center", maxWidth: 180 }}>
                    {c.description}
                  </span>
                )}
                {(tierLabel || confidence) && (
                  <span style={{ fontSize: 8, fontWeight: 400, color: "var(--text-2)", marginTop: 2 }}>
                    {tierLabel}{confidence ? ` (${confidence})` : ""}
                  </span>
                )}
              </span>
              <span style={{ width: 16, height: 1, background: "var(--blue)", opacity: isExcluded ? 0.15 : 0.3 }} />
            </div>

            {/* Right column name */}
            <div style={{ flex: 1, padding: "0 16px" }}>
              {c.mappings[1] && (
                <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: isExcluded ? "var(--text-2)" : "var(--blue)", textDecoration: isExcluded ? "line-through" : undefined }}>
                  {c.mappings[1].column}
                </span>
              )}
            </div>

            {/* Exclude toggle */}
            <button
              onClick={() => toggleExclude(i)}
              title={isExcluded ? "Re-include this concept" : "Exclude this concept"}
              style={{
                marginRight: 12, width: 22, height: 22, borderRadius: "50%",
                border: `1px solid ${isExcluded ? "var(--border)" : "var(--blue)"}`,
                background: isExcluded ? "var(--surface)" : "var(--blue-soft)",
                color: isExcluded ? "var(--text-2)" : "var(--blue)",
                cursor: "pointer", fontSize: 13, fontWeight: 700,
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                lineHeight: 1,
              }}
            >
              {isExcluded ? "+" : "×"}
            </button>
          </div>
        );
      })}

      {/* Join preview result */}
      {preview && (
        <div style={{
          margin: "0 16px 12px",
          padding: "10px 14px",
          borderRadius: 8,
          background: preview.row_count === 0 ? "var(--error-soft, #fff0f0)" : "var(--surface)",
          border: `1px solid ${preview.row_count === 0 ? "var(--error)" : preview.unmatched_count > 0 ? "var(--border-strong)" : "var(--border)"}`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: (preview.row_count > 0 || preview.warnings.length > 0) ? 8 : 0 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: preview.row_count === 0 ? "var(--error)" : preview.unmatched_count > 0 ? "var(--text)" : "var(--green, #22c55e)" }}>
              {preview.row_count === 0
                ? "⚠ 0 rows matched"
                : `✓ ${preview.row_count.toLocaleString()} rows matched${preview.unmatched_count > 0 ? ` (${preview.unmatched_count} unmatched)` : ""}`}
            </span>
          </div>
          {preview.warnings.map((w, i) => (
            <div key={i} style={{ fontSize: 12, color: "var(--error)", marginBottom: 6 }}>
              {w} — click × on the concept to exclude it, then preview again.
            </div>
          ))}
          {preview.row_count > 0 && preview.sample_rows.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "collapse", fontSize: 11, width: "100%" }}>
                <thead>
                  <tr>
                    {preview.sample_columns.map((c) => (
                      <th key={c} className="mono" style={{ padding: "4px 8px", borderBottom: "1px solid var(--border)", color: "var(--text-2)", fontWeight: 700, whiteSpace: "nowrap" }}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.sample_rows.map((row, i) => (
                    <tr key={i}>
                      {preview.sample_columns.map((c) => (
                        <td key={c} className="mono" style={{ padding: "4px 8px", borderBottom: "1px solid var(--border)", color: "var(--text)", whiteSpace: "nowrap" }}>
                          {row[c] == null ? "" : String(row[c])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <button
          className="pill-btn ghost"
          disabled={previewing || activeCount === 0}
          onClick={previewJoin}
          style={{ height: 36, fontSize: 13 }}
        >
          {previewing ? "Checking..." : "Preview join"}
        </button>
        <button
          className="pill-btn primary"
          disabled={confirming || activeCount === 0 || !preview || preview.row_count === 0}
          onClick={confirm}
          title={!preview ? "Preview the join first" : preview.row_count === 0 ? "Fix the join keys — 0 rows matched" : undefined}
          style={{ height: 36, fontSize: 13 }}
        >
          {confirming ? "Building L3..." : "Confirm and descend to L3"}
        </button>
        {error && <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>}
      </div>
    </div>
  );
}


function SourceCard({
  name, table, shape, defaultOpen,
}: {
  name: string; table: DecodedTable | null; shape?: string; defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [showAllRows, setShowAllRows] = useState(false);
  const [showAllCols, setShowAllCols] = useState(false);

  const cols = table ? (showAllCols ? table.columns : table.columns.slice(0, 8)) : [];
  const rows = table ? (showAllRows ? table.rows : table.rows.slice(0, 20)) : [];
  const hiddenCols = table ? table.columns.length - 8 : 0;

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex", alignItems: "center", gap: 10, padding: "12px 16px",
          width: "100%", border: "none", background: open ? "var(--surface)" : "transparent",
          cursor: "pointer", borderBottom: open ? "1px solid var(--border)" : "none", textAlign: "left",
        }}
      >
        <Icon name={open ? "down" : "arrowRight"} size={14} />
        <span className="mono" style={{ fontWeight: 600, fontSize: 13, color: "var(--blue)" }}>{name}</span>
        {table && (
          <span className="t-meta mono" style={{ fontSize: 12 }}>
            {table.rows.length} rows x {table.columns.length} cols
          </span>
        )}
        {shape && <span className="t-meta" style={{ fontSize: 12 }}>{shape}</span>}
      </button>

      {open && table && cols.length > 0 && (
        <>
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 480 }}>
              <thead>
                <tr>
                  {cols.map((c) => <th key={c} className="mono" style={thStyle}>{c}</th>)}
                  {!showAllCols && hiddenCols > 0 && (
                    <th className="mono" style={{ ...thStyle, color: "var(--border-strong)" }}>+{hiddenCols} ...</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className="rawrow">
                    {cols.map((c) => <td key={c} className="mono" style={tdStyle}>{formatCell(row[c])}</td>)}
                    {!showAllCols && hiddenCols > 0 && (
                      <td style={{ ...tdStyle, color: "var(--border-strong)" }}>...</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: "10px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {table.rows.length > 20 && (
              <button className="pill-btn ghost" style={{ height: 26, fontSize: 11 }} onClick={() => setShowAllRows((v) => !v)}>
                {showAllRows ? "Show first 20" : `Show all ${table.rows.length} rows`}
              </button>
            )}
            {hiddenCols > 0 && (
              <button className="pill-btn ghost" style={{ height: 26, fontSize: 11, marginLeft: "auto" }} onClick={() => setShowAllCols((v) => !v)}>
                {showAllCols ? "Show 8 columns" : `Show all ${table.columns.length} columns`}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}


const thStyle: React.CSSProperties = {
  textAlign: "left", padding: "9px 12px", fontSize: 12, fontWeight: 700,
  color: "var(--text-2)", borderBottom: "1px solid var(--border)", background: "var(--surface)",
  position: "sticky", top: 0, letterSpacing: "0.01em", whiteSpace: "nowrap",
};
const tdStyle: React.CSSProperties = {
  padding: "10px 12px", fontSize: 13, borderBottom: "1px solid var(--border)",
  color: "var(--text)", whiteSpace: "nowrap",
};

function formatCell(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  return String(value);
}

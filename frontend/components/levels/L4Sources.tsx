"use client";

import { useMemo, useState } from "react";
import type { NodeDetail } from "@/lib/api/types";
import { decodeDataframe, type DecodedTable } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

/*
 * L4 — the raw, unlinkable sources. Each source gets its own card with a
 * collapsible table preview. Multiple sources stack vertically so you can
 * see all your datasets at a glance.
 */
export function L4Sources({ node, onAddSource, sessionId }: { node: NodeDetail; onAddSource?: () => void; sessionId?: string }) {
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
      {/* summary header */}
      <div
        className="card"
        style={{
          padding: "14px 16px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexWrap: "wrap",
        }}
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

      {/* one card per source */}
      {sources.map((s) => (
        <SourceCard
          key={s.name}
          name={s.name}
          table={s.table}
          shape={shapes?.[s.name] != null ? String(shapes[s.name]) : undefined}
          defaultOpen={sources.length <= 2}
        />
      ))}

      {/* Entity matching panel — appears when 2+ sources */}
      {sources.length >= 2 && sessionId && (
        <EntityMatchPanel sources={sources} sessionId={sessionId} />
      )}

      {sources.length === 0 && (
        <div className="card" style={{ padding: 16 }}>
          <p className="t-meta">No source files yet — add one to begin.</p>
        </div>
      )}
    </div>
  );
}


interface Relationship {
  source_a: string;
  column_a: string;
  source_b: string;
  column_b: string;
}

interface MatchResult {
  catalog: Array<{ concept: string; description: string; mappings: Array<{ source: string; column: string; notes: string }> }>;
  join_plan: { strategy?: string; join_key?: string; confidence?: string; join_type?: string; transformations?: string[] };
  explanation: string;
  error?: string;
}

function EntityMatchPanel({
  sources,
  sessionId,
}: {
  sources: Array<{ name: string; table: DecodedTable | null }>;
  sessionId: string;
}) {
  const [open, setOpen] = useState(false);
  const [selA, setSelA] = useState(0);
  const [selB, setSelB] = useState(Math.min(1, (sources?.length ?? 1) - 1));
  const [colA, setColA] = useState("");
  const [colB, setColB] = useState("");
  const [pairs, setPairs] = useState<Relationship[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!sources || sources.length < 2) return null;

  const srcA = sources[selA];
  const srcB = sources[selB];
  const colsA = srcA?.table?.columns ?? [];
  const colsB = srcB?.table?.columns ?? [];

  function addPair() {
    if (!colA || !colB) return;
    setPairs((p) => [...p, { source_a: srcA.name, column_a: colA, source_b: srcB.name, column_b: colB }]);
    setColA("");
    setColB("");
  }

  function removePair(i: number) {
    setPairs((p) => p.filter((_, idx) => idx !== i));
  }

  async function runMatch() {
    if (!pairs.length) return;
    setBusy(true);
    setError(null);
    try {
      await apiPost(`/sessions/${sessionId}/entity-match`, { relationships: pairs });
      // The endpoint descends to L3 — reload the page to show the new state
      window.location.reload();
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        className="card"
        onClick={() => setOpen(true)}
        style={{
          padding: "14px 16px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          width: "100%",
          border: "1.5px dashed var(--blue)",
          background: "var(--blue-soft)",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <Icon name="graph" size={16} />
        <span style={{ fontWeight: 600, color: "var(--blue)" }}>
          Connect these sources — declare entity relationships
        </span>
        <span className="t-meta" style={{ marginLeft: "auto" }}>
          {sources.length} sources to match
        </span>
      </button>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", border: "1.5px solid var(--blue)" }}>
      {/* Header */}
      <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
        <Icon name="graph" size={16} />
        <span style={{ fontWeight: 700, fontSize: 14 }}>Entity Matching</span>
        <span className="t-meta">Declare which columns are deeply related across sources</span>
        <button className="pill-btn ghost" onClick={() => setOpen(false)} style={{ marginLeft: "auto", height: 26, fontSize: 11 }}>Close</button>
      </div>

      {/* Column pairing */}
      <div style={{ padding: 16, display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 150 }}>
          <label className="t-meta" style={{ display: "block", marginBottom: 4, fontSize: 11 }}>{srcA.name}</label>
          <select
            className="mono"
            value={colA}
            onChange={(e) => setColA(e.target.value)}
            style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid var(--border)", fontSize: 13 }}
          >
            <option value="">Select column…</option>
            {colsA.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", padding: "0 8px", color: "var(--blue)", fontWeight: 700, fontSize: 18 }}>↔</div>

        <div style={{ flex: 1, minWidth: 150 }}>
          <label className="t-meta" style={{ display: "block", marginBottom: 4, fontSize: 11 }}>{srcB.name}</label>
          <select
            className="mono"
            value={colB}
            onChange={(e) => setColB(e.target.value)}
            style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid var(--border)", fontSize: 13 }}
          >
            <option value="">Select column…</option>
            {colsB.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <button
          className="pill-btn primary"
          disabled={!colA || !colB}
          onClick={addPair}
          style={{ height: 36, fontSize: 12, flex: "none" }}
        >
          + Link
        </button>
      </div>

      {/* Declared pairs */}
      {pairs.length > 0 && (
        <div style={{ padding: "0 16px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
          {pairs.map((p, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px", background: "var(--blue-soft)", borderRadius: 6 }}>
              <span className="mono" style={{ fontSize: 12, color: "var(--blue)", fontWeight: 600 }}>
                {p.source_a.split(".")[0]}.{p.column_a}
              </span>
              <span style={{ color: "var(--blue)" }}>↔</span>
              <span className="mono" style={{ fontSize: 12, color: "var(--blue)", fontWeight: 600 }}>
                {p.source_b.split(".")[0]}.{p.column_b}
              </span>
              <button onClick={() => removePair(i)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--error)", fontSize: 14 }}>×</button>
            </div>
          ))}
        </div>
      )}

      {/* Action */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
        <button
          className="pill-btn primary"
          disabled={!pairs.length || busy}
          onClick={runMatch}
          style={{ height: 36, fontSize: 13 }}
        >
          {busy ? "Analyzing with LLM…" : `Match entities (${pairs.length} relationship${pairs.length === 1 ? "" : "s"})`}
        </button>
        {error && <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>}
      </div>

    </div>
  );
}


function SourceCard({
  name,
  table,
  shape,
  defaultOpen,
}: {
  name: string;
  table: DecodedTable | null;
  shape?: string;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [showAllRows, setShowAllRows] = useState(false);
  const [showAllCols, setShowAllCols] = useState(false);

  const cols = table ? (showAllCols ? table.columns : table.columns.slice(0, 8)) : [];
  const rows = table ? (showAllRows ? table.rows : table.rows.slice(0, 20)) : [];
  const hiddenCols = table ? table.columns.length - 8 : 0;

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {/* source header — always visible */}
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "12px 16px",
          width: "100%",
          border: "none",
          background: open ? "var(--surface)" : "transparent",
          cursor: "pointer",
          borderBottom: open ? "1px solid var(--border)" : "none",
          textAlign: "left",
        }}
      >
        <Icon name={open ? "down" : "arrowRight"} size={14} />
        <span className="mono" style={{ fontWeight: 600, fontSize: 13, color: "var(--blue)" }}>
          {name}
        </span>
        {table && (
          <span className="t-meta mono" style={{ fontSize: 12 }}>
            {table.rows.length} rows × {table.columns.length} cols
          </span>
        )}
        {shape && (
          <span className="t-meta" style={{ fontSize: 12 }}>
            {shape}
          </span>
        )}
      </button>

      {/* collapsible table preview */}
      {open && table && cols.length > 0 && (
        <>
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 480 }}>
              <thead>
                <tr>
                  {cols.map((c) => (
                    <th key={c} className="mono" style={thStyle}>
                      {c}
                    </th>
                  ))}
                  {!showAllCols && hiddenCols > 0 && (
                    <th className="mono" style={{ ...thStyle, color: "var(--border-strong)" }}>
                      +{hiddenCols} …
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className="rawrow">
                    {cols.map((c) => (
                      <td key={c} className="mono" style={tdStyle}>
                        {formatCell(row[c])}
                      </td>
                    ))}
                    {!showAllCols && hiddenCols > 0 && (
                      <td style={{ ...tdStyle, color: "var(--border-strong)" }}>…</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div
            style={{
              padding: "10px 16px",
              borderTop: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            {table.rows.length > 20 && (
              <button
                className="pill-btn ghost"
                style={{ height: 26, fontSize: 11, flex: "none" }}
                onClick={() => setShowAllRows((v) => !v)}
              >
                {showAllRows ? "Show first 20" : `Show all ${table.rows.length} rows`}
              </button>
            )}
            {hiddenCols > 0 && (
              <button
                className="pill-btn ghost"
                style={{ height: 26, fontSize: 11, flex: "none", marginLeft: "auto" }}
                onClick={() => setShowAllCols((v) => !v)}
              >
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
  textAlign: "left",
  padding: "9px 12px",
  fontSize: 12,
  fontWeight: 700,
  color: "var(--text-2)",
  borderBottom: "1px solid var(--border)",
  background: "var(--surface)",
  position: "sticky",
  top: 0,
  letterSpacing: "0.01em",
  whiteSpace: "nowrap",
};
const tdStyle: React.CSSProperties = {
  padding: "10px 12px",
  fontSize: 13,
  borderBottom: "1px solid var(--border)",
  color: "var(--text)",
  whiteSpace: "nowrap",
};

function formatCell(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  return String(value);
}

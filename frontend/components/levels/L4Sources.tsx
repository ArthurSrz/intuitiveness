"use client";

import { useMemo, useState } from "react";
import type { NodeDetail } from "@/lib/api/types";
import { decodeDataframe, type DecodedTable } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

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
        <ConnectSourcesButton sessionId={sessionId} />
      )}

      {sources.length === 0 && (
        <div className="card" style={{ padding: 16 }}>
          <p className="t-meta">No source files yet — add one to begin.</p>
        </div>
      )}
    </div>
  );
}


function ConnectSourcesButton({ sessionId }: { sessionId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      await apiPost(`/sessions/${sessionId}/entity-match`, { relationships: [] });
      window.location.reload();
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  return (
    <button
      className="card"
      onClick={connect}
      disabled={busy}
      style={{
        padding: "14px 16px",
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        border: "1.5px dashed var(--blue)",
        background: busy ? "var(--surface)" : "var(--blue-soft)",
        cursor: busy ? "wait" : "pointer",
        textAlign: "left",
      }}
    >
      <Icon name="graph" size={16} />
      <span style={{ fontWeight: 600, color: "var(--blue)" }}>
        {busy ? "Analyzing with LLM..." : "Connect these sources"}
      </span>
      {error && <span style={{ color: "var(--error)", fontSize: 12, marginLeft: "auto" }}>{error}</span>}
    </button>
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

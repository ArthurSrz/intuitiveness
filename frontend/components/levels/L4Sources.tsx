"use client";

import { useMemo } from "react";
import type { NodeDetail } from "@/lib/api/types";
import { decodeDataframe, type DecodedTable } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";

/*
 * L4 — the raw, unlinkable sources. The payload is a dict of
 * { <source name>: <dataframe encoding> }. We surface every source as a chip and
 * preview the first decodable table in the design's raw-table chrome, framing
 * the "full complexity you didn't ask for" that the descent strips away.
 */
export function L4Sources({ node }: { node: NodeDetail }) {
  const payload = node.payload;
  const sources = useMemo(() => {
    if (!payload || typeof payload !== "object") return [];
    return Object.entries(payload as Record<string, unknown>).map(([name, enc]) => ({
      name,
      table: typeof enc === "string" ? decodeDataframe(enc) : null,
    }));
  }, [payload]);

  const shapes = (node.summary?.shapes as Record<string, unknown> | undefined) ?? undefined;
  const primary = sources.find((s) => s.table) ?? sources[0];
  const table: DecodedTable | null = primary?.table ?? null;
  const previewCols = table ? table.columns.slice(0, 8) : [];
  const previewRows = table ? table.rows.slice(0, 12) : [];

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {/* header — sources as chips */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "14px 16px",
          borderBottom: "1px solid var(--border)",
          flexWrap: "wrap",
        }}
      >
        <span className="chip">
          <Icon name="dataset" size={15} />
          Raw sources
        </span>
        {sources.map((s) => (
          <span key={s.name} className="chip mono" style={{ whiteSpace: "nowrap" }}>
            {s.name}
            {shapes?.[s.name] != null && (
              <span className="t-meta" style={{ fontWeight: 400 }}>
                {String(shapes[s.name])}
              </span>
            )}
          </span>
        ))}
        <span className="t-meta mono" style={{ marginLeft: "auto" }}>
          {sources.length} source{sources.length === 1 ? "" : "s"}
        </span>
      </div>

      {/* preview of the primary source */}
      {table && previewCols.length > 0 ? (
        <>
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 480 }}>
              <thead>
                <tr>
                  {previewCols.map((c) => (
                    <th key={c} className="mono" style={thStyle}>
                      {c}
                    </th>
                  ))}
                  {table.columns.length > previewCols.length && (
                    <th className="mono" style={{ ...thStyle, color: "var(--border-strong)" }}>
                      +{table.columns.length - previewCols.length} …
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, i) => (
                  <tr key={i} className="rawrow">
                    {previewCols.map((c) => (
                      <td key={c} className="mono" style={tdStyle}>
                        {formatCell(row[c])}
                      </td>
                    ))}
                    {table.columns.length > previewCols.length && (
                      <td style={{ ...tdStyle, color: "var(--border-strong)" }}>…</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div
            style={{
              padding: "12px 16px",
              borderTop: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            <span className="t-meta mono">
              {primary.name} — {table.rows.length} rows × {table.columns.length} cols
            </span>
            {table.columns.length > previewCols.length && (
              <span
                className="chip"
                style={{ marginLeft: "auto", background: "var(--error-soft)", color: "var(--error)" }}
              >
                <Icon name="info" size={14} /> {table.columns.length - previewCols.length} columns
                you didn&apos;t ask for
              </span>
            )}
          </div>
        </>
      ) : (
        <div style={{ padding: 16 }}>
          {sources.length === 0 ? (
            <p className="t-meta">No source files reported.</p>
          ) : (
            <p className="t-meta">
              {sources.length} raw source{sources.length === 1 ? "" : "s"} ready — the descent
              begins by facing the full complexity.
            </p>
          )}
        </div>
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

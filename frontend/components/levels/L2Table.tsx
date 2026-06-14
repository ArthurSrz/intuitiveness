"use client";

import { useMemo } from "react";
import type { NodeDetail, SessionOptions, AscendMove } from "@/lib/api/types";
import { decodeDataframe, type DecodedTable } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";
import { EdgeControls, type EdgeParams } from "@/components/shell/EdgeControls";
import { SelectFeatureButton } from "./SelectFeatureButton";
import { LinkDomainsButton } from "./LinkDomainsButton";

interface InlineEdgeProps {
  edgeParams: EdgeParams;
  onEdgeChange: (patch: Partial<EdgeParams>) => void;
  options?: SessionOptions;
  ascendMove?: AscendMove;
  phase?: "descent" | "ascent";
}

/*
 * Tabular level view (kind "dataframe" = zlib+base64, inflated client-side with
 * pako). Rendered in the design's bordered table chrome with a header chip +
 * row count, and a graceful summary fallback if decoding fails. Used for the L2
 * categorized table and the L3 ascent "purpose-built dataset" (via `code`).
 */
export function L2Table({
  node,
  code = "L2",
  glyph = "categories",
  edgeProps,
  sessionId,
  onConfirm,
  phase,
  initialIntent,
}: {
  node: NodeDetail;
  code?: string;
  glyph?: string;
  edgeProps?: InlineEdgeProps;
  sessionId?: string;
  onConfirm?: () => void;
  phase?: "descent" | "ascent";
  initialIntent?: string;
}) {
  const table: DecodedTable | null = useMemo(() => {
    if (typeof node.payload === "string") {
      return decodeDataframe(node.payload);
    }
    return null;
  }, [node.payload]);

  if (!table) {
    return (
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <Header code={code} glyph={glyph} label="Categorized table" meta="" />
        <div style={{ padding: 16 }}>
          <SummaryFallback node={node} />
        </div>
      </div>
    );
  }

  const previewRows = table.rows.slice(0, 50);

  return (
    <>
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <Header
        code={code}
        glyph={glyph}
        label={node.decision_description ?? (code === "L3" ? "Purpose-built dataset" : "Categorized table")}
        meta={`${table.rows.length} rows · ${table.columns.length} cols`}
      />
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 480 }}>
          <thead>
            <tr>
              {table.columns.map((col) => {
                const cat = isCategory(col);
                return (
                  <th
                    key={col}
                    className="mono"
                    style={cat ? { ...thStyle, color: "var(--blue)" } : thStyle}
                  >
                    {col}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {previewRows.map((row, i) => (
              <tr key={i} className="rawrow">
                {table.columns.map((col) => {
                  const cat = isCategory(col);
                  return (
                    <td
                      key={col}
                      className="mono"
                      style={cat ? { ...tdStyle, color: "var(--blue)", fontWeight: 700 } : tdStyle}
                    >
                      {formatCell(row[col])}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.rows.length > previewRows.length && (
        <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
          <span className="t-meta mono">
            Showing first {previewRows.length} of {table.rows.length} rows
          </span>
        </div>
      )}
    </div>
    {sessionId && (
      <>
        {phase !== "ascent" && <SelectFeatureButton sessionId={sessionId} onConfirm={onConfirm} />}
        {phase !== "descent" && <LinkDomainsButton sessionId={sessionId} onConfirm={onConfirm} initialIntent={initialIntent} />}
      </>
    )}
    </>
  );
}

function Header({
  code,
  glyph,
  label,
  meta,
}: {
  code: string;
  glyph: string;
  label: string;
  meta: string;
}) {
  return (
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
        <Icon name={glyph} size={15} />
        {code} · Table
      </span>
      <span className="t-name" style={{ fontWeight: 700 }}>
        {label}
      </span>
      {meta && (
        <span className="t-meta mono" style={{ marginLeft: "auto" }}>
          {meta}
        </span>
      )}
    </div>
  );
}

function SummaryFallback({ node }: { node: NodeDetail }) {
  const summary = node.summary ?? node.output_snapshot;
  if (!summary) return <p className="t-meta">No table payload available.</p>;
  return (
    <pre
      className="mono"
      style={{
        overflowX: "auto",
        borderRadius: "var(--radius-md)",
        background: "var(--surface)",
        padding: 16,
        fontSize: 12,
        color: "var(--text)",
      }}
    >
      {JSON.stringify(summary, null, 2)}
    </pre>
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

/** The categorization column the L3→L2 step adds, highlighted in blue. */
function isCategory(col: string): boolean {
  return col === "category" || col === "domain";
}

function formatCell(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  return String(value);
}

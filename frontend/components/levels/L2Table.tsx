"use client";

import { useMemo } from "react";
import type { NodeDetail } from "@/lib/api/types";
import { decodeDataframe, type DecodedTable } from "@/lib/payload";
import { Card } from "@/components/ui/Card";

/*
 * L2 — A table (kind "dataframe" = zlib+base64). We inflate it client-side with
 * pako. If decoding fails or the payload is absent, we fall back to whatever
 * the summary/output_snapshot reports so the view still renders something.
 */
export function L2Table({ node }: { node: NodeDetail }) {
  const table: DecodedTable | null = useMemo(() => {
    if (typeof node.payload === "string") {
      return decodeDataframe(node.payload);
    }
    return null;
  }, [node.payload]);

  if (!table) {
    return (
      <Card title="L2 · Table" subtitle="Categorized table">
        <SummaryFallback node={node} />
      </Card>
    );
  }

  const previewRows = table.rows.slice(0, 50);

  return (
    <Card
      title="L2 · Table"
      subtitle={`${table.rows.length} rows × ${table.columns.length} columns`}
    >
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-surface-muted text-left">
              {table.columns.map((col) => (
                <th
                  key={col}
                  className="border-b border-border px-3 py-2 font-medium text-fg"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {previewRows.map((row, i) => (
              <tr key={i} className="even:bg-surface-muted">
                {table.columns.map((col) => (
                  <td
                    key={col}
                    className="border-b border-border px-3 py-2 font-mono text-xs text-fg"
                  >
                    {formatCell(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.rows.length > previewRows.length && (
        <p className="mt-3 text-xs text-fg-muted">
          Showing first {previewRows.length} of {table.rows.length} rows.
        </p>
      )}
    </Card>
  );
}

function SummaryFallback({ node }: { node: NodeDetail }) {
  const summary = node.summary ?? node.output_snapshot;
  if (!summary) {
    return <p className="text-sm text-fg-muted">No table payload available.</p>;
  }
  return (
    <pre className="overflow-x-auto rounded-md bg-surface-muted p-4 font-mono text-xs text-fg">
      {JSON.stringify(summary, null, 2)}
    </pre>
  );
}

function formatCell(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  return String(value);
}

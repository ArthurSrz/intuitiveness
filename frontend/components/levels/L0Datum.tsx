import type { NodeDetail } from "@/lib/api/types";
import { Card } from "@/components/ui/Card";

/*
 * L0 — A single datum. The value lives in `payload` (kind "value") and is
 * also mirrored on `summary.value`. We render it large and centered.
 */
export function L0Datum({ node }: { node: NodeDetail }) {
  const value =
    node.payload != null
      ? node.payload
      : (node.summary?.value as unknown);

  const display =
    value == null
      ? "—"
      : typeof value === "number"
        ? formatNumber(value)
        : String(value);

  return (
    <Card title="L0 · Datum" subtitle="The single aggregated value">
      <div className="flex flex-col items-center justify-center py-8">
        <span className="font-mono text-4xl font-semibold text-level-0">
          {display}
        </span>
        {node.decision_description && (
          <p className="mt-4 text-center text-sm text-fg-muted">
            {node.decision_description}
          </p>
        )}
      </div>
    </Card>
  );
}

function formatNumber(n: number): string {
  // Keep at most 2 decimals but drop trailing zeros.
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
}

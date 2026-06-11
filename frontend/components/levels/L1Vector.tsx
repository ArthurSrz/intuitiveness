import type { NodeDetail } from "@/lib/api/types";
import { decodeVector } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";
import { scoreColor, initials } from "@/lib/design";

/*
 * L1 — the feature vector: one scalar per entity. Rendered as the design's
 * bracketed bar row (each bar coloured along the neutral→blue gradient by its
 * value), driven by the live "vector" payload (a zlib+base64 split-orient
 * DataFrame, decoded in lib/payload).
 */
export function L1Vector({ node }: { node: NodeDetail }) {
  const entries = decodeVector(node.payload);
  const values = entries.map((e) => e.value);
  const max = values.length ? Math.max(...values) : 1;
  const min = values.length ? Math.min(...values) : 0;
  const metricLabel =
    (typeof node.summary?.metric_label === "string" && node.summary.metric_label) ||
    node.decision_description ||
    "Feature vector";

  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <span className="t-label">{metricLabel}</span>
        <span className="t-meta" style={{ marginLeft: "auto" }}>
          one scalar per entity · <span className="mono">{entries.length} dims</span>
        </span>
      </div>

      {entries.length === 0 ? (
        <p className="t-meta">No vector values to display.</p>
      ) : (
        <div style={{ display: "flex", alignItems: "stretch", gap: 6 }}>
          <Bracket side="left" />
          <div style={{ display: "flex", gap: 6, overflowX: "auto", flex: 1, padding: "2px 0" }}>
            {entries.map((e, i) => {
              const h = ((e.value - min) / (max - min || 1)) * 78 + 14;
              const col = scoreColor(e.value, min, max);
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 6,
                    minWidth: 44,
                  }}
                  title={`${e.label}: ${e.value}`}
                >
                  <div style={{ height: 96, display: "flex", alignItems: "flex-end" }}>
                    <div style={{ width: 30, height: h, borderRadius: 6, background: col }} />
                  </div>
                  <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: col }}>
                    {formatValue(e.value)}
                  </span>
                  <span className="mono" style={{ fontSize: 10, color: "var(--text-2)" }}>
                    {shortLabel(e.label, i)}
                  </span>
                </div>
              );
            })}
          </div>
          <Bracket side="right" />
        </div>
      )}
    </div>
  );
}

function Bracket({ side }: { side: "left" | "right" }) {
  return (
    <div
      style={{
        width: 14,
        borderTop: "3px solid var(--border-strong)",
        borderBottom: "3px solid var(--border-strong)",
        [side === "left" ? "borderLeft" : "borderRight"]: "3px solid var(--border-strong)",
        borderRadius: side === "left" ? "6px 0 0 6px" : "0 6px 6px 0",
      }}
    />
  );
}

/** A 2-char tag under each bar: entity initials, else a #index. */
function shortLabel(label: string, index: number): string {
  if (label === String(index)) return `#${index}`;
  const ini = initials(label);
  return ini || label.slice(0, 2).toUpperCase();
}

function formatValue(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

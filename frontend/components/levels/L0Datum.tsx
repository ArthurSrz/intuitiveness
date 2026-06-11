import type { NodeDetail } from "@/lib/api/types";
import { decodeValue } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";

/*
 * L0 — the core datum. The single aggregated value lives in `payload`
 * (kind "value", zlib+base64-encoded) and is mirrored on `summary.value`.
 * Rendered large, mono, and gently glowing — the floor of the descent.
 */
export function L0Datum({ node }: { node: NodeDetail }) {
  const decoded = decodeValue(node.payload);
  const value = decoded != null ? decoded : (node.summary?.value as unknown);
  const display =
    value == null ? "—" : typeof value === "number" ? formatNumber(value) : String(value);
  const unit = typeof node.summary?.unit === "string" ? (node.summary.unit as string) : "";

  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        padding: "44px 24px",
        gap: 6,
      }}
    >
      <span className="chip" style={{ marginBottom: 14 }}>
        <Icon name="core" size={14} />
        The core datum
      </span>
      <div style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
        <div
          className="mono"
          style={{
            fontSize: 104,
            fontWeight: 700,
            lineHeight: 1,
            letterSpacing: "-0.03em",
            color: "var(--ink)",
            animation: "countGlow 3.2s ease-in-out infinite",
          }}
        >
          {display}
          {unit && <span style={{ fontSize: 44, color: "var(--text-2)" }}>{unit}</span>}
        </div>
      </div>
      <div className="t-section" style={{ marginTop: 12 }}>
        {node.decision_description ?? "A single atomic value"}
      </div>
      <div className="t-meta" style={{ maxWidth: 360 }}>
        Every row, column, entity and category in the source dataset reduces to this one atomic
        value.
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 20, alignItems: "center" }}>
        <span className="chip mono">raw dataset</span>
        <Icon name="arrowRight" size={18} style={{ color: "var(--text-2)" }} />
        <span className="chip mono" style={{ background: "var(--blue)", color: "#fff" }}>
          1
        </span>
      </div>
    </div>
  );
}

function formatNumber(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
}

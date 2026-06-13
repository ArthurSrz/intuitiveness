"use client";

import { useEffect, useState } from "react";
import type { NodeDetail, SessionOptions, AscendMove } from "@/lib/api/types";
import { decodeValue } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";
import { EdgeControls, type EdgeParams } from "@/components/shell/EdgeControls";
import { EnrichButton } from "./EnrichButton";
import { apiPost } from "@/lib/api/client";

interface InlineEdgeProps {
  edgeParams: EdgeParams;
  onEdgeChange: (patch: Partial<EdgeParams>) => void;
  options?: SessionOptions;
  ascendMove?: AscendMove;
  phase?: "descent" | "ascent";
}

export function L0Datum({ node, edgeProps, sessionId, onConfirm }: { node: NodeDetail; edgeProps?: InlineEdgeProps; sessionId?: string; onConfirm?: () => void }) {
  const decoded = decodeValue(node.payload);
  const value = decoded != null ? decoded : (node.summary?.value as unknown);
  const display =
    value == null ? "—" : typeof value === "number" ? formatNumber(value) : String(value);
  const unit = typeof node.summary?.unit === "string" ? (node.summary.unit as string) : "";

  const [aiTitle, setAiTitle] = useState<string | null>(null);
  const [aiDesc, setAiDesc] = useState<string | null>(null);
  const [descFetched, setDescFetched] = useState(false);

  useEffect(() => {
    if (!sessionId || descFetched) return;
    setDescFetched(true);
    apiPost<{ title: string; description: string }>(`/sessions/${sessionId}/datum-describe`, {})
      .then((res) => {
        if (res.title) setAiTitle(res.title);
        if (res.description) setAiDesc(res.description);
      })
      .catch(() => setDescFetched(false));
  }, [sessionId, descFetched]);

  const aggregation = (node.summary?.aggregation_method as string) || "";
  const parentName = (node.summary?.parent_name as string) || "";

  return (
    <>
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
        Atomic certainty
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
      <div className="t-section" style={{ marginTop: 12, fontSize: 16 }}>
        {aiTitle || "The single truth underneath all the data"}
      </div>
      <div className="t-meta" style={{ maxWidth: 420, lineHeight: 1.5 }}>
        {aiDesc
          ? aiDesc
          : aggregation && parentName
            ? `Computed as the ${aggregation} of "${parentName}" — every row, column, entity and category traded away to reach this one certain value.`
            : "Every row, column, entity and category in the source dataset reduces to this one atomic value. The descent is complete."}
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 20, alignItems: "center" }}>
        <span className="chip mono">heterogeneous sources</span>
        <Icon name="arrowRight" size={14} style={{ color: "var(--text-2)" }} />
        <span className="chip mono">graph</span>
        <Icon name="arrowRight" size={14} style={{ color: "var(--text-2)" }} />
        <span className="chip mono">domain</span>
        <Icon name="arrowRight" size={14} style={{ color: "var(--text-2)" }} />
        <span className="chip mono">vector</span>
        <Icon name="arrowRight" size={14} style={{ color: "var(--text-2)" }} />
        <span className="chip mono" style={{ background: "var(--blue)", color: "#fff" }}>
          {display}
        </span>
      </div>
    </div>
    {sessionId && (
      <EnrichButton sessionId={sessionId} onConfirm={onConfirm} />
    )}
    </>
  );
}

function formatNumber(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
}

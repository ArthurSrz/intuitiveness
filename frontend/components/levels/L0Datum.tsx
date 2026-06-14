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

export function L0Datum({ node, edgeProps, sessionId, onConfirm, phase, initialIntent }: { node: NodeDetail; edgeProps?: InlineEdgeProps; sessionId?: string; onConfirm?: () => void; phase?: "descent" | "ascent"; initialIntent?: string }) {
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
        Your summary number
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
        {aiTitle || "One number that captures the big picture"}
      </div>
      <div className="t-meta" style={{ maxWidth: 420, lineHeight: 1.5 }}>
        {aiDesc
          ? aiDesc
          : aggregation && parentName
            ? `Calculated as the ${aggregation} of "${parentName}" across all rows in your data.`
            : "All your data has been simplified down to this single number. You can now use it as a starting point to explore further."}
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 20, alignItems: "center", flexWrap: "wrap" }}>
        <span className="chip mono">raw files</span>
        <Icon name="arrowRight" size={14} style={{ color: "var(--text-2)" }} />
        <span className="chip mono">connected</span>
        <Icon name="arrowRight" size={14} style={{ color: "var(--text-2)" }} />
        <span className="chip mono">grouped</span>
        <Icon name="arrowRight" size={14} style={{ color: "var(--text-2)" }} />
        <span className="chip mono">one value per item</span>
        <Icon name="arrowRight" size={14} style={{ color: "var(--text-2)" }} />
        <span className="chip mono" style={{ background: "var(--blue)", color: "#fff" }}>
          {display}
        </span>
      </div>
    </div>
    {sessionId && phase === "ascent" && !initialIntent && (
      <div
        className="card"
        style={{
          padding: "16px 20px",
          background: "var(--blue-soft)",
          border: "1.5px solid var(--blue)",
          borderRadius: "var(--radius-md)",
          marginBottom: 8,
        }}
      >
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: "var(--text)" }}>
          <strong style={{ color: "var(--blue)" }}>What happens now?</strong>{" "}
          You have found your key number. Now let us rebuild the data around a question <em>you</em> care about.
          Instead of simplifying, we will add detail back — but only what is relevant to your question.
        </p>
      </div>
    )}
    {sessionId && (
      <EnrichButton sessionId={sessionId} onConfirm={onConfirm} initialIntent={initialIntent} />
    )}
    </>
  );
}

function formatNumber(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
}

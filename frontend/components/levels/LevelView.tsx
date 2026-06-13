"use client";

import dynamic from "next/dynamic";
import type { NodeDetail, SessionOptions, AscendMove } from "@/lib/api/types";
import type { EdgeParams } from "@/components/shell/EdgeControls";
import { L4Sources } from "./L4Sources";
import { L2Table } from "./L2Table";
import { L1Vector } from "./L1Vector";
import { L0Datum } from "./L0Datum";

const L3Graph = dynamic(() => import("./L3Graph").then((m) => m.L3Graph), {
  loading: () => (
    <div className="rounded-lg border border-border bg-surface p-5 text-sm text-fg-muted shadow-sm">
      Loading graph…
    </div>
  ),
  ssr: false,
});

export interface LevelViewProps {
  node?: NodeDetail;
  level?: number;
  onAddSource?: () => void;
  sessionId?: string;
  onConnect?: () => void;
  edgeParams?: EdgeParams;
  onEdgeChange?: (patch: Partial<EdgeParams>) => void;
  options?: SessionOptions;
  ascendMove?: AscendMove;
  phase?: "descent" | "ascent";
}

export function LevelView({
  node, level, onAddSource, sessionId, onConnect,
  edgeParams, onEdgeChange, options, ascendMove, phase,
}: LevelViewProps) {
  if (!node) {
    return (
      <div className="rounded-lg border border-border bg-surface p-5 text-sm text-fg-muted shadow-sm">
        Loading level view…
      </div>
    );
  }

  const resolved = node.level ?? level;
  const edgeProps = edgeParams && onEdgeChange
    ? { edgeParams, onEdgeChange, options, ascendMove, phase }
    : undefined;

  switch (resolved) {
    case 4:
      return <L4Sources node={node} onAddSource={onAddSource} sessionId={sessionId} onConnect={onConnect} />;
    case 3:
      return node.payload_kind === "dataframe" ? (
        <L2Table node={node} code="L3" glyph="graph" />
      ) : (
        <L3Graph node={node} sessionId={sessionId} onConfirm={onConnect} />
      );
    case 2:
      return <L2Table node={node} edgeProps={edgeProps} sessionId={sessionId} onConfirm={onConnect} />;
    case 1:
      return <L1Vector node={node} edgeProps={edgeProps} sessionId={sessionId} onConfirm={onConnect} />;
    case 0:
      return <L0Datum node={node} edgeProps={edgeProps} sessionId={sessionId} onConfirm={onConnect} />;
    default:
      return (
        <div className="rounded-lg border border-border bg-surface p-5 text-sm text-fg-muted shadow-sm">
          Unknown level: {String(resolved)}
        </div>
      );
  }
}

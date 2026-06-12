"use client";

import type { NodeDetail } from "@/lib/api/types";
import { L4Sources } from "./L4Sources";
import { L3Graph } from "./L3Graph";
import { L2Table } from "./L2Table";
import { L1Vector } from "./L1Vector";
import { L0Datum } from "./L0Datum";

/*
 * Picks the right level component for a node by its abstraction level.
 * `level` may come from the node record or be passed explicitly when the
 * detail is still loading.
 */
export function LevelView({
  node,
  level,
  onAddSource,
}: {
  node?: NodeDetail;
  level?: number;
  onAddSource?: () => void;
}) {
  if (!node) {
    return (
      <div className="rounded-lg border border-border bg-surface p-5 text-sm text-fg-muted shadow-sm">
        Loading level view…
      </div>
    );
  }

  const resolved = node.level ?? level;
  switch (resolved) {
    case 4:
      return <L4Sources node={node} onAddSource={onAddSource} />;
    case 3:
      // Descent L3 is a graph; the L2→L3 ascent rebuilds a dataframe (the
      // "purpose-built dataset"), so render that as a table.
      return node.payload_kind === "dataframe" ? (
        <L2Table node={node} code="L3" glyph="graph" />
      ) : (
        <L3Graph node={node} />
      );
    case 2:
      return <L2Table node={node} />;
    case 1:
      return <L1Vector node={node} />;
    case 0:
      return <L0Datum node={node} />;
    default:
      return (
        <div className="rounded-lg border border-border bg-surface p-5 text-sm text-fg-muted shadow-sm">
          Unknown level: {String(resolved)}
        </div>
      );
  }
}

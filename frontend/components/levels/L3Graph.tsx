"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphPayload, NodeDetail } from "@/lib/api/types";
import { Card } from "@/components/ui/Card";

/*
 * L3 — A graph (kind "graph" = NetworkX node-link JSON). We decode the
 * { nodes, links } payload into reactflow nodes/edges and lay them out on a
 * simple grid (the backend doesn't ship coordinates).
 */
export function L3Graph({ node }: { node: NodeDetail }) {
  const { nodes, edges } = useMemo(
    () => toFlowGraph(node.payload),
    [node.payload],
  );

  if (nodes.length === 0) {
    return (
      <Card title="L3 · Graph" subtitle="Entity / relationship graph">
        <p className="text-sm text-fg-muted">No graph payload available.</p>
      </Card>
    );
  }

  return (
    <Card
      title="L3 · Graph"
      subtitle={`${nodes.length} nodes · ${edges.length} edges`}
    >
      <div className="h-96 overflow-hidden rounded-md border border-border">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          proOptions={{ hideAttribution: true }}
          nodesDraggable
          nodesConnectable={false}
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </Card>
  );
}

/** Decode a node-link payload into reactflow's { nodes, edges }. */
function toFlowGraph(payload: unknown): { nodes: Node[]; edges: Edge[] } {
  if (!isGraphPayload(payload)) {
    return { nodes: [], edges: [] };
  }

  // Grid layout — sqrt columns so the graph stays roughly square.
  const cols = Math.max(1, Math.ceil(Math.sqrt(payload.nodes.length)));
  const gapX = 180;
  const gapY = 110;

  const nodes: Node[] = payload.nodes.map((n, i) => ({
    id: String(n.id),
    position: { x: (i % cols) * gapX, y: Math.floor(i / cols) * gapY },
    data: { label: labelForNode(n) },
    style: {
      // Tokens flow through CSS vars so reactflow inline styles stay themed.
      background: "var(--color-surface)",
      color: "var(--color-fg)",
      border: "1px solid var(--color-level-3)",
      borderRadius: "var(--radius-md)",
      fontSize: "var(--text-xs)",
      padding: "var(--space-2)",
    },
  }));

  const edges: Edge[] = payload.links.map((link, i) => ({
    id: `e-${i}`,
    source: String(link.source),
    target: String(link.target),
    label: link.type ? String(link.type) : undefined,
    style: { stroke: "var(--color-border)" },
  }));

  return { nodes, edges };
}

function labelForNode(n: Record<string, unknown>): string {
  if (n.label != null) return String(n.label);
  if (n.name != null) return String(n.name);
  return String(n.id);
}

function isGraphPayload(payload: unknown): payload is GraphPayload {
  return (
    typeof payload === "object" &&
    payload !== null &&
    Array.isArray((payload as GraphPayload).nodes) &&
    Array.isArray((payload as GraphPayload).links)
  );
}

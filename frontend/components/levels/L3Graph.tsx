"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { NodeDetail } from "@/lib/api/types";
import { decodeGraph } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";

/*
 * L3 — the entity graph (kind "graph" = NetworkX node-link JSON). We decode the
 * { nodes, links } payload into reactflow nodes/edges laid out on a grid, and
 * dress it in the Blue Pulse chrome: a header chip, a circular themed node
 * style, and a relationship legend footer.
 */
export function L3Graph({ node }: { node: NodeDetail }) {
  const { nodes, edges } = useMemo(() => toFlowGraph(node.payload), [node.payload]);

  return (
    <div className="card" style={{ padding: 12 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "4px 6px 12px",
          flexWrap: "wrap",
        }}
      >
        <span className="chip">
          <Icon name="graph" size={15} />
          L3 · Graph
        </span>
        <span className="t-name" style={{ fontWeight: 700 }}>
          {node.decision_description ?? "Entity / relationship graph"}
        </span>
      </div>

      {nodes.length === 0 ? (
        <p className="t-meta" style={{ padding: "0 6px 8px" }}>
          No graph payload available.
        </p>
      ) : (
        <>
          <div
            style={{
              height: 420,
              overflow: "hidden",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--border)",
              background: "var(--surface)",
            }}
          >
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              proOptions={{ hideAttribution: true }}
              nodesDraggable
              nodesConnectable={false}
            >
              <Background color="var(--border-strong)" gap={22} />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
          <div
            style={{
              display: "flex",
              gap: 16,
              alignItems: "center",
              flexWrap: "wrap",
              padding: "12px 6px 4px",
              borderTop: "1px solid var(--border)",
              marginTop: 10,
            }}
          >
            <span className="t-label">Relationship</span>
            <span className="t-meta">
              nodes → <b style={{ color: "var(--text)" }}>entities</b>
            </span>
            <span className="t-meta">
              links → <b style={{ color: "var(--blue)" }}>relationships</b>
            </span>
            <span className="t-meta" style={{ marginLeft: "auto" }}>
              <span className="mono">{nodes.length}</span> entities ·{" "}
              <span className="mono">{edges.length}</span> links
            </span>
          </div>
        </>
      )}
    </div>
  );
}

/** Decode a node-link payload (zlib+base64 or object) into reactflow nodes/edges. */
function toFlowGraph(payload: unknown): { nodes: Node[]; edges: Edge[] } {
  const graph = decodeGraph(payload);
  if (!graph || graph.nodes.length === 0) return { nodes: [], edges: [] };

  const cols = Math.max(1, Math.ceil(Math.sqrt(graph.nodes.length)));
  const gapX = 170;
  const gapY = 120;

  const nodes: Node[] = graph.nodes.map((n, i) => ({
    id: String(n.id),
    position: { x: (i % cols) * gapX, y: Math.floor(i / cols) * gapY },
    data: { label: labelForNode(n) },
    style: {
      background: "var(--blue)",
      color: "#fff",
      border: "2px solid var(--bg)",
      borderRadius: "var(--pill)",
      fontSize: 11,
      fontWeight: 700,
      width: 64,
      height: 64,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      padding: 4,
      boxShadow: "var(--shadow-1)",
    },
  }));

  const edges: Edge[] = graph.links.map((link, i) => ({
    id: `e-${i}`,
    source: String(link.source),
    target: String(link.target),
    label: link.type ? String(link.type) : undefined,
    style: { stroke: "var(--border-strong)" },
  }));

  return { nodes, edges };
}

function labelForNode(n: Record<string, unknown>): string {
  if (n.label != null) return truncate(String(n.label));
  if (n.name != null) return truncate(String(n.name));
  return truncate(String(n.id));
}

function truncate(s: string): string {
  return s.length > 12 ? s.slice(0, 11) + "…" : s;
}

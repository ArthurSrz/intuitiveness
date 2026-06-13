"use client";

import { useMemo, useState } from "react";
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

export function L3Graph({ node }: { node: NodeDetail }) {
  const graph = useMemo(() => decodeGraph(node.payload), [node.payload]);
  const isSchema = useMemo(
    () => graph?.nodes.some((n) => n.node_type === "concept") ?? false,
    [graph],
  );

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="card" style={{ padding: 12 }}>
        <span className="chip"><Icon name="graph" size={15} /> L3 · Graph</span>
        <p className="t-meta" style={{ padding: "8px 6px" }}>No graph payload available.</p>
      </div>
    );
  }

  if (isSchema) return <SchemaView graph={graph} node={node} />;
  return <EntityGraph graph={graph} node={node} />;
}


/* ─────────────────────────────────────────────────────────────────────── */
/* Schema View — metadata catalog with source cards + concept bridges     */
/* ─────────────────────────────────────────────────────────────────────── */

interface GraphNode { id: string; [k: string]: unknown }
interface GraphLink { source: string; target: string; type?: string; [k: string]: unknown }
interface DecodedGraph { nodes: GraphNode[]; links: GraphLink[] }

function SchemaView({ graph, node: detail }: { graph: DecodedGraph; node: NodeDetail }) {
  const { sources, concepts, mappings } = useMemo(() => {
    const sources: Array<{ id: string; rows?: number; columns: Array<{ id: string; col: string; notes: string }> }> = [];
    const concepts: Array<{ id: string; description: string }> = [];
    const mappings: Array<{ concept: string; colId: string; transform: string }> = [];

    for (const n of graph.nodes) {
      if (n.node_type === "source") {
        sources.push({
          id: String(n.id),
          rows: n.rows as number | undefined,
          columns: [],
        });
      } else if (n.node_type === "concept") {
        concepts.push({ id: String(n.id), description: String(n.description ?? "") });
      }
    }

    // Collect columns under their source
    for (const n of graph.nodes) {
      if (n.node_type === "column") {
        const src = sources.find((s) => s.id === n.source);
        if (src) {
          src.columns.push({ id: String(n.id), col: String(n.column ?? n.id), notes: String(n.notes ?? "") });
        }
      }
    }

    // Collect concept → column mappings from edges
    for (const e of graph.links) {
      if (e.relationship === "maps_to" || e.type === "maps_to") {
        mappings.push({ concept: String(e.source), colId: String(e.target), transform: String(e.transform ?? "") });
      }
    }

    return { sources, concepts, mappings };
  }, [graph]);

  // Build concept bridges: for each concept, find the columns it connects
  const bridges = useMemo(() => {
    return concepts.map((c) => {
      const cols = mappings.filter((m) => m.concept === c.id);
      return { ...c, columns: cols };
    }).filter((b) => b.columns.length > 0);
  }, [concepts, mappings]);

  // Connected column IDs (for dimming unconnected ones)
  const connectedIds = useMemo(
    () => new Set(mappings.map((m) => m.colId)),
    [mappings],
  );

  const leftName = sources[0] ? sources[0].id.replace(/\.csv$/i, "").replace(/_/g, " ") : "";
  const rightName = sources[1] ? sources[1].id.replace(/\.csv$/i, "").replace(/_/g, " ") : "";
  const leftUnmatched = sources[0]?.columns.filter((c) => !connectedIds.has(c.id)) ?? [];
  const rightUnmatched = sources[1]?.columns.filter((c) => !connectedIds.has(c.id)) ?? [];
  const [showLeftExtra, setShowLeftExtra] = useState(false);
  const [showRightExtra, setShowRightExtra] = useState(false);

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
        <span className="chip"><Icon name="graph" size={15} /> L3 · Schema</span>
        <span className="t-meta" style={{ marginLeft: "auto" }}>
          {sources.length} sources · {concepts.length} concepts · {mappings.length} mappings
        </span>
      </div>

      {/* Source headers row */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
        <div style={{ flex: 1, padding: "10px 16px", borderRight: "1px solid var(--border)" }}>
          <div style={{ fontWeight: 700, fontSize: 13 }}>{leftName}</div>
          {sources[0]?.rows != null && <span className="t-meta mono" style={{ fontSize: 11 }}>{sources[0].rows} rows</span>}
        </div>
        <div style={{ flex: "0 0 40px" }} />
        <div style={{ flex: 1, padding: "10px 16px", textAlign: "right", borderLeft: "1px solid var(--border)" }}>
          <div style={{ fontWeight: 700, fontSize: 13 }}>{rightName}</div>
          {sources[1]?.rows != null && <span className="t-meta mono" style={{ fontSize: 11 }}>{sources[1].rows} rows</span>}
        </div>
      </div>

      {/* Bridge rows — one per concept */}
      {bridges.map((b) => {
        const leftCol = b.columns.find((c) => sources[0]?.columns.some((sc) => sc.id === c.colId));
        const rightCol = b.columns.find((c) => sources[1]?.columns.some((sc) => sc.id === c.colId));
        return (
          <div key={b.id} style={{
            display: "flex", alignItems: "center",
            borderBottom: "1px solid var(--border)", padding: "8px 0",
          }}>
            <div style={{ flex: 1, padding: "0 16px", textAlign: "right" }}>
              {leftCol && (
                <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--blue)" }}>
                  {leftCol.colId.split(":")[1]}
                </span>
              )}
            </div>
            <div style={{ flex: "0 0 auto", display: "flex", alignItems: "center", gap: 0, padding: "0 4px" }}>
              <span style={{ width: 20, height: 1, background: "var(--blue)", opacity: 0.3 }} />
              <span style={{
                padding: "4px 12px", background: "var(--blue-soft)", borderRadius: 16,
                border: "1px solid var(--blue)", fontSize: 11, fontWeight: 700,
                color: "var(--blue)", whiteSpace: "nowrap",
                display: "flex", flexDirection: "column", alignItems: "center", gap: 1,
              }}>
                {b.id}
                {b.description && (
                  <span style={{ fontSize: 9, fontWeight: 400, color: "var(--text-2)", whiteSpace: "normal", textAlign: "center", maxWidth: 160 }}>
                    {b.description}
                  </span>
                )}
              </span>
              <span style={{ width: 20, height: 1, background: "var(--blue)", opacity: 0.3 }} />
            </div>
            <div style={{ flex: 1, padding: "0 16px" }}>
              {rightCol && (
                <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--blue)" }}>
                  {rightCol.colId.split(":")[1]}
                </span>
              )}
            </div>
          </div>
        );
      })}

      {/* Unmatched columns footer */}
      <div style={{ display: "flex", padding: "8px 0", background: "var(--surface)" }}>
        <div style={{ flex: 1, padding: "0 16px" }}>
          {leftUnmatched.length > 0 && (
            <>
              <button onClick={() => setShowLeftExtra((v) => !v)} style={{
                background: "none", border: "none", cursor: "pointer", fontSize: 11,
                color: "var(--text-2)", padding: 0,
              }}>
                {showLeftExtra ? "Hide" : `+${leftUnmatched.length} unmatched columns`}
              </button>
              {showLeftExtra && (
                <div style={{ marginTop: 4 }}>
                  {leftUnmatched.map((c) => (
                    <div key={c.id} className="mono" style={{ fontSize: 11, color: "var(--text-2)", padding: "1px 0" }}>
                      {c.col}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
        <div style={{ flex: "0 0 40px" }} />
        <div style={{ flex: 1, padding: "0 16px", textAlign: "right" }}>
          {rightUnmatched.length > 0 && (
            <>
              <button onClick={() => setShowRightExtra((v) => !v)} style={{
                background: "none", border: "none", cursor: "pointer", fontSize: 11,
                color: "var(--text-2)", padding: 0,
              }}>
                {showRightExtra ? "Hide" : `+${rightUnmatched.length} unmatched columns`}
              </button>
              {showRightExtra && (
                <div style={{ marginTop: 4 }}>
                  {rightUnmatched.map((c) => (
                    <div key={c.id} className="mono" style={{ fontSize: 11, color: "var(--text-2)", padding: "1px 0" }}>
                      {c.col}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function SourceCard({
  source,
  connectedIds,
  side,
}: {
  source: { id: string; rows?: number; columns: Array<{ id: string; col: string; notes: string }> };
  connectedIds: Set<string>;
  side: "left" | "right";
}) {
  const [showAll, setShowAll] = useState(false);
  const matched = source.columns.filter((c) => connectedIds.has(c.id));
  const unmatched = source.columns.filter((c) => !connectedIds.has(c.id));
  const displayName = source.id.replace(/\.csv$/i, "").replace(/_/g, " ");

  return (
    <div style={{
      flex: 1, minWidth: 180, border: "1px solid var(--border)", borderRadius: 10,
      overflow: "hidden", background: "white",
    }}>
      <div style={{
        padding: "10px 14px", background: "var(--surface)",
        borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <Icon name="dataset" size={14} />
        <span style={{ fontWeight: 700, fontSize: 13 }}>{displayName}</span>
        {source.rows != null && (
          <span className="t-meta mono" style={{ fontSize: 11, marginLeft: "auto" }}>
            {source.rows} rows
          </span>
        )}
      </div>

      <div style={{ padding: "4px 0" }}>
        {matched.map((c) => (
          <div
            key={c.id}
            style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "5px 14px",
              background: "var(--blue-soft)",
              flexDirection: side === "right" ? "row-reverse" : "row",
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: "50%", flex: "none", background: "var(--blue)" }} />
            <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: "var(--blue)" }}>
              {c.col}
            </span>
          </div>
        ))}

        {showAll && unmatched.map((c) => (
          <div
            key={c.id}
            style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "3px 14px",
              flexDirection: side === "right" ? "row-reverse" : "row",
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", flex: "none", background: "var(--border)" }} />
            <span className="mono" style={{ fontSize: 11, color: "var(--text-2)" }}>
              {c.col}
            </span>
          </div>
        ))}

        {unmatched.length > 0 && (
          <button
            onClick={() => setShowAll((v) => !v)}
            style={{
              display: "block", width: "100%", padding: "6px 14px",
              background: "none", border: "none", cursor: "pointer",
              fontSize: 11, color: "var(--text-2)",
              textAlign: side === "right" ? "right" : "left",
            }}
          >
            {showAll ? "Hide" : `+${unmatched.length} more columns`}
          </button>
        )}
      </div>
    </div>
  );
}


/* ─────────────────────────────────────────────────────────────────────── */
/* Entity Graph — generic ReactFlow view (rows_as_nodes, bipartite, etc) */
/* ─────────────────────────────────────────────────────────────────────── */

function EntityGraph({ graph, node: detail }: { graph: DecodedGraph; node: NodeDetail }) {
  const { nodes, edges } = useMemo(() => {
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
        textAlign: "center" as const,
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
  }, [graph]);

  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 6px 12px", flexWrap: "wrap" }}>
        <span className="chip"><Icon name="graph" size={15} /> L3 · Graph</span>
        <span className="t-name" style={{ fontWeight: 700 }}>
          {detail.decision_description ?? "Entity / relationship graph"}
        </span>
      </div>
      <div style={{ height: 420, overflow: "hidden", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface)" }}>
        <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }} nodesDraggable nodesConnectable={false}>
          <Background color="var(--border-strong)" gap={22} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap", padding: "12px 6px 4px", borderTop: "1px solid var(--border)", marginTop: 10 }}>
        <span className="t-label">Relationship</span>
        <span className="t-meta">nodes → <b style={{ color: "var(--text)" }}>entities</b></span>
        <span className="t-meta">links → <b style={{ color: "var(--blue)" }}>relationships</b></span>
        <span className="t-meta" style={{ marginLeft: "auto" }}>
          <span className="mono">{nodes.length}</span> entities · <span className="mono">{edges.length}</span> links
        </span>
      </div>
    </div>
  );
}

function labelForNode(n: Record<string, unknown>): string {
  if (n.label != null) return truncate(String(n.label));
  if (n.name != null) return truncate(String(n.name));
  return truncate(String(n.id));
}

function truncate(s: string): string {
  return s.length > 12 ? s.slice(0, 11) + "…" : s;
}

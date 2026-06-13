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
import { decodeGraph, decodeGraphFull } from "@/lib/payload";
import { Icon } from "@/components/ui/Icon";
import { MapDomainsButton } from "./MapDomainsButton";

export function L3Graph({ node, sessionId, onConfirm }: { node: NodeDetail; sessionId?: string; onConfirm?: () => void }) {
  const decoded = useMemo(() => decodeGraphFull(node.payload), [node.payload]);
  const graph = decoded?.graph ?? null;
  const graphAttrs = decoded?.attrs ?? {};

  const isSchema = useMemo(
    () => graph?.nodes.some((n) => n.node_type === "concept") ?? false,
    [graph],
  );

  const hasCatalog = !!graphAttrs._catalog;
  const isRowData = useMemo(() => {
    if (!graph || graph.nodes.length === 0) return false;
    const attrCount = Object.keys(graph.nodes[0]).filter((k) => k !== "id").length;
    return attrCount > 3;
  }, [graph]);

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="card" style={{ padding: 12 }}>
        <span className="chip"><Icon name="graph" size={15} /> L3 · Graph</span>
        <p className="t-meta" style={{ padding: "8px 6px" }}>No graph payload available.</p>
      </div>
    );
  }

  const view = isSchema
    ? <SchemaView graph={graph} node={node} />
    : isRowData && hasCatalog
      ? <ReconciliatedView graph={graph} node={node} graphAttrs={graphAttrs} />
      : <EntityGraph graph={graph} node={node} />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {view}
      {sessionId && (
        <MapDomainsButton sessionId={sessionId} onConfirm={onConfirm} />
      )}
    </div>
  );
}


/* ─────────────────────────────────────────────────────────────────────── */
/* Schema View — metadata catalog with source cards + concept bridges     */
/* ─────────────────────────────────────────────────────────────────────── */

interface GraphNode { id: string | number; [k: string]: unknown }
interface GraphLink { source: string | number; target: string | number; type?: string; [k: string]: unknown }
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
/* Multi-Level Pivot Table — paper's L3 = shared keys × source attributes */
/* ─────────────────────────────────────────────────────────────────────── */

type CatalogEntry = { concept: string; description: string; mappings: Array<{ source: string; column: string }> };

function MultiLevelTable({
  table,
  sourceNames,
  catalog,
  colSources,
  showAllRows,
  setShowAllRows,
}: {
  table: { columns: string[]; rows: Record<string, unknown>[] };
  sourceNames: string[];
  catalog: CatalogEntry[];
  colSources: Record<string, string>; // column → short source name (from backend)
  showAllRows: boolean;
  setShowAllRows: (v: boolean) => void;
}) {
  const INTERNAL_COLS = new Set(["id", "index", "_id", "_index", "_source"]);

  // Identify shared key columns: catalog entries with mappings covering 2+ sources
  const sharedKeyCols = useMemo(() => {
    const keys = new Set<string>();
    for (const entry of catalog) {
      for (const m of entry.mappings) {
        if (table.columns.includes(m.column)) keys.add(m.column);
      }
    }
    return Array.from(keys);
  }, [catalog, table.columns]);

  // Group columns by source using the explicit backend mapping (fully generic)
  const sourceColGroups = useMemo(() => {
    const groups: Record<string, string[]> = {};
    for (const col of table.columns) {
      if (sharedKeyCols.includes(col) || INTERNAL_COLS.has(col)) continue;
      const src = colSources[col] ?? "other";
      if (!groups[src]) groups[src] = [];
      groups[src].push(col);
    }
    return groups;
  }, [colSources, sharedKeyCols, table.columns]);

  const allSourceGroups = Object.entries(sourceColGroups).filter(([, cols]) => cols.length > 0);
  const displayRows = showAllRows ? table.rows : table.rows.slice(0, 50);
  const friendlyName = (src: string) => src.replace(/\.csv$/i, "").replace(/_/g, " ").replace(/_/g, " ");

  if (table.rows.length === 0) return null;

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
        <span className="chip"><Icon name="table" size={15} /> L3 · Linked data</span>
        <span className="t-meta mono" style={{ marginLeft: "auto" }}>
          {table.rows.length} rows · {table.columns.length} cols
        </span>
      </div>

      {/* Scrollable table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 600 }}>
          <thead>
            {/* Row 1: group headers */}
            <tr style={{ background: "var(--surface)" }}>
              {/* Shared key columns span together */}
              {sharedKeyCols.length > 0 && (
                <th
                  colSpan={sharedKeyCols.length}
                  style={{ ...thStyle, borderRight: "2px solid var(--border-strong)", textAlign: "center", color: "var(--text-2)", fontSize: 10, letterSpacing: "0.08em" }}
                >
                  SHARED KEYS
                </th>
              )}
              {/* Source group headers */}
              {allSourceGroups.map(([src, cols]) => (
                <th
                  key={src}
                  colSpan={cols.length}
                  style={{ ...thStyle, textAlign: "center", color: "var(--blue)", fontSize: 11, fontWeight: 700, borderLeft: "2px solid var(--blue)", borderRight: "1px solid var(--border)" }}
                >
                  {friendlyName(src)}
                </th>
              ))}
            </tr>
            {/* Row 2: actual column names */}
            <tr>
              {sharedKeyCols.map((col) => (
                <th key={col} className="mono" style={{ ...thStyle, borderRight: col === sharedKeyCols[sharedKeyCols.length - 1] ? "2px solid var(--border-strong)" : undefined }}>
                  {col}
                </th>
              ))}
              {allSourceGroups.map(([src, cols]) =>
                cols.map((col, i) => {
                  // Strip source name prefix for cleaner display
                  const shortSrc = src.replace(/\.csv$/i, "");
                  const label = col.startsWith(`value_${shortSrc}_`)
                    ? col.slice(`value_${shortSrc}_`.length)
                    : col.replace(`_${shortSrc}`, "").replace(`${shortSrc}_`, "");
                  return (
                    <th
                      key={col}
                      className="mono"
                      style={{
                        ...thStyle,
                        color: "var(--blue)",
                        borderLeft: i === 0 ? "2px solid var(--blue)" : undefined,
                      }}
                    >
                      {label || col}
                    </th>
                  );
                }),
              )}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, i) => (
              <tr key={i} className="rawrow">
                {sharedKeyCols.map((col) => (
                  <td key={col} className="mono" style={{ ...tdStyle, fontWeight: 600, borderRight: col === sharedKeyCols[sharedKeyCols.length - 1] ? "2px solid var(--border-strong)" : undefined }}>
                    {formatCell(row[col])}
                  </td>
                ))}
                {allSourceGroups.map(([src, cols]) =>
                  cols.map((col, i) => (
                    <td
                      key={col}
                      className="mono"
                      style={{
                        ...tdStyle,
                        color: "var(--text)",
                        borderLeft: i === 0 ? "2px solid var(--blue)" : undefined,
                      }}
                    >
                      {formatCell(row[col])}
                    </td>
                  )),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Show more / summary */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 12 }}>
        <span className="t-meta mono" style={{ flex: 1 }}>
          Showing {displayRows.length} of {table.rows.length} rows
        </span>
        {table.rows.length > 50 && (
          <button
            className="pill-btn ghost"
            onClick={() => setShowAllRows(!showAllRows)}
            style={{ height: 28, fontSize: 12 }}
          >
            {showAllRows ? "Show less" : `Show all ${table.rows.length} rows`}
          </button>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────── */
/* Entity Graph — generic ReactFlow view (rows_as_nodes, bipartite, etc) */
/* ─────────────────────────────────────────────────────────────────────── */

/* ─────────────────────────────────────────────────────────────────────── */
/* Reconciliated View — schema + data table (no ReactFlow)               */
/* ─────────────────────────────────────────────────────────────────────── */

function ReconciliatedView({
  graph, node: detail, graphAttrs,
}: {
  graph: DecodedGraph; node: NodeDetail; graphAttrs: Record<string, string>;
}) {
  const [showAllCols, setShowAllCols] = useState(false);
  const [showAllRows, setShowAllRows] = useState(false);

  const catalog: Array<{ concept: string; description: string; mappings: Array<{ source: string; column: string; notes?: string }> }> =
    useMemo(() => {
      try { return JSON.parse(graphAttrs._catalog || "[]"); }
      catch { return []; }
    }, [graphAttrs]);

  const sourceMeta: Record<string, { rows: number; columns: string[] }> =
    useMemo(() => {
      try { return JSON.parse(graphAttrs._sources || "{}"); }
      catch { return {}; }
    }, [graphAttrs]);

  const colSources: Record<string, string> =
    useMemo(() => {
      try { return JSON.parse(graphAttrs._col_sources || "{}"); }
      catch { return {}; }
    }, [graphAttrs]);

  const sourceNames = Object.keys(sourceMeta);
  const leftName = sourceNames[0]?.replace(/\.csv$/i, "").replace(/_/g, " ") ?? "";
  const rightName = sourceNames[1]?.replace(/\.csv$/i, "").replace(/_/g, " ") ?? "";

  // Extract table from graph nodes
  const table = useMemo(() => {
    const allKeys = new Set<string>();
    for (const n of graph.nodes) {
      for (const k of Object.keys(n)) if (k !== "_source") allKeys.add(k);
    }
    const columns = Array.from(allKeys);
    const rows = graph.nodes.map((n) => {
      const row: Record<string, unknown> = {};
      for (const c of columns) row[c] = n[c] ?? null;
      return row;
    });
    return { columns, rows };
  }, [graph]);

  const displayCols = showAllCols ? table.columns : table.columns.slice(0, 8);
  const displayRows = showAllRows ? table.rows : table.rows.slice(0, 50);
  const hiddenCols = table.columns.length - 8;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Relational gain banner */}
      <div style={{
        padding: "10px 16px", borderRadius: "var(--radius-md)",
        background: "var(--blue-soft)", border: "1px solid var(--blue)",
        display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
      }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--blue)" }}>
          {sourceNames.length} sources · {catalog.length} shared concept{catalog.length === 1 ? "" : "s"} → {table.rows.length.toLocaleString()} rows linked
        </span>
        <span className="t-meta" style={{ fontSize: 11 }}>
          Artefactual heterogeneity reduced — relational structure established
        </span>
      </div>

      {/* Schema reconciliation */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
          <span className="chip"><Icon name="graph" size={15} /> L3 · Schema</span>
          <span className="t-meta" style={{ marginLeft: "auto" }}>
            {sourceNames.length} sources · {catalog.length} concepts
          </span>
        </div>

        {/* Source headers */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
          <div style={{ flex: 1, padding: "10px 16px", borderRight: "1px solid var(--border)" }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{leftName}</div>
            {sourceMeta[sourceNames[0]] && <span className="t-meta mono" style={{ fontSize: 11 }}>{sourceMeta[sourceNames[0]].rows} rows</span>}
          </div>
          <div style={{ flex: "0 0 40px" }} />
          <div style={{ flex: 1, padding: "10px 16px", textAlign: "right", borderLeft: "1px solid var(--border)" }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{rightName}</div>
            {sourceMeta[sourceNames[1]] && <span className="t-meta mono" style={{ fontSize: 11 }}>{sourceMeta[sourceNames[1]].rows} rows</span>}
          </div>
        </div>

        {/* Concept bridge rows */}
        {catalog.map((c, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", borderBottom: "1px solid var(--border)", padding: "8px 0" }}>
            <div style={{ flex: 1, padding: "0 16px", textAlign: "right" }}>
              {c.mappings[0] && <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--blue)" }}>{c.mappings[0].column}</span>}
            </div>
            <div style={{ flex: "0 0 auto", padding: "0 4px", display: "flex", alignItems: "center" }}>
              <span style={{ width: 16, height: 1, background: "var(--blue)", opacity: 0.3 }} />
              <span style={{
                padding: "4px 12px", background: "var(--blue-soft)", borderRadius: 16,
                border: "1px solid var(--blue)", fontSize: 11, fontWeight: 700,
                color: "var(--blue)", whiteSpace: "nowrap",
                display: "flex", flexDirection: "column", alignItems: "center", gap: 1,
              }}>
                {c.concept}
                {c.description && <span style={{ fontSize: 9, fontWeight: 400, color: "var(--text-2)", whiteSpace: "normal", textAlign: "center", maxWidth: 180 }}>{c.description}</span>}
              </span>
              <span style={{ width: 16, height: 1, background: "var(--blue)", opacity: 0.3 }} />
            </div>
            <div style={{ flex: 1, padding: "0 16px" }}>
              {c.mappings[1] && <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--blue)" }}>{c.mappings[1].column}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* Multi-level linked data table */}
      <MultiLevelTable table={table} sourceNames={sourceNames} catalog={catalog} colSources={colSources} showAllRows={showAllRows} setShowAllRows={setShowAllRows} />
    </div>
  );
}


function EntityGraph({ graph, node: detail }: { graph: DecodedGraph; node: NodeDetail }) {
  const [showAllCols, setShowAllCols] = useState(false);
  const [showAllRows, setShowAllRows] = useState(false);

  // Detect row-like data: nodes have many attributes (merged table rows)
  const isRowData = useMemo(() => {
    if (graph.nodes.length === 0) return false;
    const attrCount = Object.keys(graph.nodes[0]).filter((k) => k !== "id").length;
    return attrCount > 3;
  }, [graph]);

  // Extract table from graph nodes
  const table = useMemo(() => {
    if (!isRowData) return null;
    const allKeys = new Set<string>();
    for (const n of graph.nodes) {
      for (const k of Object.keys(n)) allKeys.add(k);
    }
    const columns = Array.from(allKeys);
    const rows = graph.nodes.map((n) => {
      const row: Record<string, unknown> = {};
      for (const c of columns) row[c] = n[c] ?? null;
      return row;
    });
    return { columns, rows };
  }, [graph, isRowData]);

  const displayCols = table
    ? showAllCols ? table.columns : table.columns.slice(0, 8)
    : [];
  const displayRows = table
    ? showAllRows ? table.rows : table.rows.slice(0, 50)
    : [];
  const hiddenCols = table ? table.columns.length - 8 : 0;

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
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Graph view (compact when table is present) */}
      <div className="card" style={{ padding: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 6px 12px", flexWrap: "wrap" }}>
          <span className="chip"><Icon name="graph" size={15} /> L3 · Knowledge Graph</span>
          <span className="t-name" style={{ fontWeight: 700 }}>
            {detail.decision_description ?? "Entity / relationship graph"}
          </span>
          <span className="t-meta" style={{ marginLeft: "auto" }}>
            <span className="mono">{nodes.length}</span> entities
            {edges.length > 0 && <> · <span className="mono">{edges.length}</span> links</>}
          </span>
        </div>
        <div style={{ height: isRowData ? 200 : 420, overflow: "hidden", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface)" }}>
          <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }} nodesDraggable nodesConnectable={false}>
            <Background color="var(--border-strong)" gap={22} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      </div>

      {/* Data table (when nodes contain row-like data) */}
      {table && (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
            <span className="chip"><Icon name="table" size={15} /> L3 · Merged Data</span>
            <span className="t-meta mono">
              {table.rows.length} rows x {table.columns.length} cols
            </span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 480 }}>
              <thead>
                <tr>
                  {displayCols.map((c) => (
                    <th key={c} className="mono" style={thStyle}>{c}</th>
                  ))}
                  {!showAllCols && hiddenCols > 0 && (
                    <th className="mono" style={{ ...thStyle, color: "var(--border-strong)" }}>+{hiddenCols} ...</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {displayRows.map((row, i) => (
                  <tr key={i} className="rawrow">
                    {displayCols.map((c) => (
                      <td key={c} className="mono" style={tdStyle}>{formatCell(row[c])}</td>
                    ))}
                    {!showAllCols && hiddenCols > 0 && (
                      <td style={{ ...tdStyle, color: "var(--border-strong)" }}>...</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: "10px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {table.rows.length > 50 && (
              <button className="pill-btn ghost" style={{ height: 26, fontSize: 11 }} onClick={() => setShowAllRows((v) => !v)}>
                {showAllRows ? "Show first 50" : `Show all ${table.rows.length} rows`}
              </button>
            )}
            {hiddenCols > 0 && (
              <button className="pill-btn ghost" style={{ height: 26, fontSize: 11, marginLeft: "auto" }} onClick={() => setShowAllCols((v) => !v)}>
                {showAllCols ? "Show 8 columns" : `Show all ${table.columns.length} columns`}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left", padding: "9px 12px", fontSize: 12, fontWeight: 700,
  color: "var(--text-2)", borderBottom: "1px solid var(--border)", background: "var(--surface)",
  position: "sticky", top: 0, letterSpacing: "0.01em", whiteSpace: "nowrap",
};
const tdStyle: React.CSSProperties = {
  padding: "10px 12px", fontSize: 13, borderBottom: "1px solid var(--border)",
  color: "var(--text)", whiteSpace: "nowrap",
};

function formatCell(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  return String(value);
}

function labelForNode(n: Record<string, unknown>): string {
  if (n.label != null) return truncate(String(n.label));
  if (n.name != null) return truncate(String(n.name));
  return truncate(String(n.id));
}

function truncate(s: string): string {
  return s.length > 12 ? s.slice(0, 11) + "…" : s;
}

/*
 * Hand-written domain types layered over the generated `schema.ts`.
 *
 * The generated schema gives us request/response shapes straight from the
 * OpenAPI contract; these aliases name the ones the UI uses most, plus a few
 * loosely-typed shapes (tree + node payloads) the backend returns as open
 * objects (`additionalProperties: true`).
 */
import type { components } from "./schema";

/** Introspection for per-edge controls (service `_options`). */
export interface SessionOptions {
  builders: string[];
  aggregations: string[];
  columns: string[];
  sources: string[];
}

/** A registry enrichment function (L0→L1 ascent), from `available_moves`. */
export interface EnrichmentOption {
  name: string;
  description?: string;
  requires_context?: boolean;
}

/** A registry dimension (L1→L2 / L2→L3 ascent), from `available_moves`. */
export interface DimensionOption {
  name: string;
  description?: string;
  possible_values?: string[];
}

/** An ascent move descriptor; carries the registry option lists. */
export interface AscendMove {
  target?: string;
  step?: string;
  description?: string;
  enrichment_functions?: EnrichmentOption[];
  dimensions?: DimensionOption[];
}

/*
 * The backend adds `options` to its state projection (service.state_of). The
 * generated schema types it loosely; this augmentation names the shape the UI
 * relies on without a full openapi regen.
 */
export type SessionState = components["schemas"]["SessionState"] & {
  options?: SessionOptions;
};
export type SessionSummary = components["schemas"]["SessionSummary"];
export type CreateSessionRequest =
  components["schemas"]["CreateSessionRequest"];
export type DescendRequest = components["schemas"]["DescendRequest"];
export type AscendRequest = components["schemas"]["AscendRequest"];
export type BranchFromRequest = components["schemas"]["BranchFromRequest"];
export type MutationCount = components["schemas"]["MutationCount"];
export type HealthResponse = components["schemas"]["HealthResponse"];

/** Demo dataset sources the landing page can start a session from. */
export type DemoSource = "demo:school_scores" | "demo:ademe" | "demo:energy";

/** A single node in the move tree (`GET /tree` returns these flat). */
export interface TreeNode {
  id: string;
  level: number;
  level_name?: string;
  parent_id: string | null;
  children_ids: string[];
  action?: string | null;
  decision_description?: string | null;
  timestamp?: string | null;
  metadata?: Record<string, unknown>;
  output_snapshot?: Record<string, unknown>;
}

/** Response shape of `GET /sessions/{id}/tree`. */
export interface TreeResponse {
  root_id: string;
  current_id: string;
  nodes: TreeNode[];
}

/** Payload encodings produced by the engine (spec 015). */
export type PayloadKind =
  | "dataframe"
  | "graph"
  | "vector"
  | "value"
  | "unlinkable";

/** Full node record from `GET /sessions/{id}/nodes/{node_id}`. */
export interface NodeDetail {
  id: string;
  level: number;
  level_name?: string;
  parent_id?: string | null;
  children_ids?: string[];
  action?: string | null;
  decision_description?: string | null;
  payload_kind?: PayloadKind;
  payload?: unknown;
  lineage?: unknown;
  edge_decision?: unknown;
  output_snapshot?: Record<string, unknown>;
  summary?: Record<string, unknown>;
}

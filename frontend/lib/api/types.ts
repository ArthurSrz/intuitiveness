/*
 * Hand-written domain types layered over the generated `schema.ts`.
 *
 * The generated schema gives us request/response shapes straight from the
 * OpenAPI contract; these aliases name the ones the UI uses most, plus a few
 * loosely-typed shapes (tree + node payloads) the backend returns as open
 * objects (`additionalProperties: true`).
 */
import type { components } from "./schema";

export type SessionState = components["schemas"]["SessionState"];
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

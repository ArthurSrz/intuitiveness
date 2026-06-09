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

/** Demo datasets the landing page offers. */
export const DEMO_SOURCES = [
  { id: "demo:school_scores", label: "School Scores" },
  { id: "demo:ademe", label: "ADEME Fundings" },
  { id: "demo:energy", label: "Energy Prices" },
] as const;

export type DemoSource = (typeof DEMO_SOURCES)[number]["id"];

/** Human labels per abstraction level (L4 raw -> L0 datum). */
export const LEVEL_NAMES: Record<number, string> = {
  4: "Sources",
  3: "Graph",
  2: "Table",
  1: "Vector",
  0: "Datum",
};

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

/** node-link JSON shape (NetworkX) we expect for an L3 graph payload. */
export interface GraphPayload {
  directed?: boolean;
  multigraph?: boolean;
  graph?: Record<string, unknown>;
  nodes: Array<{ id: string | number; [key: string]: unknown }>;
  links: Array<{
    source: string | number;
    target: string | number;
    [key: string]: unknown;
  }>;
}

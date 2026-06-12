"use client";

/*
 * React Query hooks over the typed client.
 *
 * Convention: every mutation invalidates the session + tree queries for its
 * session, so the level rail, current level view, and branch tree all re-read
 * fresh state after any descend/ascend/time-travel/branch/prune.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiUpload } from "./client";
import type {
  AscendRequest,
  BranchFromRequest,
  CreateSessionRequest,
  DescendRequest,
  HealthResponse,
  MutationCount,
  NodeDetail,
  SessionState,
  SessionSummary,
  TreeResponse,
} from "./types";

/** Centralized query keys so invalidation stays consistent. */
export const queryKeys = {
  sessions: ["sessions"] as const,
  session: (id: string) => ["session", id] as const,
  tree: (id: string) => ["tree", id] as const,
  node: (sessionId: string, nodeId: string) =>
    ["node", sessionId, nodeId] as const,
  health: ["health"] as const,
};

/** Invalidate everything that depends on a session's state. */
function invalidateSession(
  queryClient: ReturnType<typeof useQueryClient>,
  sessionId: string,
) {
  queryClient.invalidateQueries({ queryKey: queryKeys.session(sessionId) });
  queryClient.invalidateQueries({ queryKey: queryKeys.tree(sessionId) });
  queryClient.invalidateQueries({ queryKey: ["node", sessionId] });
}

// ---- Reads ----------------------------------------------------------------

export function useSessions(): UseQueryResult<SessionSummary[]> {
  return useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => apiGet<SessionSummary[]>("/sessions"),
  });
}

export function useSession(
  sessionId: string | undefined,
): UseQueryResult<SessionState> {
  return useQuery({
    queryKey: queryKeys.session(sessionId ?? ""),
    queryFn: () => apiGet<SessionState>(`/sessions/${sessionId}`),
    enabled: Boolean(sessionId),
  });
}

export function useTree(
  sessionId: string | undefined,
): UseQueryResult<TreeResponse> {
  return useQuery({
    queryKey: queryKeys.tree(sessionId ?? ""),
    queryFn: () => apiGet<TreeResponse>(`/sessions/${sessionId}/tree`),
    enabled: Boolean(sessionId),
  });
}

export function useNode(
  sessionId: string | undefined,
  nodeId: string | undefined,
): UseQueryResult<NodeDetail> {
  return useQuery({
    queryKey: queryKeys.node(sessionId ?? "", nodeId ?? ""),
    queryFn: () =>
      apiGet<NodeDetail>(`/sessions/${sessionId}/nodes/${nodeId}`),
    enabled: Boolean(sessionId && nodeId),
  });
}

export function useHealth(): UseQueryResult<HealthResponse> {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiGet<HealthResponse>("/healthz"),
    refetchInterval: 30_000,
  });
}

// ---- Mutations ------------------------------------------------------------

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateSessionRequest) =>
      apiPost<SessionState>("/sessions", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });
}

export function useImportUrl() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { url: string; filename?: string }) =>
      apiPost<SessionState>("/sessions/import-url", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });
}

export function useUploadCsv() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) =>
      apiUpload<SessionState>("/sessions/upload", files),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });
}

export function useImportWorldBank() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { indicator_id: string; indicator_name: string; mrv?: number }) =>
      apiPost<SessionState>("/sessions/import-worldbank", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });
}

export function useAddSource(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) =>
      apiUpload<SessionState>(`/sessions/${sessionId}/add-source`, files),
    onSuccess: () => invalidateSession(queryClient, sessionId),
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiDelete(`/sessions/${sessionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });
}

export function useDescend(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: DescendRequest) =>
      apiPost<SessionState>(`/sessions/${sessionId}/descend`, body),
    onSuccess: () => invalidateSession(queryClient, sessionId),
  });
}

export function useAscend(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AscendRequest) =>
      apiPost<SessionState>(`/sessions/${sessionId}/ascend`, body),
    onSuccess: () => invalidateSession(queryClient, sessionId),
  });
}

export function useTimeTravel(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nodeId: string) =>
      apiPost<SessionState>(`/sessions/${sessionId}/time-travel`, {
        node_id: nodeId,
      }),
    onSuccess: () => invalidateSession(queryClient, sessionId),
  });
}

export function useBranchFrom(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: BranchFromRequest) =>
      apiPost<SessionState>(`/sessions/${sessionId}/branch-from`, body),
    onSuccess: () => invalidateSession(queryClient, sessionId),
  });
}

export function usePrune(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nodeId: string) =>
      apiPost<MutationCount>(`/sessions/${sessionId}/prune`, {
        node_id: nodeId,
      }),
    onSuccess: () => invalidateSession(queryClient, sessionId),
  });
}

export function useArchive(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nodeId: string) =>
      apiPost<MutationCount>(`/sessions/${sessionId}/archive`, {
        node_id: nodeId,
      }),
    onSuccess: () => invalidateSession(queryClient, sessionId),
  });
}

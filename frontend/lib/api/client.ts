/*
 * Typed fetch wrapper around the Intuitiveness FastAPI backend.
 * Base URL comes from NEXT_PUBLIC_API_URL (default localhost:8000).
 *
 * Errors are surfaced as ApiError, which carries the backend's structured
 * `{detail, code}` payload so callers can react to 409 (prune conflicts)
 * and 422 (validation) precisely.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** A single FastAPI/Pydantic validation entry (`HTTPValidationError.detail[]`). */
export interface ValidationDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/** Thrown for any non-2xx response. Holds parsed backend error info. */
export class ApiError extends Error {
  readonly status: number;
  /** String detail (e.g. 409 conflicts) or array of validation entries (422). */
  readonly detail?: string | ValidationDetail[];
  /** Optional machine-readable code the backend may attach. */
  readonly code?: string;

  constructor(
    status: number,
    message: string,
    detail?: string | ValidationDetail[],
    code?: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
  }

  /** Human-readable single-line summary, useful for toasts/banners. */
  get displayMessage(): string {
    if (typeof this.detail === "string") return this.detail;
    if (Array.isArray(this.detail) && this.detail.length > 0) {
      return this.detail.map((d) => d.msg).join("; ");
    }
    return this.message;
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: string | ValidationDetail[] | undefined;
  let code: string | undefined;
  try {
    const body = await response.json();
    detail = body?.detail;
    code = body?.code;
  } catch {
    // Non-JSON error body — fall through with status text only.
  }
  return new ApiError(
    response.status,
    `Request failed with status ${response.status}`,
    detail,
    code,
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  // 204 No Content (e.g. DELETE) has no body to parse.
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: JSON.stringify(body ?? {}),
  });
}

export function apiDelete<T = void>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

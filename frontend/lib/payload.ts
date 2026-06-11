/*
 * Decoders for the engine's payload encodings (spec 015).
 *
 * "dataframe" = a pandas DataFrame serialized as JSON, then zlib-compressed,
 * then base64-encoded. We base64-decode, pako-inflate, and JSON.parse it.
 * The DataFrame JSON uses pandas' default `to_json()` (orient="columns"):
 *   { "<column>": { "<row index>": <value>, ... }, ... }
 * We normalize that into { columns, rows } for table rendering.
 */
import pako from "pako";

export interface DecodedTable {
  columns: string[];
  rows: Array<Record<string, unknown>>;
}

/** Base64 -> Uint8Array (browser-safe via atob). */
function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/** Inflate a zlib+base64 string back into its original UTF-8 text. */
export function inflateBase64(b64: string): string {
  const bytes = base64ToBytes(b64);
  return pako.inflate(bytes, { to: "string" });
}

/**
 * Decode a "dataframe" payload string into a tabular shape.
 * Returns null if the input cannot be decoded (caller falls back to summary).
 */
export function decodeDataframe(encoded: string): DecodedTable | null {
  try {
    const parsed = JSON.parse(inflateBase64(encoded)) as unknown;
    // The engine serializes DataFrames in pandas `split` orient:
    //   { columns: [...], index: [...], data: [[...row...], ...] }
    if (isSplitFrame(parsed)) return splitFrameToTable(parsed);
    // Fallback: pandas `columns` orient { col: { idx: value } }.
    return columnsObjectToTable(parsed as Record<string, Record<string, unknown>>);
  } catch {
    return null;
  }
}

interface SplitFrame {
  columns: (string | number)[];
  index?: (string | number)[];
  data: unknown[][];
}

function isSplitFrame(p: unknown): p is SplitFrame {
  return (
    typeof p === "object" &&
    p !== null &&
    Array.isArray((p as SplitFrame).columns) &&
    Array.isArray((p as SplitFrame).data)
  );
}

function splitFrameToTable(frame: SplitFrame): DecodedTable {
  const columns = frame.columns.map(String);
  const rows = frame.data.map((rowArr, i) => {
    const row: Record<string, unknown> = { __index: String(frame.index?.[i] ?? i) };
    columns.forEach((col, c) => {
      row[col] = rowArr[c];
    });
    return row;
  });
  return { columns, rows };
}

export interface DecodedGraph {
  nodes: Array<{ id: string | number; [key: string]: unknown }>;
  links: Array<{ source: string | number; target: string | number; [key: string]: unknown }>;
}

/**
 * Decode a "graph" payload. The engine ships NetworkX node-link JSON the same
 * way as dataframes — zlib-compressed then base64-encoded — and uses the
 * `edges` key (newer NetworkX) rather than the legacy `links`. We inflate,
 * parse, and normalize both the encoding and the edges/links naming.
 * Returns null if the input can't be decoded.
 */
export function decodeGraph(encoded: unknown): DecodedGraph | null {
  try {
    const obj =
      typeof encoded === "string"
        ? (JSON.parse(inflateBase64(encoded)) as Record<string, unknown>)
        : (encoded as Record<string, unknown>);
    if (!obj || typeof obj !== "object") return null;
    const nodes = obj.nodes as DecodedGraph["nodes"] | undefined;
    const links = (obj.links ?? obj.edges) as DecodedGraph["links"] | undefined;
    if (!Array.isArray(nodes)) return null;
    return { nodes, links: Array.isArray(links) ? links : [] };
  } catch {
    return null;
  }
}

/**
 * Decode a "value" (L0 datum) payload. The engine zlib+base64-encodes scalars
 * too, so a string payload is inflated then parsed; a plain number passes
 * through. Returns a number when the text is numeric, else the raw string.
 */
export function decodeValue(payload: unknown): number | string | null {
  if (payload == null) return null;
  if (typeof payload === "number") return payload;
  if (typeof payload !== "string") return null;
  let text = payload;
  try {
    text = inflateBase64(payload); // encoded scalar → its JSON text
  } catch {
    // not zlib+base64 — treat the string as the literal value
  }
  const n = Number(text);
  return Number.isFinite(n) ? n : text;
}

export interface VectorEntry {
  value: number;
  label: string;
}

/**
 * Decode a "vector" payload into [{value,label}]. The engine ships the vector
 * as a one-column DataFrame in pandas `split` orient
 * ({columns, index, data:[[v],…]}), zlib+base64-encoded — but we also accept a
 * plain array of numbers / {value,label} objects as a fallback.
 */
export function decodeVector(payload: unknown): VectorEntry[] {
  let data: unknown = payload;
  if (typeof payload === "string") {
    try {
      data = JSON.parse(inflateBase64(payload));
    } catch {
      return [];
    }
  }
  // split-orient DataFrame: { columns, index, data:[[v],…] }
  if (data && typeof data === "object" && Array.isArray((data as { data?: unknown }).data)) {
    const split = data as { index?: unknown[]; data: unknown[][] };
    return split.data
      .map((row, i) => ({
        value: toNum(Array.isArray(row) ? row[0] : row),
        label: String(split.index?.[i] ?? i),
      }))
      .filter((e): e is VectorEntry => e.value !== null) as VectorEntry[];
  }
  // plain array of numbers or {value,label}
  if (Array.isArray(data)) {
    return data
      .map((v, i) => ({
        value: toNum(typeof v === "object" && v ? (v as { value?: unknown }).value : v),
        label:
          typeof v === "object" && v
            ? String((v as { label?: unknown; name?: unknown }).label ??
                (v as { name?: unknown }).name ??
                i)
            : String(i),
      }))
      .filter((e): e is VectorEntry => e.value !== null) as VectorEntry[];
  }
  return [];
}

function toNum(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Convert pandas orient="columns" JSON into { columns, rows }. */
function columnsObjectToTable(
  data: Record<string, Record<string, unknown>>,
): DecodedTable {
  const columns = Object.keys(data);
  // Collect the union of row indices, preserving first-seen order.
  const rowIndex: string[] = [];
  const seen = new Set<string>();
  for (const col of columns) {
    for (const idx of Object.keys(data[col] ?? {})) {
      if (!seen.has(idx)) {
        seen.add(idx);
        rowIndex.push(idx);
      }
    }
  }
  const rows = rowIndex.map((idx) => {
    const row: Record<string, unknown> = { __index: idx };
    for (const col of columns) {
      row[col] = data[col]?.[idx];
    }
    return row;
  });
  return { columns, rows };
}

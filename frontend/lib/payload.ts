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
    const json = inflateBase64(encoded);
    const parsed = JSON.parse(json) as Record<
      string,
      Record<string, unknown>
    >;
    return columnsObjectToTable(parsed);
  } catch {
    return null;
  }
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

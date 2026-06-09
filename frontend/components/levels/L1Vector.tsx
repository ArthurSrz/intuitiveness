import type { NodeDetail } from "@/lib/api/types";
import { Card } from "@/components/ui/Card";

/*
 * L1 — A vector (kind "vector" = list of values). We render it as a compact
 * sparkline-style bar row plus the raw list so the user sees both shape and
 * values.
 */
export function L1Vector({ node }: { node: NodeDetail }) {
  const raw = node.payload;
  const values: number[] = Array.isArray(raw)
    ? raw.map(toNumber).filter((n): n is number => n !== null)
    : [];

  const labels: string[] = Array.isArray(raw) ? raw.map(labelOf) : [];

  const max = values.length ? Math.max(...values) : 0;
  const min = values.length ? Math.min(...values) : 0;
  const span = max - min || 1;

  return (
    <Card
      title="L1 · Vector"
      subtitle={`${values.length} value${values.length === 1 ? "" : "s"}`}
    >
      {values.length === 0 ? (
        <p className="text-sm text-fg-muted">No vector values to display.</p>
      ) : (
        <>
          {/* Sparkline: one bar per value, height scaled within [min, max]. */}
          <div className="flex h-6 items-end gap-px">
            {values.map((v, i) => {
              const heightPct = ((v - min) / span) * 100;
              return (
                <span
                  key={i}
                  className="flex-1 rounded-sm bg-level-1"
                  style={{ height: `${Math.max(heightPct, 4)}%` }}
                  title={`${labels[i]}: ${v}`}
                />
              );
            })}
          </div>

          <ul className="mt-4 flex flex-wrap gap-2">
            {values.map((v, i) => (
              <li
                key={i}
                className="rounded-md border border-border bg-surface-muted px-3 py-1 font-mono text-xs text-fg"
              >
                {labels[i] !== String(i) && (
                  <span className="text-fg-muted">{labels[i]}: </span>
                )}
                {v}
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}

function toNumber(v: unknown): number | null {
  if (typeof v === "number") return v;
  if (typeof v === "object" && v !== null && "value" in v) {
    const inner = (v as { value: unknown }).value;
    return typeof inner === "number" ? inner : null;
  }
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function labelOf(v: unknown, index: number): string {
  if (typeof v === "object" && v !== null) {
    const obj = v as Record<string, unknown>;
    if ("label" in obj) return String(obj.label);
    if ("name" in obj) return String(obj.name);
  }
  return String(index);
}

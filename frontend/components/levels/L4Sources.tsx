import type { NodeDetail } from "@/lib/api/types";
import { Card } from "@/components/ui/Card";

/*
 * L4 — Raw sources. The payload for L4 is "unlinkable": a dict of
 * { <source name>: <dataframe encoding> }. We don't decode every table here;
 * we just list the source names and any shape hints the summary carries.
 */
export function L4Sources({ node }: { node: NodeDetail }) {
  const payload = node.payload;
  const sourceNames =
    payload && typeof payload === "object"
      ? Object.keys(payload as Record<string, unknown>)
      : [];

  const shapes =
    (node.summary?.shapes as Record<string, unknown> | undefined) ?? undefined;

  return (
    <Card title="L4 · Sources" subtitle="Raw input files for this session">
      {sourceNames.length === 0 ? (
        <p className="text-sm text-fg-muted">No source files reported.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {sourceNames.map((name) => (
            <li
              key={name}
              className="flex items-center justify-between rounded-md border border-border bg-surface-muted px-4 py-3"
            >
              <span className="font-mono text-sm text-fg">{name}</span>
              {shapes?.[name] != null && (
                <span className="text-xs text-fg-muted">
                  {String(shapes[name])}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

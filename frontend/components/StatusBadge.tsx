"use client";

import { useHealth } from "@/lib/api/hooks";

/*
 * Small health indicator driven by GET /healthz. Green when status is "ok"
 * and every configured dependency reports ok; amber on degraded deps; red on
 * error / unreachable.
 */
export function StatusBadge() {
  const { data, isError, isLoading } = useHealth();

  let tone: "ok" | "warn" | "down" = "warn";
  let label = "checking…";

  if (isLoading) {
    tone = "warn";
    label = "checking…";
  } else if (isError || !data) {
    tone = "down";
    label = "offline";
  } else {
    const deps = Object.values(data.deps ?? {});
    const degraded = deps.some((d) => d.configured && !d.ok);
    if (data.status === "ok" && !degraded) {
      tone = "ok";
      label = "healthy";
    } else {
      tone = "warn";
      label = "degraded";
    }
  }

  const dotClass =
    tone === "ok" ? "bg-success" : tone === "warn" ? "bg-warning" : "bg-danger";

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-fg-muted">
      <span className={`inline-block h-2 w-2 rounded-full ${dotClass}`} />
      API {label}
    </span>
  );
}

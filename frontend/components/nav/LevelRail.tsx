"use client";

import { useState } from "react";
import type { DescendRequest, SessionState } from "@/lib/api/types";
import { LEVEL_NAMES } from "@/lib/api/types";
import { useAscend, useDescend } from "@/lib/api/hooks";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/Button";

/*
 * Vertical L4 -> L0 rail. Highlights the current level, and renders a small
 * param form for the next descend/ascend edge based on `available_moves`.
 *
 * Per-edge descend params:
 *   L4->L3: { builder: "rows_as_nodes" }
 *   L3->L2: { domains: ["high score", "low score"] }
 *   L2->L1: { column: "value" }
 *   L1->L0: { aggregation: "mean" | "sum" | "count" }
 * Ascend params are all optional; we send {} (defaults).
 */
const LEVELS = [4, 3, 2, 1, 0] as const;

export function LevelRail({ session }: { session: SessionState }) {
  const descend = useDescend(session.session_id);
  const ascend = useAscend(session.session_id);

  const current = session.current_level;
  const canDescend = (session.available_moves?.descend?.length ?? 0) > 0;
  const canAscend = (session.available_moves?.ascend?.length ?? 0) > 0;

  // Edge param form state.
  const [builder, setBuilder] = useState("rows_as_nodes");
  const [domains, setDomains] = useState("high score, low score");
  const [column, setColumn] = useState("value");
  const [aggregation, setAggregation] = useState("mean");

  const pending = descend.isPending || ascend.isPending;
  const error = (descend.error ?? ascend.error) as ApiError | null;

  function handleDescend() {
    const body = buildDescendBody(current, {
      builder,
      domains,
      column,
      aggregation,
    });
    descend.mutate(body);
  }

  return (
    <aside className="flex w-full flex-col gap-4">
      <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold text-fg">Levels</h3>
        <ol className="flex flex-col gap-2">
          {LEVELS.map((lvl) => {
            const active = lvl === current;
            return (
              <li
                key={lvl}
                className={[
                  "flex items-center justify-between rounded-md border px-3 py-2",
                  active
                    ? "border-primary bg-surface-muted"
                    : "border-border bg-surface",
                ].join(" ")}
              >
                <span className="flex items-center gap-2">
                  <span
                    className={`inline-block h-2 w-2 rounded-full bg-level-${lvl}`}
                  />
                  <span className="text-sm font-medium text-fg">
                    L{lvl}
                  </span>
                  <span className="text-xs text-fg-muted">
                    {LEVEL_NAMES[lvl]}
                  </span>
                </span>
                {active && (
                  <span className="text-xs font-medium text-primary">
                    current
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </div>

      {/* Next descend edge form. */}
      {canDescend && (
        <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-fg">
            Descend to L{current - 1}
          </h3>
          <EdgeForm
            level={current}
            builder={builder}
            setBuilder={setBuilder}
            domains={domains}
            setDomains={setDomains}
            column={column}
            setColumn={setColumn}
            aggregation={aggregation}
            setAggregation={setAggregation}
          />
          <Button
            onClick={handleDescend}
            disabled={pending}
            className="mt-3 w-full"
          >
            {descend.isPending ? "Descending…" : `Descend ↓`}
          </Button>
        </div>
      )}

      {/* Next ascend edge — defaults work, so a single button. */}
      {canAscend && (
        <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-fg">
            Ascend to L{current + 1}
          </h3>
          <p className="mb-3 text-xs text-fg-muted">
            Uses registry defaults for this edge.
          </p>
          <Button
            variant="secondary"
            onClick={() => ascend.mutate({})}
            disabled={pending}
            className="w-full"
          >
            {ascend.isPending ? "Ascending…" : "Ascend ↑"}
          </Button>
        </div>
      )}

      {error && (
        <p className="rounded-md border border-border bg-surface px-3 py-2 text-xs text-danger">
          {error.displayMessage}
        </p>
      )}
    </aside>
  );
}

/** Per-level descend param inputs. */
function EdgeForm({
  level,
  builder,
  setBuilder,
  domains,
  setDomains,
  column,
  setColumn,
  aggregation,
  setAggregation,
}: {
  level: number;
  builder: string;
  setBuilder: (v: string) => void;
  domains: string;
  setDomains: (v: string) => void;
  column: string;
  setColumn: (v: string) => void;
  aggregation: string;
  setAggregation: (v: string) => void;
}) {
  if (level === 4) {
    return (
      <Field label="Builder">
        <select
          className={selectClass}
          value={builder}
          onChange={(e) => setBuilder(e.target.value)}
        >
          <option value="rows_as_nodes">rows_as_nodes</option>
          <option value="bipartite">bipartite</option>
        </select>
      </Field>
    );
  }
  if (level === 3) {
    return (
      <Field label="Domains (comma-separated)">
        <input
          className={inputClass}
          value={domains}
          onChange={(e) => setDomains(e.target.value)}
          placeholder="high score, low score"
        />
      </Field>
    );
  }
  if (level === 2) {
    return (
      <Field label="Column">
        <input
          className={inputClass}
          value={column}
          onChange={(e) => setColumn(e.target.value)}
          placeholder="value"
        />
      </Field>
    );
  }
  if (level === 1) {
    return (
      <Field label="Aggregation">
        <select
          className={selectClass}
          value={aggregation}
          onChange={(e) => setAggregation(e.target.value)}
        >
          <option value="mean">mean</option>
          <option value="sum">sum</option>
          <option value="count">count</option>
        </select>
      </Field>
    );
  }
  return null;
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-fg-muted">{label}</span>
      {children}
    </label>
  );
}

const inputClass =
  "rounded-md border border-border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-primary";
const selectClass = inputClass;

/** Assemble the per-edge descend body from the current level + form state. */
function buildDescendBody(
  level: number,
  form: {
    builder: string;
    domains: string;
    column: string;
    aggregation: string;
  },
): DescendRequest {
  switch (level) {
    case 4:
      return { builder: form.builder };
    case 3:
      return {
        domains: form.domains
          .split(",")
          .map((d) => d.trim())
          .filter(Boolean),
      };
    case 2:
      return { column: form.column };
    case 1:
      return { aggregation: form.aggregation };
    default:
      return {};
  }
}

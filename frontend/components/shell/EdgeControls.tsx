"use client";

import type { CSSProperties } from "react";
import type {
  AscendMove,
  AscendRequest,
  DescendRequest,
  SessionOptions,
} from "@/lib/api/types";
import { Icon } from "@/components/ui/Icon";

/*
 * EdgeControls — the per-transition parameter inputs that restore the choices
 * the Streamlit app offered (and the spec-015 engine already honors), driven by
 * the backend's introspection `options` + the ascent option lists on
 * `available_moves`. Renders exactly ONE transition's controls (the move the
 * current "Next" / Descend / Ascend button will perform).
 *
 * The captured state lives in the orchestrator (one `EdgeParams` object);
 * `buildDescendBody` / `buildAscendBody` turn it into the real request body.
 */

export interface EdgeParams {
  builder: string;
  idColumn: string;
  entityColumn: string;
  attributeColumn: string;
  valueColumn: string;
  domains: string; // comma-separated
  column: string; // L2→L1
  filterQuery: string;
  aggregation: string;
  enrichmentFunc: string; // L0→L1
  dimensions: string[]; // L1→L2, L2→L3
  relationships: string; // L2→L3, comma-separated
  sourceColumn: string; // L2→L3
}

export function defaultEdgeParams(): EdgeParams {
  return {
    builder: "rows_as_nodes",
    idColumn: "",
    entityColumn: "",
    attributeColumn: "",
    valueColumn: "",
    domains: "high, low",
    column: "",
    filterQuery: "",
    aggregation: "mean",
    enrichmentFunc: "",
    dimensions: [],
    relationships: "",
    sourceColumn: "",
  };
}

const splitList = (s: string): string[] =>
  s.split(",").map((x) => x.trim()).filter(Boolean);

/** Prefer a numeric-looking measure column, else the last column. */
function defaultColumn(columns: string[]): string {
  if (columns.length === 0) return "value";
  const measure = columns.find((c) => /value|amount|price|score|count|total/i.test(c));
  return measure ?? columns[columns.length - 1];
}

/** Build the descend request body for the transition leaving `level`. */
export function buildDescendBody(
  level: number,
  p: EdgeParams,
  options?: SessionOptions,
): DescendRequest {
  const columns = options?.columns ?? [];
  switch (level) {
    case 4: {
      const config: Record<string, string> = {};
      if (p.builder === "rows_as_nodes" && p.idColumn) config.id_column = p.idColumn;
      if (p.builder === "bipartite") {
        if (p.entityColumn) config.entity_column = p.entityColumn;
        if (p.attributeColumn) config.attribute_column = p.attributeColumn;
        if (p.valueColumn) config.value_column = p.valueColumn;
      }
      return { builder: p.builder, config };
    }
    case 3:
      return { domains: splitList(p.domains) };
    case 2:
      return {
        column: p.column || defaultColumn(columns),
        ...(p.filterQuery ? { filter_query: p.filterQuery } : {}),
      };
    case 1:
      return { aggregation: p.aggregation };
    default:
      return {};
  }
}

/** Build the ascend request body for the transition leaving `level`. */
export function buildAscendBody(level: number, p: EdgeParams): AscendRequest {
  switch (level) {
    case 0:
      return p.enrichmentFunc ? { enrichment_func: p.enrichmentFunc } : {};
    case 1:
      return p.dimensions.length ? { dimensions: p.dimensions } : {};
    case 2:
      return {
        ...(p.dimensions.length ? { dimensions: p.dimensions } : {}),
        ...(p.relationships ? { relationships: splitList(p.relationships) } : {}),
        ...(p.sourceColumn ? { source_column: p.sourceColumn } : {}),
      };
    default:
      return {};
  }
}

/* -------------------------------- UI ----------------------------------- */

export function EdgeControls({
  dir,
  level,
  options,
  ascendMove,
  params,
  onChange,
}: {
  dir: "descend" | "ascend";
  level: number; // source level of the transition
  options?: SessionOptions;
  ascendMove?: AscendMove;
  params: EdgeParams;
  onChange: (patch: Partial<EdgeParams>) => void;
}) {
  const columns = options?.columns ?? [];
  const builders = options?.builders ?? ["rows_as_nodes", "bipartite"];
  const aggregations = options?.aggregations ?? ["mean", "sum", "count", "min", "max"];

  const body = (() => {
    if (dir === "descend") {
      if (level === 4) {
        return (
          <>
            <Select
              label="Graph builder"
              value={params.builder}
              options={builders}
              onChange={(v) => onChange({ builder: v })}
            />
            {params.builder === "rows_as_nodes" ? (
              <Select
                label="Entity (id) column"
                value={params.idColumn || columns[0] || ""}
                options={columns}
                onChange={(v) => onChange({ idColumn: v })}
              />
            ) : (
              <>
                <Select label="Entity column" value={params.entityColumn || columns[0] || ""} options={columns} onChange={(v) => onChange({ entityColumn: v })} />
                <Select label="Attribute column" value={params.attributeColumn || columns[1] || ""} options={columns} onChange={(v) => onChange({ attributeColumn: v })} />
                <Select label="Value column (optional)" value={params.valueColumn} options={["", ...columns]} onChange={(v) => onChange({ valueColumn: v })} />
              </>
            )}
          </>
        );
      }
      if (level === 3) {
        return (
          <Text
            label="Domain categories (comma-separated)"
            value={params.domains}
            placeholder="e.g. high, low"
            onChange={(v) => onChange({ domains: v })}
          />
        );
      }
      if (level === 2) {
        return (
          <>
            <Select
              label="Feature column to extract"
              value={params.column || defaultColumn(columns)}
              options={columns}
              onChange={(v) => onChange({ column: v })}
            />
            <Text
              label="Filter (optional pandas query)"
              value={params.filterQuery}
              placeholder="e.g. value > 30"
              onChange={(v) => onChange({ filterQuery: v })}
            />
          </>
        );
      }
      if (level === 1) {
        return (
          <Select
            label="Aggregation metric"
            value={params.aggregation}
            options={aggregations}
            onChange={(v) => onChange({ aggregation: v })}
          />
        );
      }
      return null;
    }
    // ascend
    if (level === 0) {
      const funcs = (ascendMove?.enrichment_functions ?? []).map((f) => f.name);
      return (
        <Select
          label="Enrichment function"
          value={params.enrichmentFunc}
          options={["", ...funcs]}
          emptyLabel="(default: rebuild from source)"
          onChange={(v) => onChange({ enrichmentFunc: v })}
        />
      );
    }
    if (level === 1 || level === 2) {
      const dims = (ascendMove?.dimensions ?? []).map((d) => d.name);
      return (
        <>
          <MultiSelect
            label="Dimensions to add"
            selected={params.dimensions}
            options={dims}
            onToggle={(name) =>
              onChange({
                dimensions: params.dimensions.includes(name)
                  ? params.dimensions.filter((d) => d !== name)
                  : [...params.dimensions, name],
              })
            }
          />
          {level === 2 && (
            <>
              <Text
                label="Relationships to link (comma-separated)"
                value={params.relationships}
                placeholder="e.g. belongs_to"
                onChange={(v) => onChange({ relationships: v })}
              />
              <Select
                label="Source column"
                value={params.sourceColumn}
                options={["", "value", ...(options?.columns ?? [])]}
                emptyLabel="(default: value)"
                onChange={(v) => onChange({ sourceColumn: v })}
              />
            </>
          )}
        </>
      );
    }
    return null;
  })();

  if (!body) return null;

  const target = dir === "descend" ? level - 1 : level + 1;
  return (
    <div className="card surface" style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Icon name="sliders" size={15} style={{ color: "var(--blue)" }} />
        <span className="t-label" style={{ color: "var(--text-2)" }}>
          {dir === "descend" ? "REDUCE" : "AMPLIFY"} TO L{target}
        </span>
        <span className="t-meta" style={{ marginLeft: "auto" }}>
          applied when you press {dir === "descend" ? "Descend / Next" : "Ascend / Next"}
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>{body}</div>
    </div>
  );
}

/* ---- small styled field primitives (tokens-only) ---- */

const fieldLabel: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  color: "var(--text-2)",
  marginBottom: 5,
  display: "block",
  letterSpacing: "0.01em",
};
const control: CSSProperties = {
  width: "100%",
  height: 36,
  padding: "0 10px",
  borderRadius: "var(--radius-md)",
  border: "1px solid var(--border-strong)",
  background: "var(--bg)",
  color: "var(--text)",
  fontFamily: "var(--font)",
  fontSize: 13.5,
  outline: "none",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ minWidth: 0 }}>
      <span style={fieldLabel}>{label}</span>
      {children}
    </label>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
  emptyLabel,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  emptyLabel?: string;
}) {
  return (
    <Field label={label}>
      <select style={control} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o || "__empty"} value={o}>
            {o === "" ? emptyLabel ?? "(none)" : o}
          </option>
        ))}
      </select>
    </Field>
  );
}

function Text({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (v: string) => void;
}) {
  return (
    <Field label={label}>
      <input
        style={control}
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </Field>
  );
}

function MultiSelect({
  label,
  selected,
  options,
  onToggle,
}: {
  label: string;
  selected: string[];
  options: string[];
  onToggle: (name: string) => void;
}) {
  return (
    <div style={{ gridColumn: "1 / -1" }}>
      <span style={fieldLabel}>{label}</span>
      {options.length === 0 ? (
        <span className="t-meta">Registry defaults will be used.</span>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {options.map((name) => {
            const on = selected.includes(name);
            return (
              <button
                key={name}
                onClick={() => onToggle(name)}
                className="chip"
                style={{
                  cursor: "pointer",
                  background: on ? "var(--blue)" : "var(--bg)",
                  color: on ? "#fff" : "var(--text)",
                  border: `1px solid ${on ? "var(--blue)" : "var(--border-strong)"}`,
                }}
              >
                {on && <Icon name="check" size={12} stroke={2.6} />}
                {name}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

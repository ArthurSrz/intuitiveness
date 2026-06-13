/*
 * design.ts — shared metadata + helpers for the Blue Pulse redesign.
 *
 * Ported from the design handoff (levels.jsx + data.js). The level identities,
 * guided-workflow steps, and per-level narrative copy are static design data;
 * the *values* shown in each view come from the live backend session.
 */
export type Phase = "descent" | "ascent" | "pivot";

/** The five granularity levels, top (L4 raw) → bottom (L0 datum). */
export interface LevelMeta {
  n: number;
  code: string;
  name: string;
  glyph: string;
  tag: string;
}

export const LEVELS: LevelMeta[] = [
  { n: 4, code: "L4", name: "Heterogeneous Sources", glyph: "table", tag: "Unlinkable, multi-source data" },
  { n: 3, code: "L3", name: "Knowledge Graph", glyph: "graph", tag: "Entities linked through shared structure" },
  { n: 2, code: "L2", name: "Domain Table", glyph: "categories", tag: "One coherent domain, categorized" },
  { n: 1, code: "L1", name: "Feature Vector", glyph: "vector", tag: "One variable per entity" },
  { n: 0, code: "L0", name: "Atomic Datum", glyph: "core", tag: "A single certain value" },
];

/** Free-navigation level identities — the five granularity levels (paper §3). */
export const NAV_LEVELS: Record<
  number,
  { code: string; name: string; glyph: string; desc: string }
> = {
  4: { code: "L4", name: "Sources", glyph: "table", desc: "Heterogeneous, unlinkable datasets" },
  3: { code: "L3", name: "Graph", glyph: "graph", desc: "Entities linked through shared structure" },
  2: { code: "L2", name: "Domain", glyph: "categories", desc: "One coherent table · categorized by meaning" },
  1: { code: "L1", name: "Vector", glyph: "vector", desc: "One variable · one value per entity" },
  0: { code: "L0", name: "Datum", glyph: "core", desc: "A single atomic value" },
};

/** Guided-workflow steps — the FULL descent–ascent cycle: L4 → L0, then L0 → L3. */
export interface Step {
  id: string;
  glyph: string;
  title: string;
  level: string;
  phase: Phase;
  stageLevel: number;
  question: string;
}

export const STEPS: Step[] = [
  /* ---- descent: trade away complexity for certainty ---- */
  { id: "upload", glyph: "dataset", title: "Heterogeneous Sources", level: "L4", phase: "descent", stageLevel: 4, question: "Your data as-is — unlinkable, multi-source. The descent trades away complexity one level at a time." },
  { id: "entities", glyph: "graph", title: "Match Entities", level: "L4 → L3", phase: "descent", stageLevel: 3, question: "Trade heterogeneity for structure — connect sources through shared entities." },
  { id: "domains", glyph: "categories", title: "Map Domains", level: "L3 → L2", phase: "descent", stageLevel: 2, question: "Trade domain breadth for coherence — name the categories that carve your data." },
  { id: "features", glyph: "vector", title: "Select Feature", level: "L2 → L1", phase: "descent", stageLevel: 1, question: "Trade dimensionality for legibility — isolate the one variable that matters." },
  { id: "metric", glyph: "core", title: "Aggregate", level: "L1 → L0", phase: "descent", stageLevel: 0, question: "Trade extent for certainty — compress to a single atomic value." },
  /* ---- pivot: the core datum + your intent ---- */
  { id: "intent", glyph: "intent", title: "Set Your Intent", level: "L0", phase: "pivot", stageLevel: 0, question: "You've reached the core datum. What question will you rebuild the data to answer?" },
  /* ---- ascent: rebuild only what your intent needs ---- */
  { id: "rebuild", glyph: "vector", title: "Enrich", level: "L0 → L1", phase: "ascent", stageLevel: 1, question: "Reconstruct a vector — one comparable number per entity, guided by your intent." },
  { id: "split", glyph: "categories", title: "Add Dimensions", level: "L1 → L2", phase: "ascent", stageLevel: 2, question: "Add the categorical dimension that answers your question." },
  { id: "link", glyph: "graph", title: "Link Domains", level: "L2 → L3", phase: "ascent", stageLevel: 3, question: "Link back the one relationship your intent asked for — a dataset built for your question." },
];

/** Header copy keyed by phase + level. */
export const LEVEL_COPY: Record<"descent" | "ascent", Record<number, { title: string; sub: string }>> = {
  descent: {
    4: { title: "Heterogeneous sources", sub: "Multiple unlinkable datasets — every column, every row. The descent trades away complexity to find the core." },
    3: { title: "Relational structure gained", sub: "Sources are now linked through shared entities. You traded heterogeneity for a knowledge graph." },
    2: { title: "Domain coherence gained", sub: "The graph is now a single coherent table, sliced by the categories you named. Breadth traded for focus." },
    1: { title: "Feature legibility gained", sub: "One variable isolated — every entity reduced to a single comparable number. Dimensions traded for clarity." },
    0: { title: "Atomic certainty", sub: "One value remains. This is the floor — the core datum. Extent traded for certainty." },
  },
  ascent: {
    0: { title: "The core datum — with intent", sub: "The descent found the floor. The ascent rebuilds upward, but only the dimensions your question needs." },
    1: { title: "Vector rebuilt with purpose", sub: "The datum is re-expanded into a feature vector — one number per entity, guided by your intent." },
    2: { title: "Dimensions shaped by your question", sub: "Categorical dimensions added — a purposeful cut that answers what you came to ask." },
    3: { title: "A dataset built for your question", sub: "Domains linked by the relationship your intent asked for. Ready for analysis." },
  },
};

/** Intent options for the ascent pivot (client-side narrative). */
export interface Intent {
  id: string;
  question: string;
  short: string;
}

export const INTENTS: Intent[] = [
  { id: "compare", question: "Which groups have the highest and lowest values?", short: "Top vs bottom" },
  { id: "trend", question: "How does this change over time or across regions?", short: "Trends" },
  { id: "outlier", question: "Are there unusual values that stand out?", short: "Outliers" },
];

/* ----------------------------- helpers ----------------------------------- */

const STOP = new Set(["collège", "de", "des", "du", "la", "le", "les", "d'", "aux", "à"]);

/** Two-letter initials for an entity label (drops common French stop-words). */
export function initials(name: string): string {
  const words = name
    .split(/[\s’']+/)
    .filter((w) => w && !STOP.has(w.toLowerCase()));
  return words
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

function lerp(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t);
}

/**
 * Map a normalized 0..1 position to the neutral-slate → blue gradient that
 * carries the whole design. Pass a value plus its [min,max] domain.
 */
export function gradientColor(t: number): string {
  const c = Math.max(0, Math.min(1, t));
  return `rgb(${lerp(83, 29, c)}, ${lerp(100, 161, c)}, ${lerp(113, 242, c)})`;
}

/** Color a numeric value within a domain (e.g. a score or vector entry). */
export function scoreColor(value: number, min = 0, max = 100): string {
  const span = max - min || 1;
  return gradientColor((value - min) / span);
}

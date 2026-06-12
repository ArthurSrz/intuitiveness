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
  { n: 4, code: "L4", name: "Raw Dataset", glyph: "table", tag: "Original tabular data" },
  { n: 3, code: "L3", name: "Entity Graph", glyph: "graph", tag: "A graph of relationships" },
  { n: 2, code: "L2", name: "Domain Categories", glyph: "categories", tag: "Grouped by meaning" },
  { n: 1, code: "L1", name: "Feature Vector", glyph: "vector", tag: "One number per entity" },
  { n: 0, code: "L0", name: "Core Datum", glyph: "core", tag: "A single atomic truth" },
];

/** Free-navigation level identities — the five granularity levels (paper §3). */
export const NAV_LEVELS: Record<
  number,
  { code: string; name: string; glyph: string; desc: string }
> = {
  4: { code: "L4", name: "Unlinkable", glyph: "table", desc: "Unlinkable, multi-level datasets" },
  3: { code: "L3", name: "Linkable", glyph: "graph", desc: "Linkable, multi-level datasets" },
  2: { code: "L2", name: "Table", glyph: "categories", desc: "One dataset · several entities & attributes" },
  1: { code: "L1", name: "Vector", glyph: "vector", desc: "One entity (or attribute) · several values" },
  0: { code: "L0", name: "Value", glyph: "core", desc: "A single entity-attribute-value triplet" },
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
  /* ---- descent: strip complexity to the core ---- */
  { id: "upload", glyph: "dataset", title: "Your Raw Dataset", level: "L4", phase: "descent", stageLevel: 4, question: "This is your data as-is — every column, every row. The descent will strip it down to its core." },
  { id: "entities", glyph: "graph", title: "Define Entities", level: "L4 → L3", phase: "descent", stageLevel: 3, question: "What are the main entities you want in your knowledge graph?" },
  { id: "domains", glyph: "categories", title: "Isolate Domains", level: "L3 → L2", phase: "descent", stageLevel: 2, question: "Query the graph to isolate domain-specific subsets" },
  { id: "features", glyph: "vector", title: "Extract Features", level: "L2 → L1", phase: "descent", stageLevel: 1, question: "Extract a column to create vectors for analysis" },
  { id: "metric", glyph: "core", title: "Compute Metric", level: "L1 → L0", phase: "descent", stageLevel: 0, question: "What aggregation metric do you want to compute?" },
  /* ---- pivot: the core datum + your intent ---- */
  { id: "intent", glyph: "intent", title: "Set Your Intent", level: "L0", phase: "pivot", stageLevel: 0, question: "You've reached the core datum. What question will you rebuild the data to answer?" },
  /* ---- ascent: rebuild only what your intent needs ---- */
  { id: "rebuild", glyph: "vector", title: "Rebuild Vector", level: "L0 → L1", phase: "ascent", stageLevel: 1, question: "Re-expand the datum into one comparable number per entity" },
  { id: "split", glyph: "categories", title: "Categorize", level: "L1 → L2", phase: "ascent", stageLevel: 2, question: "Split the vector by the line that answers your question" },
  { id: "link", glyph: "graph", title: "Link & Build", level: "L2 → L3", phase: "ascent", stageLevel: 3, question: "Add back the one relationship your intent asked for" },
];

/** Header copy keyed by phase + level. */
export const LEVEL_COPY: Record<"descent" | "ascent", Record<number, { title: string; sub: string }>> = {
  descent: {
    4: { title: "The dataset, exactly as published", sub: "Every column, every row. Most of it isn't what you came for — the descent begins by facing the full complexity." },
    3: { title: "Keep the entities, drop the noise", sub: "Columns collapse to what matters: each entity, how big it is, and how it scored — now a graph of entities and one relationship." },
    2: { title: "Name the categories that matter", sub: "Group the entities by a human idea the raw table never stated outright." },
    1: { title: "Reduce each entity to one number", sub: "Strip the categories. Every entity becomes a single comparable value — the dataset is now one feature vector." },
    0: { title: "The single truth underneath", sub: "Average everything that's left and one atomic value remains. This is the floor of the descent — the core datum." },
  },
  ascent: {
    0: { title: "Start from the truth — with intent", sub: "The descent found the floor. The ascent rebuilds upward, but this time only the dimensions your question needs." },
    1: { title: "Re-expand into one number per entity", sub: "Unfold the datum back into a feature vector — every entity, scored — ready to be shaped by your intent." },
    2: { title: "Split by the line that answers you", sub: "Categorise around the median: results above versus below. A purposeful cut, not an arbitrary one." },
    3: { title: "A dataset built for your question", sub: "Add back exactly one relationship — the one your intent asked for." },
  },
};

/** Intent options for the ascent pivot (client-side narrative). */
export interface Intent {
  id: string;
  question: string;
  short: string;
}

export const INTENTS: Intent[] = [
  { id: "class-size", question: "Do smaller classes lead to higher results?", short: "Class size → results" },
  { id: "locale", question: "Are countryside schools outperforming downtown?", short: "Locale → results" },
  { id: "ips", question: "Does social position (IPS) drive results?", short: "Social index → results" },
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

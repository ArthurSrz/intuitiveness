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
  { n: 4, code: "L4", name: "Your raw files", glyph: "table", tag: "All your data files, not yet connected" },
  { n: 3, code: "L3", name: "Connected data", glyph: "graph", tag: "Files linked through shared columns" },
  { n: 2, code: "L2", name: "Grouped table", glyph: "categories", tag: "Data organized into categories" },
  { n: 1, code: "L1", name: "Values list", glyph: "vector", tag: "One number per item" },
  { n: 0, code: "L0", name: "Summary number", glyph: "core", tag: "One number that captures the big picture" },
];

/** Free-navigation level identities — the five granularity levels (paper §3). */
export const NAV_LEVELS: Record<
  number,
  { code: string; name: string; glyph: string; desc: string }
> = {
  4: { code: "L4", name: "Raw files", glyph: "table", desc: "Your data files, not yet connected" },
  3: { code: "L3", name: "Connected", glyph: "graph", desc: "Files linked through shared columns" },
  2: { code: "L2", name: "Grouped", glyph: "categories", desc: "One table, organized into categories" },
  1: { code: "L1", name: "Values", glyph: "vector", desc: "One number per item" },
  0: { code: "L0", name: "Summary", glyph: "core", desc: "One number that captures the big picture" },
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
  { id: "upload", glyph: "dataset", title: "Load your data", level: "Step 1", phase: "descent", stageLevel: 4, question: "Start with your raw files. We will simplify them step by step." },
  { id: "entities", glyph: "graph", title: "Find what connects your files", level: "Step 2", phase: "descent", stageLevel: 3, question: "The app looks for shared columns so your files can talk to each other." },
  { id: "domains", glyph: "categories", title: "Group into categories", level: "Step 3", phase: "descent", stageLevel: 2, question: "Organize your data into meaningful groups for easier analysis." },
  { id: "features", glyph: "vector", title: "Pick the key number", level: "Step 4", phase: "descent", stageLevel: 1, question: "Choose the single measurement that matters most to you." },
  { id: "metric", glyph: "core", title: "Get the summary", level: "Step 5", phase: "descent", stageLevel: 0, question: "Compress everything into one number that captures the big picture." },
  /* ---- pivot: the core datum + your intent ---- */
  { id: "intent", glyph: "intent", title: "Ask your question", level: "Pivot", phase: "pivot", stageLevel: 0, question: "You have one summary number. Now decide: what question do you want your data to answer?" },
  /* ---- ascent: rebuild only what your intent needs ---- */
  { id: "rebuild", glyph: "vector", title: "Expand the details", level: "Step 6", phase: "ascent", stageLevel: 1, question: "Bring back individual values, but only the ones relevant to your question." },
  { id: "split", glyph: "categories", title: "Compare groups", level: "Step 7", phase: "ascent", stageLevel: 2, question: "Split into groups so you can spot differences and patterns." },
  { id: "link", glyph: "graph", title: "Bring in related data", level: "Step 8", phase: "ascent", stageLevel: 3, question: "Connect to other datasets to test whether your insight holds up." },
];

/** Header copy keyed by phase + level. */
export const LEVEL_COPY: Record<"descent" | "ascent", Record<number, { title: string; sub: string }>> = {
  descent: {
    4: { title: "Your raw data", sub: "All your files loaded. We will simplify them step by step to find the essential number." },
    3: { title: "Files connected", sub: "Your files are now linked through columns they share. This lets us work with them as one dataset." },
    2: { title: "Data grouped", sub: "Your data is organized into meaningful categories, making it easier to spot patterns." },
    1: { title: "One number per item", sub: "Each item now has a single comparable value. We are almost at the summary." },
    0: { title: "The big picture", sub: "Everything compressed into one number. This is your starting point for analysis." },
  },
  ascent: {
    0: { title: "Your question", sub: "You have the summary. Now choose what question you want to answer — we will rebuild the data around it." },
    1: { title: "Details restored", sub: "Individual values are back, but only the ones relevant to your question." },
    2: { title: "Groups compared", sub: "Your data is split into groups so you can see differences and test your question." },
    3: { title: "Related data added", sub: "Other datasets brought in to put your insight to the test." },
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

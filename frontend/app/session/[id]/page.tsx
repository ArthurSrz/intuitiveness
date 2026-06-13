"use client";

import { use, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  useAddSource,
  useAddSourceUrl,
  useAddSourceWorldBank,
  useAscend,
  useDescend,
  useNode,
  useSession,
  useTimeTravel,
  useTree,
  useInvalidateSession,
} from "@/lib/api/hooks";
import { apiGet } from "@/lib/api/client";
import { API_BASE_URL, ApiError } from "@/lib/api/client";
import { decodeValue } from "@/lib/payload";
import type { AscendMove, SessionState, TreeResponse } from "@/lib/api/types";
import { LevelView } from "@/components/levels/LevelView";
import { L0Datum } from "@/components/levels/L0Datum";
import { Icon } from "@/components/ui/Icon";
import { StatusBadge } from "@/components/StatusBadge";
import { Brand, LevelLadder, ModeToggle, WorkflowSidebar } from "@/components/shell/Sidebar";
import { GuidedHeader, WorkflowNav } from "@/components/shell/Guided";
import { ExploreMetrics, ExploreNavOptions } from "@/components/shell/Explore";
import { CoreCard, IntentCard, JourneyCard } from "@/components/shell/Context";
import {
  EdgeControls,
  buildAscendBody,
  buildDescendBody,
  defaultEdgeParams,
  type EdgeParams,
} from "@/components/shell/EdgeControls";
import {
  INTENTS,
  LEVEL_COPY,
  NAV_LEVELS,
  STEPS,
  type Phase,
} from "@/lib/design";

/*
 * Session orchestrator — the Blue Pulse app shell (app.jsx) wired to the live
 * FastAPI session. Two modes share one backend session:
 *
 *   Guided   — the 9-step descent→ascent cycle. The step index is DERIVED from
 *              the session's real position (current_level + the move that made
 *              the current node), so "Next" runs an actual descend/ascend and
 *              the checklist always reflects true state.
 *   Explore  — free one-level-at-a-time descend/ascend via available_moves.
 *
 * Movement is real: descend/ascend mutate the backend; Previous time-travels to
 * the parent node; Start over time-travels to the root.
 */

const TOTAL_STEPS = STEPS.length;

export default function SessionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();

  // ---- server state ----
  const session = useSession(id);
  const tree = useTree(id);
  const node = useNode(id, session.data?.current_node_id);

  // ---- mutations ----
  const invalidate = useInvalidateSession(id);
  const descend = useDescend(id);
  const ascend = useAscend(id);
  const timeTravel = useTimeTravel(id);
  const addSource = useAddSource(id);
  const addSourceUrl = useAddSourceUrl(id);
  const addSourceWB = useAddSourceWorldBank(id);
  const addSourceRef = useRef<HTMLInputElement>(null);
  const [addSourcePanel, setAddSourcePanel] = useState(false);
  const [addSourceTab, setAddSourceTab] = useState<"datagouv" | "worldbank" | "upload">("datagouv");
  const [dgQuery, setDgQuery] = useState("");
  const [dgResults, setDgResults] = useState<Array<{id:string;title:string;organization:string;has_csv:boolean}> | null>(null);
  const [dgBusy, setDgBusy] = useState(false);
  const [dgError, setDgError] = useState<string|null>(null);
  const [dgImportingId, setDgImportingId] = useState<string|null>(null);
  const [wbQuery, setWbQuery] = useState("");
  const [wbResults, setWbResults] = useState<Array<{id:string;name:string;database_id:string}> | null>(null);
  const [wbBusy, setWbBusy] = useState(false);
  const [wbError, setWbError] = useState<string|null>(null);
  const [wbImportingId, setWbImportingId] = useState<string|null>(null);
  const pending =
    descend.isPending || ascend.isPending || timeTravel.isPending || node.isFetching;

  // ---- client narrative state ----
  const [mode, setMode] = useState<"guided" | "explore">("guided");
  const [intentId, setIntentId] = useState(INTENTS[0].id);
  const [intentPivot, setIntentPivot] = useState(false);
  const [stepsTaken, setStepsTaken] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [dark, setDark] = useState(false);
  const [showContext, setShowContext] = useState(true);
  // Per-edge transition parameters — set inline in each level view, used by Next.
  const [edgeParams, setEdgeParams] = useState<EdgeParams>(defaultEdgeParams);
  const patchEdge = (patch: Partial<EdgeParams>) =>
    setEdgeParams((p) => ({ ...p, ...patch }));

  // theme tweak → :root
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }, [dark]);

  const currentLevel = session.data?.current_level ?? 4;

  // The engine stores every node's action as "entry", so phase can't come from
  // it. Instead we read it from the tree: a node whose PARENT sits at a lower
  // level was reached by ascending; otherwise we're descending.
  const { phase, parentId } = useMemo(() => {
    const nodes = tree.data?.nodes ?? [];
    const cur = nodes.find((n) => n.id === session.data?.current_node_id);
    const parent = cur?.parent_id ? nodes.find((n) => n.id === cur.parent_id) : undefined;
    const ph: Phase = parent && cur && parent.level < cur.level ? "ascent" : "descent";
    return { phase: ph, parentId: cur?.parent_id ?? null };
  }, [tree.data, session.data]);

  const coreReached = useMemo(
    () => (tree.data?.nodes ?? []).some((n) => n.level === 0),
    [tree.data],
  );
  const datum = useMemo(
    () => deriveDatum(currentLevel, session.data, node.data?.payload, tree.data),
    [currentLevel, session.data, node.data, tree.data],
  );
  // The L0 value only appears in the session summary while we sit at L0 (the
  // tree's L0 node carries no snapshot), so remember it for the ascent —
  // persisted per session so a page reload mid-ascent keeps the core datum.
  const datumKey = `intuitiveness:datum:${id}`;
  const [seenDatum, setSeenDatum] = useState<string | null>(null);
  useEffect(() => {
    const stored = sessionStorage.getItem(datumKey);
    if (stored) setSeenDatum(stored);
  }, [datumKey]);
  useEffect(() => {
    if (datum != null) {
      setSeenDatum(datum);
      sessionStorage.setItem(datumKey, datum);
    }
  }, [datum, datumKey]);
  const shownDatum = datum ?? seenDatum;

  // Derived guided step index. Each step represents "you are at this level,
  // about to do the next transition". L4=0, L3=2 (Map Domains), L2=3, etc.
  const stepIndex = useMemo(() => {
    if (intentPivot && currentLevel === 0) return 5;
    if (phase === "ascent" && currentLevel >= 1) return 5 + currentLevel;
    if (currentLevel === 4) return 0;
    return 5 - currentLevel;
  }, [intentPivot, currentLevel, phase]);
  const step = STEPS[Math.max(0, Math.min(TOTAL_STEPS - 1, stepIndex))];

  const canDescend = (session.data?.available_moves?.descend?.length ?? 0) > 0;
  const canAscend = (session.data?.available_moves?.ascend?.length ?? 0) > 0;
  const ascendMove = session.data?.available_moves?.ascend?.[0] as AscendMove | undefined;

  // Which transition the guided "Next" will run (so EdgeControls shows the
  // matching inputs) — null on the L0 pivot and final export steps.
  const guidedEdge: { dir: "descend" | "ascend"; level: number } | null =
    stepIndex <= 4 && stepIndex > 0
      ? { dir: "descend", level: currentLevel }
      : stepIndex === 5
        ? { dir: "ascend", level: 0 }
        : stepIndex === 6 || stepIndex === 7
          ? { dir: "ascend", level: currentLevel }
          : null;

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2600);
  }

  function handleAddSource(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    addSource.mutate(files, {
      onSuccess: () => { flash(`Added ${files.length} source${files.length === 1 ? "" : "s"}`); setAddSourcePanel(false); },
    });
    if (addSourceRef.current) addSourceRef.current.value = "";
  }

  async function handleDgSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!dgQuery.trim()) return;
    setDgBusy(true); setDgError(null); setDgResults(null);
    try {
      const res = await apiGet<{datasets: Array<{id:string;title:string;organization:string;has_csv:boolean}>}>(`/search?q=${encodeURIComponent(dgQuery)}&size=8`);
      setDgResults(res.datasets);
      if (!res.datasets.length) setDgError("No CSV datasets found.");
    } catch { setDgError("Search unavailable."); }
    finally { setDgBusy(false); }
  }

  function handleDgImport(ds: {id:string;title:string}) {
    setDgImportingId(ds.id);
    addSourceUrl.mutate({ url: `https://www.data.gouv.fr/fr/datasets/${ds.id}/`, filename: ds.title + ".csv" }, {
      onSuccess: () => { setAddSourcePanel(false); setDgImportingId(null); },
      onError: () => { setDgError("Import failed."); setDgImportingId(null); },
    });
  }

  async function handleWbSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!wbQuery.trim()) return;
    setWbBusy(true); setWbError(null); setWbResults(null);
    try {
      const res = await apiGet<{indicators: Array<{id:string;name:string;database_id:string}>}>(`/search/worldbank?q=${encodeURIComponent(wbQuery)}&size=8`);
      setWbResults(res.indicators);
      if (!res.indicators.length) setWbError("No indicators found.");
    } catch { setWbError("Search unavailable."); }
    finally { setWbBusy(false); }
  }

  function handleWbImport(ind: {id:string;name:string;database_id:string}) {
    setWbImportingId(ind.id);
    addSourceWB.mutate({ indicator_id: ind.id, database_id: ind.database_id, indicator_name: ind.name }, {
      onSuccess: () => { setAddSourcePanel(false); setWbImportingId(null); },
      onError: () => { setWbError("Import failed."); setWbImportingId(null); },
    });
  }

  // Reset the captured params after a move so the next edge starts clean.
  const afterMove = { onSuccess: () => setEdgeParams(defaultEdgeParams()) };

  const multiSource = (session.data?.options?.sources?.length ?? 0) > 1;

  // ---- guided transitions ----
  // Most transitions are handled by AI-powered buttons in each level view.
  // guidedNext only handles: L4 single-source descent, L0 pivot, and export.
  function guidedNext() {
    if (currentLevel === 4 && !multiSource) {
      descend.mutate(buildDescendBody(currentLevel, edgeParams, session.data?.options), afterMove);
    } else if (currentLevel === 0 && !intentPivot) {
      setIntentPivot(true);
    } else if (currentLevel === 0 && intentPivot) {
      // Intent selected — trigger L0→L1 ascent with source_expansion
      ascend.mutate({ enrichment_func: "source_expansion" }, afterMove);
    } else if (stepIndex >= TOTAL_STEPS - 1) {
      void exportDataset();
    }
    // All other transitions: use the AI button in the level view
  }
  function guidedPrev() {
    if (stepIndex === 5) {
      setIntentPivot(false); // pivot → L0 metric, no move
      return;
    }
    if (stepIndex === 6) setIntentPivot(true); // landing back on L0 shows the pivot
    if (parentId) timeTravel.mutate(parentId);
  }
  function resetWorkflow() {
    setIntentPivot(false);
    if (tree.data?.root_id) timeTravel.mutate(tree.data.root_id);
  }

  // ---- explore transitions ----
  function exploreDescend() {
    if (currentLevel === 4 && multiSource) return;
    setStepsTaken((s) => s + 1);
    descend.mutate(buildDescendBody(currentLevel, edgeParams, session.data?.options), afterMove);
  }
  function exploreAscend() {
    setStepsTaken((s) => s + 1);
    ascend.mutate(buildAscendBody(currentLevel, edgeParams), afterMove);
  }

  function switchMode(m: "guided" | "explore") {
    if (m === mode) return;
    if (m === "explore") setStepsTaken(0);
    setMode(m);
  }

  async function exportDataset() {
    try {
      const res = await fetch(`${API_BASE_URL}/sessions/${id}/export`);
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const record = await res.json();
      const blob = new Blob([JSON.stringify(record, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `intuitiveness-${id}.json`;
      a.click();
      URL.revokeObjectURL(url);
      flash("Exported · intuitiveness-dataset.json");
    } catch (e) {
      flash(e instanceof Error ? e.message : "Export failed");
    }
  }

  const goHome = () => router.push("/");

  // ---- error / loading ----
  if (session.isError) {
    const err = session.error as ApiError;
    return (
      <div style={{ padding: 40, maxWidth: 640, margin: "0 auto" }}>
        <div className="card" style={{ borderColor: "var(--error)", color: "var(--error)" }}>
          Could not load session: {err.displayMessage}
        </div>
        <button className="pill-btn ghost" style={{ marginTop: 16 }} onClick={goHome}>
          <Icon name="up" size={16} /> Back to start
        </button>
      </div>
    );
  }

  const mutationError = (descend.error ?? ascend.error ?? timeTravel.error) as ApiError | null;
  const stats = buildStats(session.data, shownDatum, phase, currentLevel);
  const navState: "entry" | "exploring" = stepsTaken === 0 ? "entry" : "exploring";
  const copy = LEVEL_COPY[phase === "ascent" ? "ascent" : "descent"][currentLevel];

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* ---------------- left sidebar ---------------- */}
      <aside
        className="nav-col"
        style={{
          width: "var(--nav-w)",
          flex: "none",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          padding: "18px 14px 16px",
          gap: 16,
          overflowY: "auto",
        }}
      >
        <Brand onHome={goHome} />
        <ModeToggle mode={mode} onMode={switchMode} />
        <div style={{ flex: 1, minHeight: 0 }}>
          {mode === "guided" ? (
            <WorkflowSidebar stepIndex={stepIndex} onReset={resetWorkflow} />
          ) : (
            <>
              <div className="t-label" style={{ color: "var(--text-2)", padding: "2px 4px 10px" }}>
                GRANULARITY LADDER
              </div>
              <LevelLadder levelN={currentLevel} phase={phase} />
            </>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, justifyContent: "center" }}>
          <button
            className="icon-btn"
            title="Toggle dark mode"
            onClick={() => setDark((d) => !d)}
            style={{ width: 30, height: 30 }}
          >
            <Icon name={dark ? "spark" : "moon"} size={15} />
          </button>
          <button
            className="icon-btn"
            title="Toggle context panel"
            onClick={() => setShowContext((c) => !c)}
            style={{ width: 30, height: 30, color: showContext ? "var(--blue)" : "var(--text-2)" }}
          >
            <Icon name="info" size={15} />
          </button>
        </div>
      </aside>

      {/* ---------------- main ---------------- */}
      <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* slim top bar: status + export */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "12px 28px",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <span className="t-meta mono">session {id.slice(0, 8)}</span>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
            <button className="pill-btn ghost" style={{ height: 34 }} onClick={() => void exportDataset()}>
              <Icon name="export" size={15} /> Export
            </button>
            <StatusBadge />
          </div>
        </div>

        <div style={{ flex: 1, overflowY: "auto" }}>
          <div style={{ maxWidth: 760, margin: "0 auto", padding: "0 28px 40px", width: "100%" }}>
            {mode === "guided" ? (
              <>
                <GuidedHeader step={step} />
                <div key={`g-${stepIndex}`} className={phase === "ascent" ? "stage-anim-up" : "stage-anim-down"}>
                  {stepIndex === 5 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
                      {node.data && <L0Datum node={node.data} sessionId={id} />}
                      <IntentCard value={intentId} onChange={setIntentId} active sessionId={id} />
                    </div>
                  ) : node.isLoading || !node.data ? (
                    <StagePlaceholder />
                  ) : (
                    <LevelView
                      node={node.data}
                      level={currentLevel}
                      onAddSource={currentLevel === 4 ? () => setAddSourcePanel(true) : undefined}
                      sessionId={id}
                      onConnect={invalidate}
                    />
                  )}
                </div>
                <WorkflowNav
                  stepIndex={stepIndex}
                  total={TOTAL_STEPS}
                  onPrev={guidedPrev}
                  onNext={guidedNext}
                  pending={pending}
                  lastAction={{ label: "Export dataset", onClick: () => void exportDataset() }}
                />
              </>
            ) : (
              <>
                <div style={{ padding: "22px 4px 18px" }}>
                  <h1
                    className="t-display"
                    style={{ margin: "0 0 4px", fontSize: 28, display: "flex", alignItems: "center", gap: 10 }}
                  >
                    <Icon name="graph" size={26} style={{ color: "var(--blue)" }} stroke={1.9} /> Navigation explorer
                  </h1>
                  <p className="t-body" style={{ margin: 0, color: "var(--text-2)", fontWeight: 600 }}>
                    Move freely through the granularity hierarchy — descend to reduce, ascend to
                    rebuild with intent.
                  </p>
                </div>
                <ExploreMetrics level={currentLevel} stepsTaken={stepsTaken} navState={navState} />
                <ExploreNavOptions
                  level={currentLevel}
                  canDescend={canDescend}
                  canAscend={canAscend}
                  onDescend={exploreDescend}
                  onAscend={exploreAscend}
                  pending={pending}
                />
                {canDescend && (
                  <EdgeControls
                    dir="descend"
                    level={currentLevel}
                    options={session.data?.options}
                    params={edgeParams}
                    onChange={patchEdge}
                  />
                )}
                {canAscend && (
                  <EdgeControls
                    dir="ascend"
                    level={currentLevel}
                    ascendMove={ascendMove}
                    params={edgeParams}
                    onChange={patchEdge}
                  />
                )}
                <div style={{ height: "var(--gap)" }} />
                <div className="divider" />
                <div style={{ padding: "18px 0 6px", display: "flex", alignItems: "center", gap: 9 }}>
                  <Icon name={NAV_LEVELS[currentLevel].glyph} size={17} style={{ color: "var(--text-2)" }} />
                  <span className="t-section" style={{ fontSize: 16 }}>
                    {copy?.title ?? NAV_LEVELS[currentLevel].name}
                  </span>
                  <span
                    className="chip"
                    style={{
                      marginLeft: "auto",
                      background: phase === "descent" ? "var(--neutral-soft)" : "var(--blue-soft)",
                      color: phase === "descent" ? "var(--neutral)" : "var(--blue)",
                    }}
                  >
                    <Icon name={phase === "descent" ? "down" : "up"} size={13} stroke={2.2} />
                    {phase === "descent" ? "Descending" : "Ascending"}
                  </span>
                </div>
                <div key={`e-${phase}-${currentLevel}`} className={phase === "ascent" ? "stage-anim-up" : "stage-anim-down"}>
                  {node.isLoading || !node.data ? (
                    <StagePlaceholder />
                  ) : (
                    <LevelView
                      node={node.data}
                      level={currentLevel}
                      onAddSource={currentLevel === 4 ? () => setAddSourcePanel(true) : undefined}
                      sessionId={id}
                      onConnect={invalidate}
                    />
                  )}
                </div>
              </>
            )}

            {mutationError && (
              <p className="t-meta" style={{ color: "var(--error)", marginTop: 14 }}>
                {mutationError.displayMessage}
              </p>
            )}
          </div>
        </div>
      </main>

      {/* ---------------- right context aside ---------------- */}
      {showContext && (
        <aside
          className="aside-col"
          style={{
            width: "var(--aside-w)",
            flex: "none",
            borderLeft: "1px solid var(--border)",
            overflowY: "auto",
            padding: "20px 18px",
            display: "flex",
            flexDirection: "column",
            gap: "var(--gap)",
          }}
        >
          {(mode === "explore" || (mode === "guided" && (step.phase === "ascent" || step.phase === "pivot"))) && (
            <IntentCard
              value={intentId}
              onChange={setIntentId}
              active={mode === "explore" ? phase === "ascent" : true}
              sessionId={id}
            />
          )}
          <CoreCard reached={coreReached || seenDatum != null} datum={shownDatum ?? undefined} />
          <JourneyCard stats={stats} />
        </aside>
      )}

      <input ref={addSourceRef} type="file" accept=".csv,text/csv" multiple style={{ display: "none" }} onChange={handleAddSource} />

      {/* ---------------- add-source panel ---------------- */}
      {addSourcePanel && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setAddSourcePanel(false)}>
          <div className="card" style={{ width: 480, maxWidth: "94vw", padding: 24, display: "flex", flexDirection: "column", gap: 16 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span className="t-name" style={{ fontSize: 16 }}>Add a source</span>
              <button className="pill-btn ghost" style={{ height: 28, fontSize: 12 }} onClick={() => setAddSourcePanel(false)}>Close</button>
            </div>
            {/* tabs */}
            <div style={{ display: "flex", gap: 6 }}>
              {(["datagouv","worldbank","upload"] as const).map((t) => (
                <button key={t} className={`pill-btn ${addSourceTab === t ? "primary" : "ghost"}`} style={{ height: 30, fontSize: 12 }} onClick={() => setAddSourceTab(t)}>
                  {t === "datagouv" ? "data.gouv.fr" : t === "worldbank" ? "World Bank" : "Upload CSV"}
                </button>
              ))}
            </div>

            {addSourceTab === "datagouv" && (
              <form onSubmit={handleDgSearch} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <input autoFocus type="text" value={dgQuery} onChange={(e) => setDgQuery(e.target.value)} placeholder={`"énergie", "résultats brevet"…`} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--surface)", padding: "9px 12px", fontFamily: "var(--font)", fontSize: 14, color: "var(--text)", outline: "none" }} />
                <button type="submit" className="pill-btn primary" style={{ justifyContent: "center" }} disabled={dgBusy || !dgQuery.trim()}>{dgBusy ? "Searching…" : "Search"}</button>
                {dgError && <p className="t-meta" style={{ color: "var(--error)", margin: 0 }}>{dgError}</p>}
                {dgResults && dgResults.map((ds) => (
                  <div key={ds.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="t-name" style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ds.title}</div>
                      <div className="t-meta" style={{ fontSize: 11.5 }}>{ds.organization}</div>
                    </div>
                    <button className="pill-btn ghost" style={{ height: 28, fontSize: 12, flex: "none" }} disabled={!!dgImportingId} onClick={() => handleDgImport(ds)}>
                      {dgImportingId === ds.id ? "…" : "Import"}
                    </button>
                  </div>
                ))}
              </form>
            )}

            {addSourceTab === "worldbank" && (
              <form onSubmit={handleWbSearch} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <input autoFocus type="text" value={wbQuery} onChange={(e) => setWbQuery(e.target.value)} placeholder={`"GDP", "fertility rate"…`} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--surface)", padding: "9px 12px", fontFamily: "var(--font)", fontSize: 14, color: "var(--text)", outline: "none" }} />
                <button type="submit" className="pill-btn primary" style={{ justifyContent: "center" }} disabled={wbBusy || !wbQuery.trim()}>{wbBusy ? "Searching…" : "Search"}</button>
                {wbError && <p className="t-meta" style={{ color: "var(--error)", margin: 0 }}>{wbError}</p>}
                {wbResults && wbResults.map((ind) => (
                  <div key={ind.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="t-name" style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ind.name}</div>
                      <div className="t-meta mono" style={{ fontSize: 11 }}>{ind.id}</div>
                    </div>
                    <button className="pill-btn ghost" style={{ height: 28, fontSize: 12, flex: "none" }} disabled={!!wbImportingId} onClick={() => handleWbImport(ind)}>
                      {wbImportingId === ind.id ? "…" : "Load"}
                    </button>
                  </div>
                ))}
              </form>
            )}

            {addSourceTab === "upload" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <p className="t-meta" style={{ margin: 0 }}>Upload one or more CSV files to add to this session.</p>
                <button className="pill-btn primary" style={{ justifyContent: "center" }} onClick={() => addSourceRef.current?.click()}>
                  {addSource.isPending ? "Uploading…" : "Choose CSV files"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---------------- toast ---------------- */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: 28,
            left: "50%",
            transform: "translateX(-50%)",
            background: "var(--ink)",
            color: "var(--bg)",
            padding: "12px 18px",
            borderRadius: 999,
            boxShadow: "var(--shadow-2)",
            display: "flex",
            alignItems: "center",
            gap: 10,
            zIndex: 50,
            animation: "popIn .2s ease both",
          }}
        >
          <Icon name="check" size={17} style={{ color: "var(--success)" }} stroke={2.6} />
          <span className="t-body" style={{ fontWeight: 600 }}>
            {toast}
          </span>
        </div>
      )}
    </div>
  );
}

function StagePlaceholder() {
  return (
    <div className="card" style={{ color: "var(--text-2)" }}>
      <span className="t-meta">Loading the current level…</span>
    </div>
  );
}

/** The L0 value, as a display string — from the current node or the tree's L0 node. */
function deriveDatum(
  level: number,
  session: SessionState | undefined,
  payload: unknown,
  tree: TreeResponse | undefined,
): string | null {
  let value: unknown = null;
  if (level === 0) {
    // The session summary carries the clean numeric value; the node payload is
    // a zlib+base64-encoded scalar — prefer the former, decode the latter.
    const v = session?.summary?.value;
    value = typeof v === "number" ? v : decodeValue(payload);
  } else if (tree) {
    const l0 = tree.nodes.find((n) => n.level === 0);
    const ov = l0?.output_snapshot?.value;
    value = typeof ov === "number" ? ov : decodeValue(ov ?? null);
  }
  if (value == null) return null;
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
  }
  return String(value);
}

/** Reduction stats for the journey card, read from the live session summary. */
function buildStats(
  session: SessionState | undefined,
  datum: string | null,
  phase: Phase,
  level: number,
): { k: string; v: string; accent?: boolean }[] {
  const summary = session?.summary ?? {};
  const stats: { k: string; v: string; accent?: boolean }[] = [];

  const rows = num(summary.rows ?? summary.n_rows ?? summary.length);
  const cols = num(summary.cols ?? summary.columns ?? summary.n_cols);
  if (rows != null && cols != null) {
    stats.push({ k: "Current shape", v: `${rows} × ${cols}` });
  } else if (rows != null) {
    stats.push({ k: "Current shape", v: `${rows} values` });
  }

  stats.push({ k: "Level", v: NAV_LEVELS[level].code });
  stats.push({ k: "Core datum", v: datum ?? "—" });
  stats.push({
    k: "Phase",
    v: phase === "ascent" ? "Ascending" : "Descending",
    accent: phase === "ascent",
  });
  return stats;
}

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

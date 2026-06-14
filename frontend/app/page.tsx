"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useCreateSession, useUploadCsv, useImportUrl, useImportWorldBank } from "@/lib/api/hooks";
import { apiGet, ApiError } from "@/lib/api/client";
import type { DemoSource } from "@/lib/api/types";
import { Icon } from "@/components/ui/Icon";
import { gradientColor } from "@/lib/design";

interface DatasetResult {
  id: string;
  title: string;
  description: string;
  organization: string;
  has_csv: boolean;
  resource_count: number;
}

interface SearchResponse {
  datasets: DatasetResult[];
  total: number;
  has_more: boolean;
}

interface WBIndicator {
  id: string;
  name: string;
  database_id: string;
  score: number;
}

interface WBSearchResponse {
  indicators: WBIndicator[];
  total: number;
}

/*
 * Landing — the "Interactive Data Redesign Method" entry screen, recreated from
 * the Blue Pulse design (landing.jsx): hero + descent/ascent diagram, a
 * federated search bar, the paper's two demo use-cases, an upload row, and the
 * UNESCO / author footer.
 *
 * Every entry action creates a real backend session (useCreateSession) and
 * routes to /session/{id}. The two demo cards map to live demo sources.
 */
export default function HomePage() {
  const router = useRouter();
  const createSession = useCreateSession();
  const uploadCsv = useUploadCsv();
  const importUrl = useImportUrl();
  const importWB = useImportWorldBank();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pendingSource, setPendingSource] = useState<DemoSource | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  // which source panel is expanded: "datagouv" | "worldbank" | "upload" | null
  const [activePanel, setActivePanel] = useState<"datagouv" | "worldbank" | "upload" | null>(null);
  // data.gouv.fr search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<DatasetResult[] | null>(null);
  const [searchBusy, setSearchBusy] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [importingId, setImportingId] = useState<string | null>(null);
  // World Bank search
  const [wbQuery, setWbQuery] = useState("");
  const [wbResults, setWbResults] = useState<WBIndicator[] | null>(null);
  const [wbBusy, setWbBusy] = useState(false);
  const [wbError, setWbError] = useState<string | null>(null);
  const [wbImportingId, setWbImportingId] = useState<string | null>(null);

  // First visit plays the animated descent–ascent intro (served from
  // /public/intro). Once "Enter the app" / "Skip intro" is clicked it sets the
  // flag, so we only auto-redirect the very first time. Gate the render until
  // we've checked, so first-timers never flash the landing before the intro.
  const [introChecked, setIntroChecked] = useState(false);
  useEffect(() => {
    try {
      if (!localStorage.getItem("intuitiveness:intro-seen")) {
        window.location.href = "/intro/index.html";
        return;
      }
    } catch {
      // localStorage unavailable — just show the landing.
    }
    setIntroChecked(true);
  }, []);

  function start(source: DemoSource) {
    setPendingSource(source);
    createSession.mutate(
      { source },
      {
        onSuccess: (state) => router.push(`/session/${state.session_id}`),
        onError: () => setPendingSource(null),
      },
    );
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchBusy(true);
    setSearchError(null);
    setSearchResults(null);
    try {
      const res = await apiGet<SearchResponse>(`/search?q=${encodeURIComponent(searchQuery)}&size=8`);
      setSearchResults(res.datasets);
      if (res.datasets.length === 0) setSearchError("No datasets found — try different keywords.");
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.displayMessage : "Search unavailable.");
    } finally {
      setSearchBusy(false);
    }
  }

  function handleImportDataset(ds: DatasetResult) {
    setImportingId(ds.id);
    // We import the dataset page URL; the backend resolves its first CSV resource.
    const datagouv_page = `https://www.data.gouv.fr/fr/datasets/${ds.id}/`;
    importUrl.mutate(
      { url: datagouv_page, filename: ds.title + ".csv" },
      {
        onSuccess: (state) => router.push(`/session/${state.session_id}`),
        onError: (err) => {
          setSearchError(err instanceof ApiError ? err.displayMessage : String(err));
          setImportingId(null);
        },
      },
    );
  }

  async function handleWbSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!wbQuery.trim()) return;
    setWbBusy(true);
    setWbError(null);
    setWbResults(null);
    try {
      const res = await apiGet<WBSearchResponse>(`/search/worldbank?q=${encodeURIComponent(wbQuery)}&size=8`);
      setWbResults(res.indicators);
      if (res.indicators.length === 0) setWbError("No indicators found — try different keywords.");
    } catch (err) {
      setWbError(err instanceof ApiError ? err.displayMessage : "World Bank search unavailable.");
    } finally {
      setWbBusy(false);
    }
  }

  function handleWbImport(indicator: WBIndicator) {
    setWbImportingId(indicator.id);
    importWB.mutate(
      { indicator_id: indicator.id, database_id: indicator.database_id, indicator_name: indicator.name },
      {
        onSuccess: (state) => router.push(`/session/${state.session_id}`),
        onError: (err) => {
          setWbError(err instanceof ApiError ? err.displayMessage : String(err));
          setWbImportingId(null);
        },
      },
    );
  }

  function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    setUploadError(null);
    uploadCsv.mutate(files, {
      onSuccess: (state) => router.push(`/session/${state.session_id}`),
      onError: (err) => setUploadError(err instanceof ApiError ? err.displayMessage : String(err)),
    });
    // reset so re-selecting the same file fires onChange again
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const busy = createSession.isPending || uploadCsv.isPending || importUrl.isPending || importWB.isPending;
  const error = (createSession.error ?? uploadError) as ApiError | string | null;

  // Hold the landing back until the intro check runs (avoids a flash before the
  // first-visit redirect to /intro).
  if (!introChecked) {
    return <div style={{ minHeight: "100vh", background: "var(--surface)" }} />;
  }

  return (
    <div style={{ minHeight: "100vh", overflowY: "auto", background: "var(--surface)" }}>
      {/* top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "20px 32px",
          maxWidth: 1080,
          margin: "0 auto",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/intuitiveness_mark.svg"
          alt="Intuitiveness"
          width={40}
          height={40}
          style={{ display: "block", flex: "none", borderRadius: 11 }}
        />
        <div style={{ lineHeight: 1 }}>
          <div className="t-name" style={{ fontWeight: 800, letterSpacing: "-0.02em", fontSize: 17 }}>
            Intuitiveness
          </div>
          <div className="t-meta" style={{ fontSize: 11.5, marginTop: 2 }}>
            make sense of complex data
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <a
            href="/intro/index.html"
            className="chip"
            style={{ color: "var(--blue)", background: "var(--blue-soft)", whiteSpace: "nowrap" }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
              <path d="M5 3l16 9-16 9V3z" />
            </svg>{" "}
            Watch the intro
          </a>
          <span className="chip">
            <Icon name="dataset" size={14} /> data.gouv.fr
          </span>
          <span className="chip" style={{ color: "var(--text)" }}>
            <Icon name="info" size={14} /> The paper
          </span>
        </div>
      </div>

      {/* hero */}
      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "12px 32px 56px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
            gap: 40,
            alignItems: "center",
            padding: "20px 0 36px",
          }}
        >
          <div>
            <span
              className="chip"
              style={{ background: "var(--blue-soft)", color: "var(--blue)", marginBottom: 18 }}
            >
              <Icon name="spark" size={14} /> Intuitiveness — the next stage of dataset design
            </span>
            <h1
              style={{
                fontSize: 44,
                lineHeight: 1.05,
                fontWeight: 800,
                letterSpacing: "-0.03em",
                margin: "0 0 16px",
                textWrap: "balance",
              }}
            >
              Design datasets that adapt&nbsp;to the reader
            </h1>
            <p
              className="t-body"
              style={{
                fontSize: 17,
                lineHeight: 1.55,
                color: "var(--text-2)",
                margin: "0 0 24px",
                maxWidth: 482,
                textWrap: "pretty",
              }}
            >
              <b style={{ color: "var(--text)" }}>Intuitive datasets</b> are tabular data whose
              complexity adapts to each reader&apos;s data literacy level. Strip a dataset from{" "}
              <b style={{ color: "var(--text)" }}>chaos</b> down to its{" "}
              <b style={{ color: "var(--text)" }}>core</b>, then rebuild it for your own
              readers&apos; needs.
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
              <button
                className="pill-btn primary lg"
                onClick={() => document.getElementById("entry-options")?.scrollIntoView({ behavior: "smooth" })}
              >
                Start exploring <Icon name="arrowRight" size={18} stroke={2.1} />
              </button>
            </div>
          </div>

          {/* diagram card */}
          <div className="card" style={{ padding: 26, background: "var(--bg)" }}>
            <div className="t-label" style={{ color: "var(--text-2)", marginBottom: 18 }}>
              HOW IT WORKS
            </div>
            <DescentAscentDiagram />
          </div>
        </div>

        {/* entry choice — 3 options */}
        <div id="entry-options" style={{ marginTop: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <span className="t-section" style={{ fontSize: 18 }}>
              Where is your data?
            </span>
            <span className="divider" style={{ flex: 1 }} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--gap)", alignItems: "start" }}>

            {/* Option 1 — data.gouv.fr */}
            <div
              className="card"
              style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14, cursor: activePanel === "datagouv" ? "default" : "pointer", borderColor: activePanel === "datagouv" ? "var(--blue)" : undefined }}
              onClick={() => activePanel !== "datagouv" && setActivePanel("datagouv")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 36, height: 36, borderRadius: 9, flex: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", background: activePanel === "datagouv" ? "var(--blue)" : "var(--blue-soft)", color: activePanel === "datagouv" ? "#fff" : "var(--blue)" }}>
                  <Icon name="search" size={18} />
                </span>
                <div>
                  <div className="t-label" style={{ color: "var(--text-2)", fontSize: 10.5 }}>OPTION 1</div>
                  <div className="t-name" style={{ fontSize: 15 }}>data.gouv.fr</div>
                </div>
              </div>
              <p className="t-meta" style={{ margin: 0 }}>Hundreds of thousands of French open datasets.</p>
              {activePanel === "datagouv" && (
                <>
                  <form onSubmit={handleSearch} style={{ display: "flex", flexDirection: "column", gap: 8 }} onClick={(e) => e.stopPropagation()}>
                    <input
                      autoFocus
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder={`"résultats du brevet", "énergie"…`}
                      style={{ width: "100%", boxSizing: "border-box", border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--surface)", outline: "none", color: "var(--text)", fontFamily: "var(--font)", fontSize: 14, padding: "9px 12px" }}
                    />
                    <button type="submit" className="pill-btn primary" style={{ width: "100%", justifyContent: "center" }} disabled={searchBusy || !searchQuery.trim()}>
                      {searchBusy ? "Searching…" : <>Search <Icon name="arrowRight" size={15} stroke={2.1} /></>}
                    </button>
                  </form>
                  {searchError && <p className="t-meta" style={{ color: "var(--error)", margin: 0 }}>{searchError}</p>}
                  {searchResults && searchResults.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      {searchResults.map((ds) => (
                        <div key={ds.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div className="t-name" style={{ fontSize: 13, marginBottom: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ds.title}</div>
                            <div className="t-meta" style={{ fontSize: 11.5 }}>{ds.organization}</div>
                          </div>
                          <button className="pill-btn ghost" style={{ height: 30, flex: "none", fontSize: 12 }} disabled={!!importingId || !ds.has_csv} onClick={() => handleImportDataset(ds)}>
                            {importingId === ds.id ? "…" : ds.has_csv ? <>Import <Icon name="arrowRight" size={12} /></> : "No CSV"}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Option 2 — World Bank */}
            <div
              className="card"
              style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14, cursor: activePanel === "worldbank" ? "default" : "pointer", borderColor: activePanel === "worldbank" ? "var(--blue)" : undefined }}
              onClick={() => activePanel !== "worldbank" && setActivePanel("worldbank")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 36, height: 36, borderRadius: 9, flex: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", background: activePanel === "worldbank" ? "var(--blue)" : "var(--blue-soft)", color: activePanel === "worldbank" ? "#fff" : "var(--blue)" }}>
                  <Icon name="core" size={18} />
                </span>
                <div>
                  <div className="t-label" style={{ color: "var(--text-2)", fontSize: 10.5 }}>OPTION 2</div>
                  <div className="t-name" style={{ fontSize: 15 }}>World Bank</div>
                </div>
              </div>
              <p className="t-meta" style={{ margin: 0 }}>Search global development indicators across all countries.</p>
              {activePanel === "worldbank" && (
                <>
                  <form onSubmit={handleWbSearch} style={{ display: "flex", flexDirection: "column", gap: 8 }} onClick={(e) => e.stopPropagation()}>
                    <input
                      autoFocus
                      type="text"
                      value={wbQuery}
                      onChange={(e) => setWbQuery(e.target.value)}
                      placeholder="e.g. fertility rate, GDP, education spending"
                      style={{ width: "100%", boxSizing: "border-box", border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--surface)", outline: "none", color: "var(--text)", fontFamily: "var(--font)", fontSize: 14, padding: "9px 12px" }}
                    />
                    <button type="submit" className="pill-btn primary" style={{ width: "100%", justifyContent: "center" }} disabled={wbBusy || !wbQuery.trim()}>
                      {wbBusy ? "Searching…" : <>Search <Icon name="arrowRight" size={15} stroke={2.1} /></>}
                    </button>
                  </form>
                  {wbError && <p className="t-meta" style={{ color: "var(--error)", margin: 0 }}>{wbError}</p>}
                  {wbResults && wbResults.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      {wbResults.map((ind) => (
                        <div key={ind.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div className="t-name" style={{ fontSize: 13, marginBottom: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ind.name}</div>
                            {/* indicator codes hidden — non-technical users don't need them */}
                          </div>
                          <button className="pill-btn ghost" style={{ height: 30, flex: "none", fontSize: 12 }} disabled={!!wbImportingId} onClick={() => handleWbImport(ind)}>
                            {wbImportingId === ind.id ? "Loading…" : <>Load <Icon name="arrowRight" size={12} /></>}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Option 3 — Upload */}
            <div
              className="card"
              style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14, cursor: activePanel === "upload" ? "default" : "pointer", borderColor: activePanel === "upload" ? "var(--blue)" : undefined }}
              onClick={() => { if (activePanel !== "upload") { setActivePanel("upload"); setTimeout(() => fileInputRef.current?.click(), 50); } }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 36, height: 36, borderRadius: 9, flex: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", background: activePanel === "upload" ? "var(--blue)" : "var(--blue-soft)", color: activePanel === "upload" ? "#fff" : "var(--blue)" }}>
                  <Icon name="export" size={18} />
                </span>
                <div>
                  <div className="t-label" style={{ color: "var(--text-2)", fontSize: 10.5 }}>OPTION 3</div>
                  <div className="t-name" style={{ fontSize: 15 }}>Upload your data</div>
                </div>
              </div>
              <p className="t-meta" style={{ margin: 0 }}>Upload your spreadsheet (.xlsx or .csv) and start exploring.</p>
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" multiple style={{ display: "none" }} onChange={handleUpload} />
              {activePanel === "upload" && (
                <button
                  className="pill-btn primary"
                  style={{ width: "100%", justifyContent: "center" }}
                  disabled={busy}
                  onClick={(e) => { e.stopPropagation(); !busy && fileInputRef.current?.click(); }}
                >
                  {uploadCsv.isPending ? "Uploading…" : <>Choose a file <Icon name="export" size={15} stroke={2.1} /></>}
                </button>
              )}
            </div>
          </div>

          {error && (
            <p className="t-meta" style={{ color: "var(--error)", marginTop: 14, paddingLeft: 4 }}>
              Could not start a session:{" "}
              {typeof error === "string" ? error : (error as ApiError).displayMessage}
            </p>
          )}
        </div>

        {/* footer */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            marginTop: 40,
            paddingTop: 22,
            borderTop: "1px solid var(--border)",
            flexWrap: "wrap",
          }}
        >
          <span className="t-meta">
            In partnership with the{" "}
            <b style={{ color: "var(--text)" }}>UNESCO Chair in AI &amp; Data Science for Society</b>
          </span>
          <span
            className="t-meta"
            style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}
          >
            By
            <a
              href="https://www.linkedin.com/in/arthursarazin/"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--blue)", fontWeight: 600 }}
            >
              Arthur Sarazin
            </a>
            <span aria-hidden="true">·</span>
            <a
              href="https://www.linkedin.com/in/mathis-mourey-189640153/"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--blue)", fontWeight: 600 }}
            >
              Mathis Mourey
            </a>
          </span>
        </div>
      </div>
    </div>
  );
}

/* ---- the five-level descent/ascent diagram in the hero card ---- */
function DescentAscentDiagram() {
  const steps = [
    { code: "Start", glyph: "table", label: "Your raw files" },
    { code: "Step 1", glyph: "graph", label: "Find links" },
    { code: "Step 2", glyph: "categories", label: "Group & sort" },
    { code: "Step 3", glyph: "vector", label: "Key numbers" },
    { code: "Result", glyph: "core", label: "Your answer" },
  ];
  const colColor = (i: number) => gradientColor(i / (steps.length - 1));

  const IconCell = ({ s, i }: { s: (typeof steps)[number]; i: number }) => {
    const col = colColor(i);
    const isCore = i === steps.length - 1;
    return (
      <span
        style={{
          width: 52,
          height: 52,
          borderRadius: 15,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          background: isCore ? col : "var(--bg)",
          color: isCore ? "#fff" : col,
          border: `2px solid ${col}`,
          boxShadow: isCore ? "var(--shadow-1)" : "none",
          justifySelf: "center",
        }}
      >
        <Icon name={s.glyph} size={25} stroke={1.9} />
      </span>
    );
  };

  const Conn = ({ ascent }: { ascent: boolean }) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 9, alignSelf: "center", padding: "0 3px" }}>
      <div style={{ position: "relative", height: 2, background: "var(--border-strong)", borderRadius: 2 }}>
        <span
          style={{
            position: "absolute",
            right: -1,
            top: -4,
            width: 0,
            height: 0,
            borderTop: "5px solid transparent",
            borderBottom: "5px solid transparent",
            borderLeft: "7px solid var(--border-strong)",
          }}
        />
      </div>
      <div style={{ position: "relative", height: 2, background: ascent ? "var(--blue)" : "transparent", borderRadius: 2 }}>
        {ascent && (
          <span
            style={{
              position: "absolute",
              left: -1,
              top: -4,
              width: 0,
              height: 0,
              borderTop: "5px solid transparent",
              borderBottom: "5px solid transparent",
              borderRight: "7px solid var(--blue)",
            }}
          />
        )}
      </div>
    </div>
  );

  const cols = "auto 1fr auto 1fr auto 1fr auto 1fr auto";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, width: "100%" }}>
      <div style={{ display: "grid", gridTemplateColumns: cols, alignItems: "center", rowGap: 9 }}>
        {steps.map((s, i) => (
          <span key={"i" + s.code} style={{ display: "contents" }}>
            <IconCell s={s} i={i} />
            {i < steps.length - 1 && <Conn ascent={i > 0} />}
          </span>
        ))}
        {steps.map((s, i) => (
          <span key={"l" + s.code} style={{ display: "contents" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
              <span className="mono" style={{ fontSize: 12, fontWeight: 700, color: colColor(i) }}>
                {s.code}
              </span>
              <span className="t-meta" style={{ fontSize: 11.5 }}>
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && <div />}
          </span>
        ))}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
        <span className="chip" style={{ background: "var(--neutral-soft)", color: "var(--neutral)" }}>
          <Icon name="arrowRight" size={14} stroke={2.2} /> Simplify -- find the core insight
        </span>
        <span className="chip" style={{ background: "var(--blue-soft)", color: "var(--blue)" }}>
          <Icon name="up" size={14} stroke={2.2} /> Rebuild -- add context for your question
        </span>
      </div>
    </div>
  );
}

/* ---- a single entry card (demo use-case) ---- */
function EntryCard({
  glyph,
  kicker,
  title,
  desc,
  meta,
  cta,
  sources,
  busy,
  onClick,
}: {
  glyph: string;
  kicker: string;
  title: string;
  desc: string;
  meta?: string;
  cta: string;
  sources?: [string, string];
  busy?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      style={{
        textAlign: "left",
        display: "flex",
        flexDirection: "column",
        gap: 0,
        width: "100%",
        background: "var(--bg)",
        borderRadius: "var(--radius-xl)",
        padding: 22,
        border: "1px solid var(--border)",
        transition: "border-color .15s, box-shadow .15s, transform .08s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "var(--blue)";
        e.currentTarget.style.boxShadow = "var(--shadow-1)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--border)";
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
        <span
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            flex: "none",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--blue)",
            color: "#fff",
          }}
        >
          <Icon name={glyph} size={22} stroke={1.9} />
        </span>
        <span className="t-label" style={{ color: "var(--text-2)", whiteSpace: "nowrap" }}>
          {kicker}
        </span>
      </div>
      <div className="t-section" style={{ fontSize: 19, marginBottom: 6 }}>
        {title}
      </div>
      <div className="t-body" style={{ color: "var(--text-2)", marginBottom: sources ? 14 : 16, textWrap: "pretty" }}>
        {desc}
      </div>
      {sources && (
        <div style={{ display: "flex", flexDirection: "column", gap: 7, marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span className="chip mono" style={{ whiteSpace: "nowrap" }}>
              {sources[0]}
            </span>
            <span className="mono" style={{ color: "var(--text-2)", fontWeight: 700 }}>
              +
            </span>
            <span className="chip mono" style={{ whiteSpace: "nowrap" }}>
              {sources[1]}
            </span>
          </div>
          <span className="t-meta" style={{ fontSize: 11.5 }}>
            two unrelated tables → one raw dataset
          </span>
        </div>
      )}
      <div style={{ marginTop: "auto", display: "flex", alignItems: "center", gap: 10 }}>
        <span className="pill-btn primary" style={{ height: 40, pointerEvents: "none" }}>
          {busy ? "Starting…" : cta} <Icon name="arrowRight" size={16} stroke={2.1} />
        </span>
        {meta && (
          <span className="t-meta mono" style={{ marginLeft: "auto" }}>
            {meta}
          </span>
        )}
      </div>
    </button>
  );
}

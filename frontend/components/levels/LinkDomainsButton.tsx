"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { apiPost } from "@/lib/api/client";

function isFrench(text: string): boolean {
  const frenchWords = /\b(les|des|dans|pour|avec|sur|qui|que|quoi|est|sont|comment|quels?|quel(?:le)?s?|où|ou)\b/i;
  return frenchWords.test(text);
}

function PersonaCard({ icon, name, description }: { icon: string; name: string; description: string }) {
  return (
    <div
      role="banner"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px",
        background: "var(--blue-soft-2)",
        borderRadius: "var(--radius-md)",
        marginBottom: 8,
      }}
    >
      <span style={{ fontSize: 20 }} aria-hidden="true">{icon}</span>
      <div>
        <span style={{ fontWeight: 700, fontSize: 13, color: "var(--text)" }}>{name}</span>
        <p style={{ margin: 0, fontSize: 12, color: "var(--text-2)", lineHeight: 1.4 }}>{description}</p>
      </div>
    </div>
  );
}

interface LinkageAnalyzeResult {
  code: string;
  proposed_columns: string[];
  explanation: string;
  confidence: string;
  graph_description: string;
  sample_distribution: Record<string, Record<string, number>>;
  error?: string;
}

interface CatalogMatchResult {
  source: string;
  id: string;
  name: string;
  relevance_reason: string;
  database_id?: string;
  organization?: string;
}

interface CatalogSuggestResult {
  world_bank: CatalogMatchResult[];
  datagouv: CatalogMatchResult[];
  explanation: string;
  error?: string;
}

export function LinkDomainsButton({
  sessionId,
  onConfirm,
  initialIntent,
}: {
  sessionId: string;
  onConfirm?: () => void;
  initialIntent?: string;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<LinkageAnalyzeResult | null>(null);
  const [catalogResults, setCatalogResults] = useState<CatalogSuggestResult | null>(null);
  const [selectedCatalog, setSelectedCatalog] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState(initialIntent ?? "");
  const [showCode, setShowCode] = useState(false);

  async function analyze() {
    setAnalyzing(true);
    setError(null);
    setCatalogResults(null);
    setSelectedCatalog(new Set());

    const [linkageResult, catalogResult] = await Promise.allSettled([
      apiPost<LinkageAnalyzeResult>(
        `/sessions/${sessionId}/linkage-analyze`,
        { intent },
      ),
      apiPost<CatalogSuggestResult>(
        `/sessions/${sessionId}/linkage-catalog-suggest`,
        { intent },
      ),
    ]);

    if (linkageResult.status === "fulfilled" && !linkageResult.value.error) {
      setResult(linkageResult.value);
    } else if (linkageResult.status === "rejected") {
      setError(String(linkageResult.reason));
    } else if (linkageResult.status === "fulfilled" && linkageResult.value.error) {
      setError(linkageResult.value.error);
    }

    if (catalogResult.status === "fulfilled" && !catalogResult.value.error) {
      const cr = catalogResult.value;
      if (cr.world_bank.length > 0 || cr.datagouv.length > 0) {
        setCatalogResults(cr);
      }
    }

    setAnalyzing(false);
  }

  function toggleCatalogSource(key: string) {
    setSelectedCatalog((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function confirm() {
    if (!result && selectedCatalog.size === 0) return;
    setConfirming(true);
    setError(null);

    try {
      if (selectedCatalog.size > 0 && catalogResults) {
        const sources: Array<{ type: string; id: string; database_id?: string }> = [];
        for (const key of selectedCatalog) {
          const [type, id] = key.split(":", 2);
          if (type === "worldbank") {
            const match = catalogResults.world_bank.find((m) => m.id === id);
            sources.push({ type: "worldbank", id, database_id: match?.database_id });
          } else {
            sources.push({ type: "datagouv", id });
          }
        }
        await apiPost(`/sessions/${sessionId}/linkage-catalog-merge`, {
          sources,
          intent,
        });
      } else if (result) {
        await apiPost(`/sessions/${sessionId}/linkage-confirm`, {
          code: result.code,
        });
      }
      if (onConfirm) await onConfirm();
      setConfirming(false);
      setResult(null);
      setCatalogResults(null);
    } catch (e) {
      setError(String(e));
      setConfirming(false);
    }
  }

  const examplePrompts = [
    "Compare GDP across regions",
    "Link to population data",
    "Test against climate indicators",
  ];

  const fr = isFrench(intent);

  if (!result && !catalogResults) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <PersonaCard
          icon="🌍"
          name="The Explorer"
          description={fr
            ? "Je vais chercher dans les catalogues publics des données liées aux vôtres."
            : "I'll search public catalogs for related data and connect it to yours."}
        />
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder={fr ? "Quelles données voulez-vous relier ?" : "What other data would you like to bring in?"}
          style={{
            width: "100%", height: 36, borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-strong)", background: "var(--bg)",
            color: "var(--text)", fontFamily: "var(--font)", fontSize: 13, padding: "0 12px",
          }}
        />
        {!intent && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {examplePrompts.map((ex) => (
              <button
                key={ex}
                className="pill-btn ghost"
                style={{ height: 26, fontSize: 11, color: "var(--text-2)" }}
                onClick={() => setIntent(ex)}
              >
                e.g. {ex}
              </button>
            ))}
          </div>
        )}
        <button
          className="card"
          onClick={analyze}
          disabled={analyzing}
          aria-label="Search for and connect related external data"
          style={{
            padding: "14px 16px", display: "flex", alignItems: "center", gap: 10,
            width: "100%", border: "1.5px dashed var(--blue)",
            background: analyzing ? "var(--surface)" : "var(--blue-soft)",
            cursor: analyzing ? "wait" : "pointer", textAlign: "left",
          }}
        >
          <Icon name="graph" size={16} />
          <span style={{ fontWeight: 600, color: "var(--blue)" }}>
            {analyzing ? <span role="status" aria-live="polite">{fr ? "Recherche en cours (15-30 secondes)..." : "Searching catalogs and analyzing (15-30 seconds)..."}</span> : (fr ? "Explorer les données liées" : "Explore related data")}
          </span>
          {error && <span style={{ color: "var(--error)", fontSize: 12, marginLeft: "auto" }}>{error}</span>}
        </button>
      </div>
    );
  }

  const distEntries = Object.entries(result?.sample_distribution || {});
  const hasCatalog = catalogResults && (catalogResults.world_bank.length > 0 || catalogResults.datagouv.length > 0);

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", border: "1.5px solid var(--blue)" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10, background: "var(--blue-soft)" }}>
        <span style={{ fontSize: 18 }} aria-hidden="true">🌍</span>
        <span style={{ fontWeight: 700, fontSize: 14, color: "var(--blue)" }}>
          {fr ? "Voici ce que l'Explorateur a trouvé" : "Here's what the Explorer found"}
        </span>
        <button className="pill-btn ghost" onClick={() => { setResult(null); setCatalogResults(null); analyze(); }} style={{ marginLeft: "auto", height: 26, fontSize: 11 }}>
          {fr ? "Réessayer" : "Retry"}
        </button>
        <button className="pill-btn ghost" onClick={() => { setResult(null); setCatalogResults(null); }} style={{ height: 26, fontSize: 11 }}>
          {fr ? "Annuler" : "Cancel"}
        </button>
      </div>

      {/* Catalog matches from World Bank + data.gouv.fr */}
      {hasCatalog && (
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 10 }}>
            {fr ? "DONNÉES PUBLIQUES DISPONIBLES" : "PUBLIC DATA YOU CAN CONNECT"}
          </span>
          <p style={{ margin: "0 0 10px", fontSize: 12, color: "var(--text-2)" }}>
            {fr
              ? "Sélectionnez les jeux de données à relier aux vôtres pour créer un super-dataset."
              : "Select datasets to merge with yours and create a super-dataset with links nobody has seen before."}
          </p>

          {catalogResults!.world_bank.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-2)", display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span aria-hidden="true">🏦</span> World Bank
              </span>
              {catalogResults!.world_bank.map((m) => {
                const key = `worldbank:${m.id}`;
                const checked = selectedCatalog.has(key);
                return (
                  <label
                    key={key}
                    style={{
                      display: "flex", alignItems: "center", gap: 10, padding: "8px 10px",
                      borderRadius: "var(--radius-md)", cursor: "pointer",
                      background: checked ? "var(--blue-soft)" : "transparent",
                      border: checked ? "1px solid var(--blue)" : "1px solid var(--border)",
                      marginBottom: 4, transition: "background 0.15s ease",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleCatalogSource(key)}
                      style={{ accentColor: "var(--blue)" }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {m.name}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-2)" }}>{m.id}</div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}

          {catalogResults!.datagouv.length > 0 && (
            <div>
              <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-2)", display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span aria-hidden="true">🇫🇷</span> data.gouv.fr
              </span>
              {catalogResults!.datagouv.map((m) => {
                const key = `datagouv:${m.id}`;
                const checked = selectedCatalog.has(key);
                return (
                  <label
                    key={key}
                    style={{
                      display: "flex", alignItems: "center", gap: 10, padding: "8px 10px",
                      borderRadius: "var(--radius-md)", cursor: "pointer",
                      background: checked ? "var(--blue-soft)" : "transparent",
                      border: checked ? "1px solid var(--blue)" : "1px solid var(--border)",
                      marginBottom: 4, transition: "background 0.15s ease",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleCatalogSource(key)}
                      style={{ accentColor: "var(--blue)" }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {m.name}
                      </div>
                      {m.organization && (
                        <div style={{ fontSize: 11, color: "var(--text-2)" }}>{m.organization}</div>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Computed columns section (from existing linkage-analyze) */}
      {result && (
        <>
          {result.explanation && (
            <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", fontSize: 13, lineHeight: 1.5, color: "var(--text-2)" }}>
              {hasCatalog && (
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 6 }}>
                  {fr ? "COLONNES CALCULÉES À PARTIR DE VOS DONNÉES" : "COMPUTED FROM YOUR EXISTING DATA"}
                </span>
              )}
              {result.explanation}
            </div>
          )}

          {distEntries.length > 0 && (
            <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 8 }}>
                {fr ? "APERÇU DES GROUPES" : "HOW YOUR DATA WILL BE SPLIT (sample)"}
              </span>
              {distEntries.map(([colName, dist]) => (
                <div key={colName} style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{colName}</span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                    {Object.entries(dist).map(([val, count]) => (
                      <span key={val} className="chip" style={{ fontSize: 11, padding: "3px 8px", background: "var(--surface)", border: "1px solid var(--border)" }}>
                        {val}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {result.proposed_columns.length > 0 && !hasCatalog && (
            <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", display: "block", marginBottom: 8 }}>
                {fr ? "COLONNES AJOUTÉES" : "COLUMNS THAT WILL BE ADDED"}
              </span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {result.proposed_columns.map((col) => (
                  <span key={col} className="chip" style={{ fontSize: 12, padding: "4px 10px", background: "var(--blue-soft)", color: "var(--blue)", fontWeight: 600 }}>
                    {col}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.graph_description && (
            <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)" }}>
              <p className="t-meta" style={{ fontSize: 12 }}>{result.graph_description}</p>
            </div>
          )}

          {result.code && (
            <div style={{ padding: "8px 16px", borderBottom: "1px solid var(--border)" }}>
              <button
                className="pill-btn ghost"
                onClick={() => setShowCode(!showCode)}
                style={{ height: 24, fontSize: 11 }}
              >
                {showCode ? (fr ? "Masquer le code" : "Hide code") : (fr ? "Voir le code" : "Show code")}
              </button>
              {showCode && (
                <pre style={{ marginTop: 8, fontSize: 11, lineHeight: 1.4, background: "var(--surface)", padding: 10, borderRadius: "var(--radius-sm)", overflow: "auto", maxHeight: 200 }}>
                  {result.code}
                </pre>
              )}
            </div>
          )}
        </>
      )}

      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
        <button
          className="pill-btn primary"
          disabled={confirming || (!result && selectedCatalog.size === 0)}
          onClick={confirm}
          style={{ height: 36, fontSize: 13 }}
        >
          <span role="status" aria-live="polite">
            {confirming
              ? (fr ? "Construction en cours..." : "Building your super-dataset...")
              : selectedCatalog.size > 0
                ? (fr ? `Connecter ${selectedCatalog.size} source${selectedCatalog.size > 1 ? "s" : ""} et continuer` : `Connect ${selectedCatalog.size} source${selectedCatalog.size > 1 ? "s" : ""} and continue`)
                : (fr ? "Confirmer et continuer" : "Confirm and continue")}
          </span>
        </button>
        {error && <span style={{ color: "var(--error)", fontSize: 12 }}>{error}</span>}
      </div>
    </div>
  );
}

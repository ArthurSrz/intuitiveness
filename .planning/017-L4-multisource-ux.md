# Plan: L4 Multi-Source UX — Branch 017-backend-phase-a

## Problem
The L4 level is designed around **multiple unlinked tables** (e.g. "DNB brevet results + Collège effectifs"), but the current UI makes it look like a single-file upload. Three gaps:

1. Source chips in `L4Sources.tsx` are `<span>` — not clickable, only first table previewed
2. No "Add another dataset" affordance once a session has started
3. Home page copy doesn't explain the unlinked multi-table pattern

---

## Fix 1 — Clickable source tabs in `L4Sources.tsx`

**File:** `frontend/components/levels/L4Sources.tsx`

**Change:** Add `selectedSource` state (default = first source name). Render each source chip as a `<button>` instead of `<span>`. Preview the **selected** source's table, not always the primary.

```tsx
// Add at top of component body:
const [selectedName, setSelectedName] = useState<string>(sources[0]?.name ?? "");
const selected = sources.find(s => s.name === selectedName) ?? sources[0];
const table = selected?.table ?? null;

// Chip button (replace <span key={s.name} className="chip mono">):
<button
  key={s.name}
  className={`chip mono ${s.name === selectedName ? "chip--active" : ""}`}
  style={{ cursor: "pointer", border: s.name === selectedName ? "1.5px solid var(--blue)" : undefined }}
  onClick={() => setSelectedName(s.name)}
>
  {s.name}
  {shapes?.[s.name] != null && (
    <span className="t-meta" style={{ fontWeight: 400 }}>{String(shapes[s.name])}</span>
  )}
</button>
```

Also update the footer row label from `primary.name` to `selected.name`.

---

## Fix 2 — "Add a source" button in the guided L4 step

**Files:**
- `frontend/components/shell/Guided.tsx` — add UI
- `backend/app/routers/sessions.py` — add endpoint
- `backend/app/service.py` — add service method

### Backend endpoint
```python
# POST /sessions/{session_id}/add-source
# Accepts: List[UploadFile]
# Returns: SessionState
# Logic: load current L4 node, merge new DataFrames into existing tables dict, save
```

Add to `SessionService`:
```python
def add_source(self, session_id: str, tables: Dict[str, pd.DataFrame]) -> dict:
    """Append tables to an existing L4 session node."""
    # load tree, get current L4 node, merge tables, re-save
```

### Frontend (Guided.tsx — inside the L4 step block)
Find where `current_level === 4` is rendered. Add below the `<LevelView>`:

```tsx
{/* Only show when at L4 and no descent started yet */}
{state.current_level === 4 && (
  <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 10 }}>
    <input
      ref={addSourceRef}
      type="file"
      accept=".csv,text/csv"
      multiple
      style={{ display: "none" }}
      onChange={handleAddSource}
    />
    <button
      className="pill-btn ghost"
      onClick={() => addSourceRef.current?.click()}
      disabled={addSourceBusy}
    >
      {addSourceBusy ? "Adding…" : "+ Add another dataset"}
    </button>
    <span className="t-meta">
      Each table stays unlinked at L4 — the descent joins them
    </span>
  </div>
)}
```

Add `useAddSource()` hook in `frontend/lib/api/hooks.ts`:
```ts
export function useAddSource() {
  return useMutation({ mutationFn: (p: {sessionId: string; files: File[]}) =>
    apiUpload<SessionState>(`/sessions/${p.sessionId}/add-source`, p.files) });
}
```

---

## Fix 3 — Home page copy

**File:** `frontend/app/page.tsx`

Change the "Bring your own data" description from:
> "Upload one or more CSV files — encoding and delimiter are detected for you, then we build the raw view to begin."

To:
> "Upload two unlinked tables — or one to start. Encoding and delimiter are auto-detected. You can add more sources once the session opens."

---

## Fix 4 (bonus) — Source count badge color

In `L4Sources.tsx`, make the `{sources.length} source{s}` badge turn blue when `> 1`:

```tsx
<span className="t-meta mono" style={{
  marginLeft: "auto",
  color: sources.length > 1 ? "var(--blue)" : undefined,
  fontWeight: sources.length > 1 ? 700 : undefined,
}}>
  {sources.length} source{sources.length === 1 ? "" : "s"}
</span>
```

---

## Context to restore in next session

- Branch: `017-backend-phase-a`
- Backend live at: `https://backend-production-fafb.up.railway.app`
- Frontend live at: `https://frontend-production-be0d8.up.railway.app`
- All P2/P3/P4/P5 features committed and tested
- This plan has NOT been implemented yet — start here

## Test to write after implementing

```python
# tests/test_l4_multisource.py
def test_add_source_to_existing_session(tmp_path):
    svc = make_svc(tmp_path)
    state = svc.create_from_tables({"scores.csv": df1})
    assert state["summary"]["source_count"] == 1
    state2 = svc.add_source(state["session_id"], {"funding.csv": df2})
    assert state2["summary"]["source_count"] == 2
```

## Files to touch (summary)

| File | Change |
|------|--------|
| `frontend/components/levels/L4Sources.tsx` | Clickable tabs, selected-source preview |
| `frontend/components/shell/Guided.tsx` | "Add another dataset" button |
| `frontend/lib/api/hooks.ts` | `useAddSource()` hook |
| `backend/app/routers/sessions.py` | `POST /sessions/{id}/add-source` endpoint |
| `backend/app/service.py` | `add_source()` method |
| `frontend/app/page.tsx` | Updated copy for "Bring your own data" |
| `tests/test_l4_multisource.py` | New test (TDD: write first) |

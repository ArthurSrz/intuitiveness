# Frontend Troubleshooting

Problems met (and their fixes) while wiring the Blue Pulse redesign to the live
backend. Found during the Chrome MCP descent→ascent walkthrough (2026-06-09).

## 1. "Could not start a session" / `TypeError: Failed to fetch` from the browser

**Symptom:** Clicking a demo on the landing page failed with a blank "Could not
start a session:". `curl` to the same backend worked fine.

**Cause:** CORS. The deployed backend's `ALLOWED_ORIGINS` only allows the
Railway frontend origin, not `http://localhost:3100`. `curl` skips the CORS
preflight, so it succeeded while the browser `fetch` was blocked. (A plain
network/CORS failure throws a `TypeError`, not an `ApiError`, so
`error.displayMessage` was `undefined` → the message looked empty.)

**Fix for local dev:** run the backend locally with the dev origin allowed and
point the frontend at it:
```bash
# backend (from repo root)
cd backend && ALLOWED_ORIGINS="http://localhost:3100" \
  PYTHONPATH="$(cd .. && pwd)" python3 -m uvicorn app.main:app --port 8000
# frontend
cd frontend && NEXT_PUBLIC_API_URL="http://localhost:8000" npx next dev -p 3100
```
Note: `allow_credentials=True` can't pair with `allow_origins=["*"]`, so set the
explicit origin. The local backend falls back to file storage with no
`DATABASE_URL`.

## 2. Level views showed encoded blobs / wrong columns

The engine encodes every payload; the UI must decode each kind. The decoders
live in `lib/payload.ts`.

- **L0 datum showed `eJwzNdUzAAACAwDJ`** — the "value" payload is a
  zlib+base64-encoded scalar. Added `decodeValue()` (inflate → parse number);
  the clean numeric value is also on the *session* summary (`summary.value`).
- **L4 / L2 tables showed `columns / index / data` as headers** — DataFrames
  are serialized in pandas **`split` orient** (`{columns, index, data}`), not
  `columns` orient. `decodeDataframe()` now detects split orient
  (`splitFrameToTable`).
- **L1 vector was empty ("0 dims")** — the vector is a one-column split-orient
  DataFrame, zlib+base64-encoded. Added `decodeVector()`.
- **L3 graph: "No graph payload available"** — the graph is zlib+base64-encoded
  NetworkX node-link JSON, and uses the **`edges`** key (newer NetworkX), not
  `links`. Added `decodeGraph()` (inflate + accept `edges`/`links`).
- **L3 on ascent rendered nothing** — the L2→L3 *ascent* produces a
  **dataframe** (`payload_kind: "dataframe"`, the "purpose-built dataset"), not
  a graph. `LevelView` now branches on `payload_kind`: graph on descent, the
  table component (`<L2Table code="L3">`) on ascent.

## 3. Guided phase / step was always "Descending"

**Symptom:** After ascending L0→L1, the app still showed "Extract Features"
(descent L1) instead of "Rebuild Vector" (ascent L1).

**Cause:** phase was derived from `node.action === "ascend"`, but the engine
stores **every** node's action as `"entry"` — that signal doesn't exist.

**Fix:** derive phase from the tree topology — a node whose parent sits at a
*lower* level was reached by ascending; otherwise descending
(`app/session/[id]/page.tsx`).

## 4. Core datum disappeared during the ascent

The L0 value only appears on the session summary while the pointer is at L0 (the
tree's L0 node carries an empty `output_snapshot`). Fixed by remembering the
datum in client state + `sessionStorage` (`intuitiveness:datum:<id>`) so the
CORE DATUM card keeps showing it through the ascent and across reloads.

# Intuitiveness Frontend

Next.js (App Router) + TypeScript + Tailwind frontend for the Intuitiveness
descent/ascent engine. It talks to the FastAPI backend over the contract in
`lib/api/openapi.json`.

## Stack

- **Next.js 15** (App Router) + **React 19**
- **Tailwind CSS** wired entirely to design tokens (`styles/tokens.css`)
- **@tanstack/react-query** for server state
- **reactflow** for the L3 graph view
- **pako** to inflate the zlib+base64 dataframe payloads (L2 table)
- **openapi-typescript** to generate API types from the OpenAPI schema

## Setup

```bash
npm install
npm run gen:api      # generates lib/api/schema.ts from lib/api/openapi.json
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL if not localhost:8000
npm run dev          # http://localhost:3000
```

The backend base URL is read from `NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`).

## Scripts

| Script            | What it does                                            |
| ----------------- | ------------------------------------------------------- |
| `npm run dev`     | Start the dev server                                    |
| `npm run build`   | Production build (the contract-drift gate, SC-003)      |
| `npm run gen:api` | Regenerate `lib/api/schema.ts` from `openapi.json`      |

## Design tokens (SC-004)

Every visual value lives in `styles/tokens.css` and is exposed to Tailwind via
`tailwind.config.ts`. Components consume **only** token-backed utilities
(`bg-bg`, `text-fg`, `rounded-md`, …) — never raw hex/px. Flip a token value and
the whole app restyles with zero component edits. A `[data-theme="dark"]`
palette is included; set `data-theme="dark"` on `<html>` to use it.

## Structure

```
app/
  layout.tsx            # tokens.css + globals + React Query provider
  providers.tsx         # QueryClientProvider (client component)
  page.tsx              # landing: pick a demo, create session, route
  session/[id]/page.tsx # workspace: rail + level view + tree + export/import
components/
  levels/               # L4Sources, L3Graph, L2Table, L1Vector, L0Datum, LevelView
  nav/                  # LevelRail, BranchTree
  ui/                   # Card, Button
  StatusBadge.tsx       # /healthz indicator
  SessionActions.tsx    # export / import
lib/
  api/                  # client, hooks, types, schema (generated), openapi.json
  payload.ts            # dataframe (pako) decoder
styles/
  tokens.css            # the design-system seam
```

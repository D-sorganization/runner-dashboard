# Frontend — Migration Plan

## Current state (Phase 1)

The original single-file SPA (`_legacy/index.html`, ~17 900 lines) is preserved
for reference. A Vite + React + TypeScript build pipeline is now in place.

### Directory layout

```
frontend/
  _legacy/index.html   # Original single-file SPA (reference only — do not edit)
  src/
    main.tsx           # React entry point
    App.tsx            # Root component (Phase 1 placeholder)
    vite-env.d.ts      # Vite client type reference
  index.html           # Vite HTML entry (thin shell)
  package.json         # Dependencies: React 18, react-router-dom, TypeScript
  vite.config.ts       # Build config — output to dist/, dev proxy → localhost:8321
  tsconfig.json        # Strict TypeScript config
```

## Development workflow

```bash
# Install dependencies (one-time)
cd frontend
npm install

# Start Vite dev server (proxies /api to backend on :8321)
npm run dev          # → http://localhost:5173

# Type-check without building
npm run typecheck

# Production build (output to frontend/dist/)
npm run build
```

## Backend integration

In development the Vite dev server proxies `/api/*` to the FastAPI backend
running on `http://localhost:8321` (see `vite.config.ts`).

For production, run `npm run build` and point the FastAPI `FRONTEND_DIR`
at `frontend/dist/` (or serve `dist/index.html` via the existing
`serve_index` route after updating the path).

## Migration phases

| Phase | Goal | Status |
|-------|------|--------|
| 1 | Vite + React-TS scaffold, preserve legacy SPA | **Done** (this PR) |
| 2 | Extract CSS variables / design tokens into `src/styles/` | Planned |
| 3 | Extract API layer (`src/api/`) — thin wrappers around fetch | Planned |
| 4 | Extract shared components (Header, Cards, Badges…) | Planned |
| 5 | Extract tab pages (Runners, Workflows, Metrics, Settings…) | Planned |
| 6 | Wire routing with react-router-dom, remove legacy file | Planned |

Track progress in GitHub issue #173.

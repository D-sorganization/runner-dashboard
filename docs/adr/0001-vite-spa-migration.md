# 0001. Single-file SPA to Vite + React + TypeScript migration

## Status

Accepted

## Context

The runner-dashboard frontend originally shipped as a single self-contained
`frontend/index.html` (~18,000 lines) that loaded React from a CDN, used the
hand-written `h()` helper instead of JSX, and had no build step. This made
the project trivial to deploy: any operator could open the file and serve it
behind FastAPI without `node_modules`, lockfiles, or a compiler. For a small
single-tab dashboard this was a reasonable tradeoff.

As the surface area grew, the single-file approach started to hurt:

- Eleven independent tabs (Fleet, Org, Heavy, Workflows, Remediation,
  Maxwell, Assessments, Feature Requests, Credentials, Reports, Queue
  Health) all live in one document. A failure in one tab can crash the
  shell, which violates the orthogonality principle in `CLAUDE.md`.
- The bundle is downloaded eagerly, even for tabs the operator never opens.
  There is no code splitting and no lazy loading.
- The frontend speaks to ~80 typed API contracts but has no static types.
  Drift between backend payload shapes and frontend consumers is only
  caught at runtime, in production, by the operator.
- `h()` is unfamiliar to most contributors and makes diffs harder to read.
- Modern tooling (ESLint, prettier, Vitest, source maps, tree shaking,
  CSS modules, design tokens) is unavailable.

We needed a path that preserved the no-friction local dev story while
giving us types, lazy loading, and module boundaries.

## Decision

Migrate the frontend to a Vite + React + TypeScript build:

- Source lives in `frontend/src/` with a TSX entrypoint `main.tsx`.
- `vite build` produces a hashed static bundle that the FastAPI backend
  serves verbatim. There is no separate Node process at runtime.
- Tabs are independent components under `frontend/src/pages/`, lazy-loaded
  via `React.lazy` so each tab is a separate chunk.
- Shared primitives live in `frontend/src/primitives/` and design tokens in
  `frontend/src/design/`.
- Legacy code is parked under `frontend/src/legacy/` and migrated
  incrementally; new code must be TSX, not `h()`.
- A perf budget at `frontend/perf-budget.json` is enforced in CI by
  `tests/test_frontend_perf_budget.py` so the bundle cannot silently bloat.

## Consequences

Positive:

- Static types catch backend/frontend contract drift before it reaches
  operators. Generated TypeScript types from pydantic models close the loop.
- Per-tab code splitting means a broken Maxwell tab does not download or
  execute Fleet tab code, reinforcing orthogonality.
- JSX/TSX is the industry default; new contributors do not have to learn
  the `h()` idiom.
- Vitest, ESLint, and source maps make the frontend testable and
  debuggable in ways the single-file SPA never was.

Negative:

- A build step now exists. Local development requires `npm install` and a
  running Vite dev server (or a pre-built `dist/`). The `start-dashboard.sh`
  flow is more complex.
- `package.json`, `package-lock.json`, and `node_modules` are now part of
  the supply chain. Dependency audits and Renovate policy must cover both
  Python and npm.
- The legacy `index.html` cannot be deleted overnight; the `legacy/` folder
  is a long-lived migration zone that has to be policed so it does not
  accrue new code.
- CI is slower: lint, type-check, build, and perf-budget checks all run on
  every PR.

The tradeoff is accepted: type safety, lazy loading, and code splitting
outweigh the build-step cost as the dashboard surface continues to grow.

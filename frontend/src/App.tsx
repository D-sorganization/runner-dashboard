import type { ReactElement } from "react";

/**
 * App — Phase 1 placeholder.
 *
 * The single-file SPA (17 k+ lines) is preserved at frontend/_legacy/index.html.
 * Subsequent phases will extract components from the legacy file into
 * src/components/, src/hooks/, src/api/, etc. and route them here.
 *
 * See frontend/README.md for the full migration plan.
 */
export default function App(): ReactElement {
  return (
    <div
      style={{
        background: "#0f1117",
        color: "#e6edf3",
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 32 32"
        width="64"
        height="64"
      >
        <defs>
          <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#4f8ff7" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="6" fill="url(#g)" />
        <path d="M18 6l-7 13h6l-1 7 7-13h-6z" fill="white" />
      </svg>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 600 }}>
        Runner Dashboard — Migration in progress
      </h1>
      <p style={{ color: "#8b949e", maxWidth: "480px", textAlign: "center" }}>
        Phase 1 Vite + React scaffold is live. Component extraction from the
        legacy single-file SPA begins in Phase 2.
      </p>
      <div style={{ display: "flex", gap: "16px", marginTop: "8px" }}>
        <a
          href="/api/health"
          style={{
            color: "#58a6ff",
            textDecoration: "none",
            border: "1px solid #30363d",
            padding: "8px 16px",
            borderRadius: "6px",
          }}
        >
          API Health
        </a>
        <a
          href="/docs"
          style={{
            color: "#58a6ff",
            textDecoration: "none",
            border: "1px solid #30363d",
            padding: "8px 16px",
            borderRadius: "6px",
          }}
        >
          API Docs
        </a>
      </div>
    </div>
  );
}

import type { CSSProperties } from "react";
import { prefersReducedMotion } from "../design/motion";

export interface SkeletonProps {
  /** Accessible label announced by assistive tech. Defaults to "Loading". */
  "aria-label"?: string;
  /** Width (number → px, string passed through, e.g. "50%"). Default: "100%". */
  width?: number | string;
  /** Height (number → px, string passed through). Default: 16. */
  height?: number | string;
  /** Border radius in px. Default: 4. */
  radius?: number;
  /** When set to N > 1, renders N stacked bars (multi-line text skeleton). */
  lines?: number;
  /** Optional className for the outer wrapper. */
  className?: string;
}

function toCssLength(value: number | string | undefined, fallback: string): string {
  if (value === undefined) return fallback;
  return typeof value === "number" ? `${value}px` : value;
}

export function Skeleton({
  "aria-label": ariaLabel = "Loading",
  width = "100%",
  height = 16,
  radius = 4,
  lines = 1,
  className = "",
}: SkeletonProps) {
  // Resolve once at render — matches the pattern used elsewhere in the app.
  const reducedMotion = prefersReducedMotion();

  const wrapperClasses = [
    "skeleton",
    reducedMotion ? "skeleton-reduced-motion" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const count = Math.max(1, Math.floor(lines));
  const lastIndex = count - 1;

  function barStyle(index: number): CSSProperties {
    // For multi-line skeletons, taper the final line for a natural ragged edge.
    const isLastShortened = count > 1 && index === lastIndex;
    return {
      width: isLastShortened ? "60%" : toCssLength(width, "100%"),
      height: toCssLength(height, "16px"),
      borderRadius: `${radius}px`,
      marginTop: index === 0 ? 0 : 8,
    };
  }

  return (
    <div
      aria-busy="true"
      aria-label={ariaLabel}
      className={wrapperClasses}
      data-touch-primitive="Skeleton"
      role="status"
    >
      {Array.from({ length: count }).map((_, index) => (
        <div
          aria-hidden="true"
          className="skeleton-bar"
          key={index}
          style={barStyle(index)}
        />
      ))}
    </div>
  );
}

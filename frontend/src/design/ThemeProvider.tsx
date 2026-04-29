import React from "react";
import { toCssVariables } from "./tokens";
import { motionDurations, motionEasing, reducedMotionCss } from "./motion";

export interface ThemeProviderProps {
  children: React.ReactNode;
  reducedMotion?: boolean;
}

/**
 * ThemeProvider injects the design-token CSS custom properties into a <style>
 * block so every component—legacy or modern—reads from the same source of truth.
 *
 * Usage:
 *   <ThemeProvider>
 *     <App />
 *   </ThemeProvider>
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  reducedMotion = false,
}) => {
  const css = `
    :root {
      ${toCssVariables()}
      --motion-instant: ${motionDurations.instant};
      --motion-fast: ${motionDurations.fast};
      --motion-normal: ${motionDurations.normal};
      --motion-slow: ${motionDurations.slow};
      --easing-standard: ${motionEasing.standard};
      --easing-emphasized: ${motionEasing.emphasized};
    }
    ${reducedMotion ? reducedMotionCss : ""}
  `;

  return (
    <>
      <style>{css}</style>
      {children}
    </>
  );
};

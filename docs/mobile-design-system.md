# Mobile Design System

## Accessibility Guards

Mobile interactive controls use the shared `--mobile-hit-target` CSS token,
currently `44px`, as the minimum hit target for primary button, tab, sub-tab,
report-card, input, select, and search controls at mobile viewport widths.

The frontend includes a `prefers-reduced-motion: reduce` media query that
collapses CSS animations and transitions. Inline transition styles must also
consult `prefersReducedMotion()` before applying animated transitions.

Static frontend integrity tests enforce this baseline so mobile accessibility
regressions fail in the existing Python test suite without requiring a flaky
browser pass.

## Manual Screen Reader Notes

Issue #201 still calls for a full VoiceOver and TalkBack walk-through of the M10
dispatch flow. This slice does not claim that manual audit; it establishes the
static guard coverage needed before that manual pass is useful.

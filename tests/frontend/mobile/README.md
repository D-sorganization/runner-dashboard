# Mobile Playwright Harness

Issue #202 is intentionally landing in slices. This directory is the checked-in
contract for the mobile Playwright suite before the repo enables browser-driven
CI or screenshot baselines.

- `viewport_profiles.json` defines the two required mobile profiles:
  `iphone-12` at 390 x 844 and `pixel-5` at 393 x 851.
- `viewport_profiles.schema.json` documents the stable shape of the checked-in
  harness metadata.
- `touch_helpers.js` provides the tap, swipe, and long-press helper surface that
  future Playwright tests should import.
- Visual regression is scaffolded but disabled in CI until the suite proves
  stable. Screenshot baselines must be created by an explicit
  `--update-snapshots` run, not by silent CI mutation.

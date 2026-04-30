#!/usr/bin/env python3
"""Regenerate the ADR index in docs/adr/README.md.

Scans docs/adr/ for files matching NNNN-*.md, sorts them by number, and
rewrites the "## Index" section of README.md with a Markdown table of
contents linking to each ADR. The README header (everything above the
"## Index" heading) is preserved verbatim.

Run from the repo root:

    python3 scripts/regenerate-adr-index.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent.parent / "docs" / "adr"
README_PATH = ADR_DIR / "README.md"
ADR_FILENAME_RE = re.compile(r"^(\d{4})-([a-z0-9][a-z0-9-]*)\.md$")
INDEX_HEADING = "## Index"


def find_adrs(adr_dir: Path) -> list[tuple[str, str, Path]]:
    """Return a sorted list of (number, slug, path) for ADR files."""
    entries: list[tuple[str, str, Path]] = []
    for path in sorted(adr_dir.iterdir()):
        match = ADR_FILENAME_RE.match(path.name)
        if not match:
            continue
        number, slug = match.group(1), match.group(2)
        entries.append((number, slug, path))
    return entries


def extract_title(adr_path: Path) -> str:
    """Pull the H1 title from an ADR file, stripping the leading number."""
    with adr_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                # Drop a leading "NNNN. " prefix if present.
                m = re.match(r"^\d{4}\.\s+(.*)$", title)
                if m:
                    return m.group(1)
                return title
    return adr_path.stem


def render_index(entries: list[tuple[str, str, Path]]) -> str:
    """Render the ## Index section body as Markdown."""
    if not entries:
        return f"{INDEX_HEADING}\n\n*None yet — this is a placeholder for future ADRs.*\n"

    lines = [INDEX_HEADING, ""]
    for number, _slug, path in entries:
        title = extract_title(path)
        link = path.name
        lines.append(f"- [{number}. {title}](./{link})")
    lines.append("")
    return "\n".join(lines)


def regenerate(readme_path: Path, index_body: str) -> str:
    """Return the new README contents with the Index section replaced."""
    if not readme_path.exists():
        raise FileNotFoundError(f"README not found at {readme_path}")
    text = readme_path.read_text(encoding="utf-8")
    head, sep, _ = text.partition(INDEX_HEADING)
    if not sep:
        # No existing Index heading; append.
        if not head.endswith("\n"):
            head += "\n"
        return head + "\n" + index_body
    if not head.endswith("\n"):
        head += "\n"
    return head + index_body


def main() -> int:
    entries = find_adrs(ADR_DIR)
    index_body = render_index(entries)
    new_text = regenerate(README_PATH, index_body)
    README_PATH.write_text(new_text, encoding="utf-8")
    print(f"Regenerated {README_PATH} with {len(entries)} ADR entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

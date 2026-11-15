#!/usr/bin/env python3
"""Validate pending release metadata and promote it into the published changelog."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
DATE_RE = re.compile(r"^Release date: (\d{4}-\d{2}-\d{2})$")
PLACEHOLDERS = {"tbd", "todo", "placeholder", "no changes", "n/a"}
CATEGORIES = {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}


def pending_notes(metadata: str, version: str) -> tuple[str, str]:
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"Invalid release version {version!r}; expected vMAJOR.MINOR.PATCH.")
    lines = metadata.splitlines()
    expected = f"# Pending release metadata: {version}"
    if not lines or lines[0].strip() != expected:
        raise ValueError(f"Pending metadata must begin with {expected!r}.")
    if len(lines) < 2 or not (date_match := DATE_RE.fullmatch(lines[1].strip())):
        raise ValueError("Pending metadata must include 'Release date: YYYY-MM-DD' on line 2.")
    release_date = date_match.group(1)
    try:
        dt.date.fromisoformat(release_date)
    except ValueError as error:
        raise ValueError(f"Invalid release date for {version}.") from error

    body = "\n".join(lines[2:]).strip()
    bullets = [
        match.group(1).strip()
        for line in lines[2:]
        if (match := re.match(r"^\s*-\s+(.+)$", line))
    ]
    meaningful = [
        item for item in bullets
        if item.lower() not in PLACEHOLDERS
        and "add changelog entries here" not in item.lower()
        and item != "..."
    ]
    if not meaningful:
        raise ValueError(f"Pending notes for {version} must contain at least one meaningful bullet.")
    notes = f"## [{version}] - {release_date}\n\n{body}\n"
    return release_date, notes


def promote_changelog(changelog: str, version: str, notes: str) -> str:
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"Invalid release version {version!r}; expected vMAJOR.MINOR.PATCH.")
    if re.search(rf"^## \[{re.escape(version)}\](?:\s|$)", changelog, re.MULTILINE):
        raise ValueError(f"Changelog already contains a published entry for {version}.")
    unreleased = re.search(r"^## \[Unreleased\]\s*$", changelog, re.MULTILINE)
    if not unreleased:
        raise ValueError("CHANGELOG.md is missing the ## [Unreleased] section.")
    return changelog[:unreleased.start()] + notes.rstrip() + "\n\n" + changelog[unreleased.start():]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Release tag such as v1.2.3")
    parser.add_argument("--metadata", help="Path to pending metadata (defaults to release-notes/<version>.md)")
    parser.add_argument("--output", help="Write validated release notes to this file")
    parser.add_argument("--promote-changelog", help="Promote validated notes into this changelog path")
    args = parser.parse_args()

    metadata_path = Path(args.metadata or f"release-notes/{args.version}.md")
    try:
        release_date, notes = pending_notes(metadata_path.read_text(encoding="utf-8"), args.version)
        if args.promote_changelog:
            changelog_path = Path(args.promote_changelog)
            promoted = promote_changelog(changelog_path.read_text(encoding="utf-8"), args.version, notes)
            changelog_path.write_text(promoted, encoding="utf-8")
            print(f"Promoted {args.version} ({release_date}) into {changelog_path}.")
        elif args.output:
            Path(args.output).write_text(notes, encoding="utf-8")
            print(f"Validated pending metadata for {args.version}; release notes written to {args.output}.")
        else:
            print(notes, end="")
    except (OSError, ValueError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

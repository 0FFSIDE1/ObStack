#!/usr/bin/env python3
"""Validate and extract the changelog notes for a semantic-version release."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r"^v(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$")
ENTRY_RE = re.compile(r"^## \\[(v\\d+\\.\\d+\\.\\d+)\\] - (\\d{4}-\\d{2}-\\d{2})\\s*$")
PLACEHOLDERS = {"tbd", "todo", "placeholder", "no changes", "n/a"}


def release_notes(changelog: str, version: str) -> str:
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"Invalid release version {version!r}; expected vMAJOR.MINOR.PATCH.")

    lines = changelog.splitlines()
    matches = [
        index
        for index, line in enumerate(lines)
        if (match := ENTRY_RE.fullmatch(line)) and match.group(1) == version
    ]
    if not matches:
        raise ValueError(f"Missing dated changelog entry for {version}.")
    if len(matches) > 1:
        raise ValueError(f"Duplicate changelog entries found for {version}.")

    start = matches[0]
    date_match = ENTRY_RE.fullmatch(lines[start])
    try:
        dt.date.fromisoformat(date_match.group(2))
    except ValueError as error:
        raise ValueError(f"Invalid release date in changelog entry for {version}.") from error

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break

    section = lines[start:end]
    bullets = [
        line.strip()[2:].strip()
        for line in section[1:]
        if re.match(r"^\\s*-\\s+", line)
    ]
    meaningful = [
        item
        for item in bullets
        if item.lower() not in PLACEHOLDERS
        and "add changelog entries here" not in item.lower()
        and item != "..."
    ]
    if not meaningful:
        raise ValueError(f"Changelog entry for {version} must contain at least one meaningful bullet.")

    return "\\n".join(section).strip() + "\\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Release tag such as v1.2.3")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Path to changelog")
    parser.add_argument("--output", help="Write extracted release notes to this file")
    args = parser.parse_args()

    try:
        notes = release_notes(Path(args.changelog).read_text(encoding="utf-8"), args.version)
    except (OSError, ValueError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(notes, encoding="utf-8")
        print(f"Validated changelog for {args.version}; release notes written to {args.output}.")
    else:
        print(notes, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

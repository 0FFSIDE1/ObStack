#!/usr/bin/env python3
"""Generate pending release metadata from merged pull requests on the release branch."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION_RE = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
CATEGORY_LABELS = {
    "release:added": "Added",
    "release:changed": "Changed",
    "release:deprecated": "Deprecated",
    "release:removed": "Removed",
    "release:fixed": "Fixed",
    "release:security": "Security",
}
CATEGORIES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")
CONVENTIONAL = re.compile(r"^(feat|fix|security|refactor|perf|docs|chore|ci|test|build)(?:\([^)]*\))?!?:\s*(.+)$", re.IGNORECASE)


def run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def release_commits(previous_tag: str | None) -> set[str]:
    revision = f"{previous_tag}..HEAD" if previous_tag else "HEAD"
    output = run(["git", "rev-list", "--first-parent", revision])
    return {line.strip().lower() for line in output.splitlines() if line.strip()}


def latest_release_tag() -> str | None:
    tags = run(["git", "tag", "--merged", "HEAD", "--list", "v[0-9]*", "--sort=-version:refname"])
    return tags.splitlines()[0] if tags else None


def classify(pr: dict) -> str:
    labels = {
        item["name"] if isinstance(item, dict) else str(item)
        for item in pr.get("labels", [])
    }
    selected = labels.intersection(set(CATEGORY_LABELS) | {"release:none"})
    if len(selected) > 1:
        raise ValueError(f"PR #{pr.get('number')} has conflicting release labels: {', '.join(sorted(selected))}.")
    if selected:
        label = next(iter(selected))
        return "None" if label == "release:none" else CATEGORY_LABELS[label]

    title = str(pr.get("title", "")).strip()
    match = CONVENTIONAL.match(title)
    if not match:
        raise ValueError(
            f"PR #{pr.get('number')} has no release label and its title is not Conventional Commit format. "
            "Add one release:* label or use a conventional PR title."
        )
    kind = match.group(1).lower()
    return {
        "feat": "Added",
        "fix": "Fixed",
        "security": "Security",
        "refactor": "Changed",
        "perf": "Changed",
        "docs": "Changed",
        "chore": "None",
        "ci": "None",
        "test": "None",
        "build": "None",
    }[kind]


def build_metadata(version: str, prs: list[dict], included_commits: set[str], release_date: str) -> str:
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"Invalid release version {version!r}; expected vMAJOR.MINOR.PATCH.")
    try:
        dt.date.fromisoformat(release_date)
    except ValueError as error:
        raise ValueError("Release date must be a valid YYYY-MM-DD date.") from error

    entries: dict[str, list[str]] = {category: [] for category in CATEGORIES}
    for pr in sorted(prs, key=lambda item: int(item.get("number", 0))):
        merge_commit = (pr.get("mergeCommit") or {}).get("oid", "").lower()
        if not merge_commit or merge_commit not in included_commits:
            continue
        category = classify(pr)
        if category == "None":
            continue
        title = re.sub(r"\s+", " ", str(pr.get("title", "")).strip())
        if not title:
            raise ValueError(f"PR #{pr.get('number')} has an empty title.")
        url = str(pr.get("url", "")).strip()
        reference = f"[#{pr['number']}]({url})" if url else f"#{pr['number']}"
        entries[category].append(f"- {title} ({reference})")

    sections = [
        f"### {category}\n" + "\n".join(entries[category])
        for category in CATEGORIES if entries[category]
    ]
    if not sections:
        raise ValueError("No user-facing merged pull requests were found since the previous release tag.")

    return (
        f"# Pending release metadata: {version}\n"
        f"Release date: {release_date}\n\n"
        + "\n\n".join(sections)
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Release tag such as v1.2.3")
    parser.add_argument("--repo", required=True, help="GitHub repository in owner/name form")
    parser.add_argument("--base-branch", default="release")
    parser.add_argument("--output", help="Output path; defaults to release-notes/<version>.md")
    parser.add_argument("--previous-tag", help="Override automatic previous release tag detection")
    args = parser.parse_args()

    try:
        if not VERSION_RE.fullmatch(args.version):
            raise ValueError(f"Invalid release version {args.version!r}; expected vMAJOR.MINOR.PATCH.")
        previous_tag = args.previous_tag or latest_release_tag()
        included = release_commits(previous_tag)
        raw = run([
            "gh", "pr", "list", "--repo", args.repo, "--state", "merged",
            "--base", args.base_branch, "--limit", "1000",
            "--json", "number,title,labels,mergeCommit,url",
        ])
        prs = json.loads(raw)
        date = dt.datetime.now(ZoneInfo("Africa/Lagos")).date().isoformat()
        content = build_metadata(args.version, prs, included, date)
        output = Path(args.output or f"release-notes/{args.version}.md")
        if output.exists():
            raise ValueError(f"Refusing to overwrite existing release metadata: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        boundary = previous_tag or "repository history"
        print(f"Generated {output} from merged PRs after {boundary}.")
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        print(f"::error::{detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

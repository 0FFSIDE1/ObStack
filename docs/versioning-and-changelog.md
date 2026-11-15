# Versioning and changelog

ObStack keeps its release history in the repository's root `CHANGELOG.md`.
The changelog follows Keep a Changelog conventions and Semantic Versioning.

## Required workflow

1. For every user-facing change merged toward the `release` branch, add a concise
   entry under `[Unreleased]` in the appropriate category:
   - **Added**: new capabilities
   - **Changed**: behavior or configuration changes
   - **Deprecated**: capabilities scheduled for removal
   - **Removed**: removed capabilities
   - **Fixed**: bug fixes
   - **Security**: security-related changes
2. Before cutting a version, convert the Unreleased heading into a dated version
   heading such as `## [v1.2.3] - 2026-11-15`. Keep the entries underneath it.
3. Add a fresh `## [Unreleased]` section at the top for subsequent work.
4. Create the version tag only on the exact reviewed `release` branch HEAD, following
   the repository's release policy.

## Automated enforcement

The release workflow runs `scripts/release_changelog.py` against the pushed version
tag. It fails unless `CHANGELOG.md` contains a matching dated `vMAJOR.MINOR.PATCH`
section with at least one meaningful bullet. After the existing validation and
production deployment succeed, the workflow creates a GitHub Release whose notes
are extracted from that exact changelog section.

Validate locally:

```bash
python scripts/release_changelog.py v1.2.3
```

Extract notes to a file:

```bash
python scripts/release_changelog.py v1.2.3 --output release-notes.md
```

A tag without a matching changelog entry cannot pass the release workflow.

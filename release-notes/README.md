# Pending release metadata

Release-note files are generated automatically from merged pull requests on
the `release` branch. Run **Actions → Prepare release notes from merged pull
requests** on the `release` branch and provide a version such as `v1.3.0`.
The workflow creates a reviewed PR containing
`release-notes/v1.3.0.md`; merge it before tagging.

Use clear PR titles and one of the labels `release:added`,
`release:changed`, `release:deprecated`, `release:removed`,
`release:fixed`, `release:security`, or `release:none`. Without a release
label, supported Conventional Commit title prefixes are used to infer the
category. See `docs/versioning-and-changelog.md` for the complete mapping.

The first line must be `# Pending release metadata: vMAJOR.MINOR.PATCH`, the
second line must be `Release date: YYYY-MM-DD`, followed by meaningful notes.
The generator uses the `Africa/Lagos` date, includes PR references, validates
the output, and refuses to overwrite existing metadata.

The file is validated again on the release tag and is used as GitHub Release
notes only after production deployment succeeds. Successful deployment and
GitHub Release publication trigger a PR that promotes these notes into root
`CHANGELOG.md` and removes the pending metadata file. Failed deployment does
not publish either artifact.

# Pending release metadata

Create one file per release tag at `release-notes/vMAJOR.MINOR.PATCH.md`.
The first line must be `# Pending release metadata: vMAJOR.MINOR.PATCH`, the
second line must be `Release date: YYYY-MM-DD`, followed by meaningful notes
in Keep a Changelog categories. This file is validated on the tag and is used
as GitHub Release notes only after production deployment succeeds.

Successful deployment and GitHub Release publication trigger a PR that promotes
these notes into root `CHANGELOG.md` and removes the pending metadata file.
Failed deployment does not publish either artifact.

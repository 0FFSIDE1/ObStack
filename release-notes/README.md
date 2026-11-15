# Pending release metadata

Prepare one file per release tag at `release-notes/vMAJOR.MINOR.PATCH.md`
using the controller-only Ansible playbook
`ansible/playbooks/prepare-release-metadata.yml`. Supply the tag and meaningful
notes in Keep a Changelog categories (Added, Changed, Deprecated, Removed,
Fixed, Security). The playbook sets the release date using `Africa/Lagos`,
validates the rendered file with `scripts/release_changelog.py`, and refuses
to overwrite an existing file.

The first line must be `# Pending release metadata: vMAJOR.MINOR.PATCH`, the
second line must be `Release date: YYYY-MM-DD`, followed by meaningful notes.
The file is validated again on the release tag and is used as GitHub Release
notes only after production deployment succeeds.

Successful deployment and GitHub Release publication trigger a PR that promotes
these notes into root `CHANGELOG.md` and removes the pending metadata file.
Failed deployment does not publish either artifact.

The preparation playbook runs only on the Ansible controller. It does not
connect to production hosts, create tags, push commits, publish GitHub Releases,
or deploy the platform.

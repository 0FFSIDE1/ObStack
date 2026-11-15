# Versioning and changelog

ObStack's root `CHANGELOG.md` is the published release history. Release notes
are kept as pending metadata under `release-notes/vMAJOR.MINOR.PATCH.md` until
the tagged deployment has succeeded.

## Preparing pending release metadata

Create `release-notes/v1.2.3.md` for the intended tag. Use this exact format:

```markdown
# Pending release metadata: v1.2.3
Release date: 2026-11-15

### Added
- Describe a user-facing capability.

### Changed
- Describe a behavior change.

### Fixed
- Describe a fix.
```

The metadata must match the tag, contain a valid ISO date, and include at least
one meaningful bullet. Keep `CHANGELOG.md`'s `[Unreleased]` section for ongoing
work; do not move pending notes into the versioned history before deployment.

## Required release automation secret

Configure repository secret `OBSTACK_RELEASE_AUTOMATION_TOKEN` before releasing.
Use a fine-grained PAT restricted to this repository with **Contents: Read and
write** and **Pull requests: Read and write**. The workflow preflight checks that
the secret is present before deployment. The token is used after successful
deployment to push the promotion branch and open a PR; using this dedicated
token allows GitHub Actions checks to trigger on that generated PR.

## Release ordering and failure behavior

1. The release tag must point to the exact reviewed `release` branch HEAD.
2. Pending metadata, configuration CI, Ansible validation, and the automation-token
   preflight are checked.
3. Production deployment runs only when all those checks pass.
4. Only after deployment succeeds, the workflow publishes a GitHub Release using
   the pending metadata as its notes.
5. After the GitHub Release succeeds, the workflow opens a changelog-promotion PR
   against `release`. That PR moves the notes into a dated version section in
   root `CHANGELOG.md` and removes the pending metadata file.

If validation or deployment fails, no GitHub Release is published and no
changelog-promotion PR is opened. Root `CHANGELOG.md` remains unchanged.

The promotion is intentionally a PR, not a direct push: the release branch's
required review and protection rules stay in effect. The published GitHub Release
is already created after deployment; merging the follow-up PR synchronizes the
repository's changelog history under normal governance.

## Local validation

```bash
python scripts/release_changelog.py v1.2.3
python scripts/release_changelog.py v1.2.3 --output release-notes.md
```

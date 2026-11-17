# Versioning and changelog

ObStack's root `CHANGELOG.md` is the published release history. Release notes
are kept as pending metadata under `release-notes/vMAJOR.MINOR.PATCH.md` until
the tagged deployment has succeeded.

**Repository snapshot (2026-11-17):** `v0.0.2` metadata is pending on the
`release` branch. No version tag or GitHub Release has been published, and no
tagged deployment has run. See [current implementation and project
status](implementation-status.md) for the branch heads and CI evidence.

## Automatic release-note generation

Release-note entries are generated from merged pull requests on the `release`
branch. You do not need to write changelog bullets manually.

1. Give each user-facing PR a clear, user-facing title. Conventional Commit
   titles are supported: `feat:` maps to Added, `fix:` to Fixed,
   `security:` to Security, and `refactor:`, `perf:`, and `docs:` to
   Changed. `chore:`, `ci:`, `test:`, and `build:` are excluded.
2. For exact classification, add one label: `release:added`,
   `release:changed`, `release:deprecated`, `release:removed`,
   `release:fixed`, or `release:security`. An explicit label overrides
   title inference. Use `release:none` to exclude internal or non-user-facing
   work. Do not apply more than one release label.
3. Before tagging a release, open **Actions → Prepare release notes from
   merged pull requests → Run workflow**, select the `release` branch, and
   enter the version (for example `v1.3.0`).
4. The workflow finds merged PRs on `release` since the previous reachable
   version tag, categorizes their titles, adds PR links, dates the file in
   `Africa/Lagos`, validates it, and opens a PR containing
   `release-notes/v1.3.0.md`.
5. Review and merge that metadata PR into `release`. Then create the version
   tag on the updated release branch HEAD.

A PR without a release label must use a recognized Conventional Commit title;
otherwise generation fails with the PR number so it can be classified. The
generator fails on conflicting labels and refuses to overwrite existing
metadata. It excludes the release-metadata preparation PR automatically via
the `release:none` label.

The Ansible playbook
`ansible/playbooks/prepare-release-metadata.yml` remains available for
controller-only manual preparation when needed. It validates metadata but
does not contact production hosts or publish releases.

## Required release automation secret

Configure repository secret `OBSTACK_RELEASE_AUTOMATION_TOKEN` before running
the workflow. Use a fine-grained PAT restricted to this repository with
**Contents: Read and write** and **Pull requests: Read and write**. It is used
to push the metadata branch and open the PR.

## Release ordering and failure behavior

1. The release tag must point to the exact reviewed `release` branch HEAD.
2. Pending metadata, configuration CI, Ansible validation, and the
   automation-token preflight are checked.
3. Production deployment runs only when all those checks pass.
4. Only after deployment succeeds, the workflow publishes a GitHub Release
   using the pending metadata as its notes.
5. After the GitHub Release succeeds, the workflow opens a changelog-promotion
   PR against `release`. That PR moves the notes into a dated version section
   in root `CHANGELOG.md` and removes the pending metadata file.

If validation or deployment fails, no GitHub Release is published and no
changelog-promotion PR is opened. Root `CHANGELOG.md` remains unchanged.

The promotion is intentionally a PR, not a direct push: the release branch's
required review and protection rules stay in effect.

## Local validation

```bash
python scripts/release_changelog.py v1.3.0
python scripts/release_changelog.py v1.3.0 --output release-notes.md
python -m unittest discover -s tests -p 'test_*.py'
```

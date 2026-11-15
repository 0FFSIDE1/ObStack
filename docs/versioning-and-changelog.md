# Versioning and changelog

ObStack's root `CHANGELOG.md` is the published release history. Release notes
are kept as pending metadata under `release-notes/vMAJOR.MINOR.PATCH.md` until
the tagged deployment has succeeded.

## Preparing pending release metadata with Ansible

Run the controller-only playbook from the repository root. Supply a semantic
version tag and meaningful notes as lists under Keep a Changelog categories:

```bash
ANSIBLE_CONFIG="$PWD/ansible/ansible.cfg" ansible-playbook \
  ansible/playbooks/prepare-release-metadata.yml \
  -e '{"release_version":"v1.3.0","obstack_release_notes":{"Added":["Add a capability description."],"Fixed":["Describe a user-visible fix."]}}'
```

The playbook creates `release-notes/v1.3.0.md`, writes the release date in
`Africa/Lagos`, and validates the result with the same Python validator used
by CI and the tag-triggered release workflow. Supported categories are Added,
Changed, Deprecated, Removed, Fixed and Security. At least one meaningful
bullet is required; placeholder-only notes fail validation. Existing metadata
is validated but never overwritten.

This playbook runs on `localhost` with privilege escalation disabled. It does
not connect to production hosts, create or push tags, publish GitHub Releases,
or deploy anything. Review and commit the generated file through a normal PR.

Keep `CHANGELOG.md`'s `[Unreleased]` section for ongoing work; do not move
pending notes into the versioned history before deployment.

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
python scripts/release_changelog.py v1.3.0
python scripts/release_changelog.py v1.3.0 --output release-notes.md
```

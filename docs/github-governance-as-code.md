# GitHub governance as code

This repository stores its GitHub repository rulesets in `.github/rulesets/*.json`. The workflow `.github/workflows/apply-github-governance.yml` validates the files and can create or update the rulesets through the GitHub REST API.

## Scope

- Protect `main` and `release` with pull-request-only changes.
- Require one approving review, dismiss stale approvals, require approval of the latest push, and resolve review conversations.
- Require the two CI checks that have been observed on the current PR: `config` and `Syntax, lint, Compose and Nginx validation`.
- Require signed commits and linear history; disallow force pushes and branch deletion.
- Protect semantic version tags matching `v*`: only the repository owner can create them, and no actor can update or delete them.
- Keep release deployment's exact-`release`-HEAD check in `.github/workflows/release.yml`. A ruleset does not prove the tag points to the reviewed release branch commit.

## Important implementation detail

Tag creation and tag immutability are separate rulesets. The creation ruleset has the repository owner as its only bypass actor so the owner can create a version tag. A second ruleset has no bypass actors and blocks updates and deletion. This avoids giving the tag creator a blanket bypass over immutability.

The branch ruleset has no bypass actors. Repository administrators are therefore not silently exempted from its requirements.

## One-time GitHub setup

1. Open **Settings → Environments** and create an environment named exactly `github-governance`.
2. Configure **Required reviewers** for that environment. Add the repository owner or designated repository administrators. Enable prevention of self-review if available.
3. Add an environment secret named `OBSTACK_GOVERNANCE_TOKEN`.
4. Use a fine-grained personal access token scoped only to `0FFSIDE1/ObStack`, with **Administration: Read and write** and **Contents: Read-only**. Do not paste the token into chat or commit it to the repository. A dedicated GitHub App installation token with equivalent repository administration permission is also suitable.
5. In **Actions → Validate and apply GitHub governance**, run the workflow from the reviewed default branch with `apply=false` first. Review the validation output.
6. Run it again with `apply=true`. The apply job will pause for approval at the `github-governance` environment. Approving the environment is the explicit authorization to change repository rulesets.

The workflow uses GitHub's authenticated API and is idempotent: it creates missing rulesets and updates existing rulesets by name. After the run, verify the three rulesets are listed and active under **Settings → Rules → Rulesets**.

## Safety and limitations

- Committing these JSON files does not activate any repository protection by itself.
- The workflow's validation job is read-only. Repository settings are changed only when `apply=true`, the required environment approval is granted, and the administrator token is available.
- The current connector cannot write repository rulesets directly, so activation must happen through the approved workflow run.
- The branch protection rules require the exact CI check names listed above. If a workflow/job is renamed, update the required contexts in the JSON before applying; otherwise PRs can remain blocked by a missing required check.
- GitHub rulesets do not guarantee that a tag's target is the current release branch HEAD. The release workflow independently enforces exact SHA equality before deployment.
- No AWS resources, EC2 instances, production hosts, WireGuard configuration, or deployments are changed by this governance workflow.

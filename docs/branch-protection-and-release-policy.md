# Protected branch and release policy

## Current repository limitation

ObStack is a private repository. GitHub currently reports that repository rulesets require an upgrade or a public repository, and the connected GitHub integration cannot read or write classic branch-protection settings. GitHub's plan documentation states that protected branches are available on private repositories with GitHub Pro, GitHub Team, or GitHub Enterprise; GitHub Free supports protected branches only on public repositories.

Therefore, repository policy files and CI checks do not themselves enforce protected-branch rules. An administrator must upgrade the private repository to GitHub Pro (or higher) and configure the settings below in GitHub. Do not treat this policy as active until the GitHub UI shows the rules enabled and the branch protection endpoint confirms protection.

## Branch layout

- `main`: integration branch; receives changes only through reviewed pull requests.
- `release`: production release branch; receives reviewed pull requests from `main` (or approved hotfix branches), never direct pushes.
- `feat/*`, `fix/*`, `docs/*`, `chore/*`: working branches; normal pushes are allowed here and all changes enter `main`/`release` through pull requests.

The `release` branch has been created from the current `main` baseline. It must be updated from `main` through a PR after the pending integration PRs have merged. Do not push commits directly to `release`.

## Required protection for both `main` and `release`

In **Settings → Branches → Add classic branch protection rule**, create a rule for each exact branch name (`main` and `release`). If GitHub Pro rulesets are available, a single branch ruleset targeting both names is preferred.

Enable all of the following:

1. **Require a pull request before merging.** No direct branch updates.
2. **Require 2 approving reviews** before merge. Both approvals must be from distinct collaborators with write access; do not count the PR author.
3. **Dismiss stale pull request approvals when new commits are pushed.**
4. **Require approval of the most recent reviewable push** by someone other than the person who pushed it.
5. **Require conversation resolution before merging.** Every inline review thread must be resolved; requested changes must be addressed and then approved. Do not dismiss a blocking `CHANGES_REQUESTED` review merely to bypass it.
6. **Require status checks to pass before merging**, and **require branches to be up to date** before merge. Select these check names after they have reported on a PR:
   - `config` (configuration validation)
   - `Syntax, lint, Compose and Nginx validation` (Ansible syntax/lint and related checks)
   Ensure the release workflow validation checks remain required for release changes.
7. **Require signed commits.**
8. **Require linear history.** Use squash or rebase merges; disable merge commits if enforcing this.
9. **Do not allow bypassing the above settings**, including administrators.
10. **Do not allow force pushes** (leave force-push allowance disabled).
11. **Do not allow deletions** of protected branches.
12. Do not add bypass actors or deploy bots to the bypass list.

The PR template at `.github/PULL_REQUEST_TEMPLATE.md` reminds contributors of the expected checks and review hygiene. It is a checklist, not a security boundary; branch protection is the enforcement layer.

## Protect release tags

Create a tag ruleset targeting `v*` (for example `v1.2.3`) and enable:

- Restrict tag creation to designated release managers/release automation only.
- Block tag updates and deletion.
- No bypass actors except the minimum dedicated release administrators, if a bypass is unavoidable.

Do not allow force-updating or deleting published version tags. Tag protection is separate from branch protection. On the current private GitHub Free plan, rulesets are not available; upgrade to GitHub Pro or higher to enforce tag rulesets.

## Deployment tag source enforcement

`.github/workflows/release.yml` runs only on version-tag pushes. Before CI or deployment, it fetches `origin/release` and requires the tag's commit SHA to equal the exact current `release` branch HEAD. A tag from `main`, a feature branch, an old release commit, or any other commit fails closed before deployment. Configuration validation and Ansible syntax/lint validation must then pass before the production deployment job can run.

This exact-HEAD check prevents a tag pointing to an arbitrary commit from deploying, but it is not a substitute for a tag ruleset: a user with tag-write permission could still create, move, or delete a tag. Keep tag creation restricted and immutable through GitHub settings.

## Release procedure

1. Merge approved feature/fix PRs into `main` after all required checks and two approvals.
2. Open a PR from `main` into `release`.
3. Obtain two approvals, resolve all review conversations, and pass all required checks on the release PR.
4. Merge the PR into `release`.
5. Create the semantic version tag on the exact current `release` HEAD (for example, `v1.2.3`). Do not tag a feature or `main` commit.
6. Confirm the release workflow's branch verification, configuration validation, and Ansible validation pass.
7. Production deployment still requires approval of the separate `production` GitHub Environment, if configured.

No branch protection or tag ruleset has been activated by this code change. No production deployment or host changes were made.

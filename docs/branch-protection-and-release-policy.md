# Protected branch and release policy

## Repository visibility and enforcement

ObStack is a **public** GitHub repository. GitHub repository rulesets can be used on this repository; the earlier statement in this document that it was private and required a paid-plan upgrade was incorrect and is superseded.

The desired policy is defined as code in `.github/rulesets/`. The configuration is not enforcement until the rulesets have been applied and GitHub confirms that they are active. See [GitHub governance as code](github-governance-as-code.md) for the approval-gated apply procedure.

## Branch layout

- `main`: integration branch; receives changes only through reviewed pull requests.
- `release`: production release branch; receives reviewed pull requests from `main` (or approved hotfix branches), never direct pushes.
- `feat/*`, `fix/*`, `docs/*`, `chore/*`: working branches.

The `release` branch exists from the current `main` baseline. Update it through a pull request after integration changes are ready. Do not push commits directly to `release`.

## Required branch controls

The `obstack-main-release-protection` ruleset targets both `main` and `release` and requires:

1. Pull requests for all changes; direct pushes are blocked.
2. Two approving reviews.
3. Dismissal of stale approvals when new commits are pushed.
4. Approval of the most recent reviewable push by someone other than its author.
5. Resolution of all review conversations.
6. Successful and up-to-date `config` and `Syntax, lint, Compose and Nginx validation` checks.
7. Verified signed commits and linear history.
8. No force pushes and no branch deletion.
9. No bypass actors, including repository administrators.
10. Squash or rebase merging only.

If a CI job is renamed, update the required check context in the ruleset JSON before applying it. A mismatched required check intentionally blocks merging rather than weakening the policy.

## Version tag controls

Two rulesets target `refs/tags/v*`:

- `obstack-version-tag-creation`: only the repository owner (GitHub user ID `173492580`) can create matching version tags.
- `obstack-version-tags-immutable`: blocks updates and deletion and has no bypass actors.

Keeping creation and immutability separate is deliberate: the creation exception does not grant the owner a bypass over the immutable-tag ruleset.

## Deployment tag source enforcement

`.github/workflows/release.yml` runs only on version-tag pushes. Before validation or deployment it fetches `origin/release` and requires the tag's commit SHA to equal the exact current `release` branch HEAD. A tag from `main`, a feature branch, an older release commit, or any other commit fails closed.

Rulesets do not prove tag ancestry or that a tag points to the latest reviewed release commit; the workflow's exact-SHA check enforces that condition.

## Release procedure

1. Merge approved feature/fix PRs into `main` after required checks and two approvals.
2. Open a PR from `main` into `release`.
3. Obtain two approvals, resolve review conversations, and pass required checks.
4. Merge the PR into `release`.
5. Create the semantic version tag on the exact current `release` HEAD (for example, `v1.2.3`).
6. Confirm release verification, configuration validation, and Ansible validation pass.
7. Production deployment remains gated by the separate `production` GitHub Environment.

No production host, AWS resource, WireGuard configuration, or deployment is changed by repository governance configuration.
